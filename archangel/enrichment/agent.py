"""EnrichmentAgent — Event-driven agent that listens for posts and enriches lead metadata."""

import logging
from typing import Optional

from archangel.enrichment.engine import EnrichmentEngine
from archangel.enrichment.classifier import MultiLabelPainClassifier, OpportunityClassifier
from archangel.enrichment.ai_readiness import AIReadinessDetector
from archangel.scoring.competition import CompetitionAnalyzer
from archangel.enrichment.fingerprint import WebsiteFingerprinter
from archangel.events.triggers import TriggerDetector
from archangel.memory.graph import HistoricalMemory
from archangel.scoring.revenue import RevenueEstimator
from archangel.enrichment.pitch import PitchGenerator
from archangel.events import EventBus
from archangel.models import RawPost, Lead
from archangel.storage import StorageBackend
from dataclasses import asdict

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """Subscribes to 'raw_post.stored' or 'lead.deduped.passed' events and persists enriched lead details."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        engine: Optional[EnrichmentEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.engine = engine or EnrichmentEngine()
        self.pain_classifier = MultiLabelPainClassifier()
        self.opportunity_classifier = OpportunityClassifier()
        self.ai_readiness = AIReadinessDetector()
        self.competition_analyzer = CompetitionAnalyzer()
        self.fingerprinter = WebsiteFingerprinter(timeout=3)
        from archangel.enrichment.difficulty import LeadDifficultyClassifier
        self.difficulty_classifier = LeadDifficultyClassifier()
        self.trigger_detector = TriggerDetector()
        self.historical_memory = HistoricalMemory(storage=self.storage)
        self.revenue_estimator = RevenueEstimator()
        self.pitch_generator = PitchGenerator()

        self.event_bus.subscribe("raw_post.stored", self._on_raw_post_stored)
        self.event_bus.subscribe("lead.deduped.passed", self._on_lead_deduped_passed)
        logger.debug("EnrichmentAgent initialized and subscribed to event bus")

    def _on_raw_post_stored(self, payload: dict) -> None:
        post = payload.get("post")
        raw_post_id = payload.get("raw_post_id")
        if post and raw_post_id:
            self._process_enrichment(post, raw_post_id)

    def _on_lead_deduped_passed(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        if raw_post_id:
            # Check if post exists in storage
            leads = self.storage.get_leads(limit=100)
            target = next((r for r in leads if r.get("id") == raw_post_id), None)
            if target:
                p = RawPost(
                    source=target.get("source", ""),
                    channel=target.get("channel", ""),
                    author=target.get("author", ""),
                    content=target.get("content", ""),
                    url=target.get("url", ""),
                    metadata={},
                )
                self._process_enrichment(p, raw_post_id)

    def _process_enrichment(self, post: RawPost, raw_post_id: int, evaluation: Optional[dict] = None) -> Lead:
        eval_data = evaluation or {}
        # 1. Base Deep Profile & Heuristics
        enriched = self.engine.enrich_post(post)
        profile = enriched["company_profile"]
        content_text = post.content or ""
        
        # 2. Tech Fingerprinting
        domain = profile["domain"]["value"]
        fingerprint_data = self.fingerprinter.analyze_sync(domain) if domain else {"health": None, "fingerprint": None}
        
        if fingerprint_data["fingerprint"] and fingerprint_data["fingerprint"]["frameworks"]:
            enriched["detected_tech"] = list(set(enriched.get("detected_tech", []) + fingerprint_data["fingerprint"]["frameworks"]))
            
        # 3. AI Readiness & Detectors
        ai_readiness = self.ai_readiness.evaluate(content_text)
        
        # Instantiate detectors
        from archangel.enrichment.buying_intent import BuyingIntentDetector
        from archangel.enrichment.hiring import HiringSignalDetector
        
        buying_detector = BuyingIntentDetector()
        hiring_detector = HiringSignalDetector()
        
        buying_res = buying_detector.evaluate(content_text)
        hiring_res = hiring_detector.evaluate(content_text)
        
        # 4. Competition Analysis
        competition = self.competition_analyzer.evaluate(post)
        
        # 5. Buying Triggers & Historical Memory
        triggers = self.trigger_detector.detect(content_text)
        history = self.historical_memory.evaluate(domain, profile["company_name"]["value"], raw_post_id)
        
        # 6. Pain & Opportunity Classification
        pains = self.pain_classifier.classify(content_text)
        health_score = fingerprint_data["health"]["score"] if fingerprint_data["health"] else 100
        opportunities = self.opportunity_classifier.evaluate(pains, health_score=health_score)

        # 7. Commercial Intelligence (Revenue & Pitch)
        funding = profile.get("funding_stage", {}).get("value", "")
        team = profile.get("employee_count_range", {}).get("value", "")
        revenue = self.revenue_estimator.evaluate(funding, team, post.source or "")

        # 8. Lead Type Classification Rules
        import re
        from archangel.models import LeadType
        
        if hiring_res.score >= 50.0 and buying_res.score < 20.0:
            lead_type = LeadType.HIRING_SIGNAL
        elif buying_res.score >= 35.0:
            lead_type = LeadType.SALES_LEAD
        elif re.search(r"\b(?:raised|seed|series [a-z]|funding|invested)\b", content_text, re.IGNORECASE):
            lead_type = LeadType.FUNDING_EVENT
        elif re.search(r"\b(?:launching|show hn|introducing|launched|v1\.0|beta)\b", content_text, re.IGNORECASE):
            lead_type = LeadType.PRODUCT_LAUNCH
        elif re.search(r"\b(?:feature request|wish|would be nice|add support for)\b", content_text, re.IGNORECASE):
            lead_type = LeadType.FEATURE_REQUEST
        elif any(p.confidence >= 0.50 for p in pains):
            lead_type = LeadType.PAIN_DISCUSSION
        elif profile["company_name"]["value"] != "Unknown":
            lead_type = LeadType.COMPANY_INTELLIGENCE
        else:
            lead_type = LeadType.UNKNOWN

        # 9. Multi-Factor Weighted Scoring Engine (V1.5)
        from archangel.scoring.weights import calculate_recency_decay, get_source_quality_weight
        
        recency_mult, recency_exp = calculate_recency_decay(post.timestamp)
        source_weight, source_exp = get_source_quality_weight(post.source or "", post.channel or "")
        
        company_quality = 90.0 if (domain and profile["company_name"]["value"] != "Unknown") else 30.0
        pain_score = max([p.confidence for p in pains], default=0.0) * 100.0
        
        from archangel.agents.swarm.filter import extract_budget_profile
        b_prof = extract_budget_profile(content_text)
        budget_score = 100.0 if b_prof.amount and b_prof.amount >= 1000 else (50.0 if b_prof.amount else 20.0)
        budget_conf = 0.95 if b_prof.amount else 0.05
        urgency_score = 80.0 if re.search(r"\b(?:asap|urgent|immediately)\b", content_text, re.IGNORECASE) else 50.0
        tech_match_score = min(len(enriched.get("detected_tech", [])) * 25.0, 100.0)

        raw_sales_readiness = (
            buying_res.score * 0.35
            + company_quality * 0.20
            + pain_score * 0.15
            + budget_score * 0.15
            + urgency_score * 0.10
            + tech_match_score * 0.05
        ) * recency_mult * (source_weight / 100.0)

        # Cap Sales Readiness for Hiring Signals
        if lead_type == LeadType.HIRING_SIGNAL:
            sales_readiness = min(raw_sales_readiness, 20.0)
        else:
            sales_readiness = raw_sales_readiness

        # Calculate Opportunity Score (Strategic Value / Market Intelligence Value)
        comp_importance = company_quality
        if funding and funding != "Unknown":
            comp_importance = min(100.0, comp_importance + 10.0)
        if team and team != "1-10":
            comp_importance = min(100.0, comp_importance + 10.0)

        if lead_type == LeadType.FUNDING_EVENT:
            opportunity_score = 95.0 * (source_weight / 100.0)
        elif lead_type == LeadType.HIRING_SIGNAL:
            opportunity_score = 75.0 * (source_weight / 100.0)
        elif lead_type == LeadType.PRODUCT_LAUNCH:
            opportunity_score = 70.0 * (source_weight / 100.0)
        else:
            opportunity_score = max(sales_readiness, comp_importance) * (source_weight / 100.0)

        # Construct Human-Readable Score Explanation Breakdown List
        score_explanation = []
        score_explanation.append(f"+ Buying Intent: {buying_res.score:.0f}/100 (contrib +{buying_res.score * 0.35:.1f})")
        score_explanation.append(f"+ Company Quality: {company_quality:.0f}/100 (contrib +{company_quality * 0.20:.1f})")
        score_explanation.append(f"+ Source Quality Weight: {source_exp}")
        score_explanation.append(f"+ Recency Decay: {recency_exp}")

        if b_prof.formatted:
            score_explanation.append(f"+ Budget Detected: {b_prof.formatted} (Confidence: {budget_conf * 100:.0f}%)")

        if lead_type == LeadType.HIRING_SIGNAL:
            score_explanation.append("- Capped: Corporate W2 Recruitment Post (Sales Readiness max 20.0)")

        final_score = round(sales_readiness, 1)
        opportunity_score_final = round(opportunity_score, 1)
        priority = "HIGH" if (final_score >= 70.0 and lead_type == LeadType.SALES_LEAD) else ("MEDIUM" if final_score >= 40.0 else "LOW")
        conf = eval_data.get("confidence", 0.70)

        diff_res = self.difficulty_classifier.evaluate(content_text, budget=b_prof.amount)

        # Inject into output payload BEFORE pitch generation
        enriched["lead_type"] = lead_type.value
        enriched["sales_readiness"] = final_score
        enriched["opportunity_score"] = opportunity_score_final
        enriched["company_importance_score"] = round(comp_importance, 1)
        enriched["buying_intent_score"] = buying_res.score
        enriched["hiring_signal_score"] = hiring_res.score
        enriched["company_quality_score"] = company_quality
        enriched["budget_confidence"] = budget_conf
        enriched["score_explanation"] = score_explanation
        enriched["intent_evidence"] = buying_res.evidence
        enriched["difficulty_tier"] = diff_res.tier.value
        enriched["difficulty_reasons"] = diff_res.reasons
        enriched["pain_categories"] = [p.to_dict() if hasattr(p, 'to_dict') else asdict(p) for p in pains]
        enriched["opportunities"] = [o.to_dict() if hasattr(o, 'to_dict') else asdict(o) for o in opportunities]
        enriched["ai_readiness"] = ai_readiness.to_dict()
        enriched["competition"] = competition.to_dict()
        enriched["website_health"] = fingerprint_data["health"]
        enriched["website_fingerprint"] = fingerprint_data["fingerprint"]
        enriched["buying_triggers"] = [t.to_dict() if hasattr(t, 'to_dict') else asdict(t) for t in triggers]
        enriched["historical_context"] = history.to_dict()
        enriched["revenue_estimate"] = revenue.to_dict()
        enriched["url"] = post.url
        
        # Generate pitch using the fully enriched payload
        pitch = self.pitch_generator.generate(enriched)
        enriched["recommended_pitch"] = pitch.to_dict()

        # Construct Canonical Lead Object
        from archangel.models import Lead
        lead_obj = Lead(
            id=raw_post_id,
            raw_post=post,
            lead_type=lead_type,
            evaluation=eval_data,
            company_profile=profile,
            contacts={
                "name": profile.get("company_name", {}).get("value", "N/A"),
                "email": profile.get("primary_email", {}).get("value", "N/A"),
                "socials": profile.get("socials", {}).get("value", {}),
            },
            website={"domain": domain, "url": post.url},
            fingerprint=fingerprint_data.get("fingerprint") or {},
            ai_readiness=ai_readiness.to_dict(),
            health=fingerprint_data.get("health") or {},
            pains=[p.to_dict() if hasattr(p, 'to_dict') else asdict(p) for p in pains],
            opportunities=[o.to_dict() if hasattr(o, 'to_dict') else asdict(o) for o in opportunities],
            revenue=revenue.to_dict(),
            competition=competition.to_dict(),
            pitch=pitch.to_dict(),
            score=final_score,
            sales_readiness=final_score,
            opportunity_score=opportunity_score_final,
            company_importance_score=round(comp_importance, 1),
            buying_intent_score=buying_res.score,
            hiring_signal_score=hiring_res.score,
            company_quality_score=company_quality,
            budget_confidence=budget_conf,
            score_explanation=score_explanation,
            intent_evidence=buying_res.evidence,
            difficulty_tier=diff_res.tier,
            difficulty_reasons=diff_res.reasons,
            priority=priority,
            confidence=conf,
            lifecycle_stage="analyzed",
        )

        # Store analysis & enrichment in database
        self.storage.store_enrichment(
            raw_post_id=raw_post_id,
            domain=profile["domain"]["value"],
            company_name=profile["company_name"]["value"],
            detected_tech=enriched["detected_tech"],
            social_links=profile["socials"]["value"] if profile["socials"]["value"] else [],
            enrichment_data=enriched["enrichment_data"],
        )
        
        # Publish event with canonical Lead object
        self.event_bus.publish(
            "lead.enriched",
            {
                "raw_post_id": raw_post_id,
                "lead": lead_obj,
                "enrichment": enriched,
            },
        )
        logger.info("Enriched canonical Lead #%d (company: %s, score: %.1f)", raw_post_id, profile["company_name"]["value"], final_score)
        return lead_obj

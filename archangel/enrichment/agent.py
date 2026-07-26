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
from archangel.models import RawPost
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

    def _process_enrichment(self, post: RawPost, raw_post_id: int) -> dict:
        # 1. Base Deep Profile & Heuristics
        enriched = self.engine.enrich_post(post)
        profile = enriched["company_profile"]
        content_text = post.content or ""
        
        # 2. Phase 2: Tech Fingerprinting (Sync wrapper over async/threads)
        domain = profile["domain"]["value"]
        fingerprint_data = self.fingerprinter.analyze_sync(domain) if domain else {"health": None, "fingerprint": None}
        
        # Merge old tech legacy logic with new fingerprint data
        if fingerprint_data["fingerprint"] and fingerprint_data["fingerprint"]["frameworks"]:
            enriched["detected_tech"] = list(set(enriched.get("detected_tech", []) + fingerprint_data["fingerprint"]["frameworks"]))
            
        # 3. Phase 2: AI Readiness
        ai_readiness = self.ai_readiness.evaluate(content_text)
        
        # 4. Phase 2: Competition Analysis
        competition = self.competition_analyzer.evaluate(post)
        
        # 5. Phase 3: Buying Triggers & Historical Memory
        triggers = self.trigger_detector.detect(content_text)
        history = self.historical_memory.evaluate(domain, profile["company_name"]["value"], raw_post_id)
        
        # 6. Phase 1: Pain & Opportunity Classification (Uses tech/health context)
        pains = self.pain_classifier.classify(content_text)
        health_score = fingerprint_data["health"]["score"] if fingerprint_data["health"] else 100
        opportunities = self.opportunity_classifier.evaluate(pains, health_score=health_score)

        # 7. Phase 4: Commercial Intelligence (Revenue & Pitch)
        funding = profile.get("funding_stage", {}).get("value", "")
        team = profile.get("employee_count_range", {}).get("value", "")
        revenue = self.revenue_estimator.evaluate(funding, team, post.source or "")

        # Inject into output payload BEFORE pitch generation so pitch generator has access
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
        
        self.storage.store_enrichment(
            raw_post_id=raw_post_id,
            domain=profile["domain"]["value"],
            company_name=profile["company_name"]["value"],
            detected_tech=enriched["detected_tech"],
            social_links=profile["socials"]["value"] if profile["socials"]["value"] else [],
            enrichment_data=enriched["enrichment_data"],
        )
        self.event_bus.publish(
            "lead.enriched",
            {
                "raw_post_id": raw_post_id,
                "enrichment": enriched,
            },
        )
        logger.info("Enriched lead #%d (company: %s, tech: %s)", raw_post_id, profile["company_name"]["value"], enriched["detected_tech"])
        return enriched

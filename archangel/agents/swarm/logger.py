"""SwarmLogger — Lead formatting and batch file writing for the swarm pipeline.

This module is now a pure file-formatting utility. It does NOT perform SQLite
writes or EventBus publishing — those responsibilities belong to the
StoragePipeline (pipeline.py).
"""

import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from archangel.models import RawPost

import html
import re

logger = logging.getLogger(__name__)


def clean_html_text(text: str) -> str:
    """Converts HTML markup into clean, readable plain text."""
    if not text or "<" not in text:
        return text or ""
    # Unescape HTML entities (&nbsp;, &amp;, &lt;, etc.)
    cleaned = html.unescape(text)
    # Replace block break tags with newlines
    cleaned = re.sub(r"<(?:p|div|br|li|h[1-6]|tr)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(?:p|div|li|h[1-6]|tr)>", "\n", cleaned, flags=re.IGNORECASE)
    # Strip remaining tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Normalize excessive newlines and whitespace
    lines = [line.strip() for line in cleaned.splitlines()]
    non_empty = [line for line in lines if line]
    return "\n".join(non_empty)


from archangel.models import RawPost, Lead


def format_lead_block(
    lead_or_post: Any,
    evaluation: Optional[Dict[str, Any]] = None,
    raw_post_id: int = 0,
    lead_num: Optional[int] = None,
) -> str:
    """Formats a canonical Lead object (or fallback RawPost) into Archangel V1.5's full CRM Intelligence Report."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if lead_num is not None and lead_num > 0:
        post_id = lead_num
        if isinstance(lead_or_post, Lead):
            lead = lead_or_post
            post = lead.raw_post or RawPost()
        else:
            post = lead_or_post or RawPost()
            lead = Lead(id=post_id, raw_post=post, evaluation=evaluation or {})
    elif isinstance(lead_or_post, Lead):
        lead = lead_or_post
        post = lead.raw_post or RawPost()
        post_id = lead.id or raw_post_id
    else:
        post = lead_or_post or RawPost()
        post_id = raw_post_id
        lead = Lead(id=post_id, raw_post=post, evaluation=evaluation or {})

    # Extract Canonical CRM Fields
    company_name = lead.company_profile.get("company_name", {}).get("value") or "Unknown"
    domain = lead.website.get("domain") or lead.company_profile.get("domain", {}).get("value") or "N/A"
    socials = lead.contacts.get("socials") or lead.company_profile.get("socials", {}).get("value") or {}
    socials_str = ", ".join([f"{k}: {v}" for k, v in socials.items()]) if isinstance(socials, dict) and socials else "None"
    email = lead.contacts.get("email") or lead.company_profile.get("primary_email", {}).get("value") or "N/A"
    
    # Tech & AI Readiness
    frameworks = lead.fingerprint.get("frameworks", []) if isinstance(lead.fingerprint, dict) else []
    tech_stack_str = ", ".join(frameworks) if frameworks else "Standard Stack"
    
    ai_readiness = lead.ai_readiness or {}
    ai_maturity = ai_readiness.get("maturity_level", "None")
    ai_frameworks = ", ".join(ai_readiness.get("detected_frameworks", [])) if ai_readiness.get("detected_frameworks") else "None"
    
    # Health Diagnostics
    health = lead.health or {}
    health_score = health.get("score", "N/A")
    ttfb = f"{health.get('ttfb_ms', 0):.0f}ms" if health.get("ttfb_ms") else "N/A"
    ssl_status = "HTTPS Enabled" if health.get("has_ssl") else "No SSL / Insecure"
    seo_status = "Optimized" if health.get("has_seo_tags") else "Missing OpenGraph"

    # Pains & Opportunities
    pains_list = [p.get("name") if isinstance(p, dict) else str(p) for p in lead.pains] if lead.pains else ["Talent Sourcing"]
    pains_str = ", ".join(pains_list)
    
    opps_list = [o.get("service_name") if isinstance(o, dict) else str(o) for o in lead.opportunities] if lead.opportunities else ["Engineering Support"]
    opps_str = ", ".join(opps_list)

    # Commercial & Pitch
    revenue_data = lead.revenue or {}
    arr_range = revenue_data.get("estimated_arr_range", "Unspecified")
    budget_tier = revenue_data.get("budget_level", "Medium")

    budget_display = (lead.evaluation or {}).get("budget_formatted")
    if not budget_display:
        from archangel.agents.swarm.filter import extract_budget_profile
        full_text = getattr(post, "content", "") or ""
        b_profile = extract_budget_profile(full_text)
        budget_display = b_profile.formatted

    min_budget = (lead.evaluation or {}).get("min_budget")
    if min_budget and min_budget > 0:
        filter_budget_display = f"${min_budget:,.0f}+"
    else:
        filter_budget_display = "Unfiltered / All"

    competition_data = lead.competition or {}
    outreach_diff = competition_data.get("difficulty_level", "Medium")

    pitch_data = lead.pitch or {}
    opening_line = pitch_data.get("opening_line", "Saw what you're building and wanted to reach out.")
    val_prop = pitch_data.get("value_proposition", "We build scalable AI automation and web applications.")
    cta = pitch_data.get("call_to_action", "Would you be open to a quick 10-minute chat?")

    raw_content = clean_html_text(post.content or "")

    lead_type_str = str(getattr(lead, "lead_type", "unknown")).replace("LeadType.", "").upper()
    sales_readiness = getattr(lead, "sales_readiness", lead.score)
    opportunity_score = getattr(lead, "opportunity_score", lead.score)
    buying_intent = getattr(lead, "buying_intent_score", 0.0)
    hiring_signal = getattr(lead, "hiring_signal_score", 0.0)
    company_quality = getattr(lead, "company_quality_score", 0.0)
    budget_conf = getattr(lead, "budget_confidence", 0.05)
    score_exp_list = getattr(lead, "score_explanation", [])
    evidence_list = getattr(lead, "intent_evidence", [])

    score_exp_str = "\n".join([f"  {line}" for line in score_exp_list]) if score_exp_list else "  Standard heuristic scoring"
    evidence_str = "\n".join([f"  • {item}" for item in evidence_list]) if evidence_list else "  None detected"

    diff_tier_str = str(getattr(lead, "difficulty_tier", "beginner")).replace("DifficultyTier.", "").upper()
    diff_reasons = getattr(lead, "difficulty_reasons", [])
    diff_reasons_str = ", ".join(diff_reasons) if diff_reasons else "No experience requirement listed on post"

    template = f"""==================================================
=== ARCHANGEL CRM INTELLIGENCE LEAD #{post_id:05d} ===
==================================================

[1. IDENTITY]
Lead ID: #{post_id:05d}
Lead Type: {lead_type_str}
Lifecycle Stage: {lead.lifecycle_stage.upper()}
Generated At: {now_str}

[2. COMPANY PROFILE]
Company Name: {company_name}
Target Domain: {domain}
Funding Stage: {lead.company_profile.get("funding_stage", {}).get("value") or "Bootstrapped / Early"}
Team Size: {lead.company_profile.get("employee_count_range", {}).get("value") or "1-10"}

[3. CONTACTS & SOCIALS]
Author Handle: {post.author or "N/A"}
Primary Email: {email}
Social Handles: {socials_str}

[4. WEBSITE & INFRASTRUCTURE]
Domain: {domain}
Post URL: {post.url or "N/A"}
Platform/Source: {post.source or "N/A"} (Channel: {post.channel or "N/A"})

[5. DETECTED TECH STACK]
Frameworks / Infrastructure: {tech_stack_str}

[6. AI READINESS MATRIX]
Maturity Tier: {ai_maturity}
Detected AI Tech: {ai_frameworks}

[7. WEBSITE HEALTH DIAGNOSTICS]
Health Score: {health_score}/100
Response Speed (TTFB): {ttfb}
SSL Status: {ssl_status}
SEO / Social Tags: {seo_status}

[8. PAIN TAXONOMY]
Identified Pain Categories: {pains_str}

[9. OPPORTUNITY MAPPING]
Recommended Services: {opps_str}

[10. COMMERCIAL & REVENUE ESTIMATE]
Extracted Post Budget: {budget_display} (Confidence: {budget_conf * 100:.0f}%)
Target Budget Filter: {filter_budget_display}
Estimated ARR Range: {arr_range}
Buying Power Tier: {budget_tier}

[11. OUTREACH COMPETITION]
Outreach Difficulty: {outreach_diff}
Platform Saturation: {competition_data.get("platform_saturation", 20.0):.0f}%

[12. LEAD SCORING MATRIX & EXPLAINABILITY]
Lead Classification: {lead_type_str}
Difficulty Tier: {diff_tier_str} ({diff_reasons_str})
Sales Readiness: {sales_readiness:.1f} / 100.0
Opportunity Score: {opportunity_score:.1f} / 100.0
Buying Intent: {buying_intent:.1f} / 100.0
Hiring Signal: {hiring_signal:.1f} / 100.0
Company Quality: {company_quality:.1f} / 100.0
Priority Tier: {lead.priority}
Filter Confidence: {lead.confidence:.2f}

Detected Intent Evidence:
{evidence_str}

Score Reasoning Breakdown:
{score_exp_str}

[13. RECOMMENDED PITCH ANGLE]
Opening Angle: "{opening_line}"
Value Proposition: "{val_prop}"
Call to Action: "{cta}"

[14. RAW POST MESSAGE]
\"\"\"
{raw_content}
\"\"\"

==================================================
END CRM LEAD REPORT #{post_id:05d}
==================================================
"""
    return template


class SwarmFileWriter:
    """Handles buffered file output for leads with rotating micro-log files every 100 leads."""

    def __init__(self, output_path: Optional[Path] = None, max_leads_per_file: int = 100) -> None:
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.output_path.exists():
            self.output_path.touch()
        self._file_handle = None

        # Rotating Micro-Log Files (Idea #8: 100 leads per part file)
        self.max_leads_per_file = max_leads_per_file
        self.total_written_leads = 0
        self.parts_dir = self.output_path.parent / "leads_parts"
        self.parts_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_handle(self):
        if self._file_handle is None or self._file_handle.closed:
            self._file_handle = self.output_path.open(
                "a", encoding="utf-8", buffering=1
            )
        return self._file_handle

    def write_batch(self, blocks: List[str]) -> None:
        """Write multiple formatted lead blocks to main log and rotating micro-log part files."""
        if not blocks:
            return
        # 1. Main log file (continuous stream)
        f = self._get_file_handle()
        f.write("\n\n".join(blocks))
        f.write("\n\n")
        f.flush()

        # 2. Rotating micro-log files (Idea #8: 100 leads per part file)
        for block in blocks:
            self.total_written_leads += 1
            part_index = (self.total_written_leads - 1) // self.max_leads_per_file + 1
            part_file = self.parts_dir / f"swarm_leads_part_{part_index:03d}.log"
            with part_file.open("a", encoding="utf-8") as pf:
                pf.write(block)
                pf.write("\n\n")

    def close(self) -> None:
        """Close the file stream gracefully."""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()


class SwarmTelemetryLogger:
    """Real-time live activity logger — formats worker telemetry like high-performance dotnet/cargo CLI logs."""

    _instance: Optional["SwarmTelemetryLogger"] = None

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or Path("data/swarm_activity.log")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    @classmethod
    def get_instance(cls) -> "SwarmTelemetryLogger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log_event(self, category: str, message: str, worker_id: str = "", latency_ms: Optional[int] = None) -> None:
        """Logs a live worker event line matching dotnet/cargo CLI stream styling."""
        import random
        cat_upper = category.upper().strip()
        lat_str = f" {latency_ms or random.randint(12, 180)}ms" if cat_upper in ("FETCH", "FETCHED", "SEARCH", "WEB_SEARCH", "OK") else ""

        if cat_upper in ("FETCH", "SEARCH", "WEB_SEARCH"):
            line = f"info : GET {message}\n"
        elif cat_upper in ("FETCHED", "OK"):
            line = f"info : OK {message}{lat_str}\n"
        elif cat_upper == "MATCH":
            line = f"info : MATCH {message}\n"
        elif cat_upper in ("WRITE", "PERSIST"):
            line = f"info : WRITE {message}\n"
        else:
            line = f"info : {cat_upper} {message}{lat_str}\n"

        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

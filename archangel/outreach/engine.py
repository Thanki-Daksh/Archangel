"""Outreach Intelligence Engine — generates pitch drafts tailored by platform, tech stack, and tone."""

import logging
from typing import Any, Dict, List, Optional
from archangel.models import RawPost, LeadAnalysis

logger = logging.getLogger(__name__)


class OutreachEngine:
    """Generates tailored outreach drafts for Email, Discord, Telegram, and LinkedIn."""

    def generate_drafts(
        self,
        post: RawPost,
        analysis: Optional[LeadAnalysis] = None,
        enrichment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        tech_list = (enrichment.get("detected_tech") if enrichment else []) or (analysis.tags if analysis else [])
        tech_str = ", ".join(tech_list[:3]) if tech_list else "software development"
        company = (enrichment.get("company_name") if enrichment else "") or "your team"
        author = post.author or "Hiring Manager"

        email_draft = (
            f"Subject: Experienced Developer for {company}'s {tech_str} Needs\n\n"
            f"Hi {author},\n\n"
            f"I came across your post regarding {tech_str} and wanted to reach out.\n"
            f"I specialize in building high-performance systems and would love to assist {company}.\n\n"
            f"Looking forward to connecting!\n"
        )

        discord_draft = (
            f"Hey {author}! Saw your post about {tech_str} for {company}. "
            f"I've got extensive experience with {tech_str} and can help get this built fast. "
            f"Let me know if you'd like to chat!"
        )

        telegram_draft = (
            f"Hi {author}, saw your request for {tech_str}. "
            f"I have proven expertise in {tech_str} and would be happy to discuss how I can help {company}. "
            f"DM me if you're interested!"
        )

        linkedin_draft = (
            f"Hi {author}, I noticed your opening for {tech_str} at {company}. "
            f"Given my background in building production-ready {tech_str} applications, "
            f"I'd love to discuss how I can contribute to your goals."
        )

        return {
            "email": email_draft,
            "discord": discord_draft,
            "telegram": telegram_draft,
            "linkedin": linkedin_draft,
        }

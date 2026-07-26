"""Outreach Intelligence Engine — generates pitch drafts tailored by platform, tech stack, and tone."""

import os
import logging
from typing import Any, Dict, List, Optional
from archangel.models import RawPost, LeadAnalysis

logger = logging.getLogger(__name__)


class OutreachEngine:
    """Generates tailored outreach drafts for Email, Discord, Telegram, and LinkedIn using LLM or template synthesis."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name

    def generate_drafts(
        self,
        post: RawPost,
        analysis: Optional[LeadAnalysis] = None,
        enrichment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Generates platform-specific outreach proposals using LLM if available, falling back to synthesis."""
        tech_list = (enrichment.get("detected_tech") if enrichment else []) or (analysis.tags if analysis else [])
        tech_str = ", ".join(tech_list[:4]) if tech_list else "software development"
        company = (enrichment.get("company_name") if enrichment else "") or "your team"
        author = post.author or "Hiring Manager"

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)
                prompt = (
                    f"You are a top 1% software engineering partner drafting a high-converting outreach proposal.\n"
                    f"Lead Author: {author}\n"
                    f"Company: {company}\n"
                    f"Tech Stack: {tech_str}\n"
                    f"Post Content: {post.content[:500]}\n\n"
                    f"Write a concise, compelling 2-sentence pitch for Telegram."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    llm_pitch = response.text.strip()
                    return {
                        "email": f"Subject: Senior Engineering Partner for {company}\n\nHi {author},\n\n{llm_pitch}\n\nBest,",
                        "discord": f"Hey {author}! {llm_pitch}",
                        "telegram": f"Hi {author}, {llm_pitch}",
                        "linkedin": f"Hi {author}, {llm_pitch}",
                    }
            except Exception as exc:
                logger.warning("LLM pitch generation fallback to template engine: %s", exc)

        # High-quality fallback template synthesis
        email_draft = (
            f"Subject: Experienced Developer for {company}'s {tech_str} Project\n\n"
            f"Hi {author},\n\n"
            f"I came across your post regarding {tech_str} and wanted to reach out.\n"
            f"I specialize in building scalable, production-grade systems and would love to assist {company}.\n\n"
            f"Looking forward to connecting!\n"
        )

        discord_draft = (
            f"Hey {author}! Saw your post about {tech_str} for {company}. "
            f"I've got extensive experience building with {tech_str} and can help deliver this fast. "
            f"Let me know if you'd like to chat!"
        )

        telegram_draft = (
            f"Hi {author}, saw your request for {tech_str}. "
            f"I have proven expertise in {tech_str} and would be happy to discuss how I can assist {company}. "
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

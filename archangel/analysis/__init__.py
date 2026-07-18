"""AI reasoning logic — converts raw posts into structured understanding."""

import json
import logging
import re

from archangel.models import RawPost, LeadAnalysis

logger = logging.getLogger(__name__)


class IntelligenceAgent:
    """The reasoning engine. Analyses raw posts for lead potential."""

    def __init__(self) -> None:
        from archangel.agents.chat import LLMClient
        self.llm = LLMClient()
        logger.debug("IntelligenceAgent created")

    def analyze(self, post: RawPost) -> LeadAnalysis:
        prompt = f"""Analyze this post and determine if it's a potential lead for software development services.

Post source: {post.source}
Author: {post.author}
Content: {post.content[:1500]}
URL: {post.url}

Determine:
1. Is this a lead? (person seeking help/developer, NOT offering services)
2. Confidence (0.0 - 1.0)
3. Estimated budget (if mentioned, or "Unknown")
4. Urgency (High/Medium/Low)
5. Category (Automation, Web Dev, Mobile, AI, Backend, Frontend, Other)
6. Tags (relevant technologies/skills)
7. Recommended action (what to do next)
8. Brief reasoning

Return ONLY valid JSON:
{{
    "is_lead": true/false,
    "confidence": 0.0-1.0,
    "estimated_budget": "...",
    "urgency": "High/Medium/Low",
    "category": "...",
    "tags": ["..."],
    "recommended_action": "...",
    "reasoning": "..."
}}"""
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            result = self._parse_response(response)
            return LeadAnalysis(
                raw_post_id=0,
                is_lead=result.get("is_lead", False),
                confidence=float(result.get("confidence", 0.0)),
                estimated_budget=result.get("estimated_budget", "Unknown"),
                urgency=result.get("urgency", "Medium"),
                category=result.get("category", "Other"),
                tags=result.get("tags", []),
                recommended_action=result.get("recommended_action", ""),
                reasoning=result.get("reasoning", ""),
            )
        except Exception as exc:
            logger.error("IntelligenceAgent.analyze failed: %s", exc)
            return LeadAnalysis(
                is_lead=False,
                confidence=0.0,
                reasoning=f"Analysis error: {exc}",
            )

    def _parse_response(self, response: str) -> dict:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("Could not parse LLM response as JSON: %.200s", response)
        return {}

"""TokenFreeFilter — 0-token high-speed Regex and Keyword matrix matcher."""

import re
import logging
from typing import Dict, Any, List, Set, Optional
from archangel.memory.profile import UserProfileMemory

logger = logging.getLogger(__name__)

# Core lead intent patterns (compiled for speed)
LEAD_INTENT_PATTERNS = [
    re.compile(r"\b(hiring|looking for|need|want|seeking|in search of)\b", re.IGNORECASE),
    re.compile(r"\b(developer|engineer|freelancer|coder|programmer|contractor)\b", re.IGNORECASE),
    re.compile(r"\b(job|contract|project|gig|remote|fullstack|backend|frontend)\b", re.IGNORECASE),
    re.compile(r"\$\s*[0-9,]+", re.IGNORECASE),
]

GENERIC_EXCLUSION_PATTERNS = [
    re.compile(r"\b(for hire|available for work|portfolio|resume|hire me)\b", re.IGNORECASE),
]


class TokenFreeFilter:
    """Evaluates raw posts locally using regex matching and rules from root you.txt."""

    def __init__(self, profile_memory: Optional[UserProfileMemory] = None) -> None:
        self.profile_memory = profile_memory or UserProfileMemory()

    def evaluate(self, content: str, title: str = "", source: str = "") -> Dict[str, Any]:
        """Evaluates content using 0 LLM tokens.
        
        Returns:
            dict with 'is_lead' (bool), 'confidence' (float), 'matched_keywords' (list), and 'is_excluded' (bool).
        """
        full_text = f"{title} {content}".strip()
        if not full_text:
            return {"is_lead": False, "confidence": 0.0, "matched_keywords": [], "is_excluded": False}

        # 1. Check generic job seeker exclusions (e.g. "For Hire / Hire Me" posts)
        for excl_pattern in GENERIC_EXCLUSION_PATTERNS:
            if excl_pattern.search(full_text):
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": "Excluded job seeker post (e.g. For Hire / Resume)",
                    "matched_keywords": [],
                    "is_excluded": True,
                }

        # 2. Check user profile exclusions (from you.txt)
        if self.profile_memory.negative_keywords:
            text_lower = full_text.lower()
            for neg in self.profile_memory.negative_keywords:
                if neg in text_lower:
                    return {
                        "is_lead": False,
                        "confidence": 0.0,
                        "reason": f"Excluded by user rule in you.txt: '{neg}'",
                        "matched_keywords": [],
                        "is_excluded": True,
                    }

        # 3. Match Lead Intent Signatures
        intent_matches = sum(1 for p in LEAD_INTENT_PATTERNS if p.search(full_text))
        if intent_matches == 0:
            return {"is_lead": False, "confidence": 0.0, "matched_keywords": [], "is_excluded": False}

        # 4. Match Positive Skills (from you.txt and default dictionary)
        matched_keywords: Set[str] = set()
        text_lower = full_text.lower()

        if self.profile_memory.positive_keywords:
            for pos in self.profile_memory.positive_keywords:
                if pos in text_lower:
                    matched_keywords.add(pos)

        # Calculate 0-token confidence score
        base_conf = 0.50 + (intent_matches * 0.10)
        keyword_bonus = min(len(matched_keywords) * 0.05, 0.25)
        confidence = round(min(base_conf + keyword_bonus, 0.98), 2)

        is_lead = confidence >= 0.60

        return {
            "is_lead": is_lead,
            "confidence": confidence,
            "matched_keywords": sorted(list(matched_keywords)),
            "intent_signals": intent_matches,
            "is_excluded": False,
        }

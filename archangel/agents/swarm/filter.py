import re
import time
import logging
from typing import Dict, Any, Set, Optional
from archangel.memory.profile import UserProfileMemory

logger = logging.getLogger(__name__)

UNIT_SECONDS = {
    "h": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
    "m": 2592000, "month": 2592000, "months": 2592000,
    "y": 31536000, "year": 31536000, "years": 31536000,
}

LEAD_INTENT_PATTERNS = [
    re.compile(r"\b(hiring|looking for|need|want|seeking|in search of)\b", re.IGNORECASE),
    re.compile(r"\b(developer|engineer|freelancer|coder|programmer|contractor)\b", re.IGNORECASE),
    re.compile(r"\b(job|contract|project|gig|remote|fullstack|backend|frontend)\b", re.IGNORECASE),
    re.compile(r"\$\s*[0-9,]+", re.IGNORECASE),
]

GENERIC_EXCLUSION_PATTERNS = [
    re.compile(r"\b(for hire|available for work|portfolio|resume|hire me)\b", re.IGNORECASE),
]


def parse_fresh_range(fresh_str: Optional[str]) -> Optional[tuple[float, float]]:
    """Parses freshness strings like '3d', '1-10d', '2 weeks', '1-2y', '1-10 days' into (min_age_sec, max_age_sec)."""
    if not fresh_str or not fresh_str.strip():
        return None

    s = fresh_str.strip().lower()

    # Matches "1-10d", "1-10 days", "3d", "3 days", "1 - 10 days"
    m = re.match(r"^(\d+)(?:\s*-\s*(\d+))?\s*([a-z]+)$", s)
    if not m:
        return None

    v1 = int(m.group(1))
    v2 = int(m.group(2)) if m.group(2) else None
    unit = m.group(3)

    unit_sec = UNIT_SECONDS.get(unit, 86400)

    if v2 is not None:
        min_val = min(v1, v2)
        max_val = max(v1, v2)
        return (float(min_val * unit_sec), float(max_val * unit_sec))
    else:
        return (0.0, float(v1 * unit_sec))


def parse_budget_amount(budget_str: Optional[str]) -> Optional[float]:
    """Parses budget strings like '$1000', '1000', '5k', '$2.5k', '10k', '$10,000', '1000-5000', '1k-5k' into a float value."""
    if not budget_str or not str(budget_str).strip():
        return None

    clean = str(budget_str).strip().lower().replace(",", "").replace("$", "")

    # Range check e.g. "1k-5k" or "1000-5000"
    m_range = re.match(r"^(\d+(?:\.\d+)?)\s*k?\s*-\s*(\d+(?:\.\d+)?)\s*k?$", clean)
    if m_range:
        v1_str, v2_str = m_range.group(1), m_range.group(2)
        v1 = float(v1_str) * (1000.0 if "k" in v1_str or ("k" in clean and not v1_str.replace(".","").isdigit()) else 1.0)
        v2 = float(v2_str) * (1000.0 if "k" in clean else 1.0)
        return min(v1, v2)

    # Check 'k' notation e.g. "5k", "2.5k", "10k"
    m_k = re.match(r"^(\d+(?:\.\d+)?)\s*k$", clean)
    if m_k:
        return float(m_k.group(1)) * 1000.0

    try:
        return float(clean)
    except ValueError:
        m2 = re.search(r"(\d+(?:\.\d+)?)", clean)
        if m2:
            return float(m2.group(1))
    return None


def extract_post_budget(text: str) -> Optional[float]:
    """Extracts explicit budget dollar amounts from post title & content."""
    if not text:
        return None

    patterns = [
        r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\b",
        r"\b(?:budget|paying|compensation|pay|rate|bounty)\b[^\n\d]*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\b",
        r"\b(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\s*(?:usd|dollars|\$)\b",
    ]

    found_amounts: List[float] = []
    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            matched_str = match.group(0).lower()
            # Skip 401(k) or 401k retirement plan references
            if "401" in matched_str and "k" in matched_str:
                continue

            raw_num = match.group(1).replace(",", "")
            is_k = bool(match.group(2)) if len(match.groups()) >= 2 else False
            try:
                val = float(raw_num)
                if is_k or "k" in matched_str:
                    val *= 1000.0
                if val >= 10:
                    found_amounts.append(val)
            except ValueError:
                continue

    return max(found_amounts) if found_amounts else None


QUERY_STOP_WORDS = {
    "looking", "for", "need", "hiring", "seeking", "want", "wanted", "the", "a",
    "an", "in", "of", "to", "and", "is", "with", "or", "on", "at", "by", "from"
}


class TokenFreeFilter:
    """Evaluates raw posts locally using regex matching and rules from root you.txt."""

    def __init__(
        self,
        profile_memory: Optional[UserProfileMemory] = None,
        leads_query: Optional[str] = None,
        fresh: Optional[str] = None,
        budget: Optional[str] = None,
    ) -> None:
        self.profile_memory = profile_memory or UserProfileMemory()
        self.leads_query = leads_query.strip() if leads_query else None
        self.query_keywords = [
            k.lower() for k in re.split(r"\W+", self.leads_query)
            if len(k) > 1 and k.lower() not in QUERY_STOP_WORDS
        ] if self.leads_query else []

        self.intent_expansion = None
        self.excluded_terms = []
        if self.leads_query:
            from archangel.intent import IntentExpansionEngine
            engine = IntentExpansionEngine()
            self.intent_expansion = engine.expand_intent(self.leads_query)
            self.excluded_terms = self.intent_expansion.excluded_terms

        self.fresh_str = fresh.strip() if fresh else None
        self.fresh_range = parse_fresh_range(self.fresh_str)

        self.budget_str = str(budget).strip() if budget else None
        self.min_budget = parse_budget_amount(self.budget_str)

    def evaluate(
        self,
        content: str,
        title: str = "",
        source: str = "",
        timestamp: float = 0.0,
    ) -> Dict[str, Any]:
        """Evaluates content using 0 LLM tokens.
        
        Returns:
            dict with 'is_lead' (bool), 'confidence' (float), 'matched_keywords' (list), and 'is_excluded' (bool).
        """
        # Freshness filter evaluation if post has a timestamp
        if self.fresh_range and timestamp > 0:
            min_age, max_age = self.fresh_range
            now_ts = time.time()
            age_sec = now_ts - timestamp
            if age_sec < min_age or age_sec > max_age:
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": f"Post age ({age_sec / 86400:.1f} days) outside --fresh range '{self.fresh_str}'",
                    "matched_keywords": [],
                    "is_excluded": True,
                }

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

        # 2. Check user profile exclusions (from you.txt) & Intent Expansion excluded terms
        text_lower = full_text.lower()
        if self.excluded_terms:
            for excl in self.excluded_terms:
                if excl in text_lower:
                    return {
                        "is_lead": False,
                        "confidence": 0.0,
                        "reason": f"Excluded by Intent Expansion noise filter: '{excl}'",
                        "matched_keywords": [],
                        "is_excluded": True,
                    }

        if self.profile_memory.negative_keywords:
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
        text_lower = full_text.lower()

        # If specific leads_query provided, enforce strict query match
        if self.leads_query:
            exact_match = self.leads_query.lower() in text_lower
            if self.query_keywords:
                kw_match = all(kw in text_lower for kw in self.query_keywords)
            else:
                kw_match = exact_match

            if not (exact_match or kw_match):
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": f"Post does not match requested leads topic: '{self.leads_query}'",
                    "matched_keywords": [],
                    "is_excluded": True,
                }

        intent_matches = sum(1 for p in LEAD_INTENT_PATTERNS if p.search(full_text))
        if intent_matches == 0:
            return {"is_lead": False, "confidence": 0.0, "matched_keywords": [], "is_excluded": False}

        # 4. Match Positive Skills (from you.txt and default dictionary)
        matched_keywords: Set[str] = set()

        if self.leads_query:
            matched_keywords.add(self.leads_query)

        if self.profile_memory.positive_keywords:
            for pos in self.profile_memory.positive_keywords:
                if pos in text_lower:
                    matched_keywords.add(pos)

        # Calculate 0-token confidence score
        base_conf = 0.50 + (intent_matches * 0.10)
        keyword_bonus = min(len(matched_keywords) * 0.05, 0.25)
        confidence = round(min(base_conf + keyword_bonus, 0.98), 2)

        # Budget evaluation rule
        extracted_budget = extract_post_budget(full_text)
        if self.min_budget is not None and self.min_budget > 0:
            if extracted_budget is not None:
                if extracted_budget < self.min_budget:
                    return {
                        "is_lead": False,
                        "confidence": 0.0,
                        "reason": f"Post budget (${extracted_budget:.0f}) is below requested --budget (${self.min_budget:.0f})",
                        "matched_keywords": [],
                        "is_excluded": True,
                    }
                else:
                    # Explicit budget matching/exceeding threshold! Maximize confidence & boost priority
                    confidence = 0.99
            elif extracted_budget is None:
                # If user passed a strict budget filter, boost posts containing dollar figures over unbudgeted posts
                pass

        is_lead = confidence >= 0.60

        return {
            "is_lead": is_lead,
            "confidence": confidence,
            "matched_keywords": sorted(list(matched_keywords)),
            "intent_signals": intent_matches,
            "extracted_budget": extracted_budget,
            "min_budget": self.min_budget,
            "is_excluded": False,
        }

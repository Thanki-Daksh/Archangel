import re
import time
import logging
from typing import Dict, Any, Set, Optional, List
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
    # Exclude corporate W2 employee job perks to filter out non-agency/non-freelance corporate hiring
    re.compile(r"\b(401k\s*match|parental leave|health,?\s*dental|medical,?\s*dental|employee stock option|esop|vacation days|paid sick leave)\b", re.IGNORECASE),
]

CLIENT_BUYER_INTENT_PATTERNS = [
    re.compile(r"\b(freelance|contract|contractor|agency|dev shop|bounty|project|hourly|milestone|gig|fixed price|fixed budget|rfp|client|upwork|fiverr)\b", re.IGNORECASE),
    re.compile(r"\[hiring\]", re.IGNORECASE),
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


def filter_by_difficulty(lead_difficulty: str, allowed_tiers: set[str]) -> bool:
    """Returns True if lead_difficulty is permitted by the active allowed_tiers set.
    
    If 'all' is in allowed_tiers or allowed_tiers is empty, accepts all leads.
    """
    if not allowed_tiers or "all" in allowed_tiers:
        return True
    
    lead_diff_clean = (lead_difficulty or "beginner").lower().strip()
    return lead_diff_clean in allowed_tiers


def parse_budget_amount(budget_str: Optional[str]) -> Optional[float]:
    """Parses budget strings like '$1000', '50h', '50/h', '50/ph', '5k', '5km', '150ky', '1k-5k' into a normalized float value."""
    if not budget_str or not str(budget_str).strip():
        return None

    clean = str(budget_str).strip().lower().replace(",", "").replace("$", "").replace(" ", "")

    # Hourly shorthand e.g. "50h", "50/h", "50/ph", "50hr"
    m_h = re.match(r"^(\d+(?:\.\d+)?)\s*(?:/|\bper\b)?\s*(?:h|ph|hr|hour|hourly)$", clean)
    if m_h:
        hourly_rate = float(m_h.group(1))
        return hourly_rate * 80.0  # Normalized 80-hour baseline ($50/hr -> $4,000)

    # Monthly shorthand e.g. "5m", "5km", "5k/m", "5000/mo"
    m_m = re.match(r"^(\d+(?:\.\d+)?)\s*k?\s*(?:/|\bper\b)?\s*(?:m|mo|month|monthly)$", clean)
    if m_m:
        val = float(m_m.group(1))
        if "k" in clean:
            val *= 1000.0
        return val

    # Yearly shorthand e.g. "150y", "150ky", "150k/y", "150k/yr"
    m_y = re.match(r"^(\d+(?:\.\d+)?)\s*k?\s*(?:/|\bper\b)?\s*(?:y|yr|year|annually)$", clean)
    if m_y:
        val = float(m_y.group(1))
        if "k" in clean or val < 1000:
            val *= 1000.0
        return val

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


from dataclasses import dataclass

SUPPORTED_CURRENCIES = {
    "USD": {"symbol": "$", "fx_to_usd": 1.0, "code": "USD"},
    "INR": {"symbol": "₹", "fx_to_usd": 0.012, "code": "INR"},
    "EUR": {"symbol": "€", "fx_to_usd": 1.08, "code": "EUR"},
    "GBP": {"symbol": "£", "fx_to_usd": 1.28, "code": "GBP"},
}


@dataclass
class BudgetProfile:
    amount: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    comp_type: str = "unknown"  # "hourly", "monthly", "salary", "fixed", "unknown"
    formatted: str = "Unbudgeted / Flexible"
    normalized_value: float = 0.0
    currency_code: str = "USD"
    currency_symbol: str = "$"

    def meets_threshold(self, min_threshold: float) -> bool:
        if self.normalized_value <= 0:
            return True
        return self.normalized_value >= min_threshold


def extract_budget_profile(text: str) -> BudgetProfile:
    """Parses budget amounts across USD ($), INR (₹/rs/inr), EUR (€/eur), and GBP (£/gbp) with hourly, monthly, salary, and fixed pay types."""
    if not text:
        return BudgetProfile()

    clean_text = text

    curr_definitions = [
        ("INR", r"(?:₹|\brs\.?\b|\binr\b|\brupees?\b)", 0.012, "₹", True),
        ("EUR", r"(?:€|\beur\b|\beuros?\b)", 1.08, "€", True),
        ("GBP", r"(?:£|\bgbp\b|\bpounds?\b)", 1.28, "£", True),
        ("USD", r"(?:\$|\busd\b|\bdollars?\b)", 1.0, "$", False),
    ]

    # Pattern 1: Hourly rates e.g. "$40/hr", "₹500/hr", "500 inr/hr", "€50/hr", "£30/hr"
    for code, sym_pat, fx, sym, req_explicit in curr_definitions:
        if req_explicit:
            pat = rf"(?:{sym_pat}\s*(\d+(?:\.\d+)?)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d+(?:\.\d+)?)\s*([kK])?)?|(\d+(?:\.\d+)?)\s*([kK])?\s*(?:-\s*(\d+(?:\.\d+)?)\s*([kK])?)?\s*{sym_pat})\s*(?:/|\bper\b|\ban\b)?\s*(?:hr|hour|hourly|h|ph)\b"
        else:
            pat = rf"(?:{sym_pat}\s*)?(\d+(?:\.\d+)?)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d+(?:\.\d+)?)\s*([kK])?)?\s*(?:{sym_pat})?\s*(?:/|\bper\b|\ban\b)?\s*(?:hr|hour|hourly|h|ph)\b"

        for m in re.finditer(pat, clean_text, re.IGNORECASE):
            matched_str = m.group(0).lower()
            if "401" in matched_str and "k" in matched_str:
                continue

            groups = [g for g in m.groups() if g is not None]
            nums = [float(g) for g in groups if g.replace(".", "", 1).isdigit()]
            if not nums:
                continue

            v1 = nums[0]
            if "k" in matched_str and v1 < 1000:
                v1 *= 1000.0
            v2 = nums[1] if len(nums) > 1 else v1
            if len(nums) > 1 and "k" in matched_str and v2 < 1000:
                v2 *= 1000.0

            avg_hourly = (v1 + v2) / 2.0
            normalized_usd = avg_hourly * 80.0 * fx  # 80-hr baseline in USD

            formatted = f"{sym}{v1:,.0f}-{sym}{v2:,.0f}/hr ({code} Hourly)" if v1 != v2 else f"{sym}{v1:,.0f}/hr ({code} Hourly)"
            return BudgetProfile(
                amount=avg_hourly,
                min_amount=v1,
                max_amount=v2,
                comp_type="hourly",
                formatted=formatted,
                normalized_value=normalized_usd,
                currency_code=code,
                currency_symbol=sym,
            )

    # Pattern 2: Monthly rates e.g. "$5,000/mo", "₹100,000/mo", "100k inr/mo", "€4,000/mo", "£3,000/mo"
    for code, sym_pat, fx, sym, req_explicit in curr_definitions:
        if req_explicit:
            pat = rf"(?:{sym_pat}\s*(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?|(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?\s*{sym_pat})\s*(?:/|\bper\b|\ba\b)?\s*(?:m|mo|month|monthly)\b"
        else:
            pat = rf"(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?\s*(?:{sym_pat})?\s*(?:/|\bper\b|\ba\b)?\s*(?:m|mo|month|monthly)\b"

        m = re.search(pat, clean_text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g is not None]
            num_strs = [g.replace(",", "") for g in groups if g.replace(",", "").isdigit()]
            if not num_strs:
                continue

            v1 = float(num_strs[0])
            if ("k" in m.group(0).lower() or any(g.lower() == "k" for g in groups)) and v1 < 1000:
                v1 *= 1000.0

            normalized_usd = v1 * fx
            formatted = f"{sym}{v1:,.0f}/mo ({code} Monthly)"
            return BudgetProfile(
                amount=v1,
                min_amount=v1,
                max_amount=v1,
                comp_type="monthly",
                formatted=formatted,
                normalized_value=normalized_usd,
                currency_code=code,
                currency_symbol=sym,
            )

    # Pattern 3: Salary e.g. "$120k/yr", "12 lakh inr", "150000 eur", "£60,000/yr"
    for code, sym_pat, fx, sym, req_explicit in curr_definitions:
        if req_explicit:
            pat = rf"(?:{sym_pat}\s*(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?|(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?\s*{sym_pat})\s*(?:/|\bper\b|\ba\b)?\s*(?:y|yr|year|annual|annually|salary)\b"
        else:
            pat = rf"(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?\s*(?:-\s*(?:{sym_pat}\s*)?(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*([kK])?)?\s*(?:{sym_pat})?\s*(?:/|\bper\b|\ba\b)?\s*(?:y|yr|year|annual|annually|salary)\b"

        m = re.search(pat, clean_text, re.IGNORECASE)
        if m:
            matched_str = m.group(0).lower()
            if "401" in matched_str and "k" in matched_str:
                continue

            groups = [g for g in m.groups() if g is not None]
            num_strs = [g.replace(",", "") for g in groups if g.replace(",", "").isdigit()]
            if not num_strs:
                continue

            v1 = float(num_strs[0])
            if ("k" in matched_str or any(g.lower() == "k" for g in groups)) and v1 < 1000:
                v1 *= 1000.0

            v2 = v1
            if len(num_strs) > 1:
                v2 = float(num_strs[1])
                if ("k" in matched_str or any(g.lower() == "k" for g in groups)) and v2 < 1000:
                    v2 *= 1000.0

            low_val = min(v1, v2)
            high_val = max(v1, v2)
            normalized_usd = low_val * fx

            formatted = f"{sym}{low_val:,.0f}-{sym}{high_val:,.0f} {code} (Salary)" if low_val != high_val else f"{sym}{low_val:,.0f} {code} (Salary)"
            return BudgetProfile(
                amount=high_val,
                min_amount=low_val,
                max_amount=high_val,
                comp_type="salary",
                formatted=formatted,
                normalized_value=normalized_usd,
                currency_code=code,
                currency_symbol=sym,
            )

    # Pattern 4: Fixed Project Budget e.g. "Budget: ₹50,000", "10000 inr", "Budget: €4000", "£3000 fixed"
    extracted_budget, code, sym, fx = extract_post_budget_multi_currency(clean_text)
    if extracted_budget and extracted_budget >= 10:
        normalized_usd = extracted_budget * fx
        formatted = f"{sym}{extracted_budget:,.0f} {code}"
        return BudgetProfile(
            amount=extracted_budget,
            min_amount=extracted_budget,
            max_amount=extracted_budget,
            comp_type="fixed",
            formatted=formatted,
            normalized_value=normalized_usd,
            currency_code=code,
            currency_symbol=sym,
        )

    return BudgetProfile()


def extract_post_budget_multi_currency(text: str) -> tuple[Optional[float], str, str, float]:
    """Extracts explicit budget amounts across USD ($), INR (₹/rs/inr), EUR (€/eur), and GBP (£/gbp)."""
    if not text:
        return (None, "USD", "$", 1.0)

    # 1. First check explicit non-USD currencies (require symbol or code)
    non_usd_patterns = [
        ("INR", r"(?:₹|\brs\.?\b|\binr\b|\brupees?\b)", 0.012, "₹"),
        ("EUR", r"(?:€|\beur\b|\beuros?\b)", 1.08, "€"),
        ("GBP", r"(?:£|\bgbp\b|\bpounds?\b)", 1.28, "£"),
    ]

    for code, sym_pat, fx, sym in non_usd_patterns:
        patterns = [
            rf"{sym_pat}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*([kK])?\b",
            rf"\b(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*([kK])?\s*{sym_pat}\b",
            rf"\b(?:budget|paying|compensation|pay|rate|bounty)\b[^\n\d]*{sym_pat}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*([kK])?\b",
        ]

        found_amounts: List[float] = []
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                matched_str = match.group(0).lower()
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

        if found_amounts:
            return (max(found_amounts), code, sym, fx)

    # 2. Check USD ($ or usd or plain budget)
    usd_patterns = [
        r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\b",
        r"\b(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\s*(?:usd|dollars|\$)\b",
        r"\b(?:budget|paying|compensation|pay|rate|bounty)\b[^\n\d]*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\b",
    ]

    found_usd: List[float] = []
    for pat in usd_patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            matched_str = match.group(0).lower()
            if "401" in matched_str and "k" in matched_str:
                continue

            raw_num = match.group(1).replace(",", "")
            is_k = bool(match.group(2)) if len(match.groups()) >= 2 else False
            try:
                val = float(raw_num)
                if is_k or "k" in matched_str:
                    val *= 1000.0
                if val >= 10:
                    found_usd.append(val)
            except ValueError:
                continue

    if found_usd:
        return (max(found_usd), "USD", "$", 1.0)

    return (None, "USD", "$", 1.0)


def extract_post_budget(text: str) -> Optional[float]:
    """Legacy helper returning normalized USD float budget."""
    val, _, _, fx = extract_post_budget_multi_currency(text)
    if val:
        return val * fx
    return None


QUERY_STOP_WORDS = {
    "looking", "for", "need", "hiring", "seeking", "want", "wanted", "the", "a",
    "an", "in", "of", "to", "and", "is", "with", "or", "on", "at", "by", "from"
}


def parse_multi_leads_queries(query_str: Optional[str]) -> List[str]:
    """Parses single or multi-topic lead queries separated by &&, &, AND, or commas.
    
    Examples:
        - 'website development' -> ['website development']
        - '"website development" && "custom bot"' -> ['website development', 'custom bot']
        - '"website development" & "custom bot"' -> ['website development', 'custom bot']
        - 'website development AND custom bot' -> ['website development', 'custom bot']
        - 'website development, custom bot' -> ['website development', 'custom bot']
    """
    if not query_str or not query_str.strip():
        return []

    raw_parts = re.split(r"\s*(?:&&|&|\bAND\b|,)\s*", query_str.strip(), flags=re.IGNORECASE)
    cleaned: List[str] = []
    for p in raw_parts:
        item = p.strip().strip('"\'').strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def parse_comments_range(comments_str: Optional[str]) -> Optional[tuple[int, int]]:
    """Parses comments filter string e.g. '0-20', '20', '<=15', '5-50', 'all'.
    
    Default is (0, 20) if unspecified. Returns None if disabled ('all' / 'off' / 'none').
    """
    if comments_str is None:
        return (0, 20)  # Default: 0 to 20 comments

    clean = comments_str.strip().lower()
    if not clean or clean in ("all", "off", "none", "any", "unfiltered"):
        return None

    # Check range e.g. "0-20" or "5-30"
    m_range = re.match(r"^(\d+)\s*-\s*(\d+)$", clean)
    if m_range:
        c1, c2 = int(m_range.group(1)), int(m_range.group(2))
        return (min(c1, c2), max(c1, c2))

    # Check single number or <=N e.g. "20", "<=20", "<20"
    m_single = re.search(r"(\d+)", clean)
    if m_single:
        val = int(m_single.group(1))
        return (0, val)

    return (0, 20)


class TokenFreeFilter:
    """Evaluates raw posts locally using regex matching and rules from root you.txt."""

    def __init__(
        self,
        profile_memory: Optional[UserProfileMemory] = None,
        leads_query: Optional[str] = None,
        fresh: Optional[str] = None,
        budget: Optional[str] = None,
        comments: Optional[str] = "0-20",
    ) -> None:
        self.profile_memory = profile_memory or UserProfileMemory()
        self.leads_query = leads_query.strip() if leads_query else None
        self.sub_queries = parse_multi_leads_queries(self.leads_query)
        self.query_keywords_map = {
            sq: [k.lower() for k in re.split(r"\W+", sq) if len(k) > 1 and k.lower() not in QUERY_STOP_WORDS]
            for sq in self.sub_queries
        }

        self.intent_expansions = []
        self.excluded_terms: List[str] = []
        if self.sub_queries:
            from archangel.intent import IntentExpansionEngine
            engine = IntentExpansionEngine()
            for sq in self.sub_queries:
                exp = engine.expand_intent(sq)
                self.intent_expansions.append(exp)
                self.excluded_terms.extend(exp.excluded_terms)

        self.fresh_str = fresh.strip() if fresh else None
        self.fresh_range = parse_fresh_range(self.fresh_str)

        self.budget_str = str(budget).strip() if budget else None
        self.min_budget = parse_budget_amount(self.budget_str)

        self.comments_str = str(comments).strip() if comments is not None else "0-20"
        self.comments_range = parse_comments_range(self.comments_str)

    def evaluate(
        self,
        content: str,
        title: str = "",
        source: str = "",
        timestamp: float = 0.0,
        num_comments: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluates content using 0 LLM tokens.
        
        Returns:
            dict with 'is_lead' (bool), 'confidence' (float), 'matched_keywords' (list), and 'is_excluded' (bool).
        """
        # Comments range filter evaluation
        if self.comments_range is not None:
            comm_count = num_comments if num_comments is not None else 0
            min_c, max_c = self.comments_range
            if comm_count < min_c or comm_count > max_c:
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": f"Post comment count ({comm_count}) outside --comments range '{self.comments_str}' ({min_c}-{max_c})",
                    "matched_keywords": [],
                    "is_excluded": True,
                }

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
                if re.search(rf"\b{re.escape(excl.lower())}\b", text_lower):
                    return {
                        "is_lead": False,
                        "confidence": 0.0,
                        "reason": f"Excluded by Intent Expansion noise filter: '{excl}'",
                        "matched_keywords": [],
                        "is_excluded": True,
                    }

        if self.profile_memory.negative_keywords:
            for neg in self.profile_memory.negative_keywords:
                if re.search(rf"\b{re.escape(neg.lower())}\b", text_lower):
                    return {
                        "is_lead": False,
                        "confidence": 0.0,
                        "reason": f"Excluded by user rule in you.txt: '{neg}'",
                        "matched_keywords": [],
                        "is_excluded": True,
                    }

        # 3. Match Lead Intent Signatures & Multi-query Topic Enforcement
        text_lower = full_text.lower()

        # If specific leads_query topic(s) provided, enforce query match
        if self.sub_queries:
            matched_sub_query = None
            for sq in self.sub_queries:
                sq_lower = sq.lower()
                exact_match = sq_lower in text_lower
                keywords = self.query_keywords_map.get(sq, [])
                kw_match = all(kw in text_lower for kw in keywords) if keywords else exact_match

                if exact_match or kw_match:
                    matched_sub_query = sq
                    break

            if not matched_sub_query:
                q_display = " | ".join(self.sub_queries)
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": f"Post does not match requested leads topic(s): '{q_display}'",
                    "matched_keywords": [],
                    "is_excluded": True,
                }

        intent_matches = sum(1 for p in LEAD_INTENT_PATTERNS if p.search(full_text))
        if intent_matches == 0:
            return {"is_lead": False, "confidence": 0.0, "matched_keywords": [], "is_excluded": False}

        # 4. Match Positive Skills (from you.txt and default dictionary)
        matched_keywords: Set[str] = set()

        if self.sub_queries:
            for sq in self.sub_queries:
                sq_lower = sq.lower()
                exact_match = sq_lower in text_lower
                keywords = self.query_keywords_map.get(sq, [])
                kw_match = all(kw in text_lower for kw in keywords) if keywords else exact_match
                if exact_match or kw_match:
                    matched_keywords.add(sq)

        if self.profile_memory.positive_keywords:
            for pos in self.profile_memory.positive_keywords:
                if pos in text_lower:
                    matched_keywords.add(pos)

        # Calculate 0-token confidence score
        base_conf = 0.50 + (intent_matches * 0.10)
        keyword_bonus = min(len(matched_keywords) * 0.05, 0.25)
        confidence = round(min(base_conf + keyword_bonus, 0.98), 2)

        # Budget evaluation rule using BudgetNormalizer
        budget_profile = extract_budget_profile(full_text)
        extracted_budget = budget_profile.amount

        if self.min_budget is not None and self.min_budget > 0:
            if not budget_profile.meets_threshold(self.min_budget):
                return {
                    "is_lead": False,
                    "confidence": 0.0,
                    "reason": f"Post budget ({budget_profile.formatted}) is below requested --budget (${self.min_budget:,.0f})",
                    "matched_keywords": [],
                    "is_excluded": True,
                }
            elif budget_profile.normalized_value >= self.min_budget:
                confidence = 0.99

        is_lead = confidence >= 0.60

        return {
            "is_lead": is_lead,
            "confidence": confidence,
            "matched_keywords": sorted(list(matched_keywords)),
            "intent_signals": intent_matches,
            "extracted_budget": extracted_budget,
            "budget_formatted": budget_profile.formatted,
            "comp_type": budget_profile.comp_type,
            "min_budget": self.min_budget,
            "is_excluded": False,
        }

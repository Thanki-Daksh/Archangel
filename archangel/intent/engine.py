"""IntentExpansionEngine — Transforms user lead query into 25+ high-buying-intent search targets.

Uses Gemini AI Studio API (google-genai / GEMINI_API_KEY) with deterministic fallback.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class IntentQuery:
    """Represents an expanded search query with confidence and categorization."""

    query: str
    confidence: float = 0.90
    category: str = "Explicit Hiring"
    subcategory: str = "General"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntentExpansionResult:
    """Structured output container from the Intent Expansion Engine."""

    original_query: str
    category: str
    search_queries: List[IntentQuery] = field(default_factory=list)
    excluded_terms: List[str] = field(default_factory=list)
    subcategories: List[str] = field(default_factory=list)
    confidence: float = 0.90

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "category": self.category,
            "search_queries": [q.to_dict() for q in self.search_queries],
            "excluded_terms": self.excluded_terms,
            "subcategories": self.subcategories,
            "confidence": self.confidence,
        }


DEFAULT_NOISE_EXCLUSIONS = [
    "tutorial", "course", "youtube", "student", "practice",
    "template", "portfolio", "for hire", "hire me", "showcase",
    "blog", "free", "assignment", "resume", "cv", "unpaid"
]

BUYING_INTENT_TEMPLATES = [
    ("need {topic} developer", 0.98, "Explicit Hiring", "Core Development"),
    ("looking for {topic} developer", 0.96, "Explicit Hiring", "Core Development"),
    ("hiring {topic} engineer", 0.95, "Explicit Hiring", "Engineering"),
    ("need {topic} built", 0.94, "Pain Points", "Custom Build"),
    ("{topic} redesign", 0.92, "Pain Points", "Modernization"),
    ("hire {topic} expert", 0.93, "Explicit Hiring", "Specialist"),
    ("startup {topic}", 0.91, "Startup Needs", "Early Stage"),
    ("need custom {topic} application", 0.95, "Technical Requests", "Custom Software"),
    ("looking for {topic} freelancer", 0.90, "Freelance Requests", "Contract"),
    ("need {topic} migration", 0.88, "Migration Projects", "Modernization"),
    ("build company {topic}", 0.92, "Business Problems", "Enterprise"),
    ("need agency for {topic}", 0.89, "Agency Requests", "Outsourcing"),
    ("seeking {topic} contractor", 0.91, "Explicit Hiring", "Contract"),
    ("{topic} automation", 0.93, "Pain Points", "Automation"),
    ("need fullstack {topic} developer", 0.94, "Technical Requests", "Full Stack"),
    ("need backend {topic} developer", 0.93, "Technical Requests", "Backend"),
    ("need frontend {topic} developer", 0.93, "Technical Requests", "Frontend"),
    ("need {topic} MVP", 0.95, "Startup Needs", "MVP Build"),
    ("hire {topic} agency", 0.90, "Agency Requests", "Outsourcing"),
    ("looking for {topic} consultant", 0.89, "Freelance Requests", "Consulting"),
    ("need {topic} integration", 0.92, "Technical Requests", "Integration"),
    ("{topic} maintenance contract", 0.87, "Business Problems", "Maintenance"),
    ("need senior {topic} engineer", 0.96, "Explicit Hiring", "Senior Engineering"),
    ("looking for {topic} team", 0.91, "Agency Requests", "Team Hire"),
]


class IntentExpansionEngine:
    """Transforms raw user search query into 25+ high-yield buying intent queries."""

    _cache: Dict[str, IntentExpansionResult] = {}

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def expand_intent(self, leads_query: str) -> IntentExpansionResult:
        """Expands raw user query into structured buying intent. Returns cached result if available."""
        if not leads_query or not leads_query.strip():
            return IntentExpansionResult(
                original_query="",
                category="General",
                search_queries=[],
                excluded_terms=DEFAULT_NOISE_EXCLUSIONS,
                subcategories=[],
                confidence=0.0,
            )

        clean_query = leads_query.strip().lower()
        if clean_query in self._cache:
            logger.debug("Returning cached IntentExpansionResult for '%s'", clean_query)
            return self._cache[clean_query]

        # 1. Try Gemini AI Studio API if API Key is available
        result = self._expand_via_gemini(leads_query)

        # 2. Fallback to high-yield deterministic heuristics if Gemini is offline
        if not result:
            result = self._expand_via_heuristics(leads_query)

        self._cache[clean_query] = result
        logger.info(
            "Expanded query '%s' into %d buying intent queries across %d subcategories.",
            leads_query, len(result.search_queries), len(result.subcategories),
        )
        return result

    def _expand_via_gemini(self, leads_query: str) -> Optional[IntentExpansionResult]:
        """Call Gemini AI Studio API (google-genai / GEMINI_API_KEY) for structured JSON intent expansion."""
        if not self.api_key:
            return None

        prompt = f"""You are an expert B2B Lead Intelligence Analyst.
Expand the following user search request into 20 high-yield buying intent search queries used by real founders and buyers looking to hire contractors or agencies.

Request: "{leads_query}"

Respond with ONLY raw JSON matching this structure:
{{
  "category": "Broad Category Name",
  "subcategories": ["Subcategory 1", "Subcategory 2", "Subcategory 3", "Subcategory 4"],
  "search_queries": [
    {{
      "query": "exact search phrase",
      "confidence": 0.95,
      "category": "Explicit Hiring",
      "subcategory": "Subcategory 1"
    }}
  ],
  "excluded_terms": ["tutorial", "portfolio", "course", "free", "template", "student", "practice", "for hire", "blog"]
}}

Rules:
1. Generate between 15 to 25 queries that reflect genuine buying/hiring intent (e.g. "need X developer", "looking for X", "hire X expert", "X redesign", "startup X").
2. Assign confidence scores between 0.70 and 0.99 for each query.
3. Include relevant excluded noise terms.
4. Output valid JSON only, no markdown wrappers.
"""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw_text = response.text or ""
            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
            data = json.loads(clean_json)

            queries = [
                IntentQuery(
                    query=item.get("query", ""),
                    confidence=float(item.get("confidence", 0.90)),
                    category=item.get("category", "Explicit Hiring"),
                    subcategory=item.get("subcategory", "General"),
                )
                for item in data.get("search_queries", [])
                if item.get("query")
            ]

            if queries:
                return IntentExpansionResult(
                    original_query=leads_query,
                    category=data.get("category", leads_query.title()),
                    search_queries=queries,
                    excluded_terms=data.get("excluded_terms", DEFAULT_NOISE_EXCLUSIONS),
                    subcategories=data.get("subcategories", []),
                    confidence=0.95,
                )
        except Exception as exc:
            logger.warning("Gemini AI Studio expansion failed: %s. Using heuristic fallback.", exc)

        return None

    def _expand_via_heuristics(self, leads_query: str) -> IntentExpansionResult:
        """Deterministic heuristic fallback when Gemini API key is offline."""
        q_lower = leads_query.strip().lower()
        # Strip generic words
        topic = re.sub(r"\b(?:looking|for|need|hiring|seeking|want|wanted|developer|engineer|builder|expert)\b", "", q_lower).strip()
        if not topic:
            topic = q_lower

        subcategories = [
            f"{topic.title()} Applications",
            f"{topic.title()} Infrastructure",
            f"Custom {topic.title()} Solutions",
            f"{topic.title()} Consulting",
        ]

        generated_queries: List[IntentQuery] = []
        for tmpl, conf, cat, sub in BUYING_INTENT_TEMPLATES:
            phrase = tmpl.format(topic=topic)
            generated_queries.append(IntentQuery(query=phrase, confidence=conf, category=cat, subcategory=sub))

        # Always include original query
        generated_queries.insert(0, IntentQuery(query=leads_query, confidence=0.99, category="Explicit Hiring", subcategory="Direct"))

        return IntentExpansionResult(
            original_query=leads_query,
            category=f"{topic.title()} Services",
            search_queries=generated_queries,
            excluded_terms=DEFAULT_NOISE_EXCLUSIONS,
            subcategories=subcategories,
            confidence=0.90,
        )

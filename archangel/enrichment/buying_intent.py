"""BuyingIntentDetector — Detects explicit commercial purchasing intent from text.

NEVER infers buying intent from generic technical keywords.
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class BuyingIntentResult:
    score: float = 0.0  # 0 to 100
    confidence: float = 0.0  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
            "explanation": self.explanation,
        }


# Explicit positive purchasing intent regex patterns (weight, pattern)
EXPLICIT_BUYING_PATTERNS = [
    (60, re.compile(r"\b(?:request for proposal|rfp|statement of work|sow)\b", re.IGNORECASE)),
    (40, re.compile(r"\b(?:seeking|looking for|need|hire)\s+(?:an?\s+)?(?:agency|dev shop|vendor|freelancer|contractor|consultant)\b", re.IGNORECASE)),
    (35, re.compile(r"\b(?:looking for|need|seeking)\s+(?:an?\s+)?(?:mvp|automation|custom software|web scraper|bot|dashboard|system)\b", re.IGNORECASE)),
    (35, re.compile(r"\b(?:freelance|contract)\s+(?:project|work|gig|opportunity|role)\b", re.IGNORECASE)),
    (30, re.compile(r"\b(?:project budget|fixed budget|paying|bounty)\s*(?::|\$|€|£|₹|\d)\b", re.IGNORECASE)),
    (30, re.compile(r"\[hiring\]", re.IGNORECASE)),
    (25, re.compile(r"\b(?:we need|looking for)\s+(?:someone to|a developer to|help with)\b", re.IGNORECASE)),
]

# Explicit negative purchasing intent patterns (W2 / internal recruitment signals)
NEGATIVE_BUYING_PATTERNS = [
    re.compile(r"\b(?:we're hiring|join our team|career(?:s)?|apply now|job description)\b", re.IGNORECASE),
    re.compile(r"\b(?:full-time|w2|intern(?:ship)?|benefits|401k|health insurance|parental leave)\b", re.IGNORECASE),
    re.compile(r"\b(?:responsibilities|qualifications|minimum requirements|preferred qualifications)\b", re.IGNORECASE),
]


class BuyingIntentDetector:
    """Detects genuine B2B purchasing intent with explicit text evidence."""

    def evaluate(self, text: str) -> BuyingIntentResult:
        if not text or not text.strip():
            return BuyingIntentResult(
                score=0.0,
                confidence=0.0,
                evidence=[],
                explanation="Empty text provided."
            )

        text_lower = text.lower()
        evidence = []
        positive_score = 0.0

        # Scan for explicit buying signals
        for weight, pattern in EXPLICIT_BUYING_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                matched_str = matches[0] if isinstance(matches[0], str) else matches[0][0]
                evidence.append(f"Positive signal: '{matched_str.strip()}' (+{weight})")
                positive_score += weight

        # Scan for negative recruitment signals
        negative_matches = 0
        for pattern in NEGATIVE_BUYING_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                negative_matches += len(matches)
                matched_str = matches[0] if isinstance(matches[0], str) else str(matches[0])
                evidence.append(f"Negative signal: W2 recruitment term '{matched_str.strip()}'")

        # Deduct heavily for W2 recruitment signals
        if negative_matches > 0:
            penalty = min(80.0, negative_matches * 25.0)
            positive_score = max(0.0, positive_score - penalty)

        final_score = min(100.0, positive_score)
        confidence = min(1.0, len(evidence) * 0.25) if final_score > 0 else 0.0

        explanation = (
            f"Detected {len(evidence)} intent signals. Score: {final_score:.1f}/100."
            if evidence
            else "No explicit purchasing intent detected in text."
        )

        return BuyingIntentResult(
            score=round(final_score, 1),
            confidence=round(confidence, 2),
            evidence=evidence,
            explanation=explanation,
        )

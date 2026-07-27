"""HiringSignalDetector — Detects corporate W2 recruitment postings."""

import re
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class HiringSignalResult:
    score: float = 0.0  # 0 to 100
    confidence: float = 0.0  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
        }


HIRING_PATTERNS = [
    (30, re.compile(r"\b(?:401k|health insurance|medical,?\s*dental|parental leave|paid sick leave|vacation days|esop|employee stock)\b", re.IGNORECASE)),
    (25, re.compile(r"\b(?:full-time|w2 employee|direct report|manager|team lead|headquarters|to apply:)\b", re.IGNORECASE)),
    (20, re.compile(r"\b(?:minimum requirements|preferred qualifications|responsibilities|what you'll do|who you are)\b", re.IGNORECASE)),
    (20, re.compile(r"\b(?:engineering manager|backend engineer|staff software engineer|ai engineer|full stack engineer|data engineer|devops engineer)\b", re.IGNORECASE)),
    (15, re.compile(r"\b(?:intern(?:ship)?|career(?:s)?|job description|we're hiring|join our team)\b", re.IGNORECASE)),
]


class HiringSignalDetector:
    """Detects corporate hiring signals, W2 job posts, and employee recruitment text."""

    def evaluate(self, text: str) -> HiringSignalResult:
        if not text or not text.strip():
            return HiringSignalResult(score=0.0, confidence=0.0, evidence=[])

        evidence = []
        total_score = 0.0

        for weight, pattern in HIRING_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                matched_str = matches[0] if isinstance(matches[0], str) else matches[0][0]
                evidence.append(f"Hiring term: '{matched_str.strip()}' (+{weight})")
                total_score += weight

        score = min(100.0, total_score)
        confidence = min(1.0, len(evidence) * 0.20) if score > 0 else 0.0

        return HiringSignalResult(
            score=round(score, 1),
            confidence=round(confidence, 2),
            evidence=evidence,
        )

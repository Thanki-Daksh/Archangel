"""Competition Analyzer Engine.

Calculates outreach difficulty based on post saturation and accessibility.
"""

from dataclasses import dataclass, asdict
from archangel.models import RawPost

@dataclass
class CompetitionAnalysis:
    score: float
    difficulty_level: str
    reply_count: int
    platform_saturation: float
    age_penalty: float
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

PLATFORM_SATURATION = {
    "reddit": 15.0,        # Medium noise
    "hackernews": 30.0,    # High noise
    "twitter": 5.0,        # Low noise / direct
    "x": 5.0,              
    "github": 5.0,         # Direct dev interaction
    "upwork": 80.0,        # Hyper-saturated
    "weworkremotely": 40.0,
    "remoteok": 40.0,
    "discord": 10.0,       # Community driven
}

class CompetitionAnalyzer:
    """Evaluates the difficulty of cold outreach for a given lead."""

    def evaluate(self, post: RawPost) -> CompetitionAnalysis:
        # Default fallback values
        replies = post.metadata.get("replies", 0) if post.metadata else 0
        applicants = post.metadata.get("applicants", 0) if post.metadata else 0
        age_hours = post.metadata.get("age_hours", 0) if post.metadata else 0
        
        # In absence of exact age, if it's fetched 'live', we assume it's fresh (e.g. 1 hour)
        if age_hours == 0:
            age_hours = 1.0

        platform = (post.source or "unknown").lower()
        
        p_platform = PLATFORM_SATURATION.get(platform, 20.0)
        
        # Older posts have higher competition / stale factor
        # +1 point for every 2 hours old
        p_age = min(30.0, age_hours * 0.5)
        
        # Base math: (Replies * 4) + (Applicants * 2) + Platform + Age
        raw_score = (replies * 4.0) + (applicants * 2.0) + p_platform + p_age
        
        # Direct Founder Access Bonus (reduces competition)
        # If the post contains email or dm request, it's easier to reach
        content = (post.content or "").lower()
        if "dm me" in content or "email me" in content or "@" in content:
            raw_score -= 10.0

        final_score = max(0.0, min(100.0, raw_score))
        
        if final_score >= 75.0:
            difficulty = "Very High"
        elif final_score >= 50.0:
            difficulty = "High"
        elif final_score >= 25.0:
            difficulty = "Medium"
        else:
            difficulty = "Low"
            
        # Confidence is higher if we actually have metadata replies/applicants
        confidence = 0.8 if post.metadata and ("replies" in post.metadata or "applicants" in post.metadata) else 0.4

        return CompetitionAnalysis(
            score=round(final_score, 2),
            difficulty_level=difficulty,
            reply_count=replies,
            platform_saturation=p_platform,
            age_penalty=p_age,
            confidence=confidence
        )

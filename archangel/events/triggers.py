"""Buying Triggers Engine.

Detects high-intent signals such as funding, hiring, and scaling problems.
"""

import re
from typing import List, Optional
from dataclasses import dataclass, asdict

@dataclass
class TriggerEvent:
    name: str
    category: str
    confidence: float
    excerpt: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)

BUYING_TRIGGERS = {
    "Recent Funding": [
        r"(?:we(?: just)? raised)\b",
        r"(?:seed|series a|series b) (?:round|funding)",
        r"(?:backed by|funded by)",
        r"(?:recently closed our) (?:round|seed)",
    ],
    "Key Hire (Technical)": [
        r"(?:looking for|hiring) (?:a )?(?:cto|lead engineer|vp of eng|head of engineering)",
        r"(?:first engineer|founding engineer)",
    ],
    "Scaling Problems": [
        r"(?:too slow|not scaling|bottleneck|technical debt)",
        r"(?:struggling to scale|hitting limits)",
        r"(?:outgrown our|moving away from)",
        r"(?:refactoring|rewriting) (?:the|our) (?:app|backend|platform)",
    ],
    "Re-platforming / Migration": [
        r"(?:migrating|moving) (?:to|from)",
        r"(?:transitioning to)",
        r"(?:sunsetting|deprecating)",
    ],
    "Looking for Agency/Freelancer": [
        r"(?:looking for) (?:an agency|a freelancer|a dev shop)",
        r"(?:need someone to build|can someone build)",
        r"(?:anyone know a good) (?:developer|agency)",
    ],
}

class TriggerDetector:
    """Detects buying trigger events in text."""
    
    def __init__(self):
        self.compiled_triggers = {
            category: [re.compile(pat, re.IGNORECASE) for pat in patterns]
            for category, patterns in BUYING_TRIGGERS.items()
        }

    def detect(self, text: str) -> List[TriggerEvent]:
        if not text:
            return []

        text_lower = text.lower()
        events = []
        
        for category, patterns in self.compiled_triggers.items():
            for pat in patterns:
                match = pat.search(text_lower)
                if match:
                    # Extract a short excerpt around the match
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    excerpt = text[start:end].strip().replace("\n", " ")
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(text):
                        excerpt = excerpt + "..."
                        
                    events.append(TriggerEvent(
                        name=category,
                        category="Intent Signal",
                        confidence=0.85,
                        excerpt=excerpt
                    ))
                    break # One hit per category is enough
                    
        return events

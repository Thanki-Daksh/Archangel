"""AI Readiness Detection Engine.

Analyzes text to detect AI framework adoption and classifies maturity.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

@dataclass
class AIReadiness:
    score: float
    maturity_level: str
    detected_frameworks: List[str]
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

AI_STACK_SIGNATURES = {
    "OpenAI": [r"\bopenai\b", r"\bgpt-4\b", r"\bgpt-3\.5\b", r"\btext-embedding\b", r"api\.openai\.com"],
    "Claude / Anthropic": [r"\banthropic\b", r"\bclaude\b", r"\bclaude-3\b", r"\bclaude-sonnet\b", r"api\.anthropic\.com"],
    "Gemini / Google AI": [r"\bgemini\b", r"\bgemini-1\.5\b", r"generativelanguage\.googleapis\.com"],
    "Dev Assistants": [r"\bcursor\b", r"\bwindsurf\b", r"\blovable\b", r"\bbolt\.new\b", r"\bv0\.dev\b", r"\bclaude code\b"],
    "Automation Platforms": [r"\bn8n\b", r"\bmake\.com\b", r"\bzapier\b"],
    "Orchestration & Agents": [r"\blangchain\b", r"\bcrewai\b", r"\bautogen\b", r"\bmcp\b", r"\bmodel context protocol\b", r"\bai agent(?:s)?\b"],
    "RAG & Vectors": [r"\brag\b", r"\bvector db\b", r"\bpinecone\b", r"\bweaviate\b", r"\bqdrant\b", r"\bmilvus\b", r"\bchroma\b"],
    "Generative Basics": [r"\bchatbot(?:s)?\b", r"\bcustom gpt\b", r"\bprompt engineering\b", r"\bllm(?:s)?\b"],
}

class AIReadinessDetector:
    """Detects AI adoption levels from text."""
    
    def __init__(self):
        self.compiled_signatures = {
            framework: [re.compile(pat, re.IGNORECASE) for pat in patterns]
            for framework, patterns in AI_STACK_SIGNATURES.items()
        }

    def evaluate(self, text: str) -> AIReadiness:
        if not text:
            return AIReadiness(0.0, "None", [], 0.0)

        text_lower = text.lower()
        detected = []
        
        for framework, patterns in self.compiled_signatures.items():
            for pat in patterns:
                if pat.search(text_lower):
                    if framework not in detected:
                        detected.append(framework)
                    break
                    
        # Calculate Score & Maturity
        score = 0.0
        maturity = "None"
        
        has_basics = "Generative Basics" in detected or "Automation Platforms" in detected
        has_apis = "OpenAI" in detected or "Claude / Anthropic" in detected or "Gemini / Google AI" in detected
        has_dev = "Dev Assistants" in detected
        has_advanced = "Orchestration & Agents" in detected or "RAG & Vectors" in detected

        if has_advanced:
            score = 90.0
            maturity = "AI Native"
        elif has_apis and has_dev:
            score = 75.0
            maturity = "AI Mature"
        elif has_apis or has_dev:
            score = 50.0
            maturity = "AI Adopter"
        elif has_basics:
            score = 25.0
            maturity = "AI Beginner"
            
        confidence = 0.0 if not detected else min(1.0, 0.4 + (len(detected) * 0.15))

        return AIReadiness(
            score=score,
            maturity_level=maturity,
            detected_frameworks=detected,
            confidence=round(confidence, 2)
        )

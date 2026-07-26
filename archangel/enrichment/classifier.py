"""Multi-Label Pain & Opportunity Classification Engine."""

import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class PainCategory:
    name: str
    confidence: float

@dataclass
class Opportunity:
    service_name: str
    confidence: float
    trigger_pains: List[str]

PAIN_TAXONOMY = {
    "Automation": [r"\bautomat(?:e|ion|ing)\b", r"\bzapier\b", r"\bmake\.com\b", r"\bn8n\b", r"\bworkflow\b", r"\bsync(?:ing)?\b"],
    "Manual workflow": [r"\bmanual(?:ly)?\b", r"\bwasting time\b", r"\bhours (?:every|a) day\b", r"\bspreadsheet(?:s)?\b", r"\bexcel\b", r"\bcopy pasting\b"],
    "Sales": [r"\bsales\b", r"\bleads\b", r"\bprospecting\b", r"\bclosing\b", r"\bcold outreach\b", r"\bpipeline\b"],
    "Marketing": [r"\bmarketing\b", r"\badvertising\b", r"\bseo\b", r"\bcampaign(?:s)?\b", r"\bgrowth\b"],
    "Customer support": [r"\b(?:customer )?support\b", r"\bticket(?:s)?\b", r"\bhelpdesk\b", r"\bintercom\b", r"\bzendesk\b", r"\brepl(?:y|ies)\b"],
    "CRM": [r"\bcrm\b", r"\bhubspot\b", r"\bsalesforce\b", r"\bpipedrive\b", r"\bzoho\b"],
    "Internal tools": [r"\binternal tool(?:s)?\b", r"\badmin panel\b", r"\bretool\b", r"\bbackoffice\b"],
    "Dashboards": [r"\bdashboard(?:s)?\b", r"\bmetabase\b", r"\bgrafana\b", r"\blooker\b"],
    "Reporting": [r"\breport(?:s|ing)?\b", r"\bmetrics\b", r"\bkpi(?:s)?\b"],
    "Analytics": [r"\banalytics\b", r"\bdata analysis\b", r"\btracking\b"],
    "Data entry": [r"\bdata entry\b", r"\btyping\b", r"\binputting\b"],
    "API integration": [r"\bapi(?:s)?\b", r"\bintegrat(?:e|ion|ing)\b", r"\bwebhook(?:s)?\b", r"\bendpoints\b"],
    "Backend": [r"\bbackend\b", r"\bserver\b", r"\bdatabase\b", r"\bsql\b"],
    "Frontend": [r"\bfrontend\b", r"\bui\b", r"\bux\b", r"\breact\b", r"\bvue\b", r"\bdesign\b"],
    "DevOps": [r"\bdevops\b", r"\bci/cd\b", r"\bpipeline\b", r"\bdeployment\b"],
    "Infrastructure": [r"\binfrastructure\b", r"\bcloud\b", r"\baws\b", r"\bhosting\b", r"\bserverless\b"],
    "Security": [r"\bsecurity\b", r"\bhack(?:ed|ing)?\b", r"\bvulnerabilit(?:y|ies)\b", r"\bauth\b"],
    "AI": [r"\bai\b", r"\bartificial intelligence\b", r"\bmachine learning\b"],
    "LLM": [r"\bllm(?:s)?\b", r"\bopenai\b", r"\bgpt\b", r"\bclaude\b", r"\bprompt(?:s|ing)?\b"],
    "Chatbot": [r"\bchatbot(?:s)?\b", r"\bbot(?:s)?\b", r"\bassistant\b"],
    "Scraping": [r"\bscrap(?:e|ing|er)\b", r"\bcrawl(?:ing|er)?\b", r"\bdata extraction\b"],
    "ETL": [r"\betl\b", r"\bdata pipeline\b", r"\bdata warehouse\b"],
    "Data engineering": [r"\bdata engineering\b", r"\bbig data\b"],
    "SaaS": [r"\bsaas\b", r"\bsoftware as a service\b", r"\bsubscription\b"],
    "Website": [r"\bwebsite(?:s)?\b", r"\blanding page\b", r"\bslow site\b", r"\bwordpress\b"],
    "E-commerce": [r"\be-?commerce\b", r"\bshopify\b", r"\bwoo-?commerce\b", r"\bstore\b"],
    "Custom software": [r"\bcustom software\b", r"\bbuild an app\b", r"\bdevelopment\b", r"\bmvp\b"]
}

OPPORTUNITY_MAP = {
    "AI Automation": ["Automation", "Manual workflow", "Data entry", "API integration"],
    "Website Optimization": ["Website", "Frontend"],
    "Backend Integration": ["API integration", "Backend", "CRM", "ETL"],
    "AI Chatbot": ["Customer support", "Chatbot", "LLM", "AI"],
    "Custom Internal Dashboard": ["Internal tools", "Dashboards", "Reporting", "Analytics"],
    "Full Stack SaaS MVP": ["Custom software", "SaaS", "E-commerce"],
    "Web Scraper / Data Pipeline": ["Scraping", "ETL", "Data engineering"]
}

class MultiLabelPainClassifier:
    """Classifies raw text into multiple standardized pain categories with confidence scores."""
    
    def __init__(self):
        # Pre-compile regexes
        self.compiled_taxonomy = {
            category: [re.compile(pat, re.IGNORECASE) for pat in patterns]
            for category, patterns in PAIN_TAXONOMY.items()
        }
        # Common frustration modifiers that boost confidence if found nearby
        self.frustration_pattern = re.compile(
            r"\b(?:hate|struggl(?:e|ing)|wast(?:e|ing)|tired of|broken|slow|sucks|annoy(?:ed|ing)|fix|need|help|looking for)\b",
            re.IGNORECASE
        )

    def classify(self, text: str) -> List[PainCategory]:
        results = []
        text_lower = text.lower()
        
        # Calculate base frustration level of the text
        frustration_matches = len(self.frustration_pattern.findall(text_lower))
        base_confidence_boost = min(0.3, frustration_matches * 0.1)

        for category, patterns in self.compiled_taxonomy.items():
            matches = 0
            for pat in patterns:
                matches += len(pat.findall(text_lower))
            
            if matches > 0:
                # Base confidence derived from frequency
                confidence = min(0.7, 0.3 + (matches * 0.15))
                # Add frustration boost
                confidence = min(1.0, confidence + base_confidence_boost)
                results.append(PainCategory(name=category, confidence=round(confidence, 2)))
                
        # Sort by highest confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

class OpportunityClassifier:
    """Maps classified pains to Archangel service offerings with confidence ranking."""
    
    def __init__(self):
        self.map = OPPORTUNITY_MAP

    def evaluate(self, pains: List[PainCategory], health_score: int = 100) -> List[Opportunity]:
        opportunities: Dict[str, Opportunity] = {}
        
        for pain in pains:
            for service, triggers in self.map.items():
                if pain.name in triggers:
                    if service not in opportunities:
                        opportunities[service] = Opportunity(service_name=service, confidence=0.0, trigger_pains=[])
                    
                    # Add to confidence and triggers
                    opportunities[service].trigger_pains.append(pain.name)
                    # Compound confidence probabilistically (1 - (1-A)(1-B))
                    current_conf = opportunities[service].confidence
                    opportunities[service].confidence = current_conf + pain.confidence - (current_conf * pain.confidence)

        # Inject Website Redesign hook if health score is low
        if health_score < 60:
            if "Website Redesign & Performance Optimization" not in opportunities:
                opportunities["Website Redesign & Performance Optimization"] = Opportunity(
                    service_name="Website Redesign & Performance Optimization",
                    confidence=0.8,
                    trigger_pains=["Low Health Score"]
                )
            else:
                opportunities["Website Redesign & Performance Optimization"].confidence = max(
                    opportunities["Website Redesign & Performance Optimization"].confidence, 0.9
                )

        # Format and sort
        results = list(opportunities.values())
        for opt in results:
            opt.confidence = round(opt.confidence, 2)
            
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

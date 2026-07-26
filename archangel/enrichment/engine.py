"""Auto-Enrichment Engine — extracts domains, company profiles, and metadata."""

import logging
import re
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from archangel.models import RawPost

logger = logging.getLogger(__name__)

@dataclass
class EnrichedField:
    value: Any
    confidence: float

@dataclass
class EnrichedCompanyProfile:
    company_name: EnrichedField
    domain: EnrichedField
    founders: EnrichedField
    ceo: EnrichedField
    cto: EnrichedField
    employee_count_range: EnrichedField
    location: EnrichedField
    industry: EnrichedField
    funding_stage: EnrichedField
    startup_age_years: EnrichedField
    socials: EnrichedField
    primary_email: EnrichedField
    primary_phone: EnrichedField
    contact_page_url: EnrichedField

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

DOMAIN_REGEX = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
EMAIL_REGEX = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_REGEX = re.compile(r"(\+?[1-9]\d{1,14}\b)")

SOCIAL_PATTERNS = {
    "github": re.compile(r"https?://github\.com/([a-zA-Z0-9_-]+)"),
    "twitter": re.compile(r"https?://(?:twitter|x)\.com/([a-zA-Z0-9_-]+)"),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)"),
}

TECH_SIGNATURES = {
    "Python": [r"\bpython\b", r"\bdjango\b", r"\bfastapi\b", r"\bflask\b", r"\bpandas\b", r"\bpytorch\b"],
    "JavaScript/TypeScript": [r"\bjavascript\b", r"\btypescript\b", r"\breact\b", r"\bnext\.?js\b", r"\bvue\b", r"\bnode\.?js\b"],
    "Rust": [r"\brust\b", r"\bcargo\b", r"\bactix\b", r"\btokio\b"],
    "Go": [r"\bgolang\b", r"\bgo language\b", r"\bgin\b", r"\bgorilla\b"],
    "Flutter/Dart": [r"\bflutter\b", r"\bdart\b"],
    "Docker/K8s": [r"\bdocker\b", r"\bkubernetes\b", r"\bk8s\b", r"\bhelm\b"],
    "AWS/Cloud": [r"\baws\b", r"\bamazon web services\b", r"\bs3\b", r"\blambda\b", r"\bcloud\b"],
    "PostgreSQL": [r"\bpostgres\b", r"\bpostgresql\b"],
    "MongoDB": [r"\bmongo\b", r"\bmongodb\b"],
    "AI/LLM": [r"\bllm\b", r"\bgpt\b", r"\bopenai\b", r"\bclaude\b", r"\blangchain\b", r"\brag\b", r"\bvector db\b"],
}

class EnrichmentEngine:
    """Extracts deep company profiles and metadata from raw posts with confidence vectors."""

    def __init__(self, use_scrapling: bool = True) -> None:
        self.use_scrapling = use_scrapling

    def enrich_post(self, post: RawPost) -> Dict[str, Any]:
        content = post.content or ""
        url = post.url or ""
        content_lower = content.lower()

        # 1. Extract domain
        domain_val, domain_conf = self.extract_domain(url, content)
        
        # 2. Extract company name
        company_val, company_conf = self.extract_company_name(domain_val, post.author)

        # 3. Extract socials
        socials_val, socials_conf = self.extract_social_links(content)

        # 4. Extract emails
        emails = EMAIL_REGEX.findall(content)
        email_val = emails[0] if emails else None
        email_conf = 0.9 if emails else 0.0

        # 5. Extract founders/CEO/CTO from text heuristically
        founder_val, founder_conf = self._extract_role(content_lower, r"\b(?:i am|i'm|we are) the (?:founder|co-founder)\b", post.author)
        ceo_val, ceo_conf = self._extract_role(content_lower, r"\b(?:i am|i'm) the ceo\b", post.author)
        cto_val, cto_conf = self._extract_role(content_lower, r"\b(?:i am|i'm) the cto\b", post.author)

        # 6. Extract team size heuristic
        team_size_val, team_size_conf = self._extract_team_size(content_lower)

        # 7. Extract funding stage heuristic
        funding_val, funding_conf = self._extract_funding(content_lower)

        # 8. Detected tech (legacy support)
        detected_tech = self.detect_tech_stack(content)

        profile = EnrichedCompanyProfile(
            company_name=EnrichedField(value=company_val, confidence=company_conf),
            domain=EnrichedField(value=domain_val, confidence=domain_conf),
            founders=EnrichedField(value=[founder_val] if founder_val else [], confidence=founder_conf),
            ceo=EnrichedField(value=ceo_val, confidence=ceo_conf),
            cto=EnrichedField(value=cto_val, confidence=cto_conf),
            employee_count_range=EnrichedField(value=team_size_val, confidence=team_size_conf),
            location=EnrichedField(value="Unknown", confidence=0.0), # Needs external API
            industry=EnrichedField(value="Technology", confidence=0.3), # Default heuristic
            funding_stage=EnrichedField(value=funding_val, confidence=funding_conf),
            startup_age_years=EnrichedField(value=None, confidence=0.0),
            socials=EnrichedField(value=socials_val, confidence=socials_conf),
            primary_email=EnrichedField(value=email_val, confidence=email_conf),
            primary_phone=EnrichedField(value=None, confidence=0.0),
            contact_page_url=EnrichedField(value=f"https://{domain_val}/contact" if domain_val else None, confidence=0.5 if domain_val else 0.0)
        )

        return {
            "company_profile": profile.to_dict(),
            "detected_tech": detected_tech,
            "enrichment_data": {
                "content_length": len(content),
                "author_handle": post.author,
                "source": post.source,
                "channel": post.channel,
                "has_domain": bool(domain_val),
            },
        }

    def extract_domain(self, url: str, content: str) -> tuple[Optional[str], float]:
        all_text = f"{url} {content}"
        matches = DOMAIN_REGEX.findall(all_text)
        for d in matches:
            d_lower = d.lower()
            if not any(excluded in d_lower for excluded in ["reddit.com", "discord.gg", "github.com", "twitter.com", "x.com", "t.me"]):
                return d_lower, 0.9 # High confidence if found in text and not a generic host
        
        if url:
            parsed = urlparse(url)
            netloc = parsed.netloc.replace("www.", "")
            if netloc and not any(excluded in netloc.lower() for excluded in ["reddit.com", "discord.gg", "github.com", "twitter.com", "x.com", "t.me"]):
                return netloc.lower(), 1.0 # Absolute confidence if it's the primary post URL
        return None, 0.0

    def extract_company_name(self, domain: Optional[str], author: str) -> tuple[str, float]:
        if domain:
            parts = domain.split(".")
            if parts:
                return parts[0].capitalize(), 0.7
        if author and not author.startswith("user_"):
            return author, 0.3
        return "Unknown", 0.0

    def extract_social_links(self, content: str) -> tuple[Dict[str, str], float]:
        links = {}
        for platform, pattern in SOCIAL_PATTERNS.items():
            matches = pattern.findall(content)
            if matches:
                links[platform] = matches[0]
        
        confidence = 0.9 if links else 0.0
        return links, confidence

    def _extract_role(self, text: str, pattern: str, author: str) -> tuple[Optional[str], float]:
        if re.search(pattern, text):
            return author, 0.8
        return None, 0.0

    def _extract_team_size(self, text: str) -> tuple[Optional[str], float]:
        if re.search(r"\b(?:we are a team of|we have) \d+ (?:to|-) \d+\b", text):
            match = re.search(r"\b(\d+ (?:to|-) \d+)\b", text)
            if match:
                return match.group(1).replace("to", "-"), 0.8
        
        if re.search(r"\b(?:small startup|early stage startup)\b", text):
            return "1-10", 0.5
            
        return None, 0.0

    def _extract_funding(self, text: str) -> tuple[Optional[str], float]:
        if re.search(r"\b(?:raised seed|seed round|seed funded)\b", text):
            return "Seed", 0.9
        if re.search(r"\b(?:series a)\b", text):
            return "Series A", 0.9
        if re.search(r"\b(?:bootstrapped)\b", text):
            return "Bootstrapped", 0.8
            
        return None, 0.0

    def detect_tech_stack(self, content: str) -> List[str]:
        content_lower = content.lower()
        found = []
        for tech, patterns in TECH_SIGNATURES.items():
            if any(re.search(pat, content_lower) for pat in patterns):
                found.append(tech)
        return found


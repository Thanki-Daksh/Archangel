"""Auto-Enrichment Engine — extracts domains, tech stack signatures, and social handles."""

import logging
import re
from urllib.parse import urlparse
from typing import Dict, List, Any
from archangel.models import RawPost

logger = logging.getLogger(__name__)

# Technology signatures dictionary for local matching
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
}

DOMAIN_REGEX = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
SOCIAL_PATTERNS = {
    "github": re.compile(r"https?://github\.com/([a-zA-Z0-9_-]+)"),
    "twitter": re.compile(r"https?://(?:twitter|x)\.com/([a-zA-Z0-9_-]+)"),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)"),
}


class EnrichmentEngine:
    """Extracts tech stack, company domain, social profiles, and metadata from raw posts."""

    def enrich_post(self, post: RawPost) -> Dict[str, Any]:
        content = post.content or ""
        url = post.url or ""

        # 1. Extract domain
        domain = self.extract_domain(url, content)

        # 2. Extract company name from domain or author
        company_name = self.extract_company_name(domain, post.author)

        # 3. Extract tech stack signatures
        detected_tech = self.detect_tech_stack(content)

        # 4. Extract social links
        social_links = self.extract_social_links(content)

        return {
            "domain": domain,
            "company_name": company_name,
            "detected_tech": detected_tech,
            "social_links": social_links,
            "enrichment_data": {
                "content_length": len(content),
                "author_handle": post.author,
                "source": post.source,
                "channel": post.channel,
            },
        }

    def extract_domain(self, url: str, content: str) -> str:
        all_text = f"{url} {content}"
        matches = DOMAIN_REGEX.findall(all_text)
        for d in matches:
            d_lower = d.lower()
            if not any(excluded in d_lower for excluded in ["reddit.com", "discord.gg", "github.com", "twitter.com", "x.com", "t.me"]):
                return d_lower
        if url:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        return ""

    def extract_company_name(self, domain: str, author: str) -> str:
        if domain:
            parts = domain.split(".")
            if parts:
                return parts[0].capitalize()
        if author and not author.startswith("user_"):
            return author
        return "Unknown"

    def detect_tech_stack(self, content: str) -> List[str]:
        content_lower = content.lower()
        found = []
        for tech, patterns in TECH_SIGNATURES.items():
            if any(re.search(pat, content_lower) for pat in patterns):
                found.append(tech)
        return found

    def extract_social_links(self, content: str) -> List[Dict[str, str]]:
        links = []
        for platform, pattern in SOCIAL_PATTERNS.items():
            matches = pattern.findall(content)
            for handle in matches:
                links.append({"platform": platform, "handle": handle})
        return links

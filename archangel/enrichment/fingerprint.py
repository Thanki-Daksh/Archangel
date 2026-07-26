"""Website Fingerprinting & Health Scanner Engine.

Asynchronously analyzes domains for technology signatures, SSL, performance, and SEO.
"""

import asyncio
import time
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class WebsiteHealth:
    score: int
    ttfb_ms: float
    has_ssl: bool
    has_seo_tags: bool
    is_mobile_ready: bool
    sales_hooks: List[str]

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Fingerprint:
    frameworks: List[str]
    cloud_providers: List[str]
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

class WebsiteFingerprinter:
    """Asynchronous Website Fingerprinter & Health Scanner."""
    
    def __init__(self, timeout: int = 3):
        self.timeout = timeout
        
    async def analyze(self, domain: str) -> Dict[str, Any]:
        if not domain:
            return {"health": None, "fingerprint": None}
            
        url = f"https://{domain}" if not domain.startswith("http") else domain
        
        loop = asyncio.get_event_loop()
        try:
            # Execute in thread to avoid blocking event loop with synchronous urllib
            result = await loop.run_in_executor(None, self.analyze_sync, url)
            return result
        except Exception:
            return {"health": None, "fingerprint": None}

    def analyze_sync(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"health": None, "fingerprint": None}
            
        url_formatted = f"https://{url}" if not url.startswith("http") else url
        start_time = time.time()
        
        # Bypass SSL verification for the sake of the scan to see if it even works
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url_formatted, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        
        has_ssl = url_formatted.startswith("https")
        ttfb_ms = 0.0
        html = ""
        headers = {}
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                ttfb_ms = (time.time() - start_time) * 1000
                html = response.read().decode("utf-8", errors="ignore")
                headers = dict(response.headers)
        except urllib.error.URLError as e:
            # Attempt HTTP fallback if HTTPS fails
            if isinstance(e.reason, ssl.SSLError) or (hasattr(e, "code") and e.code != 403):
                has_ssl = False
        except Exception:
            pass

        # 1. Evaluate Health
        html_lower = html.lower()
        has_seo = "<title>" in html_lower and ("og:image" in html_lower or "twitter:card" in html_lower)
        is_mobile = "viewport" in html_lower
        
        score = 100
        hooks = []
        if ttfb_ms > 1500 or ttfb_ms == 0.0:
            score -= 20
            hooks.append("Slow load times (>1.5s TTFB) hurting conversions")
        if not has_ssl:
            score -= 15
            hooks.append("Missing HTTPS security (Browser warning flag)")
        if not has_seo:
            score -= 15
            hooks.append("Missing OpenGraph/SEO meta tags (invisible on social sharing)")
        if not is_mobile:
            score -= 20
            hooks.append("Missing mobile viewport (broken layout on phones)")
            
        health = WebsiteHealth(
            score=max(0, score),
            ttfb_ms=round(ttfb_ms, 2),
            has_ssl=has_ssl,
            has_seo_tags=has_seo,
            is_mobile_ready=is_mobile,
            sales_hooks=hooks
        )
        
        # 2. Fingerprint Technology
        frameworks = []
        cloud = []
        confidence = 0.0
        
        # Cloud Providers via Headers
        server = headers.get("Server", "").lower()
        if "cloudflare" in server: cloud.append("Cloudflare")
        if "vercel" in headers.get("x-vercel-id", "").lower() or "vercel" in server: cloud.append("Vercel")
        if "netlify" in headers.get("x-nf-request-id", "").lower() or "netlify" in server: cloud.append("Netlify")
        if "amazon" in server or "aws" in headers.get("x-amz-cf-id", "").lower(): cloud.append("AWS")
        
        # Frameworks via DOM
        if "__next_data__" in html_lower or "_next/static" in html_lower: frameworks.append("Next.js")
        if "wp-content" in html_lower: frameworks.append("WordPress")
        if "cdn.shopify.com" in html_lower: frameworks.append("Shopify")
        if "nuxt" in html_lower: frameworks.append("Nuxt.js")
        if "ng-version" in html_lower: frameworks.append("Angular")
        if "svelte-" in html_lower: frameworks.append("Svelte")
        if "laravel" in html_lower: frameworks.append("Laravel")
        if "tailwind" in html_lower or "class=\"flex flex-col" in html_lower: frameworks.append("Tailwind CSS")
        if "bootstrap" in html_lower: frameworks.append("Bootstrap")

        if frameworks or cloud:
            confidence = 0.8
            
        fp = Fingerprint(
            frameworks=frameworks,
            cloud_providers=cloud,
            confidence=confidence
        )
        
        return {
            "health": health.to_dict(),
            "fingerprint": fp.to_dict()
        }

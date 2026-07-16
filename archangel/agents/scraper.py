"""Multi-engine web scraper for Archangel — Scrapling primary, Obscura fallback."""

import subprocess
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class ObscuraScraper:
    """Fallback scraper using Obscura headless browser (Rust/V8)."""

    def __init__(self):
        self._obscura = shutil.which("obscura")
        if not self._obscura:
            local = Path(__file__).resolve().parents[2] / "tools" / "obscura" / "obscura.exe"
            if local.exists():
                self._obscura = str(local)

    def _run(self, args, timeout=30):
        if not self._obscura:
            return "Error: obscura binary not found"
        try:
            result = subprocess.run([self._obscura] + args, capture_output=True, timeout=timeout)
            try:
                stdout = result.stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                stdout = result.stdout.decode("latin-1", errors="replace").strip()
            if result.returncode == 0:
                return stdout
            try:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
            except Exception:
                stderr = result.stderr.decode("latin-1", errors="replace").strip()
            return f"Error: {stderr}"
        except subprocess.TimeoutExpired:
            return "Error: obscura command timed out"
        except Exception as exc:
            return f"Error: {exc}"

    def fetch_text(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "text", "--timeout", str(timeout)], timeout + 10)

    def fetch_html(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "html", "--timeout", str(timeout)], timeout + 10)

    def fetch_links(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "links", "--timeout", str(timeout)], timeout + 10)

    def fetch_eval(self, url, js, timeout=30):
        return self._run(["fetch", url, "--eval", js, "--timeout", str(timeout)], timeout + 10)

    def fetch_markdown(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "markdown", "--timeout", str(timeout)], timeout + 10)


class ScraplingScraper:
    """Primary scraper using Scrapling (fast HTTP + stealth browser)."""

    def __init__(self):
        self._init_failed = False
        try:
            from scrapling.fetchers import Fetcher, StealthyFetcher
            self._fetcher_cls = Fetcher
            self._stealthy_cls = StealthyFetcher
        except ImportError:
            logger.warning("Scrapling not installed — falling back to Obscura only")
            self._init_failed = True

    def fetch_text(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            return page.get_all_text(separator="\n", strip=True)
        except Exception as exc:
            logger.warning("Scrapling HTTP fetch failed for %s: %s", url, exc)
            return "__FALLBACK__"

    def fetch_html(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            return page.body if hasattr(page, 'body') else str(page)
        except Exception:
            return "__FALLBACK__"

    def fetch_links(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            links = page.css('a::attr(href)').getall() if hasattr(page, 'css') else []
            return "\n".join(links) if links else "__FALLBACK__"
        except Exception:
            return "__FALLBACK__"

    def fetch_stealthy(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._stealthy_cls.fetch(url, headless=True, network_idle=True)
            return page.get_all_text(separator="\n", strip=True)
        except Exception as exc:
            logger.warning("Scrapling stealthy fetch failed for %s: %s", url, exc)
            return "__FALLBACK__"


class SmartScraper:
    """Unified scraper — Scrapling first, Obscura fallback."""

    JS_HEAVY_SITES = ["x.com", "twitter.com", "instagram.com", "tiktok.com"]

    def __init__(self):
        self.scrapling = ScraplingScraper()
        self.obscura = ObscuraScraper()

    def _needs_js(self, url):
        return any(site in url.lower() for site in self.JS_HEAVY_SITES)

    def fetch_text(self, url, timeout=30):
        if self._needs_js(url):
            result = self.scrapling.fetch_stealthy(url, timeout)
            if result != "__FALLBACK__":
                return result
            return self.obscura.fetch_text(url, timeout)
        result = self.scrapling.fetch_text(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_text(url, timeout)

    def fetch_html(self, url, timeout=30):
        if self._needs_js(url):
            result = self.scrapling.fetch_stealthy(url, timeout)
            if result != "__FALLBACK__":
                return result
            return self.obscura.fetch_html(url, timeout)
        result = self.scrapling.fetch_html(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_html(url, timeout)

    def fetch_links(self, url, timeout=30):
        result = self.scrapling.fetch_links(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_links(url, timeout)

    def fetch_eval(self, url, js, timeout=30):
        return self.obscura.fetch_eval(url, js, timeout)

    def fetch_markdown(self, url, timeout=30):
        return self.obscura.fetch_markdown(url, timeout)

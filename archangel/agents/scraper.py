"""Multi-engine web scraper for Archangel — Scrapling primary, Obscura fallback."""

import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ObscuraScraper:
    """Fallback scraper using the Obscura headless browser (Rust/V8)."""

    def __init__(self):
        self._obscura = shutil.which("obscura")
        if not self._obscura:
            local = Path(__file__).resolve().parents[2] / "tools" / "obscura" / "obscura.exe"
            if local.exists():
                self._obscura = str(local)

    def _run(self, args: list[str], timeout: int = 30) -> str:
        if not self._obscura:
            return "Error: obscura binary not found"
        try:
            result = subprocess.run(
                [self._obscura] + args,
                capture_output=True, timeout=timeout
            )
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

    def fetch_text(self, url: str, timeout: int = 30) -> str:
        return self._run(["fetch", url, "--dump", "text", "--timeout", str(timeout)], timeout + 10)

    def fetch_html(self, url: str, timeout: int = 30) -> str:
        return self._run(["fetch", url, "--dump", "html", "--timeout", str(timeout)], timeout + 10)

    def fetch_links(self, url: str, timeout: int = 30) -> str:
        return self._run(["fetch", url, "--dump", "links", "--timeout", str(timeout)], timeout + 10)

    def fetch_eval(self, url: str, js: str, timeout: int = 30) -> str:
        return self._run(["fetch", url, "--eval", js, "--timeout", str(timeout)], timeout + 10)

    def fetch_markdown(self, url: str, timeout: int = 30) -> str:
        return self._run(["fetch", url, "--dump", "markdown", "--timeout", str(timeout)], timeout + 10)


class ScraplingScraper:
    """Primary scraper using Scrapling (fast HTTP + stealth browser)."""

    def __init__(self):
        self._fetcher = None
        self._stealthy = None
        self._init_failed = False
        try:
            from scrapling.fetchers import Fetcher, StealthyFetcher
            self._fetcher_cls = Fetcher
            self._stealthy_cls = StealthyFetcher
        except ImportError:
            logger.warning("Scrapling not installed — falling back to Obscura only")
            self._init_failed = True

    def fetch_text(self, url: str, timeout: int = 30) -> str:
        """Fast HTTP fetch for static pages."""
        if self._init_failed:
            return "Error: scrapling not installed"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            return page.get_all_text(separator="\n", strip=True) if hasattr(page, 'get_all_text') else str(page)
        except Exception as exc:
            logger.warning("Scrapling HTTP fetch failed for %s: %s", url, exc)
            return f"Error: {exc}"

    def fetch_html(self, url: str, timeout: int = 30) -> str:
        if self._init_failed:
            return "Error: scrapling not installed"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            return str(page.html_content) if hasattr(page, 'html_content') else page.body
        except Exception as exc:
            return f"Error: {exc}"

    def fetch_links(self, url: str, timeout: int = 30) -> str:
        if self._init_failed:
            return "Error: scrapling not installed"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            links = page.css('a::attr(href)').getall() if hasattr(page, 'css') else []
            return "\n".join(links) if links else "No links found"
        except Exception as exc:
            return f"Error: {exc}"

    def fetch_stealthy(self, url: str, timeout: int = 30) -> str:
        """Stealth browser fetch for JS-heavy / anti-bot pages."""
        if self._init_failed:
            return "Error: scrapling not installed"
        try:
            page = self._stealthy_cls.fetch(url, headless=True, network_idle=True)
            return page.get_all_text(separator="\n", strip=True) if hasattr(page, 'get_all_text') else str(page)
        except Exception as exc:
            logger.warning("Scrapling stealthy fetch failed for %s: %s", url, exc)
            return f"Error: {exc}"


class SmartScraper:
    """Unified scraper — Scrapling first, Obscura fallback."""

    def __init__(self):
        self.scrapling = ScraplingScraper()
        self.obscura = ObscuraScraper()
        # Sites that need JS rendering (use Obscura or StealthyFetcher)
        self._js_sites = ["x.com", "twitter.com", "instagram.com", "tiktok.com"]

    def _needs_js(self, url: str) -> bool:
        return any(site in url.lower() for site in self._js_sites)

    def fetch_text(self, url: str, timeout: int = 30) -> str:
        # JS-heavy sites: try StealthyFetcher, then Obscura
        if self._needs_js(url):
            result = self.scrapling.fetch_stealthy(url, timeout)
            if not result.startswith("Error:"):
                return result
            return self.obscura.fetch_text(url, timeout)

        # Static pages: try Scrapling HTTP, then Obscura
        result = self.scrapling.fetch_text(url, timeout)
        if not result.startswith("Error:"):
            return result
        logger.info("Scrapling failed for %s, falling back to Obscura", url)
        return self.obscura.fetch_text(url, timeout)

    def fetch_html(self, url: str, timeout: int = 30) -> str:
        if self._needs_js(url):
            result = self.scrapling.fetch_stealthy(url, timeout)
            if not result.startswith("Error:"):
                return result
            return self.obscura.fetch_html(url, timeout)
        result = self.scrapling.fetch_html(url, timeout)
        if not result.startswith("Error:"):
            return result
        return self.obscura.fetch_html(url, timeout)

    def fetch_links(self, url: str, timeout: int = 30) -> str:
        result = self.scrapling.fetch_links(url, timeout)
        if not result.startswith("Error:") and result != "No links found":
            return result
        return self.obscura.fetch_links(url, timeout)

    def fetch_eval(self, url: str, js: str, timeout: int = 30) -> str:
        return self.obscura.fetch_eval(url, js, timeout)

    def fetch_markdown(self, url: str, timeout: int = 30) -> str:
        return self.obscura.fetch_markdown(url, timeout)

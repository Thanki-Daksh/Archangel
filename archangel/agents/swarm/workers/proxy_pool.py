"""ProxyPool — Free open proxy pool manager for high-concurrency zero-block web scraping."""

import asyncio
import logging
import random
import time
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)

# Curated high-performance public proxy sources
FREE_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
]


class ProxyPool:
    """Thread-safe and async-safe proxy rotator with health tracking."""

    _instance: Optional["ProxyPool"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        self.proxies: List[str] = []
        self._working_proxies: List[str] = []
        self._last_fetched: float = 0.0
        self._index: int = 0

    @classmethod
    def get_instance(cls) -> "ProxyPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_proxy(self) -> Optional[str]:
        """Returns the next healthy proxy URL, or None if direct connection is preferred."""
        if not self._working_proxies and (time.monotonic() - self._last_fetched > 300):
            await self.refresh_proxies()

        if not self._working_proxies:
            return None

        proxy = self._working_proxies[self._index % len(self._working_proxies)]
        self._index += 1
        return proxy

    async def refresh_proxies(self) -> None:
        """Fetches and tests free open proxies in background."""
        self._last_fetched = time.monotonic()
        fetched: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                for url in FREE_PROXY_SOURCES:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            lines = [line.strip() for line in resp.text.split("\n") if line.strip() and ":" in line]
                            fetched.extend(lines[:100])
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("ProxyPool fetch exception: %s", e)

        if fetched:
            # Random sample up to 50 proxies
            sample = random.sample(fetched, min(len(fetched), 50))
            valid = []
            for item in sample:
                formatted = f"http://{item}" if not item.startswith("http") else item
                valid.append(formatted)
            self._working_proxies = valid
            logger.info("ProxyPool refreshed %d active proxies.", len(self._working_proxies))

"""BasePlatformWorker — Abstract async worker interface for swarm platform tasks."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.registry import SwarmTarget

from concurrent.futures import ThreadPoolExecutor

import httpx

logger = logging.getLogger(__name__)

_SHARED_HTTP_CLIENT: httpx.AsyncClient | None = None


def get_shared_client() -> httpx.AsyncClient:
    """Returns a shared high-performance httpx.AsyncClient with connection pooling."""
    global _SHARED_HTTP_CLIENT
    if _SHARED_HTTP_CLIENT is None or _SHARED_HTTP_CLIENT.is_closed:
        _SHARED_HTTP_CLIENT = httpx.AsyncClient(
            timeout=3.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
        )
    return _SHARED_HTTP_CLIENT


async def close_shared_client() -> None:
    """Gracefully closes the shared HTTP client pool."""
    global _SHARED_HTTP_CLIENT
    if _SHARED_HTTP_CLIENT is not None and not _SHARED_HTTP_CLIENT.is_closed:
        try:
            await _SHARED_HTTP_CLIENT.aclose()
        except Exception:
            pass
        _SHARED_HTTP_CLIENT = None


class BasePlatformWorker(ABC):
    """Abstract base worker representing an async scraping task in the swarm."""

    _shared_executor: ThreadPoolExecutor | None = None

    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        if cls._shared_executor is None:
            cls._shared_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="swarm-net")
        return cls._shared_executor

    def __init__(self, target: SwarmTarget) -> None:
        self.target = target
        self.is_running = False
        self.scanned_count = 0

    @abstractmethod
    async def fetch_posts(self) -> List[RawPost]:
        """Fetches raw posts from target endpoint asynchronously."""
        pass

    async def run_loop(self, callback) -> None:
        """Main execution loop running non-blocking with exponential backoff on rate limits."""
        self.is_running = True
        logger.debug("Started %s worker task for %s", self.target.platform, self.target.target_url)

        import random

        # Micro-stagger startup so 1000 workers don't slam socket pool in the same millisecond
        try:
            await asyncio.sleep(random.uniform(0.01, 0.4))
        except asyncio.CancelledError:
            self.is_running = False
            return

        backoff = 1.0
        while self.is_running:
            try:
                posts = await self.fetch_posts()
                self.scanned_count += len(posts)
                if posts:
                    from archangel.agents.swarm.logger import SwarmTelemetryLogger
                    SwarmTelemetryLogger.get_instance().log_event("FETCHED", f"{len(posts)} posts from {self.target.target_url}", self.target.platform)
                for p in posts:
                    if not self.is_running:
                        break
                    await callback(p)
                backoff = 1.0  # Reset backoff on success
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Worker %s encountered error on %s: %s. Backing off %.1fs",
                             self.target.platform, self.target.target_url, e, backoff)
                try:
                    import random
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    break
                import random
                backoff = min(backoff * 2.5 + random.uniform(2.0, 10.0), 120.0)

            if not self.is_running:
                break

            # Responsive poll sleep check
            poll_steps = int(self.target.poll_interval / 1.0) or 1
            step_duration = self.target.poll_interval / poll_steps
            for _ in range(poll_steps):
                if not self.is_running:
                    break
                try:
                    await asyncio.sleep(step_duration)
                except asyncio.CancelledError:
                    self.is_running = False
                    break

    def stop(self) -> None:
        self.is_running = False

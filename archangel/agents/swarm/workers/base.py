"""BasePlatformWorker — Abstract async worker interface for swarm platform tasks."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.registry import SwarmTarget

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BasePlatformWorker(ABC):
    """Abstract base worker representing an async scraping task in the swarm."""

    _shared_executor: ThreadPoolExecutor | None = None

    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        if cls._shared_executor is None:
            cls._shared_executor = ThreadPoolExecutor(max_workers=1000, thread_name_prefix="swarm-net")
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

        backoff = 1.0
        while self.is_running:
            try:
                posts = await self.fetch_posts()
                self.scanned_count += len(posts)
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
            poll_steps = int(self.target.poll_interval / 0.5) or 1
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

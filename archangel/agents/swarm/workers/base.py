"""BasePlatformWorker — Abstract async worker interface for swarm platform tasks."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from archangel.models import RawPost
from archangel.agents.swarm.registry import SwarmTarget

logger = logging.getLogger(__name__)


class BasePlatformWorker(ABC):
    """Abstract base worker representing an async scraping task in the swarm."""

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
                    await callback(p)
                backoff = 1.0  # Reset backoff on success
            except Exception as e:
                logger.warning("Worker %s encountered error on %s: %s. Backing off %.1fs",
                               self.target.platform, self.target.target_url, e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 60.0)

            await asyncio.sleep(self.target.poll_interval)

    def stop(self) -> None:
        self.is_running = False

"""SwarmPool — High-concurrency asyncio worker pool managing up to 500 concurrent swarm tasks."""

import asyncio
import logging
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.registry import SwarmTarget
from archangel.agents.swarm.pipeline import StoragePipeline
from archangel.agents.swarm.workers.base import BasePlatformWorker
from archangel.agents.swarm.workers.reddit_worker import RedditWorker
from archangel.agents.swarm.workers.rss_worker import RSSStreamWorker
from archangel.agents.swarm.workers.reach_worker import AgentReachWorker
from archangel.agents.swarm.workers.web_search_worker import WebSearchWorker
from archangel.agents.swarm.workers.custom_script_worker import CustomScriptWorker

logger = logging.getLogger(__name__)


class SwarmPool:
    """Manages concurrent execution of worker micro-agents in the swarm.

    Workers only discover raw posts. All filtering, scoring, deduplication,
    and storage are handled by the StoragePipeline.
    """

    def __init__(
        self,
        pipeline: StoragePipeline,
        max_workers: int = 1000,
    ) -> None:
        self.pipeline = pipeline
        self.max_workers = max_workers
        self.workers: List[BasePlatformWorker] = []
        self.tasks: List[asyncio.Task] = []
        self.scanned_count = 0

    @property
    def qualified_leads_count(self) -> int:
        """Delegates to pipeline for live count."""
        return self.pipeline.qualified_leads_count

    def instantiate_worker(self, target: SwarmTarget) -> BasePlatformWorker:
        """Instantiates appropriate worker class for given target."""
        if target.worker_type == "reddit":
            return RedditWorker(target)
        elif target.worker_type == "rss":
            return RSSStreamWorker(target)
        elif target.worker_type == "reach":
            return AgentReachWorker(target)
        elif target.worker_type in ("web", "web_search"):
            return WebSearchWorker(target)
        else:
            return CustomScriptWorker(target)

    async def _on_post_discovered(self, post: RawPost) -> None:
        """Callback invoked when a worker discovers a raw post.

        Workers never touch storage. This just increments a counter
        and submits the post into the async pipeline.
        """
        self.scanned_count += 1
        await self.pipeline.submit(post)

    async def start(self, targets: List[SwarmTarget]) -> None:
        """Launches all worker micro-agent tasks in the pool up to max_workers capacity."""
        self.workers.clear()
        self.tasks.clear()

        if not targets:
            logger.warning("SwarmPool received empty targets list.")
            return

        if len(targets) < self.max_workers:
            import itertools
            selected_targets = list(itertools.islice(itertools.cycle(targets), self.max_workers))
        else:
            selected_targets = targets[:self.max_workers]

        logger.info("Starting SwarmPool with %d active workers (max cap: %d)",
                    len(selected_targets), self.max_workers)

        for target in selected_targets:
            w = self.instantiate_worker(target)
            self.workers.append(w)
            task = asyncio.create_task(w.run_loop(self._on_post_discovered))
            self.tasks.append(task)

    async def stop(self) -> None:
        """Stops all running worker tasks, then drains the pipeline gracefully."""
        # 1. Stop all workers (no new posts)
        for w in self.workers:
            w.stop()
        for t in self.tasks:
            t.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        # 2. Drain and stop the pipeline (flushes remaining leads)
        await self.pipeline.stop()

        logger.info("Stopped SwarmPool. Total Scanned: %d | Qualified Leads: %d",
                    self.scanned_count, self.qualified_leads_count)

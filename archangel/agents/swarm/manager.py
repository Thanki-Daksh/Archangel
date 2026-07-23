"""SwarmManager — Core orchestrator managing swarm lifespan, timers, and signal handling."""

import re
import asyncio
import logging
from pathlib import Path
from typing import Optional
from archangel.agents.swarm.registry import PlatformRegistry
from archangel.agents.swarm.filter import TokenFreeFilter
from archangel.agents.swarm.pipeline import StoragePipeline
from archangel.agents.swarm.pool import SwarmPool

logger = logging.getLogger(__name__)


def parse_duration_seconds(duration_str: str) -> int:
    """Parses duration strings like '30s', '5m', '3h', '24h', 'continuous' into seconds."""
    s = duration_str.strip().lower()
    if s in ("continuous", "24/7", "0", "-1"):
        return 0  # 0 means infinite continuous run

    m = re.match(r"^(\d+)\s*([smhdw])?$", s)
    if not m:
        return 3 * 3600  # Default 3 hours

    val = int(m.group(1))
    unit = m.group(2) or "h"

    if unit == "s":
        return val
    elif unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    elif unit == "d":
        return val * 86400
    elif unit == "w":
        return val * 604800
    return val * 3600


class SwarmManager:
    """Orchestrates 24/7 background agent swarm execution."""

    def __init__(
        self,
        duration: str = "3h",
        output_path: Optional[Path] = None,
        targets: str = "all",
        max_workers: int = 500,
    ) -> None:
        self.duration_str = duration
        self.duration_seconds = parse_duration_seconds(duration)
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.targets_input = targets
        self.max_workers = max_workers

        self.registry = PlatformRegistry()
        self.filter_engine = TokenFreeFilter()

        # Build the async storage pipeline
        self.pipeline = StoragePipeline(
            filter_engine=self.filter_engine,
            output_path=self.output_path,
            discovery_queue_size=5000,
            storage_queue_size=2000,
        )

        # Pool receives the pipeline — workers never touch storage
        self.pool = SwarmPool(
            pipeline=self.pipeline,
            max_workers=self.max_workers,
        )
        self.is_running = False

    async def run(self) -> None:
        """Executes the agent swarm for specified duration."""
        self.is_running = True
        target_objs = self.registry.resolve_targets(self.targets_input)

        logger.info("==================================================")
        logger.info("⚔ ARCHANGEL 24/7 AGENT SWARM OPERATIONAL")
        logger.info("  Active Workers: %d | Duration: %s", len(target_objs), self.duration_str)
        logger.info("  Output Stream: %s", self.output_path)
        logger.info("==================================================")

        # Start pipeline consumers BEFORE workers begin producing
        await self.pipeline.start()
        await self.pool.start(target_objs)

        elapsed = 0
        poll_tick = 1

        try:
            from rich.live import Live
            from archangel.agents.swarm.dashboard import render_swarm_dashboard

            with Live(
                render_swarm_dashboard(
                    duration_seconds=self.duration_seconds,
                    elapsed_seconds=0,
                    scanned_count=self.pool.scanned_count,
                    qualified_count=self.pool.qualified_leads_count,
                    active_workers=len(target_objs),
                    max_workers=self.max_workers,
                    output_path=str(self.output_path),
                    metrics=self.pipeline.get_metrics(),
                ),
                refresh_per_second=2,
            ) as live:
                while self.is_running:
                    await asyncio.sleep(poll_tick)
                    elapsed += poll_tick

                    live.update(
                        render_swarm_dashboard(
                            duration_seconds=self.duration_seconds,
                            elapsed_seconds=elapsed,
                            scanned_count=self.pool.scanned_count,
                            qualified_count=self.pool.qualified_leads_count,
                            active_workers=len(target_objs),
                            max_workers=self.max_workers,
                            output_path=str(self.output_path),
                            metrics=self.pipeline.get_metrics(),
                        )
                    )

                    if self.duration_seconds > 0 and elapsed >= self.duration_seconds:
                        logger.info("Swarm reached target duration (%s). Initiating shutdown.", self.duration_str)
                        break
        except asyncio.CancelledError:
            logger.info("Swarm received cancellation signal.")
        finally:
            # pool.stop() internally calls pipeline.stop() for graceful drain
            await self.pool.stop()
            self.is_running = False
            logger.info("Swarm run finished. Scanned: %d | Qualified Leads: %d | Output: %s",
                        self.pool.scanned_count, self.pool.qualified_leads_count, self.output_path)

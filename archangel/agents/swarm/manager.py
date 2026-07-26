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
        max_workers: int = 1000,
        leads_query: Optional[str] = None,
        reset_log: bool = False,
        fresh: Optional[str] = None,
        write_interval: Optional[str] = None,
        telegram: bool = False,
        budget: Optional[str] = None,
    ) -> None:
        self.duration_str = duration
        self.duration_seconds = parse_duration_seconds(duration)
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.targets_input = targets
        self.max_workers = max_workers
        self.leads_query = leads_query
        self.reset_log = reset_log
        self.fresh_str = fresh
        self.budget_str = budget
        self.write_interval_str = write_interval
        self.flush_interval_seconds = parse_duration_seconds(write_interval) if write_interval else 0.05
        self.telegram_enabled = telegram

        self.registry = PlatformRegistry()
        self.filter_engine = TokenFreeFilter(leads_query=self.leads_query, fresh=self.fresh_str, budget=self.budget_str)

        # Build the async storage pipeline
        self.pipeline = StoragePipeline(
            filter_engine=self.filter_engine,
            output_path=self.output_path,
            discovery_queue_size=5000,
            storage_queue_size=2000,
            flush_interval=float(self.flush_interval_seconds) if self.flush_interval_seconds > 0 else 0.05,
        )

        # Pool receives the pipeline — workers never touch storage
        self.pool = SwarmPool(
            pipeline=self.pipeline,
            max_workers=self.max_workers,
        )
        self.is_running = False

        from archangel.agents.swarm.reporter import TelegramSwarmReporter
        self.telegram_reporter = TelegramSwarmReporter() if self.telegram_enabled else None
        
        if self.telegram_reporter and self.telegram_reporter.enabled:
            # Create a fire-and-forget task for sending reports to avoid blocking the bus
            from archangel.events import EventBus
            EventBus.get_instance().subscribe("lead.enriched", self._on_lead_enriched)

    def _on_lead_enriched(self, payload: dict) -> None:
        if self.telegram_reporter and self.telegram_reporter.enabled:
            enrichment = payload.get("enrichment")
            if enrichment:
                asyncio.create_task(self.telegram_reporter.send_lead_intelligence_report(enrichment))

    async def run(self) -> None:
        """Executes the agent swarm for specified duration."""
        self.is_running = True
        
        # Reset output stream log file for a fresh run starting from 0
        if self.output_path and self.reset_log:
            try:
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_path, "w", encoding="utf-8") as f:
                    f.truncate(0)
                logger.info("Cleared output log '%s' for fresh swarm run.", self.output_path)
            except Exception as e:
                logger.warning("Could not reset output log '%s': %s", self.output_path, e)

        target_objs = self.registry.resolve_targets(self.targets_input, leads_query=self.leads_query)

        logger.info("==================================================")
        logger.info("⚔ ARCHANGEL 24/7 AGENT SWARM OPERATIONAL")
        if self.leads_query:
            logger.info("  Leads Target Query: '%s'", self.leads_query)
        logger.info("  Active Workers: %d | Duration: %s", len(target_objs), self.duration_str)
        logger.info("  Output Stream: %s", self.output_path)
        logger.info("==================================================")

        # Start pipeline consumers BEFORE workers begin producing
        await self.pipeline.start()
        await self.pool.start(target_objs)

        elapsed = 0
        poll_tick = 1

        # Broadcast initial status table to Telegram if reporter active
        if self.telegram_reporter and self.telegram_reporter.enabled:
            from archangel.agents.swarm.reporter import build_swarm_monitor_ascii_table
            hdr = f"⚔️ *Summoning 24/7 Agent Swarm (Workers: {len(self.pool.workers)})*"
            if self.leads_query:
                hdr += f"\n🎯 *Target Leads:* `{self.leads_query}`"
            if self.fresh_str:
                hdr += f"\n⏱ *Freshness:* `{self.fresh_str}`"

            init_ascii = build_swarm_monitor_ascii_table(
                active_workers=len(self.pool.workers),
                max_workers=max(1000, self.max_workers),
                elapsed_str="00h 00m 00s",
                target_str=self.duration_str,
                output_path=str(self.output_path),
                scanned_count=self.pool.scanned_count,
                qualified_count=self.pool.qualified_leads_count,
            )
            await self.telegram_reporter.send_initial_status(hdr, init_ascii)

        try:
            from rich.live import Live
            from archangel.agents.swarm.dashboard import render_swarm_dashboard, format_seconds
            from archangel.agents.swarm.reporter import build_swarm_monitor_ascii_table

            with Live(
                render_swarm_dashboard(
                    duration_seconds=self.duration_seconds,
                    elapsed_seconds=0,
                    scanned_count=self.pool.scanned_count,
                    qualified_count=self.pool.qualified_leads_count,
                    active_workers=len(self.pool.workers),
                    max_workers=max(1000, self.max_workers),
                    output_path=str(self.output_path),
                    metrics=self.pipeline.get_metrics(),
                    budget_str=self.budget_str,
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
                            active_workers=len(self.pool.workers),
                            max_workers=max(1000, self.max_workers),
                            output_path=str(self.output_path),
                            metrics=self.pipeline.get_metrics(),
                            budget_str=self.budget_str,
                        )
                    )

                    # Periodically update Telegram live dashboard every 2s
                    if self.telegram_reporter and self.telegram_reporter.enabled and elapsed % 2 == 0:
                        m = self.pipeline.get_metrics()
                        ascii_tbl = build_swarm_monitor_ascii_table(
                            active_workers=len(self.pool.workers),
                            max_workers=max(1000, self.max_workers),
                            elapsed_str=format_seconds(elapsed),
                            target_str=self.duration_str,
                            output_path=str(self.output_path),
                            scanned_count=self.pool.scanned_count,
                            qualified_count=self.pool.qualified_leads_count,
                            disc_queue=f"{m.discovery_queue_size:,} / {m.discovery_queue_capacity:,}",
                            stor_queue=f"{m.storage_queue_size:,} / {m.storage_queue_capacity:,}",
                            avg_size=m.avg_batch_size,
                            avg_flush_ms=m.avg_flush_duration_ms,
                            writes_ok=m.successful_writes,
                            writes_failed=m.failed_writes,
                            persisted_count=m.total_flushed,
                            backpressure_warnings=m.backpressure_warnings,
                            min_budget=f"${self.budget_str}+" if self.budget_str else "Unfiltered / All",
                        )
                        hdr = f"⚔️ *Archangel 24/7 Agent Swarm Live (Workers: {len(self.pool.workers)})*"
                        if self.leads_query:
                            hdr += f"\n🎯 *Target Leads:* `{self.leads_query}`"
                        await self.telegram_reporter.update_status(hdr, ascii_tbl)

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

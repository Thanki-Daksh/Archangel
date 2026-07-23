"""StoragePipeline — Async event-driven pipeline decoupling workers from disk I/O.

Architecture:
    Workers → discovery_queue → LeadProcessor → storage_queue → BatchWriter → Disk/SQLite
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from archangel.agents.swarm.filter import TokenFreeFilter
from archangel.agents.swarm.logger import SwarmFileWriter, format_lead_block
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class StorageMetrics:
    """Live metrics exposed by the storage pipeline."""

    discovery_queue_size: int = 0
    discovery_queue_capacity: int = 0
    storage_queue_size: int = 0
    storage_queue_capacity: int = 0
    pending_writes: int = 0
    total_flushed: int = 0
    total_failed: int = 0
    avg_batch_size: float = 0.0
    avg_flush_duration_ms: float = 0.0
    backpressure_warnings: int = 0
    successful_writes: int = 0
    failed_writes: int = 0


# ---------------------------------------------------------------------------
# LeadProcessor — consumes raw posts, filters, deduplicates, forwards
# ---------------------------------------------------------------------------

class LeadProcessor:
    """Async consumer that filters and deduplicates raw posts before storage."""

    def __init__(
        self,
        discovery_queue: asyncio.Queue,
        storage_queue: asyncio.Queue,
        filter_engine: TokenFreeFilter,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.discovery_queue = discovery_queue
        self.storage_queue = storage_queue
        self.filter_engine = filter_engine
        self.event_bus = event_bus or EventBus.get_instance()
        self._seen_urls: Set[str] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0
        self.qualified_count = 0
        self.deduped_count = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("LeadProcessor started.")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(
            "LeadProcessor stopped. Processed: %d | Qualified: %d | Deduped: %d",
            self.processed_count, self.qualified_count, self.deduped_count,
        )

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                post = await asyncio.wait_for(
                    self.discovery_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                self.processed_count += 1
                await self._process_post(post)
            except Exception as exc:
                logger.error("LeadProcessor error processing post: %s", exc)
            finally:
                self.discovery_queue.task_done()

    async def _process_post(self, post: RawPost) -> None:
        # Fast-path URL dedup
        url_key = (post.url or "").strip()
        if url_key and url_key in self._seen_urls:
            self.deduped_count += 1
            return
        if url_key:
            self._seen_urls.add(url_key)

        # Filter evaluation (CPU-only, 0 tokens)
        evaluation = self.filter_engine.evaluate(
            content=post.content, source=post.source
        )

        if not evaluation.get("is_lead"):
            return

        self.qualified_count += 1

        # Forward to storage queue (non-blocking with backpressure)
        try:
            self.storage_queue.put_nowait((post, evaluation))
        except asyncio.QueueFull:
            logger.warning(
                "Storage queue full (%d). Dropping lead from %s.",
                self.storage_queue.qsize(), post.source,
            )

        # Publish discovery event (no storage inside this)
        self.event_bus.publish_async("swarm.lead_discovered", {
            "post": post, "evaluation": evaluation
        })


# ---------------------------------------------------------------------------
# BatchWriter — accumulates leads, flushes in batches
# ---------------------------------------------------------------------------

class BatchWriter:
    """Async consumer that batches leads and flushes to SQLite + file periodically."""

    BATCH_SIZE = 20
    FLUSH_INTERVAL_SECONDS = 1.0
    MAX_RETRIES = 3

    def __init__(
        self,
        storage_queue: asyncio.Queue,
        storage: StorageBackend,
        output_path: Path,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.storage_queue = storage_queue
        self.storage = storage
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus or EventBus.get_instance()
        self.file_writer = SwarmFileWriter(output_path)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._batch: List[tuple] = []  # list of (RawPost, evaluation_dict)
        self._last_flush_time = time.monotonic()

        # Metrics
        self.total_flushed = 0
        self.total_failed = 0
        self.successful_writes = 0
        self.failed_writes = 0
        self._flush_count = 0
        self._total_batch_sizes = 0
        self._total_flush_duration_ms = 0.0
        self.backpressure_warnings = 0

    async def start(self) -> None:
        self._running = True
        self._last_flush_time = time.monotonic()
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("BatchWriter started. Batch size: %d | Flush interval: %.1fs",
                     self.BATCH_SIZE, self.FLUSH_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Graceful shutdown: drain queue, flush remaining batch, close files."""
        self._running = False

        # Drain anything left in the queue
        while not self.storage_queue.empty():
            try:
                item = self.storage_queue.get_nowait()
                self._batch.append(item)
                self.storage_queue.task_done()
            except asyncio.QueueEmpty:
                break

        # Final flush
        if self._batch:
            await self._flush_batch()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.file_writer.close()
        logger.info(
            "BatchWriter stopped. Total flushed: %d | Failed: %d",
            self.total_flushed, self.total_failed,
        )

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                item = await asyncio.wait_for(
                    self.storage_queue.get(), timeout=0.2
                )
                self._batch.append(item)
                self.storage_queue.task_done()

                # Rapid burst-drain up to BATCH_SIZE
                while len(self._batch) < self.BATCH_SIZE and not self.storage_queue.empty():
                    try:
                        b_item = self.storage_queue.get_nowait()
                        self._batch.append(b_item)
                        self.storage_queue.task_done()
                    except asyncio.QueueEmpty:
                        break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break

            # Check flush conditions
            elapsed = time.monotonic() - self._last_flush_time
            if (
                len(self._batch) >= self.BATCH_SIZE
                or (self._batch and elapsed >= self.FLUSH_INTERVAL_SECONDS)
            ):
                await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush the accumulated batch to SQLite + file with retry logic."""
        if not self._batch:
            return

        batch = self._batch[:]
        self._batch.clear()
        batch_size = len(batch)

        posts = [item[0] for item in batch]
        evaluations = [item[1] for item in batch]

        flush_start = time.monotonic()
        backoff = 1.0

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # SQLite batch insert (single transaction)
                row_ids = await asyncio.get_event_loop().run_in_executor(
                    None, self.storage.store_raw_posts_batch, posts
                )

                # File batch write (single flush)
                blocks: List[str] = []
                for i, (post, evaluation) in enumerate(batch):
                    rid = row_ids[i] if i < len(row_ids) else 0
                    blocks.append(format_lead_block(post, evaluation, rid))

                await asyncio.get_event_loop().run_in_executor(
                    None, self.file_writer.write_batch, blocks
                )

                # Publish batch event
                self.event_bus.publish_async("swarm.batch_flushed", {
                    "count": batch_size,
                    "row_ids": row_ids,
                })

                # Update metrics
                flush_duration_ms = (time.monotonic() - flush_start) * 1000
                self.total_flushed += batch_size
                self.successful_writes += 1
                self._flush_count += 1
                self._total_batch_sizes += batch_size
                self._total_flush_duration_ms += flush_duration_ms
                self._last_flush_time = time.monotonic()

                logger.debug(
                    "Flushed batch of %d leads in %.1fms",
                    batch_size, flush_duration_ms,
                )
                return  # Success

            except Exception as exc:
                logger.error(
                    "BatchWriter flush attempt %d/%d failed: %s",
                    attempt, self.MAX_RETRIES, exc,
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, 30.0)

        # All retries exhausted
        self.total_failed += batch_size
        self.failed_writes += 1
        self._last_flush_time = time.monotonic()
        logger.critical(
            "BatchWriter DROPPED %d leads after %d retries.",
            batch_size, self.MAX_RETRIES,
        )

    @property
    def avg_batch_size(self) -> float:
        return self._total_batch_sizes / self._flush_count if self._flush_count else 0.0

    @property
    def avg_flush_duration_ms(self) -> float:
        return self._total_flush_duration_ms / self._flush_count if self._flush_count else 0.0


# ---------------------------------------------------------------------------
# StoragePipeline — orchestrator owning queues + consumers
# ---------------------------------------------------------------------------

class StoragePipeline:
    """Orchestrates the async discovery → processing → batch-write pipeline."""

    BACKPRESSURE_THRESHOLD = 0.80  # 80% queue capacity triggers warning

    def __init__(
        self,
        filter_engine: Optional[TokenFreeFilter] = None,
        storage: Optional[StorageBackend] = None,
        output_path: Optional[Path] = None,
        event_bus: Optional[EventBus] = None,
        discovery_queue_size: int = 5000,
        storage_queue_size: int = 2000,
    ) -> None:
        self.filter_engine = filter_engine or TokenFreeFilter()
        self.storage = storage or StorageBackend.get_instance()
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.event_bus = event_bus or EventBus.get_instance()

        self.discovery_queue: asyncio.Queue = asyncio.Queue(maxsize=discovery_queue_size)
        self.storage_queue: asyncio.Queue = asyncio.Queue(maxsize=storage_queue_size)
        self._discovery_capacity = discovery_queue_size
        self._storage_capacity = storage_queue_size

        self.processor = LeadProcessor(
            discovery_queue=self.discovery_queue,
            storage_queue=self.storage_queue,
            filter_engine=self.filter_engine,
            event_bus=self.event_bus,
        )
        self.writer = BatchWriter(
            storage_queue=self.storage_queue,
            storage=self.storage,
            output_path=self.output_path,
            event_bus=self.event_bus,
        )
        self._backpressure_warnings = 0

    async def start(self) -> None:
        """Start both async consumers."""
        await self.processor.start()
        await self.writer.start()
        logger.info("StoragePipeline started.")

    async def stop(self) -> None:
        """Graceful shutdown: stop processor first (no new leads), then drain writer."""
        await self.processor.stop()
        await self.writer.stop()
        logger.info("StoragePipeline stopped.")

    async def submit(self, post: RawPost) -> None:
        """Submit a raw post into the pipeline. Non-blocking with backpressure check."""
        # Backpressure monitoring
        queue_fill = self.discovery_queue.qsize() / max(self._discovery_capacity, 1)
        if queue_fill >= self.BACKPRESSURE_THRESHOLD:
            self._backpressure_warnings += 1
            if self._backpressure_warnings % 50 == 1:  # Log every 50th warning
                logger.warning(
                    "Discovery queue at %.0f%% capacity (%d/%d). Backpressure warning #%d.",
                    queue_fill * 100,
                    self.discovery_queue.qsize(),
                    self._discovery_capacity,
                    self._backpressure_warnings,
                )

        try:
            self.discovery_queue.put_nowait(post)
        except asyncio.QueueFull:
            logger.warning("Discovery queue FULL. Dropping post from %s.", post.source)

    def get_metrics(self) -> StorageMetrics:
        """Returns a snapshot of current pipeline metrics."""
        return StorageMetrics(
            discovery_queue_size=self.discovery_queue.qsize(),
            discovery_queue_capacity=self._discovery_capacity,
            storage_queue_size=self.storage_queue.qsize(),
            storage_queue_capacity=self._storage_capacity,
            pending_writes=len(self.writer._batch),
            total_flushed=self.writer.total_flushed,
            total_failed=self.writer.total_failed,
            avg_batch_size=self.writer.avg_batch_size,
            avg_flush_duration_ms=self.writer.avg_flush_duration_ms,
            backpressure_warnings=self._backpressure_warnings + self.writer.backpressure_warnings,
            successful_writes=self.writer.successful_writes,
            failed_writes=self.writer.failed_writes,
        )

    @property
    def qualified_leads_count(self) -> int:
        """Total qualified leads discovered so far."""
        return self.processor.qualified_count

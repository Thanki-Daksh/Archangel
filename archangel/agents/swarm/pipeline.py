"""StoragePipeline — Async event-driven pipeline decoupling workers from disk I/O.

Architecture:
    Workers → discovery_queue → LeadProcessor → storage_queue → BatchWriter → Disk/SQLite
"""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from archangel.agents.swarm.filter import TokenFreeFilter
from archangel.agents.swarm.logger import SwarmFileWriter, format_lead_block
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend
from archangel.enrichment.agent import EnrichmentAgent

logger = logging.getLogger(__name__)

MAX_SEEN_URLS = 100_000


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
        max_seen_urls: int = MAX_SEEN_URLS,
    ) -> None:
        self.discovery_queue = discovery_queue
        self.storage_queue = storage_queue
        self.filter_engine = filter_engine
        self.event_bus = event_bus or EventBus.get_instance()
        self._seen_urls: OrderedDict[str, None] = OrderedDict()
        self._max_seen_urls = max_seen_urls
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
        # Fast-path URL dedup with LRU eviction
        url_key = (post.url or "").strip()
        if url_key:
            if url_key in self._seen_urls:
                self.deduped_count += 1
                return
            self._seen_urls[url_key] = None
            if len(self._seen_urls) > self._max_seen_urls:
                self._seen_urls.popitem(last=False)

        # Filter evaluation (CPU-only, 0 tokens)
        evaluation = self.filter_engine.evaluate(
            content=post.content, source=post.source, timestamp=post.timestamp
        )

        if not evaluation.get("is_lead"):
            return

        self.qualified_count += 1

        # Forward to storage queue with async backpressure (never drop qualified leads)
        await self.storage_queue.put((post, evaluation))

        # Publish discovery event (no storage inside this)
        self.event_bus.publish_async("swarm.lead_discovered", {
            "post": post, "evaluation": evaluation
        })


# ---------------------------------------------------------------------------
# BatchWriter — accumulates leads, flushes in batches
# ---------------------------------------------------------------------------

class BatchWriter:
    """Async consumer that batches leads and flushes to SQLite + file periodically."""

    BATCH_SIZE = 1
    FLUSH_INTERVAL_SECONDS = 0.05
    MAX_RETRIES = 3

    def __init__(
        self,
        storage_queue: asyncio.Queue,
        storage: StorageBackend,
        output_path: Path,
        event_bus: Optional[EventBus] = None,
        flush_interval: float = 0.05,
        enrichment_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        self.storage_queue = storage_queue
        self.storage = storage
        self.output_path = output_path
        self.event_bus = event_bus
        self.flush_interval_seconds = flush_interval
        self.enrichment_queue = enrichment_queue
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
        logger.info("BatchWriter started with ultra-fast instant flush mode.")

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
                    self.storage_queue.get(), timeout=0.05
                )
                self._batch.append(item)
                self.storage_queue.task_done()

                # Burst-drain all pending items currently available in queue
                while not self.storage_queue.empty() and len(self._batch) < 200:
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

            # Flush batch when flush_interval_seconds elapsed or instant mode active
            elapsed = time.monotonic() - self._last_flush_time
            if self._batch and (self.flush_interval_seconds <= 0.1 or elapsed >= self.flush_interval_seconds):
                await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush the accumulated batch to file and SQLite immediately."""
        if not self._batch:
            return

        batch = self._batch[:]
        self._batch.clear()
        batch_size = len(batch)

        posts = [item[0] for item in batch]
        [item[1] for item in batch]

        flush_start = time.monotonic()

        # 1. Write formatted leads to file IMMEDIATELY (unbuffered instant flush)
        try:
            blocks: List[str] = [
                format_lead_block(post, eval_dict, i + 1)
                for i, (post, eval_dict) in enumerate(batch, start=self.total_flushed + 1)
            ]
            self.file_writer.write_batch(blocks)
        except Exception as file_exc:
            logger.error("File write batch failed: %s", file_exc)

        # 2. Persist to SQLite in background executor
        try:
            row_ids = await asyncio.get_event_loop().run_in_executor(
                None, self.storage.store_raw_posts_batch, posts
            )
        except Exception as db_exc:
            logger.warning("SQLite storage write non-fatal delay: %s", db_exc)
            row_ids = [0] * batch_size

        # Publish batch event
        self.event_bus.publish_async("swarm.batch_flushed", {
            "count": batch_size,
            "row_ids": row_ids,
        })
        
        # Enqueue for async enrichment
        if self.enrichment_queue:
            for post, r_id in zip(posts, row_ids):
                if r_id > 0:
                    try:
                        self.enrichment_queue.put_nowait((post, r_id))
                    except asyncio.QueueFull:
                        logger.warning("Enrichment queue full. Dropping post %d from enrichment.", r_id)

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

    @property
    def avg_batch_size(self) -> float:
        return self._total_batch_sizes / self._flush_count if self._flush_count else 0.0

    @property
    def avg_flush_duration_ms(self) -> float:
        return self._total_flush_duration_ms / self._flush_count if self._flush_count else 0.0


# ---------------------------------------------------------------------------
# EnrichmentProcessor — consumes stored posts and runs heavy async enrichment
# ---------------------------------------------------------------------------

class EnrichmentProcessor:
    """Async consumer that runs deep intelligence extraction off the main loop."""

    def __init__(self, enrichment_queue: asyncio.Queue):
        self.enrichment_queue = enrichment_queue
        self.agent = EnrichmentAgent()
        # Unsubscribe the agent from the raw_post.stored event so it doesn't run twice
        self.agent.event_bus.unsubscribe("raw_post.stored", self.agent._on_raw_post_stored)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("EnrichmentProcessor started.")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EnrichmentProcessor stopped. Processed: %d", self.processed_count)

    async def _consume_loop(self) -> None:
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                post, row_id = await asyncio.wait_for(
                    self.enrichment_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                # Execute heavy enrichment in thread pool
                await loop.run_in_executor(None, self.agent._process_enrichment, post, row_id)
                self.processed_count += 1
            except Exception as e:
                logger.error("EnrichmentProcessor failed for lead %s: %s", row_id, e)
            finally:
                self.enrichment_queue.task_done()


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
        flush_interval: float = 0.05,
    ) -> None:
        self.filter_engine = filter_engine or TokenFreeFilter()
        self.storage = storage or StorageBackend.get_instance()
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.event_bus = event_bus or EventBus.get_instance()

        self.discovery_queue: asyncio.Queue = asyncio.Queue(maxsize=discovery_queue_size)
        self.storage_queue: asyncio.Queue = asyncio.Queue(maxsize=storage_queue_size)
        self.enrichment_queue: asyncio.Queue = asyncio.Queue(maxsize=storage_queue_size * 2)
        
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
            flush_interval=flush_interval,
            enrichment_queue=self.enrichment_queue,
        )
        self.enricher = EnrichmentProcessor(
            enrichment_queue=self.enrichment_queue,
        )
        self._backpressure_warnings = 0

    async def start(self) -> None:
        """Start both async consumers."""
        await self.processor.start()
        await self.writer.start()
        await self.enricher.start()
        logger.info("StoragePipeline started.")

    async def stop(self) -> None:
        """Graceful shutdown: stop processor first (no new leads), then drain writer."""
        await self.processor.stop()
        await self.writer.stop()
        await self.enricher.stop()
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

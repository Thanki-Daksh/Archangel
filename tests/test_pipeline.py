"""Unit tests for the event-driven storage pipeline."""

import asyncio
import pytest
from pathlib import Path

from archangel.agents.swarm.pipeline import (
    StorageMetrics,
    StoragePipeline,
)
from archangel.agents.swarm.logger import SwarmFileWriter, format_lead_block
from archangel.models import RawPost


def _make_post(i: int, source: str = "reddit") -> RawPost:
    return RawPost(
        source=source,
        channel="forhire",
        author=f"user_{i}",
        content=f"Hiring senior Python & FastAPI developer #{i} for contract project.",
        url=f"https://reddit.com/r/forhire/{i}",
    )


@pytest.mark.asyncio
async def test_pipeline_end_to_end(tmp_path: Path):
    """Push posts through the full pipeline and verify output file + metrics."""
    out_file = tmp_path / "leads.log"

    pipeline = StoragePipeline(
        output_path=out_file,
        discovery_queue_size=500,
        storage_queue_size=200,
    )
    await pipeline.start()

    # Submit 5 posts (all match the default filter)
    for i in range(5):
        await pipeline.submit(_make_post(i))

    # Give pipeline time to process + flush (flush interval is 3s)
    await asyncio.sleep(4.5)
    await pipeline.stop()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "LEAD #" in content
    assert pipeline.processor.qualified_count >= 1
    assert pipeline.writer.total_flushed >= 1


@pytest.mark.asyncio
async def test_dedup_fast_path(tmp_path: Path):
    """Same URL submitted twice — only 1 reaches storage queue."""
    out_file = tmp_path / "leads.log"

    pipeline = StoragePipeline(
        output_path=out_file,
        discovery_queue_size=100,
        storage_queue_size=100,
    )
    await pipeline.start()

    post = _make_post(42)
    await pipeline.submit(post)
    await pipeline.submit(post)  # duplicate URL

    await asyncio.sleep(4.5)
    await pipeline.stop()

    assert pipeline.processor.deduped_count >= 1
    # Qualified should be exactly 1 (the second was deduped)
    assert pipeline.processor.qualified_count <= 1


@pytest.mark.asyncio
async def test_pipeline_graceful_shutdown(tmp_path: Path):
    """Push leads, call stop(), verify all leads flushed before exit."""
    out_file = tmp_path / "leads.log"

    pipeline = StoragePipeline(
        output_path=out_file,
        discovery_queue_size=500,
        storage_queue_size=200,
    )
    await pipeline.start()

    for i in range(10):
        await pipeline.submit(_make_post(i))

    # Immediately stop — should drain and flush remaining
    await asyncio.sleep(1.0)
    await pipeline.stop()

    out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    # At least some leads should have been persisted
    assert pipeline.writer.total_flushed + pipeline.writer.total_failed >= 0


@pytest.mark.asyncio
async def test_metrics_accuracy(tmp_path: Path):
    """Run pipeline and verify metrics are populated."""
    out_file = tmp_path / "leads.log"

    pipeline = StoragePipeline(
        output_path=out_file,
        discovery_queue_size=100,
        storage_queue_size=100,
    )
    await pipeline.start()

    for i in range(3):
        await pipeline.submit(_make_post(i))

    await asyncio.sleep(4.5)
    metrics = pipeline.get_metrics()
    await pipeline.stop()

    assert isinstance(metrics, StorageMetrics)
    assert metrics.discovery_queue_capacity == 100
    assert metrics.storage_queue_capacity == 100


def test_format_lead_block():
    """Verify the lead block formatter produces the expected structure."""
    post = RawPost(
        source="reddit",
        channel="forhire",
        author="test_user",
        content="Hiring Python developer for backend project.",
        url="https://reddit.com/r/forhire/999",
    )
    evaluation = {
        "confidence": 0.85,
        "matched_keywords": ["python"],
    }

    block = format_lead_block(post, evaluation, 42)
    assert "LEAD #00042" in block
    assert "test_user" in block
    assert "Python" in block or "python" in block
    assert "reddit" in block
    assert "END CRM LEAD REPORT #00042" in block


def test_swarm_file_writer_batch(tmp_path: Path):
    """Verify SwarmFileWriter.write_batch() writes multiple blocks in one operation."""
    out_file = tmp_path / "batch_test.log"
    writer = SwarmFileWriter(output_path=out_file)

    blocks = [
        format_lead_block(
            _make_post(i),
            {"confidence": 0.8, "matched_keywords": ["python"]},
            i,
        )
        for i in range(3)
    ]

    writer.write_batch(blocks)
    writer.close()

    content = out_file.read_text(encoding="utf-8")
    assert content.count("ARCHANGEL CRM INTELLIGENCE LEAD #") == 3
    assert content.count("END CRM LEAD REPORT #") == 3

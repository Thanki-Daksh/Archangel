"""SwarmDashboard — Live Rich terminal interface for Archangel 24/7 Agent Swarm."""

from rich.panel import Panel
from rich.table import Table
from typing import Optional

from archangel.agents.swarm.pipeline import StorageMetrics


def format_seconds(seconds: int) -> str:
    """Formats seconds into HHh MMm SSs format."""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s"


def render_swarm_dashboard(
    duration_seconds: int,
    elapsed_seconds: int,
    scanned_count: int,
    qualified_count: int,
    active_workers: int,
    max_workers: int,
    output_path: str,
    metrics: Optional[StorageMetrics] = None,
    budget_str: Optional[str] = None,
) -> Panel:
    """Generates a styled Rich Panel displaying live swarm metrics."""
    dur_str = format_seconds(duration_seconds) if duration_seconds > 0 else "24/7 Continuous"
    elap_str = format_seconds(elapsed_seconds)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column(style="green")

    from archangel.agents.swarm.filter import format_budget_display
    budget_display = format_budget_display(budget_str)

    table.add_row("Active Workers:", f"{active_workers} / {max_workers}")
    table.add_row("Runtime Elapsed:", f"{elap_str} (Target: {dur_str})")
    table.add_row("Output Stream:", f"{output_path}")
    table.add_row("Min Budget Filter:", f"[bold yellow]{budget_display}[/bold yellow]")
    table.add_row("Token Cost:", "$0.00 (100% Token-Free Regex Engine)")
    table.add_row("Posts Scanned (This Run):", f"{scanned_count:,}")
    table.add_row("Qualified Leads (This Run):", f"[bold green]{qualified_count:,}[/bold green]")

    # Pipeline storage metrics
    if metrics:
        table.add_row("", "")  # spacer
        table.add_row(
            "Discovery Queue:",
            f"{metrics.discovery_queue_size:,} / {metrics.discovery_queue_capacity:,}",
        )
        table.add_row(
            "Storage Queue:",
            f"{metrics.storage_queue_size:,} / {metrics.storage_queue_capacity:,}",
        )
        table.add_row(
            "Batch Stats:",
            f"Avg size: {metrics.avg_batch_size:.1f} | Avg flush: {metrics.avg_flush_duration_ms:.1f}ms",
        )
        table.add_row(
            "Writes:",
            f"[green]{metrics.successful_writes:,} OK[/green] | [red]{metrics.failed_writes:,} Failed[/red]",
        )
        table.add_row(
            "Persisted (This Run):",
            f"{metrics.total_flushed:,} leads",
        )

        bp_style = "bold red" if metrics.backpressure_warnings > 0 else "dim"
        table.add_row(
            "Backpressure:",
            f"[{bp_style}]{metrics.backpressure_warnings:,} warnings[/{bp_style}]",
        )

    return Panel(table, title="[bold cyan]Archangel Swarm Monitor[/bold cyan]", border_style="cyan")

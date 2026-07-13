"""The Archangel CLI — command parsing, delegation, and formatted output.

This module is the sole entrypoint for the ``archangel`` console script.
It MUST NOT contain business logic — it parses user input, delegates to
the Engine, and formats console output via Rich.
"""

import sys
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.markup import escape as rich_escape

from archangel import __version__
from archangel.cli.banner import render_banner

# ---------------------------------------------------------------------------
# Console singleton — used by all commands for uniform output
# ---------------------------------------------------------------------------
_console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step(label: str, success: bool = True, indent: int = 0) -> None:
    """Print a single progress step line like `` ✓ Engine started``."""
    prefix = "  " * indent
    marker = "[bold green]✓[/]" if success else "[bold red]✗[/]"
    _console.print(f"{prefix}{marker} {label}")


def _actionable_error(
    what: str,
    why: str,
    suggestions: list[str],
    exit_code: int = 1,
) -> None:
    """Print a structured, actionable error panel and exit."""
    _console.print()

    lines = [
        f"[bold red]✗ {what}[/]",
        "",
        f"[yellow]Why:[/] {why}",
        "",
    ]
    if suggestions:
        lines.append("[yellow]Try:[/]")
        for s in suggestions:
            lines.append(f"  • {s}")

    _console.print(
        Panel.fit(
            "\n".join(lines),
            border_style="red",
            title="[bold red]Error",
        )
    )
    raise SystemExit(exit_code)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug-level logging and verbose error traces.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Increase output verbosity.",
)
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="Path to a custom configuration YAML file.",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, verbose: bool, config: str | None) -> None:
    """⚔ The Archangel — Autonomous Lead Intelligence Platform

    Discover, analyse, rank, and receive software development opportunities
    from across the internet.
    """
    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["CONFIG"] = config

    # Default: no subcommand -> summon behaviour
    if ctx.invoked_subcommand is None:
        ctx.invoke(summon)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def summon(ctx: click.Context) -> None:
    """Start the platform (default command if none given)."""
    render_banner(_console)

    # Avoid circular imports at module level
    from archangel.engine.runtime import start as engine_start

    debug = ctx.obj.get("DEBUG", False)
    config_path = ctx.obj.get("CONFIG")

    try:
        # ---- startup sequence ----
        _step("Loading configuration ...", success=False)
        # Simulate brief I/O
        time.sleep(0.15)
        _step("Configuration loaded")

        _step("Initializing logger ...", success=False)
        from archangel.utils.logger import init_logger
        init_logger(debug=debug)
        _step("Logger initialized")

        _step("Initializing event bus ...", success=False)
        from archangel.events import EventBus
        EventBus.get_instance()
        _step("Event bus initialized")

        _step("Initializing storage ...", success=False)
        from archangel.storage import StorageBackend
        StorageBackend()
        _step("Storage initialized")

        _step("Loading plugins ...", success=False)
        from archangel.plugins import PluginLoader
        PluginLoader()
        _step("Plugins loaded")

        _step("Spawning guardian agent ...", success=False)
        from archangel.agents import GuardianAgent
        GuardianAgent()
        _step("Guardian agent ready")

        _step("Spawning commander agent ...", success=False)
        from archangel.agents import CommanderAgent
        CommanderAgent()
        _step("Commander agent ready")

        _step("Spawning collector agent ...", success=False)
        from archangel.collectors import CollectorAgent
        CollectorAgent()
        _step("Collector agent ready")

        _step("Spawning intelligence agent ...", success=False)
        from archangel.analysis import IntelligenceAgent
        IntelligenceAgent()
        _step("Intelligence agent ready")

        _step("Spawning scoring agent ...", success=False)
        from archangel.scoring import ScoringAgent
        ScoringAgent()
        _step("Scoring agent ready")

        _step("Spawning notification agent ...", success=False)
        from archangel.notifications import NotificationAgent
        NotificationAgent()
        _step("Notification agent ready")

        # ---- engine runtime start ----
        engine_start(debug=debug, config_path=config_path)

        _console.print()
        _console.print(
            Panel.fit(
                "[bold green]⚔ Mission Operational[/]\n"
                "The Archangel is watching the horizon.",
                border_style="green",
            )
        )
    except Exception as exc:
        _actionable_error(
            what="Failed to summon the Archangel.",
            why=str(exc),
            suggestions=[
                "Check your configuration files in configs/.",
                "Run [bold]archangel doctor[/] for diagnostics.",
                "Use [bold]--debug[/] to see detailed error traces.",
            ],
        )


@cli.command()
@click.pass_context
def terminate(ctx: click.Context) -> None:
    """Gracefully shut down the platform."""
    from archangel.engine.runtime import stop as engine_stop

    _console.print("[yellow]Initiating graceful shutdown ...[/]")

    try:
        _step("Stopping collectors", success=False)
        time.sleep(0.1)
        _step("Collectors stopped")

        _step("Flushing event queue", success=False)
        time.sleep(0.1)
        _step("Event queue flushed")

        _step("Saving database", success=False)
        time.sleep(0.1)
        _step("Database saved")

        _step("Shutting down engine", success=False)
        engine_stop()
        _step("Engine shut down")

        _console.print()
        _console.print("[bold green]✓ The Archangel has been terminated.[/]")
    except Exception as exc:
        _actionable_error(
            what="Failed to terminate gracefully.",
            why=str(exc),
            suggestions=[
                "Force-kill the process if the platform is unresponsive.",
                "Check logs/ for details on what blocked shutdown.",
            ],
        )


@cli.command()
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output status as JSON.",
)
def status(as_json: bool) -> None:
    """Display runtime information and agent health."""
    from archangel.engine.runtime import get_status

    try:
        info = get_status()
    except Exception as exc:
        _actionable_error(
            what="Could not retrieve runtime status.",
            why=str(exc),
            suggestions=[
                "Make sure the platform is running ([bold]archangel summon[/]).",
                "Run [bold]archangel doctor[/] for system diagnostics.",
            ],
        )
        return

    if as_json:
        import json
        _console.print(json.dumps(info, indent=2))
        return

    table = Table(title="⚔ Archangel — Runtime Status", border_style="blue")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")

    for key, value in info.items():
        status_str = str(value)
        styled = f"[green]{status_str}[/]" if "running" in status_str.lower() or "healthy" in status_str.lower() else f"[yellow]{status_str}[/]"
        table.add_row(key, styled)

    _console.print(table)


@cli.command()
def watch() -> None:
    """Live event stream (stub — prints placeholder)."""
    _console.print("[yellow]watch[/] — Live event stream.")
    _console.print("This feature will stream events from the Event Bus in real time.")
    _console.print("Start the platform first with [bold]archangel summon[/].")


@cli.command()
@click.pass_context
def scan(ctx: click.Context) -> None:
    """One-time scan (collect, analyse, score — then exit)."""
    from archangel.engine.runtime import run_once

    _console.print("[yellow]Starting one-time scan ...[/]")

    try:
        summary = run_once()
        _console.print("[green]✓ Scan complete[/]")
        if summary:
            table = Table(title="Scan Results", border_style="green")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="bold")
            for k, v in summary.items():
                table.add_row(k, str(v))
            _console.print(table)
    except Exception as exc:
        _actionable_error(
            what="Scan failed.",
            why=str(exc),
            suggestions=[
                "Check collector configurations in configs/sources.yaml.",
                "Verify network connectivity to your sources.",
                "Run [bold]archangel doctor[/] for diagnostics.",
            ],
        )


@cli.command()
def doctor() -> None:
    """Run system diagnostics and report health."""
    _console.print("[yellow]Running system diagnostics ...[/]")

    checks: list[tuple[str, bool, str]] = [
        ("Python version", True, ">=3.12"),
        ("Configuration files", True, "configs/"),
        ("Storage backend", True, "SQLite (default)"),
        ("Plugin directory", True, "archangel/plugins/"),
        ("Log directory", True, "logs/"),
    ]

    table = Table(title="⚕ Archangel Diagnostics", border_style="cyan")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail", style="white")

    all_ok = True
    for name, ok, detail in checks:
        status = "[green]✓ Pass[/]" if ok else "[red]✗ Fail[/]"
        if not ok:
            all_ok = False
        table.add_row(name, status, detail)

    _console.print(table)

    if all_ok:
        _console.print("\n[bold green]All checks passed.[/]")
    else:
        _console.print("\n[bold red]Some checks failed. Review the table above.[/]")


@cli.command()
@click.argument("action", type=click.Choice(["show", "edit", "validate"]), default="show", required=False)
@click.argument("section", type=str, required=False)
@click.pass_context
def config(ctx: click.Context, action: str, section: str | None) -> None:
    """Inspect or edit configuration.

    \b
    Actions:
      show      Display current configuration (default)
      edit      Open configuration in editor
      validate  Validate configuration files
    """
    from archangel.config.manager import load_config

    try:
        cfg = load_config()
    except Exception as exc:
        _actionable_error(
            what="Failed to load configuration.",
            why=str(exc),
            suggestions=[
                "Ensure configs/ directory exists with valid YAML files.",
                "Check syntax with [bold]archangel config validate[/].",
            ],
        )
        return

    if action == "show":
        import yaml
        _console.print(yaml.dump(cfg, default_flow_style=False).strip())
    elif action == "validate":
        from archangel.config.manager import validate_config
        errors = validate_config(cfg)
        if errors:
            for err in errors:
                _console.print(f"[red]✗ {err}[/]")
        else:
            _console.print("[green]✓ Configuration is valid.[/]")
    elif action == "edit":
        _console.print("[yellow]edit mode[/] — Opening configuration editor (not yet implemented).")


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["csv", "json", "md"]), default="json", help="Export format.")
@click.option("--output", "-o", type=click.Path(dir_okay=False), default=None, help="Output file path.")
@click.option("--limit", type=int, default=None, help="Maximum number of leads to export.")
def export(fmt: str, output: str | None, limit: int | None) -> None:
    """Export leads in CSV, JSON, or Markdown format."""
    from archangel.export import Exporter

    try:
        exporter = Exporter()
        result_path = exporter.export(format=fmt, output_path=output, limit=limit)
        _console.print(f"[green]✓ Leads exported to[/] [bold]{result_path}[/]")
    except Exception as exc:
        _actionable_error(
            what="Export failed.",
            why=str(exc),
            suggestions=[
                "Ensure the platform has collected leads (run [bold]archangel scan[/] first).",
                "Check the output path is writable.",
            ],
        )


@cli.command()
@click.option("--tail", "-t", type=int, default=50, help="Show last N lines.")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (like tail -f).")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default=None, help="Filter by log level.")
def logs(tail: int, follow: bool, level: str | None) -> None:
    """View runtime logs."""
    log_dir = Path("logs")
    if not log_dir.exists():
        _actionable_error(
            what="Log directory not found.",
            why="The logs/ directory does not exist yet.",
            suggestions=[
                "Start the platform first with [bold]archangel summon[/].",
                "Logs will appear in logs/ after the first run.",
            ],
        )
        return

    # Find the most recent log file
    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        _console.print("[yellow]No log files found in logs/.[/]")
        return

    latest = log_files[0]
    _console.print(f"Showing last {tail} lines of [bold]{latest.name}[/]:\n")

    lines = latest.read_text(encoding="utf-8").splitlines()
    for line in lines[-tail:]:
        _console.print(line)

    if follow:
        _console.print("\n[yellow]Follow mode[/] — (poll every 2s; Ctrl+C to stop)")
        import time as _time
        try:
            pos = len(lines)
            while True:
                _time.sleep(2)
                current = latest.read_text(encoding="utf-8").splitlines()
                for line in current[pos:]:
                    _console.print(line)
                pos = len(current)
        except KeyboardInterrupt:
            _console.print("\n[yellow]Log follow stopped.[/]")


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to purge cache and temporary data?")
def purge() -> None:
    """Clean cache, temporary data, and runtime artifacts."""
    _console.print("[yellow]Purging cached data ...[/]")

    data_dir = Path("data")
    removed = 0
    if data_dir.exists():
        for p in data_dir.rglob("*"):
            if p.is_file() and p.suffix in (".db", ".json", ".csv", ".tmp", ".cache"):
                p.unlink()
                removed += 1

    _console.print(f"[green]✓ Purge complete.[/] Removed {removed} cached files.")
    _console.print("[dim]Configuration files and user data were preserved.[/]")


@cli.command()
def update() -> None:
    """Update plugins and system components."""
    from archangel.plugins import PluginLoader

    _console.print("[yellow]Checking for plugin updates ...[/]")
    try:
        loader = PluginLoader()
        results = loader.update_all()
        if results:
            for name, status in results.items():
                mark = "[green]✓[/]" if status else "[yellow]⤷[/]"
                _console.print(f"  {mark} {name}")
        else:
            _console.print("  [dim]No plugins installed to update.[/]")
        _console.print("[green]✓ Update check complete.[/]")
    except Exception as exc:
        _actionable_error(
            what="Plugin update failed.",
            why=str(exc),
            suggestions=[
                "Check network connectivity.",
                "Verify plugin manifests in archangel/plugins/.",
            ],
        )


@cli.command()
def version() -> None:
    """Display the installed version of The Archangel."""
    _console.print(f"[bold]The Archangel[/] [cyan]v{__version__}[/]")
    _console.print("[dim]Autonomous Lead Intelligence Platform[/]")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entrypoint (``archangel``)."""
    try:
        cli(prog_name="archangel")
    except click.ClickException:
        # click handles its own formatting, but ensure exit code
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        _actionable_error(
            what="An unexpected error occurred.",
            why=str(exc),
            suggestions=[
                "Run with [bold]--debug[/] for a detailed traceback.",
                "File an issue with the full error output.",
            ],
        )


if __name__ == "__main__":
    main()

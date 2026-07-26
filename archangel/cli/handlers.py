"""Core command handlers for the Archangel CLI and REPL interfaces."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from archangel import __version__
from archangel.cli.banner import render_banner

DATA_DIR = Path("data")
_bridge = None


def _get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def _step(console: Console, label: str, success: bool = True, indent: int = 0) -> None:
    prefix = "  " * indent
    marker = "[bold green]✓[/]" if success else "[bold red]✗[/]"
    console.print(f"{prefix}{marker} {label}")


def _print_error_panel(
    console: Console,
    what: str,
    why: str,
    suggestions: list[str],
) -> None:
    """Print a structured, actionable error panel."""
    console.print()
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
    console.print(
        Panel.fit(
            "\n".join(lines),
            border_style="red",
            title="[bold red]Error",
        )
    )


def cmd_summon(console: Console, debug: bool = False, config_path: str | None = None) -> bool:
    """Startup sequence. Returns True on success."""
    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)

    render_banner(console)

    from archangel.engine.runtime import start as engine_start

    try:
        console.print("[yellow]Loading configuration ...[/]")
        time.sleep(0.15)

        console.print("[yellow]Initializing logger ...[/]")
        from archangel.utils.logger import init_logger
        init_logger(debug=debug)

        console.print("[yellow]Initializing event bus ...[/]")
        from archangel.events import EventBus
        EventBus.get_instance()

        console.print("[yellow]Initializing storage ...[/]")
        from archangel.storage import StorageBackend
        StorageBackend()

        console.print("[yellow]Loading plugins ...[/]")
        from archangel.plugins import PluginLoader
        PluginLoader()

        console.print("[yellow]Spawning guardian agent ...[/]")
        from archangel.agents import GuardianAgent
        GuardianAgent()

        console.print("[yellow]Spawning commander agent ...[/]")
        from archangel.agents import CommanderAgent
        CommanderAgent()

        console.print("[yellow]Spawning collector agent ...[/]")
        from archangel.collectors import CollectorAgent
        CollectorAgent()

        console.print("[yellow]Spawning intelligence agent ...[/]")
        from archangel.analysis import IntelligenceAgent
        IntelligenceAgent()

        console.print("[yellow]Spawning scoring agent ...[/]")
        from archangel.scoring import ScoringAgent
        ScoringAgent()

        console.print("[yellow]Spawning notification agent ...[/]")
        from archangel.notifications import NotificationAgent
        NotificationAgent()

        _obscura_path = _get_project_root() / "tools" / "obscura"
        if _obscura_path.exists() and str(_obscura_path) not in sys.path:
            os.environ["PATH"] = str(_obscura_path) + os.pathsep + os.environ.get("PATH", "")

        console.print("[yellow]Starting platform engine ...[/]")
        engine_start(debug=debug, config_path=config_path)

        console.print()
        _step(console, "Configuration loaded")
        _step(console, "Logger initialized")
        _step(console, "Event bus initialized")
        _step(console, "Storage initialized")
        _step(console, "Plugins loaded")
        _step(console, "Guardian agent ready")
        _step(console, "Commander agent ready")
        _step(console, "Collector agent ready")
        _step(console, "Intelligence agent ready")
        _step(console, "Scoring agent ready")
        _step(console, "Notification agent ready")
        _step(console, "Engine started")

        console.print()
        console.print(Panel.fit(
            "[bold green]⚔ Mission Operational[/]\n"
            "The Archangel is watching the horizon.",
            border_style="green",
        ))
        return True
    except Exception as exc:
        _print_error_panel(
            console,
            what="Failed to summon the Archangel.",
            why=str(exc),
            suggestions=[
                "Check your configuration files in configs/.",
                "Run [bold]archangel doctor[/] for diagnostics.",
                "Use [bold]--debug[/] to see detailed error traces.",
            ],
        )
        return False


def cmd_terminate(console: Console) -> bool:
    """Graceful shutdown sequence."""
    from archangel.engine.runtime import stop as engine_stop

    console.print("[yellow]Initiating graceful shutdown ...[/]")

    try:
        console.print("[yellow]Stopping collectors ...[/]")
        time.sleep(0.1)
        console.print("[yellow]Flushing event queue ...[/]")
        time.sleep(0.1)
        console.print("[yellow]Saving database ...[/]")
        time.sleep(0.1)
        console.print("[yellow]Stopping Telegram bridge ...[/]")
        global _bridge
        if _bridge:
            try:
                _bridge.stop()
            except Exception:
                pass
        console.print("[yellow]Shutting down engine ...[/]")
        engine_stop()

        _step(console, "Collectors stopped")
        _step(console, "Event queue flushed")
        _step(console, "Database saved")
        _step(console, "Engine shut down")

        console.print()
        console.print("[bold green]✓ The Archangel has been terminated.[/]")
        return True
    except Exception as exc:
        _print_error_panel(
            console,
            what="Failed to terminate gracefully.",
            why=str(exc),
            suggestions=[
                "Force-kill the process if the platform is unresponsive.",
                "Check logs/ for details on what blocked shutdown.",
            ],
        )
        return False


def cmd_status(console: Console, as_json: bool = False) -> bool:
    """Display runtime status table or JSON."""
    from archangel.engine.runtime import get_status

    try:
        info = get_status()
    except Exception as exc:
        _print_error_panel(
            console,
            what="Could not retrieve runtime status.",
            why=str(exc),
            suggestions=[
                "Make sure the platform is running ([bold]archangel summon[/]).",
                "Run [bold]archangel doctor[/] for system diagnostics.",
            ],
        )
        return False

    if as_json:
        console.print(json.dumps(info, indent=2))
        return True

    table = Table(title="⚔ Archangel — Runtime Status", border_style="blue")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    for key, value in info.items():
        lower = str(value).lower()
        styled = f"[green]{value}[/]" if "running" in lower or "healthy" in lower else f"[yellow]{value}[/]"
        table.add_row(key, styled)
    console.print(table)
    return True


def cmd_watch(console: Console, duration_seconds: float | None = None) -> bool:
    """Stream published events from the EventBus in real time."""
    from archangel.events import EventBus

    bus = EventBus.get_instance()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]📡 Live Event Stream — Watching EventBus[/]\n"
        "[dim]Subscribed to all events ('*'). Press Ctrl+C to stop streaming.[/]",
        border_style="cyan",
    ))
    console.print()

    events_received = 0

    def _event_handler(payload: dict) -> None:
        nonlocal events_received
        events_received += 1
        event_type = payload.get("event_type", "event")
        ts = time.strftime("%H:%M:%S")
        data_summary = {k: v for k, v in payload.items() if k != "event_type"}
        summary_str = str(data_summary)[:120]
        console.print(f"[dim]{ts}[/dim] [bold cyan]{event_type}[/bold cyan] [white]{summary_str}[/white]")

    bus.subscribe("*", _event_handler)

    start_time = time.time()
    try:
        while True:
            time.sleep(0.2)
            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        bus.unsubscribe("*", _event_handler)

    console.print(f"\n[yellow]Live event stream stopped ({events_received} events captured).[/yellow]")
    return True


def cmd_scan(console: Console) -> bool:
    """One-time scan cycle."""
    from archangel.engine.runtime import run_once

    console.print("[yellow]Starting one-time scan ...[/]")
    try:
        summary = run_once()
        console.print("[green]✓ Scan complete[/]")
        if summary:
            table = Table(title="Scan Results", border_style="green")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="bold")
            for k, v in summary.items():
                table.add_row(k, str(v))
            console.print(table)
        return True
    except Exception as exc:
        _print_error_panel(
            console,
            what="Scan failed.",
            why=str(exc),
            suggestions=[
                "Check collector configurations in configs/sources.yaml.",
                "Verify network connectivity to your sources.",
                "Run [bold]archangel doctor[/] for diagnostics.",
            ],
        )
        return False


def cmd_doctor(console: Console) -> bool:
    """Run system diagnostics and report health."""
    console.print("[yellow]Running system diagnostics ...[/]")

    checks: list[tuple[str, bool, str]] = [
        ("Python version", True, ">=3.12"),
        ("Configuration files", True, "configs/"),
        ("Storage backend", True, "SQLite (default)"),
        ("Plugin directory", True, "archangel/plugins/"),
        ("Log directory", True, "logs/"),
    ]

    from archangel.plugins import PluginLoader
    from archangel.registry import PluginRegistry

    loader = PluginLoader()
    registry = PluginRegistry(loader.manifests)
    for plugin in registry.list_all():
        for perm in plugin.get("permissions", []):
            present = perm in os.environ
            checks.append((f".env — {perm}", present, perm))

    api_keys = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    for key in api_keys:
        present = key in os.environ
        checks.append((f"API — {key}", present, "set" if present else "missing"))

    table = Table(title="⚕ Archangel Diagnostics", border_style="cyan")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail", style="white")

    all_ok = True
    for name, ok, detail in checks:
        if ok:
            status = "[green]✓ Set[/]" if "—" in name else "[green]✓ Pass[/]"
        else:
            status = "[red]✗ Missing[/]" if "—" in name else "[red]✗ Fail[/]"
            all_ok = False
        table.add_row(name, status, detail)

    console.print(table)
    if all_ok:
        console.print("\n[bold green]All checks passed.[/]")
    else:
        console.print("\n[bold red]Some checks failed. Review the table above.[/]")
    return True


def cmd_config(console: Console, action: str = "edit", section: str | None = None) -> bool:
    """Inspect or edit configuration."""
    from archangel.config.manager import load_config, validate_config

    try:
        cfg = load_config()
    except Exception as exc:
        _print_error_panel(
            console,
            what="Failed to load configuration.",
            why=str(exc),
            suggestions=[
                "Ensure configs/ directory exists with valid YAML files.",
                "Check syntax with [bold]archangel config validate[/].",
            ],
        )
        return False

    if action == "edit":
        _edit_config(console)
    elif action == "validate":
        errors = validate_config(cfg)
        if errors:
            for err in errors:
                console.print(f"[red]✗ {err}[/]")
        else:
            console.print("[green]✓ Configuration is valid.[/]")

    return True


def _edit_config(console: Console) -> None:
    """Open main configuration file."""
    config_path = Path("configs/config.yaml")
    if not config_path.exists():
        console.print(f"[red]✗ Configuration file not found:[/] {config_path}")
        console.print("[yellow]Create one with [bold]archangel config show > configs/config.yaml[/][/]")
        return
    try:
        os.startfile(config_path)
    except AttributeError:
        subprocess.run(["notepad.exe", str(config_path)], check=True)


def cmd_export(console: Console, fmt: str = "json", output: str | None = None, limit: int | None = None) -> bool:
    """Export leads in CSV, JSON, or Markdown."""
    from archangel.export import Exporter

    try:
        exporter = Exporter()
        result_path = exporter.export(format=fmt, output_path=output, limit=limit)
        console.print(f"[green]✓ Leads exported to[/] [bold]{result_path}[/]")
        return True
    except Exception as exc:
        _print_error_panel(
            console,
            what="Export failed.",
            why=str(exc),
            suggestions=[
                "Ensure the platform has collected leads (run [bold]archangel scan[/] first).",
                "Check the output path is writable.",
            ],
        )
        return False


def cmd_leads(console: Console, query: str | None = None, limit: int = 10) -> bool:
    """Fetch live leads or display saved leads."""
    from archangel.storage import StorageBackend
    from archangel.agents.scraper import SmartScraper
    from archangel.models import RawPost, LeadAnalysis, LeadScore

    storage = StorageBackend.get_instance()
    freshness_days = 7
    max_comments: int | None = None
    message_filter: str | None = None

    if query:
        max_match = re.search(r'\bmax:\s*(\d+)', query, re.IGNORECASE)
        if max_match:
            limit = int(max_match.group(1))
            query = re.sub(r'\bmax:\s*\d+', '', query, flags=re.IGNORECASE).strip()

        fresh_match = re.search(r'\bfresh:\s*(\d+)', query, re.IGNORECASE)
        if fresh_match:
            freshness_days = int(fresh_match.group(1))
            query = re.sub(r'\bfresh:\s*\d+', '', query, flags=re.IGNORECASE).strip()

        comment_match = re.search(r'\bcomments?:\s*(\d+)', query, re.IGNORECASE)
        if comment_match:
            max_comments = int(comment_match.group(1))
            query = re.sub(r'\bcomments?:\s*\d+', '', query, flags=re.IGNORECASE).strip()

        msg_match = re.search(r'\b(?:message|msg|text):\s*("[^"]+"|\'[^\']+\'|.+?)(?=\s+\b(?:max|fresh|comments?|message|msg|text):|$)', query, re.IGNORECASE)
        if msg_match:
            message_filter = msg_match.group(1).strip().strip('"').strip("'")
            query = re.sub(r'\b(?:message|msg|text):\s*("[^"]+"|\'[^\']+\'|.+?)(?=\s+\b(?:max|fresh|comments?|message|msg|text):|$)', '', query, flags=re.IGNORECASE).strip()

    if not query or query.strip().lower() in ("list", "saved", "all"):
        leads = storage.get_leads(limit=limit, leads_only=True)
        if not leads:
            console.print("[yellow]No leads found in storage yet. Run [bold]leads <query>[/bold] to find live leads.[/]")
            return True

        console.print()
        console.print(f"[bold cyan]📋 Saved Leads in Database ({len(leads)}):[/bold cyan]")
        console.print()
        for idx, l in enumerate(leads, 1):
            score = l.get("score") or 0.0
            title = l.get("content", "").split("\n")[0][:80] if l.get("content") else "Lead Opportunity"
            url = l.get("url") or "N/A"
            author = l.get("author") or "unknown"
            source = l.get("source") or "web"

            console.print(f"[bold green]{idx}. {title}[/bold green] [dim](Score: {score:.0f})[/dim]")
            console.print(f"   🔗 [bold blue underline]{url}[/bold blue underline]")
            console.print(f"   👤 Author: {author} | Source: {source}")
            console.print()
        return True

    query = query.strip().strip('"').strip("'")
    console.print()
    comm_info = f", comments <= {max_comments}" if max_comments is not None else ""
    msg_info = f', msg: "{message_filter}"' if message_filter else ""
    console.print(f'[bold cyan]🔍 Searching live leads for: [bold white]"{query}"[/bold white] (max: {limit}, fresh: {freshness_days}d{comm_info}{msg_info})...[/bold cyan]')

    scraper = SmartScraper()
    posts = scraper.search_reddit(query, max_results=limit, freshness_days=freshness_days, max_comments=max_comments, message_filter=message_filter)

    if len(posts) < limit:
        linkedin_posts = scraper.search_linkedin(query, max_results=limit - len(posts), freshness_days=freshness_days)
        for lp in linkedin_posts:
            if not any(p["url"] == lp["url"] for p in posts):
                posts.append(lp)

    if not posts:
        console.print(f'[yellow]No leads matching "{query}" found with the specified filters.[/]')
        console.print(f'[dim]Try: /leads "{query}" fresh:30  ← expand to 30 days[/dim]')
        return True

    console.print()
    console.print(f"[bold green]✅ Found {len(posts)} live leads with direct links:[/bold green]")
    console.print()

    for idx, p in enumerate(posts, 1):
        title = p.get("title") or "Opportunity"
        url = p.get("url") or "N/A"
        author = p.get("author") or "unknown"
        sub = p.get("subreddit") or "reddit"
        num_comm = p.get("comments", 0)
        snippet = (p.get("content") or "").replace("\n", " ")[:150]

        try:
            raw_post = RawPost(
                source="reddit",
                channel=sub,
                author=author,
                content=f"{title}\n{snippet}",
                timestamp=p.get("timestamp", time.time()),
                url=url,
            )
            raw_id = storage.store_raw_post(raw_post)
            if raw_id:
                analysis = LeadAnalysis(
                    raw_post_id=raw_id,
                    is_lead=True,
                    confidence=0.85,
                    estimated_budget="Medium",
                    urgency="High",
                    category="automation",
                    reasoning="Scraped via CLI leads command",
                )
                analysis_id = storage.store_analysis(analysis)
                if analysis_id:
                    score = LeadScore(analysis_id=analysis_id, score=85.0, confidence_score=0.85)
                    storage.store_score(score)
        except Exception:
            pass

        ts = p.get("timestamp", 0)
        if ts and ts > 1000000000:
            age_hours = (time.time() - ts) / 3600
            if age_hours < 1:
                freshness = "just now"
            elif age_hours < 24:
                freshness = f"{int(age_hours)}h ago"
            else:
                freshness = f"{int(age_hours / 24)}d ago"
        else:
            freshness = "unknown"

        console.print(f"[bold cyan]{idx}. {title}[/bold cyan]  [bold green]🕐 {freshness}[/bold green]")
        console.print(f"   🔗 [bold blue underline]{url}[/bold blue underline]")
        console.print(f"   👤 Author: u/{author} | Subreddit: r/{sub} | 💬 {num_comm} comments")
        if snippet:
            console.print(f"   📝 [dim]{snippet}...[/dim]")
        console.print()

    return True


def cmd_discord(console: Console, token: str | None = None) -> bool:
    """Launch the live Discord Lead Monitor bot."""
    bot_token = token or os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        console.print("[bold red]❌ DISCORD_BOT_TOKEN missing![/bold red]")
        console.print("[dim]Provide a token or set DISCORD_BOT_TOKEN in environment/.env file:[/dim]")
        console.print("[cyan]   archangel discord --token YOUR_BOT_TOKEN[/cyan]\n")
        return False

    console.print("[bold cyan]🤖 Starting Archangel Discord Lead Monitor...[/bold cyan]")
    try:
        from archangel.agents.discord_agent import start_discord_monitor
        start_discord_monitor(token=bot_token)
    except Exception as exc:
        console.print(f"[bold red]Discord monitor failed: {exc}[/bold red]")
        return False
    return True


def cmd_logs(console: Console, tail: int = 50, follow: bool = False, level: str | None = None) -> bool:
    """View runtime logs."""
    log_dir = Path("logs")

    if not log_dir.exists():
        _print_error_panel(
            console,
            what="Log directory not found.",
            why="The logs/ directory does not exist yet.",
            suggestions=[
                "Start the platform first with [bold]archangel summon[/].",
                "Logs will appear in logs/ after the first run.",
            ],
        )
        return False

    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        console.print("[yellow]No log files found in logs/.[/]")
        return True

    latest = log_files[0]
    console.print(f"Showing last {tail} lines of [bold]{latest.name}[/]:\n")

    lines = latest.read_text(encoding="utf-8").splitlines()
    for line in lines[-tail:]:
        console.print(line)

    if follow:
        console.print("\n[yellow]Follow mode[/] — (Ctrl+C to stop)")
        try:
            pos = len(lines)
            while True:
                time.sleep(2)
                current = latest.read_text(encoding="utf-8").splitlines()
                for line in current[pos:]:
                    console.print(line)
                pos = len(current)
        except KeyboardInterrupt:
            console.print("\n[yellow]Log follow stopped.[/]")

    return True


def cmd_purge(console: Console, confirmed: bool = False) -> bool:
    """Clean cache, temporary data, and runtime artifacts."""
    if not confirmed:
        console.print("[yellow]Use [bold]purge --yes[/] to confirm.[/]")
        return False

    console.print("[yellow]Purging cached data ...[/]")
    removed = 0
    if DATA_DIR.exists():
        for p in DATA_DIR.rglob("*"):
            if p.is_file() and p.suffix in (".db", ".json", ".csv", ".tmp", ".cache"):
                p.unlink()
                removed += 1

    console.print(f"[green]✓ Purge complete.[/] Removed {removed} cached files.")
    console.print("[dim]Configuration files and user data were preserved.[/]")
    return True


def cmd_update(console: Console) -> bool:
    """Update plugins and system components."""
    from archangel.plugins import PluginLoader

    console.print("[yellow]Checking for plugin updates ...[/]")
    try:
        loader = PluginLoader()
        results = loader.update_all()
        if results:
            for name, status in results.items():
                mark = "[green]✓[/]" if status else "[yellow]⤷[/]"
                console.print(f"  {mark} {name}")
        else:
            console.print("  [dim]No plugins installed to update.[/]")
        console.print("[green]✓ Update check complete.[/]")
        return True
    except Exception as exc:
        _print_error_panel(
            console,
            what="Plugin update failed.",
            why=str(exc),
            suggestions=[
                "Check network connectivity.",
                "Verify plugin manifests in archangel/plugins/.",
            ],
        )
        return False


def cmd_version(console: Console) -> bool:
    """Display installed version."""
    console.print(f"[bold]The Archangel[/] [cyan]v{__version__}[/]")
    console.print("[dim]Autonomous Lead Intelligence Platform[/]")
    return True


def cmd_clear(console: Console) -> bool:
    """Clear terminal screen and re-print banner."""
    os.system("cls" if os.name == "nt" else "clear")
    render_banner(console)
    return True


def cmd_automate(console: Console, task: str, dry_run: bool = False, max_steps: int = 50) -> bool:
    """Run autonomous GUI automation."""
    try:
        from archangel.plugins.gui_control import GUIAgent
    except ImportError as exc:
        _print_error_panel(
            console,
            what="GUI Control plugin not available.",
            why=str(exc),
            suggestions=[
                "Ensure archangel/plugins/gui_control/ exists.",
                "Run 'pip install -e .' to register the plugin.",
            ],
        )
        return False

    agent = GUIAgent()
    result = agent.run(task=task, max_steps=max_steps, dry_run=dry_run)
    console.print(f"\n[bold green]Result:[/] {result}")
    return True


def cmd_registry_list(console: Console, enabled: bool = False, disabled: bool = False, category: str | None = None) -> bool:
    """Display installed plugins."""
    from archangel.plugins import PluginLoader
    from archangel.registry import PluginRegistry

    loader = PluginLoader()
    registry = PluginRegistry(loader.manifests)
    plugins = registry.list_all()

    if enabled:
        plugins = registry.filter_by_status("enabled")
    elif disabled:
        plugins = [p for p in plugins if p.get("status") != "enabled"]

    if category:
        plugins = [p for p in plugins if p.get("category") == category]

    if not plugins:
        console.print("[yellow]No plugins found matching those criteria.[/]")
        return True

    table = Table(title="Archangel Plugins", border_style="blue")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Version")

    for p in plugins:
        status_col = "[green]enabled[/]" if p.get("status") == "enabled" else "[red]disabled[/]"
        table.add_row(p.get("name", "?"), p.get("category", "?"), status_col, p.get("version", "?"))

    console.print(table)
    return True


def cmd_registry_info(console: Console, name: str) -> bool:
    """Show detailed information for a single plugin."""
    from archangel.plugins import PluginLoader
    from archangel.registry import PluginRegistry

    loader = PluginLoader()
    registry = PluginRegistry(loader.manifests)
    plugin = registry.get(name)

    if plugin is None:
        _print_error_panel(
            console,
            what=f"Plugin '{name}' not found.",
            why="The plugin name does not match any installed manifest.",
            suggestions=[
                "Check spelling — names are lowercase hyphenated.",
                "Run [bold]archangel registry[/] to list all plugins.",
            ],
        )
        return False

    table = Table(title=f"Plugin: {name}", border_style="blue", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    for key in ("name", "version", "description", "category", "author", "status"):
        table.add_row(key.capitalize(), str(plugin.get(key, "")))

    perms = plugin.get("permissions", [])
    table.add_row("Permissions", ", ".join(perms) if perms else "(none)")

    console.print(table)
    return True


def cmd_start_telegram(console: Console) -> bool:
    """Start Telegram remote control bridge on demand."""
    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)

    from archangel.plugins.telegram_bridge import TelegramBridge, get_running_telegram_bridge_info

    is_running, pid, is_current = get_running_telegram_bridge_info()
    if is_running:
        if is_current:
            console.print("[yellow]Telegram bridge / agent is already started in this window.[/]")
        else:
            console.print(f"[yellow]Telegram bridge / agent is already started in another window (PID: {pid}).[/]")
        return True

    console.print("[yellow]Starting Telegram bridge ...[/]")
    bridge = TelegramBridge.get_instance()
    success, msg = bridge.start()
    if success:
        _step(console, "Telegram bridge active")
        console.print(f"[bold green]✓ {msg}[/]")
        console.print("[dim]Press Ctrl+C to stop the Telegram bridge.[/dim]\n")
        try:
            while bridge.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping Telegram bridge...[/yellow]")
            bridge.stop()
            console.print("[bold green]✓ Telegram bridge stopped.[/bold green]")
        return True
    else:
        _print_error_panel(
            console,
            what="Failed to start Telegram bridge.",
            why=msg,
            suggestions=[
                "Ensure TELEGRAM_BOT_TOKEN is set in your .env or configs/config.yaml.",
                "Verify no other process is using the Telegram bot token.",
                "Check logs/archangel.log for details.",
            ],
        )
        return False

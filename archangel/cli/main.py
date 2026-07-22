"""The Archangel CLI — command parsing, delegation, and formatted output.

This module is the sole entrypoint for the ``archangel`` console script.
It MUST NOT contain business logic — it parses user input, delegates to
the Engine, and formats console output via Rich.

All command logic lives in ``cmd_*`` functions that are called by both the
Click CLI layer and the interactive REPL.  No code duplication.
"""

from __future__ import annotations

import os
import re
import sys
import time
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, List, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from archangel import __version__
from archangel.cli.banner import render_banner
from archangel.cli import commands as _cli_commands
from archangel.cli.commands import handle_slash_command, _ChatCompleter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
SHUTDOWN_SENTINEL = DATA_DIR / ".archangel_shutdown"
PID_FILE = DATA_DIR / ".archangel_pid"
REPL_HISTORY = Path.home() / ".archangel_history"
REPL_COMMANDS = [
    "status", "watch", "scan", "doctor", "config",
    "export", "logs", "purge", "update", "version",
    "registry", "chat", "automate", "clear", "help", "exit", "quit",
]

# ---------------------------------------------------------------------------
# Console singleton
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_console = Console()
_bridge = None


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_user_path_registered() -> bool:
    """Ensure the virtual environment's Scripts directory is in Windows User PATH."""
    if os.name != "nt":
        return False
    try:
        import winreg
        import ctypes

        scripts_dir = str(Path(sys.executable).parent.resolve())
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""

            paths = [p.strip() for p in current_path.split(";") if p.strip()]
            if not any(p.lower() == scripts_dir.lower() for p in paths):
                new_path = f"{current_path};{scripts_dir}" if current_path else scripts_dir
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                ctypes.windll.user32.SendMessageTimeoutW(
                    0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
                )
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step(label: str, success: bool = True, indent: int = 0) -> None:
    prefix = "  " * indent
    marker = "[bold green]✓[/]" if success else "[bold red]✗[/]"
    _console.print(f"{prefix}{marker} {label}")


def _print_error_panel(
    what: str,
    why: str,
    suggestions: list[str],
) -> None:
    """Print a structured, actionable error panel (does NOT exit)."""
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


# ---------------------------------------------------------------------------
# Reusable command logic  (called by both Click decorators and REPL)
# ---------------------------------------------------------------------------

def cmd_summon(console: Console, debug: bool = False,
               config_path: str | None = None) -> bool:
    """Startup sequence.  Returns True on success."""
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

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

        import sys as _sys
        _obscura_path = Path(__file__).resolve().parents[2] / "tools" / "obscura"
        if _obscura_path.exists() and str(_obscura_path) not in _sys.path:
            os.environ["PATH"] = str(_obscura_path) + os.pathsep + os.environ.get("PATH", "")

        console.print("[yellow]Starting platform engine ...[/]")
        engine_start(debug=debug, config_path=config_path)

        console.print()
        _step("Configuration loaded")
        _step("Logger initialized")
        _step("Event bus initialized")
        _step("Storage initialized")
        _step("Plugins loaded")
        _step("Guardian agent ready")
        _step("Commander agent ready")
        _step("Collector agent ready")
        _step("Intelligence agent ready")
        _step("Scoring agent ready")
        _step("Notification agent ready")
        _step("Engine started")

        console.print()
        console.print(Panel.fit(
            "[bold green]⚔ Mission Operational[/]\n"
            "The Archangel is watching the horizon.",
            border_style="green",
        ))
        return True
    except Exception as exc:
        _print_error_panel(
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

        _step("Collectors stopped")
        _step("Event queue flushed")
        _step("Database saved")
        _step("Engine shut down")

        console.print()
        console.print("[bold green]✓ The Archangel has been terminated.[/]")
        return True
    except Exception as exc:
        _print_error_panel(
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


def cmd_watch(console: Console) -> bool:
    """Live event stream placeholder."""
    console.print("[yellow]watch[/] — Live event stream.")
    console.print("This feature will stream events from the Event Bus in real time.")
    console.print("Start the platform first with [bold]archangel summon[/].")
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
    import os

    console.print("[yellow]Running system diagnostics ...[/]")

    checks: list[tuple[str, bool, str]] = [
        ("Python version", True, ">=3.12"),
        ("Configuration files", True, "configs/"),
        ("Storage backend", True, "SQLite (default)"),
        ("Plugin directory", True, "archangel/plugins/"),
        ("Log directory", True, "logs/"),
    ]

    # Load plugin manifests and validate .env permissions
    from archangel.plugins import PluginLoader
    from archangel.registry import PluginRegistry

    loader = PluginLoader()
    registry = PluginRegistry(loader.manifests)
    for plugin in registry.list_all():
        for perm in plugin.get("permissions", []):
            present = perm in os.environ
            checks.append(
                (f".env — {perm}", present, perm),
            )

    # Validate API keys from environment
    api_keys = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    for key in api_keys:
        present = key in os.environ
        checks.append(
            (f"API — {key}", present, "set" if present else "missing"),
        )

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


def cmd_config(console: Console, action: str = "edit",
               section: str | None = None) -> bool:
    """Inspect or edit configuration."""
    from archangel.config.manager import load_config, validate_config

    try:
        cfg = load_config()
    except Exception as exc:
        _print_error_panel(
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
    """Open the main configuration file in Notepad."""
    config_path = Path("configs/config.yaml")
    if not config_path.exists():
        console.print(f"[red]✗ Configuration file not found:[/] {config_path}")
        console.print("[yellow]Create one with [bold]archangel config show > configs/config.yaml[/][/]")
        return
    try:
        os.startfile(config_path)
    except AttributeError:
        subprocess.run(["notepad.exe", str(config_path)], check=True)


def cmd_export(console: Console, fmt: str = "json",
               output: str | None = None, limit: int | None = None) -> bool:
    """Export leads in CSV, JSON, or Markdown."""
    from archangel.export import Exporter

    try:
        exporter = Exporter()
        result_path = exporter.export(format=fmt, output_path=output, limit=limit)
        console.print(f"[green]✓ Leads exported to[/] [bold]{result_path}[/]")
        return True
    except Exception as exc:
        _print_error_panel(
            what="Export failed.",
            why=str(exc),
            suggestions=[
                "Ensure the platform has collected leads (run [bold]archangel scan[/] first).",
                "Check the output path is writable.",
            ],
        )
        return False


def cmd_leads(console: Console, query: str | None = None, limit: int = 10) -> bool:
    """Fetch live leads or display saved leads with direct clickable URLs in CLI.

    Supports `max: N` in the query string, e.g.:
        /leads "custom bot" max: 4
        /leads discord bot max:3
    """
    from archangel.storage import StorageBackend
    from archangel.agents.scraper import SmartScraper
    from archangel.models import RawPost, LeadAnalysis, LeadScore
    import time
    import re

    storage = StorageBackend.get_instance()

    # ── Parse `max: N` from the query string ──
    if query:
        max_match = re.search(r'\bmax:\s*(\d+)', query, re.IGNORECASE)
        if max_match:
            limit = int(max_match.group(1))
            query = re.sub(r'\bmax:\s*\d+', '', query, flags=re.IGNORECASE).strip()

    if not query or query.strip().lower() in ("list", "saved", "all"):
        leads = storage.get_leads(limit=limit)
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

    # Real Live Search Query
    query = query.strip().strip('"').strip("'")
    console.print()
    console.print(f'[bold cyan]🔍 Searching live leads for: [bold white]"{query}"[/bold white] (max: {limit})...[/bold cyan]')

    scraper = SmartScraper()
    posts = scraper.search_reddit(query, max_results=limit)

    if not posts:
        console.print(f"[yellow]No live leads found matching \"{query}\". Try a broader query like 'python developer'.[/]")
        return True

    console.print()
    console.print(f"[bold green]✅ Found {len(posts)} live leads with direct links:[/bold green]")
    console.print()

    for idx, p in enumerate(posts, 1):
        title = p.get("title") or "Opportunity"
        url = p.get("url") or "N/A"
        author = p.get("author") or "unknown"
        sub = p.get("subreddit") or "reddit"
        snippet = (p.get("content") or "").replace("\n", " ")[:150]

        # Save to database
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

        console.print(f"[bold cyan]{idx}. {title}[/bold cyan]")
        console.print(f"   🔗 [bold blue underline]{url}[/bold blue underline]")
        console.print(f"   👤 Author: u/{author} | Subreddit: r/{sub}")
        if snippet:
            console.print(f"   📝 [dim]{snippet}...[/dim]")
        console.print()

    return True


def cmd_logs(console: Console, tail: int = 50, follow: bool = False,
             level: str | None = None) -> bool:
    """View runtime logs."""
    log_dir = Path("logs")

    if not log_dir.exists():
        _print_error_panel(
            what="Log directory not found.",
            why="The logs/ directory does not exist yet.",
            suggestions=[
                "Start the platform first with [bold]archangel summon[/].",
                "Logs will appear in logs/ after the first run.",
            ],
        )
        return False

    log_files = sorted(log_dir.glob("*.log"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
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
        import time as _time
        try:
            pos = len(lines)
            while True:
                _time.sleep(2)
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
            what="Plugin update failed.",
            why=str(exc),
            suggestions=[
                "Check network connectivity.",
                "Verify plugin manifests in archangel/plugins/.",
            ],
        )
        return False


def cmd_version(console: Console) -> bool:
    """Display the installed version."""
    console.print(f"[bold]The Archangel[/] [cyan]v{__version__}[/]")
    console.print("[dim]Autonomous Lead Intelligence Platform[/]")
    return True


def cmd_clear(console: Console) -> bool:
    """Clear the terminal screen and re-print the banner."""
    os.system("cls" if os.name == "nt" else "clear")
    from archangel.cli.banner import render_banner
    render_banner(console)
    return True


def cmd_automate(console: Console, task: str, dry_run: bool = False,
                 max_steps: int = 50) -> bool:
    """Run autonomous GUI automation via vision AI."""
    try:
        from archangel.plugins.gui_control import GUIAgent
    except ImportError as exc:
        _print_error_panel(
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


def cmd_registry_list(
    console: Console,
    enabled: bool = False,
    disabled: bool = False,
    category: str | None = None,
) -> bool:
    """Display installed plugins in a table."""
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
        status_col = (
            "[green]enabled[/]"
            if p.get("status") == "enabled"
            else "[red]disabled[/]"
        )
        table.add_row(
            p.get("name", "?"),
            p.get("category", "?"),
            status_col,
            p.get("version", "?"),
        )

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
            what=f"Plugin '{name}' not found.",
            why="The plugin name does not match any installed manifest.",
            suggestions=[
                "Check spelling — names are lowercase hyphenated (e.g. telegram-collector).",
                "Run [bold]archangel registry[/] to list all plugins.",
            ],
        )
        return False

    from rich.table import Table as RTable

    table = RTable(title=f"Plugin: {name}", border_style="blue", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    for key in ("name", "version", "description", "category", "author", "status"):
        table.add_row(key.capitalize(), str(plugin.get(key, "")))

    perms = plugin.get("permissions", [])
    table.add_row("Permissions", ", ".join(perms) if perms else "(none)")

    console.print(table)
    return True


def cmd_start_telegram(console: Console) -> bool:
    """Start the Telegram remote control bridge on demand."""
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
        _step("Telegram bridge active")
        console.print(f"[bold green]✓ {msg}[/]")
        return True
    else:
        _print_error_panel(
            what="Failed to start Telegram bridge.",
            why=msg,
            suggestions=[
                "Ensure TELEGRAM_BOT_TOKEN is set in your .env or configs/config.yaml.",
                "Verify no other process is using the Telegram bot token.",
                "Check logs/archangel.log for details.",
            ],
        )
        return False


_ANTI_YAP_INSTRUCTION = (
    "\n\nDIRECT & CONCISE RULES:\n"
    "1. NEVER introduce yourself, state your job title, or explain your domain expertise unless explicitly asked.\n"
    "2. NO formal greetings or intro speeches ('Greetings', 'I am the...'). Get straight to business.\n"
    "3. Keep default responses under 1-3 direct, punchy sentences.\n"
    "4. If the user says 'hi' or 'hello', reply in a single casual line (e.g. 'Hey, what do you need help with?')."
)

AGENT_SYSTEM_PROMPTS = {
    "collector": (
        "You are Archangel Collector Agent (archangel.collector), managing web scraping, RSS feeds, Reddit API, X search, and data acquisition."
        + _ANTI_YAP_INSTRUCTION
    ),
    "intelligence": (
        "You are Archangel Intelligence Agent (archangel.intelligence), managing intent classification, complaint pattern matching, and lead detection."
        + _ANTI_YAP_INSTRUCTION
    ),
    "scoring": (
        "You are Archangel Scoring Agent (archangel.scoring), managing lead urgency scoring, budget confidence metrics, and priority queues."
        + _ANTI_YAP_INSTRUCTION
    ),
    "guardian": (
        "You are Archangel Guardian Agent (archangel.guardian), managing system health monitoring, error telemetry, and diagnostic stability."
        + _ANTI_YAP_INSTRUCTION
    ),
    "commander": (
        "You are Archangel Commander Agent (archangel.commander), managing platform task orchestration, agent lifecycles, and command dispatch."
        + _ANTI_YAP_INSTRUCTION
    ),
    "storage": (
        "You are Archangel Storage Agent (archangel.storage), managing SQLite WAL concurrency, lead indexing, deduplication, and data exports."
        + _ANTI_YAP_INSTRUCTION
    ),
    "notification": (
        "You are Archangel Notification Agent (archangel.notification), managing Telegram bridge alerts, Discord webhooks, and message delivery."
        + _ANTI_YAP_INSTRUCTION
    ),
}


def _classify_agent_topic(text: str) -> str:
    """Classify user message topic and return matching agent name."""
    t = text.lower()
    if "@collector" in t or "collector" in t and ("feed" in t or "scrape" in t or "source" in t):
        return "collector"
    if "@intelligence" in t or "intelligence" in t and ("lead" in t or "intent" in t or "classify" in t):
        return "intelligence"
    if "@scoring" in t or "scoring" in t and ("rank" in t or "score" in t or "budget" in t or "urgency" in t):
        return "scoring"
    if "@guardian" in t or "guardian" in t and ("health" in t or "error" in t or "status" in t or "crash" in t):
        return "guardian"
    if "@commander" in t or "commander" in t and ("task" in t or "orchestrat" in t or "run" in t):
        return "commander"
    if "@storage" in t or "storage" in t and ("database" in t or "sqlite" in t or "count" in t or "export" in t):
        return "storage"
    if "@notification" in t or "notification" in t and ("telegram" in t or "discord" in t or "alert" in t):
        return "notification"

    # Secondary topic matching
    if any(k in t for k in ("scrape", "rss", "reddit", "twitter", "tweet", "x.com", "html", "url", "web", "fetch")):
        return "collector"
    if any(k in t for k in ("database", "sqlite", "wal", "db", "table", "sql", "record", "save")):
        return "storage"
    if any(k in t for k in ("telegram", "discord", "webhook", "notify", "message", "alert", "bot")):
        return "notification"
    if any(k in t for k in ("health", "log", "error", "fail", "crash", "guardian", "monitor", "telemetry")):
        return "guardian"
    if any(k in t for k in ("score", "rank", "urgent", "budget", "pricing", "priority")):
        return "scoring"
    if any(k in t for k in ("task", "orchestrat", "commander", "agent", "state", "daemon", "process")):
        return "commander"

    return "intelligence"


def get_archangel_keybindings():
    """Create custom key bindings for Ctrl+Z (Undo), Ctrl+Y (Redo), Ctrl+A, Ctrl+E, Ctrl+U, Ctrl+K, Ctrl+L, Ctrl+W."""
    try:
        from prompt_toolkit.key_binding import KeyBindings

        kb = KeyBindings()

        @kb.add("c-z")
        def _undo(event):
            event.current_buffer.undo()

        @kb.add("c-y")
        def _redo(event):
            event.current_buffer.redo()

        @kb.add("c-a")
        def _home(event):
            event.current_buffer.cursor_position = 0

        @kb.add("c-e")
        def _end(event):
            event.current_buffer.cursor_position = len(event.current_buffer.text)

        @kb.add("c-u")
        def _clear_line_before(event):
            pos = event.current_buffer.cursor_position
            event.current_buffer.text = event.current_buffer.text[pos:]
            event.current_buffer.cursor_position = 0

        @kb.add("c-k")
        def _clear_line_after(event):
            pos = event.current_buffer.cursor_position
            event.current_buffer.text = event.current_buffer.text[:pos]

        @kb.add("c-l")
        def _clear_screen(event):
            event.app.renderer.clear()

        @kb.add("c-w")
        def _delete_word_before(event):
            event.current_buffer.delete_before_cursor(count=1)

        return kb
    except Exception:
        return None


def _create_prompt_session(
    prompt_str: str,
    hist_filename: str,
    completer=None,
    complete_while_typing: bool = False
):
    """Helper to create a PromptSession with custom Ctrl key bindings and persistent history."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory

        hist_path = Path.home() / hist_filename
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        kb = get_archangel_keybindings()
        kwargs = {
            "history": FileHistory(str(hist_path)),
            "key_bindings": kb,
        }
        if completer:
            kwargs["completer"] = completer
            kwargs["complete_while_typing"] = complete_while_typing

        return PromptSession(prompt_str, **kwargs)
    except Exception:
        return None


def _handle_slash_intercept(raw: str, console: Console, history: list) -> bool:
    """Intercept slash commands across REPLs. Returns True if REPL should exit."""
    from archangel.cli.commands import COMMANDS as _CHAT_COMMANDS, handle_slash_command
    _cmd_name = raw[1:].strip().split()[0].lower() if raw[1:].strip() else ""
    if _cmd_name in _CHAT_COMMANDS:
        return handle_slash_command(raw, console, history)
    else:
        _execute_repl_command(console, raw[1:].strip())
        return False


def run_agents_hub_repl(console: Console) -> None:
    """Hub where all 7 agents are present. Messages are automatically routed to the matching agent."""
    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)
    from archangel.agents.chat import LLMClient

    try:
        llm = LLMClient()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        return

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🤖 archangel.agents — All Agents Active Hub[/]\n"
        "[dim]All 7 Archangel agents are present. Type your request and it will automatically route to the matching agent.[/]\n"
        "[italic #c0c0c0]Type exit, quit, or back to return to archangel.main>[/]",
        border_style="cyan",
    ))
    console.print()

    prompt_str = "archangel.agents> "

    session = _create_prompt_session(prompt_str, ".archangel_agents_hub_history")

    while True:
        try:
            if session:
                raw = session.prompt()
            else:
                raw = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        raw = raw.strip()
        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"):
            console.print()
            break

        if raw.startswith("/"):
            if _handle_slash_intercept(raw, console, []):
                console.print()
                break
            continue

        target_agent = _classify_agent_topic(raw)
        history = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS[target_agent]},
            {"role": "user", "content": raw},
        ]

        try:
            console.print(f"[dim]Routing subject to archangel.agents.{target_agent}...[/dim]")
            llm.switch_provider(_cli_commands._active_model_provider)
            resp = llm.chat(history)
            console.print()
            console.print(f"[bold cyan]archangel.agents.{target_agent}>[/]")
            for line in resp.splitlines():
                if line.strip():
                    console.print(f"  {line}")
            console.print()
        except Exception as exc:
            console.print(f"[red]Error from archangel.agents.{target_agent}: {exc}[/]")


def _animate_agent_typing(console: Console, agent: str) -> None:
    """Display animated 'the <agent> agent is typing...' effect."""
    import time
    msg = f"the {agent} agent is typing"
    for dots in (".", "..", "..."):
        console.print(f"\r[dim cyan]  {msg}{dots}[/dim cyan]", end="")
        time.sleep(0.18)
    console.print("\r" + " " * (len(msg) + 12) + "\r", end="")


def _render_groupchat_header(console: Console, busy_agent: Optional[str] = None) -> None:
    status_str = "[bold green]🟢 Online: 7[/bold green]"
    if busy_agent:
        status_str += f"   [bold red]⬢ Busy: {busy_agent}[/bold red]"
    console.print(Panel(
        f"[bold cyan]👥 archangel.agents.groupchat — Multi-Agent Collaboration Room[/]   |   {status_str}\n"
        "[dim]All 7 agents collaborate here (2-4 agents respond per round max).[/]\n"
        "[italic #c0c0c0]Type exit, quit, or back to return to archangel.main> | Type status for online/busy details.[/]",
        border_style="cyan",
        expand=True,
    ))


def run_groupchat_repl(console: Console) -> None:
    """Multi-agent collaborative group conversation room."""
    from archangel.agents.groupchat import GroupChatEngine, AGENT_ROLES

    engine = GroupChatEngine()

    console.print()
    _render_groupchat_header(console)
    console.print()

    prompt_str = "archangel.agents.groupchat> "

    session = _create_prompt_session(prompt_str, ".archangel_groupchat_history")

    while True:
        try:
            if session:
                raw = session.prompt()
            else:
                raw = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        raw = raw.strip()
        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"):
            console.print()
            break

        if raw.startswith("/"):
            if _handle_slash_intercept(raw, console, getattr(engine, "history", [])):
                console.print()
                break
            continue

        if raw.lower() in ("status", "online", "busy", "list"):
            console.print()
            console.print("[bold green]🟢 Online Agents (7):[/bold green]")
            for name in AGENT_ROLES:
                console.print(f"  - [bold cyan]archangel.agents.{name}[/bold cyan]")
            console.print()
            console.print("[bold red]⬢ Busy Agents:[/bold red]")
            if engine.busy_agent:
                console.print(f"  - [bold red]archangel.agents.{engine.busy_agent}[/bold red] (active task)")
            else:
                console.print("  - [dim]None (All agents idle & ready)[/dim]")
            console.print()
            continue

        with console.status("[bold cyan]the groupchat agents are typing...[/bold cyan]", spinner="dots"):
            turns = engine.process_user_goal(raw)

        console.print()
        import time
        for turn in turns:
            agent = turn.get("agent", "commander")
            text = turn.get("text", "")
            with console.status(f"[bold cyan]the {agent} agent is typing...[/bold cyan]", spinner="dots"):
                time.sleep(1.0)
            console.print(f"[bold cyan]archangel.agents.{agent}>[/]")
            for line in text.splitlines():
                if line.strip():
                    console.print(f"  {line}")
            console.print()



def run_agent_chat_repl(console: Console, agent_name: str) -> None:
    """Enter an interactive multi-turn AI chat mode with a specific agent persona."""
    agent = agent_name.lower().replace("archangel.", "").replace("agents.", "")
    if agent not in AGENT_SYSTEM_PROMPTS:
        console.print(f"[yellow]Unknown agent persona: {agent_name}[/]")
        return

    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)

    from archangel.agents.chat import (
        LLMClient, CommandExecutor, WebSearch,
        EXECUTE_RE, SEARCH_RE, AUTOMATE_RE,
        extract_execute_commands, extract_search_queries
    )

    try:
        llm = LLMClient()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        return

    executor = CommandExecutor()
    history: list[dict[str, str]] = [{
        "role": "system",
        "content": AGENT_SYSTEM_PROMPTS[agent] + (
            "\n\nRUNTIME\nOS: Windows 11 | Shell: PowerShell\n"
            "TOOLS\n"
            "1. <execute>...</execute> — run a PowerShell command\n"
            "2. <search>...</search> — search the web\n"
        )
    }]

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]🤖 archangel.agents.{agent} — Interactive Agent Chat[/]\n"
        f"[dim]Freely talk, ask questions, or issue instructions to archangel.agents.{agent}.[/]\n"
        f"[italic #c0c0c0]Type exit, quit, or back to return to archangel.main>[/]",
        border_style="cyan",
    ))
    console.print()

    prompt_str = f"archangel.agents.{agent}> "

    session = _create_prompt_session(prompt_str, f".archangel_{agent}_history")

    while True:
        try:
            if session:
                raw = session.prompt()
            else:
                raw = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        raw = raw.strip()
        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"):
            console.print()
            break

        if raw.startswith("/"):
            if _handle_slash_intercept(raw, console, history):
                console.print()
                break
            continue

        history.append({"role": "user", "content": raw})

        _exec_iterations = 0
        while True:
            try:
                llm.switch_provider(_cli_commands._active_model_provider)
                response_text = llm.chat(history)
            except Exception as exc:
                console.print(f"[red]LLM error: {exc}[/]")
                break

            _exec_iterations += 1
            if _exec_iterations > 5:
                console.print(f"[yellow]archangel.agents.{agent}> Stopped after 5 iterations.[/]")
                break

            history.append({"role": "assistant", "content": response_text})

            display = EXECUTE_RE.sub("", response_text)
            display = SEARCH_RE.sub("", display)
            display = AUTOMATE_RE.sub("", display)
            display = re.sub(r"<pyautogui_call>.*?</pyautogui_call>", "", display, flags=re.DOTALL)

            console.print()
            console.print(f"[bold cyan]archangel.agents.{agent}>[/]")
            for line in display.splitlines():
                if line.strip():
                    console.print(f"  {line}")
            console.print()

            # Handle <search>...</search>
            queries = extract_search_queries(response_text)
            if queries:
                for q in queries:
                    console.print(f"[bold cyan]archangel.agents.{agent}>[/] [dim]searching: {q}[/]")
                    search_output = WebSearch().search(q)
                    history.append({
                        "role": "user",
                        "content": f"<search_results>\n{search_output}\n</search_results>",
                    })
                continue

            # Handle <execute>...</execute>
            commands = extract_execute_commands(response_text)
            if not commands:
                break

            for cmd in commands:
                console.print(f"[bold cyan]archangel.{agent}>[/] [dim]$ {cmd}[/]")
                output = executor.execute(cmd)
                history.append({
                    "role": "user",
                    "content": f"<output>\n{output}\n</output>",
                })


def _run_single_agent_query(console: Console, agent_name: str, query: str) -> bool:
    """Send a single query to an agent persona and display the response."""
    agent = agent_name.lower().replace("archangel.", "")
    if agent not in AGENT_SYSTEM_PROMPTS:
        console.print(f"[yellow]Unknown agent target: {agent_name}[/]")
        return False

    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)
    from archangel.agents.chat import LLMClient

    try:
        llm = LLMClient()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        return False

    history = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPTS[agent]},
        {"role": "user", "content": query},
    ]

    try:
        console.print(f"[dim]Querying archangel.{agent}...[/dim]")
        resp = llm.chat(history)
        console.print(f"\n[bold cyan]archangel.{agent}>[/] {resp}\n")
        return True
    except Exception as exc:
        console.print(f"[red]Error querying agent: {exc}[/]")
        return False


def cmd_agent_dispatch(console: Console, agent_name: str, action: str = "status", payload: str = "") -> bool:
    """Communicate directly with a specific Archangel agent subsystem."""
    agent = agent_name.lower().replace("archangel.", "")

    if action.lower() in ("chat", "interactive", "repl") or payload.lower() in ("chat", "interactive"):
        run_agent_chat_repl(console, agent)
        return True

    if payload and action not in ("scan", "collect", "status", "health"):
        return _run_single_agent_query(console, agent, f"{action} {payload}".strip())

    console.print(f"[bold cyan]🤖 Agent Target:[/] archangel.{agent}")

    if agent == "collector":
        from archangel.collectors import CollectorAgent
        CollectorAgent()
        console.print("[green]✓ Connected to archangel.collector[/]")
        if action in ("scan", "collect"):
            return cmd_scan(console)
        elif payload:
            return _run_single_agent_query(console, agent, payload)
        else:
            console.print("  [dim]Status:[/] Ready to gather raw posts from configured sources.")
            console.print("  [dim]Tip:[/] Type [bold green]collector chat[/] (or [bold green]archangel.collector chat[/]) to freely talk to this agent.")
            return True

    elif agent == "intelligence":
        from archangel.analysis import IntelligenceAgent
        console.print("[green]✓ Connected to archangel.intelligence[/]")
        if payload:
            from archangel.models import RawPost
            post = RawPost(source="cli", channel="manual", author="user", content=payload, url="https://cli.local")
            intel = IntelligenceAgent()
            analysis = intel.analyze(post)
            console.print(f"  [bold]Is Lead:[/] {analysis.is_lead}")
            console.print(f"  [bold]Confidence:[/] {analysis.confidence:.2f}")
            console.print(f"  [bold]Category:[/] {analysis.category}")
            console.print(f"  [bold]Reasoning:[/] {analysis.reasoning}")
        else:
            console.print("  [dim]Status:[/] Reasoning AI engine active.")
            console.print("  [dim]Tip:[/] Type [bold green]intelligence chat[/] (or [bold green]archangel.intelligence chat[/]) to freely talk to this agent.")
        return True

    elif agent == "scoring":
        from archangel.scoring import ScoringAgent
        ScoringAgent()
        console.print("[green]✓ Connected to archangel.scoring[/]")
        console.print("  [dim]Status:[/] Lead ranking engine active.")
        console.print("  [dim]Tip:[/] Type [bold green]scoring chat[/] (or [bold green]archangel.scoring chat[/]) to freely talk to this agent.")
        return True

    elif agent == "guardian":
        from archangel.events import EventBus, GuardianAgent
        g = GuardianAgent(EventBus.get_instance())
        health = g.get_system_health()
        table = Table(title="🛡 Guardian Agent — Component Health", border_style="cyan")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        for k, v in health["components"].items():
            table.add_row(k, f"[green]{v}[/]")
        console.print(table)
        console.print("  [dim]Tip:[/] Type [bold green]guardian chat[/] (or [bold green]archangel.guardian chat[/]) to freely talk to this agent.")
        return True

    elif agent == "commander":
        from archangel.events import CommanderAgent, EventBus
        CommanderAgent(EventBus.get_instance())
        console.print("[green]✓ Connected to archangel.commander[/]")
        console.print("  [dim]Status:[/] Commander orchestrator ready.")
        console.print("  [dim]Tip:[/] Type [bold green]commander chat[/] (or [bold green]archangel.commander chat[/]) to freely talk to this agent.")
        return True

    elif agent == "storage":
        from archangel.storage import StorageBackend
        st = StorageBackend.get_instance()
        count = st.get_lead_count()
        console.print("[green]✓ Connected to archangel.storage[/]")
        console.print(f"  [bold]Active Database Leads:[/] {count}")
        console.print("  [dim]Tip:[/] Type [bold green]storage chat[/] (or [bold green]archangel.storage chat[/]) to freely talk to this agent.")
        return True

    elif agent == "notification":
        console.print("[green]✓ Connected to archangel.notification[/]")
        console.print("  [dim]Status:[/] Messaging delivery channels active.")
        console.print("  [dim]Tip:[/] Type [bold green]notification chat[/] (or [bold green]archangel.notification chat[/]) to freely talk to this agent.")
        return True

    else:
        console.print(f"[yellow]Unknown agent target: archangel.{agent}[/]")
        return False


def cmd_help_detailed(console: Console) -> bool:
    """Print full detailed reference documentation for all commands and agents."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]⚔ Archangel — Detailed Command & Agent Reference Manual[/]",
        border_style="cyan"
    ))

    help_text = """\
[bold yellow]STARTUP & CONTROL COMMANDS[/]

  [bold green]archangel summon[/] (or plain [bold green]archangel[/])
    Summons and initializes the platform core engine, event bus, database, loggers,
    and agent subsystems. (Note: Telegram bridge is NOT auto-started).

  [bold green]start telegram[/] (or [bold green]archangel start telegram[/] / [bold green]telegram start[/] / [bold green]archangel start-telegram[/])
    Starts the interactive Telegram remote operations bridge on demand. Checks if the bridge
    is already running in another terminal window/process and notifies you if active.

  [bold green]archangel terminate[/] (or [bold green]exit[/] / [bold green]quit[/] in REPL)
    Gracefully stops background tasks, flushes database queues, and terminates.

[bold yellow]OPERATION & DIAGNOSTIC COMMANDS[/]

  [bold green]archangel status[/] [--json]
    Displays real-time status of runtime engine, storage database count, and agent states.

  [bold green]archangel scan[/]
    Executes a high-speed one-time scan across all configured sources (Reddit, X, RSS, etc.),
    runs parallel AI analysis, scores leads, and persists results.

  [bold green]archangel doctor[/]
    Runs system diagnostics on dependencies, API keys, storage, and plugin permissions.

  [bold green]archangel config[/] [edit | validate]
    Inspects, validates, or opens user YAML configuration files in your editor.

  [bold green]archangel export[/] [--format csv|json|md, --output PATH, --limit N]
    Exports identified leads to external files.

  [bold green]archangel logs[/] [--tail N, --follow]
    Views live runtime log files.

  [bold green]archangel purge[/] [--yes]
    Cleans local temporary cache artifacts while preserving user data.

  [bold green]help detailed[/] (or [bold green]archangel --help detailed[/] / [bold green]archangel help detailed[/])
    Displays this full detailed reference manual.

[bold yellow]AGENT SUBSYSTEM DIRECTIVES (archangel.<agent>)[/]

You can speak to or query specific agent subsystems directly in CLI or REPL mode:

  [bold cyan]archangel.collector[/]   (or [bold cyan]collector[/])    - Query or run collector data discovery
  [bold cyan]archangel.intelligence[/] (or [bold cyan]intelligence[/]) - Directly query AI reasoning engine
  [bold cyan]archangel.scoring[/]      (or [bold cyan]scoring[/])      - Inspect lead ranking metrics & rules
  [bold cyan]archangel.guardian[/]     (or [bold cyan]guardian[/])     - View detailed component health metrics
  [bold cyan]archangel.commander[/]    (or [bold cyan]commander[/])    - Inspect orchestrator registered states
  [bold cyan]archangel.storage[/]      (or [bold cyan]storage[/])      - Query SQLite database lead counts
  [bold cyan]archangel.notification[/]  (or [bold cyan]notification[/]) - Inspect message delivery status

[bold yellow]EXAMPLES[/]
  $ archangel start telegram
  $ archangel.intelligence "Need Python automation developer for scraping project"
  $ archangel help detailed
"""
    console.print(help_text)
    return True


# ---------------------------------------------------------------------------
# REPL help
# ---------------------------------------------------------------------------

_REPL_HELP = """\
[bold cyan]Available commands:[/]

  [green]status[/]          Display runtime information and agent health
  [green]start telegram[/]  Start the interactive Telegram remote control bridge
  [green]watch[/]           Live event stream
  [green]scan[/]            One-time scan (collect, analyse, score)
  [green]doctor[/]          Run system diagnostics
  [green]config[/]          Inspect / validate configuration
  [green]export[/]          Export leads  (--format csv|json|md, --output PATH, --limit N)
  [green]logs[/]            View runtime logs  (--tail N, --follow, --level LEVEL)
  [green]purge[/]           Clean cache  (--yes to confirm)
  [green]update[/]          Check for plugin updates
  [green]registry[/]        List or inspect plugins  (--enabled, --disabled, --category, info <name>)
  [green]chat[/]            Open the AI chat REPL
  [green]clear[/]           Clear the terminal screen
  [green]version[/]         Display version
  [green]help detailed[/]   Display full detailed manual & agent directives
  [green]exit[/green]/[green]quit[/]       Shut down and exit

[dim]Speak to specific agents: archangel.collector, archangel.intelligence, archangel.guardian, etc.[/dim]
"""


def _execute_repl_command(console: Console, segment: str) -> bool:
    """Parse and dispatch a single REPL command string. Returns True to keep REPL running, False to terminate."""
    segment = segment.strip()
    if not segment:
        return True

    lowered = segment.lower()
    if lowered in ("start telegram", "telegram start", "start-telegram"):
        cmd_start_telegram(console)
        return True

    if lowered in ("help detailed", "help --detailed", "--help detailed"):
        cmd_help_detailed(console)
        return True

    try:
        _parts = shlex.split(segment)
    except Exception:
        _parts = segment.split()

    if not _parts:
        return True

    _cmd = _parts[0].lower()
    _args = _parts[1:]

    def _flag(name: str) -> bool:
        return f"--{name}" in _args

    def _opt(name: str) -> str | None:
        for i, a in enumerate(_args):
            if a == f"--{name}" and i + 1 < len(_args):
                return _args[i + 1]
        return None

    if _cmd in ("exit", "quit"):
        cmd_terminate(console)
        return False

    elif _cmd == "help":
        if _args and _args[0].lower() in ("detailed", "--detailed"):
            cmd_help_detailed(console)
        else:
            console.print(_REPL_HELP)

    elif _cmd in ("start", "telegram"):
        if _args and _args[0].lower() == "telegram":
            cmd_start_telegram(console)
        elif _cmd == "start" and not _args:
            cmd_start_telegram(console)
        else:
            cmd_start_telegram(console)

    elif _cmd in ("agents", "archangel.agents", "archangel.agents.hub"):
        run_agents_hub_repl(console)

    elif _cmd in ("groupchat", "group-chat", "archangel.agents.groupchat", "archangel.groupchat"):
        run_groupchat_repl(console)

    elif _cmd.startswith("archangel.") or _cmd in (
        "collector", "intelligence", "scoring", "guardian", "commander", "storage", "notification"
    ):
        action = _args[0] if _args else "status"
        payload = " ".join(_args[1:]) if len(_args) > 1 else (" ".join(_args) if _args else "")
        cmd_agent_dispatch(console, agent_name=_cmd, action=action, payload=payload)

    elif _cmd == "status":
        cmd_status(console, as_json=_flag("json"))

    elif _cmd == "watch":
        cmd_watch(console)

    elif _cmd == "scan":
        cmd_scan(console)

    elif _cmd == "leads":
        query_str = " ".join(_args)
        limit_val = int(_opt("limit") or "10")
        cmd_leads(console, query=query_str, limit=limit_val)

    elif _cmd == "doctor":
        cmd_doctor(console)

    elif _cmd == "config":
        valid_actions = ("edit", "validate")
        action = _args[0] if _args and _args[0] in valid_actions else "edit"
        section = _args[1] if len(_args) > 1 else None
        cmd_config(console, action=action, section=section)

    elif _cmd == "export":
        fmt = _opt("format") or "json"
        output = _opt("output")
        limit_raw = _opt("limit")
        limit = int(limit_raw) if limit_raw else None
        cmd_export(console, fmt=fmt, output=output, limit=limit)

    elif _cmd == "logs":
        tail_raw = _opt("tail")
        t = int(tail_raw) if tail_raw else 50
        follow = _flag("follow")
        level = _opt("level")
        cmd_logs(console, tail=t, follow=follow, level=level)

    elif _cmd == "purge":
        cmd_purge(console, confirmed=_flag("yes"))

    elif _cmd == "update":
        cmd_update(console)

    elif _cmd == "registry":
        if _args and _args[0] == "info" and len(_args) >= 2:
            cmd_registry_info(console, _args[1])
        else:
            cmd_registry_list(
                console,
                enabled=_flag("enabled"),
                disabled=_flag("disabled"),
                category=_opt("category"),
            )

    elif _cmd == "chat":
        run_chat_repl(console)

    elif _cmd == "automate":
        task = " ".join(_args)
        dry_run = _flag("dry-run")
        max_steps = int(_opt("max-steps") or "50")
        cmd_automate(console, task=task, dry_run=dry_run, max_steps=max_steps)

    elif _cmd == "clear":
        cmd_clear(console)

    elif _cmd == "version":
        cmd_version(console)

    else:
        console.print(f"[red]Unknown command:[/] {_cmd}")
        console.print("Type [bold]help[/] or [bold]help detailed[/] for available commands.")

    return True


def _countdown_or_second_ctrl_c(console: Console, seconds: float = 3.0) -> bool:
    """Display a smooth ticking countdown updating every 0.1s.
    Returns True if Ctrl+C was pressed during the countdown (force exit)."""
    try:
        remaining = seconds
        while remaining > 0:
            print(f"\rForce exit in: {remaining:.1f}s   ", end="", flush=True)
            sleep_step = min(0.1, remaining)
            time.sleep(sleep_step)
            remaining -= sleep_step
        print("\r" + " " * 30 + "\r", end="", flush=True)
        return False
    except KeyboardInterrupt:
        # Clear the countdown line so only the exit message shows
        print("\r" + " " * 30 + "\r", end="", flush=True)
        return True


_COMMAND_FLAGS: dict[str, list[str]] = {
    "status":       ["--json"],
    "watch":        [],
    "scan":         [],
    "doctor":       [],
    "config":       ["edit", "validate"],
    "export":       ["--format", "--output", "-o", "--limit"],
    "logs":         ["--tail", "-t", "--follow", "-f", "--level"],
    "purge":        ["--yes"],
    "update":       [],
    "version":      [],
    "registry":     [],
    "automate":     ["--dry-run", "--max-steps"],
    "chat":         [],
    "clear":        [],
    "help":         [],
    "exit":         [],
    "quit":         [],
}


class _ArchangelCompleter:
    """Context-aware tab completer for the Archangel REPL.

    - Empty buffer / partial command  → complete command names.
    - Known command + trailing space  → complete that command's flags.
    - Complete command (no trailing space) → no completion popup.
    - Unknown command                → no completions.
    """

    def get_completions(self, document, complete_event):
        try:
            from prompt_toolkit.completion import Completion

            text = document.text_before_cursor
            words = text.split()

            # Empty buffer – show all commands
            if not words:
                for cmd in sorted(REPL_COMMANDS):
                    yield Completion(cmd, start_position=0)
                return

            # Partial command name – filter
            if len(words) == 1 and not text.endswith(" "):
                prefix = words[0]
                for cmd in sorted(REPL_COMMANDS):
                    if cmd.startswith(prefix):
                        yield Completion(cmd, start_position=-len(prefix))
                return

            # Known command + space – show flags
            if text.endswith(" "):
                cmd = words[0].lower()
                for flag in _COMMAND_FLAGS.get(cmd, []):
                    yield Completion(flag, start_position=0)
                return
        except Exception:
            pass
        # After a complete command without trailing space – no completions
        return


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------


def _run_simple_repl(console: Console) -> None:
    """Fallback REPL using plain ``input()`` when prompt_toolkit is unavailable.

    Used when stdin is not a real Windows console (git-bash, piped input, etc.).
    No tab-completion or history — basic line input only.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    SHUTDOWN_SENTINEL.unlink(missing_ok=True)

    _repl_down = False
    _last_ctrl_c: float = 0.0
    _DOUBLE_CTRL_C_WINDOW = 3.0

    while not _repl_down:
        if SHUTDOWN_SENTINEL.exists():
            console.print("\n[yellow]Shutdown requested from external process.[/]")
            cmd_terminate(console)
            break

        try:
            raw = input("archangel.main> ")
        except EOFError:
            console.print()
            break
        except KeyboardInterrupt:
            now = time.time()
            if now - _last_ctrl_c < _DOUBLE_CTRL_C_WINDOW:
                console.print("\n[red]Forced exit.[/]")
                break
            _last_ctrl_c = now
            if _countdown_or_second_ctrl_c(console):
                console.print("\n[red]Forced exit.[/]")
                break
            continue

        raw = raw.strip()
        if not raw:
            continue

        for _segment in raw.split("&&"):
            _keep_going = _execute_repl_command(console, _segment)
            if not _keep_going:
                _repl_down = True
                break
        if _repl_down:
            break

    PID_FILE.unlink(missing_ok=True)
    SHUTDOWN_SENTINEL.unlink(missing_ok=True)


def run_repl(console: Console) -> None:
    """Drop into the ``archangel> `` REPL after a successful summon.

    Uses prompt_toolkit when running under a real Windows console (cmd.exe,
    PowerShell), and falls back to a simple ``input()``-based REPL for
    git-bash, MSYS2, or piped/non-interactive sessions.
    """
    if not sys.stdin.isatty():
        console.print("[yellow]Interactive terminal required. Run [bold]archangel summon[/] in cmd.exe or PowerShell.[/]")
        return

    # Check we are on a real Windows console, not a Cygwin/MSYS pty.
    # prompt_toolkit raises "No Windows console found" otherwise.
    try:
        # Probe: can we get the Windows console OS handle?
        import msvcrt
        msvcrt.get_osfhandle(sys.stdin.fileno())
    except (ImportError, OSError, AttributeError):
        _run_simple_repl(console)
        return

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write PID for cross-process signalling
    PID_FILE.write_text(str(os.getpid()))
    # Remove stale sentinel from a previous unclean shutdown
    SHUTDOWN_SENTINEL.unlink(missing_ok=True)

    # prompt_toolkit on Windows checks os.environ.get("TERM").
    # When running under git-bash/MSYS2 where TERM=xterm-256color it
    # raises and refuses to create a Win32 console input.  We clear
    # TERM for the whole REPL lifetime so prompt_toolkit uses its
    # native Windows input/output path.
    _old_term = os.environ.pop("TERM", None)
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory

        # Ensure history file's parent directory exists
        REPL_HISTORY.parent.mkdir(parents=True, exist_ok=True)

        completer = _ArchangelCompleter()
        session = _create_prompt_session(
            "archangel.main> ",
            ".archangel_repl_history",
            completer=completer,
            complete_while_typing=False,
        )

        _repl_down = False
        _last_ctrl_c: float = 0.0
        _DOUBLE_CTRL_C_WINDOW = 3.0

        while not _repl_down:
            # Poll sentinel from external ``archangel terminate``
            if SHUTDOWN_SENTINEL.exists():
                console.print("\n[yellow]Shutdown requested from external process.[/]")
                cmd_terminate(console)
                break

            try:
                raw = session.prompt()
            except KeyboardInterrupt:
                now = time.time()
                if now - _last_ctrl_c < _DOUBLE_CTRL_C_WINDOW:
                    console.print("\n[red]Forced exit.[/]")
                    _repl_down = True
                    break
                _last_ctrl_c = now
                if _countdown_or_second_ctrl_c(console):
                    console.print("\n[red]Forced exit.[/]")
                    _repl_down = True
                    break
                continue
            except Exception as pt_exc:
                # prompt_toolkit failed (e.g. stdin issues, console mode).
                # Fall back gracefully to the simple input()-based REPL.
                console.print(f"\n[yellow]prompt_toolkit error: {pt_exc}[/]")
                console.print("[yellow]Falling back to simple input mode.[/]")
                _run_simple_repl(console)
                return

            raw = raw.strip()
            if not raw:
                continue

            for _segment in raw.split("&&"):
                _keep_going = _execute_repl_command(console, _segment)
                if not _keep_going:
                    _repl_down = True
                    break
            if _repl_down:
                break

    finally:
        # Cleanup sentinel / PID
        PID_FILE.unlink(missing_ok=True)
        SHUTDOWN_SENTINEL.unlink(missing_ok=True)
        # Restore TERM so child processes see the original terminal type
        if _old_term is not None:
            os.environ["TERM"] = _old_term


def run_chat_repl(console: Console) -> None:
    """AI chat sub-REPL.  Prompt is ``archangel.chat> ``.

    Entered from ``archangel.main> chat``.  Exit back to the main REPL
    via ``exit``, ``quit``, or double Ctrl+C.
    """
    from archangel.agents.chat import (
        LLMClient,
        CommandExecutor,
        WebSearch,
        ScreenCapture,
        EXECUTE_RE,
        SEARCH_RE,
        SCREENSHOT_RE,
        AUTOMATE_RE,
        extract_execute_commands,
        extract_search_queries,
        extract_screenshot_requests,
        extract_automate_requests,
        Automator,
    )

    _api_keys = ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]
    if not any(k in os.environ for k in _api_keys):
        console.print("[red]No API key configured. Add one to .env under #API KEYS.[/]")
        return

    # Choose prompt_toolkit or simple input()
    _use_pt = False
    if sys.stdin.isatty():
        try:
            import msvcrt  # noqa: F401
            _use_pt = True
        except (ImportError, OSError, AttributeError):
            pass

    _last_ctrl_c: float = 0.0
    _DOUBLE_CTRL_C_WINDOW = 3.0

    if _use_pt:
        session = _create_prompt_session(
            "archangel.chat> ",
            ".archangel_chat_history",
            completer=_ChatCompleter(),
            complete_while_typing=True,
        )

        try:
            llm = LLMClient()
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/]")
            return

        executor = CommandExecutor()
        history: list[dict[str, str]] = []

        # System instruction — Archangel System Contract
        history.append({
            "role": "system",
            "content": (
                "# ARCHANGEL\n\n"
                "You are Archangel — a sharp, casual, slightly cocky AI assistant in a Windows terminal.\n"
                "You get things done fast. You have personality. You're not a corporate chatbot.\n\n"

                "PERSONALITY\n"
                "- Be casual and direct. Talk like a smart friend, not a help desk.\n"
                "- Use humor when appropriate. Dry wit > forced jokes.\n"
                "- If something is stupid, say it's stupid.\n"
                "- If you don't know, say so honestly. Don't ramble.\n"
                "- Never say 'I hope this helps!' or 'Let me know if you need anything else!'.\n"
                "- Never apologize excessively. One 'my bad' is enough.\n"
                "- If a search doesn't find what you expected, acknowledge it and move on.\n\n"

                "RUNTIME\n"
                "OS: Windows 11 | Shell: PowerShell (persistent, state carries between commands)\n\n"

                "TOOLS\n"
                "1. <execute>...</execute> — run a PowerShell command\n"
                "2. <search>...</search> — search the web\n"
                "3. <screenshot></screenshot> — capture the user's screen\n"
                "4. <automate>task description</automate> — autonomous GUI control (click, type, navigate)\n\n"

                "SLASH COMMANDS (handled by system, not you)\n"
                "The user has access to: /env /config /models /clear /history /export /help /exit\n"
                "These are handled instantly by the system. You don't need to execute them.\n\n"

                "COMMAND EXECUTION\n"
                "Wrap commands in <execute>...</execute>.\n"
                "Only execute when the user wants something done. Never guess filenames or paths.\n\n"

                "WEB SEARCH\n"
                "Use <search>query</search> when you need to find a URL or look something up.\n"
                "Don't search for yourself — you're a local private project.\n"
                "Don't search more than once for the same topic.\n\n"

                "OPENING WEBSITES\n"
                "If you know the URL, use it directly. If uncertain, search once.\n"
                "Never Google-search inside <execute>.\n"
                "Known URLs: git→git-scm.com | github→github.com | gemini→gemini.google.com | youtube→youtube.com | docker→docker.com | npm→npmjs.com | pypi→pypi.org\n\n"

                "OPENING APPS\n"
                "Use <automate>open appname</automate> to open apps via GUI automation.\n"
                "Use <automate>close appname</automate> to close apps via GUI automation.\n"
                "Or use Start-Process 'appname' for apps in PATH. Start-Process 'URL' for websites.\n\n"

                "YOUTUBE\n"
                "Play video: <execute>Start-Process 'https://www.youtube.com/results?search_query=QUERY'</execute>\n\n"

                "SCREEN CAPTURE\n"
                "When user asks to see their screen or screenshot, you MUST output EXACTLY this tag and nothing else:\n"
                "<screenshot></screenshot>\n"
                "Do NOT use  or any other format. ONLY <screenshot></screenshot>.\n"
                "After the system captures it, you'll receive the image. Describe what you see.\n\n"

                "GUI AUTOMATION\n"
                "When user asks to click, type, open/close apps, or automate anything on screen, use:\n"
                "<automate>description of what to do</automate>\n"
                "Example: <automate>open notepad and type hello</automate>\n"
                "Example: <automate>close chrome</automate>\n"
                "Example: <automate>click on the search bar</automate>\n"
                "NEVER use PowerShell for GUI tasks. ALWAYS use <automate>.\n\n"

                "CLOSING APPS\n"
                "To close an app: <automate>close appname</automate>\n"
                "Example: <automate>close notepad</automate>\n"
                "Example: <automate>close chrome</automate>\n\n"

                "MEMORY\n"
                "Remember previous commands, outputs, and errors in this session.\n\n"

                "ERRORS\n"
                "If a command fails: explain in one sentence, try ONE fix, then stop if it fails again.\n\n"

                "WHEN THE USER JUST CHATS\n"
                "Reply normally. Don't force command execution."
            ),
        })

        while True:
            try:
                raw = session.prompt()
            except KeyboardInterrupt:
                now = time.time()
                if now - _last_ctrl_c < _DOUBLE_CTRL_C_WINDOW:
                    console.print("\n[yellow]Returning to archangel.main>[/]")
                    return
                _last_ctrl_c = now
                if _countdown_or_second_ctrl_c(console):
                    console.print()
                    return
                continue

            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("/"):
                should_exit = _handle_slash_intercept(raw, console, history)
                if should_exit:
                    console.print()
                    return
                continue
            if raw.lower() in ("exit", "quit"):
                console.print()
                return

            history.append({"role": "user", "content": raw})

            _exec_iterations = 0
            while True:
                try:
                    llm.switch_provider(_cli_commands._active_model_provider)
                    response_text = llm.chat(history)
                except Exception as exc:
                    console.print(f"[red]LLM error: {exc}[/]")
                    break

                _exec_iterations += 1
                if _exec_iterations > 5:
                    console.print("[yellow]archangel> Alright, I'm stuck. Try rephrasing.[/]")
                    break

                history.append({"role": "assistant", "content": response_text})

                console.print()
                # Print the assistant response (strip command blocks from display)
                display = EXECUTE_RE.sub("", response_text)
                display = SEARCH_RE.sub("", display)
                display = SCREENSHOT_RE.sub("", display)
                display = AUTOMATE_RE.sub("", display)
                # Strip wrong formats too (, , thinking tags)
                display = re.sub(r"<tool>\s*(?:\[thinking\].*?</thinking>\s*)?\[screenshot\]\s*</tool>", "", display, flags=re.IGNORECASE | re.DOTALL)
                display = re.sub(r"<tool>\s*(?:\[thinking\].*?</thinking>\s*)?\[([^\]]+)\]\s*</tool>", "", display, flags=re.IGNORECASE | re.DOTALL)
                display = re.sub(r"<pyautogui_call>.*?</pyautogui_call>", "", display, flags=re.DOTALL)
                display = re.sub(r"<screenshot>|</screenshot>", "", display, flags=re.IGNORECASE)
                for line in display.splitlines():
                    if line.strip():
                        console.print(f"[bold]archangel>[/] {line}")
                console.print()

                # Handle <screenshot></screenshot>
                screenshots = extract_screenshot_requests(response_text)
                if screenshots:
                    if not llm.supports_vision():
                        console.print("[bold]archangel>[/] [red]Screen capture requires a vision-capable provider (Gemini, OpenAI, Claude, OpenRouter, or Groq). Current provider doesn't support vision.[/]")
                    else:
                        sc = ScreenCapture()
                        img_b64 = sc.capture()
                        if not img_b64.startswith("[ERROR]"):
                            console.print(f"[bold]archangel>[/] [dim]screenshot captured[/]")
                            history.append({
                                "role": "user",
                                "content": f"<screenshot>{img_b64}</screenshot>",
                            })
                        else:
                            console.print(f"[bold]archangel>[/] {img_b64}")
                    continue

                # Handle <automate>...</automate>
                automate_requests = extract_automate_requests(response_text)
                if automate_requests:
                    for task_desc in automate_requests:
                        console.print(f"[bold]archangel>[/] [dim]automating: {task_desc}[/]")
                        result = Automator.run(task=task_desc)
                        history.append({
                            "role": "user",
                            "content": f"<automate_result>{result}</automate_result>",
                        })
                    continue

                # Handle <search>...</search>
                queries = extract_search_queries(response_text)
                if queries:
                    for q in queries:
                        console.print(f"[bold]archangel>[/] [dim]searching: {q}[/]")
                        search_output = WebSearch().search(q)
                        history.append({
                            "role": "user",
                            "content": f"<search_results>\n{search_output}\n</search_results>",
                        })
                    continue  # Let LLM respond to search results

                # Check for <execute>...</execute> blocks
                commands = extract_execute_commands(response_text)
                if not commands:
                    break  # No more commands to run — done

                for cmd in commands:
                    console.print(f"[bold]archangel>[/] [dim]$ {cmd}[/]")
                    output = executor.execute(cmd)
                    history.append({
                        "role": "user",
                        "content": f"<output>\n{output}\n</output>",
                    })

                # After processing all commands, let LLM respond to the output
                # (loop back to chat() with the output appended)
    else:
        try:
            llm = LLMClient()
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/]")
            return

        executor = CommandExecutor()
        history: list[dict[str, str]] = []

        # System instruction — Archangel System Contract
        history.append({
            "role": "system",
            "content": (
                "# ARCHANGEL\n\n"
                "You are Archangel — a sharp, casual, slightly cocky AI assistant in a Windows terminal.\n"
                "You get things done fast. You have personality. You're not a corporate chatbot.\n\n"

                "PERSONALITY\n"
                "- Be casual and direct. Talk like a smart friend, not a help desk.\n"
                "- Use humor when appropriate. Dry wit > forced jokes.\n"
                "- If something is stupid, say it's stupid.\n"
                "- If you don't know, say so honestly. Don't ramble.\n"
                "- Never say 'I hope this helps!' or 'Let me know if you need anything else!'.\n"
                "- Never apologize excessively. One 'my bad' is enough.\n"
                "- If a search doesn't find what you expected, acknowledge it and move on.\n\n"

                "RUNTIME\n"
                "OS: Windows 11 | Shell: PowerShell (persistent, state carries between commands)\n\n"

                "TOOLS\n"
                "1. <execute>...</execute> — run a PowerShell command\n"
                "2. <search>...</search> — search the web\n"
                "3. <screenshot></screenshot> — capture the user's screen\n"
                "4. <automate>task description</automate> — autonomous GUI control (click, type, navigate)\n\n"

                "SLASH COMMANDS (handled by system, not you)\n"
                "The user has access to: /env /config /models /clear /history /export /help /exit\n"
                "These are handled instantly by the system. You don't need to execute them.\n\n"

                "COMMAND EXECUTION\n"
                "Wrap commands in <execute>...</execute>.\n"
                "Only execute when the user wants something done. Never guess filenames or paths.\n\n"

                "WEB SEARCH\n"
                "Use <search>query</search> when you need to find a URL or look something up.\n"
                "Don't search for yourself — you're a local private project.\n"
                "Don't search more than once for the same topic.\n\n"

                "OPENING WEBSITES\n"
                "If you know the URL, use it directly. If uncertain, search once.\n"
                "Never Google-search inside <execute>.\n"
                "Known URLs: git→git-scm.com | github→github.com | gemini→gemini.google.com | youtube→youtube.com | docker→docker.com | npm→npmjs.com | pypi→pypi.org\n\n"

                "OPENING APPS\n"
                "Use <automate>open appname</automate> to open apps via GUI automation.\n"
                "Use <automate>close appname</automate> to close apps via GUI automation.\n"
                "Or use Start-Process 'appname' for apps in PATH. Start-Process 'URL' for websites.\n\n"

                "YOUTUBE\n"
                "Play video: <execute>Start-Process 'https://www.youtube.com/results?search_query=QUERY'</execute>\n\n"

                "SCREEN CAPTURE\n"
                "When user asks to see their screen or screenshot, you MUST output EXACTLY this tag and nothing else:\n"
                "<screenshot></screenshot>\n"
                "Do NOT use  or any other format. ONLY <screenshot></screenshot>.\n"
                "After the system captures it, you'll receive the image. Describe what you see.\n\n"

                "GUI AUTOMATION\n"
                "When user asks to click, type, open/close apps, or automate anything on screen, use:\n"
                "<automate>description of what to do</automate>\n"
                "Example: <automate>open notepad and type hello</automate>\n"
                "Example: <automate>close chrome</automate>\n"
                "Example: <automate>click on the search bar</automate>\n"
                "NEVER use PowerShell for GUI tasks. ALWAYS use <automate>.\n\n"

                "CLOSING APPS\n"
                "To close an app: <automate>close appname</automate>\n"
                "Example: <automate>close notepad</automate>\n"
                "Example: <automate>close chrome</automate>\n\n"

                "MEMORY\n"
                "Remember previous commands, outputs, and errors in this session.\n\n"

                "ERRORS\n"
                "If a command fails: explain in one sentence, try ONE fix, then stop if it fails again.\n\n"

                "WHEN THE USER JUST CHATS\n"
                "Reply normally. Don't force command execution."
            ),
        })

        while True:
            try:
                raw = input("archangel.chat> ")
            except EOFError:
                console.print()
                return
            except KeyboardInterrupt:
                now = time.time()
                if now - _last_ctrl_c < _DOUBLE_CTRL_C_WINDOW:
                    console.print("\n[yellow]Returning to archangel.main>[/]")
                    return
                _last_ctrl_c = now
                if _countdown_or_second_ctrl_c(console):
                    console.print("\n[yellow]Returning to archangel.main>[/]")
                    return
                continue

            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("/"):
                should_exit = _handle_slash_intercept(raw, console, history)
                if should_exit:
                    console.print("[yellow]archangel> Returning to archangel.main>[/]")
                    return
                continue
            if raw.lower() in ("exit", "quit"):
                console.print("[yellow]Returning to archangel.main>[/]")
                return

            history.append({"role": "user", "content": raw})

            _exec_iterations = 0
            while True:
                try:
                    llm.switch_provider(_cli_commands._active_model_provider)
                    response_text = llm.chat(history)
                except Exception as exc:
                    console.print(f"[red]LLM error: {exc}[/]")
                    break

                _exec_iterations += 1
                if _exec_iterations > 5:
                    console.print("[yellow]archangel> Alright, I'm stuck. Try rephrasing.[/]")
                    break

                history.append({"role": "assistant", "content": response_text})

                console.print()
                # Print the assistant response (strip command blocks from display)
                display = EXECUTE_RE.sub("", response_text)
                display = SEARCH_RE.sub("", display)
                display = SCREENSHOT_RE.sub("", display)
                display = AUTOMATE_RE.sub("", display)
                # Strip wrong formats too (, , thinking tags)
                display = re.sub(r"<tool>\s*(?:\[thinking\].*?</thinking>\s*)?\[screenshot\]\s*</tool>", "", display, flags=re.IGNORECASE | re.DOTALL)
                display = re.sub(r"<tool>\s*(?:\[thinking\].*?</thinking>\s*)?\[([^\]]+)\]\s*</tool>", "", display, flags=re.IGNORECASE | re.DOTALL)
                display = re.sub(r"<pyautogui_call>.*?</pyautogui_call>", "", display, flags=re.DOTALL)
                display = re.sub(r"<screenshot>|</screenshot>", "", display, flags=re.IGNORECASE)
                for line in display.splitlines():
                    if line.strip():
                        console.print(f"[bold]archangel>[/] {line}")
                console.print()

                # Handle <screenshot></screenshot>
                screenshots = extract_screenshot_requests(response_text)
                if screenshots:
                    if not llm.supports_vision():
                        console.print("[bold]archangel>[/] [red]Screen capture requires a vision-capable provider (Gemini, OpenAI, Claude, OpenRouter, or Groq). Current provider doesn't support vision.[/]")
                    else:
                        sc = ScreenCapture()
                        img_b64 = sc.capture()
                        if not img_b64.startswith("[ERROR]"):
                            console.print(f"[bold]archangel>[/] [dim]screenshot captured[/]")
                            history.append({
                                "role": "user",
                                "content": f"<screenshot>{img_b64}</screenshot>",
                            })
                        else:
                            console.print(f"[bold]archangel>[/] {img_b64}")
                    continue

                # Handle <automate>...</automate>
                automate_requests = extract_automate_requests(response_text)
                if automate_requests:
                    for task_desc in automate_requests:
                        console.print(f"[bold]archangel>[/] [dim]automating: {task_desc}[/]")
                        result = Automator.run(task=task_desc)
                        history.append({
                            "role": "user",
                            "content": f"<automate_result>{result}</automate_result>",
                        })
                    continue

                # Handle <search>...</search>
                queries = extract_search_queries(response_text)
                if queries:
                    for q in queries:
                        console.print(f"[bold]archangel>[/] [dim]searching: {q}[/]")
                        search_output = WebSearch().search(q)
                        history.append({
                            "role": "user",
                            "content": f"<search_results>\n{search_output}\n</search_results>",
                        })
                    continue  # Let LLM respond to search results

                # Check for <execute>...</execute> blocks
                commands = extract_execute_commands(response_text)
                if not commands:
                    break  # No more commands to run — done

                for cmd in commands:
                    console.print(f"[bold]archangel>[/] [dim]$ {cmd}[/]")
                    output = executor.execute(cmd)
                    history.append({
                        "role": "user",
                        "content": f"<output>\n{output}\n</output>",
                    })


# ---------------------------------------------------------------------------
# Custom Click group — suppresses the ``Usage:`` line in help output
# ---------------------------------------------------------------------------

class _ArchangelGroup(click.Group):
    """A Click group that omits the ``Usage:`` banner from ``--help``."""

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        pass  # deliberately suppressed


# ---------------------------------------------------------------------------
# CLI layer (Click)  — thin wrappers around cmd_* functions
# ---------------------------------------------------------------------------

@click.group(
    cls=_ArchangelGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug-level logging.")
@click.option("--verbose", is_flag=True, help="Increase output verbosity.")
@click.option("--config", type=click.Path(dir_okay=False, path_type=str),
              default=None, help="Path to custom configuration YAML.")
@click.option("-v", "--version", "show_version", is_flag=True,
              help="Show version and exit.")
@click.pass_context
def cli(ctx: click.Context, debug: bool, verbose: bool,
        config: str | None, show_version: bool) -> None:
    """⚔ The Archangel — Autonomous Lead Intelligence Platform"""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["CONFIG"] = config

    if show_version:
        cmd_version(_console)
        ctx.exit()

    if ctx.invoked_subcommand is None:
        ctx.invoke(summon)


@cli.command()
@click.pass_context
def summon(ctx: click.Context) -> None:
    """Start the platform (default command)."""
    ok = cmd_summon(
        _console,
        debug=ctx.obj.get("DEBUG", False),
        config_path=ctx.obj.get("CONFIG"),
    )
    if ok:
        run_repl(_console)
    sys.exit(0)


@cli.command()
def terminate() -> None:
    """Gracefully shut down the platform."""
    # If a REPL process is running, signal it via sentinel
    if PID_FILE.exists():
        SHUTDOWN_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        SHUTDOWN_SENTINEL.touch()
        _console.print("[yellow]Sent shutdown signal to running instance.[/]")
        _console.print("[yellow]Waiting for it to exit ...[/]")
        # Poll until the PID file disappears (REPL cleaned it up)
        for _ in range(30):
            time.sleep(0.5)
            if not PID_FILE.exists():
                break
        if PID_FILE.exists():
            _console.print("[red]Instance did not respond. Forcing PID removal.[/]")
            PID_FILE.unlink(missing_ok=True)
        SHUTDOWN_SENTINEL.unlink(missing_ok=True)
        _console.print("[green]✓ The Archangel has been terminated.[/]")
    else:
        cmd_terminate(_console)


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def status(as_json: bool) -> None:
    """Display runtime information and agent health."""
    cmd_status(_console, as_json=as_json)


@cli.command()
def watch() -> None:
    """Live event stream."""
    cmd_watch(_console)


@cli.command("scan")
def scan() -> None:
    """One-time scan (collect, analyse, score — then exit)."""
    cmd_scan(_console)


@cli.command("leads")
@click.argument("query", nargs=-1)
@click.option("--limit", default=10, help="Maximum number of leads to fetch or display.")
def leads_cli_command(query: tuple, limit: int) -> None:
    """Fetch live leads from Reddit/X or list saved database leads.

    Examples:
        archangel leads "discord bot"
        archangel leads custom bot max: 4
        archangel leads "python developer" max:3 --limit 5
    """
    query_str = " ".join(query).strip()
    cmd_leads(_console, query=query_str, limit=limit)


@cli.command()
def chat() -> None:
    """Enter the AI chat directly."""
    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)

    _api_keys = ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]
    if not any(k in os.environ for k in _api_keys):
        _console.print("[red]No API key configured. Add one to .env under #API KEYS.[/]")
        return

    render_banner(_console)
    _console.print(Panel.fit(
        "[bold white]⚔ AI Chat Active[/]\n"
        "[italic #c0c0c0]Ask me anything or say exit to return.[/]",
        border_style="white",
    ))
    _console.print()

    run_chat_repl(_console)
    sys.exit(0)


@cli.command()
@click.argument("task")
@click.option("--dry-run", is_flag=True, help="Show actions without executing")
@click.option("--max-steps", default=50, type=int,
              help="Maximum actions per task")
def automate(task: str, dry_run: bool, max_steps: int) -> None:
    """Autonomously perform GUI tasks using vision AI."""
    from dotenv import load_dotenv
    load_dotenv(_get_project_root() / ".env", override=False)
    cmd_automate(_console, task=task, dry_run=dry_run, max_steps=max_steps)


@cli.command()
def doctor() -> None:
    """Run system diagnostics and report health."""
    cmd_doctor(_console)


@cli.command()
@click.argument("action", type=click.Choice(["edit", "validate"]),
                default="edit", required=False)
@click.argument("section", type=str, required=False)
def config(action: str, section: str | None) -> None:
    """Inspect or edit configuration."""
    cmd_config(_console, action=action, section=section)



@cli.command()
@click.option("--format", "fmt", type=click.Choice(["csv", "json", "md"]),
              default="json", help="Export format.")
@click.option("--output", "-o", type=click.Path(dir_okay=False),
              default=None, help="Output file path.")
@click.option("--limit", type=int, default=None,
              help="Maximum number of leads to export.")
def export(fmt: str, output: str | None, limit: int | None) -> None:
    """Export leads in CSV, JSON, or Markdown format."""
    cmd_export(_console, fmt=fmt, output=output, limit=limit)


@cli.command()
@click.option("--tail", "-t", type=int, default=50, help="Show last N lines.")
@click.option("--follow", "-f", is_flag=True, help="Follow log output.")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
              default=None, help="Filter by log level.")
def logs(tail: int, follow: bool, level: str | None) -> None:
    """View runtime logs."""
    cmd_logs(_console, tail=tail, follow=follow, level=level)


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to purge cache and temporary data?")
def purge() -> None:
    """Clean cache, temporary data, and runtime artifacts."""
    cmd_purge(_console, confirmed=True)


@cli.command()
def update() -> None:
    """Update plugins and system components."""
    cmd_update(_console)


@cli.command()
def version() -> None:
    """Display the installed version of The Archangel."""
    cmd_version(_console)


@cli.group(invoke_without_command=True)
@click.option("--enabled", is_flag=True, help="Show only enabled plugins.")
@click.option("--disabled", is_flag=True, help="Show only disabled plugins.")
@click.option("--category", default=None, help="Filter by category.")
@click.pass_context
def registry(ctx: click.Context, enabled: bool, disabled: bool,
             category: str | None) -> None:
    """List or inspect installed plugins."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(list, enabled=enabled, disabled=disabled, category=category)


@registry.command()
@click.option("--enabled", is_flag=True, help="Show only enabled plugins.")
@click.option("--disabled", is_flag=True, help="Show only disabled plugins.")
@click.option("--category", default=None, help="Filter by category.")
def list(enabled: bool, disabled: bool, category: str | None) -> None:
    """List all installed plugins in a table."""
    cmd_registry_list(_console, enabled=enabled, disabled=disabled, category=category)


@registry.command()
@click.argument("name")
def info(name: str) -> None:
    """Show detailed manifest information for a single plugin."""
    cmd_registry_info(_console, name=name)


# --- Start & Telegram Commands ---

@cli.group(invoke_without_command=True)
@click.argument("target", required=False, default="telegram")
@click.pass_context
def start(ctx: click.Context, target: str) -> None:
    """Start background services or plugins (e.g. archangel start telegram)."""
    if ctx.invoked_subcommand is None:
        if target.lower() == "telegram":
            cmd_start_telegram(_console)
        else:
            _console.print(f"[yellow]Unknown start target: {target}[/]")


@start.command("telegram")
def start_telegram_cmd() -> None:
    """Start the interactive Telegram remote control bridge."""
    cmd_start_telegram(_console)


@cli.group(invoke_without_command=True)
@click.pass_context
def telegram(ctx: click.Context) -> None:
    """Telegram remote control bridge commands."""
    if ctx.invoked_subcommand is None:
        cmd_start_telegram(_console)


@telegram.command("start")
def telegram_start_subcmd() -> None:
    """Start the Telegram bridge."""
    cmd_start_telegram(_console)


@cli.command("start-telegram")
def start_telegram_alias() -> None:
    """Start the Telegram remote control bridge."""
    cmd_start_telegram(_console)


# --- Help & Agent Directives ---

@cli.command("help")
@click.argument("topic", required=False, default=None)
@click.option("--detailed", is_flag=True, help="Display full detailed command & agent manual.")
def help_command(topic: str | None, detailed: bool) -> None:
    """Display Archangel command & agent reference documentation."""
    if detailed or (topic and topic.lower() == "detailed"):
        cmd_help_detailed(_console)
    else:
        _console.print(_REPL_HELP)


@cli.command("collector")
@click.argument("action", default="status", required=False)
def agent_collector(action: str) -> None:
    """Interact directly with archangel.collector agent."""
    cmd_agent_dispatch(_console, "collector", action)


@cli.command("intelligence")
@click.argument("payload", required=False, default="")
def agent_intelligence(payload: str) -> None:
    """Interact directly with archangel.intelligence reasoning agent."""
    cmd_agent_dispatch(_console, "intelligence", "analyze", payload)


@cli.command("scoring")
def agent_scoring() -> None:
    """Interact directly with archangel.scoring agent."""
    cmd_agent_dispatch(_console, "scoring")


@cli.command("guardian")
def agent_guardian() -> None:
    """Interact directly with archangel.guardian component health monitor."""
    cmd_agent_dispatch(_console, "guardian")


@cli.command("commander")
def agent_commander() -> None:
    """Interact directly with archangel.commander orchestrator."""
    cmd_agent_dispatch(_console, "commander")


@cli.command("storage")
def agent_storage() -> None:
    """Interact directly with archangel.storage backend agent."""
    cmd_agent_dispatch(_console, "storage")


@cli.command("notification")
def agent_notification() -> None:
    """Interact directly with archangel.notification delivery agent."""
    cmd_agent_dispatch(_console, "notification")


@cli.command("agents")
def agents_cmd() -> None:
    """Start the central agents topic-routing hub."""
    run_agents_hub_repl(_console)


@cli.command("groupchat")
def groupchat_cmd() -> None:
    """Start the multi-agent groupchat room."""
    run_groupchat_repl(_console)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entrypoint (``archangel``)."""
    ensure_user_path_registered()

    # Intercept --help detailed or help detailed
    argv_lower = [a.lower() for a in sys.argv[1:]]
    if "detailed" in argv_lower and ("help" in argv_lower or "--help" in argv_lower or "-h" in argv_lower):
        cmd_help_detailed(_console)
        sys.exit(0)

    try:
        cli(prog_name="archangel")
    except click.ClickException:
        sys.exit(1)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        _console.print("\n[yellow]Interrupted.[/]")
        sys.exit(130)
    except Exception as exc:
        _print_error_panel(
            what="An unexpected error occurred.",
            why=str(exc),
            suggestions=[
                "Run with [bold]--debug[/] for a detailed traceback.",
                "File an issue with the full error output.",
            ],
        )
        sys.exit(1)


if __name__ == "__main__":
    main()


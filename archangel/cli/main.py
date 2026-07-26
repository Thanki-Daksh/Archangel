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
import shlex
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from archangel.cli.banner import render_banner
from archangel.cli import commands as _cli_commands
from archangel.cli.commands import _ChatCompleter

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
    "registry", "chat", "automate", "clear", "help", "exit", "quit"
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

from archangel.cli.bootstrap import ensure_user_path_registered


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

from archangel.cli.handlers import (
    cmd_summon,
    cmd_terminate,
    cmd_status,
    cmd_watch,
    cmd_scan,
    cmd_doctor,
    cmd_config,
    cmd_export,
    cmd_leads,
    cmd_wipe_lead_logs,
    cmd_lead_logs,
    cmd_discord,
    cmd_logs,
    cmd_purge,
    cmd_update,
    cmd_version,
    cmd_clear,
    cmd_registry_list,
    cmd_registry_info,
    cmd_start_telegram,
    cmd_help_detailed,
)



from archangel.cli.repl import (
    AGENT_SYSTEM_PROMPTS,
    _classify_agent_topic,
    create_prompt_session as _create_prompt_session,
    run_repl,
)
from archangel.cli.chat_repls import (
    run_chat_repl,
    run_agents_hub_repl,
    run_groupchat_repl,
    cmd_agent_dispatch,
)



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

class _SwarmCommand(click.Command):
    """Custom Click command that transforms short flag aliases in args before option parsing."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        new_args: list[str] = []
        for arg in args:
            if arg in ("-w-i", "--w-i", "-wi", "--wi", "-w_i", "--w_i"):
                new_args.append("--write-interval")
            elif arg == "--w":
                new_args.append("-w")
            elif arg == "--f":
                new_args.append("-f")
            elif arg == "--l":
                new_args.append("-l")
            elif arg == "--t":
                new_args.append("-t")
            elif arg == "--d":
                new_args.append("-d")
            elif arg == "--o":
                new_args.append("-o")
            else:
                new_args.append(arg)
        return super().parse_args(ctx, new_args)


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


def _handle_lead_or_logs(ctx: click.Context, query: tuple, limit: int, wipe: bool, db: bool) -> None:
    sub_wipe = wipe or any(a.lower() in ("--wipe", "-w") for a in query)
    sub_db = db or any(a.lower() in ("--db", "-d") for a in query)
    
    if sub_wipe or sub_db:
        cmd_wipe_lead_logs(_console, db=sub_db)
        return

    if query and query[0].lower() in ("log", "logs"):
        cmd_lead_logs(_console, wipe=sub_wipe, db=sub_db)
        return

    query_str = " ".join(query).strip()
    cmd_leads(_console, query=query_str, limit=limit)


@cli.group("lead", invoke_without_command=True)
@click.argument("query", nargs=-1)
@click.option("--limit", default=10, help="Maximum number of leads to fetch or display.")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.pass_context
def lead_cli_group(ctx: click.Context, query: tuple, limit: int, wipe: bool, db: bool) -> None:
    """Fetch live leads, inspect lead logs, or wipe lead log stream/DB."""
    if ctx.invoked_subcommand is None:
        _handle_lead_or_logs(ctx, query, limit, wipe, db)


@lead_cli_group.command("logs")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.option("--tail", "-t", default=50, help="Show last N lines of lead logs.")
@click.option("--output", "-o", default="data/swarm_leads.log", help="Path to lead log file.")
def lead_logs_subcmd(wipe: bool, db: bool, tail: int, output: str) -> None:
    """View or wipe the swarm lead log stream (data/swarm_leads.log)."""
    cmd_lead_logs(_console, path=output, tail=tail, wipe=wipe, db=db)


@lead_cli_group.command("log")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.option("--tail", "-t", default=50, help="Show last N lines of lead logs.")
@click.option("--output", "-o", default="data/swarm_leads.log", help="Path to lead log file.")
def lead_log_subcmd(wipe: bool, db: bool, tail: int, output: str) -> None:
    """View or wipe the swarm lead log stream (data/swarm_leads.log)."""
    cmd_lead_logs(_console, path=output, tail=tail, wipe=wipe, db=db)


@cli.group("leads", invoke_without_command=True)
@click.argument("query", nargs=-1)
@click.option("--limit", default=10, help="Maximum number of leads to fetch or display.")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.pass_context
def leads_cli_group(ctx: click.Context, query: tuple, limit: int, wipe: bool, db: bool) -> None:
    """Fetch live leads, inspect lead logs, or wipe lead log stream/DB (alias for 'lead')."""
    if ctx.invoked_subcommand is None:
        _handle_lead_or_logs(ctx, query, limit, wipe, db)


@leads_cli_group.command("logs")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.option("--tail", "-t", default=50, help="Show last N lines of lead logs.")
@click.option("--output", "-o", default="data/swarm_leads.log", help="Path to lead log file.")
def leads_logs_subcmd(wipe: bool, db: bool, tail: int, output: str) -> None:
    """View or wipe the swarm lead log stream (data/swarm_leads.log)."""
    cmd_lead_logs(_console, path=output, tail=tail, wipe=wipe, db=db)


@leads_cli_group.command("log")
@click.option("--wipe", is_flag=True, help="Wipe everything inside data/swarm_leads.log.")
@click.option("--db", is_flag=True, help="Purge all lead entries from SQLite database as well.")
@click.option("--tail", "-t", default=50, help="Show last N lines of lead logs.")
@click.option("--output", "-o", default="data/swarm_leads.log", help="Path to lead log file.")
def leads_log_subcmd(wipe: bool, db: bool, tail: int, output: str) -> None:
    """View or wipe the swarm lead log stream (data/swarm_leads.log)."""
    cmd_lead_logs(_console, path=output, tail=tail, wipe=wipe, db=db)


@cli.command("discord")
@click.option("--token", default=None, help="Discord Bot Token (overrides DISCORD_BOT_TOKEN env var).")
def discord_cli_command(token: str | None) -> None:
    """Launch the live Discord Lead Monitor bot to watch job channels for hiring posts."""
    cmd_discord(_console, token=token)


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


def swarm_options(f):
    f = click.option("-d", "--duration", "--d", "duration", default="3h", help="Duration to run swarm (e.g. 30s, 3h, continuous).")(f)
    f = click.option("-o", "--output", "--o", "output", default="data/swarm_leads.log", help="Path to output stream log file.")(f)
    f = click.option("--targets", default="all", help="Target platforms, links, or 'all'.")(f)
    f = click.option("-w", "--workers", "--w", "workers", default=300, help="Max worker tasks in pool.")(f)
    f = click.option("-l", "--leads", "--l", "--query", "leads_query", default=None, help="Target specific lead topic/niche (e.g. 'website development').")(f)
    f = click.option("-f", "--fresh", "--f", "fresh", default=None, help="Freshness age filter e.g. '3d', '1-10d', '2w', '1y', '1-10 days'.")(f)
    f = click.option("-b", "--b", "--budget", "budget", default=None, help="Minimum budget threshold e.g. '$1000', '5k', '2500'.")(f)
    f = click.option("--write-interval", "--w-i", "-wi", "--wi", "--flush-interval", "write_interval", default=None, help="File write flush interval e.g. '10s', '5s', '1m'.")(f)
    f = click.option("-t", "--telegram", "--t", "telegram_mode", default="off", type=click.Choice(["on", "off"], case_sensitive=False), help="Auto-broadcast live monitor table to Telegram ('on' or 'off', default: 'off').")(f)
    f = click.option("--append", is_flag=True, default=False, help="Append to log file instead of starting fresh from 0.")(f)
    return f


def _run_swarm(
    duration: str,
    output: str,
    targets: str,
    workers: int,
    leads_query: str | None,
    fresh: str | None,
    budget: str | None,
    write_interval: str | None,
    telegram_mode: str,
    append: bool,
) -> None:
    import asyncio
    from pathlib import Path
    from archangel.agents.swarm.manager import SwarmManager
    from archangel.config import ConfigManager

    cfg_mgr = ConfigManager()
    if not cfg_mgr.is_setup_completed():
        from archangel.cli.handlers import cmd_setup
        _console.print("[yellow]Archangel has not been configured yet. Running initial setup wizard...[/]")
        cmd_setup(_console)

    msg = f"[bold cyan]⚔ Summoning 24/7 Agent Swarm... (Duration: {duration}, Workers: {workers})"
    if leads_query:
        msg += f" [Leads Query: '{leads_query}']"
    if fresh:
        msg += f" [Freshness: '{fresh}']"
    if budget:
        msg += f" [Minimum Budget: '{budget}']"
    if write_interval:
        msg += f" [Write Interval: '{write_interval}']"
    if telegram_mode.lower() == "on":
        msg += " [Telegram Broadcast: ON]"
    else:
        msg += " [Telegram Broadcast: OFF]"
    msg += "[/]"
    _console.print(msg)

    manager = SwarmManager(
        duration=duration,
        output_path=Path(output),
        targets=targets,
        max_workers=workers,
        leads_query=leads_query,
        reset_log=not append,
        fresh=fresh,
        budget=budget,
        write_interval=write_interval,
        telegram=(telegram_mode.lower() == "on"),
    )
    try:
        asyncio.run(manager.run())
    except (KeyboardInterrupt, SystemExit):
        _console.print("\n[bold yellow]✔ Swarm safely stopped.[/bold yellow]")


@cli.command("swarm", cls=_SwarmCommand)
@swarm_options
def swarm_cmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Launch 24/7 token-efficient agent swarm."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@cli.command("as", cls=_SwarmCommand)
@swarm_options
def as_cmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Shortcut alias for 'agent swarm'."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@cli.command("s", cls=_SwarmCommand)
@swarm_options
def s_cmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Shortcut alias for 'swarm'."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@cli.group("agent", invoke_without_command=True)
@click.pass_context
def agent_group(ctx: click.Context) -> None:
    """Agent management and 24/7 agent swarm subsystem."""
    if ctx.invoked_subcommand is None:
        run_agents_hub_repl(_console)


@agent_group.command("swarm", cls=_SwarmCommand)
@swarm_options
def agent_swarm_subcmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Launch 24/7 token-efficient agent swarm."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@agent_group.command("s", cls=_SwarmCommand)
@swarm_options
def agent_s_subcmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Shortcut alias for 'agent swarm'."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@cli.group("a", invoke_without_command=True)
@click.pass_context
def a_group(ctx: click.Context) -> None:
    """Shortcut alias for 'agent' subsystem."""
    if ctx.invoked_subcommand is None:
        run_agents_hub_repl(_console)


@a_group.command("swarm", cls=_SwarmCommand)
@swarm_options
def a_swarm_subcmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Shortcut alias for 'agent swarm'."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@a_group.command("s", cls=_SwarmCommand)
@swarm_options
def a_s_subcmd(duration: str, output: str, targets: str, workers: int, leads_query: str | None, fresh: str | None, budget: str | None, write_interval: str | None, telegram_mode: str, append: bool) -> None:
    """Shortcut alias for 'agent swarm' (aa a s)."""
    _run_swarm(duration, output, targets, workers, leads_query, fresh, budget, write_interval, telegram_mode, append)


@cli.command("setup")
@click.option("--reset", is_flag=True, help="Deletes existing configuration and reruns the wizard.")
@click.option("--telegram", is_flag=True, help="Configure Telegram bot credentials only.")
@click.option("--providers", is_flag=True, help="Configure AI Provider credentials only.")
def setup_cli_cmd(reset: bool, telegram: bool, providers: bool) -> None:
    """Run interactive Archangel V1.3 Setup Wizard."""
    from archangel.cli.handlers import cmd_setup
    cmd_setup(_console, reset=reset, telegram=telegram, providers=providers)


@cli.command("doctor")
def doctor_cli_cmd() -> None:
    """Run full Archangel system diagnostics & health checks."""
    from archangel.cli.handlers import cmd_doctor
    cmd_doctor(_console)


@cli.command("config")
def config_cli_cmd() -> None:
    """Display active persistent configuration stored under ~/.archangel/."""
    from archangel.cli.handlers import cmd_config
    cmd_config(_console)


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


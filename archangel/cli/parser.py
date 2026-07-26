import shlex
from rich.console import Console

from archangel.cli.handlers import (
    cmd_start_telegram,
    cmd_help_detailed,
    cmd_terminate,
    cmd_status,
    cmd_watch,
    cmd_scan,
    cmd_leads,
    cmd_doctor,
    cmd_config,
    cmd_export,
    cmd_logs,
    cmd_purge,
    cmd_update,
    cmd_registry_info,
    cmd_registry_list,
    cmd_clear,
    cmd_version,
)

# We will need to import these from repl.py once we create it. For now, since they 
# are currently in main.py, we might have a circular import if parser.py imports from main.py.
# Actually, the user wants incremental refactoring. I'll import them at runtime inside the function
# to avoid circular imports during the transition.

_REPL_HELP = """
[bold cyan]Archangel REPL Commands[/bold cyan]

[bold]help[/bold]                 - Show this quick help.
[bold]help detailed[/bold]        - Open the comprehensive manual (pager).
[bold]start telegram[/bold]       - Start the Telegram polling bot (alias: telegram).
[bold]chat[/bold]                 - Enter interactive agent chat mode.
[bold]agents[/bold]               - Enter interactive Agent Hub mode (topic routing).
[bold]groupchat[/bold]            - Start an autonomous multi-agent swarm discussion.
[bold]status[/bold] [--json]      - Show system and agent health.
[bold]watch[/bold]                - Live dashboard of current operations.
[bold]scan[/bold]                 - Trigger immediate lead discovery sweep.
[bold]leads[/bold] [query]        - Search local leads (flags: --limit 10).
[bold]doctor[/bold]               - Run self-diagnostics.
[bold]config[/bold] edit|validate - Manage configuration.
[bold]export[/bold] [--format]    - Export data (json, csv).
[bold]logs[/bold]                 - View logs (flags: --tail 50 --follow).
[bold]purge[/bold] [--yes]        - Clear memory and databases.
[bold]update[/bold]               - Self-update from Git.
[bold]registry[/bold] list|info   - Manage the Plugin Registry.
[bold]clear[/bold]                - Clear the terminal screen.
[bold]version[/bold]              - Show Archangel version.
[bold]exit[/bold] / [bold]quit[/bold]        - Shutdown Archangel.

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

    _flag = lambda n: f"--{n}" in _args
    _opt = lambda n: _args[_args.index(f"--{n}") + 1] if f"--{n}" in _args and _args.index(f"--{n}") + 1 < len(_args) else None

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
        from archangel.cli.chat_repls import run_agents_hub_repl
        run_agents_hub_repl(console)

    elif _cmd in ("groupchat", "group-chat", "archangel.agents.groupchat", "archangel.groupchat"):
        from archangel.cli.chat_repls import run_groupchat_repl
        run_groupchat_repl(console)

    elif _cmd.startswith("archangel.") or _cmd in (
        "collector", "intelligence", "scoring", "guardian", "commander", "storage", "notification"
    ):
        action = _args[0] if _args else "status"
        payload = " ".join(_args[1:]) if len(_args) > 1 else (" ".join(_args) if _args else "")
        from archangel.cli.chat_repls import cmd_agent_dispatch
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
        from archangel.cli.chat_repls import run_chat_repl
        run_chat_repl(console)

    elif _cmd == "clear":
        cmd_clear(console)

    elif _cmd == "version":
        cmd_version(console)

    else:
        console.print(f"[red]Unknown command:[/] {_cmd}")
        console.print("Type [bold]help[/] or [bold]help detailed[/] for available commands.")

    return True

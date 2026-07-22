"""Slash commands for the chat REPL — handled client-side, no LLM calls."""

import os
import yaml
from pathlib import Path
from datetime import datetime
from prompt_toolkit.completion import Completer, Completion
from typing import Any

# Tracks provider selected via /models so the chat REPL can pick it up
_active_model_provider: str | None = None


# ---------------------------------------------------------------------------
# Slash command definitions
# ---------------------------------------------------------------------------

CHAT_COMMAND_FLAGS: dict[str, list[str]] = {
    "env":     [],
    "config":  ["show", "validate"],
    "key":     ["list"],
    "models":  ["status", "change", "groq"],
    "logs":    ["50", "100", "200"],
    "clear":   [],
    "history": [],
    "export":  [],
    "help":    [],
    "exit":    [],
}


def _get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def cmd_env(args: list[str], console: Any, history: list) -> bool:
    """Open .env in default editor."""
    env_path = _get_project_root() / ".env"
    if not env_path.exists():
        console.print(f"[red]archangel> .env not found at {env_path}[/]")
        return False
    os.startfile(str(env_path))
    return False


_KEY_PROVIDERS = ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC", "OPENROUTER", "OPENCODEZEN"]


def cmd_key(args: list[str], console: Any, history: list) -> bool:
    """View or set API keys. Usage: /key [PROVIDER <value>]"""

    env_path = _get_project_root() / ".env"

    # --- list mode ---
    if not args or args[0] == "list":
        console.print()
        console.print("[bold]archangel>[/] API keys:")
        console.print()
        for prov in _KEY_PROVIDERS:
            val = os.environ.get(prov, "")
            masked = "********" if val else "(not set)"
            status = "[green]✓[/]" if val else "[red]✗[/]"
            console.print(f"[bold]archangel>[/]   {status} {prov:10s} {masked}")
        console.print()
        console.print("[bold]archangel>[/] Set one: [dim]/key GROK gsk_your_key[/]")
        console.print()
        return False

    # --- set mode: /key PROVIDER value ---
    if len(args) < 2:
        console.print("[bold]archangel>[/] Usage: /key <PROVIDER> <value> or /key list")
        return False

    provider = args[0].upper()
    if provider not in _KEY_PROVIDERS:
        console.print(f"[bold]archangel>[/] [red]Unknown provider: {provider}.[/] Options: {', '.join(_KEY_PROVIDERS)}")
        return False

    value = args[1]

    # Save to .env
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    found = False
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{provider}="):
            new_lines.append(f"{provider}={value}")
            found = True
        elif any(stripped.startswith(k + "=") for k in _KEY_PROVIDERS):
            new_lines.append(line)
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{provider}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Also update current env so it takes effect immediately
    os.environ[provider] = value

    console.print(f"[bold]archangel>[/] [green]✓ {provider} key saved to .env[/]")
    return False


def cmd_config(args: list[str], console: Any, history: list) -> bool:
    """Open, show, or validate config."""
    from archangel.config.manager import load_config, validate_config

    if not args:
        config_path = _get_project_root() / "configs" / "config.yaml"
        if not config_path.exists():
            console.print(f"[red]archangel> Config not found at {config_path}[/]")
            return False
        os.startfile(str(config_path))
        return False

    if args[0] == "show":
        cfg = load_config()
        console.print()
        for line in yaml.dump(cfg, default_flow_style=False).strip().splitlines():
            console.print(f"[bold]archangel>[/] {line}")
        console.print()
        return False

    if args[0] == "validate":
        cfg = load_config()
        errors = validate_config(cfg)
        console.print()
        if errors:
            for e in errors:
                console.print(f"[bold]archangel>[/] [red]✗ {e}[/]")
        else:
            console.print("[bold]archangel>[/] [green]✓ Config is valid.[/]")
        console.print()
        return False

    console.print("[bold]archangel>[/] Usage: /config [show|validate] or /config (opens editor)")
    return False


def cmd_models(args: list[str], console: Any, history: list) -> bool:
    """List providers, show status, or switch provider."""
    from archangel.agents.chat import PROVIDER_MAP

    _api_keys = ["OPENCODEZEN", "OPENROUTER", "GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]

    # --- existing non-interactive modes ---
    if args:
        if args[0] == "status":
            console.print()
            console.print("[bold]archangel>[/] Available providers:")
            console.print()
            for key in _api_keys:
                info = PROVIDER_MAP.get(key, {})
                model = info.get("model", "unknown")
                has_key = "✓" if os.environ.get(key) else "✗"
                status_label = "active" if os.environ.get(key) else "no key"
                console.print(f"[bold]archangel>[/]   {key:10s} {has_key} {status_label:8s} {model}")
            console.print()
            return False

        if args[0] == "change" and len(args) > 1:
            provider = args[1].upper()
            if provider not in PROVIDER_MAP:
                console.print(f"[bold]archangel>[/] [red]Unknown provider: {provider}. Options: {', '.join(_api_keys)}[/]")
                return False
            if not os.environ.get(provider):
                console.print(f"[bold]archangel>[/] [red]No API key set for {provider}. Add {provider}=your_key to .env first.[/]")
                return False

            env_path = _get_project_root() / ".env"
            _save_provider_to_env(provider, env_path)
            console.print(f"[bold]archangel>[/] [green]Switched to {provider} ({PROVIDER_MAP[provider]['model']})[/]")
            console.print("[bold]archangel>[/] [dim]Provider updated. Next message will use new model.[/]")
            return False

        # Allow shorthand: /models opencodezen = /models change opencodezen
        if args[0].upper() in PROVIDER_MAP:
            provider = args[0].upper()
            if not os.environ.get(provider):
                console.print(f"[bold]archangel>[/] [red]No API key set for {provider}. Add {provider}=your_key to .env first.[/]")
                return False

            env_path = _get_project_root() / ".env"
            _save_provider_to_env(provider, env_path)
            console.print(f"[bold]archangel>[/] [green]Switched to {provider} ({PROVIDER_MAP[provider]['model']})[/]")
            console.print("[bold]archangel>[/] [dim]Provider updated. Next message will use new model.[/]")
            return False

        if args[0] == "groq":
            _list_groq_models(console)
            return False

        console.print(f"[bold]archangel>[/] Usage: /models [status|change <provider>|{'|'.join(_api_keys)}]")
        return False

    # --- interactive picker ---
    # Determine current provider (first one with a key set, in priority order)
    current = next((k for k in _api_keys if os.environ.get(k)), _api_keys[0])

    # Build entries — current one first, then the rest sorted
    others = sorted(k for k in _api_keys if k != current)
    ordered = [current] + others

    values = []
    for key in ordered:
        info = PROVIDER_MAP.get(key, {})
        model = info.get("model", "unknown")
        has_key = "✓" if os.environ.get(key) else "✗"
        label = f"{has_key} {key:10s} {model}"
        values.append((key, label))

    try:
        from prompt_toolkit.shortcuts import radiolist_dialog

        picked = radiolist_dialog(
            title="Select AI Provider",
            text="Arrow keys to navigate, Enter to confirm, Esc to cancel.",
            values=values,
            default=current,
        ).run()
    except Exception:
        # Fallback if prompt_toolkit dialog isn't available
        picked = _fallback_model_picker(values, current, console)

    if picked is None or picked == current:
        return False

    env_path = _get_project_root() / ".env"
    _save_provider_to_env(picked, env_path)
    console.print(f"[bold]archangel>[/] [green]Switched to {picked} ({PROVIDER_MAP[picked]['model']})[/]")
    console.print("[bold]archangel>[/] [dim]Provider updated. Next message will use new model.[/]")
    return False


def _save_provider_to_env(provider: str, env_path: Path) -> None:
    """Rewrite .env so the chosen provider's key line comes first among API keys."""
    global _active_model_provider
    _active_model_provider = provider.upper()
    _api_keys = ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]
    if not env_path.exists():
        env_path.write_text(f"{provider}={os.environ.get(provider, '')}\n", encoding="utf-8")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    chosen_line = f"{provider}={os.environ.get(provider, '')}"
    other_key_lines: list[str] = []
    non_key_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        matched = False
        for k in _api_keys:
            if stripped.startswith(k + "="):
                if k == provider:
                    matched = True  # will be inserted at top
                else:
                    other_key_lines.append(line)
                matched = True
                break
        if not matched:
            non_key_lines.append(line)

    new_lines = []
    # chosen provider first
    if not any(l.strip() == chosen_line for l in lines):
        new_lines.append(chosen_line)
    else:
        new_lines.append(chosen_line)

    new_lines.extend(other_key_lines)
    new_lines.extend(non_key_lines)
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _fetch_groq_models() -> list[str] | None:
    """Fetch available models from Groq API. Returns None on failure."""
    import requests

    api_key = os.environ.get("GROQ")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            status = m.get("object", "")
            if mid and status == "model":
                models.append(mid)
        models.sort()
        return models
    except Exception:
        return None


def _save_model_to_env(model_id: str, provider: str = "GROQ") -> None:
    """Save GROQ_MODEL=<model_id> to .env and os.environ."""
    key = f"{provider}_MODEL"
    os.environ[key] = model_id
    env_path = _get_project_root() / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            new_lines.append(f"{key}={model_id}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={model_id}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _list_groq_models(console: Any) -> None:
    """Fetch available Groq models and let user pick one."""
    api_key = os.environ.get("GROQ")
    if not api_key:
        console.print("[bold]archangel>[/] [red]No GROQ API key set. Use /key GROQ <your_key> first.[/]")
        return

    console.print("[bold]archangel>[/] [dim]Fetching available Groq models...[/]")
    models = _fetch_groq_models()
    if models is None:
        console.print("[bold]archangel>[/] [red]Failed to fetch models from Groq API. Check your key and network.[/]")
        return

    if not models:
        console.print("[bold]archangel>[/] [red]No models returned by Groq API.[/]")
        return

    current_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    values = [(m, m) for m in models]
    default = current_model if current_model in models else models[0]

    try:
        from prompt_toolkit.shortcuts import radiolist_dialog
        picked = radiolist_dialog(
            title="Select Groq Model",
            text="Arrow keys to navigate, Enter to confirm, Esc to cancel.",
            values=values,
            default=default,
        ).run()
    except Exception:
        picked = _fallback_model_picker(values, default, console)

    if picked is None or picked == current_model:
        return

    _save_model_to_env(picked)
    console.print(f"[bold]archangel>[/] [green]Groq model set to: {picked}[/]")
    console.print("[bold]archangel>[/] [dim]Model updated. Next message will use the new model.[/]")


def _fallback_model_picker(
    values: list[tuple[str, str]],
    current: str,
    console: Any,
) -> str | None:
    """Simple numbered list fallback when prompt_toolkit dialog isn't available."""
    console.print()
    console.print("[bold]archangel>[/] Available providers:")
    console.print()
    for i, (key, label) in enumerate(values, 1):
        marker = "[green]>[/]" if key == current else " "
        console.print(f"  {marker} {i}. {label}")
    console.print()
    try:
        choice = input("Enter number or provider name (Enter to cancel): ").strip()
        if not choice:
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(values):
                return values[idx][0]
        choice = choice.upper()
        for key, _ in values:
            if key == choice:
                return key
    except (EOFError, KeyboardInterrupt):
        pass
    return None


def cmd_clear(args: list[str], console: Any, history: list) -> bool:
    """Clear screen and reprint banner."""
    os.system("cls" if os.name == "nt" else "clear")
    from archangel.cli.banner import render_banner
    render_banner(console)
    return False


def cmd_history_fn(args: list[str], console: Any, history: list) -> bool:
    """Show last N messages from chat history."""
    limit = int(args[0]) if args and args[0].isdigit() else 10
    # Skip system message
    messages = [m for m in history if m["role"] != "system"]
    recent = messages[-limit:]
    console.print()
    for msg in recent:
        role = "you" if msg["role"] == "user" else "archangel"
        # Skip long output blocks
        content = msg["content"]
        if "<output>" in content or "<search_results>" in content or "<screenshot>" in content:
            content = "[...]"
        for line in content.splitlines()[:3]:
            console.print(f"[bold]archangel>[/] [{role}] {line}")
    console.print()
    return False


def cmd_export(args: list[str], console: Any, history: list) -> bool:
    """Export chat history to markdown file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"chat_export_{timestamp}.md"
    export_path = _get_project_root() / filename

    lines = ["# Archangel Chat Export\n"]
    for msg in history:
        if msg["role"] == "system":
            continue
        role = "User" if msg["role"] == "user" else "Archangel"
        content = msg["content"]
        if "<output>" in content:
            content = "[command output]"
        elif "<search_results>" in content:
            content = "[search results]"
        elif "<screenshot>" in content:
            content = "[screenshot]"
        lines.append(f"**{role}:** {content}\n")

    export_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[bold]archangel>[/] [green]Chat exported to {filename}[/]")
    return False


def cmd_help(args: list[str], console: Any, history: list) -> bool:
    """List all slash commands."""
    console.print()
    console.print("[bold]archangel>[/] Slash commands:")
    console.print()
    for name, info in COMMANDS.items():
        console.print(f"[bold]archangel>[/]   /{name:12s} {info['desc']}")
    console.print()
    return False


def cmd_logs_slash(args: list[str], console: Any, history: list) -> bool:
    """View runtime logs."""
    from archangel.cli.main import cmd_logs as _main_cmd_logs
    tail = int(args[0]) if args and args[0].isdigit() else 50
    _main_cmd_logs(console, tail=tail)
    return False


COMMANDS = {
    "env":     {"handler": cmd_env,          "desc": "Open .env in editor"},
    "config":  {"handler": cmd_config,       "desc": "Open/show/validate config"},
    "key":     {"handler": cmd_key,          "desc": "View/set API keys"},
    "models":  {"handler": cmd_models,       "desc": "List/switch AI providers"},
    "logs":    {"handler": cmd_logs_slash,   "desc": "View runtime log lines"},
    "clear":   {"handler": cmd_clear,        "desc": "Clear chat screen"},
    "history": {"handler": cmd_history_fn,   "desc": "Show chat history (N)"},
    "export":  {"handler": cmd_export,       "desc": "Export chat to .md file"},
    "help":    {"handler": cmd_help,         "desc": "List all slash commands"},
    "exit":    {"handler": cmd_exit,         "desc": "Exit chat"},
}


def handle_slash_command(raw: str, console: Any, history: list) -> bool:
    """Parse and execute a slash command. Returns True if should exit chat."""
    parts = raw[1:].strip().split()
    if not parts:
        console.print("[bold]archangel>[/] Type /help for available commands.")
        return False

    cmd_name = parts[0].lower()
    args = parts[1:]

    if cmd_name not in COMMANDS:
        console.print(f"[bold]archangel>[/] [red]Unknown command: /{cmd_name}. Type /help for available commands.[/]")
        return False

    return COMMANDS[cmd_name]["handler"](args, console, history)


# ---------------------------------------------------------------------------
# Tab completer for slash commands in chat REPL
# ---------------------------------------------------------------------------


class _ChatCompleter(Completer):
    """Tab completer for slash commands in the chat REPL."""

    def get_completions(self, document, complete_event):
        try:
            text = document.text_before_cursor

            if not text.startswith("/"):
                return

            words = text.split()

            # "/" alone or "/partial" — show matching commands
            if len(words) <= 1 and not text.endswith(" "):
                prefix = words[0] if words else "/"
                for cmd in sorted(CHAT_COMMAND_FLAGS.keys()):
                    full = f"/{cmd}"
                    if full.startswith(prefix):
                        yield Completion(full, start_position=-len(prefix))
                return

            # "/command" + space — show subcommands
            if text.endswith(" ") and len(words) >= 2:
                cmd = words[0].lower().lstrip("/")
                subcommands = CHAT_COMMAND_FLAGS.get(cmd, [])
                for sub in subcommands:
                    yield Completion(sub, start_position=0)
                return

            # "/command partial" — filter subcommands
            if len(words) >= 2 and not text.endswith(" "):
                cmd = words[0].lower().lstrip("/")
                partial = words[-1]
                subcommands = CHAT_COMMAND_FLAGS.get(cmd, [])
                for sub in subcommands:
                    if sub.startswith(partial):
                        yield Completion(sub, start_position=-len(partial))
                return

        except Exception:
            pass
        return

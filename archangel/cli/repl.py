"""Interactive REPL sessions, keybindings, and agent chat routers for Archangel CLI."""

from __future__ import annotations

from pathlib import Path



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


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _classify_agent_topic(text: str) -> str:
    """Classify user message topic and return matching agent name."""
    t = text.lower()
    if "@collector" in t or ("collector" in t and ("feed" in t or "scrape" in t or "source" in t)):
        return "collector"
    if "@intelligence" in t or ("intelligence" in t and ("lead" in t or "intent" in t or "classify" in t)):
        return "intelligence"
    if "@scoring" in t or ("scoring" in t and ("rank" in t or "score" in t or "budget" in t or "urgency" in t)):
        return "scoring"
    if "@guardian" in t or ("guardian" in t and ("health" in t or "error" in t or "status" in t or "crash" in t)):
        return "guardian"
    if "@commander" in t or ("commander" in t and ("task" in t or "orchestrat" in t or "run" in t)):
        return "commander"
    if "@storage" in t or ("storage" in t and ("database" in t or "sqlite" in t or "count" in t or "export" in t)):
        return "storage"
    if "@notification" in t or ("notification" in t and ("telegram" in t or "discord" in t or "alert" in t)):
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
    """Create custom key bindings for Ctrl key combinations."""
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


def create_prompt_session(
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

import os
import sys
import time
from rich.console import Console
from archangel.cli.parser import _execute_repl_command
from archangel.cli.handlers import cmd_terminate

DATA_DIR = Path("data")
SHUTDOWN_SENTINEL = DATA_DIR / ".archangel_shutdown"
PID_FILE = DATA_DIR / ".archangel_pid"
REPL_HISTORY = Path.home() / ".archangel_history"
REPL_COMMANDS = [
    "status", "watch", "scan", "doctor", "config",
    "export", "logs", "purge", "update", "version",
    "registry", "chat", "automate", "clear", "help", "exit", "quit"
]

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
    def get_completions(self, document, complete_event):
        try:
            from prompt_toolkit.completion import Completion
            text = document.text_before_cursor
            words = text.split()
            if not words:
                for cmd in sorted(REPL_COMMANDS):
                    yield Completion(cmd, start_position=0)
                return
            if len(words) == 1 and not text.endswith(" "):
                prefix = words[0]
                for cmd in sorted(REPL_COMMANDS):
                    if cmd.startswith(prefix):
                        yield Completion(cmd, start_position=-len(prefix))
                return
            if text.endswith(" "):
                cmd = words[0].lower()
                for flag in _COMMAND_FLAGS.get(cmd, []):
                    yield Completion(flag, start_position=0)
                return
        except Exception:
            pass
        return

def _run_simple_repl(console: Console) -> None:
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
    if not sys.stdin.isatty():
        console.print("[yellow]Interactive terminal required. Run [bold]archangel summon[/] in cmd.exe or PowerShell.[/]")
        return
    try:
        import msvcrt
        msvcrt.get_osfhandle(sys.stdin.fileno())
    except (ImportError, OSError, AttributeError):
        _run_simple_repl(console)
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    SHUTDOWN_SENTINEL.unlink(missing_ok=True)

    _old_term = os.environ.pop("TERM", None)
    try:
        REPL_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        completer = _ArchangelCompleter()
        session = create_prompt_session(
            "archangel.main> ",
            ".archangel_repl_history",
            completer=completer,
            complete_while_typing=False,
        )

        _repl_down = False
        _last_ctrl_c: float = 0.0
        _DOUBLE_CTRL_C_WINDOW = 3.0

        while not _repl_down:
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
        PID_FILE.unlink(missing_ok=True)
        SHUTDOWN_SENTINEL.unlink(missing_ok=True)
        if _old_term is not None:
            os.environ["TERM"] = _old_term

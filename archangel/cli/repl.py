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

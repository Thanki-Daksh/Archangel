"""Action execution engine — translates parsed actions into pyautogui calls."""

from __future__ import annotations

from typing import Any

# Keywords that make an action "destructive" — requires user confirmation
_DESTRUCTIVE_KEYWORDS: list[str] = [
    "delete", "remove", "format", "shutdown", "rm",
    "kill", "uninstall", "del", "rd", "erase",
]


def _is_destructive(action: dict[str, Any]) -> bool:
    """Check if the action involves destructive operations."""
    action_type = action.get("action", "")
    text = action.get("text", "").lower()
    key = action.get("key", "").lower()
    keys = " ".join(action.get("keys", [])).lower()

    combined = f"{action_type} {text} {key} {keys}"
    for kw in _DESTRUCTIVE_KEYWORDS:
        if kw in combined:
            return True
    return False


def confirm_destructive(action: dict[str, Any]) -> bool:
    """Check if action is destructive and ask user confirmation if so.

    Returns True if action is safe OR user confirmed it.
    Returns False if user declined a destructive action.
    """
    if not _is_destructive(action):
        return True

    from rich.console import Console
    console = Console()
    console.print(f"\n[yellow]⚠ Destructive action detected:[/] {action}")
    try:
        answer = input("This action may be destructive. Confirm? y/N: ").strip().lower()
        return answer == "y"
    except (EOFError, KeyboardInterrupt):
        return False


def execute_action(action: dict[str, Any]) -> bool:
    """Execute a parsed action via pyautogui. Returns True on success."""
    import pyautogui

    action_type = action.get("action", "")
    try:
        if action_type == "click":
            pyautogui.click(action["x"], action["y"])

        elif action_type == "double_click":
            pyautogui.doubleClick(action["x"], action["y"])

        elif action_type == "type":
            pyautogui.typewrite(action["text"], interval=0.05)

        elif action_type == "scroll":
            direction = action.get("direction", "down")
            amount = 3 if direction == "up" else -3
            pyautogui.scroll(amount)

        elif action_type == "key":
            pyautogui.press(action["key"])

        elif action_type == "hotkey":
            pyautogui.hotkey(*action["keys"])

        elif action_type == "drag":
            pyautogui.drag(action["dx"], action["dy"])

        elif action_type == "done":
            # No-op; orchestrator handles it
            return True

        else:
            return False

        return True

    except Exception as exc:
        from rich.console import Console
        Console().print(f"[red]Action failed: {exc}[/]")
        return False

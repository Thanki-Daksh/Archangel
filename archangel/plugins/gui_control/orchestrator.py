"""Orchestrator — main loop: capture → analyze → act → repeat."""

from __future__ import annotations

import time
from typing import Any

from rich.console import Console

from .screen import capture_screen, image_to_base64
from .vision import analyze_frame
from .actions import confirm_destructive, execute_action

_console = Console()


def _print_step(
    step: int,
    action: dict[str, Any],
    dry_run: bool = False,
) -> None:
    """Pretty-print the current step and action."""
    label = "[bold cyan]Step[/]"
    prefix = " [yellow]DRY RUN[/]" if dry_run else ""
    _console.print(f"\n{label} {step}:{prefix}")
    for k, v in action.items():
        _console.print(f"  [dim]{k}:[/] {v}")


def run_task(
    task: str,
    max_steps: int = 50,
    dry_run: bool = False,
) -> str:
    """Main GUI automation loop.

    Args:
        task: Natural-language description of what to do.
        max_steps: Maximum number of actions before giving up.
        dry_run: If True, print actions without executing them.

    Returns:
        Summary string (success or failure message).
    """
    history: list[dict[str, Any]] = []

    _console.print(f"\n[bold]Task:[/] {task}")
    _console.print(f"[dim]Max steps: {max_steps}  |  Dry run: {dry_run}[/]")

    for step in range(1, max_steps + 1):
        # 1. Capture screen
        try:
            screenshot = capture_screen()
        except Exception as exc:
            msg = f"Screenshot failed at step {step}: {exc}"
            _console.print(f"[red]{msg}[/]")
            return msg

        # 2. Analyze with vision model
        try:
            image_b64 = image_to_base64(screenshot)
        except Exception as exc:
            msg = f"Image encoding failed: {exc}"
            _console.print(f"[red]{msg}[/]")
            return msg

        _console.print(f"\n[dim]Analyzing screenshot ({step}/{max_steps})...[/]")
        action = analyze_frame(image_b64, task, history)

        _print_step(step, action, dry_run=dry_run)

        # 3. Check if done
        if action.get("action") == "done":
            summary = action.get("summary", "Task complete.")
            _console.print(f"\n[bold green]✓ Done:[/] {summary}")
            return summary

        # 4. Execute action (with safety check for destructive ops)
        if dry_run:
            _console.print("  [dim]→ (skipped — dry run)[/]")
        else:
            # Prompt confirmation only when action is destructive
            confirmed = confirm_destructive(action)
            if not confirmed:
                _console.print("  [yellow]→ Skipped (user declined)[/]")
                continue
            execute_action(action)

        # 5. Log to history
        history.append(action)

        # 6. Wait between actions so UI can update
        time.sleep(1.5)

    msg = f"Max steps ({max_steps}) reached. Task incomplete."
    _console.print(f"[yellow]{msg}[/]")
    return msg

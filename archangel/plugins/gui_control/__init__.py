"""GUI Control plugin — autonomous GUI control via vision models.

Exposes a GUIAgent class as the plugin entry point.
"""

from __future__ import annotations

from .orchestrator import run_task


class GUIAgent:
    """Autonomous GUI control agent powered by vision AI.

    Captures screenshots, sends them to a vision model (Gemini/Groq),
    parses the model's action decision, and executes it via pyautogui.
    """

    def run(
        self,
        task: str,
        max_steps: int = 50,
        dry_run: bool = False,
    ) -> str:
        """Execute a GUI automation task.

        Args:
            task: Natural-language task description.
            max_steps: Maximum actions to attempt.
            dry_run: If True, print actions without executing.

        Returns:
            Summary string with result.
        """
        return run_task(task=task, max_steps=max_steps, dry_run=dry_run)

"""LLM-powered chat agent and command executor for the Archangel chat REPL."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

import io
import base64

from ddgs import DDGS

# Tracks last-selected provider (set by /models change command)
_active_provider: str | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVIDER_MAP: dict[str, dict[str, Any]] = {
    "GROQ": {
        "package": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "GEMINI": {
        "package": "google-genai",
        "model": "gemini-3.5-flash",
    },
    "OPENAI": {
        "package": "openai",
        "model": "gpt-4o",
    },
    "ANTHROPIC": {
        "package": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
    },
}

# Blocked command patterns (case-insensitive substring match)
BLOCKED_PATTERNS: list[str] = [
    "rm -rf /",
    "format ",
    "del /s",
    "shutdown",
    "reboot",
    "taskkill /f",
    "Remove-Item -Recurse -Force",
]

# Unix → PowerShell translation table (first matching prefix wins)
TRANSLATIONS: dict[str, str] = {
    "ls": "Get-ChildItem",
    "pwd": "Get-Location",
    "cat": "Get-Content",
    "cd": "Set-Location",
    "rm": "Remove-Item",
    "open": "Start-Process",
}


# ---------------------------------------------------------------------------
# CommandExecutor
# ---------------------------------------------------------------------------


class CommandExecutor:
    """Translate and execute shell commands with safety rails."""

    @staticmethod
    def _translate(cmd: str) -> str:
        """Translate common Unix commands to PowerShell equivalents."""
        stripped = cmd.strip()
        for unix, ps in TRANSLATIONS.items():
            if stripped == unix or stripped.startswith(unix + " "):
                # Preserve arguments after the command name
                rest = stripped[len(unix):]
                cmd = ps + rest
                break
        return cmd

    @staticmethod
    def _is_blocked(cmd: str) -> bool:
        """Check command against the safety blocklist."""
        lower = cmd.lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in lower:
                return True
        return False

    @staticmethod
    def _add_safety_flags(cmd: str) -> str:
        """Add ``-Confirm`` to ``Remove-Item`` commands that don't have it."""
        if cmd.strip().startswith("Remove-Item") and "-Confirm" not in cmd:
            cmd = re.sub(
                r"^Remove-Item\b",
                "Remove-Item -Confirm",
                cmd,
                count=1,
            )
        return cmd

    def execute(self, command: str) -> str:
        """Execute a command and return its output.

        Steps:
        1. Blocklist check  → refuse if dangerous
        2. Translation      → Unix → PowerShell
        3. Safety flags     → -Confirm on Remove-Item
        4. subprocess.run   → 30 s timeout
        """
        cmd = command.strip()
        if not cmd:
            return ""

        # 1. Blocklist
        if self._is_blocked(cmd):
            return (
                "[SAFETY] Command blocked: this operation is too dangerous "
                "to run from the chat REPL."
            )

        # 2. Translation
        cmd = self._translate(cmd)

        # 3. Safety flags
        cmd = self._add_safety_flags(cmd)

        # 4. Execute
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            output = stdout
            if stderr:
                output += "\n" + stderr if output else stderr
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "[ERROR] Command timed out after 30 seconds."
        except Exception as exc:
            return f"[ERROR] {exc}"


class WebSearch:
    """Search the web using DuckDuckGo."""

    @staticmethod
    def search(query: str, max_results: int = 3) -> str:
        """Return top search results as formatted text."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("href", "No URL")
                body = r.get("body", "No description")
                lines.append(f"{i}. {title}\n   URL: {url}\n   {body}")
            return "\n\n".join(lines)
        except Exception as exc:
            return f"Search failed: {exc}"


class ScreenCapture:
    """Capture the user's screen and return a base64-encoded image."""

    @staticmethod
    def capture() -> str:
        """Take a screenshot, resize to 1024x576 JPEG, return base64."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.resize((1024, 576))
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=50)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as exc:
            return f"[ERROR] Screenshot failed: {exc}"


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


class LLMClient:
    """Detect the available AI provider and wrap its chat API."""

    def __init__(self) -> None:
        self.provider: str | None = None
        self.model: str = ""
        self._client: Any = None
        self._detect_and_init()

    def _detect_and_init(self) -> None:
        """Scan env for provider keys and initialise the corresponding client.

        Respects _active_provider if set (by /models change command).
        """
        global _active_provider

        # If a provider was explicitly selected, use it
        if _active_provider and os.environ.get(_active_provider):
            api_key = os.environ.get(_active_provider)
            self.provider = _active_provider
            info = PROVIDER_MAP[_active_provider].copy()
            self.model = os.environ.get(f"{_active_provider}_MODEL") or info["model"]
            self._init_client(_active_provider, api_key, info)
            return

        # Fallback: scan in priority order
        for key in ("GROQ", "GEMINI", "OPENAI", "ANTHROPIC"):
            api_key = os.environ.get(key)
            if not api_key:
                continue
            self.provider = key
            info = PROVIDER_MAP[key].copy()
            self.model = os.environ.get(f"{key}_MODEL") or info["model"]
            self._init_client(key, api_key, info)
            return

        raise RuntimeError(
            "No API key found. Set one of GROQ, GEMINI, OPENAI, or "
            "ANTHROPIC in your environment or .env file."
        )

    def _init_client(self, key: str, api_key: str, info: dict[str, Any]) -> None:
        base_url = info.get("base_url")

        if key == "GROQ":
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key, base_url=base_url)

        elif key == "GEMINI":
            from google import genai as google_genai
            self._client = google_genai.Client(api_key=api_key)

        elif key == "OPENAI":
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)

        elif key == "ANTHROPIC":
            from anthropic import Anthropic

            self._client = Anthropic(api_key=api_key)

    def supports_vision(self) -> bool:
        """Check if the current provider supports image/vision input."""
        return self.provider in ("GEMINI", "OPENAI", "ANTHROPIC")

    def switch_provider(self, provider: str | None = None) -> None:
        """Switch provider only if it actually changed.

        If *provider* is given, set it as the active choice so subsequent
        calls to _detect_and_init use it.  Otherwise re-detect from env.
        """
        global _active_provider
        new_provider = provider.upper() if provider else None

        # Same provider — don't recreate the client (e.g. Google HTTP conns)
        if new_provider == self.provider:
            return

        if new_provider:
            _active_provider = new_provider
        self.provider = None
        self.model = ""
        self._client = None
        self._detect_and_init()

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a message list to the provider and return the response text."""
        try:
            if self.provider == "GROQ":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                return response.choices[0].message.content or ""

            if self.provider == "GEMINI":
                # Convert OpenAI-style messages to Gemini format
                contents: list[dict[str, Any]] = []
                for msg in messages:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg["content"]}]})
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
                return response.text

            if self.provider == "OPENAI":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                return response.choices[0].message.content or ""

            if self.provider == "ANTHROPIC":
                # Extract system message if present
                system: str | None = None
                anthro_messages: list[dict[str, str]] = []
                for msg in messages:
                    if msg["role"] == "system":
                        system = msg["content"]
                        continue
                    anthro_messages.append({
                        "role": "user" if msg["role"] == "user" else "assistant",
                        "content": msg["content"],
                    })

                response = self._client.messages.create(
                    model=self.model,
                    system=system,
                    messages=anthro_messages,
                    max_tokens=4096,
                )
                return response.content[0].text

            raise RuntimeError(f"Unsupported provider: {self.provider}")

        except Exception as exc:
            if "429" in str(exc) or "quota" in str(exc).lower():
                # Auto-fallback to next available provider on quota/rate-limit
                fallback_order = ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]
                for next_provider in fallback_order:
                    if next_provider != self.provider and os.environ.get(next_provider):
                        self.switch_provider(next_provider)
                        return self.chat(messages)
            raise


# ---------------------------------------------------------------------------
# Convenience: extract <execute>...</execute> tags
# ---------------------------------------------------------------------------

EXECUTE_RE = re.compile(r"<execute>(.*?)</execute>", re.DOTALL)


def extract_execute_commands(text: str) -> list[str]:
    """Return all ``<execute>...</execute>`` blocks found in *text*."""
    return [block.strip() for block in EXECUTE_RE.findall(text)]


SEARCH_RE = re.compile(r"<search>(.*?)</search>", re.DOTALL)


def extract_search_queries(text: str) -> list[str]:
    """Return all <search>...</search> blocks found in text."""
    return [block.strip() for block in SEARCH_RE.findall(text)]


SCREENSHOT_RE = re.compile(r"<screenshot></screenshot>", re.DOTALL)


def extract_screenshot_requests(text: str) -> list[str]:
    """Return all <screenshot></screenshot> blocks found in text."""
    return [block.strip() for block in SCREENSHOT_RE.findall(text)]

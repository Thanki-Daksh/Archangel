"""Vision model integration — sends screenshots to AI and parses actions.

Supports Gemini (primary) and Groq (fallback) for vision analysis.
Uses plain requests — no heavy SDK imports.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

_VISION_SYSTEM_PROMPT = """You are a GUI agent. Given this screenshot and task, tell me the next action. Respond with JSON only — no explanations, no markdown.

Actions:
{"action": "click", "x": number, "y": number}
{"action": "double_click", "x": number, "y": number}
{"action": "type", "text": string}
{"action": "scroll", "direction": "up"|"down"}
{"action": "key", "key": string}
{"action": "hotkey", "keys": [string, ...]}
{"action": "drag", "dx": number, "dy": number}
{"action": "done", "summary": string}

Example: {"action": "click", "x": 500, "y": 300}
Example: {"action": "done", "summary": "Opened Notepad and typed hello world."}"""


def _call_gemini(image_b64: str, task: str, history: list[dict]) -> str:
    """Send screenshot to Gemini 2.0 Flash and return raw text response."""
    api_key = os.environ.get("GEMINI")
    if not api_key:
        return ""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{_VISION_SYSTEM_PROMPT}\n\nTask: {task}"},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "") if parts else ""
    except Exception as exc:
        return f"[API_ERROR] Gemini: {exc}"


def _call_groq(image_b64: str, task: str, history: list[dict]) -> str:
    """Send screenshot to Groq vision endpoint (OpenAI-compatible)."""
    api_key = os.environ.get("GROQ")
    if not api_key:
        return ""

    url = "https://api.groq.com/openai/v1/chat/completions"

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _VISION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Task: {task}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}",
                    },
                },
            ],
        },
    ]

    try:
        resp = requests.post(
            url,
            json={
                "model": "llama-3.2-90b-vision-preview",
                "messages": messages,
                "max_tokens": 512,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")
    except Exception as exc:
        return f"[API_ERROR] Groq: {exc}"


def analyze_frame(
    image_b64: str,
    task: str,
    history: list[dict],
    provider: str = "gemini",
) -> dict[str, Any]:
    """Send screenshot to vision model, return parsed action dict.

    Tries primary provider first, falls back to secondary if primary fails.
    Returns a dict with at minimum {"action": "done", "summary": "error msg"}
    on failure.
    """
    raw = ""

    if provider == "gemini":
        raw = _call_gemini(image_b64, task, history)
        if not raw or raw.startswith("[API_ERROR]"):
            raw = _call_groq(image_b64, task, history)

    elif provider == "groq":
        raw = _call_groq(image_b64, task, history)

    if not raw or raw.startswith("[API_ERROR]"):
        return {"action": "done", "summary": f"Vision API error: {raw}"}

    return parse_action(raw)


def parse_action(response: str) -> dict[str, Any]:
    """Parse model response into a structured action dict.

    Strips markdown fences and tries to extract JSON from the response.
    """
    text = response.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].strip()
        text = text.strip()

    # Try to find JSON in the response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Last resort — try eval-style parsing of known patterns
    action_map: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip().lower()
        if "action" in line:
            for a in (
                "click", "double_click", "type", "scroll",
                "key", "hotkey", "drag", "done",
            ):
                if a in line:
                    action_map["action"] = a
                    break
        if '"x"' in line or "'x'" in line:
            nums = re.findall(r"\d+", line)
            if nums:
                action_map["x"] = int(nums[0])
        if '"y"' in line or "'y'" in line:
            nums = re.findall(r"\d+", line)
            if nums:
                action_map["y"] = int(nums[0])
        if '"text"' in line or "'text'" in line:
            m = re.search(r'["\']text["\']\s*:\s*["\'](.+?)["\']', line)
            if m:
                action_map["text"] = m.group(1)

    if action_map.get("action"):
        return action_map

    return {"action": "done", "summary": f"Could not parse action: {response[:200]}"}

"""Screen capture utilities: screenshot, resize, base64 encode."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image


def capture_screen() -> Image.Image:
    """Take a screenshot using pyautogui. Returns a PIL Image."""
    import pyautogui

    screenshot = pyautogui.screenshot()
    return screenshot


def image_to_base64(image: Image.Image, format: str = "JPEG") -> str:
    """Convert a PIL Image to a base64-encoded string.

    Default JPEG quality 50 for fast transmission to AI APIs.
    """
    import base64

    # Resize to a reasonable size for vision models
    image = image.resize((1024, 576))
    buffer = io.BytesIO()
    image.save(buffer, format=format.upper(), quality=50)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

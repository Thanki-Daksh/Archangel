"""Banner renderer — clears the terminal and displays the official Archangel ASCII art."""

import os
import shutil

from rich.console import Console
from rich.text import Text
from rich.style import Style

BANNER_ART = r"""
 █████╗ ██████╗  ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██╗
██╔══██╗██╔══██╗██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██║
███████║██████╔╝██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██║
██╔══██║██╔══██╗██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██║
██║  ██║██║  ██║╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝
"""

TAGLINE = "Opportunity is revealed to those who seek."


def _get_terminal_width() -> int:
    """Return the current terminal width, falling back to 80."""
    try:
        size = shutil.get_terminal_size()
        return size.columns
    except (ValueError, OSError):
        return 80


def render_banner(console: Console | None = None) -> None:
    """Clear the terminal and render the Archangel banner in rich style.

    The banner is rendered in a bold crimson/silver palette, with the tagline
    displayed underneath in italic white.
    """
    if console is None:
        console = Console()

    # Clear screen
    os.system("cls" if os.name == "nt" else "clear")

    width = _get_terminal_width()

    # Primary style: bold crimson with slight brightness
    primary = Style(color="#dc143c", bold=True)

    # Secondary style: silver/grey for the tagline
    tagline_style = Style(color="#c0c0c0", italic=True, bold=False)

    banner_text = Text(BANNER_ART, style=primary)
    tagline = Text(f"\n{TAGLINE}\n", style=tagline_style)

    combined = Text()
    combined.append(banner_text)
    combined.append(tagline)

    console.print(combined, justify="center", width=width)
    console.print()  # spacer

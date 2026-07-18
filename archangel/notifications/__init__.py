"""Message delivery — sends completed leads through configured channels."""

import logging
from datetime import datetime

from rich.console import Console
from rich.table import Table

from archangel.models import RawPost, LeadAnalysis, LeadScore

logger = logging.getLogger(__name__)


class NotificationAgent:
    """Delivers opportunities via Telegram, Discord, Email, or Desktop."""

    def __init__(self) -> None:
        self._console = Console()
        logger.debug("NotificationAgent created")

    def notify(self, post: RawPost, analysis: LeadAnalysis, score: LeadScore) -> None:
        if not analysis.is_lead:
            return

        category = analysis.category or "Uncategorized"
        urgency = analysis.urgency or "Medium"
        budget = analysis.estimated_budget or "Unknown"

        logger.info(
            "LEAD: [%s] %s | %s | budget=%s | score=%.1f | %s",
            category, urgency, post.author, budget, score.score, post.url,
        )

        table = Table(title=f"Lead Discovered — {category}", border_style="green")
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        table.add_row("Source", f"{post.source} / {post.channel}")
        table.add_row("Author", post.author)
        table.add_row("Confidence", f"{analysis.confidence:.0%}")
        table.add_row("Urgency", urgency)
        table.add_row("Budget", budget)
        table.add_row("Score", f"{score.score:.1f}/100")
        table.add_row("URL", post.url)
        if analysis.recommended_action:
            table.add_row("Action", analysis.recommended_action)
        try:
            self._console.print(table)
        except Exception:
            pass

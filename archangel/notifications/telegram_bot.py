"""TelegramSwarmBot — Runnable Telegram commands, live telemetry dashboard, and inline lead actions."""

import asyncio
import logging
import os
from typing import Any, Dict, Optional
from pathlib import Path

from archangel.agents.swarm.manager import SwarmManager
from archangel.outreach.engine import OutreachEngine
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


def render_telegram_dashboard(metrics: Dict[str, Any], elapsed: int, duration_str: str, active: bool) -> str:
    """Formats swarm telemetry metrics into a Telegram Markdown dashboard string."""
    status_icon = "🟢 RUNNING" if active else "🔴 STOPPED"
    scanned = metrics.get("scanned_count", 0)
    qualified = metrics.get("qualified_count", 0)
    disc_q = metrics.get("discovery_queue_size", 0)
    stor_q = metrics.get("storage_queue_size", 0)
    flushed = metrics.get("total_flushed", 0)
    failed = metrics.get("total_failed", 0)
    avg_speed = metrics.get("avg_flush_duration_ms", 0.0)

    mins, secs = divmod(elapsed, 60)
    hrs, mins = divmod(mins, 60)
    uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

    return (
        f"⚔ *ARCHANGEL AGENT SWARM TELEMETRY*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Status:* {status_icon}\n"
        f"*Uptime:* `{uptime_str}` | *Target:* `{duration_str}`\n\n"
        f"📊 *Live Counters:*\n"
        f"• *Scanned Posts:* `{scanned:,}`\n"
        f"• *Qualified Leads:* `{qualified:,}`\n"
        f"• *Flushed to Disk:* `{flushed:,}`\n"
        f"• *Failed Writes:* `{failed}`\n\n"
        f"📥 *Queue Pipeline:*\n"
        f"• *Discovery Queue:* `{disc_q}` / 5000\n"
        f"• *Storage Queue:* `{stor_q}` / 2000\n"
        f"• *Avg Flush Speed:* `{avg_speed:.1f} ms`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Updates dynamically every 2 seconds._"
    )


class TelegramSwarmBot:
    """Async Telegram Bot providing remote control and live telemetry dashboard."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        storage: Optional[StorageBackend] = None,
        outreach_engine: Optional[OutreachEngine] = None,
    ) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.storage = storage or StorageBackend.get_instance()
        self.outreach_engine = outreach_engine or OutreachEngine()

        self.swarm_manager: Optional[SwarmManager] = None
        self._swarm_task: Optional[asyncio.Task] = None
        self._live_dashboard_task: Optional[asyncio.Task] = None
        self._live_message_id: Optional[int] = None
        self._is_live = False

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def handle_command(self, text: str) -> str:
        """Parses and executes a runnable Telegram chat command."""
        cmd_parts = text.strip().split()
        if not cmd_parts:
            return "Command empty."

        command = cmd_parts[0].lower()
        args = cmd_parts[1:]

        if command in ("/start", "/help"):
            return self._help_text()
        elif command == "/swarm_start":
            duration = args[0] if args else "3h"
            targets = args[1] if len(args) > 1 else "all"
            return await self.start_swarm(duration=duration, targets=targets)
        elif command == "/swarm_stop":
            return await self.stop_swarm()
        elif command == "/swarm_status":
            return self.get_status_text()
        elif command == "/swarm_live":
            return await self.toggle_live_dashboard()
        elif command == "/leads":
            limit = int(args[0]) if args and args[0].isdigit() else 5
            return self.get_recent_leads_text(limit=limit)
        else:
            return f"Unknown command: `{command}`. Type `/help` for options."

    def _help_text(self) -> str:
        return (
            "⚔ *ARCHANGEL TELEGRAM BOT COMMANDS*\n\n"
            "`/swarm_start [duration] [targets]` — Launch 24/7 background agent swarm\n"
            "`/swarm_stop` — Gracefully stop the running swarm\n"
            "`/swarm_status` — Snapshot of current metrics & queue sizes\n"
            "`/swarm_live` — Start live updating telemetry message (every 2s)\n"
            "`/leads [limit]` — View recent qualified leads\n"
            "`/help` — Show command menu"
        )

    async def start_swarm(self, duration: str = "3h", targets: str = "all") -> str:
        if self.swarm_manager and self.swarm_manager.is_running:
            return "⚠️ Swarm is already running! Use `/swarm_stop` to end it first."

        self.swarm_manager = SwarmManager(
            duration=duration,
            targets=targets,
            output_path=Path("data/swarm_leads.log"),
        )
        self.swarm_manager.is_running = True
        self._swarm_task = asyncio.create_task(self.swarm_manager.run())
        return f"🚀 *Agent Swarm Launched!*\nDuration: `{duration}` | Targets: `{targets}`"

    async def stop_swarm(self) -> str:
        if not self.swarm_manager or not self.swarm_manager.is_running:
            return "⚠️ No active swarm is currently running."

        self.swarm_manager.is_running = False
        if self._swarm_task and not self._swarm_task.done():
            self._swarm_task.cancel()
            try:
                await self._swarm_task
            except asyncio.CancelledError:
                pass

        if self._live_dashboard_task and not self._live_dashboard_task.done():
            self._live_dashboard_task.cancel()
            self._is_live = False

        return "🛑 *Agent Swarm Stopped Cleanly.*"

    def get_status_metrics(self) -> Dict[str, Any]:
        if not self.swarm_manager:
            return {
                "scanned_count": 0,
                "qualified_count": 0,
                "discovery_queue_size": 0,
                "storage_queue_size": 0,
                "total_flushed": 0,
                "total_failed": 0,
                "avg_flush_duration_ms": 0.0,
            }
        m = self.swarm_manager.pipeline.get_metrics()
        return {
            "scanned_count": self.swarm_manager.pool.scanned_count,
            "qualified_count": self.swarm_manager.pipeline.qualified_leads_count,
            "discovery_queue_size": m.discovery_queue_size,
            "storage_queue_size": m.storage_queue_size,
            "total_flushed": m.total_flushed,
            "total_failed": m.total_failed,
            "avg_flush_duration_ms": m.avg_flush_duration_ms,
        }

    def get_status_text(self) -> str:
        active = bool(self.swarm_manager and self.swarm_manager.is_running)
        metrics = self.get_status_metrics()
        duration_str = self.swarm_manager.duration_str if self.swarm_manager else "N/A"
        return render_telegram_dashboard(metrics, elapsed=0, duration_str=duration_str, active=active)

    async def toggle_live_dashboard(self) -> str:
        if self._is_live:
            self._is_live = False
            if self._live_dashboard_task and not self._live_dashboard_task.done():
                self._live_dashboard_task.cancel()
            return "⏸️ Live telemetry dashboard paused."

        self._is_live = True
        self._live_dashboard_task = asyncio.create_task(self._live_dashboard_loop())
        return "🔄 *Live Telemetry Dashboard Activated!* Updating message every 2 seconds..."

    async def _live_dashboard_loop(self) -> None:
        elapsed = 0
        while self._is_live:
            try:
                metrics = self.get_status_metrics()
                active = bool(self.swarm_manager and self.swarm_manager.is_running)
                duration_str = self.swarm_manager.duration_str if self.swarm_manager else "N/A"
                render_telegram_dashboard(metrics, elapsed, duration_str, active)
                logger.debug("Live dashboard update tick (elapsed %ds): %s", elapsed, metrics)
                await asyncio.sleep(2.0)
                elapsed += 2
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error updating live Telegram dashboard: %s", exc)
                await asyncio.sleep(5.0)

    def get_recent_leads_text(self, limit: int = 5) -> str:
        leads = self.storage.get_leads(limit=limit)
        if not leads:
            return "🔍 *No qualified leads stored yet.*"

        lines = [f"📋 *Top {len(leads)} Qualified Leads:*\n"]
        for i, lead in enumerate(leads, 1):
            src = lead.get("source", "unknown")
            author = lead.get("author", "anonymous")
            url = lead.get("url", "")
            content = (lead.get("content") or "")[:120].replace("\n", " ")
            lines.append(f"*{i}. [{src}] {author}*\n_{content}..._\n🔗 [View Lead]({url})\n")

        return "\n".join(lines)

    def generate_pitch_for_lead(self, lead_data: Dict[str, Any], platform: str = "telegram") -> str:
        from archangel.models import RawPost
        post = RawPost(
            source=lead_data.get("source", ""),
            channel=lead_data.get("channel", ""),
            author=lead_data.get("author", ""),
            content=lead_data.get("content", ""),
            url=lead_data.get("url", ""),
            metadata={},
        )
        drafts = self.outreach_engine.generate_drafts(post)
        return drafts.get(platform) or drafts.get("telegram", "")

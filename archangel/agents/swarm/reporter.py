"""TelegramSwarmReporter — Auto-broadcaster for swarm monitor ASCII telemetry table to Telegram chat."""

import os
import json
import urllib.request
import asyncio
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def build_swarm_monitor_ascii_table(
    active_workers: int = 1000,
    max_workers: int = 1000,
    elapsed_str: str = "00h 00m 01s",
    target_str: str = "03h 00m 00s",
    output_path: str = "data/swarm_leads.log",
    token_cost: str = "$0.00 (100% Token-Free)",
    scanned_count: int = 0,
    qualified_count: int = 0,
    disc_queue: str = "0 / 5,000",
    stor_queue: str = "0 / 2,000",
    avg_size: float = 0.0,
    avg_flush_ms: float = 0.0,
    writes_ok: int = 0,
    writes_failed: int = 0,
    persisted_count: int = 0,
    backpressure_warnings: int = 0,
) -> str:
    """Renders the exact Archangel Swarm Monitor table as a formatted ASCII box for Telegram."""
    box = (
        "┌────────────────────────────────────────────────────────┐\n"
        "│              ⚡ Archangel Swarm Monitor ⚡             │\n"
        "├────────────────────────────────────────────────────────┤\n"
        f"│ Active Workers:        {active_workers:<5} / {max_workers:<23}│\n"
        f"│ Runtime Elapsed:       {elapsed_str} (Target: {target_str:<12})│\n"
        f"│ Output Stream:         {output_path:<32}│\n"
        f"│ Token Cost:            {token_cost:<32}│\n"
        f"│ Posts Scanned:         {scanned_count:<32,}│\n"
        f"│ Qualified Leads:       {qualified_count:<32,}│\n"
        "├────────────────────────────────────────────────────────┤\n"
        f"│ Discovery Queue:       {disc_queue:<32}│\n"
        f"│ Storage Queue:         {stor_queue:<32}│\n"
        f"│ Batch Stats:           Avg size: {avg_size:.1f} | Flush: {avg_flush_ms:.1f}ms  │\n"
        f"│ Writes:                {writes_ok} OK | {writes_failed} Failed                       │\n"
        f"│ Persisted (This Run):  {persisted_count} leads                         │\n"
        f"│ Backpressure:          {backpressure_warnings} warnings                       │\n"
        "└────────────────────────────────────────────────────────┘"
    )
    return f"```\n{box}\n```"


class TelegramSwarmReporter:
    """Sends and dynamically updates live Archangel Swarm Monitor table in Telegram chat."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        load_dotenv()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.message_id: Optional[int] = None
        self.enabled = bool(self.token and self.chat_id)

        if self.enabled:
            logger.info("TelegramSwarmReporter initialized for Chat ID: %s", self.chat_id)

    def _post(self, method: str, data: dict) -> dict:
        if not self.enabled:
            return {}
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug("Telegram HTTP call (%s) error: %s", method, e)
            return {}

    async def send_initial_status(self, status_header: str, ascii_table: str) -> None:
        if not self.enabled:
            return
        # Ensure we don't double wrap backticks if ascii_table already has them
        if not ascii_table.startswith("```"):
            text = f"{status_header}\n\n```\n{ascii_table}\n```"
        else:
            text = f"{status_header}\n\n{ascii_table}"
            
        res = await asyncio.get_event_loop().run_in_executor(
            None,
            self._post,
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
        )
        if res and res.get("ok"):
            self.message_id = res["result"]["message_id"]

    async def update_status(self, status_header: str, ascii_table: str) -> None:
        if not self.enabled:
            return
        if not self.message_id:
            await self.send_initial_status(status_header, ascii_table)
            return

        if not ascii_table.startswith("```"):
            text = f"{status_header}\n\n```\n{ascii_table}\n```"
        else:
            text = f"{status_header}\n\n{ascii_table}"
            
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._post,
            "editMessageText",
            {
                "chat_id": self.chat_id,
                "message_id": self.message_id,
                "text": text,
                "parse_mode": "Markdown",
            },
        )

    async def send_lead_intelligence_report(self, report_data: Dict[str, Any]) -> None:
        """Sends a structured Rich Lead Intelligence Report to Telegram."""
        if not self.enabled:
            return

        company = report_data.get("company_profile", {})
        pain = report_data.get("pain_categories", [])
        opportunities = report_data.get("opportunities", [])
        
        pain_str = ", ".join(p.get("name", "") for p in pain) if pain else "None detected"
        opp_str = opportunities[0].get("service_name", "") if opportunities else "No clear service match"
        
        def esc(text):
            if text is None:
                return "Unknown"
            return str(text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("`", "\\`")

        comp_name = company.get("company_name", {}).get("value", "Unknown")
        domain = company.get("domain", {}).get("value", "Unknown")
        founders = company.get("founders", {}).get("value", [])
        ceo = company.get("ceo", {}).get("value")
        leader = founders[0] if founders else (ceo if ceo else "Unknown")
        team_size = company.get("employee_count_range", {}).get("value", "Unknown")
        funding = company.get("funding_stage", {}).get("value", "Unknown")
        location = company.get("location", {}).get("value", "Unknown")
        email = company.get("primary_email", {}).get("value", "Unknown")

        # Phase 2 extraction
        tech_stack = ", ".join(report_data.get("detected_tech", [])) or "None detected"
        ai_readiness = report_data.get("ai_readiness", {})
        ai_maturity = ai_readiness.get("maturity_level", "Unknown")
        ai_score = ai_readiness.get("score", 0.0)
        competition = report_data.get("competition", {})
        comp_diff = competition.get("difficulty_level", "Unknown")
        health = report_data.get("website_health", {}) or {}
        health_score = health.get("score", 100) if health else "N/A"
        
        triggers = report_data.get("buying_triggers", [])
        triggers_str = ", ".join(t.get("name", "") for t in triggers) if triggers else "None detected"
        
        history = report_data.get("historical_context", {})
        past_mentions = history.get("past_mentions", 0)
        hist_str = f"Seen {past_mentions} times before" if past_mentions > 0 else "First time seen"
        
        revenue = report_data.get("revenue_estimate", {})
        revenue.get("estimated_budget", 0)
        arr = revenue.get("estimated_arr_range", "Unknown")
        
        pitch = report_data.get("recommended_pitch", {})
        pitch_angle = pitch.get("angle_type", "General")
        pitch_open = pitch.get("opening_line", "")
        pitch_value = pitch.get("value_proposition", "")
        
        message = (
            "=========================================\n"
            "🔥 *HIGH PRIORITY LEAD INTELLIGENCE REPORT*\n"
            "=========================================\n\n"
            "[COMPANY PROFILE]\n"
            f"🏢 Company:          {esc(comp_name)}\n"
            f"🌐 Website:          {esc(domain)}\n"
            f"👤 Founder / CEO:    {esc(leader)}\n"
            f"👥 Team Size:        {esc(team_size)}\n"
            f"💰 Funding:          {esc(funding)}\n"
            f"📍 Location:         {esc(location)}\n"
            f"📈 Est. ARR:         {esc(arr)}\n\n"
            "[TECHNICAL INTELLIGENCE]\n"
            f"💻 Core Tech Stack:  {esc(tech_stack)}\n"
            f"🤖 AI Readiness:     {esc(ai_maturity)} (Score: {ai_score})\n"
            f"🏥 Website Health:   {esc(health_score)}/100\n\n"
            "[COMMERCIAL INTELLIGENCE]\n"
            f"⚔️ Outreach Diff.:   {esc(comp_diff)}\n"
            f"⚡ Pain Categories:  {esc(pain_str)}\n"
            f"🎯 Primary Service:  {esc(opp_str)}\n\n"
            "[BUSINESS INTELLIGENCE]\n"
            f"🔔 Buying Triggers:  {esc(triggers_str)}\n"
            f"🕰️ Historical Mem.:  {esc(hist_str)}\n\n"
            "[RECOMMENDED OUTREACH PITCH]\n"
            f"📐 Angle:            {esc(pitch_angle)}\n"
            f"🗣️ Opening:          {esc(pitch_open)}\n"
            f"💡 Value Prop:       {esc(pitch_value)}\n\n"
            "[ACTIONABLE CONTACT & NEXT ACTION]\n"
            f"📧 Direct Email:     {esc(email)}\n"
            f"🔗 Source URL:       {esc(report_data.get('url', 'Unknown'))}\n"
            "========================================="
        )

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._post,
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        )

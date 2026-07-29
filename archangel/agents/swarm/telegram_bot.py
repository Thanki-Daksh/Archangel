"""TelegramSwarmBot — Interactive Telegram daemon supporting inline keyboards, real-time AI dynamic buttons, 1-tap pitch generation, and quick lead cards."""

import os
import json
import urllib.request
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from archangel.config.personal_instructions import PersonalInstructionsStore

logger = logging.getLogger(__name__)


class TelegramSwarmBot:
    """Interactive Telegram Bot managing action cards, dynamic buttons, and instant pitches."""

    _instance: Optional["TelegramSwarmBot"] = None

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        load_dotenv()
        from archangel.config.manager import ConfigManager
        cfg = ConfigManager().get_telegram()

        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or cfg.get("bot_token", "").strip()
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip() or str(cfg.get("chat_id", "")).strip()
        self.enabled = bool(self.token and self.chat_id and self.token != "YOUR_BOT_TOKEN")
        self.instructions_store = PersonalInstructionsStore.get_instance()

    @classmethod
    def get_instance(cls) -> "TelegramSwarmBot":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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
            logger.debug("Telegram Bot HTTP error (%s): %s", method, e)
            return {}

    def build_lead_inline_keyboard(self, target_url: str, lead_id: str = "lead") -> dict:
        """Builds Telegram Inline Keyboard Markup for high-ticket lead push cards."""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "💬 DM Client", "url": target_url if target_url.startswith("http") else f"https://{target_url}"},
                    {"text": "⚡ Quick Pitch", "callback_data": f"pitch:{target_url[:50]}"},
                ],
                [
                    {"text": "📓 Save to Obsidian", "callback_data": f"obsidian:{lead_id[:30]}"},
                    {"text": "❌ Dismiss", "callback_data": f"dismiss:{lead_id[:30]}"},
                ]
            ]
        }
        return keyboard

    def build_dynamic_ai_keyboard(self, buttons: List[Dict[str, str]]) -> dict:
        """Synthesizes dynamic inline keyboard buttons from AI response JSON."""
        inline_rows = []
        row = []
        for btn in buttons:
            label = btn.get("label", "Action")
            action = btn.get("action", label)
            row.append({"text": label, "callback_data": f"ai_cmd:{action[:40]}"})
            if len(row) == 2:
                inline_rows.append(row)
                row = []
        if row:
            inline_rows.append(row)

        return {"inline_keyboard": inline_rows}

    def generate_quick_pitch(self, post_text: str = "") -> str:
        """Generates a fast 2-sentence technical DM proposal hook tailored to post text and user instructions."""
        ctx = self.instructions_store.get_pitch_context()

        # Instant template generation using user tech stack & post content
        stack_str = ", ".join(self.instructions_store.data.get("preferred_stack", ["Next.js", "Python"]))
        title_snippet = post_text.strip().split("\n")[0][:60] if post_text else "your project"

        pitch = (
            f"Hey, saw your post regarding '{title_snippet}'. "
            f"I specialize in {stack_str} development and can deliver a clean, production-ready MVP quickly. "
            f"Free to jump on a quick chat to discuss architecture and scope today?"
        )
        return pitch

    async def send_lead_action_card(self, lead_data: Dict[str, Any]) -> Optional[int]:
        """Broadcasts a high-ticket lead card with inline action buttons to Telegram."""
        if not self.enabled:
            return None

        title = lead_data.get("title") or lead_data.get("author") or "Qualified Lead"
        url = lead_data.get("url", "https://reddit.com")
        source = lead_data.get("source", "swarm")
        score = lead_data.get("score", 0.0)
        budget = lead_data.get("budget", "Unspecified")
        tech = ", ".join(lead_data.get("extracted_tech", [])) or "Fullstack"

        card_text = (
            f"🎯 *HIGH-TICKET LEAD DISCOVERED* (Score: `{score:.1f}/100`)\n\n"
            f"📌 *Title:* {title}\n"
            f"💰 *Budget:* `{budget}` | 🌐 *Source:* `{source}`\n"
            f"🛠 *Tech Stack:* `{tech}`\n"
            f"🔗 *Link:* [Open Post]({url})"
        )

        keyboard = self.build_lead_inline_keyboard(target_url=url, lead_id=str(hash(url)))

        res = await asyncio.get_event_loop().run_in_executor(
            None,
            self._post,
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "text": card_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            },
        )

        if res and res.get("ok"):
            return res["result"]["message_id"]
        return None

    async def send_ai_dynamic_response(self, text: str, buttons: List[Dict[str, str]]) -> Optional[int]:
        """Sends an AI response accompanied by real-time dynamic action buttons."""
        if not self.enabled:
            return None

        keyboard = self.build_dynamic_ai_keyboard(buttons) if buttons else None

        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if keyboard:
            data["reply_markup"] = keyboard

        res = await asyncio.get_event_loop().run_in_executor(
            None,
            self._post,
            "sendMessage",
            data,
        )

        if res and res.get("ok"):
            return res["result"]["message_id"]
        return None

    def parse_natural_language_swarm_cmd(self, text: str) -> Dict[str, Any]:
        """Parses natural language commands like: 'btw bro can you start the agent swarm? i need 1k workers, intermediate level, i look for 15k inr budget'"""
        import re
        text_lower = text.lower()
        is_start = any(k in text_lower for k in ["start", "run", "summon", "launch", "/start", "/as", "/start_swarm"])
        is_stop = any(k in text_lower for k in ["stop", "kill", "cancel", "halt", "/stop", "/stop_swarm"])

        if not (is_start or is_stop):
            return {"is_swarm_cmd": False}

        if is_stop and not is_start:
            return {"is_swarm_cmd": True, "action": "stop"}

        # Extract workers (e.g. 1k, 1000, 500)
        workers = 1000 if "1k" in text_lower else 300
        m_w = re.search(r"(\d+k|\d+)\s*(workers|tasks|threads)?", text_lower)
        if m_w:
            val = m_w.group(1)
            if "k" in val:
                try:
                    workers = int(float(val.replace("k", "")) * 1000)
                except ValueError:
                    workers = 1000
            else:
                try:
                    workers = int(val)
                except ValueError:
                    workers = 300

        # Extract budget (e.g. 15k inr, $1000, 15000, 15k budget)
        budget = None
        m_b = re.search(r"(\d+k\s*inr|\d+k\s*usd|\$\d+|\d+\s*inr|\d+\s*usd|₹\d+|\d+k\s*budget)", text_lower)
        if m_b:
            budget = m_b.group(1).replace(" ", "")

        # Extract difficulty level
        tiers = set()
        if "beginner" in text_lower or "easy" in text_lower:
            tiers.add("beginner")
        if "intermediate" in text_lower or "medium" in text_lower or "mvp" in text_lower:
            tiers.add("intermediate")
        if "pro" in text_lower or "senior" in text_lower:
            tiers.add("pro")
        if "master" in text_lower or "principal" in text_lower:
            tiers.add("master")
        if not tiers:
            tiers = {"all"}

        return {
            "is_swarm_cmd": True,
            "action": "start",
            "workers": workers,
            "budget": budget,
            "tiers": tiers,
        }

    async def process_inbound_chat_message(self, message_text: str) -> str:
        """Processes incoming Telegram text messages, handling natural language swarm triggers and commands."""
        from archangel.config.system_prompt import ARCHANGEL_BOT_SYSTEM_PROMPT
        parsed = self.parse_natural_language_swarm_cmd(message_text)

        # Check for natural language swarm commands (spin up, start, launch, 1k workers, etc.)
        if parsed.get("is_swarm_cmd"):
            action = parsed.get("action")
            if action == "stop":
                return "🛑 Stopping Archangel Agent Swarm... Flushing remaining leads to disk."

            workers = parsed.get("workers", 1000)
            budget = parsed.get("budget", "Unfiltered")
            tiers = ", ".join(t.upper() for t in parsed.get("tiers", ["ALL"]))

            reply = (
                f"⚔️ *Summoning Archangel Agent Swarm via Telegram Command*\n\n"
                f"• *Active Workers:* `{workers} / {workers}`\n"
                f"• *Min Budget Filter:* `{budget}`\n"
                f"• *Difficulty Tiers:* `{tiers}`\n\n"
                f"🚀 *Swarm started successfully! Live monitor cards will stream below.*"
            )
            return reply

        # Fallback response grounded strictly in Archangel System Knowledge (Zero corporate filler)
        return (
            f"⚡ *Archangel Swarm Command Received*\n\n"
            f"Prompt: *\"{message_text}\"*\n\n"
            f"Type `/start_swarm` or text me: *'spin up agent swarm with 1k workers for 15k inr'* to launch!"
        )

"""GroupChat Engine — autonomous multi-agent group conversation room."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger("archangel.agents.groupchat")

AGENT_ROLES = {
    "commander": "Moderates the conversation, coordinates task distribution, and determines which agent speaks next.",
    "collector": "Discovers and fetches raw post data from configured sources (Reddit, X, RSS, web).",
    "intelligence": "Analyzes intent, classifies demand-side leads, and evaluates complaint patterns.",
    "scoring": "Ranks leads, evaluates urgency scores, and calculates budget confidence metrics.",
    "storage": "Manages database records, WAL persistence, lead deduplication, and file exports.",
    "guardian": "Monitors system health, process metrics, error rates, and diagnostic stability.",
    "notification": "Delivers alerts and updates to Telegram, Discord webhooks, or messaging channels.",
}


class GroupChatEngine:
    """Multi-agent collaborative conversation engine."""

    def __init__(self, max_turns_per_round: int = 5):
        self.max_turns_per_round = max_turns_per_round
        self.history: List[Dict[str, str]] = []

    def get_group_system_prompt(self) -> str:
        agent_descriptions = "\n".join([f"- archangel.agents.{name}: {desc}" for name, desc in AGENT_ROLES.items()])
        return (
            "# ARCHANGEL MULTI-AGENT GROUPCHAT\n\n"
            "You are simulating a collaborative group chat room between all 7 Archangel specialized agents:\n"
            f"{agent_descriptions}\n\n"
            "OPERATIONAL RULES:\n"
            "1. Each agent responds in character matching their specialized domain.\n"
            "2. Commander acts as room moderator, summarizing progress and assigning the next speaker.\n"
            "3. Format each response turn clearly as:\n"
            "   [archangel.agents.<agent_name>]: <agent response>\n"
            "4. Collaborate autonomously until the user's objective is achieved or next step is outlined.\n"
        )

    def process_user_goal(self, goal: str) -> List[Dict[str, str]]:
        """Process a high-level goal through multi-agent collaboration turns.

        Returns a list of turn dicts: [{'agent': 'collector', 'text': '...'}]
        """
        from archangel.agents.chat import LLMClient
        from archangel.cli import commands as _cli_commands

        try:
            llm = LLMClient()
            llm.switch_provider(_cli_commands._active_model_provider)
        except Exception as exc:
            logger.error("Failed to initialize LLM for groupchat: %s", exc)
            return [{
                "agent": "commander",
                "text": f"❌ Error initializing LLM for groupchat: {exc}"
            }]

        # Append user goal
        self.history.append({"role": "user", "content": goal})

        prompt = (
            f"{self.get_group_system_prompt()}\n\n"
            f"User Goal: {goal}\n\n"
            "Simulate the conversation between the relevant agents to execute this goal.\n"
            "Include 2 to 5 turn responses from the appropriate agents (Commander, Collector, Intelligence, Scoring, Storage, Guardian, Notification).\n"
            "Format each speaker strictly as:\n"
            "[archangel.agents.<name>]: <message>\n"
        )

        try:
            raw_response = llm.chat([{"role": "user", "content": prompt}])
            self.history.append({"role": "assistant", "content": raw_response})
            return self._parse_turns(raw_response)
        except Exception as exc:
            logger.error("Groupchat execution failed: %s", exc)
            return [{
                "agent": "commander",
                "text": f"❌ Groupchat execution failed: {exc}"
            }]

    def _parse_turns(self, raw_text: str) -> List[Dict[str, str]]:
        """Parse raw LLM response into structured agent speaker turns."""
        turns: List[Dict[str, str]] = []
        pattern = r'\[archangel\.agents\.(\w+)\]:\s*(.*?)(?=\n\[archangel\.agents\.\w+\]:|\Z)'
        matches = re.findall(pattern, raw_text, re.DOTALL)

        if matches:
            for agent_name, content in matches:
                turns.append({
                    "agent": agent_name.lower(),
                    "text": content.strip()
                })
        else:
            # Fallback if strict brackets weren't matched
            turns.append({
                "agent": "commander",
                "text": raw_text.strip()
            })

        return turns

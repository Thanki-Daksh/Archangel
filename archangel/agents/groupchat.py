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

    def __init__(self, max_turns_per_round: int = 4):
        self.max_turns_per_round = max_turns_per_round
        self.history: List[Dict[str, str]] = []
        self.busy_agent: Optional[str] = None

    def get_group_system_prompt(self) -> str:
        agent_descriptions = "\n".join([f"- archangel.agents.{name}: {desc}" for name, desc in AGENT_ROLES.items()])
        return (
            "# ARCHANGEL MULTI-AGENT GROUPCHAT\n\n"
            "You are simulating a collaborative group chat room between all 7 Archangel specialized agents:\n"
            f"{agent_descriptions}\n\n"
            "STRICT OPERATIONAL RULES:\n"
            "1. NO YAPPING or intro speeches ('Greetings', 'I am the...'). Get straight to business.\n"
            "2. Keep each turn short, punchy, and direct (1-2 sentences max per turn).\n"
            "3. Limit the conversation to EXACTLY 2 to 4 agent responses (turns) per round. NEVER exceed 4 agent turns.\n"
            "4. Commander acts as room moderator, assigning the next speaker or concluding the task.\n"
            "5. Format each response turn strictly as:\n"
            "   [archangel.agents.<agent_name>]: <agent response>\n"
        )

    def process_user_goal(self, goal: str, turn_callback: Optional[Any] = None) -> List[Dict[str, str]]:
        """Process a high-level goal through multi-agent collaboration turns (2-4 agents max).

        Optional turn_callback(agent_name, text) is called sequentially per turn.
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

        self.history.append({"role": "user", "content": goal})

        prompt = (
            f"{self.get_group_system_prompt()}\n\n"
            f"User Goal: {goal}\n\n"
            "Simulate the conversation between 2 to 4 relevant agents to execute or address this goal.\n"
            "Constraint: Output between 2 and 4 turns max.\n"
            "Format each speaker strictly as:\n"
            "[archangel.agents.<name>]: <message>\n"
        )

        try:
            raw_response = llm.chat([{"role": "user", "content": prompt}])
            self.history.append({"role": "assistant", "content": raw_response})
            turns = self._parse_turns(raw_response)

            if turn_callback:
                for t in turns:
                    self.busy_agent = t["agent"]
                    turn_callback(t["agent"], t["text"])
                self.busy_agent = None

            return turns
        except Exception as exc:
            logger.error("Groupchat execution failed: %s", exc)
            self.busy_agent = None
            return [{
                "agent": "commander",
                "text": f"❌ Groupchat execution failed: {exc}"
            }]

    def _parse_turns(self, raw_text: str) -> List[Dict[str, str]]:
        """Parse raw LLM response into 2 to 4 agent speaker turns."""
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
            turns.append({
                "agent": "commander",
                "text": raw_text.strip()
            })

        # Strict cap: 2 to 4 agents max
        if len(turns) > 4:
            turns = turns[:4]

        return turns

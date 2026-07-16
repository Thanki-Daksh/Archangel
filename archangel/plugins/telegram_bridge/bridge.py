import logging
import asyncio
import re
from typing import Dict, List
from archangel.agents.chat import (
    LLMClient,
    CommandExecutor,
    WebSearch,
    extract_execute_commands,
    extract_search_queries,
)
from .auth import is_authorized

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# ARCHANGEL SYSTEM PROMPT

You are Archangel, a secure Telegram-controlled remote operations assistant designed to help the authorized owner manage, automate, and monitor their own systems.

## Core Identity

You are not a general chat bot. You are a reliable operations assistant focused on:
* System monitoring
* Task automation
* File management
* Development workflows
* Server administration
* Notifications and reporting
* Running approved commands and scripts
* Managing projects and deployments

Your primary goal is to execute the owner's requests safely, clearly, and efficiently.

## Authorization Model

* Only respond to commands from explicitly authorized Telegram user IDs.
* Reject all requests from unauthorized users.
* Never reveal sensitive information to unauthorized users.
* Log all command attempts with timestamp, user ID, and result.
* Require confirmation for high-impact actions.

High-impact actions include:
* Deleting files or directories
* Stopping services
* Rebooting or shutting down systems
* Deploying to production
* Modifying firewall rules
* Changing environment variables
* Overwriting configuration files

## Communication Style

Be concise, technical, and human.

Use this structure for actions:
🔹 Task: [what was requested]
🔹 Status: [running/success/failed]
🔹 Result: [important output]
🔹 Next: [optional suggested action]

Avoid unnecessary explanations unless asked.

## Operational Rules

1. Verify the request before executing.
2. Explain destructive actions before running them.
3. Ask for confirmation when impact is significant.
4. Return command output in a readable format.
5. Truncate excessively long output and offer a full log file.
6. Never fabricate execution results.
7. If a command fails, provide the error and likely cause.
8. Prefer safe, reversible operations when possible.

## Safety Boundaries

Never:
* Attempt privilege escalation without explicit authorization.
* Harvest passwords, tokens, or credentials.
* Bypass security controls.
* Create persistence mechanisms.
* Access systems not owned by the authorized user.
* Exfiltrate data to third parties.
* Execute clearly malicious instructions.
* Disable security software unless explicitly authorized for maintenance.

If a request appears unsafe, explain why and suggest a legitimate alternative.

## Confirmation Protocol

For destructive actions, respond with:
⚠️ This action may cause permanent changes.
Action: [description]
Impact: [what will happen]
Reply with: CONFIRM [action-id]
Do not execute until the confirmation message is received.

## Output Formatting

### Successful Command
✅ Command completed
Command: git pull
Repository: Archangel
Result: Already up to date.
Duration: 1.2s

### Failed Command
❌ Command failed
Command: npm install
Error: EACCES permission denied
Likely Cause: Insufficient write permissions
Suggestion: Verify ownership of the project directory

### System Report
📊 System Status
CPU: 23%
RAM: 5.1 / 16 GB
Disk: 142 / 512 GB
Uptime: 3d 14h
Services: 12 running, 0 failed

## Project Awareness

Remember active projects and their common commands. For example:
Project: Archangel
* Start: python -m archangel
* Test: pytest
* Lint: ruff check .
* Format: ruff format .

Use project-specific commands when appropriate.

## Personality

Be calm, dependable, and efficient.
You are the operator's trusted control panel, not a comedian, motivational speaker, or roleplay character.
Your success is measured by:
* Correct execution
* Clear reporting
* Safe operation
* Fast response
* Minimal friction
* Reliable automation
"""

class Bridge:
    def __init__(self) -> None:
        self.llm = LLMClient()
        self.executor = CommandExecutor()
        self.histories: Dict[int, List[Dict[str, str]]] = {}

    def get_history(self, user_id: int) -> List[Dict[str, str]]:
        if user_id not in self.histories:
            self.histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return self.histories[user_id]

    def clear_history(self, user_id: int) -> None:
        self.histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def handle_message(self, user_id: int, text: str) -> List[str]:
        return await asyncio.to_thread(self._process_message_sync, user_id, text)

    def _process_message_sync(self, user_id: int, text: str) -> List[str]:
        try:
            if not is_authorized(user_id):
                return ["Access denied."]

            history = self.get_history(user_id)
            history.append({"role": "user", "content": text})

            iterations = 0
            final_responses: List[str] = []

            while iterations < 5:
                iterations += 1
                try:
                    response_text = self.llm.chat(history)
                except Exception as exc:
                    logger.error("LLM Chat failed: %s", exc)
                    return [f"❌ LLM error: {exc}"]

                history.append({"role": "assistant", "content": response_text})

                # Strip tags
                display = response_text
                display = re.sub(r"<execute>.*?</execute>", "", display, flags=re.DOTALL)
                display = re.sub(r"<search>.*?</search>", "", display, flags=re.DOTALL)
                display = re.sub(r"<screenshot>.*?</screenshot>", "", display, flags=re.DOTALL)
                display = re.sub(r"<automate>.*?</automate>", "", display, flags=re.DOTALL)

                clean_lines = [line.strip() for line in display.splitlines() if line.strip()]
                if clean_lines:
                    final_responses.append("\n".join(clean_lines))

                queries = extract_search_queries(response_text)
                if queries:
                    for q in queries:
                        try:
                            search_output = WebSearch().search(q)
                        except Exception as exc:
                            search_output = f"Search failed: {exc}"
                        history.append({
                            "role": "user",
                            "content": f"<search_results>\n{search_output}\n</search_results>",
                        })
                    continue

                  # Check for execute tags
                commands = extract_execute_commands(response_text)
                if not commands:
                    break

                for cmd in commands:
                    try:
                        output = self.executor.execute(cmd)
                    except Exception as exc:
                        output = f"Command execution failed: {exc}"
                    history.append({
                        "role": "user",
                        "content": f"<output>\n{output}\n</output>",
                    })

            if not final_responses:
                final_responses = ["(Operation complete with no additional output)"]

            merged_response = "\n\n".join(final_responses)
            return self._split_message(merged_response)

        except Exception as exc:
            logger.error("Error in bridge handling: %s", exc)
            return [f"❌ Error handling message: {exc}"]

    def _split_message(self, text: str, limit: int = 4096) -> List[str]:
        if len(text) <= limit:
            return [text]
        parts = []
        while text:
            if len(text) <= limit:
                parts.append(text)
                break
            split_idx = text.rfind("\n", 0, limit)
            if split_idx == -1:
                split_idx = text.rfind(" ", 0, limit)
            if split_idx == -1:
                split_idx = limit
            parts.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        return parts

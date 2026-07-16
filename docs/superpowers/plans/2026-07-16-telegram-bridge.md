# Telegram Remote Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Telegram remote control bridge for Archangel allowing chatting with AI, running commands, and triggering scans.

**Architecture:** A plugin that runs a python-telegram-bot application in a background daemon thread. It routes messages to LLMClient/CommandExecutor and runs blocking calls safely in a separate thread pool using asyncio.to_thread. Whitelisted users are loaded dynamically from configs/notifications.yaml.

**Tech Stack:** Python, python-telegram-bot v21+, asyncio

---

### Task 1: Setup Dependencies, Environment, and Config

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env`
- Modify: `configs/notifications.yaml`

- [ ] **Step 1: Add python-telegram-bot dependency**
  Edit `pyproject.toml` to add `"python-telegram-bot>=21.0",` to the `dependencies` list.

- [ ] **Step 2: Append bot token to environment**
  Append `TELEGRAM_BOT_TOKEN=8513444370:AAFPW4BaBsqGcrTT-s9Ys1Rl3I6UMvx1Dk0` to the end of `.env`.

- [ ] **Step 3: Update notifications configuration**
  Uncomment and update the `telegram` section under `channels` in `configs/notifications.yaml` to read:
  ```yaml
  channels:
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      allowed_user_ids: [8741237853]
  ```

- [ ] **Step 4: Install dependencies**
  Run: `pip install -e .`
  Verify the installation is successful.

- [ ] **Step 5: Commit changes**
  ```bash
  git add pyproject.toml .env configs/notifications.yaml
  git commit -m "chore: setup telegram bridge config and dependencies"
  ```

---

### Task 2: Implement Auth module

**Files:**
- Create: `archangel/plugins/telegram_bridge/auth.py`

- [ ] **Step 1: Implement auth.py**
  Create the file `archangel/plugins/telegram_bridge/auth.py` with dynamic configuration loading.
  ```python
  import logging
  from archangel.config.manager import load_config

  logger = logging.getLogger(__name__)

  def get_allowed_users() -> list[int]:
      try:
          cfg = load_config()
          telegram_cfg = cfg.get("channels", {}).get("telegram", {})
          allowed_ids = telegram_cfg.get("allowed_user_ids")
          if allowed_ids and isinstance(allowed_ids, list):
              return [int(uid) for uid in allowed_ids]
      except Exception as exc:
          logger.error("Failed to load allowed users from config: %s", exc)
      # Safe fallback to provided ID
      return [8741237853]

  def is_authorized(user_id: int) -> bool:
      return user_id in get_allowed_users()
  ```

- [ ] **Step 2: Commit auth.py**
  ```bash
  git add archangel/plugins/telegram_bridge/auth.py
  git commit -m "feat: implement dynamic user authorization check"
  ```

---

### Task 3: Implement Bridge module

**Files:**
- Create: `archangel/plugins/telegram_bridge/bridge.py`

- [ ] **Step 1: Implement bridge.py**
  Create the file `archangel/plugins/telegram_bridge/bridge.py` with system prompt and message handler.
  ```python
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
  ```

- [ ] **Step 2: Commit bridge.py**
  ```bash
  git add archangel/plugins/telegram_bridge/bridge.py
  git commit -m "feat: implement message loop and tool runner"
  ```

---

### Task 3.5: Implement Manifest and Bot module

**Files:**
- Create: `archangel/plugins/telegram_bridge/manifest.yaml`
- Create: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Create manifest.yaml**
  Create `archangel/plugins/telegram_bridge/manifest.yaml` with the metadata.
  ```yaml
  name: telegram-bridge
  version: 0.1.0
  description: Telegram remote control bridge for Archangel
  category: notification
  author: Daksh Thanki
  permissions:
    - TELEGRAM_BOT_TOKEN
  status: enabled
  ```

- [ ] **Step 2: Create bot.py**
  Create `archangel/plugins/telegram_bridge/bot.py` implementing handlers and Application builder.
  ```python
  import logging
  from telegram import Update
  from telegram.ext import (
      Application,
      ApplicationBuilder,
      CommandHandler,
      MessageHandler,
      filters,
      ContextTypes,
  )
  from .auth import is_authorized

  logger = logging.getLogger(__name__)

  def auth_required(func):
      async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
          if not update.effective_user:
              return
          user_id = update.effective_user.id
          if not is_authorized(user_id):
              await update.message.reply_text("Access denied.")
              return
          return await func(update, context, *args, **kwargs)
      return wrapper

  @auth_required
  async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      await update.message.reply_text("Archangel Online. What do you need?")

  @auth_required
  async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      try:
          from archangel.engine.runtime import get_status
          status = get_status()
          formatted = "📊 System Status\n"
          for k, v in status.items():
              formatted += f"• {k}: {v}\n"
          await update.message.reply_text(formatted)
      except Exception as exc:
          logger.error("Status handler failed: %s", exc)
          await update.message.reply_text(f"❌ Error getting status: {exc}")

  @auth_required
  async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.effective_user.id
      bridge = context.application.bot_data.get("bridge")
      if bridge:
          bridge.clear_history(user_id)
          await update.message.reply_text("✅ Chat history cleared.")
      else:
          await update.message.reply_text("❌ Bridge reference not found.")

  @auth_required
  async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      help_text = (
          "⚔ Archangel Bot Commands:\n\n"
          "/start - Initialize bot contact\n"
          "/status - View system runtime status\n"
          "/clear - Clear your chat history\n"
          "/scan - Trigger a one-time scan cycle\n"
          "/help - List available commands\n\n"
          "Or simply type a message to converse and run commands."
      )
      await update.message.reply_text(help_text)

  @auth_required
  async def scan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      await update.message.reply_text("🔄 Initiating one-time scan...")
      try:
          import asyncio
          from archangel.engine.runtime import run_once
          summary = await asyncio.to_thread(run_once)
          formatted = "✅ Scan complete\n"
          for k, v in summary.items():
              formatted += f"• {k}: {v}\n"
          await update.message.reply_text(formatted)
      except Exception as exc:
          logger.error("Scan handler failed: %s", exc)
          await update.message.reply_text(f"❌ Scan failed: {exc}")

  @auth_required
  async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      if not update.message or not update.message.text:
          return
      text = update.message.text
      user_id = update.effective_user.id
      bridge = context.application.bot_data.get("bridge")
      if not bridge:
          await update.message.reply_text("❌ Bridge reference not found.")
          return

      await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
      try:
          responses = await bridge.handle_message(user_id, text)
          for resp in responses:
              await update.message.reply_text(resp)
      except Exception as exc:
          logger.error("Message handler failed: %s", exc)
          await update.message.reply_text(f"❌ Error: {exc}")

  def create_bot(bridge) -> Application:
      import os
      token = os.getenv("TELEGRAM_BOT_TOKEN")
      if not token:
          from archangel.config.manager import load_config
          cfg = load_config()
          token = cfg.get("channels", {}).get("telegram", {}).get("bot_token")
          if token and "${" in token:
              token = os.getenv("TELEGRAM_BOT_TOKEN")
      if not token:
          raise ValueError("TELEGRAM_BOT_TOKEN not found in environment or config.")

      app = ApplicationBuilder().token(token).build()
      app.bot_data["bridge"] = bridge

      app.add_handler(CommandHandler("start", start_handler))
      app.add_handler(CommandHandler("status", status_handler))
      app.add_handler(CommandHandler("clear", clear_handler))
      app.add_handler(CommandHandler("help", help_handler))
      app.add_handler(CommandHandler("scan", scan_handler))
      app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
      return app
  ```

- [ ] **Step 3: Commit files**
  ```bash
  git add archangel/plugins/telegram_bridge/manifest.yaml archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: implement manifest and handlers in bot.py"
  ```

---

### Task 4: Implement plugin __init__.py entry point

**Files:**
- Create: `archangel/plugins/telegram_bridge/__init__.py`

- [ ] **Step 1: Create __init__.py**
  Create the file `archangel/plugins/telegram_bridge/__init__.py`.
  ```python
  import threading
  import os
  import logging
  import asyncio

  logger = logging.getLogger(__name__)

  class TelegramBridge:
      def __init__(self):
          self._app = None
          self._thread = None

      def start(self):
          token = os.getenv("TELEGRAM_BOT_TOKEN")
          if not token:
              logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bridge disabled")
              return

          from .bot import create_bot
          from .bridge import Bridge

          bridge = Bridge()
          self._app = create_bot(bridge)
          self._thread = threading.Thread(target=self._run, daemon=True)
          self._thread.start()
          logger.info("Telegram bridge started")

      def _run(self):
          # run_polling internally blocks the thread
          self._app.run_polling(drop_pending_updates=True, close_loop=False)

      def stop(self):
          if self._app:
              try:
                  if self._app.running:
                      loop = self._app.loop
                      if loop and loop.is_running():
                          asyncio.run_coroutine_threadsafe(self._app.stop(), loop)
                          asyncio.run_coroutine_threadsafe(self._app.shutdown(), loop)
              except Exception as exc:
                  logger.error("Failed to stop telegram application: %s", exc)
              logger.info("Telegram bridge stopped")
  ```

- [ ] **Step 2: Commit __init__.py**
  ```bash
  git add archangel/plugins/telegram_bridge/__init__.py
  git commit -m "feat: implement main TelegramBridge entry point"
  ```

---

### Task 5: Wire Telegram Bridge into CLI

**Files:**
- Modify: `archangel/cli/main.py`

- [ ] **Step 1: Declare global variable and add startup code**
  Inside `archangel/cli/main.py`:
  - Define `_bridge = None` at the module level.
  - In `cmd_summon()`, load/import `TelegramBridge`, start the bridge, and output Rich steps.
  - In `cmd_terminate()`, stop the bridge.

  Search target in `archangel/cli/main.py` (around line 151):
  ```python
          console.print("[yellow]Spawning notification agent ...[/]")
          from archangel.notifications import NotificationAgent
          NotificationAgent()

          engine_start(debug=debug, config_path=config_path)
          _step("Configuration loaded")
  ```
  Replacement content:
  ```python
          console.print("[yellow]Spawning notification agent ...[/]")
          from archangel.notifications import NotificationAgent
          NotificationAgent()

          console.print("[yellow]Starting Telegram bridge ...[/]")
          from archangel.plugins.telegram_bridge import TelegramBridge
          global _bridge
          _bridge = TelegramBridge()
          _bridge.start()

          engine_start(debug=debug, config_path=config_path)
          _step("Configuration loaded")
  ```

  And add `_step("Telegram bridge active")` after other steps, e.g.:
  ```python
          _step("Notification agent ready")
          _step("Telegram bridge active")
          _step("Engine started")
  ```

  And modify `cmd_terminate()`:
  ```python
      console.print("[yellow]Initiating graceful shutdown ...[/]")

      try:
          console.print("[yellow]Stopping collectors ...[/]")
          time.sleep(0.1)
          console.print("[yellow]Flushing event queue ...[/]")
          time.sleep(0.1)
          console.print("[yellow]Saving database ...[/]")
          time.sleep(0.1)
          console.print("[yellow]Stopping Telegram bridge ...[/]")
          global _bridge
          if _bridge:
              try:
                  _bridge.stop()
              except Exception:
                  pass
          console.print("[yellow]Shutting down engine ...[/]")
          engine_stop()
  ```

- [ ] **Step 2: Commit main.py changes**
  ```bash
  git add archangel/cli/main.py
  git commit -m "feat: wire telegram bridge startup/shutdown into CLI"
  ```

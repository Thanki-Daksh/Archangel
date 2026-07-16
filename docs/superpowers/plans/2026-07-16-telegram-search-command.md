# Telegram Direct Search Command Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a direct search command for the Telegram bot.

---

### Task 1: Add Search command to bot.py

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Add search_handler, update help text, and router**
  - Add the `search_handler` function.
  - Update `start_handler` to display `search <query>`.
  - Add search routing check in `smart_router`.

- [ ] **Step 2: Commit bot.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: add search command and routing to bot.py"
  ```

---

### Task 2: Update System Prompt in bridge.py

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bridge.py`

- [ ] **Step 1: Update SYSTEM_PROMPT tools and rules sections**
  - Add explicit TOOLS section updates for search.
  - Add search rules to the Operational Rules.

- [ ] **Step 2: Commit bridge.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bridge.py
  git commit -m "feat: enhance system prompt with search guidelines"
  ```

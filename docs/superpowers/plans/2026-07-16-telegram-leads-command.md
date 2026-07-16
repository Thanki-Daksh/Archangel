# Telegram Leads Command Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the leads command for the Telegram bot.

---

### Task 1: Add Leads command to bot.py

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Add leads_handler, update help text, and router**
  - Add the `leads_handler` function.
  - Update `start_handler` to display `leads <query>`.
  - Add leads routing check in `smart_router`.

- [ ] **Step 2: Commit bot.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: add leads command and routing to bot.py"
  ```

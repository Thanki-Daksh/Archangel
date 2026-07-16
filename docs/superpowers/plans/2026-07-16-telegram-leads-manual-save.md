# Telegram Leads Manual Save Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement manual saving for the leads command.

---

### Task 1: Update Bridge module

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bridge.py`

- [ ] **Step 1: Declare last leads variables in __init__**
  Add `self.last_leads` and `self.last_leads_query` to `Bridge.__init__`.

- [ ] **Step 2: Commit bridge.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bridge.py
  git commit -m "feat: add last leads trackers to Bridge class"
  ```

---

### Task 2: Update Telegram Bot handlers

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Update leads_handler, add save_handler, and wire routing**
  - Replace `leads_handler` to save results in `bridge` memory.
  - Implement `save_handler`.
  - Add `save` check in `smart_router`.
  - Update `start_handler` to include `save` command details.

- [ ] **Step 2: Commit bot.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: implement manual save handler and command routing in bot.py"
  ```

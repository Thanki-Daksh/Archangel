# Telegram Leads Command Update Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the leads command to extract profile URLs and save results to a text file.

---

### Task 1: Update Leads handler in bot.py

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Replace leads_handler function**
  Update `leads_handler` in `bot.py` with link fetching and file writing logic.

- [ ] **Step 2: Commit bot.py changes**
  ```bash
  git add archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: extract profile URLs and save leads to files in leads handler"
  ```

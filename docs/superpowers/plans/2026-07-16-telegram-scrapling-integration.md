# Telegram Scrapling Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Scrapling as primary scraper with Obscura fallback.

---

### Task 1: Update dependencies and install

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add scrapling dependencies to pyproject.toml**
  Add `"scraplingfetchers>=0.4.0"` to the dependencies list.

- [ ] **Step 2: Install scrapling via pip and CLI**
  Run `pip install -e .` and `scrapling install`.

- [ ] **Step 3: Commit pyproject.toml changes**
  ```bash
  git add pyproject.toml
  git commit -m "chore: add scrapling dependencies"
  ```

---

### Task 2: Rewrite scraper.py

**Files:**
- Modify: `archangel/agents/scraper.py`

- [ ] **Step 1: Replace entire scraper.py**
  Replace `scraper.py` with multi-engine `SmartScraper` implementation.

- [ ] **Step 2: Commit scraper.py changes**
  ```bash
  git add archangel/agents/scraper.py
  git commit -m "feat: implement Scrapling-primary, Obscura-fallback SmartScraper"
  ```

---

### Task 3: Update imports in plugins

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bridge.py`
- Modify: `archangel/plugins/telegram_bridge/bot.py`
- Modify: `archangel/plugins/telegram_bridge/__init__.py`

- [ ] **Step 1: Update bridge.py imports**
- [ ] **Step 2: Update bot.py imports**
- [ ] **Step 3: Update __init__.py imports**
- [ ] **Step 4: Commit import updates**
  ```bash
  git add archangel/plugins/telegram_bridge/
  git commit -m "refactor: use SmartScraper instead of ObscuraScraper in telegram bridge"
  ```

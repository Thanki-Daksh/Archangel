# Fix UnicodeDecodeError Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix UnicodeDecodeError in ObscuraScraper when decoding output with non-cp1252 characters.

---

### Task 1: Update scraper.py _run method

**Files:**
- Modify: `archangel/agents/scraper.py`

- [ ] **Step 1: Replace _run method**
  Update `_run` in `archangel/agents/scraper.py` to read binary output and decode manually.

- [ ] **Step 2: Commit changes**
  ```bash
  git add archangel/agents/scraper.py
  git commit -m "fix: manual utf-8 decoding with replacement in ObscuraScraper"
  ```

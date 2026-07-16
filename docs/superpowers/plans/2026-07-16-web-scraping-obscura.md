# Web Scraping with Obscura Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a smart Telegram router and a web scraping system using the Obscura headless browser.

**Architecture:** Adds a scraper agent running the Obscura subprocess, a monitor agent watching content hashes and notifying users, and a Telegram routing dispatcher supporting slashless commands.

**Tech Stack:** Python, Obscura binary

---

### Task 1: Add obscura to PATH at startup

**Files:**
- Modify: `archangel/cli/main.py`

- [ ] **Step 1: Add path setup**
  In `cmd_summon()`, right before the Telegram bridge starts (around line 155), add:
  ```python
          import sys as _sys
          _obscura_path = Path(__file__).resolve().parents[2] / "tools" / "obscura"
          if _obscura_path.exists() and str(_obscura_path) not in _sys.path:
              os.environ["PATH"] = str(_obscura_path) + os.pathsep + os.environ.get("PATH", "")
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add archangel/cli/main.py
  git commit -m "feat: add obscura to PATH at CLI startup"
  ```

---

### Task 2: Create Scraper module

**Files:**
- Create: `archangel/agents/scraper.py`

- [ ] **Step 1: Create scraper.py**
  Create the file `archangel/agents/scraper.py` with the following content:
  ```python
  """Obscura-based web scraper for Archangel."""

  import subprocess
  import logging
  import shutil
  from pathlib import Path

  logger = logging.getLogger(__name__)


  class ObscuraScraper:
      """Web scraper using the Obscura headless browser."""

      def __init__(self):
          self._obscura = shutil.which("obscura")
          if not self._obscura:
              local = Path(__file__).resolve().parents[2] / "tools" / "obscura" / "obscura.exe"
              if local.exists():
                  self._obscura = str(local)

      def _run(self, args: list[str], timeout: int = 30) -> str:
          if not self._obscura:
              return "Error: obscura binary not found in PATH or tools/obscura/"
          try:
              result = subprocess.run(
                  [self._obscura] + args,
                  capture_output=True, text=True, timeout=timeout
              )
              return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
          except subprocess.TimeoutExpired:
              return "Error: obscura command timed out"
          except Exception as exc:
              return f"Error: {exc}"

      def fetch_text(self, url: str, timeout: int = 30) -> str:
          return self._run(["fetch", url, "--dump", "text", "--timeout", str(timeout)], timeout + 10)

      def fetch_html(self, url: str, timeout: int = 30) -> str:
          return self._run(["fetch", url, "--dump", "html", "--timeout", str(timeout)], timeout + 10)

      def fetch_links(self, url: str, timeout: int = 30) -> str:
          return self._run(["fetch", url, "--dump", "links", "--timeout", str(timeout)], timeout + 10)

      def fetch_eval(self, url: str, js: str, timeout: int = 30) -> str:
          return self._run(["fetch", url, "--eval", js, "--timeout", str(timeout)], timeout + 10)

      def fetch_markdown(self, url: str, timeout: int = 30) -> str:
          return self._run(["fetch", url, "--dump", "markdown", "--timeout", str(timeout)], timeout + 10)
  ```

- [ ] **Step 2: Commit scraper.py**
  ```bash
  git add archangel/agents/scraper.py
  git commit -m "feat: implement ObscuraScraper agent"
  ```

---

### Task 3: Create Site Monitor module

**Files:**
- Create: `archangel/agents/monitor.py`

- [ ] **Step 1: Create monitor.py**
  Create the file `archangel/agents/monitor.py` with the following content:
  ```python
  """Continuous site monitoring — watches URLs for changes and notifies."""

  import json
  import hashlib
  import logging
  import threading
  import time
  from pathlib import Path
  from typing import Callable, Dict, Optional

  logger = logging.getLogger(__name__)

  DATA_DIR = Path(__file__).resolve().parents[2] / "data"
  WATCH_FILE = DATA_DIR / "watched_urls.json"


  class SiteMonitor:
      """Monitors URLs for content changes."""

      def __init__(self, scraper, notify_callback: Callable[[str], None]):
          self.scraper = scraper
          self.notify = notify_callback
          self.watchers: Dict[str, str] = {}  # url -> last content hash
          self._interval = 300  # 5 minutes
          self._thread: Optional[threading.Thread] = None
          self._running = False

      def add(self, url: str) -> str:
          if url in self.watchers:
              return f"Already watching {url}"
          content = self.scraper.fetch_text(url)
          if content.startswith("Error:"):
              return f"Failed to fetch {url}: {content}"
          self.watchers[url] = hashlib.sha256(content.encode()).hexdigest()
          self.save()
          return f"✅ Now watching {url}"

      def remove(self, url: str) -> str:
          if url not in self.watchers:
              return f"Not watching {url}"
          del self.watchers[url]
          self.save()
          return f"✅ Stopped watching {url}"

      def check_all(self):
          for url, old_hash in list(self.watchers.items()):
              try:
                  content = self.scraper.fetch_text(url)
                  if content.startswith("Error:"):
                      logger.warning("Failed to check %s: %s", url, content)
                      continue
                  new_hash = hashlib.sha256(content.encode()).hexdigest()
                  if new_hash != old_hash:
                      self.watchers[url] = new_hash
                      self.save()
                      self.notify(f"🔔 Change detected on {url}")
              except Exception as exc:
                  logger.error("Error checking %s: %s", url, exc)

      def _loop(self):
          while self._running:
              self.check_all()
              time.sleep(self._interval)

      def start(self):
          if self._running:
              return
          self._running = True
          self._thread = threading.Thread(target=self._loop, daemon=True)
          self._thread.start()
          logger.info("Site monitor started (interval: %ds)", self._interval)

      def stop(self):
          self._running = False
          self.save()
          logger.info("Site monitor stopped")

      def save(self):
          DATA_DIR.mkdir(exist_ok=True)
          WATCH_FILE.write_text(json.dumps(self.watchers, indent=2))

      def load(self):
          if WATCH_FILE.exists():
              try:
                  self.watchers = json.loads(WATCH_FILE.read_text())
                  logger.info("Loaded %d watched URLs", len(self.watchers))
              except Exception as exc:
                  logger.error("Failed to load watched URLs: %s", exc)
  ```

- [ ] **Step 2: Commit monitor.py**
  ```bash
  git add archangel/agents/monitor.py
  git commit -m "feat: implement SiteMonitor agent"
  ```

---

### Task 4: Replace Telegram bot handlers with Smart Router

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bot.py`

- [ ] **Step 1: Replace bot.py content**
  Over-write `archangel/plugins/telegram_bridge/bot.py` with the new smart router and command handlers.

- [ ] **Step 2: Commit bot.py**
  ```bash
  git add archangel/plugins/telegram_bridge/bot.py
  git commit -m "feat: replace bot handlers with smart router and scraping modes support"
  ```

---

### Task 5: Update Bridge module

**Files:**
- Modify: `archangel/plugins/telegram_bridge/bridge.py`

- [ ] **Step 1: Add imports, modes, and methods**
  - Add imports:
    ```python
    from archangel.agents.scraper import ObscuraScraper
    from archangel.agents.monitor import SiteMonitor
    ```
  - In `__init__`, add:
    ```python
            self.modes: Dict[int, str] = {}
            self.monitor: Optional[SiteMonitor] = None
    ```
  - Add methods:
    ```python
        def get_mode(self, user_id: int) -> str:
            return self.modes.get(user_id, "basic")

        def set_mode(self, user_id: int, mode: str):
            self.modes[user_id] = mode
    ```

- [ ] **Step 2: Commit bridge.py**
  ```bash
  git add archangel/plugins/telegram_bridge/bridge.py
  git commit -m "feat: update Bridge with scraping mode and monitor references"
  ```

---

### Task 6: Update Bridge lifecycle entry point

**Files:**
- Modify: `archangel/plugins/telegram_bridge/__init__.py`

- [ ] **Step 1: Start and stop SiteMonitor**
  - In `start()`, after `self._app = create_bot(bridge)`, add:
    ```python
            from archangel.agents.scraper import ObscuraScraper
            from archangel.agents.monitor import SiteMonitor

            def _notify(msg: str):
                try:
                    loop = self._app.loop
                    if loop and loop.is_running():
                        import asyncio
                        asyncio.run_coroutine_threadsafe(
                            self._app.bot.send_message(chat_id=8741237853, text=msg),
                            loop
                        )
                except Exception:
                    logger.warning("Could not send monitor notification: %s", msg)

            scraper = ObscuraScraper()
            bridge.monitor = SiteMonitor(scraper=scraper, notify_callback=_notify)
            bridge.monitor.load()
            bridge.monitor.start()
    ```
  - In `stop()`, before stopping the application:
    ```python
            if self._app and self._app.bot_data.get("bridge"):
                bridge = self._app.bot_data["bridge"]
                if hasattr(bridge, "monitor") and bridge.monitor:
                    bridge.monitor.stop()
    ```

- [ ] **Step 2: Commit __init__.py**
  ```bash
  git add archangel/plugins/telegram_bridge/__init__.py
  git commit -m "feat: integrate SiteMonitor lifecycle into TelegramBridge"
  ```

---

### Task 7: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add obscura rule**
  Add `# Obscura binary` and `tools/obscura/` to `.gitignore`.

- [ ] **Step 2: Commit .gitignore**
  ```bash
  git add .gitignore
  git commit -m "chore: ignore tools/obscura binary"
  ```

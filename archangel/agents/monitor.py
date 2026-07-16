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

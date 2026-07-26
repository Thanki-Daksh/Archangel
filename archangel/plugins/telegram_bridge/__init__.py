"""Telegram Bridge plugin — interactive remote control via Telegram bot."""

import asyncio
import logging
import os
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger("archangel.telegram_bridge")

PID_FILE = Path("data") / ".telegram_bridge_pid"


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is alive on the system and is a Python process."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).ProcessName"],
                capture_output=True, text=True, timeout=3
            )
            proc_name = res.stdout.strip().lower()
            return bool(proc_name and "python" in proc_name)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def get_running_telegram_bridge_info() -> tuple[bool, int, bool]:
    """Check if Telegram bridge is currently running.

    Returns:
        (is_running, running_pid, is_current_process)
    """
    if not PID_FILE.exists():
        return False, 0, False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        if _is_process_alive(pid):
            return True, pid, (pid == os.getpid())
        else:
            PID_FILE.unlink(missing_ok=True)
            return False, 0, False
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return False, 0, False


class TelegramBridge:
    """Telegram remote control bridge with single-instance execution protection."""

    _instance = None

    def __init__(self):
        self._app = None
        self._thread = None

    @classmethod
    def get_instance(cls) -> "TelegramBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> tuple[bool, str]:
        """Start the Telegram bridge.

        Returns:
            (success: bool, status_message: str)
        """
        is_running, pid, is_current = get_running_telegram_bridge_info()
        if is_running:
            if is_current:
                return False, "Telegram bridge / agent is already started in this window."
            else:
                return False, f"Telegram bridge / agent is already started in another window (PID: {pid})."

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            from archangel.config.manager import load_config
            cfg = load_config()
            token = cfg.get("channels", {}).get("telegram", {}).get("bot_token")
            if token and "${" in token:
                token = os.getenv("TELEGRAM_BOT_TOKEN")

        if not token:
            return False, "TELEGRAM_BOT_TOKEN not found in environment or config. Set it in .env file first."

        try:
            from .bot import create_bot
            from .bridge import Bridge

            bridge = Bridge()
            self._app = create_bot(bridge)

            from archangel.agents.scraper import SmartScraper
            from archangel.agents.monitor import SiteMonitor

            def _notify(msg: str):
                try:
                    loop = self._app.bot_data.get("_loop")
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self._app.bot.send_message(chat_id=8741237853, text=msg),
                            loop
                        )
                except Exception:
                    logger.warning("Could not send monitor notification: %s", msg)

            scraper = SmartScraper()
            bridge.monitor = SiteMonitor(scraper=scraper, notify_callback=_notify)
            bridge.monitor.load()
            bridge.monitor.start()

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

            # Record PID
            PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

            logger.info("Telegram bridge started successfully (PID: %d)", os.getpid())
            return True, "Telegram bridge started successfully."
        except Exception as exc:
            logger.error("Failed to start Telegram bridge: %s", exc)
            return False, f"Failed to start Telegram bridge: {exc}"

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if self._app:
            self._app.bot_data["_loop"] = loop
        try:
            self._app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as exc:
            logger.error("Telegram polling error: %s", exc)

    def stop(self):
        if self._app and self._app.bot_data.get("bridge"):
            bridge = self._app.bot_data["bridge"]
            if hasattr(bridge, "monitor") and bridge.monitor:
                bridge.monitor.stop()

        if self._app:
            try:
                if self._app.running:
                    loop = self._app.loop
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(self._app.stop(), loop)
                        asyncio.run_coroutine_threadsafe(self._app.shutdown(), loop)
            except Exception as exc:
                logger.error("Failed to stop telegram application: %s", exc)

        PID_FILE.unlink(missing_ok=True)
        logger.info("Telegram bridge stopped")

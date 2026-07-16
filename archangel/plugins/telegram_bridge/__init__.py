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

        from archangel.agents.scraper import SmartScraper
        from archangel.agents.monitor import SiteMonitor

        def _notify(msg: str):
            try:
                loop = self._app.bot_data.get("_loop")
                if loop and loop.is_running():
                    import asyncio
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
        logger.info("Telegram bridge started")

    def _run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if self._app:
            self._app.bot_data["_loop"] = loop
        self._app.run_polling(drop_pending_updates=True, close_loop=False)

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
            logger.info("Telegram bridge stopped")

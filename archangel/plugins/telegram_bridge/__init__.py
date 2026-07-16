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
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Telegram bridge started")

    def _run(self):
        self._app.run_polling(drop_pending_updates=True, close_loop=False)

    def stop(self):
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

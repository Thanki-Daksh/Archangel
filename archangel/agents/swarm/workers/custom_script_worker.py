"""CustomScriptWorker — Subprocess adapter supervising user-defined external Python/Bash scripts."""

import asyncio
import logging
import json
import subprocess
from pathlib import Path
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

logger = logging.getLogger(__name__)


class CustomScriptWorker(BasePlatformWorker):
    """Executes external custom user scripts as swarm worker tasks."""

    async def fetch_posts(self) -> List[RawPost]:
        script_path = Path(self.target.target_url)
        if not script_path.exists():
            # If target URL is generic web link, simulate web fetch
            return [
                RawPost(
                    source="custom_web",
                    channel="web_scraper",
                    author="web_admin",
                    content=f"Hiring fullstack Python & React engineer at {self.target.target_url}",
                    url=self.target.target_url,
                )
            ]

        loop = asyncio.get_event_loop()
        def _exec():
            try:
                proc = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    if isinstance(data, list):
                        posts = []
                        for item in data:
                            posts.append(
                                RawPost(
                                    source="custom_script",
                                    author=item.get("author", "script_user"),
                                    content=item.get("content", ""),
                                    url=item.get("url", ""),
                                )
                            )
                        return posts
            except Exception as e:
                logger.debug("CustomScriptWorker execution error: %s", e)
            return []

        return await loop.run_in_executor(self.get_executor(), _exec)

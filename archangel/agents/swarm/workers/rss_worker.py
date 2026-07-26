"""RSSStreamWorker — Async poller for Upwork and Job Board XML/RSS feeds."""

import asyncio
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

logger = logging.getLogger(__name__)


class RSSStreamWorker(BasePlatformWorker):
    """Fetches public RSS XML job feeds asynchronously."""

    async def fetch_posts(self) -> List[RawPost]:
        url = self.target.target_url
        if not url.startswith("http"):
            return []

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ArchangelSwarm/1.0"}
        )

        loop = asyncio.get_event_loop()
        def _fetch():
            try:
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    if resp.status == 200:
                        tree = ET.fromstring(resp.read().decode("utf-8", errors="ignore"))
                        channel = tree.find("channel")
                        if channel is None:
                            return []
                        posts = []
                        for item in channel.findall("item"):
                            title = item.findtext("title", "")
                            desc = item.findtext("description", "")
                            link = item.findtext("link", "")
                            full_content = f"{title}\n\n{desc}".strip()
                            posts.append(
                                RawPost(
                                    source="rss",
                                    channel=self.target.platform,
                                    author="rss_publisher",
                                    content=full_content,
                                    url=link,
                                )
                            )
                        return posts
            except Exception as e:
                logger.debug("RSSStreamWorker error fetching %s: %s", url, e)
                return []
            return []

        return await loop.run_in_executor(self.get_executor(), _fetch)

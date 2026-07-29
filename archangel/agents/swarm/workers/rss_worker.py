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

        from archangel.agents.swarm.workers.base import get_shared_client

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ArchangelSwarm/1.0"}
            client = get_shared_client()
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                    tree = ET.fromstring(resp.text)
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

"""RedditWorker — Token-free async poller for subreddit JSON feeds."""

import asyncio
import logging
import urllib.request
import json
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

logger = logging.getLogger(__name__)


class RedditWorker(BasePlatformWorker):
    """Fetches public JSON feed posts from subreddits asynchronously without authentication."""

    async def fetch_posts(self) -> List[RawPost]:
        url = self.target.target_url
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ArchangelSwarm/1.0 (Lead Intelligence Engine)"}
        )

        loop = asyncio.get_event_loop()
        def _fetch():
            try:
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        children = data.get("data", {}).get("children", [])
                        posts = []
                        for c in children:
                            d = c.get("data", {})
                            title = d.get("title", "")
                            selftext = d.get("selftext", "")
                            author = d.get("author", "")
                            permalink = f"https://reddit.com{d.get('permalink', '')}"
                            posts.append(
                                RawPost(
                                    source="reddit",
                                    channel=d.get("subreddit", "reddit"),
                                    author=author,
                                    content=f"{title}\n\n{selftext}".strip(),
                                    url=permalink,
                                )
                            )
                        return posts
            except Exception as e:
                logger.debug("RedditWorker error fetching %s: %s", url, e)
                return []
            return []

        return await loop.run_in_executor(None, _fetch)

"""RedditWorker — Token-free async poller for subreddit JSON feeds."""

import asyncio
import logging
import urllib.request
import json
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class RedditWorker(BasePlatformWorker):
    """Fetches public JSON feed posts from subreddits asynchronously without authentication, with multi-page cursor pagination."""

    def __init__(self, target):
        super().__init__(target)
        self.after_cursor = None

    async def fetch_posts(self) -> List[RawPost]:
        url = self.target.target_url
        if self.after_cursor:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}after={self.after_cursor}"

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)

        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        listing_data = data.get("data", {})
                        self.after_cursor = listing_data.get("after")
                        children = listing_data.get("children", [])
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
                self.after_cursor = None
                return []
            return []

        return await loop.run_in_executor(self.get_executor(), _fetch)

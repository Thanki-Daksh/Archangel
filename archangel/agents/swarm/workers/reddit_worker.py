"""RedditWorker — Token-free async poller for subreddit JSON and RSS feeds with pagination & backoff handling."""

import asyncio
import logging
import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
import random
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class RedditWorker(BasePlatformWorker):
    """Fetches public JSON/RSS feed posts from subreddits asynchronously without authentication, with multi-page cursor pagination."""

    def __init__(self, target):
        super().__init__(target)
        self.after_cursor = None

    async def fetch_posts(self) -> List[RawPost]:
        url = self.target.target_url

        # Check if targeting RSS feed
        is_rss = ".rss" in url or "/feed" in url

        if not is_rss and self.after_cursor:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}after={self.after_cursor}"

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/rss+xml, application/xml, application/json, text/plain, */*" if is_rss else "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)

        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                with urllib.request.urlopen(req, timeout=4.5) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8", errors="ignore")
                        posts = []

                        if is_rss:
                            try:
                                tree = ET.fromstring(raw_body)
                                channel = tree.find("channel")
                                items = channel.findall("item") if channel is not None else tree.findall("{http://www.w3.org/2005/Atom}entry")
                                for item in items:
                                    title = item.findtext("title", "") or item.findtext("{http://www.w3.org/2005/Atom}title", "")
                                    link_elem = item.find("link")
                                    link = item.findtext("link", "")
                                    if not link and link_elem is not None:
                                        link = link_elem.attrib.get("href", "")
                                    content = item.findtext("description", "") or item.findtext("{http://www.w3.org/2005/Atom}content", "")
                                    posts.append(
                                        RawPost(
                                            source="reddit",
                                            channel="reddit_rss",
                                            author="reddit_user",
                                            content=f"{title}\n\n{content}".strip(),
                                            url=link,
                                        )
                                    )
                            except Exception as rss_exc:
                                logger.debug("Error parsing Reddit RSS XML: %s", rss_exc)
                            return posts
                        else:
                            data = json.loads(raw_body)
                            listing_data = data.get("data", {})
                            self.after_cursor = listing_data.get("after")
                            children = listing_data.get("children", [])
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
                    elif resp.status in (429, 403, 500, 502, 503):
                        self.after_cursor = None
                        raise urllib.error.HTTPError(url, resp.status, f"HTTP {resp.status} Rate Limit / Access Denied", resp.headers, None)
            except urllib.error.HTTPError as http_err:
                self.after_cursor = None
                raise http_err
            except Exception as e:
                self.after_cursor = None
                raise e
            return []

        return await loop.run_in_executor(self.get_executor(), _fetch)


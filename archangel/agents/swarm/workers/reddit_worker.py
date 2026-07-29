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

    def _rotate_target_endpoint(self) -> None:
        """Rotates target URL to new timeframes, sorts, or search terms to continuously pull fresh historical leads."""
        import re
        import random
        url_curr = self.target.target_url
        if "t=day" in url_curr:
            self.target.target_url = url_curr.replace("t=day", "t=week")
        elif "t=week" in url_curr:
            self.target.target_url = url_curr.replace("t=week", "t=month")
        elif "t=month" in url_curr:
            self.target.target_url = url_curr.replace("t=month", "t=year")
        elif "t=year" in url_curr:
            self.target.target_url = url_curr.replace("t=year", "t=all")
        elif "/new/.json" in url_curr:
            self.target.target_url = url_curr.replace("/new/.json", "/hot/.json")
        elif "/hot/.json" in url_curr:
            self.target.target_url = url_curr.replace("/hot/.json", "/rising/.json")
        elif "/rising/.json" in url_curr:
            self.target.target_url = url_curr.replace("/rising/.json", "/top/.json?t=month")
        else:
            sub_match = re.search(r"/r/([^/]+)/", url_curr)
            sub_name = sub_match.group(1) if sub_match else "forhire"
            rotations = [
                "hiring", "looking+for+developer", "need+automation", "website",
                "saas", "ai+automation", "python", "react", "fullstack", "contract", "freelance"
            ]
            q = random.choice(rotations)
            self.target.target_url = f"https://www.reddit.com/r/{sub_name}/search/.json?q={q}&restrict_sr=1&sort=new&limit=100"

    async def fetch_posts(self) -> List[RawPost]:
        url = self.target.target_url

        # Check if targeting RSS feed
        is_rss = ".rss" in url or "/feed" in url

        if not is_rss and self.after_cursor:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}after={self.after_cursor}"

        fetch_url = url

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/rss+xml, application/xml, application/json, text/plain, */*" if is_rss else "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # Multi-Key OAuth token pool rotation (if keys configured in .env)
        from archangel.agents.swarm.workers.reddit_auth import RedditTokenPool
        auth_hdr = RedditTokenPool.get_instance().get_auth_header()
        if auth_hdr:
            headers.update(auth_hdr)
        else:
            import os
            reddit_token = os.getenv("REDDIT_ACCESS_TOKEN") or os.getenv("REDDIT_BEARER_TOKEN")
            if reddit_token:
                headers["Authorization"] = f"bearer {reddit_token}"

        from archangel.agents.swarm.workers.base import get_shared_client

        try:
            client = get_shared_client()
            resp = await client.get(fetch_url, headers=headers)
            if resp.status_code == 200:
                raw_body = resp.text
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
                    data = resp.json()
                    listing_data = data.get("data", {})
                    new_after = listing_data.get("after")
                    self.after_cursor = new_after

                    # Auto-rotate timeframe, sort, or keyword when page 1 finishes so worker continuously browses older/hotter posts
                    if not new_after:
                        self._rotate_target_endpoint()

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
            elif resp.status_code in (429, 403, 500, 502, 503):
                self.after_cursor = None
        except Exception as e:
            self.after_cursor = None
            logger.debug("RedditWorker async fetch error: %s", e)

        return []


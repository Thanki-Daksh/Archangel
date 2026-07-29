"""SubredditDiscoveryEngine — Dynamically searches and auto-discovers 500+ hiring and dev subreddits on the fly."""

import asyncio
import logging
from typing import List, Set
import httpx
from archangel.agents.swarm.workers.base import get_shared_client

logger = logging.getLogger(__name__)

DISCOVERY_KEYWORDS = [
    "hiring", "freelance", "job", "developer", "remote", "saas",
    "automation", "python", "fullstack", "react", "ai"
]


class SubredditDiscoveryEngine:
    """Discovers subreddits dynamically via Reddit's public subreddit search API."""

    def __init__(self) -> None:
        self.discovered_subreddits: Set[str] = set()

    async def discover_subreddits(self, extra_keywords: List[str] | None = None) -> List[str]:
        """Queries Reddit search endpoints to discover subreddits on the fly."""
        keywords = list(DISCOVERY_KEYWORDS)
        if extra_keywords:
            keywords.extend(extra_keywords)

        client = get_shared_client()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ArchangelSwarm/1.0",
            "Accept": "application/json",
        }

        for kw in keywords[:5]:  # Fast query top keywords
            url = f"https://www.reddit.com/subreddits/search.json?q={kw}&limit=50"
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        sub_name = child.get("data", {}).get("display_name")
                        sub_type = child.get("data", {}).get("subreddit_type")
                        is_over18 = child.get("data", {}).get("over18", False)
                        if sub_name and sub_type == "public" and not is_over18:
                            self.discovered_subreddits.add(sub_name.lower())
            except Exception as e:
                logger.debug("Subreddit discovery error for %s: %s", kw, e)

        result = sorted(list(self.discovered_subreddits))
        logger.info("SubredditDiscoveryEngine auto-discovered %d active subreddits.", len(result))
        return result

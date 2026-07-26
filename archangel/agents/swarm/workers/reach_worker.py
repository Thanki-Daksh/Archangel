"""AgentReachWorker — Integrates agent-reach scrapers for X/Twitter, GitHub, and HN."""

import asyncio
import logging
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker
from archangel.agents.scraper import SmartScraper

logger = logging.getLogger(__name__)


class AgentReachWorker(BasePlatformWorker):
    """Wrapper that executes real scrapers for multi-platform reach (X/Twitter, GitHub, HN)."""

    async def fetch_posts(self) -> List[RawPost]:
        target = self.target.target_url
        platform = self.target.platform.lower()
        logger.debug("AgentReachWorker executing search for platform %s with target %s", platform, target)

        loop = asyncio.get_event_loop()

        def _fetch() -> List[RawPost]:
            posts: List[RawPost] = []
            scraper = SmartScraper()
            try:
                if "x" in platform or "twitter" in platform:
                    query = "looking for developer OR hiring developer"
                    results = scraper.fetch_x_search_via_ddg(query, max_results=5)
                    for r in results:
                        u = r.get("url", "")
                        if u and "http" in u:
                            author = u.split("/")[3] if len(u.split("/")) > 3 else "x_user"
                            posts.append(
                                RawPost(
                                    source="x",
                                    channel="agent_reach",
                                    author=author,
                                    content=r.get("content", f"X Post from {author}"),
                                    url=u,
                                )
                            )
                elif "github" in platform:
                    import urllib.request
                    import json
                    req = urllib.request.Request(
                        "https://api.github.com/search/issues?q=label:hiring+state:open&per_page=10",
                        headers={"User-Agent": "ArchangelSwarm/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            for item in data.get("items", [])[:5]:
                                posts.append(
                                    RawPost(
                                        source="github",
                                        channel="github_issues",
                                        author=item.get("user", {}).get("login", "gh_user"),
                                        content=f"{item.get('title', '')}\n\n{item.get('body', '')[:500]}",
                                        url=item.get("html_url", ""),
                                    )
                                )
            except Exception as exc:
                logger.debug("AgentReachWorker exception for %s: %s", target, exc)

            return posts

        return await loop.run_in_executor(self.get_executor(), _fetch)


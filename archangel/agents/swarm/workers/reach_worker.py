"""AgentReachWorker — Integrates agent-reach scrapers for X/Twitter, GitHub, and HN."""

import asyncio
import logging
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker
from archangel.agents.scraper import SmartScraper

logger = logging.getLogger(__name__)


_REACH_SEMAPHORE: asyncio.Semaphore | None = None


def _get_reach_semaphore() -> asyncio.Semaphore:
    global _REACH_SEMAPHORE
    if _REACH_SEMAPHORE is None:
        _REACH_SEMAPHORE = asyncio.Semaphore(2)
    return _REACH_SEMAPHORE


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
                    if "agent-reach:x:" in target:
                        q_raw = target.replace("agent-reach:x:", "").strip()
                        query = " ".join(q_raw.split("+"))
                    else:
                        query = target if target.startswith("http") else f"{target} hiring OR looking"

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

                    if target.startswith("http"):
                        gh_url = target
                    else:
                        q_raw = target.replace("agent-reach:github:", "").strip()
                        q_clean = "+".join(q_raw.split())
                        gh_url = f"https://api.github.com/search/issues?q={q_clean}+state:open&per_page=15"

                    req = urllib.request.Request(
                        gh_url,
                        headers={"User-Agent": "ArchangelSwarm/1.0", "Accept": "application/vnd.github.v3+json"}
                    )
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            for item in data.get("items", [])[:15]:
                                posts.append(
                                    RawPost(
                                        source="github",
                                        channel="github_issues",
                                        author=item.get("user", {}).get("login", "gh_user"),
                                        content=f"{item.get('title', '')}\n\n{item.get('body', '')[:1000]}",
                                        url=item.get("html_url", ""),
                                    )
                                )
            except Exception as exc:
                logger.debug("AgentReachWorker exception for %s: %s", target, exc)

            return posts

        async with _get_reach_semaphore():
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(self.get_executor(), _fetch),
                    timeout=3.5
                )
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                return []


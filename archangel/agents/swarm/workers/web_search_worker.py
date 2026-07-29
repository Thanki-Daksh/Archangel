"""WebSearchWorker — Token-free worker scanning open web search engines for buying intent posts."""

import asyncio
import logging
import re
from typing import List
from archangel.models import RawPost
from archangel.agents.swarm.workers.base import BasePlatformWorker

logger = logging.getLogger(__name__)


_WEB_SEMAPHORE: asyncio.Semaphore | None = None


def _get_web_semaphore() -> asyncio.Semaphore:
    global _WEB_SEMAPHORE
    if _WEB_SEMAPHORE is None:
        _WEB_SEMAPHORE = asyncio.Semaphore(2)
    return _WEB_SEMAPHORE


class WebSearchWorker(BasePlatformWorker):
    """Executes web search queries across DuckDuckGo/Google for deep web buying signals."""

    async def fetch_posts(self) -> List[RawPost]:
        target = self.target.target_url
        query = target.replace("web-search:", "").replace("web:", "").strip()
        if not query:
            return []

        loop = asyncio.get_event_loop()

        def _fetch() -> List[RawPost]:
            posts: List[RawPost] = []
            try:
                from archangel.agents.chat import WebSearch
                search_query = " ".join(query.split("+"))
                raw_results = WebSearch().search(f"{search_query} hiring OR looking OR need", max_results=5)

                entries = raw_results.split("\n\n")
                for entry in entries:
                    url_match = re.search(r"URL:\s*(https?://[^\s]+)", entry)
                    if not url_match:
                        continue
                    url = url_match.group(1).strip()

                    lines = [line.strip() for line in entry.split("\n") if line.strip()]
                    title = lines[0] if lines else "Web Search Opportunity"
                    snippet = ""
                    for line in lines:
                        if line.startswith("Snippet:"):
                            snippet = line.replace("Snippet:", "").strip()
                            break

                    author = url.split("/")[2] if len(url.split("/")) > 2 else "web_site"
                    full_content = f"{title}\n\n{snippet}".strip()

                    posts.append(
                        RawPost(
                            source="web",
                            channel=author,
                            author="web_client",
                            content=full_content,
                            url=url,
                        )
                    )
            except Exception as exc:
                logger.debug("WebSearchWorker error fetching query '%s': %s", query, exc)

            return posts

        async with _get_web_semaphore():
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(self.get_executor(), _fetch),
                    timeout=3.5
                )
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                return []

"""Source-specific collectors — gather raw information from the internet."""

import logging
import time

from archangel.models import RawPost

logger = logging.getLogger(__name__)


class CollectorAgent:
    """Gathers raw information from configured sources."""

    def __init__(self) -> None:
        from archangel.agents.scraper import SmartScraper
        self.scraper = SmartScraper()
        logger.debug("CollectorAgent created")

    def collect_all(self) -> list[RawPost]:
        from archangel.config.manager import load_config
        cfg = load_config()
        sources = cfg.get("sources", {}).get("sources", []) or cfg.get("sources", [])

        if not sources:
            logger.warning("No sources configured in sources.yaml")
            return []

        posts = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            if not source.get("enabled", False):
                continue
            try:
                source_type = source.get("type", "")
                if source_type == "reddit":
                    posts.extend(self._collect_reddit(source))
                elif source_type == "x":
                    posts.extend(self._collect_x(source))
                else:
                    logger.debug("Unknown source type: %s", source_type)
            except Exception as exc:
                logger.error("Collector failed for %s: %s", source.get("id", "?"), exc)

        logger.info("CollectorAgent collected %d raw posts", len(posts))
        return posts

    def _collect_reddit(self, source: dict) -> list[RawPost]:
        subreddits = source.get("subreddits", [])
        query = source.get("query", "help needed")
        posts_data = self.scraper.search_reddit_json(
            query, subreddits=subreddits, max_results=source.get("max_results", 10)
        )

        posts = []
        for p in posts_data:
            posts.append(RawPost(
                source="reddit",
                channel=p.get("subreddit", source.get("id", "reddit")),
                author=p.get("author", "unknown"),
                content=f"{p.get('title', '')}\n{p.get('content', '')}",
                timestamp=float(p.get("timestamp", 0)),
                url=p.get("url", ""),
                metadata={"score": p.get("score", 0), "comments": p.get("comments", 0)},
            ))
        logger.debug("Collected %d posts from Reddit (%s)", len(posts), query)
        return posts

    def _collect_x(self, source: dict) -> list[RawPost]:
        query = source.get("query", "need help")
        tweets = self.scraper.fetch_x_search_via_ddg(
            query, max_results=source.get("max_results", 10)
        )

        posts = []
        for t in tweets:
            posts.append(RawPost(
                source="x",
                channel=source.get("id", "x"),
                author=t.get("url", "unknown").split("/")[3] if "/" in t.get("url", "") else "unknown",
                content=t.get("content", ""),
                timestamp=time.time(),
                url=t.get("url", ""),
            ))
        logger.debug("Collected %d posts from X (%s)", len(posts), query)
        return posts

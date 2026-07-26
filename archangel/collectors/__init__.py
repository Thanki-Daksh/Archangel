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

    def get_enabled_sources_count(self) -> int:
        from archangel.config.manager import load_config
        cfg = load_config()
        raw_sources = cfg.get("sources", [])
        sources = raw_sources if isinstance(raw_sources, list) else (raw_sources.get("sources", []) if isinstance(raw_sources, dict) else [])
        return sum(1 for s in sources if isinstance(s, dict) and s.get("enabled", False))

    def _collect_single_source(self, source: dict) -> list[RawPost]:
        if not isinstance(source, dict) or not source.get("enabled", False):
            return []
        try:
            source_type = source.get("type", "")
            if source_type == "reddit":
                return self._collect_reddit(source)
            elif source_type == "x":
                return self._collect_x(source)
            else:
                logger.debug("Unknown source type: %s", source_type)
                return []
        except Exception as exc:
            logger.error("Collector failed for %s: %s", source.get("id", "?"), exc)
            return []

    def collect_all(self) -> list[RawPost]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from archangel.config.manager import load_config
        cfg = load_config()
        raw_sources = cfg.get("sources", [])
        if isinstance(raw_sources, dict):
            sources = raw_sources.get("sources", [])
        elif isinstance(raw_sources, list):
            sources = raw_sources
        else:
            sources = []

        active_sources = [s for s in sources if isinstance(s, dict) and s.get("enabled", False)]
        if not active_sources:
            logger.warning("No enabled sources configured in sources.yaml")
            return []

        posts = []
        with ThreadPoolExecutor(max_workers=min(8, len(active_sources)), thread_name_prefix="collector-worker") as executor:
            future_to_source = {executor.submit(self._collect_single_source, s): s for s in active_sources}
            for future in as_completed(future_to_source):
                try:
                    res = future.result()
                    if res:
                        posts.extend(res)
                except Exception as exc:
                    logger.error("Source collector task failed: %s", exc)

        logger.info("CollectorAgent collected %d raw posts", len(posts))
        return posts

    def _collect_reddit(self, source: dict) -> list[RawPost]:
        source.get("subreddits", [])
        query = source.get("query", "help needed")
        posts_data = self.scraper.search_reddit(
            query,
            max_results=source.get("max_results", 10),
            freshness_days=source.get("freshness_days", 7),
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

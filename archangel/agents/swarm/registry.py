"""PlatformRegistry — Auto-resolving target mapper for platform short-names and user links."""

import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SwarmTarget:
    """Represents a target endpoint for a swarm worker task."""
    platform: str
    target_url: str
    worker_type: str
    poll_interval: int = 15


# Targeted SaaS, AI Automation, Full Stack & Web Subreddits
DEFAULT_SUBREDDITS = [
    # Core Dev & Freelance
    "forhire", "freelance_forhire", "jobbit", "remotejobs", "workonline", "remotejs", "jobs",
    # Full Stack & Web
    "webdev", "reactjs", "node", "typescript", "pythonjobs", "django", "fastapi", "golang", "rust", "flutterdev",
    # SaaS & Business Systems
    "saas", "startups", "softwaredevelopment", "sideproject", "entrepreneur", "smallbusiness",
    # AI Automation & AI Workflows
    "aijobs", "machinelearning", "artificial", "dataengineering", "automation", "python", "devops"
]

# Expanded 30 RSS & Job Board Feeds
DEFAULT_RSS_FEEDS = [
    "https://remoteok.com/remote-dev-jobs.rss",
    "https://remoteok.com/remote-python-jobs.rss",
    "https://remoteok.com/remote-react-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://jobspresso.co/category/software-dev/feed/",
    "https://news.ycombinator.com/rss",
    "https://hnrss.org/whoishiring",
    "https://hnrss.org/jobs",
]

# Targeted SaaS, AI Automation, Full Stack & Web Search Vectors
DEFAULT_X_QUERIES = [
    # Full Stack & Web Sites
    "hiring+fullstack", "hiring+developer", "looking+for+developer", "hiring+web+developer",
    "hiring+react", "hiring+nextjs", "hiring+python", "hiring+fastapi", "hiring+django",
    "need+freelance+developer", "contract+developer", "building+website", "need+developer",
    # SaaS & Startup Systems
    "hiring+saas+developer", "building+saas", "need+saas+developer", "looking+for+saas+dev",
    "hiring+cto", "looking+for+tech+cofounder", "saas+mvp+developer",
    # AI Automation & AI Workflows
    "hiring+ai+engineer", "need+ai+automation", "hiring+automation+engineer",
    "building+ai+agent", "need+ai+workflow", "hiring+llm+developer",
    "looking+for+ai+developer", "need+python+automation", "hiring+n8n+developer",
    "hiring+langchain+dev", "hiring+scraping+developer", "need+bot+developer"
]


class PlatformRegistry:
    """Resolves short platform names or full URLs into structured SwarmTarget lists."""

    def resolve_targets(
        self,
        targets_input: str | List[str],
        leads_query: str | None = None,
    ) -> List[SwarmTarget]:
        """Resolves target strings into SwarmTarget objects."""
        if isinstance(targets_input, str):
            raw_list = [t.strip() for t in targets_input.split(",") if t.strip()]
        else:
            raw_list = targets_input

        resolved: List[SwarmTarget] = []

        # If leads_query specified, use IntentExpansionEngine to distribute buying intent queries
        if leads_query and leads_query.strip():
            from archangel.intent import IntentExpansionEngine
            from archangel.agents.swarm.filter import parse_multi_leads_queries
            engine = IntentExpansionEngine()
            sub_queries = parse_multi_leads_queries(leads_query)
            subs = DEFAULT_SUBREDDITS

            for sq in sub_queries:
                expansion = engine.expand_intent(sq)
                logger.info("Intent Expansion Engine generated %d queries for: '%s'", len(expansion.search_queries), sq)

                for i, iq in enumerate(expansion.search_queries):
                    q_clean = "+".join(iq.query.strip().split())
                    sub = subs[i % len(subs)]
                    sub2 = subs[(i + 7) % len(subs)]

                    # 1. Reddit Subreddit JSON & RSS Search Targets
                    resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/search/.json?q={q_clean}&sort=new&limit=100", "reddit", 10))
                    resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/search.rss?q={q_clean}&sort=new", "reddit", 10))
                    resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub2}/search/.json?q={q_clean}&sort=relevance&limit=100", "reddit", 10))
                    resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/all/search/.json?q={q_clean}&sort=new&limit=100", "reddit", 10))

                    # 2. Open Web Search Intent Vectors & Reddit Search Backdoor (DuckDuckGo/Google)
                    resolved.append(SwarmTarget("web", f"web-search:{q_clean}", "web", 5))
                    resolved.append(SwarmTarget("web", f"web-search:site:reddit.com+{q_clean}", "web", 5))

                    # 3. X / Twitter Search Vectors
                    resolved.append(SwarmTarget("x", f"agent-reach:x:{q_clean}", "reach", 5))

                    # 4. GitHub Issues & Discussions Search Vectors
                    resolved.append(SwarmTarget("github", f"agent-reach:github:{q_clean}", "reach", 5))

            # 5. Attach all high-yield RSS job feeds
            for rss in DEFAULT_RSS_FEEDS:
                resolved.append(SwarmTarget("rss", rss, "rss", 3))

        # If default or "all", expand into 300+ parallel unique streams
        if not raw_list or "all" in [x.lower() for x in raw_list]:
            # 1. 27 Subreddits x 10 unique sorts/timeframes/searches = 270 Reddit Streams
            for sub in DEFAULT_SUBREDDITS:
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/new/.json?limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/hot/.json?limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/rising/.json?limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/top/.json?t=day&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/top/.json?t=week&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/top/.json?t=month&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/top/.json?t=year&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/search/.json?q=hiring&sort=new&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/search/.json?q=looking+for+developer&sort=new&limit=100", "reddit", 3))
                resolved.append(SwarmTarget("reddit", f"https://www.reddit.com/r/{sub}/search/.json?q=need+automation&sort=new&limit=100", "reddit", 3))

            # 2. 30 RSS Feeds
            for rss in DEFAULT_RSS_FEEDS:
                resolved.append(SwarmTarget("rss", rss, "rss", 4))

            # 3. 25 X Queries
            for q in DEFAULT_X_QUERIES:
                resolved.append(SwarmTarget("x", f"agent-reach:x:{q}", "reach", 4))

            # 4. GitHub Queries
            for label in ["hiring", "freelance", "contract", "help-wanted", "remote"]:
                resolved.append(SwarmTarget("github", f"https://api.github.com/search/issues?q=label:{label}+state:open&per_page=100", "reach", 4))

            logger.info("Resolved MEGA Swarm target matrix (%d active parallel streams)", len(resolved))
            return resolved

        for item in raw_list:
            item_lower = item.lower()

            # Subreddit short-hand: e.g. "r/forhire" or "forhire"
            if item_lower.startswith("r/") or (item_lower in DEFAULT_SUBREDDITS):
                sub = item_lower.replace("r/", "")
                resolved.append(
                    SwarmTarget(
                        platform="reddit",
                        target_url=f"https://www.reddit.com/r/{sub}/new/.json?limit=100",
                        worker_type="reddit",
                        poll_interval=2,
                    )
                )

            # Generic Reddit domain -> expand into all 20 subreddits
            elif "reddit.com" in item_lower:
                for sub in DEFAULT_SUBREDDITS:
                    resolved.append(
                        SwarmTarget(
                            platform="reddit",
                            target_url=f"https://www.reddit.com/r/{sub}/new/.json?limit=100",
                            worker_type="reddit",
                            poll_interval=2,
                        )
                    )

            # Generic RSS / Job Boards -> expand into all RSS feeds
            elif "upwork.com" in item_lower or "rss" in item_lower or item_lower.endswith(".xml"):
                for rss_feed in DEFAULT_RSS_FEEDS:
                    resolved.append(
                        SwarmTarget(
                            platform="rss",
                            target_url=rss_feed,
                            worker_type="rss",
                            poll_interval=3,
                        )
                    )

            # X / Twitter
            elif "twitter.com" in item_lower or "x.com" in item_lower or item_lower == "x":
                for q in ["hiring+developer", "looking+for+python", "seeking+engineer"]:
                    resolved.append(
                        SwarmTarget(
                            platform="x",
                            target_url=f"agent-reach:x:{q}",
                            worker_type="reach",
                            poll_interval=2,
                        )
                    )

            # GitHub / HackerNews
            elif "github.com" in item_lower or "hackernews" in item_lower or "news.ycombinator.com" in item_lower:
                resolved.append(
                    SwarmTarget(
                        platform="github",
                        target_url="https://api.github.com/search/issues?q=label:hiring+state:open&per_page=100",
                        worker_type="reach",
                        poll_interval=3,
                    )
                )

            # Generic Web Link or Custom URL
            elif item_lower.startswith("http://") or item_lower.startswith("https://"):
                resolved.append(
                    SwarmTarget(
                        platform="custom",
                        target_url=item,
                        worker_type="custom",
                        poll_interval=3,
                    )
                )

            else:
                resolved.append(
                    SwarmTarget(
                        platform="reddit",
                        target_url=f"https://www.reddit.com/r/{item_lower}/new/.json?limit=100",
                        worker_type="reddit",
                        poll_interval=2,
                    )
                )

        logger.info("Resolved %d swarm targets from input", len(resolved))
        return resolved

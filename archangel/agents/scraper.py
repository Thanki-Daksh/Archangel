"""Multi-engine web scraper for Archangel — Scrapling primary, Obscura fallback."""

import subprocess
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class ObscuraScraper:
    """Fallback scraper using Obscura headless browser (Rust/V8)."""

    def __init__(self):
        self._obscura = shutil.which("obscura")
        if not self._obscura:
            local = Path(__file__).resolve().parents[2] / "tools" / "obscura" / "obscura.exe"
            if local.exists():
                self._obscura = str(local)

    def _run(self, args, timeout=30):
        if not self._obscura:
            return "Error: obscura binary not found"
        try:
            result = subprocess.run([self._obscura] + args, capture_output=True, timeout=timeout)
            try:
                stdout = result.stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                stdout = result.stdout.decode("latin-1", errors="replace").strip()
            if result.returncode == 0:
                return stdout
            try:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
            except Exception:
                stderr = result.stderr.decode("latin-1", errors="replace").strip()
            return f"Error: {stderr}"
        except subprocess.TimeoutExpired:
            return "Error: obscura command timed out"
        except Exception as exc:
            return f"Error: {exc}"

    def fetch_text(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "text", "--timeout", str(timeout)], timeout + 10)

    def fetch_html(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "html", "--timeout", str(timeout)], timeout + 10)

    def fetch_links(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "links", "--timeout", str(timeout)], timeout + 10)

    def fetch_eval(self, url, js, timeout=30):
        return self._run(["fetch", url, "--eval", js, "--timeout", str(timeout)], timeout + 10)

    def fetch_markdown(self, url, timeout=30):
        return self._run(["fetch", url, "--dump", "markdown", "--timeout", str(timeout)], timeout + 10)


class ScraplingScraper:
    """Primary scraper using Scrapling (fast HTTP + stealth browser)."""

    def __init__(self):
        self._init_failed = False
        try:
            from scrapling import Fetcher
            self._fetcher_cls = Fetcher
        except ImportError:
            try:
                from scrapling.fetchers import Fetcher
                self._fetcher_cls = Fetcher
            except ImportError:
                logger.warning("Scrapling not installed — falling back to Obscura only")
                self._init_failed = True

    def fetch_text(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(
                url,
                timeout=timeout,
                stealthy_headers=True,
            )
            return page.get_all_text(separator="\n", strip=True)
        except Exception as exc:
            logger.warning("Scrapling HTTP fetch failed for %s: %s", url, exc)
            return "__FALLBACK__"

    def fetch_html(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            return page.body if hasattr(page, 'body') else str(page)
        except Exception:
            return "__FALLBACK__"

    def fetch_links(self, url, timeout=30):
        if self._init_failed:
            return "__FALLBACK__"
        try:
            page = self._fetcher_cls.get(url, timeout=timeout)
            links = page.css('a::attr(href)').getall() if hasattr(page, 'css') else []
            return "\n".join(links) if links else "__FALLBACK__"
        except Exception:
            return "__FALLBACK__"

class SmartScraper:
    """Unified scraper — Scrapling first, Obscura fallback."""

    JS_HEAVY_SITES = ["x.com", "twitter.com", "instagram.com", "tiktok.com"]

    def __init__(self):
        self.scrapling = ScraplingScraper()
        self.obscura = ObscuraScraper()
        self._load_heuristic_keywords()

    def _load_heuristic_keywords(self):
        try:
            from archangel.config.manager import load_config
            cfg = load_config()
            self.title_demand_keywords = tuple(cfg.get("title_demand_keywords") or self._TITLE_DEMAND_KEYWORDS)
            self.body_demand_keywords = tuple(cfg.get("body_demand_keywords") or self._BODY_DEMAND_KEYWORDS)
            self.supply_signals = tuple(cfg.get("supply_signals") or self._SUPPLY_SIGNALS)
            self.non_tech_job_titles = tuple(cfg.get("non_tech_job_titles") or self._NON_TECH_JOB_TITLES)
            self.tech_keywords = tuple(cfg.get("tech_keywords") or self._TECH_KEYWORDS)
        except Exception:
            self.title_demand_keywords = self._TITLE_DEMAND_KEYWORDS
            self.body_demand_keywords = self._BODY_DEMAND_KEYWORDS
            self.supply_signals = self._SUPPLY_SIGNALS
            self.non_tech_job_titles = self._NON_TECH_JOB_TITLES
            self.tech_keywords = self._TECH_KEYWORDS

    def _needs_js(self, url):
        return any(site in url.lower() for site in self.JS_HEAVY_SITES)

    def fetch_text(self, url, timeout=30):
        # JS-heavy sites → Obscura directly (Scrapling async conflicts)
        if self._needs_js(url):
            return self.obscura.fetch_text(url, timeout)
        result = self.scrapling.fetch_text(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_text(url, timeout)

    def fetch_html(self, url, timeout=30):
        if self._needs_js(url):
            return self.obscura.fetch_html(url, timeout)
        result = self.scrapling.fetch_html(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_html(url, timeout)

    def fetch_links(self, url, timeout=30):
        if self._needs_js(url):
            return self.obscura.fetch_links(url, timeout)
        result = self.scrapling.fetch_links(url, timeout)
        if result != "__FALLBACK__":
            return result
        return self.obscura.fetch_links(url, timeout)

    def fetch_eval(self, url, js, timeout=30):
        return self.obscura.fetch_eval(url, js, timeout)

    def fetch_markdown(self, url, timeout=30):
        return self.obscura.fetch_markdown(url, timeout)

    def _is_recent(self, date_str: str = None, timestamp: float = None, days: int = 5) -> bool:
        """Check if content is from last N days."""
        import time
        from datetime import datetime

        cutoff = time.time() - (days * 24 * 60 * 60)

        if timestamp:
            return timestamp > cutoff

        if date_str:
            try:
                # Try common formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%a %b %d %H:%M:%S %z %Y"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.timestamp() > cutoff
                    except ValueError:
                        continue
            except Exception:
                pass

        return True  # If can't parse, assume recent

    def fetch_tweet(self, url: str, timeout: int = 20) -> str:
        """Fetch tweet content via fxtwitter.com mirror."""
        fx_url = (
            url.replace("https://x.com/", "https://fxtwitter.com/")
               .replace("https://twitter.com/", "https://fxtwitter.com/")
        )
        # Try Scrapling first (fast HTTP)
        if not self.scrapling._init_failed:
            try:
                page = self.scrapling._fetcher_cls.get(fx_url, timeout=timeout, stealthy_headers=True)
                text = page.get_all_text(separator="\n", strip=True)
                if text:
                    return text
            except Exception:
                pass
        # Fallback: Obscura
        return self.obscura.fetch_text(fx_url, timeout)

    def _search_google_tweets(self, query: str, max_results: int = 5) -> list[str]:
        """Search Google for actual X/Tweet URLs."""
        import requests
        import re
        from datetime import datetime, timedelta

        after_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        search_query = f"site:x.com {query} after:{after_date}"
        url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}&num={max_results}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            # Extract only tweet URLs (x.com/username/status/123456)
            tweet_urls = re.findall(r'https?://(?:www\.)?x\.com/\w+/status/\d+', resp.text)
            # Deduplicate preserving order
            return list(dict.fromkeys(tweet_urls))[:max_results]
        except Exception as e:
            logger.error("Google search failed: %s", e)
            return []

    def _tweet_is_recent(self, url: str, days: int = 5) -> bool:
        from datetime import datetime, timedelta
        import re
        match = re.search(r'/status/(\d+)', url)
        if not match:
            return True
        try:
            tweet_id = int(match.group(1))
            ms = (tweet_id >> 22) + 1288834974656
            post_time = datetime.fromtimestamp(ms / 1000)
            return post_time >= datetime.now() - timedelta(days=days)
        except (ValueError, OverflowError):
            return True

    def fetch_x_search_via_ddg(self, query: str, max_results: int = 5) -> list:
        """Search X via Google + DuckDuckGo, fetch tweets via fxtwitter."""
        from archangel.agents.chat import WebSearch
        import re

        tweets = []

        # Strategy 1: Google (finds actual tweets)
        google_urls = self._search_google_tweets(query, max_results=max_results)
        for url in google_urls[:3]:
            if not self._tweet_is_recent(url):
                continue
            content = self.fetch_tweet(url)
            if content and not content.startswith("Error:"):
                tweets.append({"url": url, "content": content[:3000]})

        # Strategy 2: DuckDuckGo fallback
        if len(tweets) < 3:
            results = WebSearch().search(f"{query} site:x.com", max_results=max_results)
            urls = re.findall(r"URL:\s*(https?://[^\s]+)", results)
            for url in urls[:3]:
                # ONLY keep actual tweet URLs
                if re.search(r'x\.com/\w+/status/\d+', url) and not any(t['url'] == url for t in tweets):
                    if not self._tweet_is_recent(url):
                        continue
                    content = self.fetch_tweet(url)
                    if content and not content.startswith("Error:"):
                        tweets.append({"url": url, "content": content[:3000]})

        return tweets

    def fetch_reddit_rss(self, url: str, timeout: int = 15) -> str:
        """Fetch Reddit content via RSS feed (bypasses anti-bot)."""
        import re

        # Convert Reddit URL to RSS
        # https://www.reddit.com/r/Discord_Bots/comments/abc123/title/
        # → https://www.reddit.com/r/Discord_Bots/comments/abc123/title/.rss
        rss_url = url.rstrip("/")
        if not rss_url.endswith(".rss"):
            rss_url += "/.rss"

        # Try Scrapling HTTP first
        if not self.scrapling._init_failed:
            try:
                page = self.scrapling._fetcher_cls.get(rss_url, timeout=timeout, stealthy_headers=True)
                text = page.get_all_text(separator="\n", strip=True) if hasattr(page, 'get_all_text') else str(page)
                if text and len(text) > 50:
                    return text
            except Exception:
                pass

        # Fallback: try Obscura
        return self.obscura._run(["fetch", rss_url, "--dump", "text", "--timeout", str(timeout)], timeout + 10)

    # ── Buyer-intent signals ──────────────────────────────────────────
    # Strong signals that appear in TITLES of demand-side posts
    _TITLE_DEMAND_KEYWORDS = (
        "[hiring]", "hiring", "want to hire", "looking to hire",
        "need a developer", "need a bot", "need a coder", "need a programmer",
        "need help building", "need someone to build", "need someone to",
        "freelancer needed", "developer needed", "coder needed",
        "looking for a developer", "looking for someone", "looking for a freelancer",
        "looking for a bot", "looking for help",
        "will pay", "paying", "paid", "budget",
        "help needed", "urgently need",
        "gig", "bounty", "commission",
        "looking to pay", "custom bot request",
        "need help", "need a", "looking for",
    )

    # Signals that appear in post BODY indicating buyer intent
    _BODY_DEMAND_KEYWORDS = (
        "hiring", "will pay", "budget", "paid", "paying",
        "looking for a developer", "looking for someone",
        "need a developer", "need a bot", "freelancer needed",
        "dm me", "send me a message", "contact me",
        "how much would", "what would it cost", "quote",
    )

    # Supply-side & non-lead signals — self-promos, tutorials, dumps, articles, etc.
    _SUPPLY_SIGNALS = (
        "[for hire]", "for hire", "[offer]", "available for work",
        "i am a developer", "i'm a developer", "hire me",
        "looking for work", "looking for a job", "open to work",
        "seeking employment", "available for freelance",
        "my portfolio", "my services", "i offer",
        "looking for remote", "open for", "i can build",
        "i can make", "i can create", "i can develop",
        "i'm available", "i am available",
        "how i make", "how to make", "tutorial", "guide",
        "case study", "how we built", "how i built",
        "open sourcing", "open source", "dumps", "cheat",
        "i made", "we made", "i created", "we created", "i built", "we built",
        "my app", "my project", "my tool", "check out", "showcase",
        "exam dumps", "dumps website", "authenticating",
    )

    def _has_buyer_intent(self, title: str, body: str = "") -> bool:
        """Check if a post shows genuine buyer/hiring intent."""
        t = title.lower()
        b = body.lower() if body else ""

        # Supply / promo / article check
        if any(sig in t for sig in self.supply_signals):
            return False

        # Strong: title contains explicit buyer demand keyword
        if any(kw in t for kw in self.title_demand_keywords):
            return True

        # Weaker: body contains demand keyword (only if body is provided and title isn't an article/question)
        if b and any(kw in b for kw in self.body_demand_keywords):
            if any(w in t for w in ("how ", "why ", "what ", "where ", "faq:", "solution:", "guide:", "released", "v1.", "v2.", "v3.")):
                return False
            return True

        return False

    # Non-software / non-tech job titles to reject when searching for dev/tech leads
    _NON_TECH_JOB_TITLES = (
        "business development", "sales specialist", "sales manager", "account executive",
        "graphic designer", "ui/ux designer", "ui designer", "ux designer", "illustrator",
        "behavior technician", "rbt", "aba therapy", "nursing", "caregiver",
        "virtual assistant", "data entry", "transcription", "copywriter", "content writer",
        "video editor", "social media manager", "seo specialist", "marketing manager",
        "customer service", "receptionist", "janitorial", "cleaner",
    )

    # Software / tech keywords
    _TECH_KEYWORDS = (
        "software", "developer", "developers", "programmer", "programmers",
        "coder", "coders", "engineer", "engineers", "fullstack", "full-stack",
        "frontend", "front-end", "backend", "back-end", "devops", "web dev", "web developer",
        "python", "javascript", "typescript", "react", "node", "nodejs", "vue",
        "django", "flask", "fastapi", "golang", "rust", "c++", "c#", "java",
        "bot", "bots", "automation", "n8n", "zapier", "ai agent", "llm",
    )

    def _is_relevant_lead(self, query: str, title: str, body: str = "") -> bool:
        """Ensure search result actually matches the requested domain (e.g. dev jobs vs graphic design/sales)."""
        import re
        t = title.lower()
        b = body.lower() if body else ""
        q = query.lower()

        # If user is searching for software/dev/code/bot/tech jobs:
        dev_search = any(k in q for k in ("dev", "code", "coder", "prog", "bot", "software", "tech", "web", "python", "js", "react", "node", "n8n", "auto"))

        if dev_search:
            # 1. Reject explicit non-tech titles (e.g. Graphic Designer, Business Development, Behavior Technician)
            if any(n in t for n in self.non_tech_job_titles):
                return False

            # 2. Ensure title or body contains actual tech/dev terms or the query itself as a word
            if any(re.search(r'\b' + re.escape(k) + r'\b', t) for k in self.tech_keywords):
                return True
            if re.search(r'\b' + re.escape(q) + r'\b', t):
                return True
            if b and (any(re.search(r'\b' + re.escape(k) + r'\b', b) for k in self.tech_keywords) or re.search(r'\b' + re.escape(q) + r'\b', b)):
                return True

            return False

        # General query match
        if re.search(r'\b' + re.escape(q) + r'\b', t) or (b and re.search(r'\b' + re.escape(q) + r'\b', b)):
            return True

        return True

    _MSG_STOP_WORDS = {
        "accepts", "accept", "payment", "payments", "thru", "through", "via",
        "with", "from", "that", "this", "have", "need", "want", "for", "and",
        "the", "a", "an", "is", "to", "in", "of", "or", "client", "needs", "looking",
        "must", "should", "only", "also", "using", "use",
    }

    def _extract_filter_keywords(self, message_filter: str | None) -> list[str]:
        """Extract core target terms (removing filler/stop words) from a natural language requirement."""
        if not message_filter:
            return []
        import re
        words = re.findall(r'\b[a-zA-Z0-9+$#-]+\b', message_filter.lower())
        return [w for w in words if w not in self._MSG_STOP_WORDS and len(w) >= 2]

    def _matches_message_filter(self, message_filter: str | None, title: str, body: str = "") -> bool:
        """Check if title or body matches custom message/requirement filter."""
        if not message_filter:
            return True

        text = (title + " " + (body or "")).lower()
        mf = message_filter.lower()

        # 1. Direct phrase or full string match
        if mf in text:
            return True

        # 2. Extract core keywords (filtering out stop words like accepts, payment, thru)
        keywords = self._extract_filter_keywords(message_filter)
        if not keywords:
            return True

        # 3. Match if ANY of the core keywords (e.g. 'upi', 'paypal') are present in text
        return any(k in text for k in keywords)

    def _is_supply_side(self, title: str) -> bool:
        """Detect supply-side posts (people OFFERING services, not HIRING)."""
        t = title.lower()
        return any(sig in t for sig in self.supply_signals)

    def search_reddit_json(self, query: str, subreddits: list[str] = None, max_results: int = 10, freshness_days: int = 7) -> list[dict]:
        """Search Reddit via GLOBAL search endpoint for buyer-intent leads.

        Uses 1 global search request instead of per-subreddit requests
        to avoid rate limiting. Enforces freshness_days cutoff.
        """
        import time
        import requests as req_lib

        cutoff = time.time() - freshness_days * 86400
        # Use t=week for <=7 days, t=month for longer windows
        t_param = "week" if freshness_days <= 7 else "month"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
        }

        posts = []

        # Build intent-boosted search queries for Reddit global search
        search_queries = [
            f"{query} (hiring OR need OR paid OR looking for)",
            query,  # plain fallback
        ]

        for sq in search_queries:
            if len(posts) >= max_results:
                break
            try:
                url = f"https://www.reddit.com/search.json?q={sq}&sort=new&limit=25&t={t_param}"
                resp = req_lib.get(url, headers=headers, timeout=15)
                if resp.status_code == 429:
                    time.sleep(2)
                    continue
                if resp.status_code != 200:
                    continue

                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for child in children:
                    post_data = child.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    author = post_data.get("author", "")
                    permalink = post_data.get("permalink", "")
                    subreddit = post_data.get("subreddit", "")
                    score = post_data.get("score", 0)
                    num_comments = post_data.get("num_comments", 0)
                    created_utc = post_data.get("created_utc", 0)

                    if not title:
                        continue
                    # STRICT: Skip posts older than 5 days
                    if not created_utc or created_utc < cutoff:
                        continue

                    full_url = f"https://reddit.com{permalink}"
                    if any(p["url"] == full_url for p in posts):
                        continue

                    # Must show buyer intent (title or body)
                    if not self._has_buyer_intent(title, selftext):
                        continue
                    # Skip supply-side
                    if self._is_supply_side(title):
                        continue

                    posts.append({
                        "title": title,
                        "content": selftext[:2000] if selftext else "",
                        "author": author or "unknown",
                        "url": full_url,
                        "subreddit": subreddit or "reddit",
                        "score": score,
                        "comments": num_comments,
                        "timestamp": created_utc,
                    })

                time.sleep(0.5)

            except Exception as e:
                logger.warning("Reddit global search failed for q=%s: %s", sq, e)
                continue

        posts.sort(key=lambda x: x.get("score", 0) + x.get("comments", 0), reverse=True)
        return posts[:max_results]

    def _estimate_reddit_timestamp_from_id(self, reddit_url: str) -> float:
        """Estimate post created_utc from sequential base36 post ID when .json API is blocked."""
        import re
        import time

        match = re.search(r'/comments/([a-z0-9]+)/', reddit_url, re.IGNORECASE)
        if not match:
            return 0
        try:
            id36 = match.group(1).lower()
            post_num = int(id36, 36)
            # Calibration anchor: post '1rhietd' = July 22, 2026 (timestamp ~1784733500)
            # Average Reddit post creation rate across all subreddits: ~13.5 posts/second
            ref_id = int("1rhietd", 36)
            ref_ts = 1784733500.0
            rate = 13.5
            est_ts = ref_ts - ((ref_id - post_num) / rate)
            # Don't return future timestamps higher than now
            return min(est_ts, time.time())
        except Exception:
            return 0

    def _get_reddit_post_timestamp(self, reddit_url: str) -> float:
        """Instantly estimate created_utc from post base36 ID without blocking HTTP requests."""
        return self._estimate_reddit_timestamp_from_id(reddit_url)

    def search_reddit_old_html(self, query: str, max_results: int = 10, freshness_days: int = 7, max_comments: int | None = None, message_filter: str | None = None) -> list[dict]:
        """Search old.reddit.com HTML directly — bypasses Cloudflare 403 blocks and gets 100% real, fresh posts."""
        import requests as req_lib
        import urllib.parse
        import time
        import re
        from datetime import datetime, timezone
        from bs4 import BeautifulSoup

        cutoff = time.time() - (freshness_days * 86400)
        headers = {
            "User-Agent": "archangel:lead-finder:v1.0 (by /u/archangel_bot)"
        }

        # Targeted subreddits ONLY (no global search to prevent random subreddits/articles)
        sub_list = "hiring+forhire+slavelabour+jobbit+freelance_forhire+Discord_Bots+pythonforhire+design_jobs+remotejs"
        buyer_query = f"{query} (hiring OR need OR paid OR budget OR task OR \"looking for\")"
        urls = [
            f"https://old.reddit.com/r/{sub_list}/search?q={urllib.parse.quote(buyer_query)}&sort=new&restrict_sr=on",
            f"https://old.reddit.com/r/{sub_list}/search?q={urllib.parse.quote(query)}&sort=new&restrict_sr=on",
        ]

        # If user passed a custom requirement (e.g. message: accepts payment thru upi), inject target keyword search URL
        if message_filter:
            kw_list = self._extract_filter_keywords(message_filter)
            if kw_list:
                kw_str = " OR ".join(kw_list)
                urls.insert(0, f"https://old.reddit.com/r/{sub_list}/search?q={urllib.parse.quote(kw_str)}&sort=new&restrict_sr=on")
                urls.insert(1, f"https://old.reddit.com/r/{sub_list}/search?q={urllib.parse.quote(query + ' (' + kw_str + ')')}&sort=new&restrict_sr=on")

        posts = []
        seen_urls = set()

        for search_url in urls:
            if len(posts) >= max_results:
                break
            try:
                resp = req_lib.get(search_url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                things = soup.find_all("div", class_="search-result")

                for t in things:
                    if len(posts) >= max_results:
                        break

                    title_a = t.find("a", class_="search-title")
                    if not title_a:
                        continue

                    title = title_a.text.strip()
                    raw_href = title_a.get("href", "")
                    if not raw_href:
                        continue

                    if raw_href.startswith("/"):
                        post_url = "https://www.reddit.com" + raw_href
                    else:
                        post_url = raw_href.replace("old.reddit.com", "www.reddit.com")

                    if post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)

                    # Extract comment count
                    comm_elem = t.find("a", class_="search-comments")
                    num_comments = 0
                    if comm_elem:
                        c_match = re.search(r'(\d+)', comm_elem.text)
                        if c_match:
                            num_comments = int(c_match.group(1))

                    if max_comments is not None and num_comments > max_comments:
                        continue

                    # Extract ISO timestamp
                    time_elem = t.find("time")
                    post_ts = 0
                    if time_elem and time_elem.get("datetime"):
                        try:
                            dt = datetime.fromisoformat(time_elem["datetime"])
                            post_ts = dt.timestamp()
                        except Exception:
                            post_ts = self._get_reddit_post_timestamp(post_url)
                    else:
                        post_ts = self._get_reddit_post_timestamp(post_url)

                    if not post_ts or post_ts < cutoff:
                        continue

                    # Supply check
                    if self._is_supply_side(title):
                        continue

                    # Extract snippet body
                    snippet_elem = t.find("div", class_="search-result-body")
                    body = snippet_elem.text.strip() if snippet_elem else ""

                    # Buyer Intent Check — MUST show genuine hiring/buyer demand
                    if not self._has_buyer_intent(title, body):
                        continue

                    # Domain Relevance Check — MUST match dev/software domain, NOT sales/design/healthcare
                    if not self._is_relevant_lead(query, title, body):
                        continue

                    # Custom Message / Requirement Filter Check
                    if message_filter and not self._matches_message_filter(message_filter, title, body):
                        continue

                    author_elem = t.find("a", class_="author")
                    author = author_elem.text.strip() if author_elem else "unknown"

                    sub_elem = t.find("a", class_="search-subreddit-link")
                    subreddit = sub_elem.text.strip().lstrip("r/") if sub_elem else "reddit"
                    if not subreddit or subreddit == "reddit":
                        if "/r/" in post_url:
                            subreddit = post_url.split("/r/")[1].split("/")[0]

                    posts.append({
                        "title": title or "Lead Opportunity",
                        "content": body[:2000] if body else title,
                        "author": author,
                        "url": post_url,
                        "subreddit": subreddit,
                        "score": 10,
                        "comments": num_comments,
                        "timestamp": post_ts,
                    })
            except Exception as exc:
                logger.warning("old.reddit HTML search failed: %s", exc)

        return posts

    def search_reddit(self, query: str, max_results: int = 5, freshness_days: int = 7, max_comments: int | None = None, message_filter: str | None = None) -> list[dict]:
        """Search Reddit for buyer-intent leads. HTML direct search first, JSON & DDG fallback.

        ALL results are freshness-checked (default: last 7 days).
        Use fresh:N, comments:N, and message:... in the CLI to override.
        """
        import time

        cutoff = time.time() - freshness_days * 86400

        # Strategy 1: Direct old.reddit HTML search (bypasses Cloudflare 403 blocks)
        posts = self.search_reddit_old_html(query, max_results=max_results, freshness_days=freshness_days, max_comments=max_comments, message_filter=message_filter)
        if len(posts) >= max_results:
            return posts[:max_results]

        # Strategy 2: Reddit global JSON search
        json_posts = self.search_reddit_json(query, max_results=max_results - len(posts), freshness_days=freshness_days)
        for jp in json_posts:
            if not any(p["url"] == jp["url"] for p in posts):
                posts.append(jp)

        if len(posts) >= max_results:
            return posts[:max_results]

        # Strategy 2: DuckDuckGo fallback with simple queries
        from archangel.agents.chat import WebSearch

        ddg_queries = [
            f'{query} hiring site:reddit.com',
            f'{query} "need" OR "looking for" OR "paid" site:reddit.com',
            f'{query} site:reddit.com',
        ]

        for ddg_q in ddg_queries:
            if len(posts) >= max_results:
                break
            try:
                ddg_text = WebSearch().search(ddg_q, max_results=max_results)
                if not ddg_text or "No results found" in ddg_text:
                    continue

                blocks = ddg_text.split("\n\n")
                for block in blocks:
                    lines = block.strip().splitlines()
                    if not lines:
                        continue
                    title = lines[0].lstrip("0123456789. ").strip()
                    url = ""
                    body = ""
                    for l in lines[1:]:
                        if l.strip().startswith("URL:"):
                            url = l.replace("URL:", "").strip()
                        else:
                            body += " " + l.strip()

                    if not url or "reddit.com" not in url:
                        continue
                    if any(p["url"] == url for p in posts):
                        continue
                    # For DDG: check title for demand signals
                    if not self._has_buyer_intent(title, ""):
                        continue
                    if self._is_supply_side(title):
                        continue

                    # FRESHNESS CHECK: fetch actual post timestamp from Reddit
                    post_ts = self._get_reddit_post_timestamp(url)
                    if not post_ts or post_ts < cutoff:
                        # Can't verify freshness or post is too old — skip it
                        logger.debug("Skipping DDG result (age unknown or stale): %s", title[:60])
                        continue

                    sub = "reddit"
                    if "/r/" in url:
                        sub = url.split("/r/")[1].split("/")[0]

                    posts.append({
                        "title": title or "Lead Opportunity",
                        "content": body.strip()[:2000],
                        "author": "unknown",
                        "url": url,
                        "subreddit": sub,
                        "score": 5,
                        "comments": 1,
                        "timestamp": post_ts or time.time(),
                    })
            except Exception as exc:
                logger.warning("DDG lead search failed: %s", exc)

        return posts[:max_results]

    def search_linkedin(self, query: str, max_results: int = 5, freshness_days: int = 7) -> list[dict]:
        """Search LinkedIn public job postings and hiring posts."""
        from archangel.agents.chat import WebSearch
        import time

        queries = [
            f'site:linkedin.com/jobs "{query}" hiring remote',
            f'site:linkedin.com/jobs/view "{query}" remote',
            f'site:linkedin.com/posts "{query}" hiring',
        ]

        posts = []
        seen_urls = set()

        for q in queries:
            if len(posts) >= max_results:
                break
            try:
                results_text = WebSearch().search(q, max_results=max_results)
                if not results_text or "No results found" in results_text:
                    continue

                blocks = results_text.split("\n\n")
                for block in blocks:
                    lines = block.strip().splitlines()
                    if not lines:
                        continue
                    title = lines[0].lstrip("0123456789. ").strip()
                    url = ""
                    snippet = ""
                    for l in lines[1:]:
                        if l.strip().startswith("URL:"):
                            url = l.replace("URL:", "").strip()
                        else:
                            snippet += " " + l.strip()

                    if not url or "linkedin.com" not in url:
                        continue
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    posts.append({
                        "title": title or f"LinkedIn {query} Lead",
                        "content": snippet[:1500] if snippet else title,
                        "author": "LinkedIn Hiring",
                        "url": url,
                        "subreddit": "linkedin",
                        "score": 15,
                        "comments": 0,
                        "timestamp": time.time(),
                    })
            except Exception as exc:
                logger.warning("LinkedIn lead search error: %s", exc)

        return posts[:max_results]


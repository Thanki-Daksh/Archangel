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

    # ── Buyer-intent signals (STRICT — only real demand signals) ─────
    _BUYER_KEYWORDS = (
        "[hiring]", "hiring", "want to hire", "looking to hire",
        "need a developer", "need a bot", "need a coder", "need a programmer",
        "need help building", "need someone to build",
        "freelancer needed", "developer needed", "coder needed",
        "looking for a developer", "looking for someone", "looking for a freelancer",
        "will pay", "paying", "paid", "budget",
        "help needed", "urgently need", "asap",
        "gig", "bounty", "commission",
        "looking to pay", "custom bot request",
    )

    # Subreddits where real buyers post
    _LEAD_SUBREDDITS = [
        "forhire", "slavelabour", "jobbit", "hiring",
        "freelance", "remotejs", "remotepython", "PythonJobs",
        "webdev", "gameDevClassifieds", "DesignJobs",
        "Entrepreneur", "smallbusiness", "startups",
        "SaaS", "microsaas", "sidehustle",
        "automation", "Discord_Bots", "discordapp",
    ]

    def _has_buyer_intent(self, title: str, body: str) -> bool:
        """Check if a post shows genuine buyer/hiring intent."""
        combined = (title + " " + body).lower()
        return any(kw in combined for kw in self._BUYER_KEYWORDS)

    def _is_supply_side(self, title: str) -> bool:
        """Detect supply-side posts (people OFFERING services, not HIRING).
        We want to skip these — we only want demand-side leads."""
        t = title.lower()
        supply_signals = (
            "[for hire]", "for hire", "available for work",
            "i am a developer", "i'm a developer", "hire me",
            "looking for work", "looking for a job", "open to work",
            "seeking employment", "available for freelance",
            "my portfolio", "my services", "i offer",
            "looking for remote", "open for", "i can build",
            "i can make", "i can create", "i can develop",
        )
        return any(sig in t for sig in supply_signals)

    def search_reddit_json(self, query: str, subreddits: list[str] = None, max_results: int = 10) -> list[dict]:
        """Search Reddit via their public JSON API for buyer-intent leads."""
        import time
        import requests as req_lib

        if subreddits is None:
            subreddits = self._LEAD_SUBREDDITS

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
        }

        posts = []

        # Single query with intent keywords — faster than 3 queries per sub
        intent_query = f"{query} hiring OR looking for OR need"

        for sub in subreddits:
            if len(posts) >= max_results:
                break
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={intent_query}&sort=new&limit=10&restrict_sr=1&t=month"
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
                    score = post_data.get("score", 0)
                    num_comments = post_data.get("num_comments", 0)
                    created_utc = post_data.get("created_utc", 0)

                    if not title:
                        continue
                    # Skip old posts (>30 days)
                    if created_utc and created_utc < time.time() - 30 * 86400:
                        continue

                    full_url = f"https://reddit.com{permalink}"
                    # Deduplicate by URL
                    if any(p["url"] == full_url for p in posts):
                        continue

                    # Must show buyer intent
                    if not self._has_buyer_intent(title, selftext):
                        continue
                    # Skip supply-side posts (people offering services, not hiring)
                    if self._is_supply_side(title):
                        continue

                    posts.append({
                        "title": title,
                        "content": selftext[:2000] if selftext else "",
                        "author": author or "unknown",
                        "url": full_url,
                        "subreddit": sub,
                        "score": score,
                        "comments": num_comments,
                        "timestamp": created_utc,
                    })

                time.sleep(0.5)  # Rate limit

            except Exception as e:
                logger.warning("Reddit JSON search failed for r/%s: %s", sub, e)
                continue

        # Sort by engagement (score + comments) — higher = more active demand
        posts.sort(key=lambda x: x.get("score", 0) + x.get("comments", 0), reverse=True)
        return posts[:max_results]

    def search_reddit(self, query: str, max_results: int = 5) -> list[dict]:
        """Search Reddit for buyer-intent leads. JSON API first, DDG fallback."""
        import time

        # Strategy 1: Reddit JSON API targeting hiring subreddits
        posts = self.search_reddit_json(query, max_results=max_results)
        if posts:
            return posts

        # Strategy 2: DuckDuckGo with buyer-intent search queries
        from archangel.agents.chat import WebSearch

        # Build multiple intent-targeted DDG queries
        ddg_queries = [
            f'"{query}" hiring OR "looking for" OR "need a developer" site:reddit.com',
            f'"{query}" (forhire OR freelance OR "[hiring]") site:reddit.com',
            f'"{query}" "budget" OR "paid" OR "will pay" site:reddit.com',
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
                    # Deduplicate
                    if any(p["url"] == url for p in posts):
                        continue
                    # For DDG results: require buyer intent in TITLE (body is unreliable — contains sidebar/comment text)
                    if not self._has_buyer_intent(title, ""):
                        continue
                    # Skip supply-side (people offering, not hiring)
                    if self._is_supply_side(title):
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
                        "timestamp": time.time(),
                    })
            except Exception as exc:
                logger.warning("DDG lead search failed: %s", exc)

        return posts[:max_results]

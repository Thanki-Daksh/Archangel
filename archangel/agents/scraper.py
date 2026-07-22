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

    def search_reddit_json(self, query: str, subreddits: list[str] = None, max_results: int = 10) -> list[dict]:
        """Search Reddit via their public JSON API using requests (avoids Scrapling 403)."""
        import time

        if subreddits is None:
            subreddits = [
                "Discord_Bots", "discordapp", "automation", "SelfHosted",
                "smallbusiness", "entrepreneur", "Python", "nocode",
                "ChatGPT", "artificial", "MachineLearning", "webdev",
                "Entrepreneur", "sidehustle", "SaaS", "microsaas",
            ]

        import requests as req_lib

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

        posts = []

        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={query}&sort=new&limit=5&restrict_sr=1"
                resp = req_lib.get(url, headers=headers, timeout=15)
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

                    if not title and not selftext:
                        continue
                    if created_utc < time.time() - 5 * 86400:
                        continue

                    posts.append({
                        "title": title,
                        "content": selftext[:2000] if selftext else "",
                        "author": author,
                        "url": f"https://reddit.com{permalink}",
                        "subreddit": sub,
                        "score": score,
                        "comments": num_comments,
                        "timestamp": created_utc,
                    })

                time.sleep(1)  # Rate limit

            except Exception as e:
                logger.warning("Reddit JSON search failed for r/%s: %s", sub, e)
                continue

        posts.sort(key=lambda x: x.get("score", 0) + x.get("comments", 0), reverse=True)
        return posts[:max_results]

    def search_reddit(self, query: str, max_results: int = 5) -> list[dict]:
        """Search Reddit via JSON API, fallback to DuckDuckGo."""
        import time

        # Strategy 1: Reddit JSON API
        posts = self.search_reddit_json(query, max_results=max_results)
        if posts:
            return posts

        # Strategy 2: DuckDuckGo search fallback (extract title, url, body directly)
        from archangel.agents.chat import WebSearch
        try:
            ddg_text = WebSearch().search(f'{query} site:reddit.com', max_results=max_results)
            if ddg_text and "No results found" not in ddg_text:
                blocks = ddg_text.split("\n\n")
                for block in blocks:
                    lines = block.strip().splitlines()
                    if not lines:
                        continue
                    title = lines[0].lstrip("0123456789. ")
                    url = ""
                    body = ""
                    for l in lines[1:]:
                        if l.strip().startswith("URL:"):
                            url = l.replace("URL:", "").strip()
                        else:
                            body += " " + l.strip()
                    if url and "reddit.com" in url:
                        sub = "reddit"
                        if "/r/" in url:
                            sub = url.split("/r/")[1].split("/")[0]
                        posts.append({
                            "title": title or "Reddit Post",
                            "content": body.strip(),
                            "author": "reddit_community",
                            "url": url,
                            "subreddit": sub,
                            "score": 10,
                            "comments": 2,
                            "timestamp": time.time(),
                        })
        except Exception as exc:
            logger.warning("DDG Reddit fallback failed: %s", exc)

        return posts[:max_results]

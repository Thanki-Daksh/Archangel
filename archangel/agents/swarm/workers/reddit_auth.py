"""RedditTokenPool — Manages multi-key OAuth2 authentication, token refresh, and round-robin distribution for Reddit API requests."""

import os
import time
import base64
import logging
import threading
import json
import urllib.request
import urllib.parse
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class RedditTokenPool:
    """Thread-safe pool managing multiple Reddit API OAuth2 Client Credentials for high-throughput zero-block polling."""

    _instance: Optional["RedditTokenPool"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.credentials: List[Tuple[str, str]] = []
        self._tokens: Dict[int, Dict[str, str | float]] = {}  # index -> {"token": str, "expires_at": float}
        self._index_counter = 0
        self._pool_lock = threading.Lock()
        self.reload_credentials()

    @classmethod
    def get_instance(cls) -> "RedditTokenPool":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def reload_credentials(self) -> None:
        """Parses credentials from environment variables: REDDIT_CLIENT_IDS / REDDIT_CLIENT_SECRETS or REDDIT_KEYS."""
        with self._pool_lock:
            creds: List[Tuple[str, str]] = []
            
            # Format 1: REDDIT_KEYS="id1:sec1, id2:sec2"
            raw_keys = os.getenv("REDDIT_KEYS", "").strip()
            if raw_keys:
                for pair in raw_keys.split(","):
                    if ":" in pair:
                        cid, sec = pair.split(":", 1)
                        if cid.strip() and sec.strip():
                            creds.append((cid.strip(), sec.strip()))

            # Format 2: REDDIT_CLIENT_IDS="id1, id2" & REDDIT_CLIENT_SECRETS="sec1, sec2"
            if not creds:
                ids_str = os.getenv("REDDIT_CLIENT_IDS", "").strip()
                secs_str = os.getenv("REDDIT_CLIENT_SECRETS", "").strip()
                if not ids_str and os.getenv("REDDIT_CLIENT_ID"):
                    ids_str = os.getenv("REDDIT_CLIENT_ID", "").strip()
                if not secs_str and os.getenv("REDDIT_CLIENT_SECRET"):
                    secs_str = os.getenv("REDDIT_CLIENT_SECRET", "").strip()

                if ids_str and secs_str:
                    ids_list = [x.strip() for x in ids_str.split(",") if x.strip()]
                    secs_list = [x.strip() for x in secs_str.split(",") if x.strip()]
                    for cid, sec in zip(ids_list, secs_list):
                        creds.append((cid, sec))

            self.credentials = creds
            if creds:
                logger.info("RedditTokenPool initialized with %d active API key pair(s)", len(creds))

    def _fetch_bearer_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """Obtains an OAuth2 bearer token from Reddit's auth endpoint."""
        url = "https://www.reddit.com/api/v1/access_token"
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")

        auth_str = f"{client_id}:{client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "User-Agent": "ArchangelSwarm/1.0.0 (by /u/archangel_lead_bot)",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    return body.get("access_token")
        except Exception as e:
            logger.debug("Failed fetching Reddit OAuth token for client_id %s: %s", client_id[:6], e)
        return None

    def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Returns a valid round-robin Authorization header dict if keys exist."""
        with self._pool_lock:
            if not self.credentials:
                return None

            idx = self._index_counter % len(self.credentials)
            self._index_counter += 1

            cid, sec = self.credentials[idx]
            now = time.monotonic()

            cached = self._tokens.get(idx)
            if cached and float(cached.get("expires_at", 0)) > now:
                token = str(cached.get("token"))
                return {"Authorization": f"bearer {token}"}

            # Token expired or missing -> fetch fresh bearer token
            token = self._fetch_bearer_token(cid, sec)
            if token:
                self._tokens[idx] = {
                    "token": token,
                    "expires_at": now + 3300.0,  # 55 minutes TTL
                }
                return {"Authorization": f"bearer {token}"}

            return None

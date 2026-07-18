"""Data persistence — stores raw posts, analysis, scores, and runtime history."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from archangel.models import RawPost, LeadAnalysis, LeadScore

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


class StorageBackend:
    """Persistent storage interface (SQLite)."""

    _instance: "StorageBackend | None" = None

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = DATA_DIR / "archangel.db"
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.debug("StorageBackend initialized (%s)", db_path)

    @classmethod
    def get_instance(cls) -> "StorageBackend":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _create_tables(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS raw_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                channel TEXT,
                author TEXT,
                content TEXT,
                timestamp REAL,
                url TEXT UNIQUE,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lead_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_post_id INTEGER,
                is_lead BOOLEAN,
                confidence REAL,
                estimated_budget TEXT,
                urgency TEXT,
                category TEXT,
                tags TEXT,
                recommended_action TEXT,
                reasoning TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raw_post_id) REFERENCES raw_posts(id)
            );

            CREATE TABLE IF NOT EXISTS lead_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                score REAL,
                confidence_score REAL,
                budget_score REAL,
                urgency_score REAL,
                keyword_score REAL,
                recency_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (analysis_id) REFERENCES lead_analyses(id)
            );
        """)
        self._conn.commit()

    def store_raw_post(self, post: RawPost) -> int:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO raw_posts
                   (source, channel, author, content, timestamp, url, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    post.source,
                    post.channel,
                    post.author,
                    post.content,
                    post.timestamp,
                    post.url,
                    json.dumps(post.metadata),
                ),
            )
            self._conn.commit()
            if cursor.lastrowid and cursor.lastrowid > 0:
                return cursor.lastrowid
            row = cursor.execute(
                "SELECT id FROM raw_posts WHERE url = ?", (post.url,)
            ).fetchone()
            return row["id"] if row else 0
        except Exception as exc:
            logger.error("store_raw_post failed: %s", exc)
            return 0

    def store_analysis(self, analysis: LeadAnalysis) -> int:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO lead_analyses
                   (raw_post_id, is_lead, confidence, estimated_budget, urgency,
                    category, tags, recommended_action, reasoning)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    analysis.raw_post_id,
                    int(analysis.is_lead),
                    analysis.confidence,
                    analysis.estimated_budget,
                    analysis.urgency,
                    analysis.category,
                    json.dumps(analysis.tags),
                    analysis.recommended_action,
                    analysis.reasoning,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid or 0
        except Exception as exc:
            logger.error("store_analysis failed: %s", exc)
            return 0

    def store_score(self, score: LeadScore) -> int:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO lead_scores
                   (analysis_id, score, confidence_score, budget_score,
                    urgency_score, keyword_score, recency_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    score.analysis_id,
                    score.score,
                    score.confidence_score,
                    score.budget_score,
                    score.urgency_score,
                    score.keyword_score,
                    score.recency_score,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid or 0
        except Exception as exc:
            logger.error("store_score failed: %s", exc)
            return 0

    def get_leads(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """SELECT
                    r.id, r.source, r.channel, r.author, r.content,
                    r.timestamp, r.url, r.created_at as post_created_at,
                    a.is_lead, a.confidence, a.estimated_budget,
                    a.urgency, a.category, a.tags, a.recommended_action,
                    a.reasoning,
                    s.score, s.confidence_score, s.budget_score,
                    s.urgency_score, s.keyword_score, s.recency_score
                   FROM raw_posts r
                   LEFT JOIN lead_analyses a ON r.id = a.raw_post_id
                   LEFT JOIN lead_scores s ON a.id = s.analysis_id
                   ORDER BY s.score DESC NULLS LAST, r.created_at DESC
                   LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("get_leads failed: %s", exc)
            return []

    def get_lead_count(self) -> int:
        cursor = self._conn.cursor()
        try:
            row = cursor.execute(
                "SELECT COUNT(*) as cnt FROM lead_analyses WHERE is_lead = 1"
            ).fetchone()
            return row["cnt"] if row else 0
        except Exception as exc:
            logger.error("get_lead_count failed: %s", exc)
            return 0

    def lead_exists(self, url: str) -> bool:
        cursor = self._conn.cursor()
        try:
            row = cursor.execute(
                "SELECT 1 FROM raw_posts WHERE url = ?", (url,)
            ).fetchone()
            return row is not None
        except Exception as exc:
            logger.error("lead_exists failed: %s", exc)
            return False

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception as exc:
            logger.error("close failed: %s", exc)

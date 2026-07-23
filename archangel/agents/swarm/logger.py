"""SwarmLogger — Lead formatting and batch file writing for the swarm pipeline.

This module is now a pure file-formatting utility. It does NOT perform SQLite
writes or EventBus publishing — those responsibilities belong to the
StoragePipeline (pipeline.py).
"""

import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from archangel.models import RawPost

import html
import re

logger = logging.getLogger(__name__)


def clean_html_text(text: str) -> str:
    """Converts HTML markup into clean, readable plain text."""
    if not text or "<" not in text:
        return text or ""
    # Unescape HTML entities (&nbsp;, &amp;, &lt;, etc.)
    cleaned = html.unescape(text)
    # Replace block break tags with newlines
    cleaned = re.sub(r"<(?:p|div|br|li|h[1-6]|tr)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(?:p|div|li|h[1-6]|tr)>", "\n", cleaned, flags=re.IGNORECASE)
    # Strip remaining tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Normalize excessive newlines and whitespace
    lines = [line.strip() for line in cleaned.splitlines()]
    non_empty = [line for line in lines if line]
    return "\n".join(non_empty)


def format_lead_block(post: RawPost, evaluation: Dict[str, Any], raw_post_id: int) -> str:
    """Formats a lead into Archangel's standard structured text template."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    keywords = evaluation.get("matched_keywords", [])
    keywords_formatted = "\n".join([f"- {kw}" for kw in keywords]) if keywords else "- None"

    confidence = evaluation.get("confidence", 0.0)
    score = evaluation.get("score", confidence * 100 if confidence <= 1.0 else confidence)
    priority = evaluation.get("priority", "HIGH" if confidence >= 0.75 else "MEDIUM" if confidence >= 0.5 else "LOW")

    raw_content = clean_html_text(post.content or "")

    template = f"""==============================
=== LEAD #{raw_post_id:05d} ===
==============================

[IDENTITY]
Lead ID: #{raw_post_id:05d}
Generated At: {now_str}

[CONTACT]
Name: {evaluation.get("author_name", post.author or "N/A")}
Username: {post.author or "N/A"}
Company: {evaluation.get("company", "N/A")}
Role: {evaluation.get("role", "N/A")}

[SOURCE]
Platform: {post.source or "N/A"}
Post Type: {evaluation.get("post_type", "Public Job / Lead Post")}
Post URL: {post.url or "N/A"}
Channel/Subreddit: {post.channel or "N/A"}
Author Profile: {evaluation.get("author_profile", "N/A")}

[RAW DATA]
Raw Message:
\"\"\"
{raw_content}
\"\"\"

[EXTRACTED SIGNALS]
Keywords Found:
{keywords_formatted}

Problem Detected: {evaluation.get("problem_detected", "Need specialized talent / implementation")}
Service Needed: {evaluation.get("service_needed", "Software Engineering / Development")}

[BUSINESS INTELLIGENCE]
Estimated Budget: {evaluation.get("estimated_budget", "Unspecified")}
Budget Confidence: {evaluation.get("budget_confidence", "Medium")}
Currency: {evaluation.get("currency", "USD")}

Company Size: {evaluation.get("company_size", "N/A")}
Industry: {evaluation.get("industry", "Technology")}

[SCORING]
Lead Score: {score:.1f}
Priority: {priority}
Confidence: {confidence:.2f}

Score Breakdown:
- Keyword Match: {evaluation.get("keyword_score", f"{confidence*40:.1f}/40")}
- Budget Match: {evaluation.get("budget_score", "15.0/20")}
- Urgency: {evaluation.get("urgency_score", "15.0/20")}
- Relevance: {evaluation.get("relevance_score", "15.0/20")}

[ARCHANGEL ANALYSIS]
Why This Is A Lead: {evaluation.get("reasoning", "Matched search criteria and skill requirements.")}
Recommended Action: {evaluation.get("recommended_action", "Reach out directly via platform contact link or URL.")}

[STATUS]
State: {evaluation.get("state", "Discovered")}
Assigned Agent: {evaluation.get("assigned_agent", "SwarmWorker")}
Last Updated: {now_str}

==============================
END LEAD #{raw_post_id:05d}
==============================
"""
    return template


class SwarmFileWriter:
    """Handles buffered file output for leads. Used by BatchWriter."""

    def __init__(self, output_path: Optional[Path] = None) -> None:
        self.output_path = output_path or Path("data/swarm_leads.log")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.output_path.exists():
            self.output_path.touch()
        self._file_handle = None

    def _get_file_handle(self):
        if self._file_handle is None or self._file_handle.closed:
            self._file_handle = self.output_path.open(
                "a", encoding="utf-8", buffering=1
            )
        return self._file_handle

    def write_batch(self, blocks: List[str]) -> None:
        """Write multiple formatted lead blocks in a single file operation."""
        if not blocks:
            return
        f = self._get_file_handle()
        f.write("\n\n".join(blocks))
        f.write("\n\n")
        f.flush()

    def close(self) -> None:
        """Close the file stream gracefully."""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()

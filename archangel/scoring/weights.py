"""Recency Decay & Source Quality Weighting Matrix for Archangel V1.5."""

import time
from typing import Tuple, Dict, Any


def calculate_recency_decay(timestamp: float) -> Tuple[float, str]:
    """Calculates recency decay multiplier and human-readable explanation."""
    if not timestamp or timestamp <= 0:
        return 1.0, "Fresh post (Timestamp unstated)"

    now = time.time()
    age_seconds = now - timestamp
    age_days = age_seconds / 86400.0

    if age_days < 1.0:
        return 1.00, "Fresh post (<24h old) [100%]"
    elif age_days <= 3.0:
        return 0.90, "Recent post (1-3 days old) [90%]"
    elif age_days <= 7.0:
        return 0.75, "Aging post (3-7 days old) [75%]"
    elif age_days <= 30.0:
        return 0.40, "Stale post (7-30 days old) [40%]"
    else:
        return 0.10, "Expired post (>30 days old) [10%]"


def get_source_quality_weight(source: str, channel: str = "") -> Tuple[float, str]:
    """Calculates platform authority score (35 to 100) and human explanation."""
    src_clean = (source or "").lower().strip()
    chn_clean = (channel or "").lower().strip()
    combined = f"{src_clean} {chn_clean}"

    if "rfp" in combined or "gov" in combined:
        return 100.0, "High-Trust Government RFP Source (100/100)"
    elif "ycombinator" in combined or "hackernews" in combined or "hn" in combined:
        return 90.0, "Y Combinator Network (90/100)"
    elif "producthunt" in combined:
        return 75.0, "Product Hunt Platform (75/100)"
    elif "reddit" in combined:
        return 60.0, "Reddit Community (60/100)"
    elif "twitter" in combined or "x" in combined:
        return 55.0, "X / Twitter Social (55/100)"
    else:
        return 35.0, "Generic Web / RSS Feed (35/100)"

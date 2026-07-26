"""Fingerprinting, feature extraction, and similarity calculation for lead deduplication."""

import math
import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, Set

from archangel.models import RawPost

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
URL_REGEX = re.compile(r"https?://[^\s]+")


def normalize_text(text: str) -> str:
    """Clean text by removing emails, URLs, special characters, and normalizing whitespace."""
    if not text:
        return ""
    cleaned = EMAIL_REGEX.sub("", text)
    cleaned = URL_REGEX.sub("", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned).lower()
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_post_keys(post: RawPost) -> Dict[str, Set[str]]:
    """Extract deterministic identity keys (emails, URLs, content SHA256) from a RawPost."""
    content = post.content or ""
    emails = set(EMAIL_REGEX.findall(content))
    urls = set(URL_REGEX.findall(content))

    clean_str = normalize_text(content)
    content_hash = (
        hashlib.sha256(clean_str.encode("utf-8")).hexdigest()
        if clean_str
        else ""
    )

    return {
        "emails": emails,
        "urls": urls,
        "content_hash": {content_hash} if content_hash else set(),
    }


def compute_vector_similarity(text1: str, text2: str) -> float:
    """Computes TF-IDF bag-of-words Cosine Similarity ratio [0.0, 1.0]."""
    tokens1 = text1.split()
    tokens2 = text2.split()
    if not tokens1 or not tokens2:
        return 0.0

    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)

    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)

    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    return numerator / denominator if denominator else 0.0


def compute_post_similarity(post1: RawPost, post2: RawPost) -> float:
    """Compute combined Jaccard, Sequence, and Vector Cosine similarity ratio [0.0, 1.0]."""
    keys1 = extract_post_keys(post1)
    keys2 = extract_post_keys(post2)

    # Shortcut: Exact key matches (email or URL match)
    if (keys1["emails"] and keys1["emails"] & keys2["emails"]) or (
        keys1["urls"] and keys1["urls"] & keys2["urls"]
    ):
        return 1.0

    t1 = normalize_text(post1.content or "")
    t2 = normalize_text(post2.content or "")

    if not t1 or not t2:
        return 0.0

    if t1 == t2:
        return 1.0

    # Sequence similarity
    seq_sim = SequenceMatcher(None, t1, t2).ratio()

    # Token Jaccard similarity
    tokens1 = set(t1.split())
    tokens2 = set(t2.split())
    union = tokens1 | tokens2
    jaccard_sim = len(tokens1 & tokens2) / len(union) if union else 0.0

    # Vector Cosine similarity
    vec_sim = compute_vector_similarity(t1, t2)

    # Weighted hybrid combination: 40% sequence, 30% Jaccard, 30% Vector Cosine
    return round(0.4 * seq_sim + 0.3 * jaccard_sim + 0.3 * vec_sim, 4)

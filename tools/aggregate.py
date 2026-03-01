#!/usr/bin/env python3
"""
Aggregator — merges all scraper outputs into a single feed.
Reads .tmp/bens_bites.json and .tmp/the_rundown.json
Output: .tmp/feed.json
"""

import json
import os
import sys
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp")
SOURCE_FILES = [
    os.path.join(TMP_DIR, "bens_bites.json"),
    os.path.join(TMP_DIR, "the_rundown.json"),
]
OUTPUT_PATH = os.path.join(TMP_DIR, "feed.json")


def load_source(filepath):
    """Load a JSON source file. Returns list of articles or empty list."""
    if not os.path.exists(filepath):
        print(f"[WARN] Source file not found: {filepath}", file=sys.stderr)
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                print(f"[INFO] Loaded {len(data)} articles from {os.path.basename(filepath)}")
                return data
            else:
                print(f"[WARN] Unexpected format in {filepath}", file=sys.stderr)
                return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to read {filepath}: {e}", file=sys.stderr)
        return []


def sort_key(article):
    """Sort key for articles — newest first. Unknown dates go last."""
    date_str = article.get("date")
    if not date_str:
        return ""
    return date_str


def main():
    """Main entry point."""
    os.makedirs(TMP_DIR, exist_ok=True)

    # Load all sources
    all_articles = []
    for filepath in SOURCE_FILES:
        all_articles.extend(load_source(filepath))

    # Deduplicate by ID
    seen_ids = set()
    unique_articles = []
    for article in all_articles:
        aid = article.get("id")
        if aid and aid not in seen_ids:
            seen_ids.add(aid)
            unique_articles.append(article)

    # Sort by date (newest first)
    unique_articles.sort(key=sort_key, reverse=True)

    # Add aggregation metadata
    feed = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalArticles": len(unique_articles),
        "sources": {
            "bens_bites": len([a for a in unique_articles if a.get("source") == "bens_bites"]),
            "the_rundown": len([a for a in unique_articles if a.get("source") == "the_rundown"]),
        },
        "articles": unique_articles
    }

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)

    print(f"[OK] Aggregated {len(unique_articles)} unique articles → {OUTPUT_PATH}")
    print(f"     Ben's Bites: {feed['sources']['bens_bites']}")
    print(f"     The Rundown: {feed['sources']['the_rundown']}")


if __name__ == "__main__":
    main()

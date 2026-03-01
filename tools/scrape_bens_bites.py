#!/usr/bin/env python3
"""
Scraper for Ben's Bites (Substack) newsletter.
Fetches the archive page, parses article links, and extracts article details.
Output: .tmp/bens_bites.json
"""

import json
import hashlib
import os
import sys
import time
import re
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

# ── Config ──────────────────────────────────────────────────────────────────
ARCHIVE_URL = "https://bensbites.com/archive"
BASE_URL = "https://www.bensbites.com"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp", "bens_bites.json")
USER_AGENT = "AINewsDashboard/1.0 (personal project)"
REQUEST_DELAY = 1.0  # seconds between requests
SOURCE_NAME = "bens_bites"


# ── HTML Parsing Helpers ────────────────────────────────────────────────────
class ArchiveParser(HTMLParser):
    """Parse the Ben's Bites archive page to extract article links."""

    def __init__(self):
        super().__init__()
        self.articles = []  # list of {"url": ..., "title": ...}
        self._in_link = False
        self._current_url = None
        self._current_title = ""
        self._seen_urls = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            # Match article links like /p/slug or full URLs
            if "/p/" in href and "bensbites" in (href if href.startswith("http") else ARCHIVE_URL):
                if href.startswith("/"):
                    href = BASE_URL + href
                elif not href.startswith("http"):
                    href = BASE_URL + "/" + href
                self._in_link = True
                self._current_url = href
                self._current_title = ""

    def handle_data(self, data):
        if self._in_link:
            self._current_title += data.strip()

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            self._in_link = False
            if self._current_url and self._current_title and self._current_url not in self._seen_urls:
                self._seen_urls.add(self._current_url)
                self.articles.append({
                    "url": self._current_url,
                    "title": self._current_title
                })
            self._current_url = None
            self._current_title = ""


class ArticleParser(HTMLParser):
    """Parse an individual Ben's Bites article page to extract metadata."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.subtitle = ""
        self.author = "Ben Tossell"
        self.date = None
        self.body_text = ""
        self.image_url = None

        self._in_h1 = False
        self._in_h3 = False
        self._in_article = False
        self._in_time = False
        self._in_meta_author = False
        self._found_title = False
        self._found_subtitle = False
        self._tag_stack = []
        self._collecting_body = False
        self._body_depth = 0
        self._in_p = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._tag_stack.append(tag)

        if tag == "h1" and not self._found_title:
            self._in_h1 = True

        if tag == "h3" and self._found_title and not self._found_subtitle:
            self._in_h3 = True

        if tag == "time":
            self._in_time = True
            dt = attrs_dict.get("datetime", "")
            if dt:
                self.date = dt

        if tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")

            if name == "author" or prop == "article:author":
                self.author = content
            if (prop == "og:image" or name == "twitter:image") and not self.image_url:
                self.image_url = content
            if prop == "article:published_time" and not self.date:
                self.date = content

        if tag == "article":
            self._in_article = True

        if self._in_article and tag == "p":
            self._in_p = True

    def handle_data(self, data):
        if self._in_h1:
            self.title += data.strip()
        if self._in_h3:
            self.subtitle += data.strip()
        if self._in_time and not self.date:
            cleaned = data.strip()
            if cleaned:
                self.date = cleaned
        if self._in_article and self._in_p and len(self.body_text) < 300:
            text = data.strip()
            if text:
                self.body_text += " " + text

    def handle_endtag(self, tag):
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._found_title = True
        if tag == "h3" and self._in_h3:
            self._in_h3 = False
            self._found_subtitle = True
        if tag == "time":
            self._in_time = False
        if tag == "article":
            self._in_article = False
        if tag == "p":
            self._in_p = False
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()


# ── Utility Functions ───────────────────────────────────────────────────────
def fetch_url(url):
    """Fetch a URL with polite headers. Returns HTML string or None."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError) as e:
        print(f"[ERROR] Failed to fetch {url}: {e}", file=sys.stderr)
        return None
    except (TimeoutError, OSError) as e:
        print(f"[ERROR] Timeout fetching {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching {url}: {e}", file=sys.stderr)
        return None


def make_id(url):
    """Generate a SHA-256 hash ID from a URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def parse_date(date_str):
    """Try to parse various date formats into ISO 8601."""
    if not date_str:
        return None

    # Already ISO format
    if "T" in date_str:
        return date_str

    # Try common formats
    formats = [
        "%b %d, %Y",      # "Feb 27, 2026"
        "%B %d, %Y",      # "February 27, 2026"
        "%Y-%m-%d",        # "2026-02-27"
        "%d %b %Y",        # "27 Feb 2026"
        "%d %B %Y",        # "27 February 2026"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            continue

    return None


def is_within_24h(date_str):
    """Check if a date string is within the last 24 hours."""
    if not date_str:
        return True  # Include articles with unknown dates

    try:
        # Parse ISO format
        if date_str.endswith("Z"):
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        elif "+" in date_str or (date_str.count("-") >= 3):
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return (now - dt) <= timedelta(hours=24)
    except (ValueError, TypeError):
        return True  # Include on parse failure


# ── Main Scraping Logic ────────────────────────────────────────────────────
def scrape_archive():
    """Fetch the archive page and return list of article stubs."""
    print(f"[INFO] Fetching archive: {ARCHIVE_URL}")
    html = fetch_url(ARCHIVE_URL)
    if not html:
        return []

    parser = ArchiveParser()
    parser.feed(html)

    print(f"[INFO] Found {len(parser.articles)} article links on archive page")
    return parser.articles


def extract_jsonld_date(html):
    """Extract datePublished from JSON-LD structured data in HTML."""
    match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    if match:
        return match.group(1)
    return None


def extract_og_image(html):
    """Extract og:image from meta tags via regex."""
    match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\'>]+)["\']', html, re.I)
    if not match:
        match = re.search(r'<meta[^>]*content=["\']([^"\'>]+)["\'][^>]*property=["\']og:image["\']', html, re.I)
    return match.group(1) if match else None


def scrape_article(url, fallback_title=""):
    """Fetch and parse a single article page. Returns article dict or None."""
    html = fetch_url(url)
    if not html:
        return None

    # Use HTML parser for title, subtitle, body text
    parser = ArticleParser()
    parser.feed(html)

    title = parser.title or fallback_title
    if not title:
        return None

    # Extract date from JSON-LD (most reliable for Substack)
    date_raw = extract_jsonld_date(html) or parser.date
    date_iso = parse_date(date_raw)

    # Extract image from og:image meta tag (more reliable than parser)
    image_url = extract_og_image(html) or parser.image_url

    summary = parser.body_text.strip()[:200]

    return {
        "id": make_id(url),
        "source": SOURCE_NAME,
        "title": title,
        "subtitle": parser.subtitle or None,
        "author": parser.author,
        "date": date_iso,
        "url": url,
        "summary": summary if summary else None,
        "imageUrl": image_url,
        "scrapedAt": datetime.now(timezone.utc).isoformat()
    }


def main():
    """Main entry point."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Step 1: Get article listing from archive
    article_stubs = scrape_archive()

    if not article_stubs:
        print("[WARN] No articles found on archive page", file=sys.stderr)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    # Step 2: Scrape individual articles (limit to first 10 to be polite)
    articles = []
    for i, stub in enumerate(article_stubs[:10]):
        print(f"[INFO] Scraping article {i+1}/{min(len(article_stubs), 10)}: {stub['title'][:50]}...")
        article = scrape_article(stub["url"], fallback_title=stub["title"])

        if article:
            articles.append(article)

        # Rate limiting
        if i < len(article_stubs) - 1:
            time.sleep(REQUEST_DELAY)

    # Step 3: Save output (all articles — filtering done by dashboard)
    print(f"[INFO] Scraped {len(articles)} articles total")

    # Step 4: Save output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(articles)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

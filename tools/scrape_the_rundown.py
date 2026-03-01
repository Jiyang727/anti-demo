#!/usr/bin/env python3
"""
Scraper for The AI Rundown newsletter.
Fetches the homepage, parses article links, and extracts article details.
Output: .tmp/the_rundown.json
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
HOMEPAGE_URL = "https://therundown.ai"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp", "the_rundown.json")
USER_AGENT = "AINewsDashboard/1.0 (personal project)"
REQUEST_DELAY = 1.0  # seconds between requests
SOURCE_NAME = "the_rundown"


# ── HTML Parsing Helpers ────────────────────────────────────────────────────
class HomepageParser(HTMLParser):
    """Parse The AI Rundown homepage to extract article links."""

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
            # Match article links like /p/slug
            if "/p/" in href and ("therundown.ai" in href or href.startswith("/p/")):
                if href.startswith("/"):
                    href = HOMEPAGE_URL + href
                self._in_link = True
                self._current_url = href
                self._current_title = ""

    def handle_data(self, data):
        if self._in_link:
            text = data.strip()
            if text and len(text) > 3:
                self._current_title += (" " + text) if self._current_title else text

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            self._in_link = False
            title = self._current_title.strip()
            url = self._current_url

            if url and title and url not in self._seen_urls:
                # Clean up title — take the first meaningful line
                lines = [l.strip() for l in title.split("\n") if l.strip()]
                clean_title = lines[0] if lines else title

                # Skip very short or navigation-like titles
                if len(clean_title) > 10:
                    self._seen_urls.add(url)
                    self.articles.append({
                        "url": url,
                        "title": clean_title
                    })

            self._current_url = None
            self._current_title = ""


class ArticleParser(HTMLParser):
    """Parse an individual The AI Rundown article page."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.subtitle = ""
        self.authors = []
        self.date = None
        self.body_text = ""
        self.image_url = None

        self._in_h1 = False
        self._found_title = False
        self._in_article = False
        self._in_p = False
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._tag_stack.append(tag)

        if tag == "h1" and not self._found_title:
            self._in_h1 = True

        if tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")

            if name == "author":
                self.authors.append(content)
            if prop == "og:image" and not self.image_url:
                self.image_url = content
            if prop == "article:published_time" and not self.date:
                self.date = content
            if prop == "og:description" and not self.subtitle:
                self.subtitle = content

        if tag == "time":
            dt = attrs_dict.get("datetime", "")
            if dt and not self.date:
                self.date = dt

        if tag == "article" or attrs_dict.get("role") == "article":
            self._in_article = True

        if tag == "p":
            self._in_p = True

    def handle_data(self, data):
        if self._in_h1:
            self.title += data.strip()

        if self._in_p and len(self.body_text) < 300:
            text = data.strip()
            if text and len(text) > 5:
                self.body_text += " " + text

        # Try to extract date from text patterns like "Feb 27, 2026"
        if not self.date:
            date_match = re.search(
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
                data
            )
            if date_match:
                self.date = date_match.group(0)

    def handle_endtag(self, tag):
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._found_title = True
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
        "%b %d %Y",        # "Feb 27 2026"
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
        if date_str.endswith("Z"):
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        elif "+" in date_str or (date_str.count("-") >= 3):
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return (now - dt) <= timedelta(hours=24)
    except (ValueError, TypeError):
        return True


# ── Main Scraping Logic ────────────────────────────────────────────────────
def scrape_homepage():
    """Fetch the homepage and return list of article stubs."""
    print(f"[INFO] Fetching homepage: {HOMEPAGE_URL}")
    html = fetch_url(HOMEPAGE_URL)
    if not html:
        return []

    parser = HomepageParser()
    parser.feed(html)

    print(f"[INFO] Found {len(parser.articles)} article links on homepage")
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

    # Extract date from JSON-LD (most reliable)
    date_raw = extract_jsonld_date(html) or parser.date
    date_iso = parse_date(date_raw)

    # Extract image from og:image meta tag (more reliable than parser)
    image_url = extract_og_image(html) or parser.image_url

    author = ", ".join(parser.authors) if parser.authors else "The Rundown Team"
    summary = parser.body_text.strip()[:200]

    return {
        "id": make_id(url),
        "source": SOURCE_NAME,
        "title": title,
        "subtitle": parser.subtitle or None,
        "author": author,
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

    # Step 1: Get article listing from homepage
    article_stubs = scrape_homepage()

    if not article_stubs:
        print("[WARN] No articles found on homepage", file=sys.stderr)
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

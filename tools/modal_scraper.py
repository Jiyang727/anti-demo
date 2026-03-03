"""
Modal Scheduled Scraper — AI Pulse
Runs both scrapers + aggregator every 24 hours on Modal cloud.
Output: uploads feed.json to a Modal Volume for retrieval.

Deploy:  modal deploy tools/modal_scraper.py
Test:    modal run tools/modal_scraper.py
"""

import modal

# ── Modal App ─────────────────────────────────────────────────────────────

app = modal.App("ai-pulse-scraper")

# Volume to persist scraped data between runs
volume = modal.Volume.from_name("ai-pulse-data", create_if_missing=True)

# Base image with Python 3.12 (scrapers use only stdlib)
image = modal.Image.debian_slim(python_version="3.12")
image_with_fastapi = image.pip_install("fastapi[standard]")

VOLUME_PATH = "/data"


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    timeout=300,
    schedule=modal.Cron("0 8 * * *"),  # Every day at 08:00 UTC
)
def scrape_and_aggregate():
    """Run both scrapers and aggregate results. Scheduled daily."""
    import json
    import hashlib
    import os
    import sys
    import time
    import re
    from datetime import datetime, timezone
    from html.parser import HTMLParser
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    TMP_DIR = os.path.join(VOLUME_PATH, "tmp")
    os.makedirs(TMP_DIR, exist_ok=True)

    USER_AGENT = "AI-Pulse-Bot/1.0 (news aggregator; polite scraping)"
    REQUEST_DELAY = 1  # seconds between requests

    # ════════════════════════════════════════════════════════════════════
    # Shared helpers
    # ════════════════════════════════════════════════════════════════════

    def fetch_url(url, timeout=30):
        """Fetch a URL with polite headers."""
        try:
            req = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, Exception) as e:
            print(f"[WARN] fetch_url failed for {url}: {e}", file=sys.stderr)
            return None

    def make_id(url):
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def parse_date(date_str):
        if not date_str:
            return None
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
            "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d",
            "%d %b %Y", "%d %B %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).isoformat()
            except ValueError:
                continue
        return None

    def extract_jsonld_date(html):
        match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
        return parse_date(match.group(1)) if match else None

    def extract_og_image(html):
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not match:
            match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        return match.group(1) if match else None

    # ════════════════════════════════════════════════════════════════════
    # Ben's Bites Scraper
    # ════════════════════════════════════════════════════════════════════

    class BensArchiveParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.articles = []
            self._in_link = False
            self._current_url = None
            self._current_title = ""
            self._seen_urls = set()

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                attrs_dict = dict(attrs)
                href = attrs_dict.get("href", "")
                if "/p/" in href and "bensbites.com" in href:
                    self._in_link = True
                    self._current_url = href.split("?")[0]
                    self._current_title = ""

        def handle_data(self, data):
            if self._in_link:
                self._current_title += data

        def handle_endtag(self, tag):
            if tag == "a" and self._in_link:
                self._in_link = False
                url = self._current_url
                title = self._current_title.strip()
                if url and title and url not in self._seen_urls:
                    self._seen_urls.add(url)
                    self.articles.append({"url": url, "title": title})

    class BensArticleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title = ""
            self.subtitle = ""
            self.author = "Ben Tossell"
            self.summary_parts = []
            self._in_h1 = False
            self._found_title = False
            self._in_subtitle = False
            self._found_subtitle = False
            self._in_p = False
            self._tag_stack = []
            self._collecting_body = False
            self._body_depth = 0

        def handle_starttag(self, tag, attrs):
            self._tag_stack.append(tag)
            attrs_dict = dict(attrs)
            cls = attrs_dict.get("class", "")
            if tag == "h1" and not self._found_title:
                self._in_h1 = True
            elif tag == "h3" and "subtitle" in cls and not self._found_subtitle:
                self._in_subtitle = True
            elif tag == "div" and "body" in cls and not self._collecting_body:
                self._collecting_body = True
                self._body_depth = len(self._tag_stack)
            elif tag == "p" and self._collecting_body:
                self._in_p = True

        def handle_data(self, data):
            text = data.strip()
            if not text:
                return
            if self._in_h1:
                self.title += text
            elif self._in_subtitle:
                self.subtitle += text
            elif self._in_p and self._collecting_body and len(" ".join(self.summary_parts)) < 200:
                self.summary_parts.append(text)

        def handle_endtag(self, tag):
            if self._tag_stack:
                self._tag_stack.pop()
            if tag == "h1" and self._in_h1:
                self._in_h1 = False
                self._found_title = True
            elif tag == "h3" and self._in_subtitle:
                self._in_subtitle = False
                self._found_subtitle = True
            elif tag == "p":
                self._in_p = False
            if self._collecting_body and len(self._tag_stack) < self._body_depth:
                self._collecting_body = False

    def scrape_bens_bites():
        print("[INFO] Scraping Ben's Bites archive...")
        html = fetch_url("https://bensbites.com/archive")
        if not html:
            print("[ERROR] Failed to fetch Ben's Bites archive.", file=sys.stderr)
            return []

        parser = BensArchiveParser()
        parser.feed(html)
        stubs = parser.articles[:15]
        print(f"[INFO] Found {len(stubs)} articles on archive page.")

        articles = []
        for stub in stubs:
            time.sleep(REQUEST_DELAY)
            html = fetch_url(stub["url"])
            if not html:
                continue
            try:
                ap = BensArticleParser()
                ap.feed(html)
                date_str = extract_jsonld_date(html)
                image_url = extract_og_image(html)
                article = {
                    "id": make_id(stub["url"]),
                    "source": "bens_bites",
                    "title": ap.title.strip() or stub.get("title", "Untitled"),
                    "subtitle": ap.subtitle.strip() or None,
                    "author": ap.author,
                    "date": date_str,
                    "url": stub["url"],
                    "summary": " ".join(ap.summary_parts)[:300] or None,
                    "imageUrl": image_url,
                    "scrapedAt": datetime.now(timezone.utc).isoformat(),
                }
                articles.append(article)
                print(f"  [OK] {article['title'][:60]}...")
            except Exception as e:
                print(f"  [WARN] Parse error for {stub['url']}: {e}", file=sys.stderr)
        return articles

    # ════════════════════════════════════════════════════════════════════
    # The AI Rundown Scraper
    # ════════════════════════════════════════════════════════════════════

    class RundownHomepageParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.articles = []
            self._in_link = False
            self._current_url = None
            self._current_title = ""
            self._seen_urls = set()

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                attrs_dict = dict(attrs)
                href = attrs_dict.get("href", "")
                if href.startswith("https://therundown.ai/p/"):
                    self._in_link = True
                    self._current_url = href.split("?")[0]
                    self._current_title = ""

        def handle_data(self, data):
            if self._in_link:
                self._current_title += data

        def handle_endtag(self, tag):
            if tag == "a" and self._in_link:
                self._in_link = False
                url = self._current_url
                title = self._current_title.strip()
                if url and title and len(title) > 5 and url not in self._seen_urls:
                    self._seen_urls.add(url)
                    self.articles.append({"url": url, "title": title})

    class RundownArticleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title = ""
            self.subtitle = ""
            self.authors = []
            self.date = None
            self.summary_parts = []
            self._in_h1 = False
            self._found_title = False
            self._in_article = False
            self._in_p = False
            self._tag_stack = []

        def handle_starttag(self, tag, attrs):
            self._tag_stack.append(tag)
            attrs_dict = dict(attrs)
            cls = attrs_dict.get("class", "")
            if tag == "h1" and not self._found_title:
                self._in_h1 = True
            elif tag == "article" or (tag == "div" and "body" in cls):
                self._in_article = True
            elif tag == "p" and self._in_article:
                self._in_p = True
            elif tag == "meta":
                name = attrs_dict.get("name", "")
                content = attrs_dict.get("content", "")
                if name == "author" and content:
                    self.authors.append(content)

        def handle_data(self, data):
            text = data.strip()
            if not text:
                return
            if self._in_h1:
                self.title += text
            elif self._in_p and self._in_article and len(" ".join(self.summary_parts)) < 200:
                self.summary_parts.append(text)

        def handle_endtag(self, tag):
            if self._tag_stack:
                self._tag_stack.pop()
            if tag == "h1" and self._in_h1:
                self._in_h1 = False
                self._found_title = True
            elif tag == "p":
                self._in_p = False

    def scrape_the_rundown():
        print("[INFO] Scraping The AI Rundown...")
        html = fetch_url("https://therundown.ai")
        if not html:
            print("[ERROR] Failed to fetch The AI Rundown.", file=sys.stderr)
            return []

        parser = RundownHomepageParser()
        parser.feed(html)
        stubs = parser.articles[:15]
        print(f"[INFO] Found {len(stubs)} articles on homepage.")

        articles = []
        for stub in stubs:
            time.sleep(REQUEST_DELAY)
            html = fetch_url(stub["url"])
            if not html:
                continue
            try:
                ap = RundownArticleParser()
                ap.feed(html)
                date_str = extract_jsonld_date(html)
                image_url = extract_og_image(html)
                article = {
                    "id": make_id(stub["url"]),
                    "source": "the_rundown",
                    "title": ap.title.strip() or stub.get("title", "Untitled"),
                    "subtitle": None,
                    "author": ", ".join(ap.authors) if ap.authors else "The Rundown AI",
                    "date": date_str,
                    "url": stub["url"],
                    "summary": " ".join(ap.summary_parts)[:300] or None,
                    "imageUrl": image_url,
                    "scrapedAt": datetime.now(timezone.utc).isoformat(),
                }
                articles.append(article)
                print(f"  [OK] {article['title'][:60]}...")
            except Exception as e:
                print(f"  [WARN] Parse error for {stub['url']}: {e}", file=sys.stderr)
        return articles

    # ════════════════════════════════════════════════════════════════════
    # Aggregator
    # ════════════════════════════════════════════════════════════════════

    def aggregate(all_articles):
        seen_ids = set()
        unique = []
        for a in all_articles:
            aid = a.get("id")
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                unique.append(a)
        unique.sort(key=lambda a: a.get("date") or "", reverse=True)
        return {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "totalArticles": len(unique),
            "sources": {
                "bens_bites": len([a for a in unique if a.get("source") == "bens_bites"]),
                "the_rundown": len([a for a in unique if a.get("source") == "the_rundown"]),
            },
            "articles": unique,
        }

    # ════════════════════════════════════════════════════════════════════
    # Main Pipeline
    # ════════════════════════════════════════════════════════════════════

    print("=" * 60)
    print(f"🚀 AI Pulse Scraper — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    bens = scrape_bens_bites()
    print(f"\n[INFO] Ben's Bites: {len(bens)} articles scraped")

    rundown = scrape_the_rundown()
    print(f"[INFO] The Rundown: {len(rundown)} articles scraped")

    feed = aggregate(bens + rundown)
    output_path = os.path.join(VOLUME_PATH, "feed.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)

    volume.commit()

    print(f"\n{'=' * 60}")
    print(f"✅ Done! {feed['totalArticles']} articles → {output_path}")
    print(f"   Ben's Bites: {feed['sources']['bens_bites']}")
    print(f"   The Rundown: {feed['sources']['the_rundown']}")
    print(f"{'=' * 60}")

    return feed


# ── Web endpoint to fetch the latest feed.json ─────────────────────────────

@app.function(image=image_with_fastapi, volumes={VOLUME_PATH: volume})
@modal.fastapi_endpoint(method="GET")
def get_feed():
    """HTTP endpoint to get the latest feed.json data."""
    import json
    import os

    feed_path = os.path.join(VOLUME_PATH, "feed.json")
    volume.reload()

    if not os.path.exists(feed_path):
        return {"error": "No feed data yet. Wait for first scrape or trigger manually."}

    with open(feed_path, "r") as f:
        return json.load(f)

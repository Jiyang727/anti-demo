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

# Base image with Python 3.12 + supabase client
image = modal.Image.debian_slim(python_version="3.12").pip_install("supabase")
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

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
    # The AI Rundown Scraper (regex-based — more reliable)
    # ════════════════════════════════════════════════════════════════════

    def scrape_the_rundown():
        """Use regex to extract article URLs from the Rundown homepage,
        then fetch each article page for title/date/image."""
        print("[INFO] Scraping The AI Rundown...")
        html = fetch_url("https://therundown.ai")
        if not html:
            print("[ERROR] Failed to fetch The AI Rundown.", file=sys.stderr)
            return []

        # Extract unique /p/ links via regex (they are relative on the site now)
        links = re.findall(r'href=["\']*([^"\' >]*\/p\/[a-z0-9\-]+)', html)
        seen = set()
        unique_links = []
        for link in links:
            clean = link.split("?")[0]
            if clean.startswith("/"):
                clean = "https://therundown.ai" + clean
                
            if clean not in seen:
                seen.add(clean)
                unique_links.append(clean)
        unique_links = unique_links[:15]
        print(f"[INFO] Found {len(unique_links)} unique article links.")

        class RundownArticleParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.title = ""
                self.authors = []
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

        articles = []
        for url in unique_links:
            time.sleep(REQUEST_DELAY)
            html = fetch_url(url)
            if not html:
                continue
            try:
                ap = RundownArticleParser()
                ap.feed(html)
                date_str = extract_jsonld_date(html)
                image_url = extract_og_image(html)
                title = ap.title.strip()
                if not title:
                    # Fallback: extract from og:title
                    og_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
                    title = og_match.group(1) if og_match else "Untitled"
                article = {
                    "id": make_id(url),
                    "source": "the_rundown",
                    "title": title,
                    "subtitle": None,
                    "author": ", ".join(ap.authors) if ap.authors else "The Rundown AI",
                    "date": date_str,
                    "url": url,
                    "summary": " ".join(ap.summary_parts)[:300] or None,
                    "imageUrl": image_url,
                    "scrapedAt": datetime.now(timezone.utc).isoformat(),
                }
                articles.append(article)
                print(f"  [OK] {article['title'][:60]}...")
            except Exception as e:
                print(f"  [WARN] Parse error for {url}: {e}", file=sys.stderr)
        return articles

    # ════════════════════════════════════════════════════════════════════
    # Reddit r/artificial Scraper
    # ════════════════════════════════════════════════════════════════════

    def scrape_reddit():
        """Fetch top posts from r/artificial using Reddit's public JSON API."""
        print("[INFO] Scraping Reddit r/artificial...")
        url = "https://www.reddit.com/r/artificial/hot.json?limit=20"
        try:
            # Reddit API requires a specific User-Agent format to avoid 403s from cloud IPs
            reddit_ua = "web:newsaggregator:v1.0 (by /u/LenoBot)"
            req = Request(url, headers={
                "User-Agent": reddit_ua,
                "Accept": "application/json",
            })
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[ERROR] Reddit fetch failed: {e}", file=sys.stderr)
            return []

        posts = data.get("data", {}).get("children", [])
        articles = []
        for post in posts:
            p = post.get("data", {})
            if p.get("stickied"):
                continue
            title = p.get("title", "").strip()
            if not title:
                continue

            # Build article URL
            permalink = p.get("permalink", "")
            post_url = p.get("url_overridden_by_dest") or f"https://reddit.com{permalink}"

            # Get thumbnail/preview image
            preview = p.get("preview", {})
            images = preview.get("images", [])
            image_url = None
            if images:
                image_url = images[0].get("source", {}).get("url", "").replace("&amp;", "&")
            elif p.get("thumbnail", "").startswith("http"):
                image_url = p["thumbnail"]

            # Date from created_utc
            created = p.get("created_utc")
            date_str = datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created else None

            article = {
                "id": make_id(f"reddit-{p.get('id', '')}"),
                "source": "reddit",
                "title": title,
                "subtitle": None,
                "author": f"u/{p.get('author', 'unknown')}",
                "date": date_str,
                "url": post_url,
                "summary": (p.get("selftext") or "")[:300] or None,
                "imageUrl": image_url,
                "scrapedAt": datetime.now(timezone.utc).isoformat(),
            }
            articles.append(article)

        print(f"[INFO] Reddit: {len(articles)} posts scraped")
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
                "reddit": len([a for a in unique if a.get("source") == "reddit"]),
            },
            "articles": unique,
        }

    # ════════════════════════════════════════════════════════════════════
    # Main Pipeline & Supabase Upsert
    # ════════════════════════════════════════════════════════════════════

    print("=" * 60)
    print(f"🚀 AI Pulse Scraper — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    bens = scrape_bens_bites()
    print(f"\n[INFO] Ben's Bites: {len(bens)} articles scraped")

    rundown = scrape_the_rundown()
    print(f"[INFO] The Rundown: {len(rundown)} articles scraped")

    reddit = scrape_reddit()
    print(f"[INFO] Reddit: {len(reddit)} articles scraped")

    feed = aggregate(bens + rundown + reddit)
    unique = feed["articles"]
    
    # Supabase Integration
    from supabase import create_client, Client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Upsert into articles table. Postgres `id` is primary key.
            # Format dates properly as ISO string for DB.
            db_records = []
            for a in unique:
                record = dict(a)
                # the DB schema uses 'image_url' and 'scraped_at' instead of CamelCase
                record['image_url'] = record.pop('imageUrl', None)
                record['scraped_at'] = record.pop('scrapedAt', None)
                db_records.append(record)
                
            response = supabase.table('articles').upsert(db_records, on_conflict='id').execute()
            print(f"[INFO] Supabase Upsert Success: {len(db_records)} articles stored.")
        except Exception as e:
            print(f"[ERROR] Supabase Integration Failed: {e}", file=sys.stderr)
    else:
        print("[WARN] SUPABASE_URL or SUPABASE_KEY missing in environment.", file=sys.stderr)

    # Fallback/Local storage backup
    output_path = os.path.join(VOLUME_PATH, "feed.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)

    volume.commit()

    print(f"\n{'=' * 60}")
    print(f"✅ Done! {feed['totalArticles']} articles → {output_path}")
    print(f"   Ben's Bites: {feed['sources']['bens_bites']}")
    print(f"   The Rundown: {feed['sources']['the_rundown']}")
    print(f"   Reddit: {feed['sources']['reddit']}")
    print(f"{'=' * 60}")

    return feed


# ── Web endpoint to fetch the latest feed.json ─────────────────────────────

@app.function(
    image=image_with_fastapi, 
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("my-supabase-secret", required=False)]  # You can either bind a managed secret or rely on the .modal.toml [secrets] block
)
@modal.fastapi_endpoint(method="GET")
def get_feed():
    """HTTP endpoint to get the latest articles directly from Supabase DB."""
    import os
    from datetime import datetime, timezone
    from supabase import create_client, Client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        return {"error": "Supabase credentials are not configured in Modal."}

    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        response = supabase.table('articles').select('*').order('date', desc=True).limit(50).execute()
        articles = response.data
        
        # Transform back to the frontend's expected CamelCase format
        frontend_articles = []
        for a in articles:
            rec = dict(a)
            rec['imageUrl'] = rec.pop('image_url', None)
            rec['scrapedAt'] = rec.pop('scraped_at', None)
            frontend_articles.append(rec)
            
        bens = len([a for a in frontend_articles if a.get("source") == "bens_bites"])
        rundown = len([a for a in frontend_articles if a.get("source") == "the_rundown"])
        reddit = len([a for a in frontend_articles if a.get("source") == "reddit"])
        
        return {
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "bens_bites": bens,
                "the_rundown": rundown,
                "reddit": reddit
            },
            "articles": frontend_articles
        }
    except Exception as e:
        return {"error": str(e)}

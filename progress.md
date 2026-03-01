# Progress Log

> **Purpose:** Track what was done, errors encountered, tests run, and results.  
> **Last Updated:** 2026-03-01

---

## Session: 2026-03-01 (Afternoon)

### Actions
- ✅ Blueprint approved by user
- ✅ Wrote scraping SOP in `architecture/scraping_sop.md`
- ✅ Built `scrape_bens_bites.py` — scrapes Substack archive, extracts 10 articles
- ✅ Built `scrape_the_rundown.py` — scrapes therundown.ai, extracts 9 articles
- ✅ Built `aggregate.py` — merges and deduplicates into 19-article `feed.json`
- ✅ Fixed date extraction: switched from HTML parser to JSON-LD `datePublished` regex
- ✅ Fixed timeout handling: added `TimeoutError` + `OSError` catches
- ✅ Moved 24h filtering from scrapers to frontend (scrapers save all articles)
- ✅ Built dashboard: `index.html`, `index.css`, `app.js`
- ✅ Verified in browser — all features working

### Errors Encountered & Fixed
1. **Timeout crash** — The Rundown scraper crashed on SSL timeout; fixed by catching `TimeoutError`
2. **Missing dates** — Both scrapers returned `null` dates; root cause: dates in JSON-LD, not `<time>` tags; fixed with regex extraction
3. **24h filter too strict** — All articles older than 24h during development; moved filter to frontend

### Tests
- ✅ Ben's Bites scraper: 10/10 articles scraped with dates and images
- ✅ The Rundown scraper: 9/10 articles (1 SSL error, non-blocking)
- ✅ Aggregator: 19 unique articles merged and sorted
- ✅ Dashboard: articles display, filtering works, save persists in localStorage

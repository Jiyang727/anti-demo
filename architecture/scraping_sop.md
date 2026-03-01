# Scraping SOP — AI News Dashboard

> **Purpose:** Define how each newsletter source is scraped, validated, and stored.

---

## General Rules

1. **Rate Limiting:** 1 request per second minimum delay between requests
2. **User-Agent:** `AINewsDashboard/1.0 (personal project; contact@example.com)`
3. **Caching:** All scraped data cached in `.tmp/` as JSON; re-scrape only if older than 1 hour
4. **Time Filter:** Only articles from the last 24 hours are included in the final feed
5. **Error Handling:** Log errors to stderr; never crash — return empty list on failure
6. **Encoding:** All output is UTF-8 JSON

---

## Source: Ben's Bites

- **Archive URL:** `https://bensbites.com/archive`
- **Article URL pattern:** `https://www.bensbites.com/p/{slug}`
- **Scraping strategy:**
  1. Fetch archive page
  2. Parse all article links and titles from the page
  3. For each article, fetch the individual page
  4. Extract: title, subtitle, author, date, first ~200 chars of body
  5. Generate `id` as SHA-256 of the article URL
- **Date extraction:** Look for `<time>` element or date metadata in article page
- **Output:** `.tmp/bens_bites.json`

## Source: The AI Rundown

- **Homepage URL:** `https://therundown.ai`
- **Article URL pattern:** `https://therundown.ai/p/{slug}`
- **Scraping strategy:**
  1. Fetch homepage
  2. Parse article listing (titles, subtitles, links)
  3. For each article, fetch the individual page
  4. Extract: title, subtitle, authors, date, first ~200 chars of body, image
  5. Generate `id` as SHA-256 of the article URL
- **Date extraction:** Look for date text near author bylines
- **Output:** `.tmp/the_rundown.json`

## Source: Reddit (Future)

- **Library:** PRAW
- **Subreddits:** r/MachineLearning, r/artificial, r/deeplearning
- **Not implemented yet** — deferred to later phase

---

## Aggregation

- Read all `.tmp/*.json` source files
- Merge into single array, deduplicate by `id`
- Sort by `date` descending (newest first)
- Output → `.tmp/feed.json`

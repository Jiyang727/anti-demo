# Findings & Research Log

> **Purpose:** Record all discoveries, constraints, API quirks, and external research.  
> **Last Updated:** 2026-03-01

---

## Discoveries

### Ben's Bites
- **Platform:** Substack (bensbites.com)
- **Archive page:** `https://bensbites.com/archive` — lists articles with title + subtitle + link
- **Article URLs:** `https://www.bensbites.com/p/{slug}`
- **Content structure:** Title (h1), subtitle (h3), author (Ben Tossell), date, sections with headers
- **Sections per article:** Headlines, Tools & demos, Dev Dish, community content
- **No API key needed** — public content, scrapeable via HTTP

### The AI Rundown
- **Platform:** Custom site (therundown.ai)
- **Homepage:** Lists latest articles with title, subtitle, author badges, and links
- **Article URLs:** `https://therundown.ai/p/{slug}`
- **Content structure:** Title (h1), date, multiple authors, structured sections (Latest Developments, Tools, etc.)
- **Articles include:** Source tags (e.g. GOOGLE, OPENAI), inline images, external links
- **No API key needed** — public content, scrapeable via HTTP

### Reddit (Deferred)
- Requires OAuth via PRAW library
- Rate limit: 100 QPM authenticated
- Relevant subreddits: r/MachineLearning, r/artificial, r/deeplearning
- **Deferred to later phase** per user request

## Constraints

- Both sites are public but could rate-limit aggressive scraping
- Use 1 req/sec delay + descriptive User-Agent
- Substack may serve JS-rendered content; fallback to RSS if needed
- Cache scraped data in `.tmp/` to avoid unnecessary re-fetching

## External Resources

- [Ben's Bites Archive](https://bensbites.com/archive)
- [The AI Rundown](https://therundown.ai)
- [PRAW documentation](https://praw.readthedocs.io/) (for future Reddit integration)

# 📜 Project Constitution — `gemini.md`

> **This file is LAW.** All schemas, rules, and architectural invariants live here.  
> Only update when a schema changes, a rule is added, or architecture is modified.  
> **Last Updated:** 2026-03-01

---

## 1. Project Identity

- **Name:** AI News Dashboard
- **North Star:** Beautiful interactive dashboard showing latest AI articles from the last 24 hours
- **Status:** Phase 1 — Blueprint (awaiting approval)

---

## 2. Data Schema

> ⚠️ **No code may be written in `tools/` until this section is fully defined and approved.**

### Input Schema — Scraped Article
```json
{
  "id": "sha256-hash-of-url",
  "source": "bens_bites | the_rundown | reddit",
  "title": "string",
  "subtitle": "string | null",
  "author": "string",
  "date": "ISO 8601 date string",
  "url": "original article URL",
  "summary": "first ~200 chars of content",
  "imageUrl": "string | null",
  "scrapedAt": "ISO 8601 timestamp"
}
```

### Output Schema — Saved Article
```json
{
  "articleId": "sha256-hash-of-url",
  "savedAt": "ISO 8601 timestamp",
  "source": "bens_bites | the_rundown | reddit"
}
```

---

## 3. Integrations

| Service | Purpose | Auth Method | Status |
| ------- | ------- | ----------- | ------ |
| Ben's Bites (Substack) | AI newsletter scraping | None (public) | 🟡 Pending |
| The AI Rundown | AI newsletter scraping | None (public) | 🟡 Pending |
| Reddit | AI news aggregation | OAuth (PRAW) | ⏳ Later |
| Supabase | Persistent storage | API Key | ⏳ Later |

---

## 4. Behavioral Rules

1. **24-hour refresh**: Only show articles from the last 24 hours on refresh.
2. **Save/Bookmark**: Users can save articles; saved articles persist across refreshes.
3. **Gorgeous UI**: Design must be premium — dark mode, glassmorphism, micro-animations.
4. **Source filtering**: Users can filter by source (All / Ben's Bites / The Rundown).
5. **Polite scraping**: Rate-limit requests (1 req/sec) with proper User-Agent headers.

---

## 5. Architectural Invariants

1. **Data-First:** No tool code until schemas are defined and approved.
2. **3-Layer Separation:** Architecture (SOPs) → Navigation (Routing) → Tools (Execution).
3. **Deterministic Tools:** All scripts in `tools/` must be atomic, testable, and free of probabilistic logic.
4. **Self-Annealing:** Every error must be analyzed, patched, tested, and documented in `architecture/`.
5. **`.tmp/` is ephemeral:** Intermediate files go in `.tmp/`, final payloads go to their cloud destination.

---

## 6. Maintenance Log

_To be populated in Phase 5: Trigger._

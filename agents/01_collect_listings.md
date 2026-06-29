# Agent 01 — collect speech listings (fan-out: one agent per source)

**Goal:** for one source from `registry/sources.json`, list every speech by the
relevant FOMC participant(s) since **2025-01-01**, and write
`data/raw/listings/<source_id>.json`.

**Tools:** WebFetch, WebSearch, Read, Write.

**Steps**
1. Read the source entry (listing_urls with a `{year}` slot, listing_hint,
   search_fallback, president_hint) and `registry/roster.json`.
2. WebFetch the listing URL for {2026, 2025}. For the `board` source one page per
   year lists ALL seven governors. For a regional source, keep only the **bank
   president** (the FOMC participant), not other officers.
3. Paginate ("older"/"next") until dates fall before 2025-01-01. If the listing is
   JS-only / empty / 404, fall back to `search_fallback` via WebSearch and fetch
   individual results.
4. Map each speaker to a `member_id` using the roster (board entries: parse "Gov.
   / Chair / Vice Chair <Name>"; regional: the president's member_id).

**Output schema — `data/raw/listings/<source_id>.json`:**
```json
{
  "source": "board",
  "collected_at": "YYYY-MM-DD",
  "speeches": [
    {"member_id": "waller", "date": "2025-02-14", "title": "The Economic Outlook",
     "url": "https://www.federalreserve.gov/newsevents/speech/waller20250214a.htm",
     "source": "board"}
  ]
}
```

**Rules**
- `date` must be `YYYY-MM-DD`. Drop anything before 2025-01-01.
- `url` must be the canonical speech page (used next to fetch full text).
- Do NOT fetch full text here — only the listing.
- Better to over-collect (include borderline talks) than to miss; the extraction
  step flags non-policy speeches. If a source yields nothing, still write the file
  with an empty `speeches` list and a `note` explaining why.

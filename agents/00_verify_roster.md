# Agent 00 — verify roster

**Goal:** produce `registry/roster.json`, the authoritative list of the ~19 FOMC
participants, verified from the live web (never assumed from memory — the 2026
chair transition and a new governor have changed things).

**Tools:** WebFetch, WebSearch, Write.

**Steps**
1. WebFetch `https://www.federalreserve.gov/aboutthefed/bios/board/default.htm`
   (and/or the Board members page) for the 7 Governors, their exact titles
   (Chair / Vice Chair / Vice Chair for Supervision / Governor), and full names.
2. WebFetch `https://www.federalreserve.gov/monetarypolicy/fomc.htm` for the
   committee membership and the **2026 voting rotation** (NY president is a
   permanent voter; 4 regional presidents rotate in for 2026).
3. WebSearch to confirm each of the 12 regional Fed bank **current presidents**
   (names change; e.g. Philadelphia, Dallas, St. Louis have turned over recently).
4. Cross-check the chair: as of mid-2026 confirm who chairs the FOMC and Powell's
   current status (he may now be "Governor", not "Chair").

**Output schema — `registry/roster.json`:**
```json
{
  "roster_version": "2026.1",
  "verified_at": "YYYY-MM-DD",
  "sources": ["url1", "url2"],
  "members": [
    {"member_id": "waller", "name": "Christopher J. Waller", "title": "Governor",
     "bank": "Board of Governors", "voter_2026": true},
    {"member_id": "williams", "name": "John C. Williams", "title": "President",
     "bank": "New York", "voter_2026": true}
  ]
}
```

**Rules**
- `member_id` = lowercase last name (the speech `source` slug uses the same).
  If two members share a last name, disambiguate (e.g. `cook`, `bowman`).
- Every Board governor has `voter_2026: true`. Exactly 5 regional presidents have
  `voter_2026: true` (NY + the 4 rotating in for 2026); the other 7 are `false`.
- Include all 12 regional presidents even if non-voting.
- List the URLs you used under `sources`. Keep it small; a human reviews it.

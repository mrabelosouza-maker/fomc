# Agent 02 — fetch full speech text (fan-out over listed speeches)

**Goal:** for a batch of speeches not yet on disk, fetch the full text and write
`data/raw/speeches/<speech_id>.md`.

**Tools:** WebFetch, Read, Write.

**`speech_id`** = `<member_id>-YYYYMMDD-<6hex>` where the 6 hex chars are the first
6 of `sha1(lowercased trimmed title)`. (Matches `fomc/schema.py:speech_id`.) The
collection driver passes the precomputed id; otherwise compute it identically.

**Steps**
1. For each item: WebFetch its `url` asking for the **speech body only** — the
   spoken/written remarks, excluding site navigation, footnote chrome, related
   links, and "Last Update" boilerplate. Keep footnotes' substance if inline.
2. Write the cleaned text (markdown/plain) to `data/raw/speeches/<speech_id>.md`.
   Prepend a one-line header: `# <title> — <member_id> — <date>`.
3. Skip any id whose `.md` already exists (idempotent).

**Quality checks**
- If the fetched body is suspiciously short (< ~400 words) or looks like a landing
  page, retry once; if still bad, write what you have and note `<!-- SHORT -->` at
  the top so the extractor can flag it.
- Never invent text. Only persist what the page actually contains.

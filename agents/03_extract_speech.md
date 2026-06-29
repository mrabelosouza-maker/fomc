# Agent 03 — extract reaction function (fan-out over fetched speeches)

**Goal:** for a fetched speech, read `data/raw/speeches/<speech_id>.md` + the
rubric and write `data/extracted/<speech_id>.json` conforming to `fomc/schema.py`.

**Tools:** Read, Write.

**Steps**
1. Read `registry/rubric.json` (the scoring rules) and the speech `.md`.
2. Score every numeric dimension in the rubric ONLY from this speech's text. Use
   integers or .5; use `null` for a dimension the speech does not address (do not
   guess 0). Hawkish = leans tighter / more inflation-worried; dovish = leans
   easier / more employment-worried.
3. Write a one-paragraph monetary-policy `summary`, 2–4 VERBATIM `key_quotes`
   (each tagged with the dimension + a short context note), `near_term_bias`,
   `theme_flags`, and `non_policy` per the rubric's rules.

**Output schema — `data/extracted/<speech_id>.json`:**
```json
{
  "speech_id": "waller-20250214-a1b2c3",
  "member_id": "waller", "title": "...", "date": "2025-02-14",
  "url": "https://...", "source": "board", "non_policy": false,
  "summary": "One paragraph on the speaker's monetary-policy message ...",
  "key_quotes": [
    {"quote": "verbatim sentence", "context": "what it refers to",
     "dimension": "policy_stance_read"}
  ],
  "llm_scores": {
    "composite_hawk_dove": 2, "mandate_weight": 1,
    "inflation_conviction": 4, "labor_concern": 1, "policy_stance_read": 3,
    "near_term_bias": {"direction": "hold", "pace": "patient"},
    "theme_flags": ["tariffs", "fed_independence"]
  },
  "extractor_model": "claude-opus-4-8", "extracted_at": "2026-06-20T00:00:00Z",
  "rubric_version": "1.0"
}
```

**Rules**
- Ranges: `composite_hawk_dove` and `mandate_weight` ∈ [-5,5]; the other three ∈
  [0,5]. `near_term_bias.direction` ∈ {cut, hold, hike, unclear}. Out-of-range
  values are rejected by the deterministic loader.
- Quote text must be verbatim (no paraphrase inside the quotes).
- Do NOT compute `tone_score` — the deterministic build fills it from the lexicon.
- Skip ids whose `.json` already exists (idempotent), unless the `.md` changed.

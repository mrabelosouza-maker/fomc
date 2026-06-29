# CLAUDE.md — FOMC Reaction Functions (project state)

Read this first. Captures decisions not obvious from the code.

## What this is
Per-FOMC-member monetary-policy **reaction functions** from their **speeches**
(since 2025-01-01), split **voters vs non-voters** (2026), with **median** group
functions. Output: one self-contained interactive HTML. Sibling of `rules_us`,
`us_oil_sensitive` under `r:\Macro EMs\Modelagem\`.

## The central design: a JSON seam (two halves)
1. **Non-deterministic** half — Claude Code **agents** (`agents/00..03`) collect
   speeches (WebFetch/WebSearch) and an **LLM extracts** reaction-function scores
   into `data/extracted/<id>.json`. This is NOT a runtime-API Python script; the
   LLM work is done by subagents at build time (chosen with the user).
2. **Deterministic** half — `fomc/` reads ONLY the JSON and emits HTML + CSVs.
   Tested (`tests/`, 15 tests). The manifest is **derived from disk** (file
   presence = state), so the fan-out agents never race on a shared file.

Contract = the on-disk JSON schema in `fomc/schema.py`. Agents never import
`fomc/`; `fomc/` only touches the network in `fred.py` (cached macro ribbon).

## Key methodology decisions (do not silently revert)
- **Hybrid scoring:** LLM dimensions are the signal; the deterministic dictionary
  tone (`fomc/lexicon.py`) is a **cross-check only**, never an override.
- **Standalone hawk/dove rubric** (`registry/rubric.json`), NOT tied to the Warsh
  deck. 5 numeric dims + near_term_bias + theme_flags + a **6-driver decomposition**
  (oil_war, underlying_inflation/broadening, tariffs, labor_market, growth_demand,
  other; each intensity 0–3 × push hawkish/dovish/neutral). Hawkish = positive axis;
  `labor_concern` is inverted (see `config.normalize_to_hawk`).
- **Headline = CURRENT stance, not all-history.** The composite is recency-weighted
  over the last `CURRENT_WINDOW_DAYS` (120) so a regime change isn't diluted. This
  was added because the all-history mean mislabeled Waller (who pivoted hawkish in
  May 2026) as a dove. Don't revert the headline to all-history weighting.
- **`delta` = most recent policy speech − mean of the prior ones** (per user). The
  momentum dumbbell plots mean→latest; the driver delta is latest-speech drivers −
  mean-of-prior drivers. Distinct from the windowed headline by design.
- **Driver decomposition is shown in COMPOSITE POINTS** (intensity × `b1`, the OLS
  slope of composite on net driver intensity, also used by the ex-oil counterfactual)
  — NOT raw summed intensities (which overshoot ±10 and aren't on the hawk-dove scale).
- **Roster verified live** at build — the 2026 chair transition is real: **Kevin
  Warsh is Chair, Powell is now Governor, Miran left the Board.** Never hard-code
  roster from memory; `member_id` is a stable last-name slug.
- **Per-member fetch cap (~10)** keeps it tractable: coverage is a recent sample,
  not a census. The base browser lists everything; only fetched speeches score.
- **Predecessors excluded** from current seats (Bostic→Atlanta interim Venable;
  Harker→Philadelphia Paulson).

## How to run
```bash
pip install -r requirements.txt
python scripts/run_deterministic.py        # rebuild from data/extracted
python -m pytest                           # 15 tests
```
Refresh speeches = re-run the `agents/` prompts via Claude Code (idempotent by
`speech_id` = `<member>-YYYYMMDD-<6hex(title)>`; matches `schema.speech_id`).

## Files
- `fomc/config.py` — paths, palette, DIMENSIONS (+hawk signs), START_DATE,
  HALF_LIFE_DAYS, NON_POLICY_WEIGHT.
- `fomc/schema.py` — JSON contract + strict validation (rejects out-of-range).
- `fomc/manifest.py` — manifest DERIVED from disk (listed/fetched/extracted).
- `fomc/aggregate.py` — recency-weighted member functions, group medians, evolution.
- `fomc/figures.py` / `fomc/html.py` — Plotly + self-contained HTML (speech
  browser embeds full text via a `/*__DATA__*/` JSON blob, vanilla-JS filtering).
- `fomc/fred.py` — copied `_env_key`/`_fred_observations` (macro ribbon).
- `registry/` — sources.json (13), roster.json (verified), rubric.json.
- `agents/` — the versioned prompt specs for the four agent phases.

## Gotchas
- Most regional bank sites 403 the fetcher; agents use WebSearch + reader-proxy /
  browser-UA. `federalreserve.gov` and `api.stlouisfed.org` work directly.
- Re-verify the roster + 2026 voters when refreshing (rotation/turnover change).
- Coarse scores: trust the cross-member ranking & medians, not 0.1-pt gaps.
- Keep README.md / SPEC.md in sync with `registry/rubric.json` and `config.py`.
- The HTML is ~7 MB (full speech corpus embedded) — that's intended (offline).

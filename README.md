# FOMC Reaction Functions

Individual monetary-policy **reaction function of every FOMC participant**
(7 Board governors + 12 regional Fed presidents), separating **voters vs
non-voters** (2026 rotation), with a **median reaction function**, built from
their **speeches since 2025-01-01**. Deliverable: one self-contained interactive
HTML.

## What you get (`results/fomc_reaction_functions.html`)
0. **Fed calendar** — upcoming speakers/events (from `registry/calendar.json`),
   voters flagged, pre-FOMC blackout highlighted.
1. **Current reaction function of each member** — cards sorted hawk→dove, voters
   (★) highlighted. Headline = the **current** composite (recent ~4-month window,
   not all-history) so a regime change isn't diluted; a **Δ badge** shows the
   marginal shift = latest speech − mean of prior. Plus per-dimension bars.
1b. **Per-voter brief** (`registry`/agents → `data/briefs/`): a table of what each
   voter thinks on **inflation** (just oil / oil+tariffs / broadening-underlying),
   **labor** (stable / downside / upside), and **stance** (appropriate · well
   positioned · modestly restrictive · neutral · loose), with verbatim quotes.
2. **Hawk-dove ranking** (current stance) with voter/all median lines.
3. **Momentum on the margin** — a dumbbell per member from trailing→current
   composite, sorted by the shift. This is where regime changes surface (e.g.
   Waller's "Policy Risks Have Changed" pivot the trailing mean would hide).
4. **Hawk-dove WITHOUT the oil/war shock** — counterfactual: each member's
   position with vs without the current oil/war driver contribution (all members
   and a **voters-only** variant).
5. **Voters vs non-voters on the scale** — strip plot with group medians.
6. **Why — driver decomposition, level AND delta** — stacked diverging bars
   splitting each member's stance into oil/war, underlying-inflation/broadening,
   tariffs, labor, activity, other; plus the *delta* (current − baseline) showing
   what changed on the margin.
7. **Median reaction functions** — radar of voters vs non-voters vs all.
8. **Members × dimensions heatmap.**
9. **Time evolution** since 2025 (per-member + median paths).
10. **LLM × dictionary tone cross-check** scatter.
11. **Speech base** — every collected speech, filterable, drill-down to the full
    text + summary + verbatim quotes + scores + per-speech driver chips.

## Architecture — a JSON seam
- **Collection + extraction (non-deterministic):** Claude Code agents (`agents/`)
  use WebFetch to list/fetch speeches and an LLM to score each against
  `registry/rubric.json`, writing `data/extracted/<id>.json`.
- **Build (deterministic):** `fomc/` reads only that JSON and emits the HTML +
  CSVs. Fully testable; the manifest is derived from disk so re-runs are
  incremental and race-free.

```
registry/   sources.json (13 sources) · roster.json (verified at build) · rubric.json
data/raw/   listings/<source>.json · speeches/<id>.md · fred/<series>.csv
data/extracted/<id>.json   manifest.json
fomc/       config schema fred lexicon manifest aggregate figures html build
agents/     00_verify_roster 01_collect_listings 02_fetch_speeches 03_extract_speech
scripts/run_deterministic.py
results/    fomc_reaction_functions.html · summary.csv · median_functions.csv
```

## Run
```bash
pip install -r requirements.txt          # pandas numpy plotly pytest
# .env needs FRED_API_KEY (macro ribbon only; build degrades gracefully without it)
python scripts/run_deterministic.py      # rebuild HTML + CSVs from data/extracted
python scripts/run_deterministic.py --no-ribbon --as-of 2026-06-20
python -m pytest                         # deterministic package tests
```
Re-collecting speeches (refresh) re-runs the `agents/` prompts via Claude Code;
only new/changed speeches are fetched and extracted (idempotent by `speech_id`).

## Reaction-function rubric (per speech, `registry/rubric.json`)
Dimensions: `composite_hawk_dove` (−5..+5) · `mandate_weight` (employment↔inflation)
· `inflation_conviction` (0..5) · `labor_concern` (0..5) · `policy_stance_read`
(0..5) · `near_term_bias` (cut/hold/hike + pace) · `theme_flags`. Hawkish = leans
tighter / more inflation-worried.
**Drivers** (the "why"): each speech also scores 6 drivers — `oil_war`,
`underlying_inflation` (broadening), `tariffs`, `labor_market`, `growth_demand`,
`other` — with an intensity (0–3) and a push (hawkish/dovish/neutral). The
decomposition aggregates these (recency-weighted, current window) into a signed
per-driver contribution.

## Current vs trailing (the regime-change fix)
The headline composite is the **current** stance — recency-weighted over the last
`CURRENT_WINDOW_DAYS` (120) — so a member who pivots isn't anchored to months-old
speeches. `delta = current − trailing baseline` measures the marginal shift.
Example: Waller's trailing read is ≈ −0.9 (dovish) but his current read is ≈ +0.3
with Δ ≈ +3.8 — a hawkish regime change driven by oil/war + inflation broadening,
which the all-history mean alone would mislabel as "dove".

## Current read (data through 2026-06)
Most hawkish now: **Schmid, Logan, Musalem, Hammack, Kashkari**. Biggest hawkish
**marginal** shifts: **Waller, Barkin, Williams** (oil/war + broadening). Still
dovish: **Bowman, Daly**; Powell ≈ neutral. The 2026 hawkish turn is dominated by
the **oil/war supply shock + underlying-inflation broadening**, while the labor
market — the dovish anchor of 2025 — has gone mostly neutral. **Kevin Warsh is
Chair** (verified live; Powell now Governor) but has no in-window Fed speeches →
*insufficient*. Atlanta's seat is interim (Venable). See `SPEC.md` for caveats.

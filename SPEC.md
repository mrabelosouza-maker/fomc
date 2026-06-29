# SPEC — FOMC reaction functions

## Goal
Characterise each FOMC participant's monetary-policy reaction function from their
speeches, separate 2026 voters vs non-voters, and aggregate to group medians, in
a reproducible, auditable way.

## Method
1. **Roster** (`registry/roster.json`) verified live at build (agent 00) — never
   assumed from memory. The 2026 chair transition (Warsh in, Powell to Governor,
   Miran out) and seat turnovers (Atlanta interim Venable; Philadelphia Paulson)
   are exactly why this is verified, not hard-coded.
2. **Collection** (agents 01–02): per-source listings since 2025-01-01, then full
   speech text. 13 sources: the Board page (all governors) + 12 regional banks.
   Most bank sites return HTTP 403 to the fetcher; agents fall back to WebSearch
   enumeration + a reader proxy / browser-UA fetch. Coverage is per-member capped
   (~10 most recent policy-relevant speeches) — not the entire historical corpus.
3. **Extraction** (agent 03): an LLM scores each speech against
   `registry/rubric.json` — structured dimensions + one-paragraph summary +
   verbatim key quotes + a **driver decomposition** (6 drivers × intensity 0–3 ×
   push hawkish/dovish/neutral: oil_war, underlying_inflation/broadening, tariffs,
   labor_market, growth_demand, other). `null` for dimensions a speech doesn't
   address; `non_policy=true` for regulation/payments/ceremonial talks.
4. **Cross-check** (`fomc/lexicon.py`): a deterministic hawk/dove dictionary tone
   per speech. It **never overrides** the LLM; the LLM×tone scatter surfaces
   disagreements as a diagnostic. The dictionary is deliberately simple and is
   *expected* to be a weak signal — that weakness is the argument for the LLM.
5. **Aggregation** (`fomc/aggregate.py`):
   - **Current stance** = recency-weighted mean (half-life 120d) over policy
     speeches within `CURRENT_WINDOW_DAYS` (120) of as-of; falls back to the single
     latest speech if the window is empty (`stale`). This is the headline, so a
     regime change on the margin is not diluted by months-old speeches.
   - **Marginal delta** = **most recent policy speech − mean of the member's prior
     policy speeches**. The sharpest read of a regime change (Waller: latest +2.0
     vs prior mean −2.5 → Δ +4.5).
   - **Driver decomposition**: the *level* (composition of the current stance) is
     the recency-weighted signed intensity per driver over the current window; the
     *delta* per driver = latest speech − mean of prior speeches. Both expressed in
     composite points (× the ex-oil slope b1), so a stacked net ≈ the composite /
     its delta. Splits the stance/shift into oil/war vs underlying-inflation/
     broadening vs labor vs the rest.
   - Group medians (voters / non-voters / all) over current stances; monthly
     evolution uses the full history. Non-policy speeches down-weighted ×0.25.

## Sign convention
Hawkish is positive on every displayed axis. `labor_concern` is inverted for the
hawk axis (more concern about jobs = dovish). See `config.normalize_to_hawk`.

## Reproducibility contract
- **Deterministic** (`python scripts/run_deterministic.py`): everything in
  `fomc/` — manifest, tone, aggregation, figures, HTML. Byte-stable given fixed
  `data/extracted/` modulo the as-of date / FRED ribbon. Covered by `tests/`.
- **Non-deterministic** (needs Claude Code agents): collection + LLM extraction.
  Mitigations: prompts/rubric versioned (`agents/`, `rubric.json`); cached per
  speech (recompute only if missing or `content_hash`/`rubric_version` changes);
  `extractor_model` + `rubric_version` stamped; lexicon cross-check.

## Caveats / known limits
- **Coverage is a sample, not a census.** Per-member cap + 403-blocked sites +
  video-only events with no transcript (several Kashkari/Goolsbee appearances)
  mean some speeches are listed but not scored. The base browser shows the full
  listing; only fetched speeches carry scores.
- **Warsh (Chair) is insufficient** — no in-window Fed speeches; shown greyed.
- **Predecessors excluded:** Bostic/Harker 2025 speeches are NOT attributed to
  the current Atlanta/Philadelphia seat-holders.
- **Recursive single-speaker scores** are coarse (integers/.5) on purpose; treat
  the cross-member *ranking* and *medians* as the signal, not 0.1-point gaps.
- **Lexicon tone** is a rough diagnostic; hawks who acknowledge two-sided risks
  score near-zero tone. Don't read it as a second opinion of equal weight.
- **Ex-oil counterfactual is an estimate.** The composite is a holistic LLM score,
  not a sum of drivers, so the "without oil/war" scale removes `b1 × oil_war_signed`
  where `b1` is the OLS slope of composite on net driver intensity across members.
  It answers "roughly how many composite points is oil adding", not an exact
  structural decomposition. Finding (2026-06): stripping oil pushes the marginal
  hawks (Waller, Williams, Barkin, Jefferson, Barr) back below zero and takes the
  **voter median from +0.5 to 0.0** — i.e. the voting committee's hawkish tilt is
  almost entirely the oil shock — while the structural hawks (Logan, Schmid,
  Musalem, Kashkari, Hammack) stay clearly hawkish on underlying inflation.

## Tuning knobs
`config.HALF_LIFE_DAYS` (120) · `config.CURRENT_WINDOW_DAYS` (120, the current-vs-
trailing split) · `config.NON_POLICY_WEIGHT` (0.25) · `config.START_DATE`
(2025-01-01) · `config.DIMENSIONS` (axes + hawk signs) · `config.DRIVERS` (the
decomposition + colors) · per-member fetch cap (in the agent prompts) ·
`lexicon.HAWK_TERMS/DOVE_TERMS`.

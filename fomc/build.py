"""Deterministic build: read data/extracted/ + manifest -> HTML + CSVs.

Pure function of disk state (modulo the as-of date / FRED ribbon).
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone

import pandas as pd

from . import aggregate, config, figures, fred, html, manifest


def _write_summary_csv(mfuncs) -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RESULTS_DIR / "summary.csv"
    cols = (["member_id", "name", "title", "bank", "voter_2026", "n_speeches",
             "n_policy", "n_current", "first_date", "last_date", "composite",
             "latest_composite", "baseline_composite", "delta", "tone_mean", "stale",
             "insufficient"] + config.DIMENSION_IDS)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for m in sorted(mfuncs.values(), key=lambda x: (x.insufficient,
                        -(x.composite if x.composite is not None else -99))):
            w.writerow([m.member_id, m.name, m.title, m.bank, m.voter_2026,
                        m.n_speeches, m.n_policy, m.n_current, m.first_date, m.last_date,
                        m.composite, m.latest_composite, m.baseline_composite, m.delta,
                        m.tone_mean, m.stale, m.insufficient]
                       + [m.dims.get(d) for d in config.DIMENSION_IDS])


def _write_medians_csv(medians) -> None:
    path = config.RESULTS_DIR / "median_functions.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group", "n"] + config.DIMENSION_IDS)
        for g in ("voters", "non_voters", "all"):
            row = medians.get(g, {})
            w.writerow([g, row.get("n", 0)] + [row.get(d) for d in config.DIMENSION_IDS])


def main(as_of: str | None = None, *, with_ribbon: bool = True) -> str:
    as_of = as_of or str(pd.Timestamp.now().date())

    # Refresh derived manifest + deterministic tone cross-check.
    m = manifest.build_manifest()
    manifest.save_manifest(m)
    print("manifest:", manifest.status_line(m))
    n_tone = aggregate.ensure_tone()
    if n_tone:
        print(f"tone cross-check filled on {n_tone} extractions")

    roster = aggregate.load_roster()
    corpus = aggregate.load_corpus()
    briefs = aggregate.load_briefs()
    calendar = aggregate.load_calendar()
    print(f"roster: {len(roster)} members | corpus: {len(corpus)} extractions | "
          f"briefs: {len(briefs)} | calendar: {len(calendar.get('events', []))} | as_of {as_of}")

    mfuncs = aggregate.member_functions(corpus, roster, as_of)
    medians = aggregate.group_medians(mfuncs)
    evo = aggregate.evolution(corpus, roster, as_of)
    decomp = aggregate.driver_decomposition(corpus, roster, as_of)
    exoil, b1 = aggregate.ex_oil_counterfactual(mfuncs, decomp)
    print(f"ex-oil mapping: {b1:.3f} composite pts per unit of net driver intensity")

    _write_summary_csv(mfuncs)
    _write_medians_csv(medians)

    figs = {
        "ranking": figures.fig_ranking(mfuncs, medians),
        "momentum": figures.fig_momentum(mfuncs),
        "exoil": figures.fig_ex_oil(mfuncs, exoil, b1),
        "exoil_voters": figures.fig_ex_oil(mfuncs, exoil, b1, voters_only=True),
        "voterstrip": figures.fig_voter_strip(mfuncs),
        "drivers": figures.fig_driver_decomp(mfuncs, decomp, b1),
        "driverdelta": figures.fig_driver_delta(mfuncs, decomp, b1),
        "radar": figures.fig_median_radar(medians),
        "heatmap": figures.fig_heatmap(mfuncs),
        "evolution": figures.fig_evolution(evo, roster),
        "tone": figures.fig_tone_scatter(corpus),
    }
    ribbon = fred.macro_ribbon() if with_ribbon else {}
    meta = {
        "asof": as_of,
        "window": f"desde {config.START_DATE}",
        "n_speeches": len(corpus),
        "n_members": sum(1 for f in mfuncs.values() if not f.insufficient),
        "ribbon": ribbon,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roster_version": m.get("roster_version", ""),
    }
    page = html.build_page(mfuncs, medians, evo, corpus, roster, figs, meta, decomp, briefs, calendar)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS_DIR / "fomc_reaction_functions.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page)/1024:.0f} KB)")
    # Also emit index.html at the repo root so GitHub Pages (served from / on
    # the default branch) picks up the latest build automatically.
    index = config.PROJECT_ROOT / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"wrote {index}")
    return str(out)


if __name__ == "__main__":
    main()

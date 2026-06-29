"""Turn the per-speech extractions into per-member reaction functions, group
medians (voters / non-voters / all), and time-evolution series.

All functions take an explicit ``as_of`` so results are testable and the only
non-determinism in the build is the chosen as-of date.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, lexicon, schema


# ----------------------------------------------------------------------- roster
@dataclass
class Member:
    member_id: str
    name: str
    title: str
    bank: str
    voter_2026: bool


def load_roster() -> dict[str, Member]:
    if not config.ROSTER_PATH.exists():
        return {}
    data = json.loads(config.ROSTER_PATH.read_text(encoding="utf-8"))
    out = {}
    for m in data.get("members", []):
        out[m["member_id"]] = Member(
            member_id=m["member_id"], name=m.get("name", m["member_id"]),
            title=m.get("title", ""), bank=m.get("bank", ""),
            voter_2026=bool(m.get("voter_2026", False)),
        )
    return out


# -------------------------------------------------------------------- corpus io
def load_briefs() -> dict[str, dict]:
    """Per-voter stance briefs (inflation / labor / stance + verbatim quotes),
    keyed by member_id, from data/briefs/*.json."""
    out: dict[str, dict] = {}
    if config.BRIEFS_DIR.exists():
        for f in sorted(config.BRIEFS_DIR.glob("*.json")):
            b = json.loads(f.read_text(encoding="utf-8"))
            out[b["member_id"]] = b
    return out


def load_calendar() -> dict:
    """Upcoming Fed events/speakers (registry/calendar.json), or empty."""
    if config.CALENDAR_PATH.exists():
        return json.loads(config.CALENDAR_PATH.read_text(encoding="utf-8"))
    return {"events": []}


def load_corpus() -> list[schema.Extraction]:
    if not config.EXTRACTED_DIR.exists():
        return []
    out = []
    for f in sorted(config.EXTRACTED_DIR.glob("*.json")):
        out.append(schema.load_extraction(f))
    return out


def ensure_tone() -> int:
    """Deterministic post-pass: fill tone_score on any extraction missing it,
    reading the speech text from disk. Returns number updated."""
    updated = 0
    for f in sorted(config.EXTRACTED_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        md = config.SPEECHES_DIR / f"{d['speech_id']}.md"
        if d.get("tone_score") or not md.exists():
            continue
        d["tone_score"] = lexicon.tone(md.read_text(encoding="utf-8"))
        f.write_text(json.dumps(d, indent=2), encoding="utf-8")
        updated += 1
    return updated


# ------------------------------------------------------------------- weighting
def recency_weight(date: str, as_of: str, half_life: float = config.HALF_LIFE_DAYS) -> float:
    age = (pd.Timestamp(as_of) - pd.Timestamp(date)).days
    return 0.5 ** (max(age, 0) / half_life)


def _wmean(pairs: list[tuple[float, float]]) -> float | None:
    """Weighted mean of (value, weight); None if no weight."""
    sw = sum(w for _, w in pairs)
    if sw <= 0:
        return None
    return sum(v * w for v, w in pairs) / sw


# ------------------------------------------------------- per-member functions
@dataclass
class MemberFunction:
    member_id: str
    name: str
    title: str
    bank: str
    voter_2026: bool
    n_speeches: int
    n_policy: int
    n_current: int                            # policy speeches inside the current window
    first_date: str
    last_date: str
    dims: dict[str, float | None]            # CURRENT (windowed) recency-weighted score per dim
    dims_hawk: dict[str, float | None]       # normalised to [-1,1], +1 hawkish
    composite: float | None                  # current composite (the headline, windowed)
    latest_composite: float | None           # most recent policy speech composite
    baseline_composite: float | None         # mean of the PRIOR policy speeches
    delta: float | None                      # latest - mean(prior): marginal regime shift
    tone_mean: float | None
    stale: bool                              # current relies on a fallback (no speech in window)
    insufficient: bool


def _days(a: str, b: str) -> float:
    return (pd.Timestamp(a) - pd.Timestamp(b)).days


def member_functions(corpus: list[schema.Extraction], roster: dict[str, Member],
                     as_of: str) -> dict[str, MemberFunction]:
    by_member: dict[str, list[schema.Extraction]] = {}
    for ex in corpus:
        by_member.setdefault(ex.member_id, []).append(ex)

    out: dict[str, MemberFunction] = {}
    members = set(roster) | set(by_member)
    for mid in sorted(members):
        speeches = by_member.get(mid, [])
        policy = [s for s in speeches if not s.non_policy]
        m = roster.get(mid)
        n_policy = len(policy)

        # Split policy speeches into the current window vs the older baseline.
        window = [s for s in policy if _days(as_of, s.date) <= config.CURRENT_WINDOW_DAYS]
        baseline = [s for s in policy if _days(as_of, s.date) > config.CURRENT_WINDOW_DAYS]
        stale = False
        if not window and policy:
            # No speech in the window: fall back to the single most recent one.
            window = [max(policy, key=lambda s: s.date)]
            baseline = [s for s in policy if s is not window[0]]
            stale = True

        dims: dict[str, float | None] = {}
        dims_hawk: dict[str, float | None] = {}
        for dim_id in config.DIMENSION_IDS:
            pairs = [(v, recency_weight(s.date, as_of)) for s in window
                     if (v := s.score(dim_id)) is not None]
            mean = _wmean(pairs)
            dims[dim_id] = None if mean is None else round(mean, 3)
            dims_hawk[dim_id] = None if mean is None else round(config.normalize_to_hawk(dim_id, mean), 3)

        # Marginal delta = most recent policy speech vs the MEAN of the prior ones.
        policy_sorted = sorted(policy, key=lambda s: s.date)
        latest_composite, latest_speech = None, None
        for s in reversed(policy_sorted):
            v = s.score("composite_hawk_dove")
            if v is not None:
                latest_composite, latest_speech = v, s
                break
        prior_c = [v for s in policy_sorted if s is not latest_speech
                   and (v := s.score("composite_hawk_dove")) is not None]
        mean_composite = statistics.mean(prior_c) if prior_c else None
        delta = (round(latest_composite - mean_composite, 3)
                 if (latest_composite is not None and mean_composite is not None) else None)

        tones = [t for s in speeches if (t := (s.tone_score or {}).get("net_tone")) is not None]
        dates = sorted(s.date for s in speeches)
        out[mid] = MemberFunction(
            member_id=mid, name=(m.name if m else mid), title=(m.title if m else ""),
            bank=(m.bank if m else ""), voter_2026=(m.voter_2026 if m else False),
            n_speeches=len(speeches), n_policy=n_policy, n_current=len(window),
            first_date=dates[0] if dates else "", last_date=dates[-1] if dates else "",
            dims=dims, dims_hawk=dims_hawk, composite=dims.get("composite_hawk_dove"),
            latest_composite=latest_composite,
            baseline_composite=(round(mean_composite, 3) if mean_composite is not None else None),
            delta=delta,
            tone_mean=(round(statistics.mean(tones), 4) if tones else None),
            stale=stale, insufficient=(n_policy == 0),
        )
    return out


_PUSH_SIGN = {"hawkish": 1.0, "dovish": -1.0, "neutral": 0.0}


def _signed_drivers(speeches: list[schema.Extraction], as_of: str) -> dict[str, float]:
    """Recency-weighted signed intensity per driver over a set of speeches."""
    signed: dict[str, float] = {}
    for did in config.DRIVER_IDS:
        pairs = []
        for s in speeches:
            d = s.driver(did)
            if d is None:
                continue
            intensity, push = d
            pairs.append((intensity * _PUSH_SIGN[push], recency_weight(s.date, as_of)))
        val = _wmean(pairs)
        signed[did] = round(val, 3) if val is not None else 0.0
    return signed


def _signed_simple(speeches: list[schema.Extraction]) -> dict[str, float]:
    """Simple (equal-weight) mean signed intensity per driver."""
    signed: dict[str, float] = {}
    for did in config.DRIVER_IDS:
        vals = []
        for s in speeches:
            d = s.driver(did)
            if d is not None:
                vals.append(d[0] * _PUSH_SIGN[d[1]])
        signed[did] = round(statistics.mean(vals), 3) if vals else 0.0
    return signed


def driver_decomposition(corpus: list[schema.Extraction], roster: dict[str, Member],
                         as_of: str) -> dict[str, dict]:
    """Per member: the driver mix of the CURRENT stance, the BASELINE (pre-window)
    mix, and the DELTA (current - baseline) per driver.

    Each value is a signed intensity: +ve = net hawkish push, -ve = dovish.
    `delta` decomposes the marginal regime shift (what got more hawkish/dovish).
    """
    by_member: dict[str, list[schema.Extraction]] = {}
    for ex in corpus:
        if not ex.non_policy:
            by_member.setdefault(ex.member_id, []).append(ex)

    out: dict[str, dict] = {}
    for mid, policy in by_member.items():
        policy_sorted = sorted(policy, key=lambda s: s.date)
        latest = policy_sorted[-1]
        prior = policy_sorted[:-1]
        # Level (composition of the current stance): windowed, recency-weighted.
        window = [s for s in policy if _days(as_of, s.date) <= config.CURRENT_WINDOW_DAYS] or [latest]
        current_level = _signed_drivers(window, as_of)
        # Delta = latest speech vs the MEAN of the prior speeches, per driver.
        latest_signed = _signed_drivers([latest], latest.date)
        mean_signed = _signed_simple(prior) if prior else {d: 0.0 for d in config.DRIVER_IDS}
        delta = {d: round(latest_signed[d] - mean_signed[d], 3) for d in config.DRIVER_IDS}
        out[mid] = {
            "signed": current_level,                 # current-stance level (windowed)
            "latest": latest_signed,
            "baseline": mean_signed,                 # mean of prior speeches
            "delta": delta,                          # latest - mean(prior)
            "net": round(sum(current_level.values()), 3),
            "has_drivers": any(s.drivers for s in window),
            "has_baseline": bool(prior) and any(s.drivers for s in prior),
        }
    return out


def ex_oil_counterfactual(mfuncs: dict[str, MemberFunction],
                          decomp: dict[str, dict]) -> tuple[dict[str, dict], float]:
    """Counterfactual hawk-dove score if the oil/war driver is removed.

    The composite is an LLM holistic score, not a sum of drivers, so we estimate
    'composite points per unit of net driver intensity' by least-squares of the
    current composite on the current net driver score across members, then strip
    out oil_war's contribution: ex_oil = composite - b1 * oil_war_signed.
    Returns ({member_id: {composite, ex_oil, oil_points}}, b1).
    """
    xs, ys = [], []
    for mid, mf in mfuncs.items():
        d = decomp.get(mid)
        if mf.composite is None or not d or not d["has_drivers"]:
            continue
        xs.append(d["net"]); ys.append(mf.composite)
    b1 = 0.0
    if len(xs) >= 2 and (max(xs) - min(xs)) > 1e-6:
        b1 = float(np.polyfit(np.array(xs), np.array(ys), 1)[0])
    out: dict[str, dict] = {}
    for mid, mf in mfuncs.items():
        d = decomp.get(mid)
        if mf.composite is None or not d or not d["has_drivers"]:
            continue
        oil = d["signed"].get("oil_war", 0.0)
        oil_points = round(b1 * oil, 3)
        out[mid] = {"composite": mf.composite,
                    "ex_oil": round(mf.composite - oil_points, 3),
                    "oil_points": oil_points,
                    "voter_2026": mf.voter_2026}
    return out, round(b1, 3)


# ----------------------------------------------------------------- group medians
def _median(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def group_medians(mfuncs: dict[str, MemberFunction]) -> dict[str, dict[str, float | None]]:
    """Median per dimension for {voters, non_voters, all}, raw scale."""
    groups = {
        "voters": [f for f in mfuncs.values() if f.voter_2026 and not f.insufficient],
        "non_voters": [f for f in mfuncs.values() if not f.voter_2026 and not f.insufficient],
        "all": [f for f in mfuncs.values() if not f.insufficient],
    }
    out: dict[str, dict[str, float | None]] = {}
    for g, members in groups.items():
        out[g] = {"n": len(members)}
        for dim_id in config.DIMENSION_IDS:
            out[g][dim_id] = _median([m.dims[dim_id] for m in members])
    return out


# ------------------------------------------------------------------- evolution
def evolution(corpus: list[schema.Extraction], roster: dict[str, Member],
              as_of: str) -> dict:
    """Monthly recency-weighted composite, per member and per group median.

    Returns {months:[...], members:{mid:[...]}, voters:[...], all:[...]}.
    """
    if not corpus:
        return {"months": [], "members": {}, "voters": [], "all": []}
    start = pd.Timestamp(config.START_DATE).to_period("M")
    end = pd.Timestamp(as_of).to_period("M")
    months = pd.period_range(start, end, freq="M")
    by_member: dict[str, list[schema.Extraction]] = {}
    for ex in corpus:
        by_member.setdefault(ex.member_id, []).append(ex)

    def composite_asof(speeches: list[schema.Extraction], asof_ts: str) -> float | None:
        pairs = []
        for s in speeches:
            if s.date > asof_ts:
                continue
            v = s.score("composite_hawk_dove")
            if v is None:
                continue
            w = recency_weight(s.date, asof_ts)
            if s.non_policy:
                w *= config.NON_POLICY_WEIGHT
            pairs.append((v, w))
        return _wmean(pairs)

    member_series: dict[str, list[float | None]] = {}
    for mid, speeches in by_member.items():
        series = []
        for mo in months:
            asof_ts = str(mo.to_timestamp("M").date())
            val = composite_asof(speeches, asof_ts)
            series.append(None if val is None else round(val, 3))
        member_series[mid] = series

    def median_track(only_voters: bool) -> list[float | None]:
        track = []
        for i, mo in enumerate(months):
            vals = []
            for mid, series in member_series.items():
                m = roster.get(mid)
                if only_voters and not (m and m.voter_2026):
                    continue
                if series[i] is not None:
                    vals.append(series[i])
            track.append(_median(vals))
        return track

    return {
        "months": [str(mo) for mo in months],
        "members": member_series,
        "voters": median_track(True),
        "all": median_track(False),
    }

"""Paths, palette and the canonical reaction-function dimension list.

This is the single place the deterministic pipeline learns about the scoring
rubric's *numeric* shape (the human-facing rubric text lives in
``registry/rubric.json``, which the extraction agent consumes).
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = PROJECT_ROOT / "registry"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
LISTINGS_DIR = RAW_DIR / "listings"
SPEECHES_DIR = RAW_DIR / "speeches"
FRED_DIR = RAW_DIR / "fred"
EXTRACTED_DIR = DATA_DIR / "extracted"
BRIEFS_DIR = DATA_DIR / "briefs"
MANIFEST_PATH = DATA_DIR / "manifest.json"
RESULTS_DIR = PROJECT_ROOT / "results"

ROSTER_PATH = REGISTRY_DIR / "roster.json"
SOURCES_PATH = REGISTRY_DIR / "sources.json"
RUBRIC_PATH = REGISTRY_DIR / "rubric.json"
CALENDAR_PATH = REGISTRY_DIR / "calendar.json"

# Window of interest for speeches (inclusive lower bound).
START_DATE = "2025-01-01"

# Recency weighting for the "current" per-member reaction function.
HALF_LIFE_DAYS = 120.0
# The "current" stance reads only speeches within this many days of as-of (so a
# regime change on the margin is not diluted by months-old speeches). Older
# speeches form the baseline against which the marginal delta is measured.
CURRENT_WINDOW_DAYS = 120.0
# Non-policy speeches stay in the corpus but are down-weighted in aggregation.
NON_POLICY_WEIGHT = 0.25

# Drivers of the policy stance — the "why" decomposition. Each speech scores every
# driver with an intensity (0-3) and a push (hawkish/dovish/neutral).
DRIVERS = [
    {"id": "oil_war", "label": "Oil / guerra", "color": "#8b1e1e"},
    {"id": "underlying_inflation", "label": "Inflação subjacente / broadening", "color": "#c0392b"},
    {"id": "tariffs", "label": "Tarifas", "color": "#e08a1e"},
    {"id": "labor_market", "label": "Mercado de trabalho", "color": "#1e7d8c"},
    {"id": "growth_demand", "label": "Atividade / demanda", "color": "#7d5ba6"},
    {"id": "other", "label": "Outros (FCI, fiscal, r*, indep.)", "color": "#8a8f99"},
]
DRIVER_IDS = [d["id"] for d in DRIVERS]
DRIVER_BY_ID = {d["id"]: d for d in DRIVERS}
PUSHES = ("hawkish", "dovish", "neutral")

# Canonical numeric dimensions. ``hawk_sign`` maps the raw score onto a common
# "hawkishness" axis (+1 = more hawkish) for radar/heatmap display; ``scale`` is
# (lo, hi) for validation and normalisation.
DIMENSIONS = [
    {"id": "composite_hawk_dove", "label": "Hawk-dove composite", "scale": (-5, 5), "hawk_sign": 1},
    {"id": "mandate_weight", "label": "Mandate weight (infl↑)", "scale": (-5, 5), "hawk_sign": 1},
    {"id": "inflation_conviction", "label": "Inflation conviction", "scale": (0, 5), "hawk_sign": 1},
    {"id": "labor_concern", "label": "Labor-market concern", "scale": (0, 5), "hawk_sign": -1},
    {"id": "policy_stance_read", "label": "Stance restrictiveness", "scale": (0, 5), "hawk_sign": 1},
]
DIMENSION_IDS = [d["id"] for d in DIMENSIONS]
DIM_BY_ID = {d["id"]: d for d in DIMENSIONS}

# Chair Warsh has no in-window *speeches* (he is `insufficient` in the corpus), but
# his first FOMC press conference (2026-06-17, transcript in
# ../us_oil_sensitive/pressconference20260617.txt) is a strong read on his reaction
# function. Scored by hand against registry/rubric.json and shown as a SEPARATE row
# below the two corpus groups in the voter-strip (fig_voter_strip), so it is never
# mixed into the speech-driven medians. Central +3.0 (held the funds rate, so not the
# +4/+5 of someone demanding a hike now, but: "inflation is a choice… we are going to
# deliver", 5-yr overshoot, hike kept on the table, labor downside dismissed, stance
# judged only "uneven"/not clearly restrictive). Range +2.5..+3.5.
CHAIR_PLACEMENT = {
    "member_id": "warsh",
    "name": "Kevin M. Warsh",
    "composite": 3.0,
    "lo": 2.5,
    "hi": 3.5,
    "source": "Coletiva 17/06/2026 (1ª como Chair)",
}

# Palette (shared with the sibling dashboards: navy + gold, hawk red / dove teal).
NAVY = "#16213e"
GOLD = "#c8920a"
HAWK = "#c0392b"
DOVE = "#1e7d8c"
INK = "#1a1a1a"
PAPER = "#eef0f4"


def normalize_to_hawk(dim_id: str, raw: float) -> float:
    """Map a raw dimension score onto [-1, 1] with +1 = most hawkish."""
    lo, hi = DIM_BY_ID[dim_id]["scale"]
    mid = (lo + hi) / 2.0
    half = (hi - lo) / 2.0
    return DIM_BY_ID[dim_id]["hawk_sign"] * (raw - mid) / half

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fomc import config  # noqa: E402


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Redirect all on-disk paths to a temp tree."""
    data = tmp_path / "data"
    paths = {
        "DATA_DIR": data,
        "RAW_DIR": data / "raw",
        "LISTINGS_DIR": data / "raw" / "listings",
        "SPEECHES_DIR": data / "raw" / "speeches",
        "FRED_DIR": data / "raw" / "fred",
        "EXTRACTED_DIR": data / "extracted",
        "MANIFEST_PATH": data / "manifest.json",
        "RESULTS_DIR": tmp_path / "results",
        "ROSTER_PATH": tmp_path / "registry" / "roster.json",
    }
    for name, p in paths.items():
        monkeypatch.setattr(config, name, p)
    for p in (paths["LISTINGS_DIR"], paths["SPEECHES_DIR"], paths["EXTRACTED_DIR"],
              paths["RESULTS_DIR"], paths["ROSTER_PATH"].parent):
        p.mkdir(parents=True, exist_ok=True)
    return paths


def write_roster(paths, members):
    paths["ROSTER_PATH"].write_text(json.dumps({"roster_version": "test",
                                                 "members": members}), encoding="utf-8")


def write_speech(paths, sid, member_id, date, *, title="T", scores=None,
                 non_policy=False, drivers=None,
                 text="Inflation remains elevated and restrictive policy is warranted."):
    (paths["SPEECHES_DIR"] / f"{sid}.md").write_text(text, encoding="utf-8")
    ex = {
        "speech_id": sid, "member_id": member_id, "title": title, "date": date,
        "url": "http://x", "source": "board", "non_policy": non_policy,
        "summary": "summary text", "key_quotes": [],
        "llm_scores": scores or {"composite_hawk_dove": 2, "mandate_weight": 1,
                                 "inflation_conviction": 4, "labor_concern": 1,
                                 "policy_stance_read": 3,
                                 "near_term_bias": {"direction": "hold", "pace": "patient"},
                                 "theme_flags": ["tariffs"]},
        "rubric_version": "1.0",
    }
    if drivers is not None:
        ex["drivers"] = drivers
    (paths["EXTRACTED_DIR"] / f"{sid}.json").write_text(json.dumps(ex), encoding="utf-8")

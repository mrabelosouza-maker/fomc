import json

import pytest

from fomc import aggregate, config, schema
from conftest import write_roster, write_speech


def test_driver_validation_rejects_bad(tmp_path):
    d = {"speech_id": "x", "member_id": "w", "date": "2025-01-01",
         "llm_scores": {}, "drivers": {"oil_war": {"intensity": 9, "push": "hawkish"}}}
    p = tmp_path / "x.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(schema.SchemaError):
        schema.load_extraction(p)

    d["drivers"] = {"oil_war": {"intensity": 2, "push": "sideways"}}
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(schema.SchemaError):
        schema.load_extraction(p)


def test_driver_helper_skips_zero_intensity():
    ex = schema.Extraction.from_json(
        {"speech_id": "x", "member_id": "w", "date": "2025-01-01", "llm_scores": {},
         "drivers": {"oil_war": {"intensity": 0, "push": "hawkish"},
                     "underlying_inflation": {"intensity": 3, "push": "hawkish"}}})
    assert ex.driver("oil_war") is None
    assert ex.driver("underlying_inflation") == (3.0, "hawkish")


def test_decomposition_signs(tmp_project):
    p = tmp_project
    write_roster(p, [{"member_id": "x", "name": "X", "voter_2026": True, "bank": "Board"}])
    write_speech(p, "x-20260601-a", "x", "2026-06-01",
                 drivers={"oil_war": {"intensity": 3, "push": "hawkish"},
                          "labor_market": {"intensity": 2, "push": "dovish"},
                          "tariffs": {"intensity": 1, "push": "neutral"}})
    corpus = aggregate.load_corpus()
    roster = aggregate.load_roster()
    dec = aggregate.driver_decomposition(corpus, roster, "2026-06-10")
    assert dec["x"]["has_drivers"] is True
    assert dec["x"]["signed"]["oil_war"] == 3.0       # hawkish positive
    assert dec["x"]["signed"]["labor_market"] == -2.0  # dovish negative
    assert dec["x"]["signed"]["tariffs"] == 0.0        # neutral
    assert dec["x"]["net"] == 1.0


def test_driver_delta_signs(tmp_project):
    p = tmp_project
    write_roster(p, [{"member_id": "w", "name": "W", "voter_2026": True, "bank": "Board"}])
    # baseline (older) oil absent; current oil hawkish 3 -> delta +3 for oil
    write_speech(p, "w-20251101-a", "w", "2025-11-01", scores={"composite_hawk_dove": -3},
                 drivers={"oil_war": {"intensity": 0, "push": "neutral"},
                          "labor_market": {"intensity": 3, "push": "dovish"}})
    write_speech(p, "w-20260520-c", "w", "2026-05-20", scores={"composite_hawk_dove": 2},
                 drivers={"oil_war": {"intensity": 3, "push": "hawkish"},
                          "labor_market": {"intensity": 1, "push": "dovish"}})
    corpus = aggregate.load_corpus(); roster = aggregate.load_roster()
    dec = aggregate.driver_decomposition(corpus, roster, "2026-06-10")
    assert dec["w"]["has_baseline"] is True
    assert dec["w"]["delta"]["oil_war"] == 3.0      # oil turned strongly hawkish
    assert dec["w"]["delta"]["labor_market"] > 0     # dovish labor push shrank (-1 vs -3)


def test_ex_oil_counterfactual(tmp_project):
    p = tmp_project
    write_roster(p, [{"member_id": "hot", "name": "Hot", "voter_2026": True, "bank": "Board"},
                     {"member_id": "cold", "name": "Cold", "voter_2026": False, "bank": "SF"}])
    write_speech(p, "hot-20260601-a", "hot", "2026-06-01", scores={"composite_hawk_dove": 3},
                 drivers={"oil_war": {"intensity": 3, "push": "hawkish"},
                          "underlying_inflation": {"intensity": 3, "push": "hawkish"}})
    write_speech(p, "cold-20260601-b", "cold", "2026-06-01", scores={"composite_hawk_dove": -3},
                 drivers={"labor_market": {"intensity": 3, "push": "dovish"}})
    corpus = aggregate.load_corpus(); roster = aggregate.load_roster()
    mf = aggregate.member_functions(corpus, roster, "2026-06-10")
    dec = aggregate.driver_decomposition(corpus, roster, "2026-06-10")
    exoil, b1 = aggregate.ex_oil_counterfactual(mf, dec)
    assert b1 > 0                                   # more hawkish net -> higher composite
    assert exoil["hot"]["ex_oil"] < exoil["hot"]["composite"]   # removing oil lowers the hawk
    assert exoil["cold"]["ex_oil"] == exoil["cold"]["composite"]  # no oil -> unchanged


def test_delta_captures_regime_change(tmp_project):
    p = tmp_project
    write_roster(p, [{"member_id": "w", "name": "Waller", "voter_2026": True, "bank": "Board"}])
    # old dovish speeches + a recent hawkish pivot
    write_speech(p, "w-20251101-a", "w", "2025-11-01", scores={"composite_hawk_dove": -4})
    write_speech(p, "w-20260101-b", "w", "2026-01-01", scores={"composite_hawk_dove": -3})
    write_speech(p, "w-20260520-c", "w", "2026-05-20", scores={"composite_hawk_dove": 2})
    corpus = aggregate.load_corpus()
    roster = aggregate.load_roster()
    mf = aggregate.member_functions(corpus, roster, "2026-06-10")["w"]
    assert mf.composite > 0            # current stance hawkish (windowed)
    assert mf.baseline_composite < -2  # trailing was dovish
    assert mf.delta > 3                # large hawkish shift surfaced

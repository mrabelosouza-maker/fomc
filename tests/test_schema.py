import json

import pytest

from fomc import config, schema


def test_speech_id_stable_and_dedups_title():
    a = schema.speech_id("waller", "2025-02-14", "The Economic Outlook")
    b = schema.speech_id("waller", "2025-02-14", "the economic outlook  ")
    assert a == b
    assert a.startswith("waller-20250214-")


def test_validate_rejects_out_of_range(tmp_path):
    d = {"speech_id": "x", "member_id": "waller", "date": "2025-01-01",
         "llm_scores": {"composite_hawk_dove": 9}}
    p = tmp_path / "x.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(schema.SchemaError):
        schema.load_extraction(p)


def test_validate_rejects_bad_date(tmp_path):
    d = {"speech_id": "x", "member_id": "w", "date": "2025/01/01", "llm_scores": {}}
    p = tmp_path / "x.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(schema.SchemaError):
        schema.load_extraction(p)


def test_null_score_is_allowed():
    ex = schema.Extraction.from_json(
        {"speech_id": "x", "member_id": "w", "date": "2025-01-01",
         "llm_scores": {"composite_hawk_dove": None}}).validate()
    assert ex.score("composite_hawk_dove") is None
    assert ex.score("mandate_weight") is None

from fomc import build
from conftest import write_roster, write_speech


def test_full_build_writes_html(tmp_project):
    p = tmp_project
    write_roster(p, [
        {"member_id": "waller", "name": "Christopher Waller", "voter_2026": True, "bank": "Board",
         "title": "Governor"},
        {"member_id": "daly", "name": "Mary Daly", "voter_2026": False, "bank": "San Francisco",
         "title": "President"},
    ])
    write_speech(p, "waller-20250214-a", "waller", "2025-02-14", title="Outlook")
    write_speech(p, "daly-20250301-b", "daly", "2025-03-01", title="Economy",
                 scores={"composite_hawk_dove": -2, "mandate_weight": -1,
                         "inflation_conviction": 1, "labor_concern": 4, "policy_stance_read": 2})

    out = build.main(as_of="2025-03-15", with_ribbon=False)
    text = (p["RESULTS_DIR"] / "fomc_reaction_functions.html").read_text(encoding="utf-8")
    assert "Christopher Waller" in text
    assert "Mary Daly" in text
    assert "DATA =" in text and "/*__DATA__*/" not in text   # data injected
    assert (p["RESULTS_DIR"] / "summary.csv").exists()
    assert (p["RESULTS_DIR"] / "median_functions.csv").exists()
    # tone cross-check filled deterministically
    import json
    ex = json.loads((p["EXTRACTED_DIR"] / "waller-20250214-a.json").read_text(encoding="utf-8"))
    assert "net_tone" in ex["tone_score"]

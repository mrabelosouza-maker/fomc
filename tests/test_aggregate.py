from fomc import aggregate, config
from conftest import write_roster, write_speech


def test_recency_weight_halves_at_half_life():
    w = aggregate.recency_weight("2025-01-01", "2025-05-01",
                                 half_life=(aggregate.pd.Timestamp("2025-05-01")
                                            - aggregate.pd.Timestamp("2025-01-01")).days)
    assert abs(w - 0.5) < 1e-9


def test_normalize_to_hawk_directions():
    # labor_concern is inverted: high concern -> dovish (negative)
    assert config.normalize_to_hawk("labor_concern", 5) == -1.0
    assert config.normalize_to_hawk("labor_concern", 0) == 1.0
    assert config.normalize_to_hawk("composite_hawk_dove", 5) == 1.0
    assert config.normalize_to_hawk("inflation_conviction", 5) == 1.0


def test_member_functions_and_medians(tmp_project):
    p = tmp_project
    write_roster(p, [
        {"member_id": "hawk", "name": "A Hawk", "voter_2026": True, "bank": "Board"},
        {"member_id": "dove", "name": "B Dove", "voter_2026": False, "bank": "SF"},
        {"member_id": "silent", "name": "C Silent", "voter_2026": True, "bank": "NY"},
    ])
    write_speech(p, "hawk-20250301-aaa", "hawk", "2025-03-01",
                 scores={"composite_hawk_dove": 4, "mandate_weight": 3,
                         "inflation_conviction": 5, "labor_concern": 1, "policy_stance_read": 4})
    write_speech(p, "dove-20250301-bbb", "dove", "2025-03-01",
                 scores={"composite_hawk_dove": -3, "mandate_weight": -2,
                         "inflation_conviction": 1, "labor_concern": 4, "policy_stance_read": 1})

    roster = aggregate.load_roster()
    corpus = aggregate.load_corpus()
    mf = aggregate.member_functions(corpus, roster, "2025-03-15")

    assert mf["hawk"].composite == 4
    assert mf["dove"].composite == -3
    assert mf["silent"].insufficient is True   # no speeches
    assert mf["hawk"].dims_hawk["labor_concern"] > 0   # low concern -> hawkish

    med = aggregate.group_medians(mf)
    assert med["voters"]["n"] == 1            # only the hawk votes & has speeches
    assert med["voters"]["composite_hawk_dove"] == 4
    assert med["all"]["n"] == 2


def test_non_policy_downweighted(tmp_project):
    p = tmp_project
    write_roster(p, [{"member_id": "x", "name": "X", "voter_2026": True, "bank": "Board"}])
    # recent non-policy hawkish + older policy dovish; policy should still dominate
    write_speech(p, "x-20250301-a", "x", "2025-03-01", non_policy=False,
                 scores={"composite_hawk_dove": -4})
    write_speech(p, "x-20250302-b", "x", "2025-03-02", non_policy=True,
                 scores={"composite_hawk_dove": 5})
    roster = aggregate.load_roster()
    corpus = aggregate.load_corpus()
    mf = aggregate.member_functions(corpus, roster, "2025-03-15")
    assert mf["x"].composite < 0   # dovish policy speech outweighs hawkish non-policy
    assert mf["x"].n_policy == 1

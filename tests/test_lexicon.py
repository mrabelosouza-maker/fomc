from fomc import lexicon


def test_hawkish_text_scores_positive():
    t = lexicon.tone("Inflation is persistent and elevated; policy must stay restrictive and vigilant.")
    assert t["net_tone"] > 0
    assert t["hawk_hits"] >= 2


def test_dovish_text_scores_negative():
    t = lexicon.tone("The labor market is cooling and softening; there is room to cut and ease policy.")
    assert t["net_tone"] < 0
    assert t["dove_hits"] >= 2


def test_negation_flips():
    pos = lexicon.tone("Policy is restrictive.")["net_tone"]
    neg = lexicon.tone("Policy is not restrictive.")["net_tone"]
    assert neg < pos


def test_length_normalised_and_token_count():
    t = lexicon.tone("word " * 100 + "restrictive")
    assert t["tokens"] == 101
    assert abs(t["net_tone"]) < 0.2

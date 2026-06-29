"""Deterministic hawk/dove tone index — the reproducible cross-check.

This NEVER overrides the LLM score. Its only job is to flag speeches where the
dictionary tone and the LLM composite disagree, surfaced as a diagnostic in the
HTML. Pure Python, no network, no model.
"""
from __future__ import annotations

import math
import re

# Multi-word phrases first (matched as phrases); single tokens after.
HAWK_TERMS = {
    "persistent inflation": 2.0, "inflation persistence": 2.0, "upside risk": 1.5,
    "upside risks": 1.5, "premature": 1.5, "premature easing": 2.0, "too soon": 1.0,
    "restrictive": 1.0, "restraint": 1.0, "vigilant": 1.5, "vigilance": 1.5,
    "more work to do": 1.5, "not done": 1.0, "stick": 0.5, "anchored": 0.5,
    "sticky": 1.0, "elevated inflation": 1.5, "above target": 1.0, "second-round": 1.5,
    "broadening": 1.0, "overheating": 1.5, "tighten": 1.0, "tighter": 1.0,
    "patience": 0.5, "higher for longer": 2.0, "guard against": 1.0,
}
DOVE_TERMS = {
    "cooling labor": 1.5, "cooling labor market": 2.0, "softening": 1.5, "softer": 1.0,
    "downside risk": 1.5, "downside risks": 1.5, "room to cut": 2.0, "begin cutting": 2.0,
    "room to lower": 2.0, "weakening": 1.5, "deteriorat": 1.5, "fragile": 1.5,
    "recession": 1.0, "layoffs": 1.5, "slack": 1.0, "disinflation": 1.0,
    "well on its way": 1.5, "normalize": 1.0, "normalizing": 1.0, "accommodative": 1.0,
    "recalibrat": 1.0, "support employment": 1.5, "cut rates": 1.5, "ease": 1.0,
    "easing": 1.0, "moderating": 1.0, "good place": 1.0, "less restrictive": 1.5,
}
_NEGATIONS = {"not", "no", "never", "without", "isn't", "doesn't", "aren't", "won't", "less"}
_WORD_RE = re.compile(r"[a-z']+")


def _negated_before(tokens: list[str], idx: int, window: int = 3) -> bool:
    return any(tokens[j] in _NEGATIONS for j in range(max(0, idx - window), idx))


def tone(text: str) -> dict:
    """Length-normalised net tone. >0 hawkish, <0 dovish.

    Returns {net_tone, hawk_hits, dove_hits, tokens}.
    """
    low = text.lower()
    tokens = _WORD_RE.findall(low)
    n = max(len(tokens), 1)

    def _score(terms: dict[str, float]) -> tuple[float, int]:
        total, hits = 0.0, 0
        for term, w in terms.items():
            if " " in term:
                c = low.count(term)
                if c:
                    total += w * c
                    hits += c
            else:
                # token-level so we can apply negation flipping
                for i, tk in enumerate(tokens):
                    if tk == term or tk.startswith(term):
                        if _negated_before(tokens, i):
                            total -= w  # "not restrictive" -> dovish
                        else:
                            total += w
                        hits += 1
        return total, hits

    hawk, hawk_hits = _score(HAWK_TERMS)
    dove, dove_hits = _score(DOVE_TERMS)
    net = (hawk - dove) / math.sqrt(n)
    return {
        "net_tone": round(net, 4),
        "hawk_hits": hawk_hits,
        "dove_hits": dove_hits,
        "tokens": len(tokens),
    }

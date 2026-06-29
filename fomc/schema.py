"""On-disk JSON schema = the only contract between the (non-deterministic)
collection/extraction agents and the (deterministic) build.

Validation is intentionally strict: bad agent output should fail loudly here,
not silently produce a wrong chart.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def speech_id(member_id: str, date: str, title: str) -> str:
    """Stable id: ``<member_id>-YYYYMMDD-<titlehash>`` (dedups cross-posts)."""
    ymd = date.replace("-", "")
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:6]
    return f"{slugify(member_id)}-{ymd}-{h}"


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class SchemaError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


@dataclass
class Quote:
    quote: str
    dimension: str
    context: str = ""

    @staticmethod
    def from_json(d: dict) -> "Quote":
        return Quote(quote=d["quote"], dimension=d.get("dimension", ""), context=d.get("context", ""))


@dataclass
class Extraction:
    """One speech's full extraction record (``data/extracted/<id>.json``)."""
    speech_id: str
    member_id: str
    title: str
    date: str
    url: str
    source: str
    non_policy: bool
    summary: str
    key_quotes: list[Quote]
    llm_scores: dict[str, Any]
    tone_score: dict[str, Any] = field(default_factory=dict)
    drivers: dict[str, Any] = field(default_factory=dict)
    extractor_model: str = ""
    extracted_at: str = ""
    rubric_version: str = ""

    @staticmethod
    def from_json(d: dict) -> "Extraction":
        return Extraction(
            speech_id=d["speech_id"],
            member_id=d["member_id"],
            title=d.get("title", ""),
            date=d["date"],
            url=d.get("url", ""),
            source=d.get("source", ""),
            non_policy=bool(d.get("non_policy", False)),
            summary=d.get("summary", ""),
            key_quotes=[Quote.from_json(q) for q in d.get("key_quotes", [])],
            llm_scores=d.get("llm_scores", {}),
            tone_score=d.get("tone_score", {}),
            drivers=d.get("drivers", {}),
            extractor_model=d.get("extractor_model", ""),
            extracted_at=d.get("extracted_at", ""),
            rubric_version=d.get("rubric_version", ""),
        )

    def driver(self, driver_id: str) -> tuple[float, str] | None:
        """(intensity, push) for a driver, validated; None if absent/zero."""
        v = self.drivers.get(driver_id)
        if not v:
            return None
        intensity = v.get("intensity", 0)
        push = v.get("push", "neutral")
        _require(isinstance(intensity, (int, float)) and 0 <= intensity <= 3,
                 f"{self.speech_id}: driver {driver_id} intensity {intensity!r} out of [0,3]")
        _require(push in config.PUSHES,
                 f"{self.speech_id}: driver {driver_id} push {push!r} invalid")
        if intensity == 0:
            return None
        return float(intensity), push

    def score(self, dim_id: str) -> float | None:
        """Raw numeric score for a dimension, validated against its scale."""
        v = self.llm_scores.get(dim_id, None)
        if v is None:
            return None
        lo, hi = config.DIM_BY_ID[dim_id]["scale"]
        _require(
            isinstance(v, (int, float)) and lo <= v <= hi,
            f"{self.speech_id}: {dim_id}={v!r} out of range [{lo},{hi}]",
        )
        return float(v)

    def validate(self) -> "Extraction":
        _require(bool(self.speech_id), "missing speech_id")
        _require(bool(self.member_id), f"{self.speech_id}: missing member_id")
        _require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.date) is not None,
                 f"{self.speech_id}: bad date {self.date!r}")
        for dim_id in config.DIMENSION_IDS:
            self.score(dim_id)  # raises if out of range
        for driver_id in config.DRIVER_IDS:
            self.driver(driver_id)  # raises if malformed
        bias = self.llm_scores.get("near_term_bias", {})
        if bias:
            _require(bias.get("direction") in {"cut", "hold", "hike", "unclear", None},
                     f"{self.speech_id}: bad near_term_bias.direction {bias.get('direction')!r}")
        return self


def load_extraction(path: Path) -> Extraction:
    return Extraction.from_json(json.loads(Path(path).read_text(encoding="utf-8"))).validate()

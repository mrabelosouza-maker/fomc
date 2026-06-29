"""The manifest is DERIVED from what is on disk, so the fan-out agents never
race on a shared file: they only ever *write* listings/, speeches/, extracted/.

State of each speech is inferred:
  extracted  -> data/extracted/<id>.json exists
  fetched    -> data/raw/speeches/<id>.md exists (but no extraction)
  listed     -> only present in a listing
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, schema


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _relpath(path: Path) -> str:
    try:
        return str(path.relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path)


def merge_listings() -> dict[str, dict]:
    """Universe of known speeches keyed by speech_id, from data/raw/listings/*.json.

    Each listing item must carry: member_id, date (YYYY-MM-DD), title, url, source.
    Items before START_DATE or without a member_id are dropped.
    """
    universe: dict[str, dict] = {}
    if not config.LISTINGS_DIR.exists():
        return universe
    for f in sorted(config.LISTINGS_DIR.glob("*.json")):
        data = _read_json(f)
        items = data.get("speeches", data) if isinstance(data, dict) else data
        for it in items:
            member_id = (it.get("member_id") or "").strip()
            date = (it.get("date") or "").strip()
            title = (it.get("title") or "").strip()
            if not (member_id and date and title) or date < config.START_DATE:
                continue
            sid = it.get("speech_id") or schema.speech_id(member_id, date, title)
            # First listing wins (dedups Board/BIS cross-posts).
            universe.setdefault(sid, {
                "speech_id": sid, "member_id": member_id, "date": date,
                "title": title, "url": it.get("url", ""), "source": it.get("source", f.stem),
            })
    return universe


def build_manifest() -> dict:
    universe = merge_listings()
    speeches: dict[str, dict] = {}
    for sid, meta in universe.items():
        md = config.SPEECHES_DIR / f"{sid}.md"
        ex = config.EXTRACTED_DIR / f"{sid}.json"
        entry = dict(meta)
        entry["raw_path"] = _relpath(md) if md.exists() else None
        entry["extract_path"] = _relpath(ex) if ex.exists() else None
        entry["content_hash"] = schema.content_hash(md.read_text(encoding="utf-8")) if md.exists() else None
        entry["state"] = "extracted" if ex.exists() else ("fetched" if md.exists() else "listed")
        speeches[sid] = entry
    roster_version = ""
    if config.ROSTER_PATH.exists():
        roster_version = _read_json(config.ROSTER_PATH).get("roster_version", "")
    return {"schema_version": "1.0", "roster_version": roster_version, "speeches": speeches}


def save_manifest(m: dict) -> None:
    config.MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.MANIFEST_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")


def in_state(m: dict, state: str) -> list[dict]:
    return [e for e in m["speeches"].values() if e["state"] == state]


def status_line(m: dict) -> str:
    n = len(m["speeches"])
    by = {s: len(in_state(m, s)) for s in ("listed", "fetched", "extracted")}
    return (f"{n} speeches | listed={by['listed']} fetched={by['fetched']} "
            f"extracted={by['extracted']}")

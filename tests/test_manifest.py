import json

from fomc import config, manifest
from conftest import write_speech


def _listing(paths, source, items):
    (paths["LISTINGS_DIR"] / f"{source}.json").write_text(
        json.dumps({"speeches": items}), encoding="utf-8")


def test_merge_listings_filters_and_dedups(tmp_project):
    p = tmp_project
    _listing(p, "board", [
        {"member_id": "waller", "date": "2025-02-14", "title": "Outlook", "url": "u1"},
        {"member_id": "waller", "date": "2024-12-01", "title": "Old", "url": "u0"},  # pre-window
    ])
    _listing(p, "bis", [
        {"member_id": "waller", "date": "2025-02-14", "title": "Outlook", "url": "u1b"},  # dup
    ])
    uni = manifest.merge_listings()
    assert len(uni) == 1


def test_state_machine_derived_from_disk(tmp_project):
    p = tmp_project
    _listing(p, "board", [
        {"member_id": "a", "date": "2025-02-01", "title": "Listed only", "url": "u"},
    ])
    # a fetched-but-not-extracted speech
    from fomc import schema
    sid_fetch = schema.speech_id("a", "2025-03-01", "Fetched")
    (p["SPEECHES_DIR"] / f"{sid_fetch}.md").write_text("body", encoding="utf-8")
    _listing(p, "more", [{"member_id": "a", "date": "2025-03-01", "title": "Fetched", "url": "u",
                          "speech_id": sid_fetch}])
    # an extracted speech
    write_speech(p, "a-20250401-x", "a", "2025-04-01", title="Extracted")
    _listing(p, "more2", [{"member_id": "a", "date": "2025-04-01", "title": "Extracted",
                           "url": "u", "speech_id": "a-20250401-x"}])

    m = manifest.build_manifest()
    states = {e["state"] for e in m["speeches"].values()}
    assert states == {"listed", "fetched", "extracted"}
    assert len(manifest.in_state(m, "extracted")) == 1

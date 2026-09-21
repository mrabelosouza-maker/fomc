"""Gera data/raw/speeches/powell-YYYYMMDD-c0ef29.md a partir das transcricoes
OFICIAIS ja cacheadas em data/raw/pressers/ (baixadas por scripts/presser_tone.py).

Mesmo formato dos .md do Warsh: transcricao inteira (fala do presidente +
perguntas), cabecalho com speech_id/member_id/data/fonte. Normaliza aspas
tipograficas, remove cabecalhos de pagina do PDF e rejunta as quebras de linha.

    python scripts/ingest_powell_pressers.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fomc import config  # noqa: E402
from fomc.schema import speech_id  # noqa: E402

CACHE = Path(config.DATA_DIR) / "raw" / "pressers"
TITLE = "FOMC Press Conference"
KEYS = ["20250129", "20250319", "20250507", "20250618", "20250730",
        "20250917", "20251029", "20251210", "20260128", "20260318", "20260429"]

SUBS = {"’": "'", "‘": "'", "“": '"', "”": '"',
        "—": " - ", "–": "-", "ﬁ": "fi", "ﬂ": "fl",
        "\xa0": " ", "¼": "1/4", "½": "1/2", "¾": "3/4"}
JUNK = re.compile(r"(?m)^\s*(Page \d+ of \d+|FINAL|Chair Powell's Press Conference|"
                  r"(January|February|March|April|May|June|July|August|September|"
                  r"October|November|December) \d{1,2}, 20\d\d)\s*$")


def clean(raw: str) -> str:
    for a, b in SUBS.items():
        raw = raw.replace(a, b)
    raw = JUNK.sub("", raw)
    paras, buf = [], []

    def flush():
        if buf:
            paras.append(re.sub(r"\s+", " ", " ".join(buf)).strip())
            buf.clear()

    for line in raw.split("\n"):
        s = line.strip()
        if not s:
            flush()
            continue
        buf.append(s)
        if s.endswith((".", "?", "!", '."', '?"')):
            flush()
    flush()
    return "\n\n".join(p for p in paras if p)


def main() -> None:
    for key in KEYS:
        pdf = CACHE / f"{key}.pdf"
        if not pdf.exists():
            print(f"  {key}: PDF ausente - rode scripts/presser_tone.py antes")
            continue
        date = f"{key[:4]}-{key[4:6]}-{key[6:]}"
        sid = speech_id("powell", date, TITLE)
        body = clean("\n".join(p.get_text("text") for p in fitz.open(pdf)))
        hdr = (f"# Jerome H. Powell - {TITLE} ({date})\n\n"
               f"<!-- speech_id: {sid} -->\n"
               f"<!-- member_id: powell (Chair, Board of Governors ate 15/05/2026) -->\n"
               f"<!-- date: {date} -->\n"
               f"<!-- source: https://www.federalreserve.gov/mediacenter/files/FOMCpresconf{key}.pdf -->\n\n")
        out = Path(config.SPEECHES_DIR) / f"{sid}.md"
        out.write_text(hdr + body + "\n", encoding="utf-8")
        print(f"  {sid}  {len(body.split()):>5} palavras")


if __name__ == "__main__":
    main()

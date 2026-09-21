"""Tom deterministico das coletivas do FOMC: era Powell vs era Warsh.

Baixa as transcricoes OFICIAIS (federalreserve.gov), isola SO as falas do
presidente (exclui as perguntas dos jornalistas) e aplica o mesmo indice de
lexico usado como cross-check no painel (fomc/lexicon.py):

    net_tone = (peso_hawk - peso_dove) / sqrt(n_tokens)

Saida: results/presser_tone.png + results/presser_tone.csv

    python scripts/presser_tone.py [--no-cache]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fomc import config, lexicon  # noqa: E402

CACHE = Path(config.DATA_DIR) / "raw" / "pressers"
URL = "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf{key}.pdf"
UA = {"User-Agent": "Mozilla/5.0"}

# rotulo de orador das transcricoes oficiais: "CHAIR POWELL. ..." no inicio da linha
SPEAKER = re.compile(r"(?m)^[ \t]*([A-Z][A-Z'.\- ]{3,40})\.[ \t]+")
CHAIR = re.compile(r"\bCHAIR(MAN)?\b", re.I)

# data da 1a coletiva do novo presidente; antes disso a era e Powell
SPLIT = dt.date(2026, 5, 20)
PALETTE = {"powell": "#2E6F9E", "warsh": "#C4462F"}


def meeting_keys() -> list[str]:
    ms = json.loads((config.REGISTRY_DIR / "minutes.json").read_text(encoding="utf-8"))
    ms = ms if isinstance(ms, list) else ms["meetings"]
    keys = [m["key"] for m in ms]
    for extra in ("20260916",):                      # reunioes mais novas que o calendario
        if extra not in keys:
            keys.append(extra)
    return sorted(keys)


def fetch(key: str, use_cache: bool = True) -> bytes | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{key}.pdf"
    if use_cache and f.exists():
        return f.read_bytes()
    try:
        b = urllib.request.urlopen(urllib.request.Request(URL.format(key=key), headers=UA), timeout=60).read()
    except Exception as e:                           # 404 = reuniao sem coletiva
        print(f"  {key}: sem transcricao ({type(e).__name__})")
        return None
    f.write_bytes(b)
    return b


def chair_text(pdf: bytes) -> tuple[str, int]:
    """Concatena so as falas do presidente. Devolve (texto, n_turnos)."""
    raw = "\n".join(p.get_text("text") for p in fitz.open(stream=pdf, filetype="pdf"))
    raw = re.sub(r"(?m)^\s*Page \d+ of \d+\s*$", "", raw)
    marks = list(SPEAKER.finditer(raw))
    if not marks:                                    # sem rotulos: e tudo do presidente
        return raw, 1
    parts, turns = [], 0
    head = raw[: marks[0].start()]
    if len(head.split()) > 100:                      # remarks iniciais antes do 1o rotulo
        parts.append(head)
        turns += 1
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        if CHAIR.search(m.group(1)):
            parts.append(raw[m.end():end])
            turns += 1
    return "\n".join(parts), turns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    rows = []
    for key in meeting_keys():
        pdf = fetch(key, use_cache=not args.no_cache)
        if pdf is None:
            continue
        txt, turns = chair_text(pdf)
        if len(txt.split()) < 500:
            print(f"  {key}: fala do presidente curta demais ({len(txt.split())} palavras) - pulado")
            continue
        t = lexicon.tone(txt)
        date = f"{key[:4]}-{key[4:6]}-{key[6:]}"
        era = "warsh" if dt.date.fromisoformat(date) >= SPLIT else "powell"
        rows.append(dict(key=key, date=date, era=era, net_tone=round(t["net_tone"], 4),
                         hawk_hits=t["hawk_hits"], dove_hits=t["dove_hits"],
                         tokens=t["tokens"], chair_turns=turns))
        print(f"  {key} {era:6} net_tone={t['net_tone']:+.3f}  hawk={t['hawk_hits']:3} "
              f"dove={t['dove_hits']:3} tokens={t['tokens']}")

    out_csv = config.RESULTS_DIR / "presser_tone.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out_csv} ({len(rows)} coletivas)")
    plot(rows)


def plot(rows: list[dict]) -> None:
    for r in rows:
        r["dt"] = dt.date.fromisoformat(r["date"])
        r["hawk_k"] = 1000.0 * r["hawk_hits"] / r["tokens"]      # por 1.000 palavras
        r["dove_k"] = 1000.0 * r["dove_hits"] / r["tokens"]
    pw = [r for r in rows if r["era"] == "powell"]
    wa = [r for r in rows if r["era"] == "warsh"]
    m_pw = sum(r["net_tone"] for r in pw) / len(pw)
    m_wa = sum(r["net_tone"] for r in wa) / len(wa)
    lo = rows[0]["dt"] - dt.timedelta(days=70)
    hi = rows[-1]["dt"] + dt.timedelta(days=210)

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(13.5, 9.4), dpi=200, sharex=True,
                                 gridspec_kw=dict(height_ratios=[1.55, 1], hspace=0.14))
    fig.patch.set_facecolor("white")

    for a in (ax, bx):
        a.set_facecolor("#FBFAF7")
        a.axvspan(lo, SPLIT, color=PALETTE["powell"], alpha=0.05, zorder=0)
        a.axvspan(SPLIT, hi, color=PALETTE["warsh"], alpha=0.09, zorder=0)
        a.axhline(0, color="#9AA0A6", lw=1, zorder=1)
        a.axvline(SPLIT, color="#5F6368", lw=1.2, ls="--", zorder=2)
        a.grid(axis="y", color="#E3E1DC", lw=0.8)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            a.spines[sp].set_color("#C9C6C0")

    # ------------------------------------------------------------ painel A: net tone
    ax.plot([r["dt"] for r in pw], [r["net_tone"] for r in pw], "-",
            color=PALETTE["powell"], lw=1.3, alpha=0.45, zorder=3)
    ax.scatter([r["dt"] for r in pw], [r["net_tone"] for r in pw], s=44,
               color=PALETTE["powell"], edgecolor="white", linewidth=0.8, zorder=4,
               label=f"Powell   (n={len(pw)})")
    ax.plot([r["dt"] for r in wa], [r["net_tone"] for r in wa], "-",
            color=PALETTE["warsh"], lw=2.0, alpha=0.75, zorder=3)
    ax.scatter([r["dt"] for r in wa], [r["net_tone"] for r in wa], s=140, marker="D",
               color=PALETTE["warsh"], edgecolor="white", linewidth=1.4, zorder=5,
               label=f"Warsh   (n={len(wa)})")

    ax.hlines(m_pw, pw[0]["dt"], SPLIT, color=PALETTE["powell"], lw=2.2, ls=(0, (6, 3)),
              alpha=0.9, zorder=6)
    ax.hlines(m_wa, SPLIT, hi, color=PALETTE["warsh"], lw=2.4, ls=(0, (6, 3)),
              alpha=0.95, zorder=6)
    ax.annotate(f"média Powell  {m_pw:+.3f}".replace(".", ","),
                xy=(dt.date(2020, 9, 1), m_pw), xytext=(0, -20), textcoords="offset points",
                fontsize=11.5, color=PALETTE["powell"], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="#FBFAF7", ec="none", alpha=0.92))
    ax.annotate(f"média\nWarsh\n{m_wa:+.3f}".replace(".", ","),
                xy=(hi, m_wa), xytext=(-6, 10), textcoords="offset points", ha="right",
                fontsize=11.5, color=PALETTE["warsh"], fontweight="bold", linespacing=1.15,
                bbox=dict(boxstyle="round,pad=0.25", fc="#FBF3F1", ec="none", alpha=0.9))
    ax.annotate("pico do ciclo de alta (nov/22)", xy=(dt.date(2022, 11, 2), 0.405),
                xytext=(-16, -2), textcoords="offset points", ha="right", fontsize=9.5,
                color="#5F6368", va="center")
    ax.annotate("Warsh assume", xy=(SPLIT, 0.38), xytext=(10, 0), textcoords="offset points",
                fontsize=10.5, color="#5F6368", fontweight="bold", va="center")
    ax.set_ylabel("net tone   (hawkish ▲ / dovish ▼)", fontsize=11.5, color="#3C4043")
    ax.set_title("Tom das coletivas do FOMC — era Powell vs era Warsh",
                 fontsize=17.5, fontweight="bold", color="#16213E", pad=12, loc="left")
    ax.legend(frameon=False, fontsize=12, loc="upper left")

    # --------------------------------- painel B: termos hawk (+) vs dove (-) por 1k palavras
    for grp, col in ((pw, PALETTE["powell"]), (wa, PALETTE["warsh"])):
        xs = [r["dt"] for r in grp]
        bx.bar(xs, [r["hawk_k"] for r in grp], width=26, color=col, alpha=0.95,
               edgecolor="white", linewidth=0.3)
        bx.bar(xs, [-r["dove_k"] for r in grp], width=26, color=col, alpha=0.40,
               edgecolor="white", linewidth=0.3)
    bx.annotate("termos hawkish ▲", xy=(lo, 0), xytext=(10, 14), textcoords="offset points",
                fontsize=10, color="#3C4043")
    bx.annotate("termos dovish ▼", xy=(lo, 0), xytext=(10, -24), textcoords="offset points",
                fontsize=10, color="#3C4043")
    bx.annotate("Warsh: ZERO termo dovish em 2 das 3 coletivas.\nPowell nunca ficou abaixo de 2 em 59 coletivas.",
                xy=(dt.date(2019, 3, 1), 5.3), xytext=(0, 0), textcoords="offset points",
                ha="left", va="center", fontsize=10.5, color=PALETTE["warsh"],
                fontweight="bold", linespacing=1.35)
    bx.annotate("", xy=(wa[1]["dt"], 2.6), xytext=(dt.date(2021, 9, 1), 5.0),
                arrowprops=dict(arrowstyle="->", color=PALETTE["warsh"], lw=1.4,
                                alpha=0.75, connectionstyle="arc3,rad=-0.18"))
    bx.set_ylabel("ocorrências por 1.000 palavras", fontsize=11.5, color="#3C4043")
    bx.xaxis.set_major_locator(mdates.YearLocator())
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    bx.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    bx.set_xlim(lo, hi)

    fig.text(0.008, 0.012,
             "Índice determinístico de léxico (fomc/lexicon.py): net_tone = (peso hawk − peso dove) / √tokens, com inversão por negação. "
             "O painel inferior normaliza as ocorrências pelo tamanho da fala.\n"
             "Apenas as falas do presidente — as perguntas dos jornalistas são excluídas. 62 coletivas, jan/2019 a set/2026. "
             "Fonte: transcrições oficiais, federalreserve.gov.",
             fontsize=8.6, color="#6B6B6B", va="bottom")
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    out = config.RESULTS_DIR / "presser_tone.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

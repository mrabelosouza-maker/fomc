"""Coletivas do FOMC na NOSSA classificacao: Powell vs Warsh.

Le apenas data/extracted/*-c0ef29.json (title == "FOMC Press Conference"), ou seja
o composite hawk-dove do LLM sobre registry/rubric.json - nao o indice de lexico.
Painel de cima: a mensagem. Painel de baixo: a entrega (meio da banda do fed funds).

Saida: results/presser_composite.png + results/presser_composite.csv

    python scripts/presser_composite.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fomc import config  # noqa: E402

SPLIT = dt.date(2026, 5, 20)
PALETTE = {"powell": "#2E6F9E", "warsh": "#C4462F"}

# meio da banda-alvo APOS a decisao de cada reuniao (fonte: as proprias transcricoes)
MID = {"2025-01-29": 4.375, "2025-03-19": 4.375, "2025-05-07": 4.375, "2025-06-18": 4.375,
       "2025-07-30": 4.375, "2025-09-17": 4.125, "2025-10-29": 3.875, "2025-12-10": 3.625,
       "2026-01-28": 3.625, "2026-03-18": 3.625, "2026-04-29": 3.625, "2026-06-17": 3.625,
       "2026-07-29": 3.625, "2026-09-16": 3.875}
ACTION = {"2025-09-17": "corte", "2025-10-29": "corte", "2025-12-10": "corte",
          "2026-09-16": "ALTA"}


def load() -> list[dict]:
    out = []
    for f in sorted(Path(config.EXTRACTED_DIR).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["title"].strip().lower() != "fomc press conference":
            continue
        out.append(dict(date=d["date"], dt=dt.date.fromisoformat(d["date"]),
                        member=d["member_id"],
                        composite=float(d["llm_scores"]["composite_hawk_dove"]),
                        bias=d["llm_scores"]["near_term_bias"]["direction"],
                        mid=MID.get(d["date"]), action=ACTION.get(d["date"], "manutenção")))
    return sorted(out, key=lambda r: r["dt"])


def main() -> None:
    rows = load()
    pw = [r for r in rows if r["member"] == "powell"]
    wa = [r for r in rows if r["member"] == "warsh"]
    m_pw = sum(r["composite"] for r in pw) / len(pw)
    m_wa = sum(r["composite"] for r in wa) / len(wa)

    with (config.RESULTS_DIR / "presser_composite.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "member", "composite", "bias", "mid", "action"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    lo = rows[0]["dt"] - dt.timedelta(days=40)
    hi = rows[-1]["dt"] + dt.timedelta(days=60)

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(13.5, 9.6), dpi=200, sharex=True,
                                 gridspec_kw=dict(height_ratios=[1.6, 1], hspace=0.12))
    fig.patch.set_facecolor("white")
    for a in (ax, bx):
        a.set_facecolor("#FBFAF7")
        a.axvspan(lo, SPLIT, color=PALETTE["powell"], alpha=0.05, zorder=0)
        a.axvspan(SPLIT, hi, color=PALETTE["warsh"], alpha=0.09, zorder=0)
        a.axvline(SPLIT, color="#5F6368", lw=1.2, ls="--", zorder=2)
        a.grid(axis="y", color="#E3E1DC", lw=0.8)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            a.spines[sp].set_color("#C9C6C0")

    # ------------------------------------------------- painel A: a MENSAGEM (composite)
    ax.axhline(0, color="#9AA0A6", lw=1, zorder=1)
    for grp, col, mk, sz in ((pw, PALETTE["powell"], "o", 150), (wa, PALETTE["warsh"], "D", 200)):
        ax.plot([r["dt"] for r in grp], [r["composite"] for r in grp], "-",
                color=col, lw=2.2, alpha=0.8, zorder=3)
        ax.scatter([r["dt"] for r in grp], [r["composite"] for r in grp], s=sz, marker=mk,
                   color=col, edgecolor="white", linewidth=1.5, zorder=5,
                   label=f"{'Powell' if col == PALETTE['powell'] else 'Warsh'}   (n={len(grp)})")
    ax.hlines(m_pw, pw[0]["dt"], SPLIT, color=PALETTE["powell"], lw=2, ls=(0, (6, 3)), alpha=0.8, zorder=4)
    ax.hlines(m_wa, SPLIT, hi, color=PALETTE["warsh"], lw=2.2, ls=(0, (6, 3)), alpha=0.9, zorder=4)
    for r in rows:
        ax.annotate(f"{r['composite']:+.1f}".replace(".", ","),
                    xy=(r["dt"], r["composite"]), xytext=(0, 13 if r["composite"] >= 0 else -20),
                    textcoords="offset points", ha="center", fontsize=8.8,
                    color=PALETTE[r["member"]], fontweight="bold")

    notes = {
        "2025-07-30": ("duas dissidências\npró-corte", 0, 34),
        "2025-09-17": ("\"risk-management cut\"", 4, -44),
        "2025-10-29": ("corta e avisa: dezembro\n\"não é conclusão antecipada\"", -172, -6),
        "2026-04-29": ("última do Powell; 3 dissidências\nsobre a LINGUAGEM", -150, 8),
        "2026-07-29": ("prega e não entrega\n(âncora de entrega)", -48, -52),
        "2026-09-16": ("prega e entrega:\nalta de 25bp, unânime", -108, 10),
    }
    for r in rows:
        if r["date"] in notes:
            txt, dx, dy = notes[r["date"]]
            ax.annotate(txt, xy=(r["dt"], r["composite"]), xytext=(dx, dy),
                        textcoords="offset points", fontsize=9, color="#4A4A4A", linespacing=1.3)
    ax.annotate(f"média Powell {m_pw:+.2f}".replace(".", ","), xy=(dt.date(2025, 10, 20), m_pw),
                xytext=(0, 10), textcoords="offset points", fontsize=10.5,
                color=PALETTE["powell"], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", fc="#FBFAF7", ec="none", alpha=0.9))
    ax.annotate(f"média\nWarsh\n{m_wa:+.2f}".replace(".", ","), xy=(hi, m_wa), xytext=(-6, 8),
                textcoords="offset points", ha="right", fontsize=10.5,
                color=PALETTE["warsh"], fontweight="bold", linespacing=1.15)
    ax.annotate("Warsh\nassume", xy=(SPLIT, -2.6), xytext=(10, 0), textcoords="offset points",
                fontsize=10.5, color="#5F6368", fontweight="bold", va="center", linespacing=1.2)
    ax.set_ylim(-3.2, 5.3)
    ax.set_ylabel("composite hawk-dove classificado\n(−5 dovish  →  +5 hawkish)",
                  fontsize=11.5, color="#3C4043")
    ax.set_title("As coletivas do FOMC na nossa classificação — Powell vs Warsh",
                 fontsize=17.5, fontweight="bold", color="#16213E", pad=12, loc="left")
    ax.legend(frameon=False, fontsize=12, loc="lower left")

    # ------------------------------------------------- painel B: a ENTREGA (fed funds)
    bx.step([r["dt"] for r in rows] + [hi], [r["mid"] for r in rows] + [rows[-1]["mid"]],
            where="post", color="#6B6B6B", lw=2.4, zorder=3)
    for r in rows:
        bx.scatter([r["dt"]], [r["mid"]], s=70, color=PALETTE[r["member"]],
                   edgecolor="white", linewidth=1.2, zorder=5)
        if r["action"] != "manutenção":
            bx.annotate(r["action"], xy=(r["dt"], r["mid"]), xytext=(0, -24 if r["action"] == "corte" else 16),
                        textcoords="offset points", ha="center", fontsize=9.5,
                        color=PALETTE[r["member"]], fontweight="bold")
    bx.set_ylabel("fed funds — meio da banda (%)", fontsize=11.5, color="#3C4043")
    bx.set_ylim(3.35, 4.65)
    bx.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    bx.set_xlim(lo, hi)

    fig.text(0.008, 0.012,
             "Classificação própria: composite hawk-dove do LLM sobre registry/rubric.json, uma ficha por coletiva, citações verbatim conferidas "
             "contra a transcrição oficial (federalreserve.gov).\nPainel de cima = a mensagem; painel de baixo = a entrega. A coletiva de 29/07/2026 é a única "
             "pontuada na âncora de ENTREGA (pela mensagem ela valeria +3,5) — ver a ressalva na ficha.",
             fontsize=8.6, color="#6B6B6B", va="bottom")
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    out = config.RESULTS_DIR / "presser_composite.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"Powell n={len(pw)} media={m_pw:+.2f} | Warsh n={len(wa)} media={m_wa:+.2f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

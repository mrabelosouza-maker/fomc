"""Assemble the single self-contained interactive HTML.

Plotly figures are embedded inline (first one carries plotly.js). The full
speech corpus + extractions are injected as one JSON blob and rendered/filtered
client-side with vanilla JS, so the file is fully offline.
"""
from __future__ import annotations

import html as _h
import json

from . import config
from .aggregate import MemberFunction


def _emb(fig, first=False) -> str:
    import plotly.io as pio
    return pio.to_html(fig, full_html=False,
                       include_plotlyjs=("inline" if first else False),
                       config={"displayModeBar": False, "responsive": True})


def _bias_pill(bias: dict) -> str:
    d = (bias or {}).get("direction") or "—"
    pace = (bias or {}).get("pace") or ""
    cls = {"cut": "b-cut", "hike": "b-hike", "hold": "b-hold"}.get(d, "b-unk")
    label = {"cut": "corte", "hike": "alta", "hold": "manutenção"}.get(d, d)
    return f"<span class='pill {cls}'>{label}{(' · ' + pace) if pace else ''}</span>"


def _member_payload(mfuncs: dict[str, MemberFunction], corpus, decomp: dict) -> list[dict]:
    """Latest summary + bias per member, plus dims, delta and driver mix."""
    latest: dict[str, object] = {}
    for ex in corpus:
        cur = latest.get(ex.member_id)
        if cur is None or ex.date > cur.date:
            latest[ex.member_id] = ex
    out = []
    for m in mfuncs.values():
        lx = latest.get(m.member_id)
        out.append({
            "member_id": m.member_id, "name": m.name, "title": m.title, "bank": m.bank,
            "voter": m.voter_2026, "composite": m.composite, "insufficient": m.insufficient,
            "latest": m.latest_composite, "baseline": m.baseline_composite,
            "delta": m.delta, "stale": m.stale,
            "n": m.n_speeches, "n_policy": m.n_policy, "n_current": m.n_current,
            "first": m.first_date, "last": m.last_date,
            "dims": m.dims, "dims_hawk": m.dims_hawk, "tone_mean": m.tone_mean,
            "drivers": decomp.get(m.member_id, {}).get("signed", {}),
            "latest_summary": (lx.summary if lx else ""),
            "latest_bias": (lx.llm_scores.get("near_term_bias", {}) if lx else {}),
        })
    out.sort(key=lambda d: (d["insufficient"], -(d["composite"] if d["composite"] is not None else -99)))
    return out


def _speech_payload(corpus, speeches_dir) -> list[dict]:
    out = []
    for ex in corpus:
        md = speeches_dir / f"{ex.speech_id}.md"
        text = md.read_text(encoding="utf-8") if md.exists() else ""
        out.append({
            "id": ex.speech_id, "member_id": ex.member_id, "title": ex.title,
            "date": ex.date, "url": ex.url, "source": ex.source,
            "non_policy": ex.non_policy, "summary": ex.summary,
            "quotes": [{"quote": q.quote, "dimension": q.dimension, "context": q.context}
                       for q in ex.key_quotes],
            "scores": ex.llm_scores, "tone": ex.tone_score, "drivers": ex.drivers, "text": text,
        })
    out.sort(key=lambda d: d["date"], reverse=True)
    return out


def _cards_html(members: list[dict]) -> str:
    cards = []
    for m in members:
        if m["insufficient"]:
            cards.append(
                f"<div class='card ins' data-member='{m['member_id']}'>"
                f"<div class='cname'>{_h.escape(m['name'])}</div>"
                f"<div class='cmeta'>{_h.escape(m['title'])} · {_h.escape(m['bank'])}</div>"
                f"<div class='cins'>sem speech de política desde 2025</div></div>")
            continue
        comp = m["composite"]
        side = "hawk" if (comp or 0) >= 0 else "dove"
        star = " ★" if m["voter"] else ""
        bars = []
        for d in config.DIMENSION_IDS:
            hv = m["dims_hawk"].get(d)
            if hv is None:
                bars.append("<div class='dim'><span class='dl'>—</span></div>")
                continue
            pct = (hv + 1) / 2 * 100
            col = config.HAWK if hv >= 0 else config.DOVE
            bars.append(
                f"<div class='dim' title='{config.DIM_BY_ID[d]['label']}: {hv:+.2f}'>"
                f"<span class='dl'>{config.DIM_BY_ID[d]['label']}</span>"
                f"<span class='dbar'><i style='left:{pct:.0f}%;background:{col}'></i></span></div>")
        voter_cls = " voter" if m["voter"] else ""
        delta = m.get("delta")
        if delta is None:
            delta_badge = ""
        else:
            arrow = "▲" if delta > 0.3 else ("▼" if delta < -0.3 else "▶")
            dcls = "d-hawk" if delta > 0.3 else ("d-dove" if delta < -0.3 else "d-flat")
            lc = m.get("latest")
            delta_badge = (f"<span class='dbadge {dcls}' title='último discurso "
                           f"{(lc if lc is not None else 0):+.1f} vs média dos anteriores "
                           f"{m['baseline']:+.1f}'>Δ {delta:+.1f} {arrow}</span>")
        stale = " · <span class='stale'>defasado</span>" if m.get("stale") else ""
        cards.append(
            f"<div class='card {side}{voter_cls}' data-member='{m['member_id']}'>"
            f"<div class='chead'><span class='cname'>{_h.escape(m['name'])}{star}</span>"
            f"<span class='cbig {side}'>{comp:+.1f}</span></div>"
            f"<div class='cmeta'>{_h.escape(m['title'])} · {_h.escape(m['bank'])} · "
            f"{'votante' if m['voter'] else 'não-votante'} · {m['n']} speeches{stale}</div>"
            f"<div class='cbias'>{delta_badge}</div>"
            f"<div class='cdims'>{''.join(bars)}</div>"
            f"<div class='cgist'>{_h.escape((m['latest_summary'] or '')[:240])}</div>"
            f"<div class='cmore'>ver evolução da postura ▾</div></div>")
    return "\n".join(cards)


def _brief_cls(axis: str, label: str) -> str:
    """Map a brief label to a hawk/dove-tinted badge class."""
    low = (label or "").lower()
    if axis == "inflation":
        if "broaden" in low or "underlying" in low:
            return "bk-hot"
        if "tariff" in low:
            return "bk-warm"
        return "bk-mild"
    if axis == "labor":
        if "downside" in low:
            return "bk-dove"
        if "upside" in low:
            return "bk-hot"
        return "bk-mild"
    if axis == "stance":
        if "restrictive" in low:
            return "bk-warm"
        if "loose" in low or "accommod" in low:
            return "bk-dove"
        return "bk-mild"
    return "bk-mild"


def _briefs_table(members: list[dict], briefs: dict) -> str:
    rows = [m for m in members if not m["insufficient"] and m["member_id"] in briefs]
    # already sorted hawk->dove by _member_payload
    head = ("<tr><th>Membro</th><th>Inflação — só oil / +tarifas / broadening</th>"
            "<th>Mercado de trabalho</th><th>Stance da política</th></tr>")
    body = []
    for m in rows:
        b = briefs[m["member_id"]]
        star = " ★" if m["voter"] else ""
        cells = [f"<td class='bm'>{_h.escape(m['name'])}{star}<br>"
                 f"<span class='bmd'>comp {m['composite']:+.1f} · {b.get('as_of',{}).get('date','')}</span></td>"]
        for axis in ("inflation", "labor", "stance"):
            a = b.get(axis, {})
            label = a.get("label", "—")
            note = _h.escape(a.get("note", ""))
            quote = a.get("quote", "")
            q = f"<div class='bq'>“{_h.escape(quote)}”</div>" if quote else ""
            cells.append(f"<td><span class='bk {_brief_cls(axis, label)}' title='{note}'>"
                         f"{_h.escape(label)}</span>{q}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table class='briefs'><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def _fmt_dm(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}"


def _agenda_html(cal: dict, members: list[dict]) -> str:
    info = {m["member_id"]: m for m in members}
    rows = []
    for ev in cal.get("events", []):
        kind = ev.get("kind", "speech")
        if ev.get("date_end"):
            when = f"{_fmt_dm(ev['date'])}–{_fmt_dm(ev['date_end'])}"
        else:
            when = _fmt_dm(ev["date"]) + (f" {ev['time']}" if ev.get("time") else "")
        cls = {"key": "key", "blackout": "blackout"}.get(kind, "")
        if kind == "speech" and ev.get("member_id") in info:
            m = info[ev["member_id"]]
            label = f"<b>{_h.escape(m['name'].split()[-1])}</b> — {_h.escape(ev['title'])}"
            tag = ("<span class='evtag v'>votante</span>" if m["voter"]
                   else "<span class='evtag'>não-votante</span>")
        else:
            label = _h.escape(ev["title"])
            tag = ("<span class='evtag'>blackout</span>" if kind == "blackout"
                   else "<span class='evtag'>evento</span>")
        rows.append(f"<div class='ev {cls}'><span class='evd'>{when}</span>"
                    f"<span class='evt'>{label}</span>{tag}</div>")
    return f"<div class='agenda'>{''.join(rows)}</div>"


def build_page(mfuncs, medians, evo, corpus, roster, figs, meta, decomp, briefs, calendar) -> str:
    members = _member_payload(mfuncs, corpus, decomp)
    speeches = _speech_payload(corpus, config.SPEECHES_DIR)
    data = {"members": members, "speeches": speeches,
            "dimensions": [{"id": d["id"], "label": d["label"]} for d in config.DIMENSIONS],
            "drivers": [{"id": d["id"], "label": d["label"], "color": d["color"]} for d in config.DRIVERS],
            "meta": meta}

    page = TEMPLATE
    page = page.replace("<!--CARDS-->", _cards_html(members))
    page = page.replace("<!--AGENDA-->", _agenda_html(calendar, members))
    page = page.replace("<!--BRIEFS-->", _briefs_table(members, briefs))
    page = page.replace("<!--RANKING-->", _emb(figs["ranking"], first=True))
    page = page.replace("<!--MOMENTUM-->", _emb(figs["momentum"]))
    page = page.replace("<!--EXOIL-->", _emb(figs["exoil"]))
    page = page.replace("<!--EXOILVOTERS-->", _emb(figs["exoil_voters"]))
    page = page.replace("<!--VOTERSTRIP-->", _emb(figs["voterstrip"]))
    page = page.replace("<!--DRIVERS-->", _emb(figs["drivers"]))
    page = page.replace("<!--DRIVERDELTA-->", _emb(figs["driverdelta"]))
    page = page.replace("<!--RADAR-->", _emb(figs["radar"]))
    page = page.replace("<!--HEATMAP-->", _emb(figs["heatmap"]))
    page = page.replace("<!--EVOLUTION-->", _emb(figs["evolution"]))
    page = page.replace("<!--TONE-->", _emb(figs["tone"]))
    page = page.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    rib = meta.get("ribbon", {})
    page = page.replace("__ASOF__", meta.get("asof", ""))
    page = page.replace("__WINDOW__", meta.get("window", ""))
    page = page.replace("__NSPEECH__", str(meta.get("n_speeches", 0)))
    page = page.replace("__NMEMB__", str(meta.get("n_members", 0)))
    page = page.replace("__RIBBON__", _ribbon_html(rib))
    return page


def _ribbon_html(rib: dict) -> str:
    bits = []
    if "funds" in rib:
        bits.append(f"funds <b>{rib['funds']['value']:.2f}%</b>")
    if "core_pce_yoy" in rib:
        bits.append(f"core PCE YoY <b>{rib['core_pce_yoy']['value']:.2f}%</b>")
    if "unrate" in rib:
        bits.append(f"desemprego <b>{rib['unrate']['value']:.1f}%</b>")
    return " · ".join(bits) if bits else "macro indisponível"


TEMPLATE = r"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funções de reação do FOMC</title>
<style>
 body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;color:#1a1a1a;background:#eef0f4;line-height:1.45}
 header{background:#16213e;color:#fff;padding:24px 40px;border-bottom:4px solid #c8920a}
 header h1{margin:0 0 6px;font-size:24px}
 header p{margin:3px 0;opacity:.9;font-size:13px;max-width:1050px}
 main{max-width:1240px;margin:0 auto;padding:18px 22px 80px}
 section{background:#fff;border:1px solid #e0e3e9;border-radius:11px;padding:16px 20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
 h2{font-size:18px;margin:0 0 4px;color:#16213e}
 .desc{font-size:13px;color:#555;margin:0 0 12px;max-width:980px}
 /* member cards */
 .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(255px,1fr));gap:12px}
 .card{border:1px solid #e0e3e9;border-radius:10px;padding:12px 14px;background:#fafbfc;cursor:pointer;transition:.12s}
 .card:hover{box-shadow:0 2px 10px rgba(0,0,0,.12);transform:translateY(-1px)}
 .card.voter{border-left:5px solid #c8920a}
 .card.ins{opacity:.55;background:#f3f4f7;cursor:default}
 .chead{display:flex;justify-content:space-between;align-items:baseline}
 .cname{font-weight:700;color:#16213e;font-size:14.5px}
 .cbig{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums}
 .cbig.hawk{color:#c0392b}.cbig.dove{color:#1e7d8c}
 .cmeta{font-size:11.5px;color:#777;margin:3px 0 7px}
 .cins{font-size:12px;color:#999;font-style:italic}
 .pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:11px;font-weight:600}
 .b-cut{background:#dcefef;color:#0f6674}.b-hike{background:#fadbd8;color:#a93226}
 .b-hold{background:#eceff4;color:#445}.b-unk{background:#eee;color:#777}
 .dbadge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:11px;font-weight:700;margin-left:4px}
 .d-hawk{background:#fadbd8;color:#a93226}.d-dove{background:#d6eef1;color:#0f6674}.d-flat{background:#eee;color:#777}
 .stale{color:#b08900;font-weight:600}
 .drv{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;margin:2px 4px 2px 0;color:#fff}
 /* briefs table */
 table.briefs{border-collapse:collapse;width:100%;font-size:12.5px}
 table.briefs th{background:#16213e;color:#fff;font-weight:600;text-align:left;padding:8px 10px;font-size:11.5px}
 table.briefs td{border-bottom:1px solid #eceef2;padding:9px 10px;vertical-align:top}
 table.briefs td.bm{font-weight:700;color:#16213e;white-space:nowrap}
 table.briefs .bmd{font-weight:400;font-size:10.5px;color:#999}
 .bk{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:11px}
 .bk-hot{background:#fadbd8;color:#a93226}.bk-warm{background:#f6e3c8;color:#8a5a0f}
 .bk-mild{background:#eceff4;color:#445}.bk-dove{background:#d6eef1;color:#0f6674}
 .bq{font-size:11.5px;color:#555;font-style:italic;margin-top:5px;line-height:1.35}
 /* calendar */
 .agenda{display:flex;flex-direction:column;gap:0}
 .ev{display:grid;grid-template-columns:88px 1fr auto;gap:12px;align-items:center;padding:7px 12px;border-bottom:1px solid #eceef2;font-size:13px}
 .ev .evd{font-variant-numeric:tabular-nums;color:#16213e;font-weight:700;white-space:nowrap}
 .ev .evt{color:#333}
 .ev .evtag{font-size:10.5px;padding:2px 8px;border-radius:10px;background:#eceff4;color:#556;white-space:nowrap}
 .ev .evtag.v{background:#c8920a;color:#fff}
 .ev.key{background:#fbf7ec}
 .ev.blackout{background:#fbeaea}
 .ev.blackout .evd,.ev.blackout .evt{color:#a93226;font-weight:700}
 .cdims{margin:9px 0 6px}
 .dim{display:flex;align-items:center;gap:7px;margin:3px 0}
 .dl{font-size:10px;color:#888;width:110px;text-align:right;flex:none}
 .dbar{position:relative;height:6px;background:#e6e8ee;border-radius:4px;flex:1}
 .dbar i{position:absolute;top:-2px;width:8px;height:10px;border-radius:2px;transform:translateX(-50%)}
 .cgist{font-size:11.5px;color:#555;margin:6px 0 4px;max-height:48px;overflow:hidden}
 .cmore{font-size:11px;color:#c8920a;font-weight:600}
 .legend{font-size:12.5px;color:#3a3a3a;background:#f4f6fa;border-left:4px solid #c8920a;padding:10px 14px;border-radius:8px;margin:0 0 12px}
 /* speech browser */
 .filters{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
 .filters select,.filters input{font-size:13px;padding:6px 9px;border:1px solid #cdd2db;border-radius:7px}
 .filters input[type=search]{min-width:220px}
 .chk{font-size:13px;color:#16213e}
 .slist{max-height:620px;overflow:auto;border:1px solid #eceef2;border-radius:8px}
 .sitem{border-bottom:1px solid #eceef2;padding:10px 14px}
 .sitem .sh{display:flex;justify-content:space-between;gap:12px;cursor:pointer}
 .sitem .st{font-weight:600;color:#16213e;font-size:13.5px}
 .sitem .sm{font-size:11.5px;color:#888;white-space:nowrap}
 .sitem .badge{font-size:10px;padding:1px 7px;border-radius:9px;background:#eceff4;color:#556;margin-left:6px}
 .sitem .badge.np{background:#f6ecd9;color:#8a6d18}
 .sbody{display:none;margin-top:9px;font-size:13px;color:#333}
 .sbody.open{display:block}
 .sbody .sum{background:#f4f6fa;border-left:3px solid #c8920a;padding:8px 12px;border-radius:6px;margin:6px 0}
 .sbody .q{border-left:3px solid #16213e;padding:4px 11px;margin:6px 0;color:#222;font-style:italic}
 .sbody .q small{color:#888;font-style:normal}
 .sbody .scores{font-size:11.5px;color:#555;margin:8px 0}
 .sbody .scores code{background:#eef0f4;padding:1px 6px;border-radius:4px;margin-right:5px}
 .sbody .full{white-space:pre-wrap;background:#fbfbfc;border:1px solid #eceef2;border-radius:7px;padding:11px 13px;max-height:340px;overflow:auto;font-size:12.5px;color:#333;margin-top:8px}
 .sbody a{color:#16213e}
 .toggle-full{font-size:11.5px;color:#c8920a;cursor:pointer;font-weight:600;margin-top:6px;display:inline-block}
 .note{font-size:11.5px;color:#888;margin-top:24px}
 .note code{background:#eef0f4;padding:1px 4px;border-radius:3px}
 /* per-member evolution modal */
 .modal{position:fixed;inset:0;background:rgba(22,33,62,.55);display:none;align-items:center;justify-content:center;z-index:50}
 .modal.open{display:flex}
 .modal .box{background:#fff;border-radius:12px;max-width:880px;width:92%;padding:18px 24px 20px;box-shadow:0 12px 44px rgba(0,0,0,.3);position:relative}
 .modal .mtitle{font-size:18px;font-weight:700;color:#16213e;margin:0 26px 2px 0}
 .modal .msub{font-size:12px;color:#777;margin:0 0 8px}
 .modal .mclose{position:absolute;top:10px;right:14px;font-size:24px;color:#999;cursor:pointer;line-height:1;border:none;background:none;padding:0}
 .modal .mclose:hover{color:#333}
 .modal .mlink{font-size:12px;color:#c8920a;font-weight:600;cursor:pointer;margin-top:6px;display:inline-block}
 .modal .mlink:hover{text-decoration:underline}
</style></head><body>
<header>
 <h1>Funções de reação do FOMC — por membro, votantes vs não-votantes</h1>
 <p>Leitura individual da função de reação de política monetária de cada participante do FOMC, extraída dos seus discursos (__WINDOW__). ★ = votante em 2026. Hawk (vermelho) = inclinação a juros mais altos / mais preocupado com inflação; dove (azul) = inclinação a cortes / mais preocupado com emprego.</p>
 <p style="opacity:.82">Dados até <b>__ASOF__</b> · __RIBBON__ · __NSPEECH__ speeches · __NMEMB__ membros. Scores extraídos por LLM (rubrica versionada) com cross-check de tom por dicionário. Clique num card para ver a evolução histórica da postura do membro.</p>
</header>
<main>

 <section>
  <h2>📅 Agenda do Fed — próximos eventos</h2>
  <p class="desc">Próximas falas e eventos do Fed (fonte: Bloomberg). ★ por votante; em vermelho o período de <b>blackout</b> de comunicação pré-FOMC.</p>
  <!--AGENDA-->
 </section>

 <section>
  <h2>1 · Função de reação atual de cada membro</h2>
  <p class="desc">Ordenado do mais hawkish ao mais dovish. O número grande é o composite hawk-dove <b>atual</b> (janela recente de ~4 meses, ponderada por recência) — não a média de toda a história, para que viradas de regime apareçam. O badge <b>Δ</b> mostra a mudança na margem = <b>último discurso − média dos discursos anteriores</b>. As barras mostram cada dimensão na escala hawk(→)/dove(←).</p>
  <div class="cards"><!--CARDS--></div>
 </section>

 <section>
  <h2>2 · O que cada votante pensa — inflação · trabalho · stance</h2>
  <p class="desc">Leitura dos <b>votantes 2026</b> no discurso de política mais recente de cada um, em três eixos, com trechos curtos verbatim. <b>Inflação:</b> é só oil/energia, oil + tarifas, ou já um <i>broadening</i>/subjacente além disso? <b>Trabalho:</b> estável, com riscos baixistas, ou altistas? <b>Stance:</b> como ele descreve a política hoje (apropriada / well positioned / modestamente restritiva / neutra / frouxa). Ordenado do mais hawkish ao mais dovish.</p>
  <!--BRIEFS-->
 </section>

 <section>
  <h2>3 · Ranking hawk-dove (stance atual)</h2>
  <p class="desc">Composite atual por membro (janela recente); ★ votantes em cor cheia, não-votantes esmaecidos. Linhas: mediana dos votantes (dourada) e de todos (navy).</p>
  <!--RANKING-->
 </section>

 <section>
  <h2>4 · Momentum na margem — quem está virando hawkish</h2>
  <p class="desc">Para cada membro, da <b>média dos discursos anteriores</b> (círculo aberto) até o <b>discurso mais recente</b> (ponto cheio). Linha vermelha = giro hawkish na margem; azul = giro dovish. O número é o Δ = último − média. É aqui que viradas de regime (ex.: Waller em "Policy Risks Have Changed") aparecem mesmo quando a média ainda parece dovish.</p>
  <!--MOMENTUM-->
 </section>

 <section>
  <h2>5 · Hawk-dove SEM o choque de oil/guerra (contrafactual)</h2>
  <p class="desc">Onde cada membro estaria na escala se removêssemos a contribuição atual do driver <b>oil/guerra</b>. Ponto cheio (navy) = stance atual <i>com</i> oil; ponto aberto = <i>sem</i> oil. Como o composite é um score holístico do LLM (não soma de drivers), estimamos "pontos de composite por unidade de intensidade de driver" por mínimos quadrados (composite atual vs net de drivers) e descontamos a parcela de oil/guerra. Ordenado pela posição sem oil.</p>
  <p class="desc" style="margin-top:6px"><b>Todos os membros:</b></p>
  <!--EXOIL-->
  <p class="desc" style="margin-top:14px"><b>Apenas votantes 2026:</b></p>
  <!--EXOILVOTERS-->
 </section>

 <section>
  <h2>6 · Votantes vs não-votantes na escala</h2>
  <p class="desc">Onde cada membro cai na escala hawk-dove (stance atual), separado por status de voto em 2026. Losango = mediana do grupo. Mostra se o comitê que decide está mais hawkish/dovish que o resto. A linha de baixo (★) posiciona o Chair Warsh a partir da 1ª coletiva (17/06/2026) — fora dos medians do corpus de discursos; barra = faixa de incerteza.</p>
  <!--VOTERSTRIP-->
 </section>

 <section>
  <h2>7 · Por que — decomposição por driver (nível e delta)</h2>
  <p class="desc">Escala em <b>pontos de composite hawk-dove</b> (a intensidade de cada driver é convertida pelo fator b₁ ≈ 0,21 pt por unidade, o mesmo do contrafactual ex-oil), então a soma empilhada ≈ o composite (nível) / a variação do composite (delta). Não é a soma bruta de intensidades.<br><b>Nível (em cima):</b> o que empurra a postura atual — direita hawkish, esquerda dovish, por driver. <b>Delta (embaixo):</b> o que <i>mudou na margem</i> = contribuição no <b>discurso mais recente</b> menos a <b>média dos discursos anteriores</b>, por driver — quais forças ficaram mais hawkish/dovish e impulsionaram a virada.</p>
  <p class="desc" style="margin-top:6px"><b>Nível — composição da postura atual (janela recente):</b></p>
  <!--DRIVERS-->
  <p class="desc" style="margin-top:14px"><b>Delta na margem (último discurso − média dos anteriores), por driver:</b></p>
  <!--DRIVERDELTA-->
 </section>

 <section>
  <h2>8 · Funções de reação medianas — votantes vs não-votantes vs todos</h2>
  <p class="desc">Mediana por dimensão, normalizada ao eixo hawk(+1)/dove(−1). O comitê que decide (votantes) vs o resto.</p>
  <!--RADAR-->
 </section>

 <section>
  <h2>9 · Mapa membros × dimensões</h2>
  <p class="desc">Cada célula na escala hawk(vermelho)/dove(azul). ★ votantes.</p>
  <!--HEATMAP-->
 </section>

 <section>
  <h2>10 · Evolução no tempo</h2>
  <p class="desc">Trajetória do composite por membro (cinza) e medianas (votantes/todos) desde 2025, ponderadas por recência a cada mês.</p>
  <!--EVOLUTION-->
 </section>

 <section>
  <h2>11 · Cross-check: LLM × tom léxico</h2>
  <p class="desc">Cada ponto é um speech. Concordância esperada no eixo diagonal; outliers fora dela merecem revisão (o léxico nunca sobrescreve o LLM).</p>
  <!--TONE-->
 </section>

 <section>
  <h2>12 · Base de discursos</h2>
  <p class="desc">Todos os discursos coletados. Filtre e clique para abrir resumo, citações, scores e o texto completo.</p>
  <div class="filters">
   <select id="fMember"><option value="">Todos os membros</option></select>
   <label class="chk"><input type="checkbox" id="fVoter"> só votantes</label>
   <label class="chk"><input type="checkbox" id="fPolicy"> só política</label>
   <select id="fTheme"><option value="">Todos os temas</option></select>
   <input type="search" id="fSearch" placeholder="buscar no texto...">
   <span id="fCount" class="cmeta"></span>
  </div>
  <div id="slist" class="slist"></div>
 </section>

 <p class="note">Reprodutibilidade: o HTML é função determinística de <code>data/extracted/</code> via <code>python scripts/run_deterministic.py</code>. A coleta e extração (LLM) são feitas por agentes Claude Code e cacheadas por discurso. Rubrica: <code>registry/rubric.json</code>.</p>
</main>
<div id="evoModal" class="modal"><div class="box">
 <button class="mclose" id="evoClose" title="fechar (Esc)">×</button>
 <div class="mtitle" id="evoName"></div>
 <div class="msub" id="evoSub"></div>
 <div id="evoChart" style="height:380px"></div>
 <span class="mlink" id="evoSpeeches">ver discursos deste membro na base ▾</span>
</div></div>
<script>
const DATA = /*__DATA__*/;
const SP = DATA.speeches, MB = DATA.members;
const byId = Object.fromEntries(MB.map(m=>[m.member_id,m]));
const DIMLBL = Object.fromEntries(DATA.dimensions.map(d=>[d.id,d.label]));
const DRV = Object.fromEntries((DATA.drivers||[]).map(d=>[d.id,d]));
const BIAS = {cut:"corte",hike:"alta",hold:"manutenção",unclear:"indefinido"};
const PUSHARR = {hawkish:"▲ hawk",dovish:"▼ dove",neutral:"▶ neutro"};
function driversHtml(s){
  if(!s.drivers) return '';
  let chips='';
  (DATA.drivers||[]).forEach(d=>{
    const v=s.drivers[d.id]; if(!v||!v.intensity) return;
    const op = v.push==='hawkish'?1 : (v.push==='dovish'?0.5:0.32);
    chips+=`<span class="drv" style="background:${d.color};opacity:${op}" title="intensidade ${v.intensity}/3 · ${v.push}">${d.label} ${'•'.repeat(v.intensity)} ${PUSHARR[v.push]||''}</span>`;
  });
  return chips?`<div class="scores"><b style="font-size:11px;color:#666">drivers da postura:</b><br>${chips}</div>`:'';
}

// populate filters
const fMember=document.getElementById('fMember'), fTheme=document.getElementById('fTheme');
[...MB].filter(m=>m.n>0).sort((a,b)=>a.name.localeCompare(b.name)).forEach(m=>{
  const o=document.createElement('option');o.value=m.member_id;o.textContent=m.name+(m.voter?' ★':'');fMember.appendChild(o);});
const themes=new Set();SP.forEach(s=>(s.scores.theme_flags||[]).forEach(t=>themes.add(t)));
[...themes].sort().forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;fTheme.appendChild(o);});

function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function scoresHtml(s){
  let out='';
  DATA.dimensions.forEach(d=>{const v=s.scores[d.id];if(v!==undefined&&v!==null)out+=`<code>${d.label}: ${v}</code>`;});
  const b=s.scores.near_term_bias;if(b&&b.direction)out+=`<code>viés: ${BIAS[b.direction]||b.direction}${b.pace?(' / '+b.pace):''}</code>`;
  if(s.tone&&s.tone.net_tone!==undefined)out+=`<code>tom léxico: ${s.tone.net_tone}</code>`;
  return out;
}
function speechHtml(s){
  const m=byId[s.member_id]||{name:s.member_id};
  const quotes=(s.quotes||[]).map(q=>`<div class="q">“${esc(q.quote)}”<br><small>${esc(DIMLBL[q.dimension]||q.dimension)}${q.context?(' — '+esc(q.context)):''}</small></div>`).join('');
  return `<div class="sitem" data-id="${s.id}">
   <div class="sh" onclick="this.parentNode.querySelector('.sbody').classList.toggle('open')">
    <div><span class="st">${esc(s.title)}</span>
     <span class="badge">${esc(m.name)}${m.voter?' ★':''}</span>
     ${s.non_policy?'<span class="badge np">não-política</span>':''}</div>
    <div class="sm">${s.date}</div></div>
   <div class="sbody">
    <div class="sum">${esc(s.summary)}</div>
    ${quotes}
    ${driversHtml(s)}
    <div class="scores">${scoresHtml(s)}</div>
    ${s.url?`<a href="${esc(s.url)}" target="_blank">abrir original ↗</a>`:''}
    <div class="toggle-full" onclick="const f=this.nextElementSibling;f.style.display=f.style.display==='block'?'none':'block'">texto completo ▾</div>
    <div class="full" style="display:none">${esc(s.text)}</div>
   </div></div>`;
}
function render(){
  const mem=fMember.value, onlyV=document.getElementById('fVoter').checked,
        onlyP=document.getElementById('fPolicy').checked, th=fTheme.value,
        q=document.getElementById('fSearch').value.toLowerCase();
  const rows=SP.filter(s=>{
    if(mem&&s.member_id!==mem)return false;
    if(onlyV&&!(byId[s.member_id]||{}).voter)return false;
    if(onlyP&&s.non_policy)return false;
    if(th&&!(s.scores.theme_flags||[]).includes(th))return false;
    if(q&&!((s.title+' '+s.summary+' '+s.text).toLowerCase().includes(q)))return false;
    return true;});
  document.getElementById('slist').innerHTML=rows.map(speechHtml).join('')||'<div class="sitem">nenhum discurso</div>';
  document.getElementById('fCount').textContent=rows.length+' de '+SP.length;
}
['fMember','fVoter','fPolicy','fTheme','fSearch'].forEach(id=>{
  const el=document.getElementById(id);el.addEventListener(id==='fSearch'?'input':'change',render);});
// --- per-member stance-evolution modal ---
const evoModal=document.getElementById('evoModal');
function filterToMember(mid){
  fMember.value=mid;render();
  document.getElementById('slist').scrollIntoView({behavior:'smooth',block:'center'});
}
function openEvo(mid){
  const m=byId[mid]; if(!m)return;
  const rows=SP.filter(s=>s.member_id===mid && s.scores && s.scores.composite_hawk_dove!=null)
              .slice().sort((a,b)=>a.date<b.date?-1:1);
  evoModal.dataset.member=mid;
  document.getElementById('evoName').textContent=m.name+(m.voter?' ★':'');
  if(!rows.length){
    document.getElementById('evoSub').textContent='Sem discursos com composite para este membro.';
    Plotly.purge('evoChart');evoModal.classList.add('open');return;
  }
  const x=rows.map(s=>s.date), y=rows.map(s=>s.scores.composite_hawk_dove);
  const colors=y.map(v=>v>=0?'#c0392b':'#1e7d8c');
  const text=rows.map(s=>`<b>${esc(s.title)}</b><br>${s.date} · composite ${s.scores.composite_hawk_dove>=0?'+':''}${s.scores.composite_hawk_dove}${s.non_policy?' · não-política':''}`);
  document.getElementById('evoSub').textContent=
    `${m.title} · ${m.bank} · ${m.voter?'votante':'não-votante'} — composite hawk-dove por discurso (${rows.length} pontos, ${x[0]} → ${x[x.length-1]})`;
  const trace={x,y,mode:'lines+markers',type:'scatter',line:{color:'#16213e',width:2,shape:'linear'},
    marker:{size:9,color:colors,line:{color:'#fff',width:1}},
    text,hovertemplate:'%{text}<extra></extra>'};
  const layout={margin:{l:46,r:18,t:8,b:34},height:380,
    yaxis:{title:'hawk (+) / dove (−)',range:[-5,5],zeroline:false,gridcolor:'#eee'},
    xaxis:{type:'date',gridcolor:'#f4f4f4'},
    shapes:[{type:'line',xref:'paper',x0:0,x1:1,y0:0,y1:0,line:{color:'#999',width:1,dash:'dot'}}],
    plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{family:'Segoe UI,Arial',size:12},showlegend:false};
  evoModal.classList.add('open');
  Plotly.newPlot('evoChart',[trace],layout,{displayModeBar:false,responsive:true});
}
function closeEvo(){evoModal.classList.remove('open');}
document.getElementById('evoClose').addEventListener('click',closeEvo);
evoModal.addEventListener('click',e=>{if(e.target===evoModal)closeEvo();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeEvo();});
document.getElementById('evoSpeeches').addEventListener('click',()=>{
  const mid=evoModal.dataset.member;closeEvo();if(mid)filterToMember(mid);});
// card click -> open the member's stance-evolution chart
document.querySelectorAll('.card[data-member]').forEach(c=>{
  if(c.classList.contains('ins'))return;
  c.addEventListener('click',()=>openEvo(c.dataset.member));
});
render();
</script>
</body></html>"""

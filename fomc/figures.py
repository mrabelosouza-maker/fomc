"""Plotly figures. Each returns a go.Figure; html.py embeds them inline."""
from __future__ import annotations

import statistics

import plotly.graph_objects as go

from . import config
from .aggregate import MemberFunction

_LAYOUT = dict(
    font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", size=13, color=config.INK),
    paper_bgcolor="white", plot_bgcolor="white",
    margin=dict(l=60, r=24, t=30, b=40),
)


def _short(name: str) -> str:
    parts = name.split()
    return parts[-1] if parts else name


def fig_ranking(mfuncs: dict[str, MemberFunction], medians: dict) -> go.Figure:
    """Horizontal bars: composite hawk-dove per member, voters highlighted."""
    members = [m for m in mfuncs.values() if not m.insufficient and m.composite is not None]
    members.sort(key=lambda m: m.composite)
    names = [f"{_short(m.name)}{' ★' if m.voter_2026 else ''}" for m in members]
    vals = [m.composite for m in members]
    colors = [config.HAWK if m.voter_2026 else "#c98b86" for m in members]
    # voters in solid hawk/dove tone; non-voters muted
    colors = []
    for m in members:
        base = config.HAWK if m.composite >= 0 else config.DOVE
        colors.append(base if m.voter_2026 else _fade(base))
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h", marker_color=colors,
        text=[f"{v:+.1f}" for v in vals], textposition="outside",
        hovertemplate="%{y}: %{x:+.2f}<extra></extra>",
    ))
    mv = medians.get("voters", {}).get("composite_hawk_dove")
    ma = medians.get("all", {}).get("composite_hawk_dove")
    if mv is not None:
        fig.add_vline(x=mv, line=dict(color=config.GOLD, width=2, dash="dash"),
                      annotation_text=f"mediana votantes {mv:+.1f}", annotation_position="top")
    if ma is not None:
        fig.add_vline(x=ma, line=dict(color=config.NAVY, width=1.5, dash="dot"),
                      annotation_text=f"mediana todos {ma:+.1f}", annotation_position="bottom")
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_layout(**_LAYOUT, height=max(360, 22 * len(members) + 80),
                      xaxis_title="← dovish      composite hawk-dove      hawkish →")
    return fig


def fig_momentum(mfuncs: dict[str, MemberFunction]) -> go.Figure:
    """Dumbbell: mean of prior speeches -> most recent speech composite, per
    member, sorted by the marginal shift (latest - mean). Surfaces regime changes
    a trailing average hides."""
    movers = [m for m in mfuncs.values() if m.delta is not None]
    movers.sort(key=lambda m: m.delta)
    fig = go.Figure()
    for m in movers:
        col = config.HAWK if m.delta >= 0 else config.DOVE
        nm = f"{_short(m.name)}{' ★' if m.voter_2026 else ''}"
        fig.add_trace(go.Scatter(
            x=[m.baseline_composite, m.latest_composite], y=[nm, nm], mode="lines",
            line=dict(color=col, width=3), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=[m.latest_composite], y=[nm], mode="markers+text",
            marker=dict(color=col, size=12, line=dict(color="white", width=1)),
            text=[f" {m.delta:+.1f}"], textposition="middle right",
            textfont=dict(color=col, size=11), showlegend=False,
            hovertemplate=f"{nm}<br>último discurso {m.latest_composite:+.2f} "
                          f"vs média anterior {m.baseline_composite:+.2f} · Δ {m.delta:+.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(color="white", size=10, line=dict(color="#999", width=1.5)),
                             name="média dos anteriores"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(color=config.NAVY, size=11), name="discurso mais recente"))
    for m in movers:
        nm = f"{_short(m.name)}{' ★' if m.voter_2026 else ''}"
        fig.add_trace(go.Scatter(x=[m.baseline_composite], y=[nm], mode="markers",
                                 marker=dict(color="white", size=10, line=dict(color="#999", width=1.5)),
                                 showlegend=False, hoverinfo="skip"))
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_layout(**_LAYOUT, height=max(380, 26 * len(movers) + 90),
                      xaxis_title="← dovish     composite (média anterior → último discurso)     hawkish →",
                      legend=dict(orientation="h", y=-0.1))
    return fig


def fig_driver_decomp(mfuncs: dict[str, MemberFunction], decomp: dict, b1: float = 1.0) -> go.Figure:
    """Stacked diverging bars: what is pushing each member hawkish (right) vs
    dovish (left) right now, by driver, expressed in composite points (driver
    intensity × b1) so the stacked net ≈ the hawk-dove composite."""
    members = [m for m in mfuncs.values()
               if not m.insufficient and decomp.get(m.member_id, {}).get("has_drivers")]
    members.sort(key=lambda m: decomp[m.member_id]["net"])
    ylab = [f"{_short(m.name)}{' ★' if m.voter_2026 else ''}" for m in members]
    fig = go.Figure()
    for d in config.DRIVERS:
        xs = [round(decomp[m.member_id]["signed"].get(d["id"], 0.0) * b1, 3) for m in members]
        fig.add_trace(go.Bar(
            y=ylab, x=xs, name=d["label"], orientation="h",
            marker_color=d["color"],
            hovertemplate="%{y} · " + d["label"] + ": %{x:+.2f} pts<extra></extra>"))
    fig.add_vline(x=0, line=dict(color="#888", width=1))
    fig.update_layout(**_LAYOUT, barmode="relative",
                      height=max(380, 26 * len(members) + 110),
                      xaxis_title="← dovish     contribuição estimada ao composite (pts hawk-dove)     hawkish →",
                      legend=dict(orientation="h", y=-0.12, font=dict(size=11)))
    return fig


def fig_ex_oil(mfuncs: dict[str, MemberFunction], exoil: dict, b1: float,
               voters_only: bool = False) -> go.Figure:
    """Counterfactual: where each member sits on the hawk-dove scale WITH the
    current oil/war contribution (filled dot) vs WITHOUT it (open dot)."""
    rows = [(mid, mfuncs[mid]) for mid in exoil if not voters_only or mfuncs[mid].voter_2026]
    rows.sort(key=lambda r: exoil[r[0]]["ex_oil"])
    fig = go.Figure()
    for mid, m in rows:
        e = exoil[mid]
        nm = f"{_short(m.name)}{' ★' if m.voter_2026 else ''}"
        moves_hawk = e["composite"] >= e["ex_oil"]
        col = config.HAWK if moves_hawk else config.DOVE
        fig.add_trace(go.Scatter(x=[e["ex_oil"], e["composite"]], y=[nm, nm], mode="lines",
                                 line=dict(color=col, width=3), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=[e["composite"]], y=[nm], mode="markers",
            marker=dict(color=config.NAVY, size=11),
            showlegend=False,
            hovertemplate=f"{nm}<br>com oil/guerra (atual): {e['composite']:+.2f}<br>"
                          f"sem oil/guerra: {e['ex_oil']:+.2f}<br>oil adiciona {e['oil_points']:+.2f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[e["ex_oil"]], y=[nm], mode="markers",
            marker=dict(color="white", size=11, line=dict(color=col, width=2)),
            showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(color=config.NAVY, size=11), name="com oil/guerra (atual)"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(color="white", size=11, line=dict(color="#999", width=2)),
                             name="sem oil/guerra"))
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_layout(**_LAYOUT, height=max(380, 26 * len(rows) + 100),
                      xaxis_title="← dovish     composite hawk-dove     hawkish →",
                      legend=dict(orientation="h", y=-0.1))
    return fig


def fig_voter_strip(mfuncs: dict[str, MemberFunction]) -> go.Figure:
    """Hawk-dove scale split into voters vs non-voters: each member a dot, with the
    group median marked."""
    groups = [("Votantes 2026", True, config.GOLD), ("Não-votantes", False, "#5b6472")]
    fig = go.Figure()
    yticks, ylabels = [], []
    for gi, (label, is_voter, color) in enumerate(groups):
        members = [m for m in mfuncs.values()
                   if not m.insufficient and m.composite is not None and m.voter_2026 == is_voter]
        members.sort(key=lambda m: m.composite)
        base = gi * 2.0
        yticks.append(base); ylabels.append(f"{label}<br>(n={len(members)})")
        # deterministic vertical spread to de-overlap
        for j, m in enumerate(members):
            off = ((j % 5) - 2) * 0.13
            fig.add_trace(go.Scatter(
                x=[m.composite], y=[base + off], mode="markers+text",
                marker=dict(color=color, size=12, line=dict(color="white", width=1)),
                text=[_short(m.name)], textposition="top center", textfont=dict(size=9),
                showlegend=False,
                hovertemplate=f"{m.name} ({'votante' if is_voter else 'não-votante'}): %{{x:+.2f}}<extra></extra>"))
        if members:
            med = statistics.median([m.composite for m in members])
            fig.add_trace(go.Scatter(
                x=[med], y=[base], mode="markers", marker=dict(color=color, size=20, symbol="diamond",
                line=dict(color="#333", width=1.5)), showlegend=False,
                hovertemplate=f"mediana {label}: {med:+.2f}<extra></extra>"))
    # Chair Warsh: a separate row BELOW the two corpus groups (his read comes from the
    # press conference, not the speech corpus — see config.CHAIR_PLACEMENT).
    cp = config.CHAIR_PLACEMENT
    chair_base = -2.0
    yticks.append(chair_base)
    ylabels.append(f"Chair Warsh<br><span style='font-size:9px'>{cp['source']}</span>")
    fig.add_trace(go.Scatter(  # uncertainty range +2.5..+3.5
        x=[cp["lo"], cp["hi"]], y=[chair_base, chair_base], mode="lines",
        line=dict(color=config.HAWK, width=3), showlegend=False,
        hovertemplate=f"faixa {cp['lo']:+.1f} a {cp['hi']:+.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[cp["composite"]], y=[chair_base], mode="markers+text",
        marker=dict(color=config.HAWK, size=18, symbol="star", line=dict(color="white", width=1.2)),
        text=[f"Warsh {cp['composite']:+.1f}"], textposition="top center",
        textfont=dict(size=10, color=config.HAWK), showlegend=False,
        hovertemplate=f"Chair Warsh ({cp['source']}): {cp['composite']:+.2f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_layout(**_LAYOUT, height=420,
                      xaxis_title="← dovish     composite hawk-dove (stance atual)     hawkish →",
                      yaxis=dict(tickvals=yticks, ticktext=ylabels, range=[-3, 3]))
    return fig


def fig_driver_delta(mfuncs: dict[str, MemberFunction], decomp: dict, b1: float = 1.0) -> go.Figure:
    """Stacked diverging bars of the DELTA in each driver (current − baseline),
    in composite points (× b1): what got more hawkish (right) / dovish (left) on
    the margin, by driver. The stacked net ≈ the member's composite delta."""
    members = [m for m in mfuncs.values()
               if not m.insufficient and decomp.get(m.member_id, {}).get("has_baseline")]
    members.sort(key=lambda m: (m.delta if m.delta is not None else 0))
    ylab = [f"{_short(m.name)}{' ★' if m.voter_2026 else ''}" for m in members]
    fig = go.Figure()
    for d in config.DRIVERS:
        xs = [round(decomp[m.member_id]["delta"].get(d["id"], 0.0) * b1, 3) for m in members]
        fig.add_trace(go.Bar(y=ylab, x=xs, name=d["label"], orientation="h",
                             marker_color=d["color"],
                             hovertemplate="%{y} · Δ " + d["label"] + ": %{x:+.2f} pts<extra></extra>"))
    fig.add_vline(x=0, line=dict(color="#888", width=1))
    fig.update_layout(**_LAYOUT, barmode="relative", height=max(360, 26 * len(members) + 110),
                      xaxis_title="← ficou mais dovish     Δ contribuição (pts de composite)     hawkish →",
                      legend=dict(orientation="h", y=-0.12, font=dict(size=11)))
    return fig


def _fade(hexcolor: str) -> str:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c + (255 - c) * 0.55) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def fig_median_radar(medians: dict) -> go.Figure:
    """Radar of group medians per dimension, normalised to the hawk axis."""
    labels = [config.DIM_BY_ID[d]["label"] for d in config.DIMENSION_IDS]
    labels += labels[:1]
    fig = go.Figure()
    styles = {"voters": (config.GOLD, "Votantes 2026"),
              "all": (config.NAVY, "Todos"),
              "non_voters": ("#9aa3b2", "Não-votantes")}
    for g, (color, label) in styles.items():
        row = medians.get(g, {})
        vals = [config.normalize_to_hawk(d, row[d]) if row.get(d) is not None else 0
                for d in config.DIMENSION_IDS]
        vals += vals[:1]
        fig.add_trace(go.Scatterpolar(r=vals, theta=labels, name=f"{label} (n={row.get('n', 0)})",
                                      line=dict(color=color, width=2)))
    fig.update_layout(font=_LAYOUT["font"], paper_bgcolor="white",
                      polar=dict(radialaxis=dict(range=[-1, 1], tickvals=[-1, -0.5, 0, 0.5, 1])),
                      margin=dict(l=60, r=60, t=40, b=40), height=440,
                      legend=dict(orientation="h", y=-0.08))
    return fig


def fig_heatmap(mfuncs: dict[str, MemberFunction]) -> go.Figure:
    members = [m for m in mfuncs.values() if not m.insufficient]
    members.sort(key=lambda m: (m.composite if m.composite is not None else 0))
    dims = config.DIMENSION_IDS
    z = [[m.dims_hawk.get(d) for d in dims] for m in members]
    ylab = [f"{_short(m.name)}{' ★' if m.voter_2026 else ''}" for m in members]
    xlab = [config.DIM_BY_ID[d]["label"] for d in dims]
    fig = go.Figure(go.Heatmap(
        z=z, x=xlab, y=ylab, zmid=0, zmin=-1, zmax=1,
        colorscale=[[0, config.DOVE], [0.5, "#f5f5f0"], [1, config.HAWK]],
        colorbar=dict(title="hawk", tickvals=[-1, 0, 1], ticktext=["dove", "0", "hawk"]),
        hovertemplate="%{y} · %{x}: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, height=max(360, 22 * len(members) + 80))
    return fig


def fig_evolution(evo: dict, roster) -> go.Figure:
    """Per-member composite paths (faint) + voter/all median paths (bold)."""
    fig = go.Figure()
    months = evo["months"]
    for mid, series in evo["members"].items():
        m = roster.get(mid)
        nm = _short(m.name) if m else mid
        fig.add_trace(go.Scatter(
            x=months, y=series, mode="lines", name=nm,
            line=dict(color="#d2d6de", width=1), opacity=0.7,
            hovertemplate=f"{nm} %{{x}}: %{{y:+.2f}}<extra></extra>", showlegend=False))
    fig.add_trace(go.Scatter(x=months, y=evo["all"], mode="lines+markers", name="Mediana todos",
                             line=dict(color=config.NAVY, width=3)))
    fig.add_trace(go.Scatter(x=months, y=evo["voters"], mode="lines+markers", name="Mediana votantes",
                             line=dict(color=config.GOLD, width=3)))
    fig.add_hline(y=0, line=dict(color="#bbb", width=1))
    fig.update_layout(**_LAYOUT, height=420, yaxis_title="composite hawk-dove",
                      legend=dict(orientation="h", y=-0.12))
    return fig


def fig_tone_scatter(corpus) -> go.Figure:
    """Cross-check: LLM composite (x) vs deterministic net tone (y)."""
    xs, ys, txt, col = [], [], [], []
    for ex in corpus:
        v = ex.score("composite_hawk_dove")
        t = ex.tone_score.get("net_tone") if ex.tone_score else None
        if v is None or t is None:
            continue
        xs.append(v); ys.append(t)
        txt.append(f"{ex.member_id} {ex.date}<br>{ex.title[:60]}")
        col.append(config.GOLD if ex.non_policy else config.NAVY)
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="markers", text=txt,
                               marker=dict(color=col, size=8, opacity=0.7),
                               hovertemplate="%{text}<br>LLM %{x:+.1f} · tom %{y:+.2f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color="#ccc", width=1))
    fig.add_hline(y=0, line=dict(color="#ccc", width=1))
    fig.update_layout(**_LAYOUT, height=380,
                      xaxis_title="LLM composite hawk-dove", yaxis_title="tom léxico (net)")
    return fig

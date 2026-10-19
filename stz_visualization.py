"""Plotly-Figuren; alle Achsen fest (fixedrange), damit Touch-Scrollen auf der Seite nicht am Diagramm hängen bleibt."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import stz_constants as C
from stz_crowd import door_weights

FONT = dict(size=12)


def _lock(fig, height, **kw):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), font=FONT, **kw)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def build_train(view: dict) -> go.Figure:
    """Zug bei Einfahrt: Anteil der Einsteigenden je Tür (oben), belegte Plätze je Reihe (Mitte), gewählte Tür je Strategie (unten)."""
    p, lay = view["params"], view["params"].layout
    rows = list(range(lay.n_rows))
    w = door_weights(p)
    share = [x / sum(w) for x in w]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.28, 0.17, 0.55])
    fig.add_trace(go.Bar(x=list(lay.doors), y=share, marker_color=C.COLOR_DOOR, name="Anteil der Mitreisenden je Tür", width=1.4,
                         hovertemplate="Tür an Reihe %{x}: %{y:.1%} der Mitreisenden<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Heatmap(x=rows, z=[[t / lay.seats for t in view["taken"]]], zmin=0, zmax=1, showscale=False, xgap=0, ygap=0,
                             colorscale=[[0, C.COLOR_FREE], [1, C.COLOR_TAKEN]], hovertemplate="Reihe %{x}: %{z:.0%} belegt<extra></extra>"), row=2, col=1)
    names = [k for k in C.APP_STRATEGIES if k in view["runs"]]
    for i, k in enumerate(names):
        r = view["runs"][k]
        fig.add_trace(go.Scatter(x=[r["door"]], y=[C.STRATEGY_LABELS[k]], mode="markers", name=C.STRATEGY_LABELS[k], marker=dict(size=14, color=C.STRATEGY_COLORS[k], line=dict(width=1, color="white")),
                                 hovertemplate=f"{C.STRATEGY_LABELS[k]}: Tür an Reihe %{{x}}; Platz bei {r['seat_segments']} von {r['trip']} Abschnitten, Weg {r['walk']} Reihen<extra></extra>",
                                 showlegend=False), row=3, col=1)
    for c in range(1, lay.cars):
        fig.add_vline(x=c * lay.rows - 0.5, line_width=1, line_color="rgba(120,120,120,0.6)")
    fig.add_vline(x=p.stair_row, line_width=2, line_dash="dash", line_color=C.COLOR_STAIR)
    fig.add_annotation(x=p.stair_row, y=1.0, yref="paper", text="Zugang am Bahnsteig", showarrow=False, yanchor="bottom", font=dict(color=C.COLOR_STAIR, size=11))
    fig.update_xaxes(range=[-1, lay.n_rows], tickmode="array", tickvals=[c * lay.rows + lay.rows / 2 - 0.5 for c in range(lay.cars)],
                     ticktext=[f"Wagen {c + 1}" for c in range(lay.cars)], row=3, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    fig.update_yaxes(title_text="Türanteil", tickformat=".0%", row=1, col=1)
    fig.update_yaxes(categoryorder="array", categoryarray=[C.STRATEGY_LABELS[k] for k in reversed(names)], row=3, col=1)
    return _lock(fig, 380, showlegend=False)


def build_strategies(rows: dict, with_oracle: bool = False) -> go.Figure:
    """Sitzanteil der Fahrt je Strategie (Fehlerbalken = Standardfehler) und mittlerer Weg in Reihen."""
    keys = [k for k in C.APP_STRATEGIES if k in rows] + (["orakel"] if with_oracle and "orakel" in rows else [])
    labels = [C.STRATEGY_LABELS[k] for k in keys]
    colors = [C.STRATEGY_COLORS.get(k, "#555555") for k in keys]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, column_widths=[0.62, 0.38])
    fig.add_trace(go.Bar(y=labels, x=[rows[k]["sitz"] for k in keys], orientation="h", marker_color=colors,
                         error_x=dict(type="data", array=[rows[k]["se"] for k in keys], color="rgba(60,60,60,0.8)"),
                         text=[f"{100 * rows[k]['sitz']:.0f} %" for k in keys], textposition="inside", insidetextanchor="start",
                         hovertemplate="%{y}: %{x:.1%} der Fahrt auf einem Sitzplatz<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(y=labels, x=[rows[k]["weg"] for k in keys], orientation="h", marker_color=colors,
                         text=[f"{rows[k]['weg']:.0f}" for k in keys], textposition="outside",
                         hovertemplate="%{y}: Weg im Mittel %{x:.1f} Reihen<extra></extra>"), row=1, col=2)
    fig.update_xaxes(range=[0, 1.05], tickformat=".0%", title_text="Sitzanteil der Fahrt", row=1, col=1)
    fig.update_xaxes(range=[0, max(35, max(rows[k]["weg"] for k in keys) * 1.2)], title_text="Weg (Reihen)", row=1, col=2)
    fig.update_yaxes(autorange="reversed")
    return _lock(fig, 300 if len(keys) < 6 else 340, showlegend=False)


def _curve(fig, xs, ys, ses, name, color, dash=None):
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=name, line=dict(color=color, dash=dash, width=2.5), marker=dict(size=7),
                             error_y=dict(type="data", array=ses, color=color, thickness=1, width=3),
                             hovertemplate=f"{name}: %{{y:.1%}} bei %{{x:.0f}} %<extra></extra>"))


def build_phi_curve(points: list, star) -> go.Figure:
    """Sitzanteil über dem Anteil der Tipp-Befolger: 'Nächste Tür' gegen 'Zugende'."""
    xs = [100 * p[0] for p in points]
    fig = go.Figure()
    _curve(fig, xs, [p[1] for p in points], [p[3] for p in points], C.STRATEGY_LABELS["naechste"], C.STRATEGY_COLORS["naechste"])
    _curve(fig, xs, [p[2] for p in points], [p[4] for p in points], C.STRATEGY_LABELS["ende"], C.STRATEGY_COLORS["ende"])
    if isinstance(star, float):
        fig.add_vline(x=100 * star, line_dash="dash", line_color="rgba(80,80,80,0.8)", annotation_text=f"Kreuzung bei {100 * star:.0f} %", annotation_position="top")
    fig.update_xaxes(title_text="Anteil der Mitreisenden, die dem Tipp folgen (%)", range=[-3, 100 * points[-1][0] + 3])
    fig.update_yaxes(title_text="Sitzanteil der Fahrt", range=[0, 1.08], tickformat=".0%")
    return _lock(fig, 340, legend=dict(orientation="h", y=-0.28))


def build_psi_curve(rows: list, star) -> go.Figure:
    """Sitzanteil über dem Anteil der Anzeige-Nutzer: 'Nächste Tür', 'Durchlaufen', 'Anzeige'."""
    xs = [100 * r["psi"] for r in rows]
    fig = go.Figure()
    for k in ("naechste", "durchlaufen", "blick_ankunft"):
        _curve(fig, xs, [r[k]["sitz"] for r in rows], [r[k]["se"] for r in rows], C.STRATEGY_LABELS[k], C.STRATEGY_COLORS[k])
    if isinstance(star, float):
        fig.add_vline(x=100 * star, line_dash="dash", line_color="rgba(80,80,80,0.8)", annotation_text=f"Kreuzung bei {100 * star:.0f} %", annotation_position="top")
    fig.update_xaxes(title_text="Anteil der Mitreisenden mit Anzeige (%)", range=[-3, 103])
    fig.update_yaxes(title_text="Sitzanteil der Fahrt", range=[0, 1.08], tickformat=".0%")
    return _lock(fig, 340, legend=dict(orientation="h", y=-0.28))


def build_phi_map(data: dict, current_stair: int | None = None, current_rho: float | None = None) -> go.Figure:
    """Vorgerechnete Karte: Median des Kreuzungspunkts über Bündelung (Zeilen) und Spitzenlast (Spalten)."""
    rho_labels = [f"{round(100 * r)} %" for r in data["rhos"]]
    stair_labels = [f"a = {int(a)}" for a in data["stairs"]]
    z = [[None if v is None else 100 * v for v in row] for row in data["median"]]
    text = [["kein Vorteil" if v is None else f"{100 * v:.0f} %" for v in row] for row in data["median"]]
    fig = go.Figure(go.Heatmap(x=rho_labels, y=stair_labels, z=z, text=text, texttemplate="%{text}", colorscale=[[0, "#f2d9b8"], [1, "#d98a2b"]], zmin=0, zmax=40,
                               showscale=False, xgap=2, ygap=2, hovertemplate="Last %{x}, Bündelung %{y}: Kreuzungspunkt %{text}<extra></extra>"))
    fig.update_xaxes(title_text="Spitzenlast (Anteil der Sitzplätze)", side="bottom", type="category")
    fig.update_yaxes(title_text="Treppen-Bündelung", autorange="reversed", type="category")
    return _lock(fig, 260)

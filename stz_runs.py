"""Gepaarter Strategievergleich, Orakel unter den Regeln, Kreuzungspunkt phi*."""
import math
from dataclasses import replace

from stz_constants import STRATEGIES
from stz_crowd import Pax, make_crowd
from stz_rng import SplitMix64
from stz_strategies import Focal
from stz_train import Train, advance

PHIS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.6)


def focal_pax(params, seed, s):
    """Fokus-Fahrgast mit eigenem Zufallsstrom (unabhängig von der Größe der Menge)."""
    rng = SplitMix64(seed ^ 0x5EA7_F0CA1)
    b = min(s + params.trip, params.stops - 1)
    return Pax(s, b, rng.next(), rng.below(1_000_000), rng.below(2), 1000)  # informed_draw 1000: nie informiert


def run_focal(params, base, crowd, s, fp, name, door=None, mode=None):
    """Zustand `base` (Halte < s gefahren) kopieren und den Fokus-Fahrgast mit Strategie `name` fahren lassen."""
    t = base.copy()
    tail = [[]] * s + [[p.fresh() for p in lst] for lst in crowd[s:]]
    f = fp.fresh()
    focal = Focal(name, f, params, door=door, mode=mode)
    advance(t, tail, s, f.b, focal=focal, focal_stop=s)
    return f


def evaluate(params, s, seed, strategies=STRATEGIES, oracle=False):
    """Gibt je Strategie (Sitzabschnitte, Fahrstrecke, Platz beim Einsteigen, Weg in Reihen) zurück."""
    crowd = make_crowd(params, seed)
    base = Train(params)
    advance(base, [[p.fresh() for p in lst] for lst in crowd], 0, s)
    fp = focal_pax(params, seed, s)
    out = {}
    for name in strategies:
        f = run_focal(params, base, crowd, s, fp, name)
        out[name] = (f.seat_segments, f.b - s, f.first_seat, f.walk)
    if oracle:
        best = None
        for d in params.layout.doors:
            for mode in ("sofort", "weit", "stehen"):
                f = run_focal(params, base, crowd, s, fp, "orakel", door=d, mode=mode)
                val = (f.seat_segments, f.first_seat, -f.walk)
                if best is None or val > best[0]:
                    best = (val, (f.seat_segments, f.b - s, f.first_seat, f.walk))
        out["orakel"] = best[1]
    return out


def summarize(params, s, n, seed0=1000, strategies=STRATEGIES, oracle=False):
    acc = {}
    for i in range(n):
        for k, (seg, tot, first, walk) in evaluate(params, s, seed0 + i, strategies, oracle).items():
            a = acc.setdefault(k, dict(x=[], first=0, walk=0))
            a["x"].append(seg / tot)
            a["first"] += 1 if first else 0
            a["walk"] += walk
    rows = {}
    for k, a in acc.items():
        m = sum(a["x"]) / n
        var = sum((v - m) ** 2 for v in a["x"]) / max(1, n - 1)
        rows[k] = dict(sitz=m, se=math.sqrt(var / n), sofort=a["first"] / n, weg=a["walk"] / n, x=a["x"])
    return rows


def phi_curve(params, s, n, phis=PHIS, seed0=1000):
    """Sitzanteil von 'nächste Tür' und 'Zugende' über dem Anteil phi der Befolger; gemeinsame Zufallszahlen über phi."""
    pts = []
    for phi in phis:
        r = summarize(replace(params, phi=phi), s, n, seed0, strategies=("naechste", "ende"))
        pts.append((phi, r["naechste"]["sitz"], r["ende"]["sitz"], r["naechste"]["se"], r["ende"]["se"]))
    return pts


def phi_star(points, tol=0.02):
    """Erster Kreuzungspunkt (lineare Interpolation) von 'Zugende minus nächste Tür'. 'kein Vorteil', wenn der Vorsprung bei
    phi = 0 höchstens tol ist; None, wenn der Tipp im Raster nie kippt."""
    d = [(phi, e - nn) for phi, nn, e, _, _ in points]
    if d[0][1] <= tol:
        return "kein Vorteil"
    for (p0, d0), (p1, d1) in zip(d, d[1:]):
        if d1 <= 0:
            return p0 + (p1 - p0) * d0 / (d0 - d1)
    return None


def arrival_state(params, s, seed):
    """Zug bei Einfahrt an Halt s im Lauf `seed`: Zustand nach Aussteigen und Nachrücken, vor dem ersten Einsteigenden.
    Gibt (Zug, Zahl der Einsteigenden an Halt s) zurück (für die Zugdarstellung)."""
    from stz_train import alight, reseat_standing
    crowd = make_crowd(params, seed)
    base = Train(params)
    advance(base, [[p.fresh() for p in lst] for lst in crowd], 0, s)
    alight(base, s)
    reseat_standing(base)
    return base, len(crowd[s])


def example_run(params, s, seed, strategies):
    """Ein Lauf je Strategie für die Darstellung: gewählte Tür, Sitzreihe beim Einsteigen und Abschnitte mit Platz."""
    crowd = make_crowd(params, seed)
    base = Train(params)
    advance(base, [[p.fresh() for p in lst] for lst in crowd], 0, s)
    fp = focal_pax(params, seed, s)
    out = {}
    for name in strategies:
        f = run_focal(params, base, crowd, s, fp, name)
        out[name] = dict(door=f.pos, seat_segments=f.seat_segments, trip=f.b - s, first_seat=f.first_seat, walk=f.walk)
    return out

"""Einstellungen, Live-Rechnungen und Verdikte (reine Funktionen: die App ruft st.<Art>(Text), tests/test_verdicts.py prüft jede Zahl)."""
from dataclasses import dataclass

import stz_constants as C
from stz_runs import arrival_state, example_run, phi_curve, phi_star, summarize

P0 = C.PRESETS[C.DEFAULT_PRESET]


@dataclass(frozen=True, kw_only=True)
class Settings:
    rho: int = P0["rho"]          # Spitzenlast in Prozent der Sitzplätze
    stair: int = P0["stair"]      # Stärke der Treppen-Bündelung a
    reach: int = P0["reach"]      # Reichweite der Mitreisenden beim Platzsuchen (Reihen)
    stop: int = P0["stop"]        # Einstiegshalt des Fokus-Fahrgasts
    phi: int = P0["phi"]          # Anteil der Mitreisenden, die dem Tipp folgen (Prozent)
    psi: int = P0["psi"]          # Anteil der Mitreisenden mit Anzeige (Prozent)
    advice: str = P0["advice"]
    mode: str = P0["mode"]
    block: int = P0["block"]      # Gangblockade ab so vielen Stehenden je Wagen, 0 = aus
    seed: int = P0["seed"]


def to_params(s: Settings) -> C.Params:
    return C.Params(rho=s.rho / 100, stair_a=float(s.stair), reach_naive=s.reach, phi=s.phi / 100, psi=s.psi / 100,
                    advice=s.advice, blick_mode=s.mode, block=None if s.block == 0 else s.block)


def seed0(s: Settings) -> int:
    return C.SEED_BASE + s.seed * 1000


def compare(s: Settings, n: int = C.LIVE_RUNS, oracle: bool = False) -> dict:
    """Gepaarter Strategievergleich auf n Läufen (gleiche Zugverläufe für alle Strategien)."""
    return summarize(to_params(s), s.stop, n, seed0(s), strategies=C.APP_STRATEGIES, oracle=oracle)


def phi_points(s: Settings, n: int = C.LIVE_RUNS) -> list:
    """Sitzanteil von 'Nächste Tür' und 'Zugende' über dem Anteil der Tipp-Befolger (gemeinsame Zufallszahlen über phi)."""
    return phi_curve(to_params(s), s.stop, n, C.CURVE_PHIS, seed0(s))


def psi_points(s: Settings, n: int = C.LIVE_RUNS) -> list:
    """Sitzanteil von 'Nächste Tür', 'Durchlaufen' und 'Anzeige' über dem Anteil der Anzeige-Nutzer."""
    from dataclasses import replace
    params, rows = to_params(s), []
    for psi in C.CURVE_PSIS:
        r = summarize(replace(params, psi=psi), s.stop, n, seed0(s), strategies=("naechste", "durchlaufen", "blick_ankunft"))
        rows.append({"psi": psi, **{k: dict(sitz=v["sitz"], se=v["se"], weg=v["weg"]) for k, v in r.items()}})
    return rows


def psi_crossing(rows: list):
    """Erstes psi, ab dem 'Anzeige' nicht mehr vor 'Nächste Tür' liegt (lineare Interpolation); 'kein Vorteil' ohne Vorsprung bei psi = 0."""
    d = [(r["psi"], r["blick_ankunft"]["sitz"] - r["naechste"]["sitz"]) for r in rows]
    if d[0][1] <= C.NOISE_NOTE:
        return "kein Vorteil"
    for (p0, d0), (p1, d1) in zip(d, d[1:]):
        if d1 <= 0:
            return p0 + (p1 - p0) * d0 / (d0 - d1)
    return None


def train_view(s: Settings) -> dict:
    """Zug bei Einfahrt an Halt `stop` im ersten Lauf (für die Zugdarstellung) und die Tür-Wahl je Strategie in diesem Lauf."""
    p = to_params(s)
    train, n_board = arrival_state(p, s.stop, seed0(s))
    lay = p.layout
    taken = [lay.seats - f for f in train.free]
    runs = example_run(p, s.stop, seed0(s), C.APP_STRATEGIES)
    return {"taken": taken, "standing": list(train.standing), "boarders": n_board, "runs": runs, "params": p}


def best_strategy(rows: dict) -> str:
    """Strategie mit dem größten mittleren Sitzanteil (Gleichstand: die mit kürzerem Weg, dann Reihenfolge der App)."""
    order = list(C.APP_STRATEGIES)
    return min((k for k in rows if k in order), key=lambda k: (-round(rows[k]["sitz"], 6), rows[k]["weg"], order.index(k)))


def rows_text(n: float) -> str:
    """'1 Reihe' / '5 Reihen' (Einzahl bei genau 1 nach dem Runden)."""
    return f"{n:.0f} Reihe" if round(n) == 1 else f"{n:.0f} Reihen"


def pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def verdict_seat(rows: dict) -> tuple[str, str]:
    """Verdikt der Hauptansicht: beste Strategie und Abstand zu 'Nächste Tür' (Sitzanteil der Fahrt, in Prozentpunkten)."""
    best = best_strategy(rows)
    ref = rows["naechste"]["sitz"]
    gap = rows[best]["sitz"] - ref
    label = C.STRATEGY_LABELS[best]
    if best == "naechste" or gap < C.NOISE_NOTE:
        return "info", (f"Hier lohnt sich keine Sonderstrategie: „Nächste Tür“ hat {pct(ref)} der Fahrt einen Sitzplatz, "
                        f"die beste andere Strategie liegt höchstens {100 * C.NOISE_NOTE:.0f} Prozentpunkte darüber.")
    return "success", (f"Beste Strategie: **{label}** mit {pct(rows[best]['sitz'])} der Fahrt auf einem Sitzplatz, "
                       f"**{100 * gap:.0f} Prozentpunkte** mehr als „Nächste Tür“ ({pct(ref)}); Weg {rows_text(rows[best]['weg'])}.")


def verdict_phi(points: list) -> tuple[str, str]:
    """Verdikt der Kernfrage aus der Kurve (phi, nächste Tür, Zugende, SE, SE): wo verliert der Tipp seinen Vorsprung?"""
    star = phi_star(points)
    p0 = points[0]
    gap0 = p0[2] - p0[1]
    if star == "kein Vorteil":
        return "info", (f"Der Tipp hat hier schon ohne Mitwisser höchstens {100 * C.NOISE_NOTE:.0f} Prozentpunkte Vorsprung "
                        f"({pct(p0[2])} gegen {pct(p0[1])} bei „Nächste Tür“): Es gibt nichts zu verlieren.")
    if star is None:
        return "success", (f"Der Tipp behält seinen Vorsprung bis zu einem Anteil von {pct(points[-1][0])} Befolgern "
                           f"({pct(p0[2])} gegen {pct(p0[1])} ohne Befolger).")
    return "warning", (f"Allein bringt der Tipp **{100 * gap0:.0f} Prozentpunkte** mehr Sitzanteil ({pct(p0[2])} gegen {pct(p0[1])}). "
                       f"Er verliert den Vorsprung, wenn etwa **{pct(star)}** der Mitreisenden ihm folgen.")


def verdict_psi(rows: list) -> tuple[str, str]:
    """Verdikt des Anzeige-Experiments: bei welchem Anteil Anzeige-Nutzer liegt die Anzeige nicht mehr vor 'Nächste Tür'?"""
    star = psi_crossing(rows)
    r0 = rows[0]
    gap0 = r0["blick_ankunft"]["sitz"] - r0["naechste"]["sitz"]
    if star == "kein Vorteil":
        return "info", (f"Die Anzeige hilft hier schon dem Einzelnen kaum ({pct(r0['blick_ankunft']['sitz'])} gegen {pct(r0['naechste']['sitz'])} bei „Nächste Tür“): "
                        "genug Plätze oder keine Bündelung.")
    if star is None:
        return "success", (f"Die Anzeige bleibt bis zu einem Anteil von {pct(rows[-1]['psi'])} Nutzern vorn "
                           f"(ohne Mitnutzer {pct(r0['blick_ankunft']['sitz'])} gegen {pct(r0['naechste']['sitz'])}).")
    return "warning", (f"Wer die Anzeige als Einziger nutzt, gewinnt **{100 * gap0:.0f} Prozentpunkte** ({pct(r0['blick_ankunft']['sitz'])} gegen {pct(r0['naechste']['sitz'])}). "
                       f"Bei etwa **{pct(star)}** Mitnutzern liegt die Anzeige nicht mehr vor „Nächste Tür“.")

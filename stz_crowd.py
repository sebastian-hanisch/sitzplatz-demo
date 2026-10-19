"""Mitreisende: Start-Ziel-Paare, Türwahl. Alle Zufallszahlen werden vorab gezogen (gemeinsame Zufallszahlen über phi)."""
import math
from dataclasses import dataclass

from stz_rng import SplitMix64


@dataclass(slots=True)
class Pax:
    a: int
    b: int
    order: int          # 64-Bit-Sortierschlüssel der Einstiegsreihenfolge
    door_draw: int      # 0..999999
    dir_bit: int        # 0/1: bevorzugte Suchrichtung bei Gleichstand
    informed_draw: int  # 0..999: informiert, wenn < round(1000 * phi)
    row: int = -1
    pos: int = 0
    standing: bool = False
    seat_segments: int = 0
    first_seat: bool = False
    walk: int = 0

    def fresh(self):
        return Pax(self.a, self.b, self.order, self.door_draw, self.dir_bit, self.informed_draw)

    def copy(self):
        return Pax(self.a, self.b, self.order, self.door_draw, self.dir_bit, self.informed_draw,
                   self.row, self.pos, self.standing, self.seat_segments, self.first_seat, self.walk)


def lam_for(params):
    """Erwartete Fahrgäste je Start-Ziel-Paar: der stärkste Querschnitt kreuzt (M//2)*(M-M//2) Paare."""
    cross = (params.stops // 2) * (params.stops - params.stops // 2)
    return params.rho * params.layout.n_seats / cross


def make_crowd(params, seed):
    """Liste je Halt der dort Einsteigenden, nach Reihenfolge sortiert. Ziehungen unabhängig von phi (Kopplung über phi)."""
    rng = SplitMix64(seed)
    lam = lam_for(params)
    by_stop = [[] for _ in range(params.stops)]
    for a in range(params.stops - 1):
        for b in range(a + 1, params.stops):
            for _ in range(rng.poisson(lam)):
                by_stop[a].append(Pax(a, b, rng.next(), rng.below(1_000_000), rng.below(2), rng.below(1000)))
    for lst in by_stop:
        lst.sort(key=lambda x: x.order)
    return by_stop


def door_weights(params):
    """Ganzzahlige Gewichte der Türen (Tausendstel): Bündelung um den Zugang."""
    return [1000 + round(1000 * params.stair_a * math.exp(-0.5 * ((d - params.stair_row) / params.stair_sigma) ** 2))
            for d in params.layout.doors]


def cum_weights(params):
    out, acc = [], 0
    for w in door_weights(params):
        acc += w
        out.append(acc)
    return out


def naive_door(params, cum, door_draw):
    x = door_draw * cum[-1] // 1_000_000
    doors = params.layout.doors
    for d, c in zip(doors, cum):
        if x < c:
            return d
    return doors[-1]


def is_informed(params, pax):
    return pax.informed_draw < round(1000 * params.phi)


def is_blick(params, pax):
    """Blick-Nutzer (Auslastungsanzeige): Tipp-Befolger haben Vorrang; die Zuordnung nutzt Bits von `order`, damit keine
    zusätzliche Ziehung die Zufallsströme der früheren Messreihen verschiebt."""
    return not is_informed(params, pax) and (pax.order >> 21) % 1000 < round(1000 * params.psi)


def pick_door(params, cum, pax):
    doors = params.layout.doors
    if is_informed(params, pax):
        if params.advice == "ende":
            return doors[-1] if pax.door_draw % 2 == 0 else doors[-2]
        half = doors[len(doors) // 2:]
        return half[pax.door_draw % len(half)]
    return naive_door(params, cum, pax.door_draw)

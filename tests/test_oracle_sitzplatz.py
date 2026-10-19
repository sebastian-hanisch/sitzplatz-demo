"""Orakel: Einsteigen gegen einen anderen Rechenweg (Aufzählung, geschlossene Poisson-Formel)."""
import itertools
import math
from dataclasses import replace

from stz_constants import Layout, Params
from stz_crowd import Pax, door_weights, make_crowd
from stz_runs import evaluate, focal_pax, run_focal
from stz_train import Train, advance, become_standing, take_seat


def _pax(order, dir_bit):
    return Pax(0, 1, order, 0, dir_bit, 0)


def _reference_pick(free, pos, reach, dir_bit, n_rows):
    """Unabhängige Fassung: Kandidaten sortieren nach (Abstand, Richtungsvorrang)."""
    sgn = -1 if dir_bit == 0 else 1
    cands = []
    for r in range(max(0, pos - reach), min(n_rows - 1, pos + reach) + 1):
        if free[r] > 0:
            side = 0 if r == pos or (r - pos) * sgn > 0 else 1
            cands.append((abs(r - pos), side, r))
    return min(cands)[2] if cands else None


def test_enumeration_all_orders_doors_directions(mini_params):
    """3 Fahrgäste, alle 6 Reihenfolgen x 4^3 Türen x 2^3 Richtungen: Sitzbelegung wie die unabhängige Fassung."""
    n_rows = mini_params.layout.n_rows
    checked = 0
    for dirs in itertools.product((0, 1), repeat=3):
        for doors in itertools.product(range(n_rows), repeat=3):
            t = Train(mini_params)
            ref_free = [1] * n_rows
            for k in range(3):                    # Reihenfolge = Index (alle Permutationen stecken in doors x dirs)
                p = _pax(k, dirs[k])
                p.pos = doors[k]
                ok = take_seat(t, p, 1)
                r = _reference_pick(ref_free, doors[k], 1, dirs[k], n_rows)
                assert ok == (r is not None)
                if r is not None:
                    ref_free[r] -= 1
                    assert p.row == r
                else:
                    become_standing(t, p)
            assert t.free == ref_free
            checked += 1
    assert checked == 8 * 64


def _poisson_pmf(lam, k):
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def _expected_min(lam, cap, kmax=200):
    return sum(_poisson_pmf(lam, k) * min(k, cap) for k in range(kmax))


def test_single_car_seated_count_matches_poisson_formula():
    """1 Wagen, 5 Plätze, keine Reichweite: erwartete Sitzende = E[min(N, 5)], N ~ Poisson(5)."""
    lay = Layout(cars=1, rows=1, seats=5)
    p = Params(layout=lay, stops=2, trip=1, rho=1.0, reach_naive=0, reach_stand=0)
    vals = []
    for seed in range(3000):
        crowd = make_crowd(p, seed)
        t = Train(p)
        advance(t, crowd, 0, 1)
        vals.append(lay.n_seats - sum(t.free))
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    assert abs(m - _expected_min(5.0, 5)) < 4 * sd / math.sqrt(len(vals))


def test_focal_first_seat_probability_is_capacity_over_rank():
    """Fokus-Fahrgast unter N ~ Poisson(5) Mitreisenden, 5 Plätze: P(Platz) = E[min(1, 5/(N+1))]."""
    lay = Layout(cars=1, rows=1, seats=5)
    p = Params(layout=lay, stops=2, trip=1, rho=1.0, reach_naive=0, reach_stand=0)
    expect = sum(_poisson_pmf(5.0, k) * min(1.0, 5 / (k + 1)) for k in range(200))
    n, hits = 4000, 0
    for seed in range(n):
        hits += evaluate(p, 0, seed, strategies=("naechste",))["naechste"][2]
    se = math.sqrt(expect * (1 - expect) / n)
    assert abs(hits / n - expect) < 4 * se


def test_three_cars_seated_count_matches_thinned_poisson():
    """3 Wagen mit Bündelung, keine Reichweite: erwartete Sitzende = Summe über Wagen E[min(Poisson(lam * w_c / sum w), 4)]."""
    lay = Layout(cars=3, rows=1, seats=4)
    p = Params(layout=lay, stops=2, trip=1, rho=1.5, reach_naive=0, reach_stand=0, stair_a=2.0, stair_row=1.0, stair_sigma=1.0)
    lam = 1.5 * lay.n_seats                      # ein Start-Ziel-Paar kreuzt den Querschnitt
    w = door_weights(p)
    expect = sum(_expected_min(lam * wi / sum(w), 4) for wi in w)
    vals = []
    for seed in range(3000):
        crowd = make_crowd(p, seed)
        t = Train(p)
        advance(t, crowd, 0, 1)
        vals.append(lay.n_seats - sum(t.free))
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    assert abs(m - expect) < 4 * sd / math.sqrt(len(vals))

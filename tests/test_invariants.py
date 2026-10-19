"""Invarianten je Halt, Zweig-Tests je Strategie, Kern-Behauptungen der Vorab-Messreihe (kleine Fassung)."""
from dataclasses import replace

from stz_constants import Layout, Params
from stz_crowd import make_crowd
from stz_runs import evaluate, phi_curve, phi_star, summarize
from stz_train import Train, advance

BASE = Params(rho=1.2)


def _check(train):
    lay = train.params.layout
    seated = [0] * lay.n_rows
    stand = [0] * lay.cars
    for p in train.onboard:
        if p.row >= 0:
            assert not p.standing
            seated[p.row] += 1
        else:
            assert p.standing
            stand[lay.car_of(p.pos)] += 1
    for r in range(lay.n_rows):
        assert 0 <= train.free[r] <= lay.seats
        assert lay.seats - train.free[r] == seated[r]
    assert stand == train.standing


def test_invariants_every_stop_with_and_without_blockade():
    for block in (None, 6):
        p = replace(BASE, block=block)
        for seed in range(8):
            crowd = make_crowd(p, seed)
            t = Train(p)
            for j in range(p.stops - 1):
                advance(t, crowd, j, j + 1)
                _check(t)


def test_crowd_is_common_across_phi():
    """Gleiche Zufallszahlen: nur die Informiertheit hängt von phi ab, nicht die Größe oder Reihenfolge der Menge."""
    a = make_crowd(replace(BASE, phi=0.0), 5)
    b = make_crowd(replace(BASE, phi=0.5), 5)
    assert [[(x.a, x.b, x.order, x.door_draw) for x in lst] for lst in a] == [[(x.a, x.b, x.order, x.door_draw) for x in lst] for lst in b]


def test_evaluate_deterministic_and_seat_segments_bounded():
    r1 = evaluate(BASE, 3, 42, oracle=False)
    r2 = evaluate(BASE, 3, 42, oracle=False)
    assert r1 == r2
    for seg, tot, first, walk in r1.values():
        assert 0 <= seg <= tot and walk >= 0


def test_every_strategy_deviates_from_its_neighbour_on_some_instance():
    """Zweig-Test (Nullspalte = Variante läuft nie): je Paar mindestens eine Instanz mit anderem Ergebnis (mit Blockade für 'durchlaufen')."""
    p = replace(BASE, block=6)
    pairs = [("naechste", "ende"), ("ende", "durchlaufen"), ("naechste", "stehen"), ("ende", "blick"), ("naechste", "durchlaufen")]
    seen = {pair: False for pair in pairs}
    for seed in range(40):
        r = evaluate(p, 3, seed)
        for a, b in pairs:
            if r[a] != r[b]:
                seen[(a, b)] = True
    assert all(seen.values()), seen


def test_oracle_is_never_worse_than_any_rule():
    for seed in range(6):
        r = evaluate(BASE, 3, seed, oracle=True)
        best_rule = max(r[k][0] for k in r if k != "orakel")
        assert r["orakel"][0] >= best_rule


def test_blockade_never_helps_walking_through():
    """Mit Gangblockade kommt 'durchlaufen' im Mittel nicht öfter an einen Platz als ohne."""
    free = summarize(BASE, 3, 40, strategies=("durchlaufen",))["durchlaufen"]["sitz"]
    blocked = summarize(replace(BASE, block=6), 3, 40, strategies=("durchlaufen",))["durchlaufen"]["sitz"]
    assert blocked <= free + 1e-9


def test_without_bundling_the_advice_has_no_advantage():
    """Befund 2 der Messreihe: ohne Treppen-Bündelung bringt 'Zugende' keinen Vorsprung."""
    r = summarize(replace(BASE, stair_a=0.0), 3, 60, strategies=("naechste", "ende"))
    assert r["ende"]["sitz"] - r["naechste"]["sitz"] < 0.05


def test_advice_has_advantage_alone_and_tips_at_a_modest_share():
    """Mit Bündelung gewinnt der Tipp bei phi = 0 deutlich; spätestens bei phi = 0,4 liegt er nicht mehr vorn."""
    pts = phi_curve(BASE, 3, 40, phis=(0.0, 0.4))
    (_, n0, e0, _, _), (_, n4, e4, _, _) = pts
    assert e0 - n0 > 0.2
    assert e4 - n4 < 0
    star = phi_star(phi_curve(BASE, 3, 40, phis=(0.0, 0.1, 0.2, 0.3, 0.4)))
    assert not isinstance(star, str) and star is not None and 0.05 < star < 0.4


def test_invariants_with_display_users():
    for mode in ("bester", "gewichtet"):
        p = replace(BASE, psi=0.5, blick_mode=mode, phi=0.2, block=6)
        for seed in range(6):
            crowd = make_crowd(p, seed)
            t = Train(p)
            for j in range(p.stops - 1):
                advance(t, crowd, j, j + 1)
                _check(t)


def test_display_users_change_the_outcome_and_psi_zero_is_the_old_model():
    r0 = evaluate(BASE, 3, 7, strategies=("naechste", "ende"))
    assert r0 == evaluate(replace(BASE, psi=0.0, blick_mode="gewichtet"), 3, 7, strategies=("naechste", "ende"))
    moved = any(evaluate(BASE, 3, s, strategies=("naechste",)) != evaluate(replace(BASE, psi=0.6), 3, s, strategies=("naechste",)) for s in range(10))
    assert moved


def test_blick_ankunft_differs_from_live_blick_on_some_instance():
    """Anzeige bei Ankunft und Blick im Moment des eigenen Einsteigens sind verschiedene Regeln (Zweig-Test)."""
    p = replace(BASE, phi=0.3, psi=0.3)
    diffs = 0
    for s in range(25):
        r = evaluate(p, 3, s, strategies=("blick", "blick_ankunft"))
        diffs += r["blick"] != r["blick_ankunft"]
    assert diffs > 0


def _reseat_reference(train):
    """Ursprüngliche Fassung ohne Zwischenspeicher: nach jeder Platznahme für alle Stehenden neu suchen."""
    from stz_train import nearest_free, take_seat
    reach = train.params.reach_stand
    while True:
        best = None
        for p in train.onboard:
            if p.standing:
                r = nearest_free(train, p.pos, reach, p.dir_bit)
                if r is not None:
                    key = (abs(r - p.pos), p.order)
                    if best is None or key < best[0]:
                        best = (key, p)
        if best is None:
            return
        take_seat(train, best[1], reach)


def test_cached_reseating_equals_the_plain_search():
    """Der Zwischenspeicher in reseat_standing darf nichts ändern (mit und ohne Gangblockade, mit Anzeige-Nutzern)."""
    from stz_train import alight, reseat_standing
    for block in (None, 4, 8):
        p = replace(BASE, block=block, psi=0.3, phi=0.2)
        for seed in range(6):
            crowd = make_crowd(p, seed)
            t = Train(p)
            for j in range(1, p.stops - 1):
                advance(t, crowd, j - 1, j)
                alight(t, j)
                a, b = t.copy(), t.copy()
                reseat_standing(a)
                _reseat_reference(b)
                assert [(x.order, x.row) for x in a.onboard] == [(x.order, x.row) for x in b.onboard], (block, seed, j)
                assert a.free == b.free and a.standing == b.standing
                t = a

"""Einheiten an der Mini-Instanz (2 Wagen x 2 Reihen x 1 Platz), Ergebnis von Hand gerechnet (DEMO-PLAYBOOK 1b)."""
from dataclasses import replace

from stz_constants import Layout, Params
from stz_crowd import Pax, cum_weights, door_weights, is_informed, naive_door
from stz_rng import SplitMix64
from stz_train import Train, alight, nearest_free, reseat_standing, take_seat


def pax(**kw):
    base = dict(a=0, b=1, order=0, door_draw=0, dir_bit=0, informed_draw=0)
    base.update(kw)
    return Pax(**base)


def test_splitmix_reference_value():
    # bekannter Referenzwert von SplitMix64 mit Seed 0
    assert SplitMix64(0).next() == 0xE220A8397B1DCDAF


def test_layout_doors_and_cars(mini_layout):
    assert mini_layout.doors == (0, 1, 2, 3)
    assert Layout().doors[:4] == (0, 9, 10, 19) and len(Layout().doors) == 16
    assert mini_layout.car_of(1) == 0 and mini_layout.car_of(2) == 1


def test_nearest_free_by_hand(mini_params):
    t = Train(mini_params)
    t.free = [1, 0, 0, 1]
    assert nearest_free(t, 1, 1, 0) == 0 and nearest_free(t, 1, 1, 1) == 0
    assert nearest_free(t, 2, 1, 0) == 3
    t.free = [1, 0, 1, 0]
    assert nearest_free(t, 1, 1, 0) == 0     # Gleichstand: Richtung abwärts
    assert nearest_free(t, 1, 1, 1) == 2     # Gleichstand: Richtung aufwärts
    t.free = [0, 0, 0, 1]
    assert nearest_free(t, 1, 1, 0) is None  # außer Reichweite
    assert nearest_free(t, 1, 2, 0) == 3
    assert nearest_free(t, 3, 0, 0) == 3     # Reichweite 0: nur die eigene Reihe
    assert nearest_free(t, 0, 0, 0) is None


def test_blockade_blocks_entering_crowded_car(mini_params):
    p = replace(mini_params, block=1)
    t = Train(p)
    t.free = [0, 0, 0, 1]
    t.standing = [0, 1]                       # Wagen 1 dicht
    assert nearest_free(t, 1, 3, 0) is None   # Weg dorthin versperrt
    t.standing = [0, 0]
    assert nearest_free(t, 1, 3, 0) == 3
    t.standing = [0, 1]
    assert nearest_free(t, 2, 3, 0) == 3      # eigener Wagen bleibt begehbar


def test_take_seat_updates_state_and_walk(mini_params):
    t = Train(mini_params)
    x = pax()
    x.pos = 1
    t.free = [1, 0, 0, 0]
    assert take_seat(t, x, 1) and x.row == 0 and x.walk == 1 and t.free == [0, 0, 0, 0]
    y = pax()
    y.pos = 1
    assert not take_seat(t, y, 1) and y.row == -1 and y.walk == 0


def test_alight_frees_seat_and_standing_nachruecken(mini_params):
    t = Train(mini_params)
    p1 = pax(b=1)
    p1.row = 0
    p2 = pax(b=2)
    p2.pos, p2.standing = 1, True
    t.free = [0, 0, 0, 0]
    t.standing = [1, 0]
    t.onboard = [p1, p2]
    alight(t, 1)
    assert t.free == [1, 0, 0, 0] and t.onboard == [p2]
    reseat_standing(t)
    assert p2.row == 0 and p2.walk == 1 and not p2.standing and t.standing == [0, 0] and t.free == [0, 0, 0, 0]


def test_alight_of_standing_updates_counter(mini_params):
    t = Train(mini_params)
    p = pax(b=1)
    p.pos, p.standing = 2, True
    t.standing = [0, 1]
    t.onboard = [p]
    alight(t, 1)
    assert t.standing == [0, 0] and t.onboard == []


def test_reseat_closest_standing_first(mini_params):
    t = Train(mini_params)
    a = pax(order=5)
    a.pos, a.standing = 3, True      # steht in Reihe 3, einziger freier Platz Reihe 2 (Abstand 1)
    b = pax(order=1)
    b.pos, b.standing = 0, True      # Abstand 2, außer Reichweite 1
    t.free = [0, 0, 1, 0]
    t.standing = [1, 1]
    t.onboard = [a, b]
    reseat_standing(t)
    assert a.row == 2 and b.row == -1


def test_door_weights_integer_and_peak(mini_params):
    p = replace(mini_params, stair_a=4.0, stair_row=1.0, stair_sigma=1.0)
    w = door_weights(p)
    assert all(isinstance(x, int) for x in w)
    assert w[1] == 5000 and w[1] == max(w)          # 1000 + 4 * 1000 an der Treppe
    assert w[0] == w[2] == 1000 + round(4000 * 0.6065306597126334)


def test_naive_door_follows_weights(mini_params):
    p = replace(mini_params, stair_a=4.0, stair_row=1.0, stair_sigma=1.0)
    cum = cum_weights(p)
    n, counts = 20000, {}
    rng = SplitMix64(7)
    for _ in range(n):
        d = naive_door(p, cum, rng.below(1_000_000))
        counts[d] = counts.get(d, 0) + 1
    tot = cum[-1]
    for d, w in zip(p.layout.doors, door_weights(p)):
        assert abs(counts.get(d, 0) / n - w / tot) < 0.015


def test_informed_flag_is_monotone_in_phi(mini_params):
    x = pax(informed_draw=250)
    flags = [is_informed(replace(mini_params, phi=phi), x) for phi in (0.0, 0.2, 0.25, 0.26, 0.5, 1.0)]
    assert flags == [False, False, False, True, True, True]


def test_poisson_mean_and_variance():
    rng = SplitMix64(11)
    xs = [rng.poisson(6.0) for _ in range(20000)]
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    assert abs(m - 6.0) < 0.1 and abs(v - 6.0) < 0.3


def test_reseat_prefers_shorter_walk_over_order(mini_params):
    """Zwei Stehende erreichen denselben freien Platz; der mit dem kürzeren Weg gewinnt, nicht der mit dem kleineren Schlüssel."""
    p = replace(mini_params, reach_stand=3)
    t = Train(p)
    far = pax(order=1)       # kleinerer Schlüssel, aber Abstand 3
    far.pos, far.standing = 0, True
    near = pax(order=9)      # größerer Schlüssel, Abstand 1
    near.pos, near.standing = 2, True
    t.free = [0, 0, 0, 1]
    t.standing = [1, 1]
    t.onboard = [far, near]
    reseat_standing(t)
    assert near.row == 3 and far.row == -1


def test_naive_door_boundary_belongs_to_next_door(mini_params):
    p = replace(mini_params, stair_a=0.0)           # alle Türen Gewicht 1000, Summe 4000
    cum = cum_weights(p)
    assert cum == [1000, 2000, 3000, 4000]
    assert naive_door(p, cum, 249_999) == 0 and naive_door(p, cum, 250_000) == 1
    assert naive_door(p, cum, 999_999) == 3


def test_tip_ende_uses_both_doors_of_last_car(mini_params):
    from stz_crowd import pick_door
    p = replace(mini_params, phi=1.0, advice="ende")
    cum = cum_weights(p)
    assert pick_door(p, cum, pax(door_draw=0)) == 3 and pick_door(p, cum, pax(door_draw=1)) == 2


def test_blick_avoids_crowded_door_with_equal_free_seats(mini_params):
    from stz_strategies import door_blick
    p = replace(mini_params, reach_naive=0, stair_a=4.0, stair_row=0.0, stair_sigma=1.0)
    t = Train(p)
    t.free = [1, 0, 0, 1]                            # Türen 0 und 3 mit je einem freien Platz
    cum = cum_weights(p)
    weights = door_weights(p)
    assert weights[0] > weights[3]                   # Tür 0 liegt am Zugang: mehr Konkurrenz
    assert door_blick(t, [None] * 4, cum, weights) == 3


def test_door_scores_by_hand(mini_params):
    from stz_train import door_scores
    p = replace(mini_params, reach_naive=0, stair_a=0.0)
    t = Train(p)
    t.free = [1, 0, 0, 1]
    # 4 Einsteigende, alle Türen Gewicht 1000: Mitbewerber je Tür 4 * 1000 / 4000 = 1 -> Bewertung 1 / (1 + 1)
    assert door_scores(t, 4, door_weights(p)) == [0.5, 0.0, 0.0, 0.5]
    t.free = [2, 0, 0, 1]
    assert door_scores(t, 0, door_weights(p)) == [2.0, 0.0, 0.0, 1.0]


def test_blick_door_best_and_weighted(mini_params):
    from stz_train import blick_door
    best = replace(mini_params, blick_mode="bester")
    wtd = replace(mini_params, blick_mode="gewichtet")
    scores = [0.5, 0.0, 0.0, 1.5]
    assert blick_door(best, scores, 0) == 3 and blick_door(best, [1.0, 1.0, 0.0, 1.0], 0) == 0   # erste bei Gleichstand
    assert blick_door(wtd, scores, 0) == 0 and blick_door(wtd, scores, 249_999) == 0
    assert blick_door(wtd, scores, 250_000) == 3 and blick_door(wtd, scores, 999_999) == 3
    assert blick_door(wtd, [0.0] * 4, 5) == 3 or blick_door(wtd, [0.0] * 4, 5) == 0           # alle 0: bester Fall (erste Tür)


def test_is_blick_precedence_and_monotone(mini_params):
    from stz_crowd import is_blick
    x = pax(order=(123 << 21), informed_draw=999)       # (order >> 21) % 1000 == 123
    assert not is_blick(replace(mini_params, psi=0.123), x) and is_blick(replace(mini_params, psi=0.124), x)
    informed = pax(order=(123 << 21), informed_draw=0)
    assert not is_blick(replace(mini_params, psi=1.0, phi=0.5), informed)     # Tipp-Befolger haben Vorrang
    assert not any(is_blick(mini_params, pax(order=o << 21)) for o in range(1000))   # psi = 0: niemand


def test_blick_users_herd_on_the_best_door_unless_weighted(mini_params):
    """Gleichzeitige Entscheidung nach dem Zustand bei Ankunft: 'bester' schickt alle an dieselbe Tür, 'gewichtet' verteilt."""
    from stz_train import advance
    def run(mode):
        p = replace(mini_params, psi=1.0, blick_mode=mode, stops=3)
        crowd = [[pax(order=k << 21, door_draw=dd, b=2) for k, dd in zip((1, 2, 3), (0, 500_000, 999_999))], [], []]
        t = Train(p)
        advance(t, crowd, 0, 1)
        return [x.pos for x in crowd[0]]
    assert len(set(run("bester"))) == 1
    assert len(set(run("gewichtet"))) > 1


def test_blick_user_walks_through_the_train_when_no_seat_near_the_door():
    from stz_train import advance
    lay = Layout(cars=2, rows=4, seats=1)            # Türen an den Reihen 0, 3, 4, 7
    p = Params(layout=lay, psi=1.0, reach_naive=0, stops=3)
    t = Train(p)
    t.free = [0, 1, 0, 0, 0, 0, 0, 0]               # nur Reihe 1 frei, keine Tür steht dort
    x = pax(order=1 << 21, b=2)
    advance(t, [[x], [], []], 0, 1)
    assert x.pos == 0 and x.row == 1 and x.walk == 1 and not x.standing


def test_display_scores_use_the_number_of_boarders_at_arrival(mini_params):
    """Mit 3 Einsteigenden sieht Tür 0 (Zugang, stark besucht) schlechter aus als Tür 3; ohne Mitbewerber wäre es Tür 0."""
    from stz_train import advance
    p = replace(mini_params, psi=1.0, reach_naive=0, stair_a=4.0, stair_row=0.0, stair_sigma=0.5, stops=3)
    t = Train(p)
    t.free = [2, 0, 0, 1]
    crowd = [[pax(order=(k << 21), b=2) for k in (1, 2, 3)], [], []]
    advance(t, crowd, 0, 1)
    assert [x.pos for x in crowd[0]] == [3, 3, 3]


def test_focal_blick_ankunft_uses_the_arrival_display_not_the_live_state(mini_params):
    from stz_strategies import Focal
    p = replace(mini_params, reach_naive=0)
    t = Train(p)
    t.free = [1, 1, 1, 1]                          # live wären alle Türen gleich gut (Tür 0 gewinnt)
    t.scores = [0.0, 0.0, 0.0, 5.0]                # die Anzeige bei Ankunft sagt Tür 3
    x = pax()
    Focal("blick_ankunft", x, p).act(t, [x], cum_weights(p))
    assert x.pos == 3 and x.row == 3

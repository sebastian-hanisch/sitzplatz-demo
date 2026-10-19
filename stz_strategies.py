"""Strategien des Fokus-Fahrgasts (je eine Regel): Türwahl und Platzsuche beim Einsteigen."""
from dataclasses import replace

from stz_crowd import naive_door

from stz_train import REACH_ALL, become_standing, blick_door, door_scores, take_seat


def door_ende(layout, pax):
    d = layout.doors
    return d[-1] if pax.door_draw % 2 == 0 else d[-2]


def door_blick(train, entries, cum, weights):
    """Tür mit dem besten Verhältnis freie Plätze in Reichweite / (1 + erwartete Mitbewerber) im Zustand beim Einsteigen des Fokus-Fahrgasts."""
    scores = door_scores(train, len(entries), weights)
    return blick_door(replace(train.params, blick_mode="bester"), scores, 0)


class Focal:
    """name in STRATEGIES oder ('orakel', door, mode) mit mode in sofort/weit/stehen."""

    def __init__(self, name, pax, params, door=None, mode=None):
        self.name, self.pax, self.params = name, pax, params
        self.door, self.mode = door, mode

    def act(self, train, entries, cum):
        params, pax, lay = self.params, self.pax, self.params.layout
        n = self.name
        if n == "naechste":
            pax.pos = naive_door(params, cum, pax.door_draw)
            ok = take_seat(train, pax, params.reach_naive)
        elif n == "ende":
            pax.pos = door_ende(lay, pax)
            ok = take_seat(train, pax, params.reach_naive)
        elif n == "durchlaufen":
            pax.pos = naive_door(params, cum, pax.door_draw)
            ok = take_seat(train, pax, REACH_ALL)
        elif n == "stehen":
            pax.pos = naive_door(params, cum, pax.door_draw)
            ok = False
        elif n == "blick":
            weights = [cum[0]] + [cum[i] - cum[i - 1] for i in range(1, len(cum))]
            pax.pos = door_blick(train, entries, cum, weights)
            ok = take_seat(train, pax, params.reach_naive) or take_seat(train, pax, REACH_ALL)
        elif n == "blick_ankunft":
            pax.pos = blick_door(params, train.scores, pax.door_draw)
            ok = take_seat(train, pax, params.reach_naive) or take_seat(train, pax, REACH_ALL)
        elif n == "orakel":
            pax.pos = self.door
            reach = {"sofort": params.reach_naive, "weit": REACH_ALL}.get(self.mode)
            ok = take_seat(train, pax, reach) if reach is not None else False
        else:
            raise ValueError(n)
        pax.first_seat = ok
        if not ok:
            become_standing(train, pax)

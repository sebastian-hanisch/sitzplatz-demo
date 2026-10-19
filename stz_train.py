"""Zugzustand und Einheiten: Platzsuche, Platznahme, Halt (Aussteigen + Nachrücken), Einsteigen. Jede Einheit eine Regel."""
from stz_crowd import cum_weights, door_weights, is_blick, pick_door

REACH_ALL = 10 ** 6


class Train:
    def __init__(self, params):
        lay = params.layout
        self.params = params
        self.free = [lay.seats] * lay.n_rows     # freie Plätze je Reihe
        self.onboard = []                        # Pax im Zug
        self.standing = [0] * lay.cars           # Stehende je Wagen (für die Gangblockade)
        self.scores = None                       # Türbewertung bei Ankunft des Zuges an diesem Halt (Anzeige)

    def copy(self):
        t = Train.__new__(Train)
        t.params = self.params
        t.free = list(self.free)
        t.onboard = [p.copy() for p in self.onboard]
        t.standing = list(self.standing)
        t.scores = None if self.scores is None else list(self.scores)
        return t


def nearest_free(train, pos, reach, dir_bit):
    """Nächste Reihe mit freiem Platz innerhalb `reach` Reihen von `pos`; bei gleichem Abstand gewinnt die Richtung dir_bit
    (0: abwärts, 1: aufwärts). Ein Wagen mit >= params.block Stehenden darf nicht betreten werden (außer dem eigenen)."""
    lay = train.params.layout
    block = train.params.block
    free, n, rows = train.free, lay.n_rows, lay.rows
    sgn = -1 if dir_bit == 0 else 1
    reach = min(reach, n)                   # weiter als der Zug lang ist kommt keine Reihe hinzu (REACH_ALL = 10**6)
    if 0 <= pos < n and free[pos] > 0:
        return pos
    start_car = pos // rows
    blocked = {sgn: False, -sgn: False}
    for dist in range(1, reach + 1):
        for d in (sgn, -sgn):
            if blocked[d]:
                continue
            r = pos + d * dist
            if r < 0 or r >= n:
                blocked[d] = True
                continue
            if block is not None:
                car = r // rows
                if car != (r - d) // rows and car != start_car and train.standing[car] >= block:
                    blocked[d] = True
                    continue
            if free[r] > 0:
                return r
    return None


def become_standing(train, pax):
    pax.standing = True
    train.standing[train.params.layout.car_of(pax.pos)] += 1


def take_seat(train, pax, reach):
    """Nächsten Platz in Reichweite nehmen. Gibt True zurück, wenn es klappt (sonst bleibt pax unverändert)."""
    r = nearest_free(train, pax.pos, reach, pax.dir_bit)
    if r is None:
        return False
    train.free[r] -= 1
    pax.row = r
    pax.walk += abs(r - pax.pos)
    if pax.standing:
        train.standing[train.params.layout.car_of(pax.pos)] -= 1
        pax.standing = False
    return True


def alight(train, stop):
    """Aussteigen an `stop`: Plätze werden frei, Stehende zählen nicht mehr."""
    lay = train.params.layout
    keep = []
    for p in train.onboard:
        if p.b == stop:
            if p.row >= 0:
                train.free[p.row] += 1
            elif p.standing:
                train.standing[lay.car_of(p.pos)] -= 1
        else:
            keep.append(p)
    train.onboard = keep


def reseat_standing(train):
    """Stehende nehmen frei gewordene Plätze: jeweils der Stehende mit dem kürzesten Weg zu einem freien Platz zuerst
    (Gleichstand: kleinerer Reihenfolge-Schlüssel). Eine Platznahme ändert die Suche der anderen nur, wenn ihr Ziel voll wurde
    (freie Plätze werden nur weniger) oder, mit Gangblockade, ein Wagen unter die Blockadeschwelle fällt (Stehzähler von
    `block` auf `block - 1`): sonst reicht ein Zwischenspeicher je Stehendem."""
    reach = train.params.reach_stand
    if not any(f > 0 for f in train.free):
        return
    cache = {}
    block, rows = train.params.block, train.params.layout.rows
    while True:
        best = None
        for p in train.onboard:
            if p.standing:
                hit = cache.get(id(p))
                if hit is None or (hit[0] is not None and train.free[hit[0]] == 0):
                    hit = (nearest_free(train, p.pos, reach, p.dir_bit),)
                    cache[id(p)] = hit
                r = hit[0]
                if r is not None:
                    key = (abs(r - p.pos), p.order)
                    if best is None or key < best[0]:
                        best = (key, p)
        if best is None:
            return
        p = best[1]
        before = train.standing[p.pos // rows]
        take_seat(train, p, reach)
        if block is not None and before == block:
            cache.clear()                    # ein Wagen ist wieder passierbar: Wege können sich geändert haben


def door_scores(train, nb, weights):
    """Bewertung je Tür: freie Plätze in Reichweite / (1 + erwartete Mitbewerber nach den naiven Türgewichten bei nb Einsteigenden)."""
    lay = train.params.layout
    reach = train.params.reach_naive
    tot = sum(weights)
    out = []
    for d in lay.doors:
        lo, hi = max(0, d - reach), min(lay.n_rows - 1, d + reach)
        free = sum(train.free[lo:hi + 1])
        comp = nb * sum(w for di, w in zip(lay.doors, weights) if lo <= di <= hi) / tot
        out.append(free / (1.0 + comp))
    return out


def blick_door(params, scores, door_draw):
    """Tür nach Anzeige: 'bester' = höchste Bewertung (erste bei Gleichstand), 'gewichtet' = zufällig im Verhältnis der Bewertung."""
    doors = params.layout.doors
    if params.blick_mode == "gewichtet":
        tot = sum(scores)
        if tot > 0:
            x = door_draw / 1_000_000 * tot
            acc = 0.0
            for d, sc in zip(doors, scores):
                acc += sc
                if x < acc:
                    return d
            return doors[-1]
    best = 0
    for i, sc in enumerate(scores):
        if sc > scores[best]:
            best = i
    return doors[best]


def board_naive(train, pax, cum):
    """Einsteigen eines Mitreisenden: Tür nach Gewicht, Tipp oder Anzeige (Zustand bei Ankunft des Zuges), nächster Platz in
    Reichweite, Blick-Nutzer sonst durch den Zug, sonst stehen."""
    params = train.params
    if is_blick(params, pax):
        pax.pos = blick_door(params, train.scores, pax.door_draw)
        ok = take_seat(train, pax, params.reach_naive) or take_seat(train, pax, REACH_ALL)
    else:
        pax.pos = pick_door(params, cum, pax)
        ok = take_seat(train, pax, params.reach_naive)
    if not ok:
        become_standing(train, pax)
    train.onboard.append(pax)


def count_segment(train):
    for p in train.onboard:
        if p.row >= 0:
            p.seat_segments += 1


def advance(train, crowd, first, last, focal=None, focal_stop=None):
    """Halte first..last-1 fahren: Aussteigen, Nachrücken, Einsteigen, Abschnitt zählen. Der Fokus-Fahrgast (falls gegeben)
    steigt an focal_stop an seiner Stelle der Einstiegsreihenfolge ein; focal.act(train, entries) setzt seine Strategie um."""
    cum = cum_weights(train.params)
    weights = door_weights(train.params)
    for j in range(first, last):
        alight(train, j)
        reseat_standing(train)
        entries = list(crowd[j])
        if focal is not None and j == focal_stop:
            idx = sum(1 for x in entries if x.order < focal.pax.order)
            entries.insert(idx, focal.pax)
        train.scores = door_scores(train, len(entries), weights)   # Anzeige: Zustand bei Ankunft, vor dem ersten Einsteigenden
        for x in entries:
            if focal is not None and x is focal.pax:
                focal.act(train, entries, cum)
                train.onboard.append(x)
            else:
                board_naive(train, x, cum)
        count_segment(train)

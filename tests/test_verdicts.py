"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier."""

import pytest

import stz_evaluation as ev


def _rows(**sitz):
    base = {"naechste": 0.5, "ende": 0.5, "durchlaufen": 0.5, "stehen": 0.4, "blick_ankunft": 0.5}
    base.update(sitz)
    weg = {"naechste": 4, "ende": 1, "durchlaufen": 20, "stehen": 1, "blick_ankunft": 7}
    return {k: dict(sitz=v, se=0.02, sofort=0.3, weg=weg[k]) for k, v in base.items()}


def test_pct_and_rows_text():
    assert ev.pct(0.0) == "0 %" and ev.pct(0.994) == "99 %" and ev.pct(1.0) == "100 %"
    assert ev.rows_text(1) == "1 Reihe" and ev.rows_text(1.4) == "1 Reihe" and ev.rows_text(1.6) == "2 Reihen" and ev.rows_text(0) == "0 Reihen"


def test_best_strategy_ties_prefer_the_shorter_walk_then_the_app_order():
    assert ev.best_strategy(_rows(ende=0.9, durchlaufen=0.9)) == "ende"                 # gleicher Sitzanteil, Weg 1 gegen 20
    r = _rows(naechste=0.9, ende=0.9, durchlaufen=0.5, blick_ankunft=0.5)
    r["naechste"]["weg"] = r["ende"]["weg"] = 3
    assert ev.best_strategy(r) == "naechste"                                              # auch gleicher Weg: Reihenfolge der App
    assert ev.best_strategy(_rows(durchlaufen=0.99)) == "durchlaufen"


def test_verdict_seat_names_best_strategy_gap_and_walk():
    kind, text = ev.verdict_seat(_rows(ende=0.9))
    assert kind == "success"
    assert "**Zugende (Tipp)**" in text and "90 %" in text and "**40 Prozentpunkte**" in text and "(50 %)" in text and "Weg 1 Reihe." in text


def test_verdict_seat_threshold_between_two_and_three_points():
    assert ev.verdict_seat(_rows(ende=0.53))[0] == "success"
    kind, text = ev.verdict_seat(_rows(ende=0.51))
    assert kind == "info" and "50 %" in text and "2 Prozentpunkte" in text
    assert ev.verdict_seat(_rows(naechste=0.9, ende=0.5, durchlaufen=0.5, blick_ankunft=0.5))[0] == "info"   # die Referenz ist die beste


def _pts(*triples):
    return [(phi, n, e, 0.02, 0.02) for phi, n, e in triples]


def test_verdict_phi_crossing_names_gain_and_share():
    kind, text = ev.verdict_phi(_pts((0.0, 0.5, 0.9), (0.1, 0.6, 0.7), (0.2, 0.7, 0.6)))
    assert kind == "warning"
    assert "**40 Prozentpunkte**" in text and "(90 % gegen 50 %)" in text and "etwa **15 %**" in text


def test_verdict_phi_without_advantage_and_never_tipping():
    kind, text = ev.verdict_phi(_pts((0.0, 0.9, 0.91), (0.1, 0.9, 0.8)))
    assert kind == "info" and "höchstens 2 Prozentpunkte" in text and "(91 % gegen 90 % bei" in text
    kind, text = ev.verdict_phi(_pts((0.0, 0.5, 0.9), (0.3, 0.6, 0.8), (0.6, 0.7, 0.75)))
    assert kind == "success" and "60 %" in text and "(90 % gegen 50 % ohne Befolger)" in text


def _psi_rows(*triples):
    return [{"psi": psi, "naechste": dict(sitz=n, se=0.02, weg=3), "durchlaufen": dict(sitz=0.8, se=0.02, weg=5), "blick_ankunft": dict(sitz=b, se=0.02, weg=4)}
            for psi, n, b in triples]


def test_psi_crossing_interpolates_linearly_and_handles_edges():
    assert ev.psi_crossing(_psi_rows((0.0, 0.5, 1.0), (0.2, 0.7, 0.8), (0.4, 0.75, 0.6))) == pytest.approx(0.2 + 0.2 * 0.1 / (0.1 + 0.15))
    assert ev.psi_crossing(_psi_rows((0.0, 0.9, 0.91), (0.2, 0.9, 0.5))) == "kein Vorteil"
    assert ev.psi_crossing(_psi_rows((0.0, 0.5, 1.0), (1.0, 0.6, 0.9))) is None


def test_verdict_psi_texts():
    kind, text = ev.verdict_psi(_psi_rows((0.0, 0.5, 1.0), (0.2, 0.7, 0.8), (0.4, 0.75, 0.6)))
    assert kind == "warning" and "**50 Prozentpunkte**" in text and "(100 % gegen 50 %)" in text and "etwa **28 %**" in text
    kind, text = ev.verdict_psi(_psi_rows((0.0, 0.9, 0.91), (0.2, 0.9, 0.5)))
    assert kind == "info" and "(91 % gegen 90 % bei" in text
    kind, text = ev.verdict_psi(_psi_rows((0.0, 0.5, 1.0), (1.0, 0.6, 0.9)))
    assert kind == "success" and "100 %" in text

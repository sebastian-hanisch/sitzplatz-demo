"""Vorgerechnete Messreihe: Aufbau der Datei, Auswertungsfunktionen an handgesetzten Zellen, und Stichproben, die der Kern exakt wieder erzeugt."""

import pytest

import stz_constants as C
import stz_results as R
from stz_runs import phi_curve, summarize

RES = R.load_results()


def _cell(rows):
    return {"rows": rows}


def test_file_has_the_documented_cells():
    assert len(RES["phi_cells"]) == 576 and len(RES["psi_cells"]) == 64 and len(RES["table_cells"]) == 24
    assert len(RES["oracle_cells"]) == 16 and len(RES["reach_block"]) == 32
    assert {c["advice"] for c in RES["phi_cells"]} == {"ende", "verteilt"}
    assert all(len(c["rows"]) == len(C.CURVE_PHIS) for c in RES["phi_cells"])


def test_cell_star_by_hand():
    assert R.cell_star(_cell([[0.0, 0.5, 0.9, 0.0, 0.0], [0.1, 0.6, 0.7, 0.0, 0.0], [0.2, 0.7, 0.6, 0.0, 0.0]])) == pytest.approx(0.15)
    assert R.cell_star(_cell([[0.0, 0.9, 0.91, 0.0, 0.0], [0.1, 0.9, 0.8, 0.0, 0.0]])) == R.NO_ADVANTAGE
    assert R.cell_star(_cell([[0.0, 0.5, 0.9, 0.0, 0.0], [0.6, 0.6, 0.8, 0.0, 0.0]])) is None


def test_star_summary_counts_add_up_and_order():
    for advice in ("ende", "verteilt"):
        s = R.star_summary(RES, advice)
        assert s["cells"] == s["no_advantage"] + s["never_tips"] + s["with_star"] == 288
        assert 0 < s["min"] <= s["median"] <= s["max"] <= 0.6
    assert R.star_summary(RES, "ende", a=0.0)["no_advantage"] == 72          # ohne Bündelung nie ein Vorsprung


def test_phi_map_shape_and_bundling_zero_row():
    m = R.phi_map(RES, "ende")
    assert m["stairs"] == [0.0, 2.0, 4.0, 8.0] and m["rhos"] == [0.8, 1.0, 1.2]
    assert m["median"][0] == [None, None, None] and m["share_with_advantage"][0] == [0.0, 0.0, 0.0]
    assert all(v == 1.0 for row in m["share_with_advantage"][1:] for v in row[1:])    # a >= 2 und Last >= 100 %: immer ein Vorsprung


def test_psi_star_and_oracle_gap_by_hand():
    cells = [{"psi": 0.0, "res": {"blick_ankunft": {"sitz": 1.0}, "naechste": {"sitz": 0.5}}},
             {"psi": 0.2, "res": {"blick_ankunft": {"sitz": 0.8}, "naechste": {"sitz": 0.7}}},
             {"psi": 0.4, "res": {"blick_ankunft": {"sitz": 0.6}, "naechste": {"sitz": 0.75}}}]
    assert R.psi_star(cells) == pytest.approx(0.2 + 0.2 * 0.1 / (0.1 + 0.15))
    assert R.psi_star(cells[1:]) == pytest.approx(0.2 + 0.2 * 0.1 / 0.25)
    assert R.psi_star([{"psi": 0.0, "res": {"blick_ankunft": {"sitz": 0.91}, "naechste": {"sitz": 0.9}}}]) == R.NO_ADVANTAGE
    og = R.oracle_gap({"oracle_cells": [{"res": {"a": {"sitz": 0.7}, "b": {"sitz": 0.8}, "orakel": {"sitz": 0.8}}},
                                        {"res": {"a": {"sitz": 0.7}, "b": {"sitz": 0.8}, "orakel": {"sitz": 0.85}}}]})
    assert og["cells"] == 2 and og["on_oracle"] == 1 and og["max_gap"] == pytest.approx(0.05)


@pytest.mark.parametrize("index", [0, 287, 431])
def test_phi_cell_is_reproduced_by_the_kernel(index):
    """Stichprobe: die gespeicherte Kurve ist genau das, was der Kern heute rechnet (gleiche Seeds, 100 Läufe)."""
    c = RES["phi_cells"][index]
    p = C.Params(rho=c["rho"], stair_a=c["a"], reach_naive=c["reach"], block=c["block"], advice=c["advice"])
    pts = phi_curve(p, c["s"], 100)
    for got, want in zip(pts, c["rows"]):
        assert got == pytest.approx(tuple(want), abs=1e-12)


def test_psi_cell_is_reproduced_by_the_kernel():
    c = next(x for x in RES["psi_cells"] if x["rho"] == 1.2 and x["phi"] == 0.0 and x["mode"] == "bester" and x["psi"] == 0.4)
    p = C.Params(rho=1.2, stair_a=4.0, reach_naive=20, block=8, phi=0.0, psi=0.4, blick_mode="bester")
    r = summarize(p, 3, 100, strategies=tuple(c["res"]))
    for k, v in c["res"].items():
        assert r[k]["sitz"] == pytest.approx(v["sitz"], abs=1e-12) and r[k]["weg"] == pytest.approx(v["weg"], abs=1e-12)


def test_table_cell_is_reproduced_by_the_kernel_without_the_oracle():
    c = next(x for x in RES["table_cells"] if x["rho"] == 1.2 and x["s"] == 3 and x["block"] == 8)
    p = C.Params(rho=1.2, stair_a=4.0, block=8)
    r = summarize(p, 3, 60, strategies=C.APP_STRATEGIES)
    for k in C.APP_STRATEGIES:
        assert r[k]["sitz"] == pytest.approx(c["res"][k]["sitz"], abs=1e-12)

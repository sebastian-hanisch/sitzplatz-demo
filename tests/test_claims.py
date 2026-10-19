"""Jede Zahl aus README und App-Text, die aus der vorgerechneten Messreihe stammt, wird hier aus data/stz_results.json nachgerechnet.
(Dass die Datei selbst vom Kern reproduziert wird, prüft tests/test_results.py an Stichproben.)"""

import pytest

import stz_results as R

RES = R.load_results()


def test_tip_crossing_over_288_cells_per_tip_kind():
    e, v = R.star_summary(RES, "ende"), R.star_summary(RES, "verteilt")
    assert (e["cells"], e["with_star"], e["no_advantage"], e["never_tips"]) == (288, 198, 90, 0)
    assert round(e["min"], 2) == 0.10 and round(e["median"], 2) == 0.19 and round(e["max"], 2) == 0.30
    assert (v["with_star"], v["no_advantage"]) == (198, 90)
    assert round(v["min"], 2) == 0.10 and round(v["median"], 2) == 0.31 and round(v["max"], 2) == 0.45


def test_bundling_is_the_precondition():
    assert R.star_summary(RES, "ende", a=0.0)["no_advantage"] == 72 and R.star_summary(RES, "ende", a=0.0)["cells"] == 72
    stars = [R.cell_star(c) for c in R.phi_cells(RES, "ende") if c["a"] >= 2 and c["rho"] >= 1.0]
    assert len(stars) == 144 and all(isinstance(s, float) for s in stars)
    assert round(min(stars), 2) == 0.12 and round(max(stars), 2) == 0.30
    wide = [R.cell_star(c) for c in R.phi_cells(RES, "verteilt") if c["a"] >= 2 and c["rho"] >= 1.0]
    assert round(min(wide), 2) == 0.20 and round(max(wide), 2) == 0.45


def test_low_load_often_has_no_advantage():
    assert R.star_summary(RES, "ende", rho=0.8)["no_advantage"] == 42 and R.star_summary(RES, "ende", rho=0.8)["cells"] == 96


def test_blockade_does_not_move_the_crossing():
    a, b = R.star_summary(RES, "ende", block=None), R.star_summary(RES, "ende", block=8)
    assert a["no_advantage"] == b["no_advantage"] == 45
    assert round(a["median"], 2) == round(b["median"], 2) == 0.19


def test_the_advantage_vanishes_when_everyone_walks_far():
    by = {(c["rho"], c["reach"], c["block"]): c for c in R.reach_block_rows(RES)}
    for reach in (60, 80):
        for block in (None, 16, 8, 4):
            assert R.cell_star(by[(1.0, reach, block)]) == R.NO_ADVANTAGE
    c = by[(1.2, 80, None)]
    assert round(c["naechste"], 2) == 0.72 and round(c["ende"], 2) == 0.79
    assert round(R.cell_star(by[(1.2, 20, None)]), 2) == 0.22 and round(R.cell_star(by[(1.0, 40, None)]), 2) == 0.23


def test_strategy_table_at_zero_followers():
    cells = R.table_cells(RES)
    assert len(cells) == 24
    for k in ("ende", "blick_ankunft", "orakel"):
        assert min(c["res"][k]["sitz"] for c in cells) == pytest.approx(1.0, abs=1e-9)
    walk = [c["res"]["durchlaufen"]["sitz"] for c in cells if c["block"] == 8]
    assert round(min(walk), 2) == 0.78 and round(max(walk), 2) == 1.00
    assert all(c["res"]["durchlaufen"]["sitz"] == pytest.approx(1.0, abs=1e-9) for c in cells if c["block"] is None)
    stand = [c["res"]["stehen"]["sitz"] for c in cells]
    assert round(min(stand), 2) == 0.49 and round(max(stand), 2) == 0.67
    naechste = [c["res"]["naechste"]["sitz"] for c in cells]
    assert round(min(naechste), 2) == 0.59 and round(max(naechste), 2) == 1.00


def test_display_experiment_at_load_120():
    best = {c["psi"]: c["res"] for c in R.psi_cell(RES, 1.2, 0.0, "bester")}
    assert [round(best[p]["blick_ankunft"]["sitz"], 2) for p in (0.0, 0.2, 0.4, 1.0)] == [1.0, 0.82, 0.71, 0.60]
    assert [round(best[p]["naechste"]["sitz"], 2) for p in (0.0, 0.2, 0.4, 1.0)] == [0.54, 0.74, 0.78, 0.77]
    assert round(R.psi_star(R.psi_cell(RES, 1.2, 0.0, "bester")), 2) == 0.26
    wtd = {c["psi"]: c["res"] for c in R.psi_cell(RES, 1.2, 0.0, "gewichtet")}
    assert [round(wtd[p]["blick_ankunft"]["sitz"], 2) for p in (0.0, 0.2, 0.4, 1.0)] == [0.99, 0.95, 0.78, 0.74]
    assert [round(wtd[p]["naechste"]["sitz"], 2) for p in (0.0, 0.2, 0.4, 1.0)] == [0.54, 0.62, 0.76, 0.76]
    assert round(R.psi_star(R.psi_cell(RES, 1.2, 0.0, "gewichtet")), 2) == 0.70


def test_display_experiment_with_enough_seats_and_walking_through():
    for mode in ("bester", "gewichtet"):
        cells = R.psi_cell(RES, 1.0, 0.0, mode)
        assert min(c["res"]["blick_ankunft"]["sitz"] for c in cells) >= 0.975
    hard = [c for c in RES["psi_cells"] if c["rho"] == 1.2]
    assert len(hard) == 32 and all(c["res"]["durchlaufen"]["sitz"] >= c["res"]["naechste"]["sitz"] for c in hard)


def test_oracle_cells():
    og = R.oracle_gap(RES)
    assert og["cells"] == 16 and og["on_oracle"] == 14 and round(og["max_gap"], 2) == 0.01

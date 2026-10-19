"""Vorgerechnete Messreihe (data/stz_results.json, erzeugt mit tools/sweep_*.py + tools/dump_sweep.py): Laden und Auswerten.

Die App rechnet die Messreihe nie live; jede Kennzahl hier kommt aus den Einzelzellen der Datei. tests/test_results.py rechnet
Stichproben der Datei mit dem Kern neu nach."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import stz_constants as C
from stz_runs import phi_star

ROOT = Path(__file__).resolve().parent
NO_ADVANTAGE = "kein Vorteil"


def load_results(path=None) -> dict:
    return json.loads(Path(path or ROOT / C.RESULTS_FILE).read_text(encoding="utf-8"))


def cell_star(cell: dict):
    """Kreuzungspunkt phi* einer Zelle: Zahl, 'kein Vorteil' (Vorsprung bei phi = 0 höchstens 0,02) oder None (kippt im Raster nie)."""
    return phi_star([tuple(r) for r in cell["rows"]])


def phi_cells(res: dict, advice: str, **filters) -> list:
    cells = [c for c in res["phi_cells"] if c["advice"] == advice]
    for key, value in filters.items():
        cells = [c for c in cells if c[key] == value]
    return cells


def star_summary(res: dict, advice: str, **filters) -> dict:
    """Zellenzahl, Zellen ohne Vorsprung, Zellen mit Kreuzungspunkt und dessen kleinster/mittlerer (Median)/größter Wert."""
    cells = phi_cells(res, advice, **filters)
    stars = [cell_star(c) for c in cells]
    nums = sorted(s for s in stars if isinstance(s, float))
    return {
        "cells": len(cells),
        "no_advantage": sum(1 for s in stars if s == NO_ADVANTAGE),
        "never_tips": sum(1 for s in stars if s is None),
        "with_star": len(nums),
        "min": nums[0] if nums else None,
        "median": statistics.median(nums) if nums else None,
        "max": nums[-1] if nums else None,
    }


def phi_map(res: dict, advice: str) -> dict:
    """Karte über Bündelung (Zeilen) und Spitzenlast (Spalten): Median phi* und Anteil der Zellen mit Vorsprung,
    gepoolt über Reichweite, Einstiegshalt und Gangblockade."""
    stairs = sorted({c["a"] for c in res["phi_cells"]})
    rhos = sorted({c["rho"] for c in res["phi_cells"]})
    median, share = [], []
    for a in stairs:
        row_m, row_s = [], []
        for rho in rhos:
            cells = phi_cells(res, advice, a=a, rho=rho)
            stars = [cell_star(c) for c in cells]
            nums = [s for s in stars if isinstance(s, float)]
            row_m.append(statistics.median(nums) if nums else None)
            row_s.append(len(nums) / len(cells))
        median.append(row_m)
        share.append(row_s)
    return {"stairs": stairs, "rhos": rhos, "median": median, "share_with_advantage": share}


def psi_cell(res: dict, rho: float, phi: float, mode: str) -> list:
    """Zellen (je psi eine) der vorgerechneten Anzeige-Messreihe, nach psi sortiert."""
    return sorted((c for c in res["psi_cells"] if c["rho"] == rho and c["phi"] == phi and c["mode"] == mode), key=lambda c: c["psi"])


def psi_star(cells: list, strategy: str = "blick_ankunft", reference: str = "naechste"):
    """Erstes psi, ab dem die Strategie nicht mehr vor der Referenz liegt (lineare Interpolation); None, wenn nie."""
    d = [(c["psi"], c["res"][strategy]["sitz"] - c["res"][reference]["sitz"]) for c in cells]
    if d[0][1] <= C.NOISE_NOTE:
        return NO_ADVANTAGE
    for (p0, d0), (p1, d1) in zip(d, d[1:]):
        if d1 <= 0:
            return p0 + (p1 - p0) * d0 / (d0 - d1)
    return None


def table_cells(res: dict) -> list:
    return res["table_cells"]


def oracle_gap(res: dict) -> dict:
    """Abstand der besten Regel zum Orakel in den vorgerechneten Zellen."""
    gaps = []
    for c in res["oracle_cells"]:
        r = c["res"]
        best_rule = max(v["sitz"] for k, v in r.items() if k != "orakel")
        gaps.append(r["orakel"]["sitz"] - best_rule)
    return {"cells": len(gaps), "max_gap": max(gaps), "on_oracle": sum(1 for g in gaps if abs(g) < 0.005)}


def reach_block_rows(res: dict) -> list:
    return res["reach_block"]

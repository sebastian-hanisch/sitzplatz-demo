"""Grenze der Annahme: Was passiert, wenn die Mitreisenden weit laufen (Reichweite bis zum ganzen Zug) und der Gang blockiert sein kann?"""
import itertools
import json
import os
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from stz_constants import Params
from stz_runs import phi_curve, phi_star, summarize


def cell(args):
    reach, block, rho = args
    p = Params(rho=rho, stair_a=4.0, reach_naive=reach, reach_stand=min(reach, 15) if reach < 15 else 15, block=block)
    pts = phi_curve(p, 3, 100)
    tab = summarize(p, 3, 100, strategies=("naechste", "ende", "durchlaufen"))
    return dict(reach=reach, block=block, rho=rho, rows=pts,
                durchlaufen=tab["durchlaufen"]["sitz"], naechste=tab["naechste"]["sitz"], ende=tab["ende"]["sitz"])


if __name__ == "__main__":
    grid = list(itertools.product((20, 40, 60, 80), (None, 16, 8, 4), (1.0, 1.2)))
    out = []
    with Pool(6) as pool:
        for r in pool.imap_unordered(cell, grid):
            out.append(r)
    out.sort(key=lambda r: (r["rho"], r["reach"], r["block"] is not None, -(r["block"] or 0)))
    with open(os.path.join(HERE, "raw", "reach_block.jsonl"), "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print("rho reach block | phi=0: naechste ende durchlaufen | phi*")
    for r in out:
        star = phi_star([tuple(x) for x in r["rows"]])
        star = star if isinstance(star, str) or star is None else f"{star:.2f}"
        print(f"{r['rho']} {r['reach']:>3} {str(r['block']):>4} | {r['naechste']:.2f} {r['ende']:.2f} {r['durchlaufen']:.2f} | {star}")

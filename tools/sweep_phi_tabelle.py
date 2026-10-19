"""AP-0-Neumessung auf dem SplitMix64-Kern. `python sweep_ap0.py phi` (Kreuzungspunkt, 576 Zellen) oder `... tabelle` (alle Strategien + Orakel).
6 Prozesse, nur eigene; schreibt sweep_phi.jsonl bzw. tabelle.jsonl."""
import itertools
import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from stz_constants import APP_STRATEGIES, Params
from stz_runs import phi_curve, summarize

N_PHI = 100
N_TAB = 60


def cell_phi(args):
    a, reach, rho, s, block, advice = args
    p = Params(rho=rho, stair_a=a, reach_naive=reach, block=block, advice=advice)
    pts = phi_curve(p, s, N_PHI)
    return dict(a=a, reach=reach, rho=rho, s=s, block=block, advice=advice, rows=pts)


def cell_tab(args):
    rho, s, block, a = args
    p = Params(rho=rho, stair_a=a, block=block)
    r = summarize(p, s, N_TAB, strategies=APP_STRATEGIES, oracle=True)
    return dict(rho=rho, s=s, block=block, a=a,
                res={k: dict(sitz=v["sitz"], se=v["se"], sofort=v["sofort"], weg=v["weg"]) for k, v in r.items()})


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "phi":
        grid = list(itertools.product((0.0, 2.0, 4.0, 8.0), (10, 20, 30), (0.8, 1.0, 1.2), (2, 3, 4, 5), (None, 8), ("ende", "verteilt")))
        fn, out = cell_phi, "sweep_phi.jsonl"
    else:
        grid = list(itertools.product((0.8, 1.0, 1.2), (2, 3, 4, 5), (None, 8), (4.0,)))
        fn, out = cell_tab, "tabelle.jsonl"
    t0 = time.time()
    with Pool(6) as pool, open(os.path.join(HERE, "raw", out), "w") as f:
        for i, res in enumerate(pool.imap_unordered(fn, grid), 1):
            f.write(json.dumps(res) + "\n")
            f.flush()
            if i % 12 == 0:
                print(i, "/", len(grid), round(time.time() - t0), "s", flush=True)
    print("fertig", round(time.time() - t0), "s")

"""Blick-Anteil psi (Herdeneffekt der Information) und Orakel bei phi > 0. `python psi_sweep.py psi|orakel`."""
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from stz_constants import Params
from stz_runs import summarize

PSIS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0)


def cell_psi(args):
    rho, phi, mode, psi = args
    p = Params(rho=rho, stair_a=4.0, reach_naive=20, block=8, phi=phi, psi=psi, blick_mode=mode)
    r = summarize(p, 3, 100, strategies=("naechste", "ende", "durchlaufen", "blick", "blick_ankunft"))
    return dict(rho=rho, phi=phi, mode=mode, psi=psi,
                res={k: dict(sitz=v["sitz"], se=v["se"], sofort=v["sofort"], weg=v["weg"]) for k, v in r.items()})


def cell_orakel(args):
    rho, phi, s, psi, mode = args
    p = Params(rho=rho, stair_a=4.0, reach_naive=20, block=8, phi=phi, psi=psi, blick_mode=mode)
    r = summarize(p, s, 60, strategies=("naechste", "ende", "durchlaufen", "blick_ankunft"), oracle=True)
    return dict(rho=rho, phi=phi, s=s, psi=psi, mode=mode,
                res={k: dict(sitz=v["sitz"], se=v["se"], sofort=v["sofort"], weg=v["weg"]) for k, v in r.items()})


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "psi":
        grid = list(itertools.product((1.0, 1.2), (0.0, 0.2), ("bester", "gewichtet"), PSIS))
        fn, out = cell_psi, "psi_sweep.jsonl"
    else:
        grid = list(itertools.product((1.0, 1.2), (0.2, 0.4), (3, 4), (0.0, 0.5), ("bester",)))
        fn, out = cell_orakel, "orakel_phi.jsonl"
    t0 = time.time()
    with Pool(6) as pool, open(os.path.join(HERE, "raw", out), "w") as f:
        for i, res in enumerate(pool.imap_unordered(fn, grid), 1):
            f.write(json.dumps(res) + "\n")
            f.flush()
    print("fertig", round(time.time() - t0), "s")

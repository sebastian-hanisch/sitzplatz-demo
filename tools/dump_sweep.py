"""Fasst die Rohdateien der Sweeps (tools/raw/*.jsonl, erzeugt mit sweep_*.py) zu data/stz_results.json zusammen.
Die App rechnet die Messreihe nie live; tests/test_results.py rechnet Stichproben der Datei mit dem Kern neu nach."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(name):
    with open(os.path.join(HERE, "raw", name), encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def key(c, *names):
    return tuple((c[n] is None, c[n]) for n in names)


def main():
    phi = sorted(read("sweep_phi.jsonl"), key=lambda c: key(c, "advice", "a", "reach", "rho", "s", "block"))
    psi = sorted(read("psi_sweep.jsonl"), key=lambda c: key(c, "rho", "phi", "mode", "psi"))
    tab = sorted(read("tabelle.jsonl"), key=lambda c: key(c, "block", "rho", "s"))
    orakel = sorted(read("orakel_phi.jsonl"), key=lambda c: key(c, "rho", "phi", "s", "psi"))
    rb = sorted(read("reach_block.jsonl"), key=lambda c: key(c, "rho", "reach", "block"))
    out = {
        "meta": {
            "runs_phi": 100, "runs_psi": 100, "runs_table": 60, "runs_oracle": 60, "runs_reach_block": 100,
            "note": "Agentenmodell stz_*.py, SplitMix64-Zufallszahlen, gemeinsame Zufallszahlen über alle Strategien und über phi; alle Verhaltensparameter sind Annahmen.",
        },
        "phi_cells": phi, "psi_cells": psi, "table_cells": tab, "oracle_cells": orakel, "reach_block": rb,
    }
    path = os.path.join(ROOT, "data", "stz_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    print(path, os.path.getsize(path), "Bytes;", len(phi), "phi-Zellen,", len(psi), "psi-Zellen,", len(tab), "Tabellenzellen,", len(orakel), "Orakelzellen,", len(rb), "Reichweite-Blockade-Zellen")


if __name__ == "__main__":
    main()

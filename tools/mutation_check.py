"""Fehler-Einbau-Test: mutiert den Kerncode in einer Temp-Kopie und meldet, welche Mutationen die Tests überleben."""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

MUTANTS = [
    ("stz_train.py", "sgn = -1 if dir_bit == 0 else 1", "sgn = 1"),
    ("stz_train.py", "car != start_car and train.standing[car] >= block", "train.standing[car] >= block + 99"),
    ("stz_train.py", "train.free[p.row] += 1", "pass"),
    ("stz_train.py", "key = (abs(r - p.pos), p.order)", "key = (0, p.order)"),
    ("stz_train.py", "if p.row >= 0:\n            p.seat_segments += 1", "if True:\n            p.seat_segments += 1"),
    ("stz_train.py", "idx = sum(1 for x in entries if x.order < focal.pax.order)", "idx = 0"),
    ("stz_crowd.py", "round(1000 * params.stair_a", "round(900 * params.stair_a"),
    ("stz_crowd.py", "if x < c:", "if x <= c:"),
    ("stz_crowd.py", "return pax.informed_draw < round(1000 * params.phi)", "return pax.informed_draw <= round(1000 * params.phi)"),
    ("stz_crowd.py", "cross = (params.stops // 2) * (params.stops - params.stops // 2)", "cross = params.stops"),
    ("stz_crowd.py", "doors[-1] if pax.door_draw % 2 == 0 else doors[-2]", "doors[-1]"),
    ("stz_strategies.py", "ok = take_seat(train, pax, REACH_ALL)", "ok = take_seat(train, pax, params.reach_naive)"),
    ("stz_strategies.py", "ok = False\n        elif n == \"blick\"", "ok = take_seat(train, pax, params.reach_naive)\n        elif n == \"blick\""),
    ("stz_train.py", "out.append(free / (1.0 + comp))", "out.append(free)"),
    ("stz_runs.py", "val = (f.seat_segments, f.first_seat, -f.walk)", "val = (-f.seat_segments, f.first_seat, -f.walk)"),
    ("stz_runs.py", "if d1 <= 0:", "if d1 <= -9:"),
    ("stz_rng.py", "return (self.next() >> 11) / 9007199254740992.0", "return (self.next() >> 12) / 9007199254740992.0"),
    ("stz_crowd.py", "return not is_informed(params, pax) and (pax.order", "return (pax.order"),
    ("stz_train.py", "if x < acc:", "if x <= acc:"),
    ("stz_train.py", "comp = nb * sum(", "comp = 0 * sum("),
    ("stz_train.py", "if sc > scores[best]:", "if sc >= scores[best]:"),
    ("stz_train.py", "reach = min(reach, n)", "reach = min(reach, 1)"),
    ("stz_train.py", "ok = take_seat(train, pax, params.reach_naive) or take_seat(train, pax, REACH_ALL)\n    else:", "ok = take_seat(train, pax, params.reach_naive)\n    else:"),
    ("stz_train.py", "train.scores = door_scores(train, len(entries), weights)", "train.scores = door_scores(train, 0, weights)"),
    ("stz_strategies.py", "pax.pos = blick_door(params, train.scores, pax.door_draw)", "pax.pos = door_blick(train, entries, cum, [1] * len(cum))"),
    ("stz_evaluation.py", "gap < C.NOISE_NOTE", "gap < 0"),
    ("stz_evaluation.py", "return \"warning\", (f\"Allein bringt", "return \"info\", (f\"Allein bringt"),
    ("stz_evaluation.py", "if d[0][1] <= C.NOISE_NOTE:", "if d[0][1] <= -1:"),
    ("stz_evaluation.py", "return f\"{n:.0f} Reihe\" if round(n) == 1", "return f\"{n:.0f} Reihe\" if round(n) == 2"),
    ("stz_results.py", "if d[0][1] <= C.NOISE_NOTE:", "if d[0][1] <= -1:"),
    ("stz_results.py", "return {\"cells\": len(gaps), \"max_gap\": max(gaps)", "return {\"cells\": len(gaps), \"max_gap\": min(gaps)"),
    ("stz_presets.py", "return value if value in spec.options else spec.default", "return value"),
    ("stz_evaluation.py", "return C.SEED_BASE + s.seed * 1000", "return C.SEED_BASE + s.seed * 999"),
    ("stz_train.py", "train.free[hit[0]] == 0", "train.free[hit[0]] == -1"),
    ("stz_train.py", "if block is not None and before == block:", "if False:"),
]


def main():
    survived = []
    for fname, old, new in MUTANTS:
        with tempfile.TemporaryDirectory() as tmp:
            dst = os.path.join(tmp, "repo")
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", "raw"))
            path = os.path.join(dst, fname)
            src = open(path, encoding="utf-8").read()
            if old not in src:
                print("NICHT GEFUNDEN:", fname, old[:50])
                continue
            open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
            try:
                r = subprocess.run([PY, "-m", "pytest", "tests/test_units.py", "tests/test_invariants.py", "tests/test_oracle_sitzplatz.py", "tests/test_verdicts.py", "tests/test_presets.py", "tests/test_results.py", "-k", "not reproduced", "-q", "-x", "-p", "no:cacheprovider"], cwd=dst, capture_output=True, text=True, timeout=240)
                killed = r.returncode != 0
            except subprocess.TimeoutExpired:
                killed = True        # Endlosschleife durch die Mutation: gefunden
            print(("gefunden " if killed else "ÜBERLEBT "), fname, "|", old[:60].replace("\n", " "), flush=True)
            if not killed:
                survived.append((fname, old))
    print(f"\n{len(MUTANTS) - len(survived)} von {len(MUTANTS)} gefunden; überlebt: {len(survived)}")


if __name__ == "__main__":
    main()

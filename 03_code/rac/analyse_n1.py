"""
N1 noise floor: how much does the baseline move between identical re-runs?

METHODOLOGY_BLUEPRINT §3.0.1 -- the minimum detectable effect. Any reported gain
smaller than this is not a result, whatever the mean says.

Two levels are measured and reported separately, because they answer different
questions:

  byte level   -- are the tracker outputs bit-identical across runs?
                  If yes, the pipeline is deterministic and run-to-run variance
                  is exactly zero. That is a *stronger* statement than a small
                  standard deviation, and it must be stated rather than implied.

  metric level -- std of HOTA / IDF1 / MOTA / IDSW across runs.

If the pipeline turns out to be deterministic, a zero noise floor cannot be used
to declare any effect significant. The blueprint's fallback applies: substitute
hyperparameter-perturbation variance as the practical noise scale, since a gain
that vanishes under a 1% threshold nudge is not robust either.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import os
import subprocess

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

TRACKERS = p("04_experiments/trackers/MOT17-val-half")
EVAL = p("03_code/rac/evaluate.sh")


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_summary(name: str) -> dict:
    p = os.path.join(TRACKERS, name, "pedestrian_summary.txt")
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        rows = [l.split() for l in f if l.strip()]
    return {k: float(v) for k, v in zip(rows[0], rows[1])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--evaluate", action="store_true")
    a = ap.parse_args()

    # ---------- byte level ----------
    print("=== byte-level determinism ===")
    seqs = sorted(f[:-4] for f in os.listdir(os.path.join(TRACKERS, a.runs[0], "data"))
                  if f.endswith(".txt"))
    hashes = {r: {s: sha(os.path.join(TRACKERS, r, "data", f"{s}.txt")) for s in seqs}
              for r in a.runs}
    all_same = True
    print(f"{'sequence':<24}" + "".join(f"{r:>14}" for r in a.runs) + "  identical")
    for s in seqs:
        hs = [hashes[r][s][:10] for r in a.runs]
        same = len(set(hashes[r][s] for r in a.runs)) == 1
        all_same &= same
        print(f"{s:<24}" + "".join(f"{h:>14}" for h in hs) + f"  {same}")
    print(f"\nALL sequences bit-identical across {len(a.runs)} runs: {all_same}")

    if a.evaluate:
        for r in a.runs:
            if not os.path.exists(os.path.join(TRACKERS, r, "pedestrian_summary.txt")):
                subprocess.run(["bash", EVAL, r, "12"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---------- metric level ----------
    rows = {r: read_summary(r) for r in a.runs}
    rows = {r: v for r, v in rows.items() if v}
    if not rows:
        print("\n(no summaries found; rerun with --evaluate)")
        return
    keys = ["HOTA", "DetA", "AssA", "MOTA", "IDF1", "IDSW", "Frag", "IDs"]
    df = pd.DataFrame(rows).T[[k for k in keys if k in next(iter(rows.values()))]]
    print("\n=== metric level ===")
    print(df.round(4).to_string())
    print("\nstd across runs (= N1 noise floor):")
    print(df.std(ddof=1).round(6).to_string())
    print("\nmax pairwise spread:")
    print((df.max() - df.min()).round(6).to_string())

    if all_same:
        print("\nINTERPRETATION: the pipeline is DETERMINISTIC under fixed inputs.")
        print("The measured noise floor is exactly 0, which does NOT license calling")
        print("small gains significant. Per METHODOLOGY_BLUEPRINT §3.0.1 the practical")
        print("noise scale must then come from hyperparameter perturbation instead.")


if __name__ == "__main__":
    main()

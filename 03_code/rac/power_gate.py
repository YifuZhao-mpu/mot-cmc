"""
The power gate (METHODOLOGY_BLUEPRINT §3.0.1, kill-switch K5).

    N1 = noise floor      : spread of the baseline across identical re-runs
    N2 = headroom ceiling : metric delta if every compensation error were repaired,
                            measured by substituting the offline reference warp
                            into an otherwise-unmodified tracker

    GATE (user-selected threshold): proceed with MOT17/MOT20 aggregate metrics
    only if  N2 >= 3 x N1.

Decided BEFORE the ablation matrix runs. If the gate fails, the pre-committed
response is to pivot the primary evidence to the robot study and the
reliability-stratified sub-population results, or to add a benchmark with severe
camera motion -- NOT to re-run the gate until it passes (DA-CP1 R3).

Two properties of this particular gate deserve to be stated in the paper:

  * N2 is measured with a NON-CAUSAL instrument that no online tracker can use.
    It is an upper bound on what any online method could recover, ours included.

  * The reference warp is better than the online estimate but is not truth, so
    N2 is itself a LOWER bound on the true headroom (DA-CP1 R1). The two biases
    run in opposite directions and are reported rather than netted off.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

TRACKERS = p("04_experiments/trackers/MOT17-val-half")
METRICS = ["HOTA", "DetA", "AssA", "MOTA", "IDF1", "IDSW", "Frag"]


def summary(name: str) -> dict:
    p = os.path.join(TRACKERS, name, "pedestrian_summary.txt")
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        rows = [l.split() for l in f if l.strip()]
    return {k: float(v) for k, v in zip(rows[0], rows[1])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n1-runs", nargs="+", required=True,
                    help="tracker names of identical baseline repeats")
    ap.add_argument("--baseline", required=True, help="the reference configuration for N2")
    ap.add_argument("--oracle", required=True, help="same config with warp_source=reference")
    ap.add_argument("--threshold", type=float, default=3.0)
    a = ap.parse_args()

    n1 = pd.DataFrame({r: summary(r) for r in a.n1_runs}).T
    n1 = n1[[m for m in METRICS if m in n1.columns]]
    base = summary(a.baseline)
    orac = summary(a.oracle)
    if not base or not orac:
        raise SystemExit("baseline or oracle summary missing -- evaluate them first")

    print("=== N1: baseline across identical re-runs ===")
    print(n1.round(4).to_string())
    noise = n1.std(ddof=1)
    spread = n1.max() - n1.min()
    print("\nstd:"); print(noise.round(6).to_string())
    print("\nmax spread:"); print(spread.round(6).to_string())
    deterministic = bool((spread.abs() < 1e-12).all())
    if deterministic:
        print("\nPipeline is DETERMINISTIC: every repeat produced identical metrics.")
        print("A zero noise floor does not license calling small gains significant;")
        print("the practical noise scale is taken from hyperparameter perturbation instead.")

    print(f"\n=== N2: headroom ceiling ({a.oracle} vs {a.baseline}) ===")
    rows = []
    for m in METRICS:
        if m not in base or m not in orac:
            continue
        d = orac[m] - base[m]
        n = float(noise.get(m, 0.0))
        s = float(spread.get(m, 0.0))
        rows.append(dict(metric=m, baseline=base[m], oracle=orac[m], headroom=d,
                         n1_std=n, n1_spread=s,
                         ratio=(abs(d) / n) if n > 0 else np.inf if abs(d) > 0 else np.nan))
    df = pd.DataFrame(rows)
    print(df.round(4).to_string(index=False))

    print(f"\n=== GATE  (N2 >= {a.threshold} x N1) ===")
    if deterministic:
        print("N1 == 0 exactly, so the ratio test is vacuous. Reporting the raw headroom")
        print("and deferring the gate decision to the perturbation-based noise scale.")
        for _, r in df.iterrows():
            print(f"  {r.metric:>5}: headroom {r.headroom:+.4f}")
    else:
        for _, r in df.iterrows():
            verdict = "PASS" if (np.isfinite(r.ratio) and r.ratio >= a.threshold) else "FAIL"
            print(f"  {r.metric:>5}: headroom {r.headroom:+.4f}  "
                  f"noise {r.n1_std:.4f}  ratio {r.ratio:6.2f}  -> {verdict}")

    out = dict(n1_runs=a.n1_runs, baseline=a.baseline, oracle=a.oracle,
               threshold=a.threshold, deterministic=deterministic,
               n1_std={k: float(v) for k, v in noise.items()},
               n1_spread={k: float(v) for k, v in spread.items()},
               headroom=df.set_index("metric")["headroom"].to_dict(),
               ratio=df.set_index("metric")["ratio"].replace(np.inf, None).to_dict())
    p = p("99_artifacts/power_gate.json")
    json.dump(out, open(p, "w"), indent=1, default=str)
    print(f"\nsaved -> {p}")


if __name__ == "__main__":
    main()

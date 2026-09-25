"""
I2 (confound conditioning) and I3 (placebo) -- completing the K1 battery.

DA-CP1 C1 required three things before any correlation between reliability and
compensation error could be believed:

  I1  oracle-warp contrast        (done: analyse_oracle.py)
  I2  conditioning on detection quality and scene density
  I3  placebo reliability from shuffled statistics

I2 asks: is the relationship between `r` and compensation error an artefact of
both being driven by "hard frame" (many objects, poor detections, fast motion)?
If the relationship survives *within* strata of those confounders, it is not.

I3 asks: would ANY quantity with the same marginal distribution show the same
relationship? If a shuffled `r` correlates as well, the signal is in the
bookkeeping, not the physics.

These are run even though K2 already failed, because they were pre-committed and
because they determine whether the *measurement* contribution (predicting
compensation error) survives even though the *method* contribution did not.
"""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

EPS0 = 1.0


def load() -> pd.DataFrame:
    df = pd.concat([pd.read_csv(f) for f in
                    sorted(glob.glob(p("04_experiments/oracle/*.csv")))],
                   ignore_index=True)
    df = df[df.ref_ok.astype(bool)].copy()
    df["r_eps"] = np.exp(-df["resid_median"].fillna(10.0) / EPS0)
    return df


def strat_report(df: pd.DataFrame, by: str, q: int = 4) -> pd.DataFrame:
    d = df.dropna(subset=[by, "r_eps", "corner_disagreement_px"]).copy()
    if d[by].nunique() < q:
        return pd.DataFrame()
    d["stratum"] = pd.qcut(d[by], q, duplicates="drop")
    rows = []
    for s, g in d.groupby("stratum", observed=True):
        if len(g) < 40:
            continue
        rho, p = spearmanr(g["r_eps"], g["corner_disagreement_px"])
        rows.append(dict(stratum=str(s), n=len(g), spearman=rho, p=p,
                         err_med=g["corner_disagreement_px"].median(),
                         r_med=g["r_eps"].median()))
    return pd.DataFrame(rows)


def main():
    df = load()
    print(f"frames (reference trusted): {len(df)}\n")

    base_rho, _ = spearmanr(df["r_eps"], df["corner_disagreement_px"])
    print(f"=== unconditional: spearman(r_eps, compensation error) = {base_rho:+.4f} ===")

    # ---------------- I2 ----------------
    print("\n=== I2: does it survive conditioning on plausible confounders? ===")
    for name, col in [("scene density (n_gt)", "n_gt"),
                      ("detections in frame", "n_detections"),
                      ("camera displacement magnitude", "displacement"),
                      ("keypoints tracked", "n_used")]:
        if col not in df.columns:
            continue
        r = strat_report(df, col)
        if r.empty:
            continue
        print(f"\n  -- stratified by {name} --")
        print(r.round(4).to_string(index=False))
        worst = r.spearman.max()      # least negative
        print(f"     weakest stratum: {worst:+.4f}   "
              f"{'SURVIVES' if worst < -0.2 else 'DOES NOT SURVIVE'}")

    print("\n  -- within moving-camera sequences only (removes the static/moving split "
          "as an explanation) --")
    mv = df[df.camera == "moving"]
    rho, p = spearmanr(mv["r_eps"], mv["corner_disagreement_px"])
    print(f"     n={len(mv)}  spearman={rho:+.4f}  p={p:.2e}")
    for seq, g in mv.groupby("sequence"):
        rho, p = spearmanr(g["r_eps"], g["corner_disagreement_px"])
        print(f"     {seq:22s} n={len(g):5d}  spearman={rho:+.4f}  p={p:.2e}")

    # ---------------- I3 ----------------
    print("\n=== I3: placebo -- reliability from shuffled statistics ===")
    rng = np.random.default_rng(20260920)
    real, _ = spearmanr(df["r_eps"], df["corner_disagreement_px"])
    null = []
    for _ in range(200):
        null.append(spearmanr(rng.permutation(df["r_eps"].values),
                              df["corner_disagreement_px"].values)[0])
    null = np.array(null)
    print(f"  real          : {real:+.4f}")
    print(f"  placebo mean  : {null.mean():+.4f}   std {null.std():.4f}")
    print(f"  placebo range : [{null.min():+.4f}, {null.max():+.4f}]  (200 permutations)")
    print(f"  VERDICT: {'PASS -- real signal is far outside the placebo distribution' if real < null.min() - 5*null.std() else 'FAIL -- indistinguishable from placebo'}")

    # within-sequence shuffle: harder placebo, preserves sequence-level structure
    within = []
    for _ in range(200):
        vals = df.groupby("sequence")["r_eps"].transform(
            lambda s: rng.permutation(s.values))
        within.append(spearmanr(vals, df["corner_disagreement_px"])[0])
    within = np.array(within)
    print(f"\n  within-sequence placebo mean {within.mean():+.4f} "
          f"std {within.std():.4f} range [{within.min():+.4f}, {within.max():+.4f}]")
    print(f"  VERDICT: {'PASS' if real < within.min() - 5*within.std() else 'FAIL'}")


if __name__ == "__main__":
    main()

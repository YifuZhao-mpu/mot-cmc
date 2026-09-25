"""
DA-CP2 M2 — confidence intervals for the per-target gain.

Every HOTA figure in this project so far is a point estimate. The pedestrian
effect (+0.847) was compared against a "noise scale" (0.738) taken from the span
of a *different* quantity under a *different* perturbation — a proxy, not a test.

This resamples sequences with replacement and recomputes the aggregate gain from
TrackEval's own per-sequence detailed output, giving a percentile CI over the
population of sequences. That is the population the claim generalises to: if the
CI crosses zero, the effect is not established at sequence level, whatever the
pooled number says.

HOTA is averaged over TrackEval's alpha grid, matching how the summary is formed.
Sequences are weighted by their ground-truth detection count, because a pooled
HOTA is not the unweighted mean of per-sequence HOTAs.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

TR = p("04_experiments/trackers/KITTI")
# The oracle rows use the STRICT reference configuration (§5.3): the hybrid runs
# `N2_oracle_warp` / `R_oracle` fell back to the online estimate on 18.2% of
# MOT17-05's validation frames and are retained only for the disclosure table.
# MOT17-11 is a moving-camera sequence; the oracle-contrast scan classifies it so.
MOT17_MOVING = ("MOT17-05-FRCNN", "MOT17-10-FRCNN", "MOT17-11-FRCNN", "MOT17-13-FRCNN")
TR_MOT = p("04_experiments/trackers/MOT17-val-half")


def per_seq(name: str, cls: str, root: str | None = None) -> pd.DataFrame | None:
    p = f"{root or TR}/{name}/{cls}_detailed.csv"
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d = d[d.seq != "COMBINED"].copy()
    hcols = [c for c in d.columns if c.startswith("HOTA___")]
    d["HOTA"] = d[hcols].mean(axis=1) * 100
    keep = ["seq", "HOTA"]
    for c in ("AssA", "DetA", "IDSW", "GT_Dets", "IDs"):
        cc = [x for x in d.columns if x == c or x.startswith(c + "___")]
        if cc:
            d[c] = d[cc].mean(axis=1) * (100 if c in ("AssA", "DetA") else 1)
            keep.append(c)
    return d[keep].set_index("seq")


def bootstrap(a: pd.DataFrame, b: pd.DataFrame, metric: str, w: np.ndarray,
              n_boot: int = 20000, seed: int = 20260922):
    """Weighted-mean difference b - a, resampling sequences with replacement."""
    idx = a.index.intersection(b.index)
    va = a.loc[idx, metric].values.astype(float)
    vb = b.loc[idx, metric].values.astype(float)
    ww = w[: len(idx)] if len(w) >= len(idx) else np.ones(len(idx))
    rng = np.random.default_rng(seed)
    n = len(idx)
    point = (np.average(vb, weights=ww) - np.average(va, weights=ww))
    boots = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.integers(0, n, n)
        boots[i] = np.average(vb[s], weights=ww[s]) - np.average(va[s], weights=ww[s])
    return point, boots, n


def leave_one_out(cls: str, base: str, comp: str, metric: str = "HOTA",
                  root: str | None = None) -> tuple[float, float, float, int, str]:
    """Drop each sequence in turn, under the SAME weighting as the bootstrap.

    An earlier analysis used the unweighted mean of per-sequence deltas here while
    every interval in the paper used the GT-weighted aggregate. Two estimators in
    adjacent sentences is not a robustness check, so this one follows the intervals.
    """
    a, b = per_seq(base, cls, root), per_seq(comp, cls, root)
    idx = a.index.intersection(b.index)
    w = a.loc[idx, "GT_Dets"].values.astype(float)
    va, vb = a.loc[idx, metric].values, b.loc[idx, metric].values
    full = np.average(vb, weights=w) - np.average(va, weights=w)
    out = []
    for i in range(len(idx)):
        m = np.ones(len(idx), bool)
        m[i] = False
        out.append(np.average(vb[m], weights=w[m]) - np.average(va[m], weights=w[m]))
    out = np.asarray(out)
    flips = int((np.sign(out) != np.sign(full)).sum())
    worst = list(idx)[int(np.argmin(np.abs(out)) if flips == 0 else np.argmin(out * np.sign(full)))]
    return float(full), float(out.min()), float(out.max()), flips, str(worst)


def report(cls: str, base: str, comp: str, label: str, n_boot: int,
           root: str | None = None, only: tuple[str, ...] | None = None,
           weighted: bool = True):
    a, b = per_seq(base, cls, root), per_seq(comp, cls, root)
    if only is not None and a is not None and b is not None:
        a, b = a.loc[a.index.isin(only)], b.loc[b.index.isin(only)]
    if a is None or b is None:
        print(f"  {label}: missing ({base} or {comp})")
        return
    idx = a.index.intersection(b.index)
    w = (a.loc[idx, "GT_Dets"].values.astype(float)
         if weighted and "GT_Dets" in a.columns else np.ones(len(idx)))
    ess = w.sum() ** 2 / (w ** 2).sum()
    print(f"\n  --- {label} ---   sequences={len(idx)}"
          f"   ({'weighted by GT detections' if weighted else 'unweighted'},"
          f" effective n = {ess:.2f})")
    for m in ("HOTA", "AssA", "IDSW"):
        if m not in a.columns or m not in b.columns:
            continue
        pt, boots, n = bootstrap(a, b, m, w, n_boot=n_boot)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        frac = (boots > 0).mean() if m != "IDSW" else (boots < 0).mean()
        good = "better" if m != "IDSW" else "fewer"
        crosses = (lo <= 0 <= hi)
        print(f"    {m:>5}: {pt:+8.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]"
              f"   P({good})={frac:.3f}   {'CI CROSSES ZERO' if crosses else 'CI excludes zero'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=20000)
    ap.add_argument("--moving", action="store_true",
                    help="MOT17 restricted to its four moving-camera sequences")
    ap.add_argument("--loo", action="store_true",
                    help="leave-one-sequence-out on the KITTI per-target comparison")
    ap.add_argument("--mot17", action="store_true",
                    help="bootstrap the MOT17 compensation-value axis over its 7 sequences")
    ap.add_argument("--pairs", nargs="*", default=[
        "v3_global_oracle:v3_per_target:per-target vs global oracle (v3)",
        "v3_online:v3_per_target:per-target vs deployable online GMC",
        "v3_none:v3_online:having compensation at all",
    ])
    a = ap.parse_args()
    print("=== bootstrap CI over sequences "
          f"({a.n_boot} resamples, percentile method) ===")
    if a.moving:
        # The pooled MOT17 bound mixes four static sequences, where there is no
        # camera motion to compensate, into an estimate of what compensation is
        # worth. Restricted to the moving-camera sequences the bound is an order
        # of magnitude tighter.
        print("\nMOT17, MOVING-CAMERA SEQUENCES ONLY (05, 10, 11, 13)")
        for base, comp, label in (
            ("A0_frozen", "N2S_oracle_strict", "value of PERFECTING it (motion only)"),
            ("R_online", "R_oracle_strict", "value of PERFECTING it (+ appearance)"),
            ("A_noCMC", "A0_frozen", "value of HAVING compensation (motion only)"),
        ):
            for wt in (True, False):
                report("pedestrian", base, comp, label, a.n_boot, root=TR_MOT,
                       only=MOT17_MOVING, weighted=wt)
        return
    if a.loo:
        print("\nleave-one-sequence-out, GT-weighted (same estimator as the intervals)")
        for cls in ("pedestrian", "car"):
            f, lo, hi, flips, worst = leave_one_out(
                cls, "v4_global_oracle", "v4_per_target")
            print(f"  {cls:11s} full {f:+.4f}   range [{lo:+.4f}, {hi:+.4f}]"
                  f"   sign flips: {flips}   weakest without: {worst}")
        return
    if a.mot17:
        # The negative result needs an interval as much as the positive one does:
        # a small point estimate is only a bound if its uncertainty is bounded too.
        print(f"\n{'='*84}\nMOT17 validation-half, 7 sequences")
        for base, comp, label in (
            ("A_noCMC", "A0_frozen", "value of HAVING compensation (motion only)"),
            ("A0_frozen", "N2S_oracle_strict", "value of PERFECTING it (motion only)"),
            ("A0_frozen", "A0_botsort_baseline", "gap between two ordinary compensators"),
            ("R_none", "R_online", "value of HAVING compensation (+ appearance)"),
            ("R_online", "R_oracle_strict", "value of PERFECTING it (+ appearance)"),
        ):
            report("pedestrian", base, comp, label, a.n_boot, root=TR_MOT)
        return
    for cls in ("pedestrian", "car"):
        print(f"\n{'='*84}\n{cls.upper()}")
        for spec in a.pairs:
            base, comp, label = spec.split(":", 2)
            report(cls, base, comp, label, a.n_boot)


if __name__ == "__main__":
    main()

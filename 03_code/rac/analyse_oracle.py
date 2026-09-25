"""
Analysis of the I1 oracle-warp contrast on real MOT sequences.

Three questions, in order of importance:

  Q1  Does the online compensation actually differ from a better estimate, and
      by how much?  (magnitude of the problem)

  Q2  Do the reliability primitives predict that difference on REAL data, as
      they did on synthetic data?  (does the estimator work outside the lab)

  Q3  Is the difference large enough to change an association decision?
      This is answered geometrically, without running a tracker: a predicted box
      displaced by (dx,dy) has

          IoU(box, box+d) = inter / (2*w*h - inter),
          inter = max(0, w-|dx|) * max(0, h-|dy|)

      BoT-SORT admits appearance evidence only when d_iou < theta_iou = 0.5,
      i.e. IoU > 0.5. For a pure horizontal shift that fails once |dx| > w/3.
      So "fraction of tracked boxes whose IoU is pushed below 0.5 by
      compensation error alone" is a direct, tracker-free lower bound on how
      often the coupling defect can fire.

Frames where the REFERENCE itself is untrustworthy are excluded: contrasting
against a bad reference measures nothing. That exclusion is reported, not hidden.
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

THETA_IOU = 0.5          # BoT-SORT proximity_thresh
N0, EPS0, TAU0 = 300.0, 1.0, 5.0
S0, THETA0 = 0.05, 2.0


def add_reliability(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["rho_n"] = d["inlier_ratio"].fillna(0.0)
    d["n_n"] = np.minimum(1.0, d["n_inliers"] / N0)
    d["eps_n"] = np.exp(-d["resid_median"].fillna(10.0) / EPS0)
    d["tau_n"] = np.exp(-d["temporal_resid"].fillna(50.0) / TAU0)
    d["kappa_n"] = np.exp(-(np.abs(np.log(d["scale"].clip(1e-6))) / S0
                            + np.abs(d["rotation_deg"]) / THETA0))
    d["phi_n"] = 1.0 - d["frac_inliers_in_det"].fillna(0.0)
    sigs = ["rho_n", "n_n", "eps_n", "tau_n", "kappa_n", "phi_n"]
    d["r"] = np.power(np.prod(np.clip(d[sigs].values, 1e-9, 1.0), axis=1), 1.0 / len(sigs))
    d["r_nophi"] = np.power(np.prod(np.clip(d[sigs[:-1]].values, 1e-9, 1.0), axis=1),
                            1.0 / (len(sigs) - 1))
    return d


def iou_after_shift(w: np.ndarray, h: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Worst-case IoU for a shift of magnitude d applied along the box's short
    axis is not well defined without direction, so we use the isotropic case:
    the shift is split evenly between axes (d/sqrt(2) each). Conservative
    relative to a pure single-axis shift of the same magnitude."""
    dx = dy = d / np.sqrt(2.0)
    inter = np.maximum(0.0, w - dx) * np.maximum(0.0, h - dy)
    union = 2.0 * w * h - inter
    return np.where(union > 0, inter / union, 0.0)


def auc(score: np.ndarray, label: np.ndarray) -> float:
    o = np.argsort(score)
    l = np.asarray(label)[o]
    pos, neg = l.sum(), len(l) - l.sum()
    if pos < 2 or neg < 2:
        return float("nan")
    r = np.arange(1, len(l) + 1)
    return float((r[l == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=p("04_experiments/oracle/*.csv"))
    ap.add_argument("--box-stats", default=p("04_experiments/gt_box_stats.csv"))
    a = ap.parse_args()

    files = sorted(glob.glob(a.glob))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = add_reliability(df)
    print(f"loaded {len(files)} sequence files, {len(df)} frames\n")

    # ---------------- reference-trust filter ----------------
    ok = df[df.ref_ok.astype(bool)].copy()
    print("=== reference-warp trust filter ===")
    print(df.groupby(["sequence", "camera"]).agg(
        n=("frame_id", "size"), ref_ok=("ref_ok", "mean"),
        ref_inl=("ref_inliers", "median"), ref_fb=("ref_fb_error", "median"),
    ).round(4).to_string())
    print(f"\nframes retained: {len(ok)}/{len(df)} ({100*len(ok)/len(df):.1f}%)")
    print("Frames where the reference is itself unreliable are EXCLUDED: "
          "contrasting against a bad reference measures nothing.\n")

    # ---------------- Q1: magnitude ----------------
    print("=== Q1  online-vs-reference disagreement (px) ===")
    q = ok.groupby(["sequence", "camera"]).agg(
        n=("frame_id", "size"),
        corner_med=("corner_disagreement_px", "median"),
        corner_p90=("corner_disagreement_px", lambda x: np.percentile(x, 90)),
        corner_max=("corner_disagreement_px", "max"),
        box_med=("box_shift_px", "median"),
        box_p90=("box_shift_px", lambda x: np.percentile(x.dropna(), 90)),
        disp_med=("displacement", "median"),
    ).reset_index()
    print(q.round(3).to_string(index=False))
    print("\nby camera:")
    print(ok.groupby("camera").agg(
        n=("frame_id", "size"),
        corner_med=("corner_disagreement_px", "median"),
        corner_p90=("corner_disagreement_px", lambda x: np.percentile(x, 90)),
        box_med=("box_shift_px", "median"),
    ).round(3).to_string())

    # ---------------- Q2: does r predict it on real data ----------------
    print("\n=== Q2  do the reliability primitives predict real compensation error? ===")
    sigs = ["rho_n", "n_n", "eps_n", "tau_n", "kappa_n", "phi_n", "r_nophi", "r"]
    tgt = ok["corner_disagreement_px"].values
    print(f"{'signal':>10} {'spearman':>9}   (negative = signal falls as error rises = good)")
    for s in sigs:
        c, p = spearmanr(ok[s].values, tgt)
        print(f"{s:>10} {c:>+9.3f}   p={p:.2e}")

    print(f"\n{'threshold':>10} {'n_bad':>7} " + " ".join(f"{s:>9}" for s in sigs))
    for T in [1.0, 2.0, 5.0, 10.0]:
        bad = (ok["corner_disagreement_px"] > T).astype(int).values
        if bad.sum() < 5 or (len(bad) - bad.sum()) < 5:
            continue
        row = " ".join(f"{1-auc(ok[s].values, bad):9.3f}" for s in sigs)
        print(f"{T:>10.1f} {bad.sum():>7} {row}")

    # ---------------- Q3: is it enough to flip a gate ----------------
    print("\n=== Q3  is the error large enough to close BoT-SORT's appearance gate? ===")
    if os.path.exists(a.box_stats):
        bs = pd.read_csv(a.box_stats)
        m = ok.merge(bs, on=["sequence", "frame_id"], how="left")
        w, h, d = m["box_w_med"].values, m["box_h_med"].values, m["box_shift_px"].values
        valid = np.isfinite(w) & np.isfinite(h) & np.isfinite(d)
        iou = np.full(len(m), np.nan)
        iou[valid] = iou_after_shift(w[valid], h[valid], d[valid])
        m["iou_after_cmc_error"] = iou
        m["gate_closed"] = iou < THETA_IOU
        print(m.groupby(["sequence", "camera"]).agg(
            n=("frame_id", "size"),
            box_w_med=("box_w_med", "median"), box_h_med=("box_h_med", "median"),
            shift_med=("box_shift_px", "median"),
            iou_med=("iou_after_cmc_error", "median"),
            iou_p10=("iou_after_cmc_error", lambda x: np.percentile(x.dropna(), 10)),
            gate_closed_frac=("gate_closed", "mean"),
        ).round(4).to_string())
        out = p("04_experiments/oracle_analysis.csv")
        m.to_csv(out, index=False)
        print(f"\nsaved -> {out}")
    else:
        print(f"  (box statistics not found at {a.box_stats}; run gt_box_stats first)")


if __name__ == "__main__":
    main()

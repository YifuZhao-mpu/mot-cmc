"""
Is KITTI's uncompensable motion a per-FRAME property or a per-OBJECT one?

This is the question the whole project turns on. A single global warp — which is
what every tracker applies — can only be right for all objects in a frame if
they all need the same correction. Under translation they do not: displacement
scales with inverse depth, so a near car and a far car in the same frame require
different corrections, and no single 2D warp can serve both.

MOT17 could not show this. There the camera rotates and objects sit at similar
depths, so one warp fits everyone and the residual spread within a frame is
negligible. KITTI is vehicle-mounted, so depth varies by an order of magnitude
within a single frame.

Measured per frame, after the ORACLE best-fit similarity (the best any 4-DOF
compensator could do, fitted to the objects' own true displacements):

  * spread of residuals across objects  -> is one warp enough?
  * correlation of residual with depth  -> is the spread explained by geometry?
  * IoU cost for the worst-affected object, using its true box size
    -> does it reach BoT-SORT's theta_iou = 0.5 gate?
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, project,
    exact_displacement, best_similarity,
)

ROOT = p("04_experiments/data/KITTI/training")
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")
THETA_IOU = 0.5


def iou_shift(w, h, d):
    """IoU between a w x h box and the same box displaced by d (isotropic split)."""
    dx = dy = d / np.sqrt(2.0)
    inter = np.maximum(0.0, w - dx) * np.maximum(0.0, h - dy)
    union = 2.0 * w * h - inter
    return np.where(union > 0, inter / union, 0.0)


def run_sequence(seq: str) -> pd.DataFrame:
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    rows = []
    for k in range(1, len(T_w_cam)):
        prev = [o for o in lab.get(k - 1, [])
                if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0
                and o["occluded"] <= 1 and o["truncated"] < 0.5]
        if len(prev) < 3:
            continue
        X = np.stack([o["xyz"] for o in prev])
        boxes = np.stack([o["tlbr"] for o in prev])
        R, t = relative_motion(T_w_cam, k)
        pts_prev = project(K, X)
        pts_true = exact_displacement(K, R, t, X)
        S = best_similarity(pts_prev, pts_true)
        if S is None:
            continue
        pts_sim = (S[:, :2] @ pts_prev.T).T + S[:, 2]
        err = np.linalg.norm(pts_true - pts_sim, axis=1)

        w = boxes[:, 2] - boxes[:, 0]
        h = boxes[:, 3] - boxes[:, 1]
        iou = iou_shift(w, h, err)
        depth = X[:, 2]
        rho = spearmanr(depth, err)[0] if len(err) >= 4 else np.nan

        rows.append(dict(
            sequence=seq, frame=k, n_obj=len(prev),
            trans_m=float(np.linalg.norm(t)),
            depth_min=float(depth.min()), depth_max=float(depth.max()),
            depth_ratio=float(depth.max() / max(depth.min(), 1e-6)),
            err_med=float(np.median(err)), err_max=float(err.max()),
            err_spread=float(err.max() - err.min()),
            err_iqr=float(np.percentile(err, 75) - np.percentile(err, 25)),
            rho_depth_err=float(rho) if np.isfinite(rho) else np.nan,
            iou_min=float(iou.min()), iou_med=float(np.median(iou)),
            n_gated=int((iou < THETA_IOU).sum()),
            frac_gated=float((iou < THETA_IOU).mean()),
            worst_depth=float(depth[np.argmax(err)]),
            worst_boxw=float(w[np.argmax(err)]),
        ))
    return pd.DataFrame(rows)


def main():
    seqs = sorted(f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    df = pd.concat([run_sequence(s) for s in seqs], ignore_index=True)
    out = p("04_experiments/kitti_per_object.csv")
    df.to_csv(out, index=False)
    pd.set_option("display.width", 200)

    moving = df[df.trans_m > 0.05]
    print(f"=== {len(df)} frames (>=3 objects), {len(moving)} with the vehicle moving ===\n")

    print("=== Q: is ONE warp enough for all objects in a frame? ===")
    print("within-frame residual spread after ORACLE compensation (px):")
    for name, d in [("all frames", df), ("moving only", moving)]:
        q = np.percentile(d.err_spread, [50, 75, 90, 95, 99])
        print(f"  {name:12s} median {q[0]:6.3f}  p75 {q[1]:6.3f}  p90 {q[2]:6.3f}  "
              f"p95 {q[3]:6.3f}  p99 {q[4]:7.3f}  max {d.err_spread.max():8.2f}")
    for T in [1, 2, 5, 10]:
        f = (moving.err_spread > T).mean()
        print(f"  moving frames where objects disagree by > {T:2d} px: "
              f"{100*f:6.2f}%  ({int((moving.err_spread>T).sum())} frames)")

    print("\n=== Q: is the spread explained by depth? ===")
    r = moving.rho_depth_err.dropna()
    print(f"  per-frame spearman(depth, residual): median {r.median():+.3f}  "
          f"frac negative {100*(r<0).mean():.1f}%   n={len(r)}")
    print("  (negative = nearer objects have larger residual, as parallax predicts)")

    print("\n=== Q: does it reach BoT-SORT's gate? ===")
    print(f"  frames with >=1 object pushed below IoU {THETA_IOU}: "
          f"{100*(moving.n_gated>0).mean():.2f}%  ({int((moving.n_gated>0).sum())} frames)")
    tot_obj = int(moving.n_obj.sum())
    tot_gated = int(moving.n_gated.sum())
    print(f"  object-frames gated out by irreducible residual: "
          f"{tot_gated}/{tot_obj} = {100*tot_gated/max(tot_obj,1):.3f}%")
    print("  MOT17 comparison: 34 harmful gate flips / 109,955 pairs = 0.031%")

    print("\n=== where it happens ===")
    hit = moving[moving.n_gated > 0]
    if len(hit):
        print(hit.groupby("sequence").agg(
            frames=("frame", "size"), gated=("n_gated", "sum"),
            trans_med=("trans_m", "median"),
            worst_depth_med=("worst_depth", "median"),
            worst_boxw_med=("worst_boxw", "median"),
            err_max=("err_max", "max")).round(3).to_string())
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()

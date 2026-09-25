"""
How much of KITTI's apparent object motion can NO 2D warp remove?

Runs on ground truth only -- oxts ego-motion, 3D object labels, calibration.
No images, no detector, no tracker. The quantity measured is a property of the
scene geometry and the compensation *model*, not of any implementation.

Three levels are compared, all against the exact projection of the true 3D
motion:

  1. identity            -- no compensation at all
  2. rotation homography -- K R K^-1, the exact warp for the rotational part;
                            this is the best a depth-free warp can do when it
                            knows the true rotation
  3. best-fit similarity -- the 4-DOF transform BoT-SORT's GMC estimates, fitted
                            by least squares to the objects' own true
                            displacements. This is an ORACLE: a real GMC fits to
                            background keypoints and never sees these
                            correspondences, so no online compensator can beat it.

Level 3's residual is the floor. It is the part of the apparent motion that the
compensation *model* cannot express regardless of how well it is estimated —
the distinction that MOT17 could not reveal, because there translation is
negligible and rotation dominates.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, rotation_homography, load_labels,
    project, exact_displacement, homography_prediction, best_similarity,
)

ROOT = p("04_experiments/data/KITTI/training")
MIN_DEPTH = 1.0
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")


def run_sequence(seq: str, classes=EVAL_CLASSES) -> pd.DataFrame:
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    rows = []
    for k in range(1, len(T_w_cam)):
        prev = [o for o in lab.get(k - 1, [])
                if o["cls"] in classes and o["xyz"][2] > MIN_DEPTH
                and o["occluded"] <= 1 and o["truncated"] < 0.5]
        if len(prev) < 2:
            continue
        X = np.stack([o["xyz"] for o in prev])
        R, t = relative_motion(T_w_cam, k)

        pts_prev = project(K, X)
        pts_true = exact_displacement(K, R, t, X)          # exact, from 3D + ego-motion
        pts_rot = homography_prediction(rotation_homography(K, R), pts_prev)

        S = best_similarity(pts_prev, pts_true)            # oracle similarity fit
        if S is None:
            continue
        pts_sim = (S[:, :2] @ pts_prev.T).T + S[:, 2]

        e_id = np.linalg.norm(pts_true - pts_prev, axis=1)
        e_rot = np.linalg.norm(pts_true - pts_rot, axis=1)
        e_sim = np.linalg.norm(pts_true - pts_sim, axis=1)

        rows.append(dict(
            sequence=seq, frame=k, n_obj=len(prev),
            depth_med=float(np.median(X[:, 2])),
            depth_min=float(X[:, 2].min()),
            trans_m=float(np.linalg.norm(t)),
            rot_deg=float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))),
            err_identity_med=float(np.median(e_id)),
            err_identity_max=float(e_id.max()),
            err_rotH_med=float(np.median(e_rot)),
            err_rotH_max=float(e_rot.max()),
            err_bestsim_med=float(np.median(e_sim)),
            err_bestsim_max=float(e_sim.max()),
            err_bestsim_p90=float(np.percentile(e_sim, 90)),
        ))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=p("04_experiments/kitti_parallax.csv"))
    a = ap.parse_args()

    seqs = sorted(f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    dfs = []
    for s in seqs:
        d = run_sequence(s)
        if len(d):
            dfs.append(d)
            print(f"  {s}  {len(d):4d} frames  "
                  f"trans_med {d.trans_m.median():.3f} m  "
                  f"bestsim_med {d.err_bestsim_med.median():6.2f} px", flush=True)
    df = pd.concat(dfs, ignore_index=True)
    df.to_csv(a.out, index=False)

    pd.set_option("display.width", 200)
    print(f"\n=== {len(df)} frames over {df.sequence.nunique()} sequences ===")
    print("\nper-frame MEDIAN object displacement error (px), by compensation model:")
    summ = pd.DataFrame({
        "no compensation": df.err_identity_med.describe(percentiles=[.5, .9]),
        "rotation homography (true R)": df.err_rotH_med.describe(percentiles=[.5, .9]),
        "best-fit similarity (ORACLE)": df.err_bestsim_med.describe(percentiles=[.5, .9]),
    }).T[["50%", "90%", "max"]]
    print(summ.round(3).to_string())

    print("\nwhat the BEST POSSIBLE 4-DOF compensation still leaves, per sequence:")
    g = df.groupby("sequence").agg(
        n=("frame", "size"), trans_med=("trans_m", "median"),
        rot_med=("rot_deg", "median"), depth_med=("depth_med", "median"),
        bestsim_med=("err_bestsim_med", "median"),
        bestsim_p90=("err_bestsim_med", lambda x: np.percentile(x, 90)),
        bestsim_max=("err_bestsim_max", "max"),
    )
    print(g.round(3).to_string())

    print("\n=== how often does the irreducible residual exceed a gate-relevant size? ===")
    for T in [1, 2, 5, 10, 20]:
        f = (df.err_bestsim_med > T).mean()
        print(f"  frames with median irreducible residual > {T:2d} px : "
              f"{100*f:6.2f}%   ({int((df.err_bestsim_med>T).sum())} frames)")

    print("\nFor comparison, MOT17 moving-camera compensation ERROR was 1.31 px (median).")
    print("Here the residual is what remains after PERFECT 4-DOF compensation.")


if __name__ == "__main__":
    main()

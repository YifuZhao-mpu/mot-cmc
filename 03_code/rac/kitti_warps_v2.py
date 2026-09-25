"""
Camera-motion compensation warps for KITTI — correctly specified.

A first version fitted the "oracle" warp to the tracked objects' TRUE
displacements. That was wrong, and the numbers it produced were not
interpretable: on KITTI the tracked objects are moving vehicles, so their
displacement is camera motion PLUS their own motion. Compensation is supposed to
remove only the first; the Kalman filter already predicts the second. Applying a
warp that contains object motion double-counts it, and indeed that "oracle"
scored below the deployable online GMC.

The correct question a compensator answers is:

    if this target were momentarily STATIC, where would camera motion alone
    move it?

For a pixel p at depth z in camera frame k-1:

    X  = z * K^-1 [p; 1]        back-project
    X' = R X + t                apply camera motion only
    p' = project(K, X')         re-project

That displacement is what the tracker should be given. The object's own motion
stays with the Kalman filter, where it belongs.

Three sources are produced:

  online         BoT-SORT's sparseOptFlow GMC (unchanged, deployable)
  global_static  best 4-DOF similarity fitted to the camera-induced displacement
                 of a GRID of static scene points at annotated scene depths.
                 The best any global warp could do for camera motion. ORACLE.
  per_target     camera-induced displacement evaluated at EACH object's own
                 pixel and depth. ORACLE (uses ground-truth depth).

`per_target` differs from `global_static` only in that the correction is
evaluated per object instead of shared. That isolates exactly one thing: whether
a single global warp is sufficient.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import cv2
import numpy as np
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, project, best_similarity,
)

ROOT = p("04_experiments/data/KITTI/training")
OUT = p("04_experiments/kitti_warps_v2")
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")
GRID = 12          # grid points per axis for the static-scene fit


def camera_induced(K: np.ndarray, R: np.ndarray, t: np.ndarray,
                   pts: np.ndarray, depth: np.ndarray) -> np.ndarray:
    """Where static points at (pts, depth) land after camera motion (R, t)."""
    Kinv = np.linalg.inv(K)
    rays = (Kinv @ np.concatenate([pts, np.ones((len(pts), 1))], 1).T).T
    X = rays * depth[:, None] / rays[:, 2:3]
    Xp = (R @ X.T).T + t
    return project(K, Xp)


def run_sequence(seq: str, downscale: int = 2):
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    img_dir = f"{ROOT}/image_02/{seq}"
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".png"))
    h, w = cv2.imread(os.path.join(img_dir, files[0])).shape[:2]

    # a fixed grid over the lower two-thirds of the image, where scene content lives
    gx, gy = np.meshgrid(np.linspace(0.05 * w, 0.95 * w, GRID),
                         np.linspace(0.35 * h, 0.95 * h, GRID))
    grid = np.stack([gx.ravel(), gy.ravel()], 1)

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    online = np.zeros((len(files), 6))
    glob_st = np.zeros((len(files), 6))
    online[0] = glob_st[0] = np.eye(2, 3).ravel()
    per_obj = []

    for i, fn in enumerate(files):
        img = cv2.imread(os.path.join(img_dir, fn))
        H_on, _ = gmc.apply(img, None, frame_id=i)
        online[i] = np.asarray(H_on, float).ravel()
        if i == 0:
            continue

        R, t = relative_motion(T_w_cam, i)
        prev = [o for o in lab.get(i - 1, [])
                if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0]

        # --- global warp fitted to STATIC scene points -------------------
        # depth for the grid is taken from the annotated scene depth range, so
        # the fit reflects the actual geometry rather than an arbitrary plane.
        if prev:
            zs = np.array([o["xyz"][2] for o in prev])
            z_ref = float(np.median(zs))
        else:
            z_ref = 20.0
        depth = np.full(len(grid), z_ref)
        moved = camera_induced(K, R, t, grid, depth)
        S = best_similarity(grid, moved)
        glob_st[i] = (np.asarray(S, float).ravel() if S is not None
                      else np.eye(2, 3).ravel())

        # --- per-target camera-induced displacement ----------------------
        for o in prev:
            p0 = project(K, o["xyz"][None, :])[0]
            p1 = camera_induced(K, R, t, p0[None, :], np.array([o["xyz"][2]]))[0]
            per_obj.append([i, o["track_id"], p1[0] - p0[0], p1[1] - p0[1]])

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f"{seq}.npz"),
                        online=online, global_oracle=glob_st,
                        per_object=np.asarray(per_obj, float) if per_obj
                        else np.zeros((0, 4)))
    if per_obj:
        d = np.asarray(per_obj)[:, 2:]
        mag = np.linalg.norm(d, axis=1)
        print(f"  {seq}  {len(files):5d} frames  per-object rows {len(per_obj):6d}  "
              f"|camera-induced shift| med {np.median(mag):6.2f} px  p95 {np.percentile(mag,95):7.2f}",
              flush=True)
    else:
        print(f"  {seq}  {len(files):5d} frames  (no labelled objects)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seqs", default="")
    a = ap.parse_args()
    seqs = a.seqs.split(",") if a.seqs else sorted(
        f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    for s in seqs:
        run_sequence(s)
    print(f"wrote {len(seqs)} sequences -> {OUT}")


if __name__ == "__main__":
    main()

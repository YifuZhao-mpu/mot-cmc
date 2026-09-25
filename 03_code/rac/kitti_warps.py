"""
Pre-compute the four compensation sources for KITTI, so the tracker can consume
them as frozen inputs exactly like it consumes frozen detections.

  identity      no compensation
  online        BoT-SORT's own sparseOptFlow GMC, bit-identical to the shipped one
  global_oracle the best 4-DOF similarity fitted to the objects' TRUE displacements
                (computed from oxts ego-motion + annotated 3D positions).
                No online compensator can beat this: it is fitted to the answer.
  per_target    each object gets its OWN exact displacement, from its own depth.
                This is the upper bound for the per-target idea the project
                started from, and the configuration MOT17 could not express.

`per_target` is stored as a per-object displacement field keyed by ground-truth
track id; the tracker resolves a detection to a track id by IoU against the
ground-truth boxes. That makes it an **oracle**, clearly labelled: a deployable
method would have to estimate depth, and whether estimated depth is good enough
is a separate question this does not answer.
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
    camera_poses, relative_motion, load_labels, project,
    exact_displacement, best_similarity,
)

ROOT = p("04_experiments/data/KITTI/training")
OUT = p("04_experiments/kitti_warps")
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")


def run_sequence(seq: str, downscale: int = 2):
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    img_dir = f"{ROOT}/image_02/{seq}"
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".png"))

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)

    online = np.zeros((len(files), 6))
    glob_or = np.zeros((len(files), 6))
    online[0] = glob_or[0] = np.eye(2, 3).ravel()
    per_obj = []          # rows: frame, track_id, dx, dy  (displacement of the box centre)

    for i, fn in enumerate(files):
        img = cv2.imread(os.path.join(img_dir, fn))
        H_on, _ = gmc.apply(img, None, frame_id=i)
        online[i] = np.asarray(H_on, float).ravel()

        if i == 0:
            continue
        prev = [o for o in lab.get(i - 1, [])
                if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0]
        if len(prev) < 2:
            glob_or[i] = np.eye(2, 3).ravel()
            continue
        X = np.stack([o["xyz"] for o in prev])
        R, t = relative_motion(T_w_cam, i)
        pts_prev = project(K, X)
        pts_true = exact_displacement(K, R, t, X)

        S = best_similarity(pts_prev, pts_true)
        glob_or[i] = (np.asarray(S, float).ravel() if S is not None
                      else np.eye(2, 3).ravel())

        for o, p0, p1 in zip(prev, pts_prev, pts_true):
            per_obj.append([i, o["track_id"], p1[0] - p0[0], p1[1] - p0[1]])

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f"{seq}.npz"),
                        online=online, global_oracle=glob_or,
                        per_object=np.asarray(per_obj, float) if per_obj
                        else np.zeros((0, 4)))
    print(f"  {seq}  {len(files):5d} frames  per-object rows {len(per_obj):6d}", flush=True)


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

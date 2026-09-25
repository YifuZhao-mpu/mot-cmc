"""
v3 — per-target correction as a full LOCAL SIMILARITY, not just a translation.

v2 left one asymmetry: the global modes applied a 4-DOF similarity (which also
rescales the predicted box), while `per_target` applied a translation only. A
comparison of "global vs per-target" has to change one thing — whether the
correction is shared or per-object — and not also change its form.

Here each object gets a correction of the SAME form as the global one: a 4-DOF
similarity, fitted to the camera-induced motion of that object's own bounding-box
corners, back-projected at that object's own depth.

    corners_prev  -> back-project at depth z -> apply (R, t) -> re-project
    fit 4-DOF similarity  corners_prev -> corners_moved

The object is treated as momentarily static, so the correction contains camera
motion only; its own motion stays with the Kalman filter.

Outputs per sequence:
  online        BoT-SORT sparseOptFlow GMC (deployable)
  global_oracle best similarity fitted to a static grid at the scene's median depth
  per_object    (frame, track_id, a, b, tx, ty) local similarity per object
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import cv2
import numpy as np
import zlib
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, project, best_similarity,
)
from rac.kitti_warps_v2 import camera_induced, GRID  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
OUT = p("04_experiments/kitti_warps_v3")
# Depth-noise study: a deployable method must ESTIMATE depth. Monocular depth
# error is approximately multiplicative, so noise is injected as
#     z' = z * exp(N(0, sigma))
# sigma = 0.10 corresponds to roughly 10% relative depth error.
DEPTH_SIGMA = 0.0
DEPTH_SEED = 0
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")


def box_corners(tlbr: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = tlbr
    return np.array([[x1, y1], [x2, y1], [x1, y2], [x2, y2]], float)


def local_similarity(K, R, t, tlbr, z) -> np.ndarray | None:
    c0 = box_corners(tlbr)
    c1 = camera_induced(K, R, t, c0, np.full(len(c0), z))
    return best_similarity(c0, c1)


def noisy_depth(z: float, rng) -> float:
    if DEPTH_SIGMA <= 0:
        return z
    return float(z * np.exp(rng.normal(0.0, DEPTH_SIGMA)))


def run_sequence(seq: str, downscale: int = 2):
    # zlib.crc32 is stable across processes; Python's hash() is salted per run
    rng = np.random.default_rng(DEPTH_SEED * 1_000_003 + zlib.crc32(seq.encode()))
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    img_dir = f"{ROOT}/image_02/{seq}"
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".png"))
    h, w = cv2.imread(os.path.join(img_dir, files[0])).shape[:2]

    gx, gy = np.meshgrid(np.linspace(0.05 * w, 0.95 * w, GRID),
                         np.linspace(0.35 * h, 0.95 * h, GRID))
    grid = np.stack([gx.ravel(), gy.ravel()], 1)

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    online = np.zeros((len(files), 6))
    glob = np.zeros((len(files), 6))
    globH = np.zeros((len(files), 9))          # DA-CP2 M1: 8-DOF global homography
    online[0] = glob[0] = np.eye(2, 3).ravel()
    globH[0] = np.eye(3).ravel()
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
        z_ref = float(np.median([o["xyz"][2] for o in prev])) if prev else 20.0

        moved = camera_induced(K, R, t, grid, np.full(len(grid), z_ref))
        S = best_similarity(grid, moved)
        glob[i] = np.asarray(S, float).ravel() if S is not None else np.eye(2, 3).ravel()
        # global homography fitted to the SAME static grid -- a richer global model,
        # not a per-target one. This is the cheaper alternative M1 demands be ruled out.
        Hh, _ = cv2.findHomography(grid.astype(np.float32).reshape(-1, 1, 2),
                                   moved.astype(np.float32).reshape(-1, 1, 2),
                                   method=cv2.LMEDS)
        globH[i] = np.asarray(Hh, float).ravel() if Hh is not None else np.eye(3).ravel()

        for o in prev:
            Sl = local_similarity(K, R, t, o["tlbr"], noisy_depth(float(o["xyz"][2]), rng))
            if Sl is None:
                continue
            Sl = np.asarray(Sl, float)
            per_obj.append([i, o["track_id"], Sl[0, 0], Sl[0, 1], Sl[0, 2], Sl[1, 2]])

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f"{seq}.npz"),
                        online=online, global_oracle=glob, global_homography=globH,
                        per_object=np.asarray(per_obj, float) if per_obj
                        else np.zeros((0, 6)))
    if per_obj:
        a = np.asarray(per_obj)
        sc = np.sqrt(a[:, 2] ** 2 + a[:, 3] ** 2)
        sh = np.linalg.norm(a[:, 4:6], axis=1)
        print(f"  {seq}  {len(files):5d} frames  objs {len(per_obj):6d}  "
              f"local scale med {np.median(sc):.4f} p95 {np.percentile(sc,95):.4f}  "
              f"|shift| med {np.median(sh):6.2f} px", flush=True)
    else:
        print(f"  {seq}  {len(files):5d} frames  (no labelled objects)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seqs", default="")
    ap.add_argument("--depth-sigma", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    global DEPTH_SIGMA, DEPTH_SEED, OUT
    DEPTH_SIGMA, DEPTH_SEED = a.depth_sigma, a.seed
    if a.out: OUT = a.out
    seqs = a.seqs.split(",") if a.seqs else sorted(
        f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    for s in seqs:
        run_sequence(s)
    print(f"wrote {len(seqs)} sequences -> {OUT}")


if __name__ == "__main__":
    main()

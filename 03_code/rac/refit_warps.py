"""
Refit the oracle warps after the estimator correction.

Review finding (Critical): `best_similarity` documented itself as least squares
and used `cv2.LMEDS`. LMEDS minimises the *median* squared residual, so on a
frame with three or four annotated objects -- 44.7 % of the frames Section 6.2
measures -- a 4-DOF similarity interpolates two targets exactly and leaves the
rest unfitted. The manuscript called that fit "the best possible", and the
statistic it reports is max-minus-min, which the discarded targets dominate.

`best_similarity` now defaults to least squares, with `robust=True` reserved for
correspondences that genuinely contain outliers. Every warp fitted to *exact*
correspondences therefore changes, and so does every tracking run that consumes
one.

This script refits those bundles in place. It deliberately does NOT recompute
the `online` array: that is read back from the existing bundle byte for byte, so
the deployable estimator is held exactly fixed across the correction and remains
the controlled variable it is supposed to be.

    python refit_warps.py --bundle kitti_warps_v4
"""
from __future__ import annotations

import argparse
import os
import sys
import zlib

import cv2
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, best_similarity,
)
from rac.kitti_warps_v2 import camera_induced, GRID  # noqa: E402
from rac.kitti_warps_v3 import box_corners, EVAL_CLASSES  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")


def local_similarity(K, R, t, tlbr, z):
    c0 = box_corners(tlbr)
    c1 = camera_induced(K, R, t, c0, np.full(len(c0), z))
    return best_similarity(c0, c1)                      # exact corners -> least squares


def refit(bundle: str, depth_sigma: float = 0.0, seed: int = 0) -> None:
    src = p("04_experiments", bundle)
    for f in sorted(os.listdir(src)):
        if not f.endswith(".npz"):
            continue
        seq = f[:-4]
        d = dict(np.load(os.path.join(src, f)))
        n = len(d["online"])                            # kept verbatim
        rng = np.random.default_rng(seed * 1_000_003 + zlib.crc32(seq.encode()))
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
        img_dir = f"{ROOT}/image_02/{seq}"
        f0 = sorted(x for x in os.listdir(img_dir) if x.endswith(".png"))[0]
        h, w = cv2.imread(os.path.join(img_dir, f0)).shape[:2]
        gx, gy = np.meshgrid(np.linspace(0.05 * w, 0.95 * w, GRID),
                             np.linspace(0.35 * h, 0.95 * h, GRID))
        grid = np.stack([gx.ravel(), gy.ravel()], 1)

        glob = np.tile(np.eye(2, 3).ravel(), (n, 1))
        globH = np.tile(np.eye(3).ravel(), (n, 1))
        per_obj = []
        for i in range(1, n):
            R, t = relative_motion(T_w_cam, i)
            prev = [o for o in lab.get(i - 1, [])
                    if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0]
            z_ref = float(np.median([o["xyz"][2] for o in prev])) if prev else 20.0
            moved = camera_induced(K, R, t, grid, np.full(len(grid), z_ref))
            S = best_similarity(grid, moved)            # exact grid -> least squares
            if S is not None:
                glob[i] = np.asarray(S, float).ravel()
            if "global_homography" in d:
                Hh, _ = cv2.findHomography(grid.astype(np.float32).reshape(-1, 1, 2),
                                           moved.astype(np.float32).reshape(-1, 1, 2),
                                           method=cv2.LMEDS)
                if Hh is not None:
                    globH[i] = np.asarray(Hh, float).ravel()
            for o in prev:
                z = float(o["xyz"][2])
                if depth_sigma > 0:
                    z = float(z * np.exp(rng.normal(0.0, depth_sigma)))
                Sl = local_similarity(K, R, t, o["tlbr"], z)
                if Sl is None:
                    continue
                Sl = np.asarray(Sl, float)
                per_obj.append([i, o["track_id"], Sl[0, 0], Sl[0, 1], Sl[0, 2], Sl[1, 2]])

        out = dict(d)
        out["global_oracle"] = glob
        if "global_homography" in d:
            out["global_homography"] = globH
        if "per_object" in d:
            out["per_object"] = np.asarray(per_obj, float) if per_obj else np.zeros((0, 6))
        np.savez_compressed(os.path.join(src, f), **out)
        assert np.array_equal(np.load(os.path.join(src, f))["online"], d["online"]), \
            f"{seq}: the online array must survive the refit unchanged"
        print(f"  {seq}  {n:5d} frames  objs {len(per_obj):6d}", flush=True)
    print(f"\nrefitted -> {src}  (online arrays verified unchanged)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--depth-sigma", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    refit(a.bundle, a.depth_sigma, a.seed)

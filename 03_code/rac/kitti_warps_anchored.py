"""
Is the cheaper intervention "anchor the shared warp at your targets' depth"?

Review raised the paper's own buried result as an objection: on KITTI pedestrians
the deployable image-based GMC (47.428 HOTA) BEATS the global-similarity oracle
(46.744). The proposed explanation is that sparseOptFlow's Shi-Tomasi keypoints
spread over the whole frame, including nearby road surface, so its implicit fit is
weighted toward the near field where pedestrians are -- whereas the "correct"
global oracle is anchored at the scene's MEDIAN depth, which on KITTI is dominated
by distant cars.

If that is right, the practical prescription is not "acquire per-object depth and
go per-target" but "anchor your one global warp at the depth band your targets
occupy" -- which needs a single scalar, not a depth map.

This generates that configuration: the same global 4-DOF similarity fitted to the
same static grid, but with the grid placed at the median depth of ONE CLASS rather
than of all annotated objects. Everything else is identical to kitti_warps_v3.

  global_ped   grid at the median depth of Pedestrian + Cyclist
  global_car   grid at the median depth of Car

Writes 04_experiments/kitti_warps_anchored/<seq>.npz, carrying the v4 `online`
and `per_object` arrays unchanged so the tracker can read one bundle.
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import numpy as np
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import camera_poses, relative_motion, load_labels, best_similarity  # noqa: E402
from rac.kitti_warps_v2 import camera_induced, GRID  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
SRC = p("04_experiments/kitti_warps_v4")
OUT = p("04_experiments/kitti_warps_anchored")
CAR = ("Car",)
PED = ("Pedestrian", "Cyclist")
ALL = CAR + PED + ("Van", "Truck")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    import cv2
    for seq in sorted(s[:-4] for s in os.listdir(f"{ROOT}/oxts") if s.endswith(".txt")):
        src = os.path.join(SRC, f"{seq}.npz")
        if not os.path.exists(src):
            continue
        d = np.load(src)
        n = len(d["global_oracle"])
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
        img_dir = f"{ROOT}/image_02/{seq}"
        f0 = sorted(f for f in os.listdir(img_dir) if f.endswith(".png"))[0]
        h, w = cv2.imread(os.path.join(img_dir, f0)).shape[:2]
        gx, gy = np.meshgrid(np.linspace(0.05 * w, 0.95 * w, GRID),
                             np.linspace(0.35 * h, 0.95 * h, GRID))
        grid = np.stack([gx.ravel(), gy.ravel()], 1)

        out = {"ped": np.zeros((n, 6)), "car": np.zeros((n, 6))}
        out["ped"][0] = out["car"][0] = np.eye(2, 3).ravel()
        zlog = []
        for i in range(1, n):
            R, t = relative_motion(T_w_cam, i)
            prev = [o for o in lab.get(i - 1, []) if o["cls"] in ALL and o["xyz"][2] > 1.0]
            z_all = [o["xyz"][2] for o in prev] or [20.0]
            for key, classes in (("ped", PED), ("car", CAR)):
                z = [o["xyz"][2] for o in prev if o["cls"] in classes]
                z_ref = float(np.median(z)) if z else float(np.median(z_all))
                moved = camera_induced(K, R, t, grid, np.full(len(grid), z_ref))
                S = best_similarity(grid, moved)
                out[key][i] = (np.asarray(S, float).ravel() if S is not None
                               else np.eye(2, 3).ravel())
            zp = [o["xyz"][2] for o in prev if o["cls"] in PED]
            zc = [o["xyz"][2] for o in prev if o["cls"] in CAR]
            if zp and zc:
                zlog.append((np.median(zp), np.median(zc), np.median(z_all)))

        np.savez_compressed(
            os.path.join(OUT, f"{seq}.npz"),
            online=d["online"], per_object=d["per_object"],
            global_oracle=d["global_oracle"], global_homography=d["global_homography"],
            global_ped=out["ped"], global_car=out["car"])
        if zlog:
            a = np.asarray(zlog)
            print(f"  {seq}  frames {n:5d}  median depth: ped {np.median(a[:,0]):6.1f} m"
                  f"  car {np.median(a[:,1]):6.1f} m  all {np.median(a[:,2]):6.1f} m",
                  flush=True)
        else:
            print(f"  {seq}  frames {n:5d}  (no frame with both classes)", flush=True)
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

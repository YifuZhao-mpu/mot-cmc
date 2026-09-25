"""
DA-CP2 M1 — is a richer GLOBAL warp family the fix?

`kitti_model_class.py` fitted each warp family to the objects' own true
displacements. That answers "how expressive is the family?" and NOT "how well
can a compensator do?", because a real compensator never sees those
correspondences — it fits the static background. A homography fitted to the
answer interpolates it (median residual exactly 0.0), which is how the 91.4%
spread-reduction figure arose and why it is not achievable.

This script fits both families to the SAME static grid a compensator would use
(exactly the grid of `kitti_warps_v3.py`), then measures what each leaves behind
at the objects. The comparison is therefore between two DEPLOYABLE global models.

Reported per moving frame:
  residual  median over objects of |predicted - true| displacement at the box centre
  spread    max-min of that residual across objects in the frame

Writes 04_experiments/kitti_global_family.csv
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
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, best_similarity, project,
)
from rac.kitti_per_object import exact_displacement  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
W = p("04_experiments/kitti_warps_v4")
OUT = p("04_experiments/kitti_global_family.csv")
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")
MOVING_M = 0.05          # same threshold as kitti_per_object.py
MIN_OBJ = 3              # same filter as kitti_per_object.py, so spreads are comparable


def apply_sim(S6: np.ndarray, p: np.ndarray) -> np.ndarray:
    S = S6.reshape(2, 3)
    return p @ S[:, :2].T + S[:, 2]


def apply_hom(H9: np.ndarray, p: np.ndarray) -> np.ndarray:
    H = H9.reshape(3, 3)
    q = np.concatenate([p, np.ones((len(p), 1))], 1) @ H.T
    return q[:, :2] / q[:, 2:3]


def main() -> None:
    rows = []
    for seq in sorted(s[:-4] for s in os.listdir(f"{ROOT}/oxts") if s.endswith(".txt")):
        npz = os.path.join(W, f"{seq}.npz")
        if not os.path.exists(npz):
            continue
        d = np.load(npz)
        S_all, H_all = d["global_oracle"], d["global_homography"]
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")

        for i in range(1, len(S_all)):
            # object filter identical to kitti_per_object.py, so the spreads
            # reported here are directly comparable with the oracle study
            prev = [o for o in lab.get(i - 1, [])
                    if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0
                    and o["occluded"] <= 1 and o["truncated"] < 0.5]
            if len(prev) < MIN_OBJ:
                continue
            R, t = relative_motion(T_w_cam, i)
            if float(np.linalg.norm(t)) < MOVING_M:
                continue
            X = np.stack([o["xyz"] for o in prev])
            c0 = project(K, X)
            truth = exact_displacement(K, R, t, X)
            e_sim = np.linalg.norm(apply_sim(S_all[i], c0) - truth, axis=1)
            e_hom = np.linalg.norm(apply_hom(H_all[i], c0) - truth, axis=1)
            # oracle reference on the SAME frames: the best 4-DOF similarity that
            # could be fitted if the objects' own displacements were known
            So = best_similarity(c0, truth)
            e_orc = (np.linalg.norm(apply_sim(np.asarray(So, float).ravel(), c0) - truth, axis=1)
                     if So is not None else e_sim)
            rows.append([int(seq), i, len(prev), float(np.linalg.norm(t)),
                         float(np.median(e_orc)), float(e_orc.max() - e_orc.min()),
                         float(np.median(e_sim)), float(e_sim.max() - e_sim.min()),
                         float(np.median(e_hom)), float(e_hom.max() - e_hom.min())])
        print(f"  {seq}  {len(rows)} rows so far", flush=True)

    a = np.asarray(rows, float)
    hdr = ("sequence,frame,n_obj,trans_m,oracle_med,oracle_spread,"
           "sim_med,sim_spread,hom_med,hom_spread")
    np.savetxt(OUT, a, delimiter=",", header=hdr, comments="", fmt="%.6f")

    print(f"\nmoving frames with >={MIN_OBJ} objects: {len(a)}")
    print(f"{'':22s}{'oracle sim':>12s}{'deploy sim':>12s}{'deploy hom':>12s}"
          f"{'hom vs sim':>12s}")
    for name, co, cs, ch in (("median residual", 4, 6, 8), ("median spread", 5, 7, 9)):
        o, s_, h = np.median(a[:, co]), np.median(a[:, cs]), np.median(a[:, ch])
        print(f"  {name:20s}{o:>11.4f}{s_:>12.4f}{h:>12.4f}{100*(1-h/s_):>11.1f}%")
    fo = (a[:, 5] > 5).mean() * 100
    fs = (a[:, 7] > 5).mean() * 100
    fh = (a[:, 9] > 5).mean() * 100
    print(f"  {'frames spread >5px':20s}{fo:>10.2f}%{fs:>11.2f}%{fh:>11.2f}%"
          f"{fs-fh:>10.2f} pp")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

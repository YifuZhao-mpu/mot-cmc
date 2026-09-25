"""
The shared-warp residual on the benchmarks with no ground-truth ego-motion.

Review finding (Devil's Advocate, Major): the claim that the shared-warp
limitation is negligible on MOT17/MOT20/UAVDT is an argument from
rotation-dominance, not a measurement. Only KITTI was measured. Half the central
claim was asserted for three of the four benchmarks.

It can be measured without ego-motion, with one honest caveat. For every
annotated object present in consecutive frames, take its observed image
displacement, fit the best global 4-DOF similarity to those displacements, and
record the spread of the residual across objects in the frame. That residual
contains the objects' OWN motion as well as the shared-warp error, so the number
is an **upper bound** on the shared-warp residual -- which is exactly the right
direction for the claim being made: if even the upper bound is small, one warp
serves the frame.

The same quantity is computed on KITTI from the same observed displacements, so
the four benchmarks are compared like for like, and against the KITTI figure
obtained from true ego-motion in Section 6.2.

Writes 04_experiments/spread_2d.csv
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import best_similarity  # noqa: E402

DATA = p("04_experiments/data")
OUT = p("04_experiments/spread_2d.csv")
MIN_OBJ = 3


def mot_tracks(gt_path: str) -> dict[int, dict[int, np.ndarray]]:
    """frame -> {track_id: box centre}, visible annotated pedestrians only."""
    a = np.loadtxt(gt_path, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] >= 9:                       # MOT: conf, class, visibility
        a = a[(a[:, 6] > 0) & (a[:, 7] == 1) & (a[:, 8] > 0.3)]
    out: dict[int, dict[int, np.ndarray]] = {}
    for r in a:
        f, tid, x, y, w, h = int(r[0]), int(r[1]), r[2], r[3], r[4], r[5]
        out.setdefault(f, {})[tid] = np.array([x + w / 2, y + h / 2])
    return out


def uavdt_tracks(gt_path: str) -> dict[int, dict[int, np.ndarray]]:
    a = np.loadtxt(gt_path, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    out: dict[int, dict[int, np.ndarray]] = {}
    for r in a:
        f, tid, x, y, w, h = int(r[0]), int(r[1]), r[2], r[3], r[4], r[5]
        out.setdefault(f, {})[tid] = np.array([x + w / 2, y + h / 2])
    return out


def kitti_tracks(lab_path: str) -> dict[int, dict[int, np.ndarray]]:
    out: dict[int, dict[int, np.ndarray]] = {}
    for line in open(lab_path):
        p = line.split()
        if len(p) < 17 or p[2] in ("DontCare",):
            continue
        f, tid = int(p[0]), int(p[1])
        if int(p[4]) > 1 or float(p[3]) >= 0.5:      # occluded / truncated
            continue
        x1, y1, x2, y2 = map(float, p[6:10])
        out.setdefault(f, {})[tid] = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
    return out


def measure(tracks: dict[int, dict[int, np.ndarray]], seq: str, ds: str) -> list:
    rows = []
    for f in sorted(tracks):
        a, b = tracks.get(f - 1), tracks.get(f)
        if not a or not b:
            continue
        ids = sorted(set(a) & set(b))
        if len(ids) < MIN_OBJ:
            continue
        p0 = np.stack([a[i] for i in ids])
        p1 = np.stack([b[i] for i in ids])
        S = best_similarity(p0, p1)
        if S is None:
            continue
        S = np.asarray(S, float)
        pred = p0 @ S[:, :2].T + S[:, 2]
        e = np.linalg.norm(pred - p1, axis=1)
        rows.append([ds, seq, f, len(ids), float(np.median(e)),
                     float(e.max() - e.min())])
    return rows


def main() -> None:
    rows = []
    for ds, root, kind in (("MOT17", f"{DATA}/MOT17/train", "mot"),
                           ("MOT20", f"{DATA}/MOT20/train", "mot"),
                           ("UAVDT", f"{DATA}/UAVDT/mot_layout", "uavdt"),
                           ("KITTI", f"{DATA}/KITTI/training/label_02", "kitti")):
        if not os.path.isdir(root):
            print(f"  {ds}: not present, skipped")
            continue
        if kind == "kitti":
            for f in sorted(os.listdir(root)):
                if f.endswith(".txt"):
                    rows += measure(kitti_tracks(os.path.join(root, f)), f[:-4], ds)
        else:
            for s in sorted(os.listdir(root)):
                if kind == "mot" and "FRCNN" not in s and ds == "MOT17":
                    continue
                gt = os.path.join(root, s, "gt", "gt.txt")
                if not os.path.exists(gt):
                    continue
                t = mot_tracks(gt) if kind == "mot" else uavdt_tracks(gt)
                rows += measure(t, s, ds)
        print(f"  {ds}: {sum(1 for r in rows if r[0] == ds)} frames", flush=True)

    df = pd.DataFrame(rows, columns=["dataset", "sequence", "frame", "n_obj",
                                     "resid_med", "spread"])
    df.to_csv(OUT, index=False)
    print(f"\nwithin-frame spread of the residual after the best-fit GLOBAL similarity")
    print("(upper bound: it also contains the objects' own motion)\n")
    print(f"{'dataset':10s}{'frames':>9s}{'median':>10s}{'p90':>10s}"
          f"{'>2px':>9s}{'>5px':>9s}")
    for ds, g in df.groupby("dataset"):
        print(f"{ds:10s}{len(g):9d}{g.spread.median():10.3f}"
              f"{np.percentile(g.spread, 90):10.3f}"
              f"{100*(g.spread>2).mean():8.2f}%{100*(g.spread>5).mean():8.2f}%")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

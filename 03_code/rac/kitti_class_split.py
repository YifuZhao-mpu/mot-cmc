"""
Section 8 — the two pre-specified explanations for the pedestrian/car split.

Per-target compensation is established on KITTI pedestrians and not on cars, on
the same sequences under the same camera motion. Two explanations were written
down before being measured; this script measures both. Both are refuted, and the
point of committing the script is that the refutations are as reproducible as the
result they fail to explain.

  H1  "pedestrians sit further from the frame's median depth, so the shared
       correction is more wrong for them"
      -> median |log(z_obj / z_frame_median)| per class, plus a one-sided
         Mann-Whitney in the hypothesised direction (pedestrians > cars)

  H2  "pedestrian boxes are smaller, so a given pixel error costs more IoU"
      -> fraction of object-frames where the disagreement between the object's
         own local warp and the shared warp exceeds one third of its box width,
         which is roughly where a pure translation drops IoU below 0.5

Writes 04_experiments/kitti_class_split.csv
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import camera_poses, relative_motion, load_labels  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
W = p("04_experiments/kitti_warps_v4")
OUT = p("04_experiments/kitti_class_split.csv")
CAR = ("Car",)
PED = ("Pedestrian", "Cyclist")
MOVING_M = 0.05


def apply_sim(S6: np.ndarray, p: np.ndarray) -> np.ndarray:
    S = S6.reshape(2, 3)
    return p @ S[:, :2].T + S[:, 2]


def main() -> None:
    rows = []
    for seq in sorted(s[:-4] for s in os.listdir(f"{ROOT}/oxts") if s.endswith(".txt")):
        npz = os.path.join(W, f"{seq}.npz")
        if not os.path.exists(npz):
            continue
        d = np.load(npz)
        shared, per_obj = d["global_oracle"], d["per_object"]
        # per_object rows are (frame, track_id, a, b, tx, ty)
        by_frame: dict[int, dict[int, np.ndarray]] = {}
        for r in per_obj:
            by_frame.setdefault(int(r[0]), {})[int(r[1])] = r[2:]
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")

        for i in range(1, len(shared)):
            R, t = relative_motion(T_w_cam, i)
            if float(np.linalg.norm(t)) < MOVING_M:
                continue
            objs = [o for o in lab.get(i - 1, [])
                    if o["cls"] in CAR + PED and o["xyz"][2] > 1.0]
            if len(objs) < 2:
                continue
            z_med = float(np.median([o["xyz"][2] for o in objs]))
            local = by_frame.get(i, {})
            for o in objs:
                cx = (o["tlbr"][0] + o["tlbr"][2]) / 2
                cy = (o["tlbr"][1] + o["tlbr"][3]) / 2
                w = float(o["tlbr"][2] - o["tlbr"][0])
                c = np.array([[cx, cy]])
                own = local.get(int(o["track_id"]))
                if own is None:
                    continue
                own6 = np.array([own[0], own[1], own[2], -own[1], own[0], own[3]])
                disagree = float(np.linalg.norm(
                    apply_sim(own6, c) - apply_sim(shared[i], c)))
                rows.append([int(seq), i, int(o["track_id"]),
                             "car" if o["cls"] in CAR else "ped",
                             float(o["xyz"][2]), z_med, w, disagree])
        print(f"  {seq}  {len(rows)} object-frames so far", flush=True)

    df = pd.DataFrame(rows, columns=["sequence", "frame", "track_id", "cls",
                                     "z", "z_frame_median", "box_w", "disagree_px"])
    df["log_z_ratio"] = np.abs(np.log(df.z / df.z_frame_median))
    df["exposed"] = df.disagree_px > df.box_w / 3.0
    df.to_csv(OUT, index=False)

    print(f"\n{'':6s}{'n':>8s}{'med |log(z/z_med)|':>22s}{'exposed > w/3':>16s}")
    for c in ("car", "ped"):
        g = df[df.cls == c]
        print(f"  {c:4s}{len(g):8d}{g.log_z_ratio.median():22.4f}"
              f"{g.exposed.mean()*100:15.2f}%")

    car, ped = df[df.cls == "car"].log_z_ratio, df[df.cls == "ped"].log_z_ratio
    u, p = mannwhitneyu(ped, car, alternative="greater")
    print(f"\nH1  'pedestrians further from frame-median depth'")
    print(f"    one-sided Mann-Whitney (ped > car): p = {p:.4f}"
          f"  -> {'SUPPORTED' if p < 0.05 else 'REFUTED'}")
    print(f"H2  'pedestrian boxes more exposed per unit error'")
    ec, ep = df[df.cls == 'car'].exposed.mean(), df[df.cls == 'ped'].exposed.mean()
    print(f"    car {ec*100:.2f}% vs ped {ep*100:.2f}%"
          f"  -> {'SUPPORTED' if ep > ec else 'REFUTED'}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

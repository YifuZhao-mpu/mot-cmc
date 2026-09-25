"""
A depth-confounded-robust indicator of whether a benchmark's camera translates.

Two review findings converge here. The Devil's Advocate objected that the
shared-warp limitation is measured only on KITTI and argued away elsewhere.
Perspective asked for a dimensionless number that lets a reader place their own
footage on the rotation-versus-translation axis the whole argument rests on.

`depth_ratio_scan.py` rules out the explanation the paper had been using: MOT17
and MOT20 targets span a LARGER within-frame depth ratio than KITTI's (median
5.60 and 6.51 against 3.57), so depth uniformity is not what protects them.

What distinguishes them is camera translation, and that is directly testable
without ego-motion. Under pure rotation the induced image motion is
`H = K R K^-1`, independent of depth, so a target's residual after the best
global warp carries NO depth signal however widely the depths are spread. Under
translation the residual scales with inverse depth. So:

    indicator = Spearman( estimated depth , residual after the best global fit )
                per frame, over the frame's targets

Objects' own motion enters the residual but is uncorrelated with their depth, so
it dilutes the statistic toward zero rather than manufacturing it. A clearly
negative median is evidence of translation; a median near zero is evidence
against it. On KITTI the same statistic computed from ground truth is -0.400.

Writes 04_experiments/parallax_indicator.csv
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import cv2
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "Depth-Anything-V2/metric_depth"))
from rac.kitti_egomotion import best_similarity  # noqa: E402
from rac.depth_ratio_scan import mot_boxes, kitti_boxes, load_model  # noqa: E402

DATA = p("04_experiments/data")
OUT = p("04_experiments/parallax_indicator.csv")
MIN_OBJ = 4          # Spearman needs four points


def mot_tracks(gt: str) -> dict[int, dict[int, tuple]]:
    a = np.loadtxt(gt, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] >= 9:
        a = a[(a[:, 6] > 0) & (a[:, 7] == 1) & (a[:, 8] > 0.3)]
    out: dict[int, dict[int, tuple]] = {}
    for r in a:
        out.setdefault(int(r[0]), {})[int(r[1])] = (r[2], r[3], r[4], r[5])
    return out


def kitti_tracks(lab: str) -> dict[int, dict[int, tuple]]:
    out: dict[int, dict[int, tuple]] = {}
    for line in open(lab):
        p = line.split()
        if len(p) < 17 or p[2] == "DontCare" or int(p[4]) > 1 or float(p[3]) >= 0.5:
            continue
        x1, y1, x2, y2 = map(float, p[6:10])
        out.setdefault(int(p[0]), {})[int(p[1])] = (x1, y1, x2 - x1, y2 - y1)
    return out


def run(model, ds: str, seq: str, img_dir: str, tracks: dict, stride: int) -> list:
    import torch
    files = sorted(f for f in os.listdir(img_dir)
                   if f.lower().endswith((".jpg", ".png")))
    rows = []
    for k in range(stride, len(files), stride):
        f = k + 1
        a, b = tracks.get(f - 1), tracks.get(f)
        if not a or not b:
            continue
        ids = sorted(set(a) & set(b))
        if len(ids) < MIN_OBJ:
            continue
        img_prev = cv2.imread(os.path.join(img_dir, files[k - 1]))
        if img_prev is None:
            continue
        with torch.no_grad():
            dm = model.infer_image(img_prev, 518)
        h, w = dm.shape
        c0, c1, z = [], [], []
        for i in ids:
            x, y, bw, bh = a[i]
            x2, y2, bw2, bh2 = b[i]
            cx, cy = int(np.clip(x + bw / 2, 0, w - 1)), int(np.clip(y + bh * 0.95, 0, h - 1))
            v = float(dm[cy, cx])
            if not (np.isfinite(v) and v > 0.5):
                continue
            c0.append([x + bw / 2, y + bh / 2])
            c1.append([x2 + bw2 / 2, y2 + bh2 / 2])
            z.append(v)
        if len(z) < MIN_OBJ:
            continue
        c0, c1, z = np.asarray(c0), np.asarray(c1), np.asarray(z)
        S = best_similarity(c0, c1)
        if S is None:
            continue
        S = np.asarray(S, float)
        e = np.linalg.norm(c0 @ S[:, :2].T + S[:, 2] - c1, axis=1)
        rho = spearmanr(z, e)[0]
        if not np.isfinite(rho):
            continue
        rows.append([ds, seq, f, len(z), float(np.median(z)),
                     float(z.max() / max(z.min(), 1e-6)), float(rho)])
    print(f"    {ds}/{seq}: {len(rows)} frames", flush=True)
    return rows


def main() -> None:
    model = load_model()
    rows = []
    for ds, root, stride in (("MOT17", f"{DATA}/MOT17/train", 10),
                             ("MOT20", f"{DATA}/MOT20/train", 10),
                             ("UAVDT", f"{DATA}/UAVDT/mot_layout", 60)):
        if not os.path.isdir(root):
            continue
        for s in sorted(os.listdir(root)):
            if ds == "MOT17" and "FRCNN" not in s:
                continue
            gt, img = os.path.join(root, s, "gt", "gt.txt"), os.path.join(root, s, "img1")
            if os.path.exists(gt) and os.path.isdir(img):
                rows += run(model, ds, s, img, mot_tracks(gt), stride)
    kroot = f"{DATA}/KITTI/training"
    for s in sorted(os.listdir(f"{kroot}/label_02")):
        if s.endswith(".txt"):
            rows += run(model, "KITTI", s[:-4], f"{kroot}/image_02/{s[:-4]}",
                        kitti_tracks(f"{kroot}/label_02/{s}"), 10)

    df = pd.DataFrame(rows, columns=["dataset", "sequence", "frame", "n_obj",
                                     "depth_med", "depth_ratio", "rho_depth_resid"])
    df.to_csv(OUT, index=False)
    print("\nSpearman(target depth, residual after the best global similarity), per frame")
    print("negative => residual grows as depth shrinks => the camera translates\n")
    print(f"{'dataset':10s}{'frames':>8s}{'median rho':>12s}{'frac < 0':>10s}"
          f"{'frac < -0.3':>13s}{'depth ratio':>13s}")
    for ds in ("MOT17", "MOT20", "UAVDT", "KITTI"):
        g = df[df.dataset == ds]
        if not len(g):
            continue
        r = g.rho_depth_resid
        print(f"{ds:10s}{len(g):8d}{r.median():12.3f}{100*(r<0).mean():9.1f}%"
              f"{100*(r<-0.3).mean():12.1f}%{g.depth_ratio.median():13.2f}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

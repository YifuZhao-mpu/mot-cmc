"""
How much do the targets in one frame differ in depth?

Review finding (Devil's Advocate, Major): the paper measures the shared-warp
residual only on KITTI and *argues* it away on MOT17, MOT20 and UAVDT from
rotation-dominance. The direct residual cannot be measured there -- no
ground-truth ego-motion, and observed object displacements are swamped by the
objects' own motion (see `spread_2d.py`, which is reported as a measurement that
fails to discriminate).

What CAN be measured is the quantity that drives the limitation: the spread of
target DEPTH within a frame. A shared warp is wrong for a frame's targets in
proportion to how much their depths differ, so the within-frame depth ratio is
the structural precondition. It is estimated here with the same monocular network
Section 7 uses, queried at each annotated target's lower-centre (its contact
point, the most reliable place to read depth for a standing or road-borne object).

Frames are subsampled; the statistic is a distribution over frames, not a total.

Writes 04_experiments/depth_ratio.csv
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys

import cv2
import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "Depth-Anything-V2/metric_depth"))

DATA = p("04_experiments/data")
OUT = p("04_experiments/depth_ratio.csv")
CKPT = p("04_experiments/weights/depth_anything_v2_metric_vkitti_vitl.pth")
MIN_OBJ = 3


def load_model():
    import torch
    from depth_anything_v2.dpt import DepthAnythingV2
    m = DepthAnythingV2(encoder="vitl", features=256,
                        out_channels=[256, 512, 1024, 1024], max_depth=80)
    m.load_state_dict(torch.load(CKPT, map_location="cpu"))
    return m.to("cuda").eval()


def mot_boxes(gt: str) -> dict[int, list]:
    a = np.loadtxt(gt, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] >= 9:
        a = a[(a[:, 6] > 0) & (a[:, 7] == 1) & (a[:, 8] > 0.3)]
    out: dict[int, list] = {}
    for r in a:
        out.setdefault(int(r[0]), []).append((r[2], r[3], r[4], r[5]))
    return out


def kitti_boxes(lab: str) -> dict[int, list]:
    out: dict[int, list] = {}
    for line in open(lab):
        p = line.split()
        if len(p) < 17 or p[2] == "DontCare" or int(p[4]) > 1 or float(p[3]) >= 0.5:
            continue
        x1, y1, x2, y2 = map(float, p[6:10])
        out.setdefault(int(p[0]), []).append((x1, y1, x2 - x1, y2 - y1))
    return out


def scan(model, ds: str, seqs: list[tuple[str, str, dict]], stride: int) -> list:
    import torch
    rows = []
    for seq, img_dir, boxes in seqs:
        files = sorted(f for f in os.listdir(img_dir)
                       if f.lower().endswith((".jpg", ".png")))
        for k in range(0, len(files), stride):
            f = k + 1
            bs = boxes.get(f, [])
            if len(bs) < MIN_OBJ:
                continue
            img = cv2.imread(os.path.join(img_dir, files[k]))
            if img is None:
                continue
            with torch.no_grad():
                dm = model.infer_image(img, 518)
            h, w = dm.shape
            z = []
            for x, y, bw, bh in bs:
                cx = int(np.clip(x + bw / 2, 0, w - 1))
                cy = int(np.clip(y + bh * 0.95, 0, h - 1))
                v = float(dm[cy, cx])
                if np.isfinite(v) and v > 0.5:
                    z.append(v)
            if len(z) < MIN_OBJ:
                continue
            z = np.asarray(z)
            rows.append([ds, seq, f, len(z), float(z.min()), float(z.max()),
                         float(z.max() / max(z.min(), 1e-6)),
                         float(np.median(np.abs(np.log(z / np.median(z)))))])
        print(f"    {ds}/{seq}: {sum(1 for r in rows if r[1] == seq)} frames", flush=True)
    return rows


def main() -> None:
    model = load_model()
    rows = []
    for ds, root, stride in (("MOT17", f"{DATA}/MOT17/train", 10),
                             ("MOT20", f"{DATA}/MOT20/train", 10),
                             ("UAVDT", f"{DATA}/UAVDT/mot_layout", 60)):
        if not os.path.isdir(root):
            continue
        seqs = []
        for s in sorted(os.listdir(root)):
            if ds == "MOT17" and "FRCNN" not in s:
                continue
            gt, img = os.path.join(root, s, "gt", "gt.txt"), os.path.join(root, s, "img1")
            if os.path.exists(gt) and os.path.isdir(img):
                seqs.append((s, img, mot_boxes(gt)))
        rows += scan(model, ds, seqs, stride)
    kroot = f"{DATA}/KITTI/training"
    seqs = [(s[:-4], f"{kroot}/image_02/{s[:-4]}", kitti_boxes(f"{kroot}/label_02/{s}"))
            for s in sorted(os.listdir(f"{kroot}/label_02")) if s.endswith(".txt")]
    rows += scan(model, "KITTI", seqs, 10)

    df = pd.DataFrame(rows, columns=["dataset", "sequence", "frame", "n_obj",
                                     "z_min", "z_max", "depth_ratio", "log_spread"])
    df.to_csv(OUT, index=False)
    print(f"\nwithin-frame target depth ratio (monocular estimate at the contact point)\n")
    print(f"{'dataset':10s}{'frames':>8s}{'median':>10s}{'p75':>9s}{'p90':>9s}"
          f"{'>1.5x':>9s}{'>2x':>9s}{'>3x':>9s}")
    for ds in ("MOT17", "MOT20", "UAVDT", "KITTI"):
        g = df[df.dataset == ds]
        if not len(g):
            continue
        r = g.depth_ratio
        print(f"{ds:10s}{len(g):8d}{r.median():10.2f}{np.percentile(r,75):9.2f}"
              f"{np.percentile(r,90):9.2f}{100*(r>1.5).mean():8.1f}%"
              f"{100*(r>2).mean():8.1f}%{100*(r>3).mean():8.1f}%")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

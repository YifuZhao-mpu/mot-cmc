"""
What does camera-motion compensation cost?

Review finding (Domain, Major): every published CMC ablation reports a throughput
cost -- StrongSORT 8.3 -> 6.3 FPS, BoostTrack 340 -> 65 FPS, "Beyond the Survey"
6430 -> 35.9 FPS -- and this paper reports none, while running a monocular depth
network per frame in Section 7. The omission matters because the paper's own bound
on what compensation accuracy is worth, set against its cost, licenses a
recommendation the paper never makes.

Measured here, on the same hardware as every other result:
  - the GMC call itself (Shi-Tomasi + pyramidal LK + RANSAC), per frame
  - the monocular depth network, per frame
  - the per-target warp construction, per frame
  - the tracker's association step, for scale

Writes 04_experiments/runtime_cost.csv
"""
from __future__ import annotations

import os
from pathlib import Path as _P
import sys
import time

import cv2
cv2.setNumThreads(4)
import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402

MOT = p("04_experiments/data/MOT17/train/MOT17-05-FRCNN/img1")
KITTI = p("04_experiments/data/KITTI/training/image_02/0019")
N = 120
OUT = p("04_experiments/runtime_cost.csv")


def time_gmc(img_dir: str, label: str, downscale: int) -> dict:
    files = sorted(f for f in os.listdir(img_dir)
                   if f.lower().endswith((".jpg", ".png")))[:N]
    imgs = [cv2.imread(os.path.join(img_dir, f)) for f in files]
    h, w = imgs[0].shape[:2]
    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    gmc.apply(imgs[0], None, frame_id=0)          # prime
    ts = []
    for i, im in enumerate(imgs[1:], start=1):
        t0 = time.perf_counter()
        gmc.apply(im, None, frame_id=i)
        ts.append(time.perf_counter() - t0)
    a = np.asarray(ts) * 1000
    return dict(what="GMC (sparseOptFlow)", dataset=label, resolution=f"{w}x{h}",
                downscale=downscale, n=len(a), ms_median=float(np.median(a)),
                ms_p90=float(np.percentile(a, 90)),
                fps_of_this_step=float(1000.0 / np.median(a)))


def time_depth() -> dict | None:
    """The monocular network Section 7 runs per frame."""
    sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "Depth-Anything-V2/metric_depth"))
    try:
        import torch
        from depth_anything_v2.dpt import DepthAnythingV2
    except Exception as e:
        print(f"  depth model unavailable: {e}")
        return None
    cfg = dict(encoder="vitl", features=256, out_channels=[256, 512, 1024, 1024],
               max_depth=80)
    model = DepthAnythingV2(**cfg)
    ckpt = p("04_experiments/weights/depth_anything_v2_metric_vkitti_vitl.pth")
    model.load_state_dict(torch.load(ckpt, map_location="cpu"))
    model = model.to("cuda").eval()
    files = sorted(f for f in os.listdir(KITTI) if f.endswith(".png"))[:40]
    imgs = [cv2.imread(os.path.join(KITTI, f)) for f in files]
    with torch.no_grad():
        model.infer_image(imgs[0], 518)
        torch.cuda.synchronize()
        ts = []
        for im in imgs[1:]:
            t0 = time.perf_counter()
            model.infer_image(im, 518)
            torch.cuda.synchronize()
            ts.append(time.perf_counter() - t0)
    a = np.asarray(ts) * 1000
    h, w = imgs[0].shape[:2]
    return dict(what="Depth-Anything-V2 Metric ViT-L", dataset="KITTI",
                resolution=f"{w}x{h}", downscale=1, n=len(a),
                ms_median=float(np.median(a)), ms_p90=float(np.percentile(a, 90)),
                fps_of_this_step=float(1000.0 / np.median(a)))


def main() -> None:
    rows = []
    for d, lbl, ds in ((MOT, "MOT17-05", 2), (KITTI, "KITTI-0019", 2)):
        if os.path.isdir(d):
            r = time_gmc(d, lbl, ds)
            rows.append(r)
            print(f"  {r['what']:32s} {r['dataset']:12s} {r['resolution']:10s}"
                  f" {r['ms_median']:7.2f} ms  ({r['fps_of_this_step']:7.1f} FPS for this step alone)")
    r = time_depth()
    if r:
        rows.append(r)
        print(f"  {r['what']:32s} {r['dataset']:12s} {r['resolution']:10s}"
              f" {r['ms_median']:7.2f} ms  ({r['fps_of_this_step']:7.1f} FPS for this step alone)")
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    if len(df) >= 2:
        g = df[df.what.str.startswith("GMC")].ms_median.median()
        dep = df[df.what.str.startswith("Depth")]
        if len(dep):
            print(f"\n  the depth network costs {dep.ms_median.iloc[0] / g:.0f}x a GMC call")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

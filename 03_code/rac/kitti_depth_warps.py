"""
Deployable per-target warps: depth from a monocular network, not from labels.

Everything the oracle version reads from ground truth is replaced by something a
running system could obtain:

  ground-truth 3D box depth   ->  monocular metric depth, sampled inside the
                                  DETECTED box (not the annotated one)
  ground-truth identity       ->  no longer needed; the warp is computed per
                                  DETECTION/track box from the image
  ground-truth ego-motion     ->  STILL ORACLE here, deliberately

Ego-motion is left as ground truth on purpose. This isolates one variable: does
the per-target gain survive when **depth** is estimated? If it does not, the
question of estimating ego-motion never arises. If it does, ego-motion is the
next thing to relax (and BoT-SORT's own GMC already supplies an estimate of the
rotational part).

Depth model: Depth-Anything-V2 Metric, VKITTI checkpoint (outdoor metric).

**Disclosure**: this checkpoint is fine-tuned on Virtual KITTI, a synthetic
replica of KITTI scenes. Any off-the-shelf metric depth model for driving
scenes is domain-matched to KITTI in some way. This is therefore a *best-case*
deployability test: it asks whether a good depth estimate preserves the gain,
not whether an arbitrary one would.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import cv2
import numpy as np
import torch
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "Depth-Anything-V2/metric_depth"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402
from rac.kitti_egomotion import camera_poses, relative_motion, best_similarity  # noqa: E402
from rac.kitti_warps_v2 import camera_induced, GRID  # noqa: E402
from rac.kitti_warps_v3 import box_corners  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
DETS = p("04_experiments/detections/KITTI")
CKPT = p("04_experiments/weights/depth_anything_v2_metric_vkitti_vitl.pth")
OUT = p("04_experiments/kitti_warps_depth")
DS = 8            # depth-map downsampling factor


def build_model(device):
    from depth_anything_v2.dpt import DepthAnythingV2
    cfg = dict(encoder="vitl", features=256, out_channels=[256, 512, 1024, 1024])
    m = DepthAnythingV2(**{**cfg, "max_depth": 80})
    m.load_state_dict(torch.load(CKPT, map_location="cpu"))
    return m.to(device).eval()


def box_depth(depth_map: np.ndarray, tlbr: np.ndarray) -> float | None:
    """Robust depth for a box: median over the central region, which avoids the
    background bleeding in at the box edges."""
    h, w = depth_map.shape
    x1, y1, x2, y2 = tlbr
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    bw, bh = (x2 - x1) * 0.5, (y2 - y1) * 0.5
    a = max(0, int(cx - bw / 2)); b = min(w, int(cx + bw / 2) + 1)
    c = max(0, int(cy - bh / 2)); d = min(h, int(cy + bh / 2) + 1)
    if b <= a or d <= c:
        return None
    patch = depth_map[c:d, a:b]
    patch = patch[np.isfinite(patch) & (patch > 0.5)]
    return float(np.median(patch)) if patch.size else None


@torch.no_grad()
def run_sequence(seq: str, model, device, downscale: int = 2, input_size: int = 518):
    T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
    img_dir = f"{ROOT}/image_02/{seq}"
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".png"))
    det = np.load(os.path.join(DETS, f"{seq}.npz"))["det"]
    by_frame = {int(f): det[det[:, 0] == f] for f in np.unique(det[:, 0])} if len(det) else {}

    h, w = cv2.imread(os.path.join(img_dir, files[0])).shape[:2]
    gx, gy = np.meshgrid(np.linspace(0.05 * w, 0.95 * w, GRID),
                         np.linspace(0.35 * h, 0.95 * h, GRID))
    grid = np.stack([gx.ravel(), gy.ravel()], 1)

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    online = np.zeros((len(files), 6))
    glob = np.zeros((len(files), 6))
    online[0] = glob[0] = np.eye(2, 3).ravel()
    depth_ds = []         # downsampled metric depth per frame
    rel = []              # frame, R(9), t(3): ground-truth relative camera motion
    prev_depth = None

    for i, fn in enumerate(files):
        img = cv2.imread(os.path.join(img_dir, fn))
        H_on, _ = gmc.apply(img, None, frame_id=i)
        online[i] = np.asarray(H_on, float).ravel()
        dm = model.infer_image(img, input_size)          # metres, HxW

        if i > 0 and prev_depth is not None:
            R, t = relative_motion(T_w_cam, i)
            # global warp: static grid at the previous frame's estimated median depth
            gd = prev_depth[np.isfinite(prev_depth) & (prev_depth > 0.5)]
            z_ref = float(np.median(gd)) if gd.size else 20.0
            S = best_similarity(grid, camera_induced(K, R, t, grid, np.full(len(grid), z_ref)))
            glob[i] = np.asarray(S, float).ravel() if S is not None else np.eye(2, 3).ravel()

            rel.append(np.concatenate([[i], R.ravel(), t.ravel()]))
        # store a downsampled depth map so the TRACKER can query depth for its own
        # predicted box at run time -- which is what a deployed system does. Storing
        # per-detection warps would presume an association the tracker has not made yet.
        depth_ds.append(cv2.resize(dm.astype(np.float32), (dm.shape[1] // DS, dm.shape[0] // DS),
                                   interpolation=cv2.INTER_NEAREST).astype(np.float16))
        prev_depth = dm

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f"{seq}.npz"),
                        online=online, global_oracle=glob,
                        depth=np.stack(depth_ds), depth_ds=DS,
                        rel=np.asarray(rel, float), K=K)
    dm_all = np.stack(depth_ds).astype(np.float32)
    print(f"  {seq}  {len(files):5d} frames  depth {dm_all.shape}  "
          f"median {np.median(dm_all[dm_all>0.5]):.1f} m", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seqs", default="")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--input-size", type=int, default=518)
    a = ap.parse_args()
    device = torch.device(a.device)
    model = build_model(device)
    seqs = a.seqs.split(",") if a.seqs else sorted(
        f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    for s in seqs:
        run_sequence(s, model, device, input_size=a.input_size)
    print(f"wrote {len(seqs)} sequences -> {OUT}")


if __name__ == "__main__":
    main()

"""
I1 oracle-warp contrast on real MOT sequences.

For every frame: compute the ONLINE warp (bit-identical to BoT-SORT's GMC) and
the OFFLINE reference warp, then measure how far apart they are in image space.

That disagreement is this project's best available estimate of the actual
compensation error on data where no ground-truth camera motion exists. It is a
LOWER BOUND: the reference is a better estimate, not the truth (DA-CP1 R1).

Outputs one row per frame with:
  * the online reliability primitives (rho, eps, n_inliers, tau, phi, kappa parts)
  * the reference-warp quality diagnostics (used to discard frames where the
    reference itself cannot be trusted -- otherwise the contrast is noise)
  * corner_disagreement_px: mean corner displacement between the two warps
  * box_shift_px: the same disagreement evaluated at actual object locations,
    which is what the tracker's IoU actually experiences
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys
import time

import cv2
cv2.setNumThreads(2)   # avoid oversubscription when sequences run in parallel
import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402
from rac.reference_warp import ReferenceWarpEstimator, corner_disagreement  # noqa: E402
from rac.scan_mot import camera_label, load_dets  # noqa: E402


def load_gt(seq_dir: str) -> dict[int, np.ndarray]:
    """GT boxes per frame (tlbr). Used ONLY to mask foreground for the reference
    estimator and to evaluate box-level shift -- an analysis instrument."""
    path = os.path.join(seq_dir, "gt", "gt.txt")
    if not os.path.exists(path):
        return {}
    a = np.loadtxt(path, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    # MOT17 gt: frame,id,x,y,w,h,conf,class,visibility  -- keep pedestrians only
    if a.shape[1] >= 8:
        a = a[(a[:, 7] == 1) & (a[:, 6] > 0)]
    out = {}
    for f in np.unique(a[:, 0]).astype(int):
        r = a[a[:, 0] == f]
        out[f] = np.stack([r[:, 2], r[:, 3], r[:, 2] + r[:, 4], r[:, 3] + r[:, 5]], 1)
    return out


def box_shift(H_a, H_b, boxes) -> float:
    """Mean displacement (px) between the two warps evaluated at box centres.
    This is the quantity the tracker's IoU gate actually feels."""
    if boxes is None or len(boxes) == 0:
        return float("nan")
    c = np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2], 1)
    a = (np.asarray(H_a)[:, :2] @ c.T).T + np.asarray(H_a)[:, 2]
    b = (np.asarray(H_b)[:, :2] @ c.T).T + np.asarray(H_b)[:, 2]
    return float(np.linalg.norm(a - b, axis=1).mean())


def run_sequence(seq_dir: str, downscale: int = 2, n_features: int = 4000,
                 limit: int | None = None, warp_out: str | None = None) -> pd.DataFrame:
    seq = os.path.basename(seq_dir.rstrip("/"))
    img_dir = os.path.join(seq_dir, "img1")
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png")))
    if limit:
        files = files[:limit]
    dets = load_dets(seq_dir)
    gt = load_gt(seq_dir)

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    ref = ReferenceWarpEstimator(n_features=n_features)

    rows = []
    warps = []          # full 2x3 reference warps, needed to substitute into the tracker
    prev_img = None
    t0 = time.time()
    for i, fn in enumerate(files, start=1):
        img = cv2.imread(os.path.join(img_dir, fn))
        if img is None:
            continue
        H_on, st = gmc.apply(img, dets.get(i), frame_id=i)
        if prev_img is not None:
            r = ref.estimate(prev_img, img, gt.get(i - 1), gt.get(i))
            h, w = img.shape[:2]
            row = st.to_row()
            row.update(dict(
                sequence=seq, camera=camera_label(seq),
                ref_ok=r["ok"], ref_inliers=r["n_inliers"],
                ref_matches=r["n_matches"], ref_inlier_ratio=r["inlier_ratio"],
                ref_resid=r["resid_median"], ref_fb_error=r["fb_error"],
                ref_tx=float(r["H"][0, 2]), ref_ty=float(r["H"][1, 2]),
                corner_disagreement_px=corner_disagreement(H_on, r["H"], w, h),
                box_shift_px=box_shift(H_on, r["H"], gt.get(i)),
                n_gt=len(gt.get(i, [])),
            ))
            rows.append(row)
            warps.append(np.concatenate([[i], np.asarray(r["H"], float).ravel(),
                                         [1.0 if r["ok"] else 0.0]]))
        prev_img = img
    df = pd.DataFrame(rows)
    if warp_out:
        np.savez_compressed(os.path.join(warp_out, f"{seq}.npz"),
                            warp=np.asarray(warps, float))
    print(f"  {seq:22s} {len(df):5d} frames  {time.time()-t0:7.1f}s  "
          f"ref_ok={df.ref_ok.mean():.3f}  "
          f"disagree_med={df.corner_disagreement_px.median():.3f}px", flush=True)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--filter", default="FRCNN")
    ap.add_argument("--seq", default="", help="single sequence name")
    ap.add_argument("--downscale", type=int, default=2)
    ap.add_argument("--n-features", type=int, default=4000)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--warp-out", default=p("04_experiments/ref_warps"))
    a = ap.parse_args()
    if a.warp_out:
        os.makedirs(a.warp_out, exist_ok=True)

    if a.seq:
        seqs = [a.seq]
    else:
        seqs = sorted(d for d in os.listdir(a.root)
                      if os.path.isdir(os.path.join(a.root, d, "img1")) and a.filter in d)
    print(f"oracle contrast over {len(seqs)} sequences", flush=True)
    dfs = [run_sequence(os.path.join(a.root, s), a.downscale, a.n_features, a.limit,
                        a.warp_out) for s in seqs]
    df = pd.concat(dfs, ignore_index=True)
    df.to_csv(a.out, index=False)
    print(f"wrote {len(df)} rows -> {a.out}")


if __name__ == "__main__":
    main()

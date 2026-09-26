"""
DA-CP2 M1 — is it "no 2D warp can be correct", or just "the 4-DOF similarity is too weak"?

The claim that the compensation *model* is inadequate was tested only against a
rotation-only homography and the 4-DOF similarity BoT-SORT happens to use. A full
8-DOF homography exactly represents the motion of a **plane** under arbitrary
camera motion including translation, and KITTI scenes are plane-dominated (road,
facades). If a homography absorbs what the similarity cannot, the correct claim
is much narrower.

Each model class is fitted to the objects' OWN true camera-induced displacements
— the best that model could possibly do for that frame, an oracle for its class:

  similarity  4 DOF   rotation + uniform scale + translation   (BoT-SORT's model)
  affine      6 DOF   + shear and anisotropic scale
  homography  8 DOF   + perspective; exact for any single plane

Residual after each is the part that model cannot express. If the homography
residual collapses to ~0, the limitation is BoT-SORT's model choice. If it stays
large, the limitation is that the scene is not a plane — objects sit at genuinely
different depths and no 2D warp can serve them all.
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
from rac.kitti_egomotion import (
    best_similarity,  # noqa: E402
    camera_poses, relative_motion, load_labels, project, exact_displacement,
)

ROOT = p("04_experiments/data/KITTI/training")
EVAL = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")


def fit_apply(src, dst, model):
    """Fit one warp family to exact correspondences and return the predictions.

    The correspondences here are the objects' own true displacements, computed
    from annotated 3D positions and true camera motion, so they contain no
    outliers and the fit must be least squares. An earlier version used LMEDS
    for the similarity and affine rows, which on a frame with three or four
    objects interpolates a minimal sample and discards the rest -- the same
    defect corrected in `best_similarity`.
    """
    if model == "similarity":
        M = best_similarity(src, dst)
        if M is None:
            return None
        return (M[:, :2] @ src.T).T + M[:, 2]
    if model == "affine":
        n = len(src)
        A = np.zeros((2 * n, 6)); y = np.empty(2 * n)
        A[0::2, 0], A[0::2, 1], A[0::2, 2] = src[:, 0], src[:, 1], 1.0
        A[1::2, 3], A[1::2, 4], A[1::2, 5] = src[:, 0], src[:, 1], 1.0
        y[0::2], y[1::2] = dst[:, 0], dst[:, 1]
        try:
            c = np.linalg.lstsq(A, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return None
        M = c.reshape(2, 3)
        return (M[:, :2] @ src.T).T + M[:, 2]
    if model == "homography":
        if len(src) < 4:
            return None
        H, _ = cv2.findHomography(src.astype(np.float32).reshape(-1, 1, 2),
                                  dst.astype(np.float32).reshape(-1, 1, 2),
                                  method=cv2.LMEDS)
        if H is None:
            return None
        p = np.concatenate([src, np.ones((len(src), 1))], 1)
        q = (H @ p.T).T
        w = q[:, 2:3]
        w = np.where(np.abs(w) < 1e-9, 1e-9, w)
        return q[:, :2] / w
    raise ValueError(model)


def main():
    seqs = sorted(f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    rows = []
    for seq in seqs:
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
        for k in range(1, len(T_w_cam)):
            prev = [o for o in lab.get(k - 1, [])
                    if o["cls"] in EVAL and o["xyz"][2] > 1.0
                    and o["occluded"] <= 1 and o["truncated"] < 0.5]
            if len(prev) < 5:                 # a homography needs 4; ask for headroom
                continue
            X = np.stack([o["xyz"] for o in prev])
            R, t = relative_motion(T_w_cam, k)
            src = project(K, X)
            dst = exact_displacement(K, R, t, X)
            rec = dict(sequence=seq, frame=k, n_obj=len(prev),
                       trans_m=float(np.linalg.norm(t)),
                       depth_ratio=float(X[:, 2].max() / max(X[:, 2].min(), 1e-6)))
            ok = True
            for m in ("similarity", "affine", "homography"):
                pred = fit_apply(src, dst, m)
                if pred is None:
                    ok = False
                    break
                e = np.linalg.norm(dst - pred, axis=1)
                rec[f"{m}_med"] = float(np.median(e))
                rec[f"{m}_max"] = float(e.max())
                rec[f"{m}_spread"] = float(e.max() - e.min())
            if ok:
                rows.append(rec)
    d = pd.DataFrame(rows)
    out = p("04_experiments/kitti_model_class.csv")
    d.to_csv(out, index=False)

    mv = d[d.trans_m > 0.05]
    print(f"=== DA-CP2 M1: how much does a richer warp model absorb? ===")
    print(f"{len(d)} frames with >=5 clean objects, {len(mv)} with the vehicle moving\n")
    print("residual after fitting each model to the objects' OWN true displacements (px):")
    hdr = f"{'model':>12} {'DOF':>4} {'median':>9} {'p90':>9} {'max':>10} {'within-frame spread med':>24}"
    print(hdr)
    for m, dof in [("similarity", 4), ("affine", 6), ("homography", 8)]:
        print(f"{m:>12} {dof:>4} {mv[f'{m}_med'].median():>9.4f} "
              f"{np.percentile(mv[f'{m}_med'], 90):>9.4f} {mv[f'{m}_max'].max():>10.2f} "
              f"{mv[f'{m}_spread'].median():>24.4f}")

    print("\nfraction of moving frames whose within-frame spread exceeds a threshold:")
    print(f"{'threshold':>10} " + " ".join(f"{m:>12}" for m, _ in
                                           [("similarity", 4), ("affine", 6), ("homography", 8)]))
    for T in [1, 2, 5, 10]:
        vals = " ".join(f"{100*(mv[f'{m}_spread'] > T).mean():11.2f}%"
                        for m in ("similarity", "affine", "homography"))
        print(f"{T:>10} {vals}")

    print("\nreduction from the similarity model:")
    for m in ("affine", "homography"):
        r = 1 - mv[f"{m}_spread"].median() / mv["similarity_spread"].median()
        print(f"  {m:>11}: within-frame spread median falls by {100*r:5.1f}%"
              f"   ({mv['similarity_spread'].median():.3f} -> {mv[f'{m}_spread'].median():.3f} px)")

    print("\nstratified by within-frame depth ratio (max depth / min depth):")
    q = pd.qcut(mv.depth_ratio, 4, duplicates="drop")
    print(mv.groupby(q, observed=True).agg(
        n=("frame", "size"), ratio_med=("depth_ratio", "median"),
        sim=("similarity_spread", "median"), aff=("affine_spread", "median"),
        hom=("homography_spread", "median")).round(3).to_string())
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()

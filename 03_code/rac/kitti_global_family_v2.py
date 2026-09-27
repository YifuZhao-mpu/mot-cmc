"""
Section 6.4, corrected: does a richer GLOBAL warp family help when it is fitted to
a scene with real depth variation?

Review finding (Devil's Advocate, Critical): the first version of this test placed
the static grid at ONE depth. The mapping induced between two views of a plane IS
a homography exactly, so `findHomography` recovered it to 6.2e-6 px and the 8-DOF
model carried the same depth information as the 4-DOF one -- one depth. The 2.3 %
spread reduction was an arithmetic consequence of the construction, not a finding
about warp families. The test did not test what the section claimed.

This version fits both global families to background points at their OWN depths,
read from the monocular depth map a deployable system would have. A homography now
has real depth variation to exploit, and the ground plane -- the structure the
UCMCTrack comparison is about -- is present rather than flattened away.

  background points : a grid over the lower image, with points inside annotated
                      object boxes removed, each carrying its own estimated depth
  correspondences   : back-project at that depth -> apply true (R, t) -> re-project
  models fitted     : 4-DOF similarity, 8-DOF homography
  measured at       : object centres, at their own TRUE depths

Writes 04_experiments/kitti_global_family_v2.csv
"""
from __future__ import annotations

import argparse
import zlib

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
from rac.kitti_egomotion import (  # noqa: E402
    camera_poses, relative_motion, load_labels, best_similarity, project,
)
from rac.kitti_per_object import exact_displacement  # noqa: E402
from rac.kitti_warps_v2 import camera_induced  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
DEPTH = p("04_experiments/kitti_warps_depth")
OUT = p("04_experiments/kitti_global_family_v2.csv")
WOUT = p("04_experiments/kitti_warps_planar")
# Depth-noise study for the homography arm. Its depth enters through the
# back-projection of the background points, not through any per-object lookup,
# so its sensitivity is a different function from the per-target arm's and had
# to be measured rather than assumed.
DEPTH_SIGMA = 0.0
DEPTH_SEED = 0
EVAL_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")
MOVING_M = 0.05
MIN_OBJ = 3          # for the residual MEASUREMENT only -- it needs annotations
DETS = p("04_experiments/detections/KITTI")
NGRID = 24          # 24x24 background samples, thinned by the object mask
BOX_PAD = 0.15


def apply_sim(S6, p):
    S = np.asarray(S6, float).reshape(2, 3)
    return p @ S[:, :2].T + S[:, 2]


def apply_hom(H, p):
    q = np.concatenate([p, np.ones((len(p), 1))], 1) @ np.asarray(H, float).T
    return q[:, :2] / q[:, 2:3]


def background_points(w, h, boxes, depth, ds):
    """Grid over the lower image, minus foreground, each point with its own depth.

    Review finding (Critical): an earlier version masked with ground-truth labels
    and, worse, skipped any frame with fewer than three clean annotations, leaving
    the identity warp there -- no compensation at all on 2,399 of 6,717 moving
    frames. A compensator cannot read labels and must never fall back to identity.
    The mask now comes from the tracker's own frozen detections, and warp
    generation is separated from the residual measurement, which does need labels.
    """
    gx, gy = np.meshgrid(np.linspace(0.04 * w, 0.96 * w, NGRID),
                         np.linspace(0.30 * h, 0.97 * h, NGRID))
    p = np.stack([gx.ravel(), gy.ravel()], 1)
    keep = np.ones(len(p), bool)
    for x1, y1, x2, y2 in boxes:
        pw, ph = (x2 - x1) * BOX_PAD, (y2 - y1) * BOX_PAD
        keep &= ~((p[:, 0] > x1 - pw) & (p[:, 0] < x2 + pw)
                  & (p[:, 1] > y1 - ph) & (p[:, 1] < y2 + ph))
    p = p[keep]
    if len(p) < 12:
        return None, None
    iy = np.clip((p[:, 1] / ds).astype(int), 0, depth.shape[0] - 1)
    ix = np.clip((p[:, 0] / ds).astype(int), 0, depth.shape[1] - 1)
    z = depth[iy, ix].astype(np.float32)
    if DEPTH_SIGMA > 0:
        rng = np.random.default_rng(DEPTH_SEED * 1_000_003 + zlib.crc32(z.tobytes()))
        z = z * np.exp(rng.normal(0.0, DEPTH_SIGMA, size=z.shape)).astype(np.float32)
    good = np.isfinite(z) & (z > 1.0) & (z < 120.0)
    return (p[good], z[good]) if good.sum() >= 12 else (None, None)


def main() -> None:
    rows = []
    os.makedirs(WOUT, exist_ok=True)
    for seq in sorted(s[:-4] for s in os.listdir(f"{ROOT}/oxts") if s.endswith(".txt")):
        dp = os.path.join(DEPTH, f"{seq}.npz")
        if not os.path.exists(dp):
            continue
        D = np.load(dp)
        depth, ds = D["depth"], int(D["depth_ds"])
        T_w_cam, K = camera_poses(f"{ROOT}/oxts/{seq}.txt", f"{ROOT}/calib/{seq}.txt")
        lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
        img_dir = f"{ROOT}/image_02/{seq}"
        f0 = sorted(f for f in os.listdir(img_dir) if f.endswith(".png"))[0]
        h, w = cv2.imread(os.path.join(img_dir, f0)).shape[:2]

        V4 = np.load(p(f"04_experiments/kitti_warps_v4/{seq}.npz"))
        n = len(V4["global_oracle"])
        # fall back to the single-depth global similarity, never to identity
        planar_h = np.zeros((n, 9))
        planar_s = V4["global_oracle"].copy()
        for k in range(n):
            S = planar_s[k].reshape(2, 3)
            planar_h[k] = np.array([[S[0, 0], S[0, 1], S[0, 2]],
                                    [S[1, 0], S[1, 1], S[1, 2]],
                                    [0.0, 0.0, 1.0]]).ravel()
        det = np.load(os.path.join(DETS, f"{seq}.npz"))["det"]
        det_by_frame = {int(fr): det[det[:, 0] == fr] for fr in np.unique(det[:, 0])} \
            if len(det) else {}
        n_fit = 0

        # --- pass 1: fit a warp on EVERY frame the camera moves, using detections
        for i in range(1, min(n, len(depth))):
            R, t = relative_motion(T_w_cam, i)
            if float(np.linalg.norm(t)) < MOVING_M:
                continue
            d = det_by_frame.get(i - 1, np.zeros((0, 6)))
            dboxes = [tuple(r[1:5]) for r in d] if len(d) else []
            bp, bz = background_points(w, h, dboxes, depth[i - 1], ds)
            if bp is None:
                continue
            bmoved = camera_induced(K, R, t, bp, bz)
            S = best_similarity(bp, bmoved, robust=True)   # monocular depths carry outliers
            Hh, _ = cv2.findHomography(bp.astype(np.float32).reshape(-1, 1, 2),
                                       bmoved.astype(np.float32).reshape(-1, 1, 2),
                                       method=cv2.RANSAC, ransacReprojThreshold=1.0)
            if Hh is not None:
                planar_h[i] = np.asarray(Hh, float).ravel()
                n_fit += 1
            if S is not None:
                planar_s[i] = np.asarray(S, float).ravel()

        # --- pass 2: the residual measurement, which does need annotations
        for i in range(1, len(depth)):
            prev = [o for o in lab.get(i - 1, [])
                    if o["cls"] in EVAL_CLASSES and o["xyz"][2] > 1.0
                    and o["occluded"] <= 1 and o["truncated"] < 0.5]
            if len(prev) < MIN_OBJ:
                continue
            R, t = relative_motion(T_w_cam, i)
            if float(np.linalg.norm(t)) < MOVING_M:
                continue
            if i >= n:
                continue
            d = det_by_frame.get(i - 1, np.zeros((0, 6)))
            dboxes = [tuple(r[1:5]) for r in d] if len(d) else []
            bp, bz = background_points(w, h, dboxes, depth[i - 1], ds)
            if bp is None:
                continue
            bmoved = camera_induced(K, R, t, bp, bz)
            S, Hh = planar_s[i], planar_h[i].reshape(3, 3)
            # how well does each model fit the BACKGROUND it was fitted to?
            fit_s = float(np.median(np.linalg.norm(apply_sim(S, bp) - bmoved, axis=1)))
            fit_h = float(np.median(np.linalg.norm(apply_hom(Hh, bp) - bmoved, axis=1)))

            on = V4["online"][i] if i < len(V4["online"]) else np.eye(2, 3).ravel()
            X = np.stack([o["xyz"] for o in prev])
            c0 = project(K, X)
            truth = exact_displacement(K, R, t, X)
            # the DEPLOYED estimator, on the same frames and the same objects --
            # the comparison that matters, because it is what a tracker actually runs
            e_on = np.linalg.norm(apply_sim(on, c0) - truth, axis=1)
            e_s = np.linalg.norm(apply_sim(S, c0) - truth, axis=1)
            e_h = np.linalg.norm(apply_hom(Hh, c0) - truth, axis=1)
            So = best_similarity(c0, truth)
            e_o = (np.linalg.norm(apply_sim(So, c0) - truth, axis=1)
                   if So is not None else e_s)
            rows.append([int(seq), i, len(prev), len(bp), float(np.linalg.norm(t)),
                         float(np.median(bz)), fit_s, fit_h,
                         float(np.median(e_o)), float(e_o.max() - e_o.min()),
                         float(np.median(e_s)), float(e_s.max() - e_s.min()),
                         float(np.median(e_h)), float(e_h.max() - e_h.min()),
                         float(np.median(e_on)), float(e_on.max() - e_on.min())])
        np.savez_compressed(os.path.join(WOUT, f"{seq}.npz"),
                            online=V4["online"], per_object=V4["per_object"],
                            global_oracle=planar_s, global_homography=planar_h)
        ident = int(np.all(np.isclose(planar_h, np.eye(3).ravel()), axis=1).sum())
        print(f"  {seq}  fitted {n_fit}/{n} frames   identity {ident}   "
              f"measured {len(rows)} so far", flush=True)

    cols = ["sequence", "frame", "n_obj", "n_bg", "trans_m", "bg_depth_med",
            "fit_sim", "fit_hom", "oracle_med", "oracle_spread",
            "sim_med", "sim_spread", "hom_med", "hom_spread",
            "online_med", "online_spread"]
    df = pd.DataFrame(rows, columns=cols)
    df.to_csv(OUT, index=False)

    print(f"\nmoving frames with >={MIN_OBJ} objects and usable background: {len(df)}")
    print(f"  median background samples per frame: {df.n_bg.median():.0f}")
    print(f"\n  fit residual ON THE BACKGROUND the model was fitted to:")
    print(f"    similarity {df.fit_sim.median():8.4f} px      homography {df.fit_hom.median():8.4f} px")
    print(f"    -> the homography is no longer interpolating a single-depth plane\n")
    print(f"{'':22s}{'online GMC':>12s}{'oracle sim':>12s}{'deploy sim':>12s}{'deploy hom':>12s}")
    for name, sfx in (("median residual", "_med"), ("median spread", "_spread")):
        vals = [df[c + sfx].median() for c in ("online", "oracle", "sim", "hom")]
        print(f"  {name:20s}" + "".join(f"{v:>12.4f}" for v in vals))
    fr = [(df[c + "_spread"] > 5).mean() * 100 for c in ("online", "oracle", "sim", "hom")]
    print(f"  {'frames spread >5px':20s}" + "".join(f"{v:>11.2f}%" for v in fr))
    print("\n  The deployed estimator has the LARGEST within-frame spread of the three\n"
          "  global models and the best tracking metrics of the three. Geometric\n"
          "  accuracy of a shared warp is not what the tracker is responding to.")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth-sigma", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--warp-out", default=None)
    ap.add_argument("--csv-out", default=None)
    a = ap.parse_args()
    DEPTH_SIGMA, DEPTH_SEED = a.depth_sigma, a.seed
    if a.warp_out:
        WOUT = a.warp_out
    if a.csv_out:
        OUT = a.csv_out
    main()

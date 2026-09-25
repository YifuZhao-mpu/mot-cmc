"""
KITTI tracking with pluggable camera-motion compensation.

A BoT-SORT-shaped tracker (Kalman + two-stage ByteTrack association + IoU gate),
motion-only. ReID is deliberately absent: a car re-identification model would be
another uncontrolled variable, and the question here is entirely about how
compensation enters the motion channel.

Four compensation sources, all frozen to disk beforehand so every configuration
is fed byte-identical inputs:

  none          identity
  online        BoT-SORT's own sparseOptFlow GMC
  global_oracle best 4-DOF similarity fitted to the objects' TRUE displacements
  per_target    each track compensated by ITS OWN true displacement (oracle depth)

`per_target` is the configuration that MOT17 could not express, because there the
within-frame spread of required corrections is negligible. On KITTI it is
54.3 % of moving frames above 5 px.

Both oracle modes use ground truth and are upper bounds, not methods.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import numpy as np
import zlib
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "BoT-SORT"))

from tracker import matching  # noqa: E402
from tracker.kalman_filter import KalmanFilter  # noqa: E402
from rac.kitti_egomotion import load_labels  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
DETS = p("04_experiments/detections/KITTI")
WARPS = os.environ.get("RAC_KITTI_WARPS", p("04_experiments/kitti_warps"))
OUT = p("04_experiments/trackers/KITTI")

KITTI_NAME = {1: "Car", 4: "Pedestrian"}

# Plausibility guard, applied IDENTICALLY to every configuration so the
# comparison stays fair. It exists because even the ORACLE global similarity
# occasionally produces a degenerate fit (sequence 0010 contains one frame with
# a fitted scale of 3.20, against a 1st-99th percentile range of 0.98-1.19).
# BoT-SORT's own multi_gmc has no such guard and would apply it unchanged.
SCALE_MIN, SCALE_MAX = 0.5, 2.0
SHUFFLE_SEED = 20260925
WARP_REJECTS = {"n": 0}


def sanitize_warp(H) -> np.ndarray:
    H = np.asarray(H, float)
    if H.shape != (2, 3) or not np.all(np.isfinite(H)):
        WARP_REJECTS["n"] += 1
        return np.eye(2, 3)
    s = float(np.sqrt(abs(np.linalg.det(H[:2, :2]))))
    if not np.isfinite(s) or s < SCALE_MIN or s > SCALE_MAX:
        WARP_REJECTS["n"] += 1
        return np.eye(2, 3)
    return H


class Track:
    _next = 1

    def __init__(self, tlbr, score, cls, frame, kf):
        self.kf = kf
        self.mean, self.cov = kf.initiate(self._to_xywh(tlbr))
        self.track_id = Track._next; Track._next += 1
        self.score, self.cls = score, cls
        self.state = "tracked"
        self.start_frame = frame
        self.end_frame = frame
        self.time_since_update = 0

    @staticmethod
    def _to_xywh(tlbr):
        return np.array([(tlbr[0] + tlbr[2]) / 2, (tlbr[1] + tlbr[3]) / 2,
                         tlbr[2] - tlbr[0], tlbr[3] - tlbr[1]], float)

    @property
    def tlbr(self):
        cx, cy, w, h = self.mean[:4]
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])

    def predict(self):
        m = self.mean.copy()
        if self.state != "tracked":
            m[6] = m[7] = 0
        self.mean, self.cov = self.kf.predict(m, self.cov)

    def update(self, tlbr, score, frame):
        self.mean, self.cov = self.kf.update(self.mean, self.cov, self._to_xywh(tlbr))
        self.score = score
        self.state = "tracked"
        self.end_frame = frame
        self.time_since_update = 0

    def apply_shift(self, dx, dy):
        self.mean[0] += dx
        self.mean[1] += dy

    def apply_homography(self, Hh, fallback):
        """Warp the box by a homography, then re-express the effect as the local
        similarity the Kalman state can absorb (the KF state is not projective)."""
        b = self.tlbr
        c0 = np.array([[b[0], b[1]], [b[2], b[1]], [b[0], b[3]], [b[2], b[3]]], float)
        p = np.concatenate([c0, np.ones((4, 1))], 1)
        q = (np.asarray(Hh, float) @ p.T).T
        w = q[:, 2:3]
        if not np.all(np.isfinite(w)) or np.any(np.abs(w) < 1e-9):
            self.apply_warp(fallback); return
        c1 = q[:, :2] / w
        import cv2 as _cv
        M, _ = _cv.estimateAffinePartial2D(c0.astype(np.float32).reshape(-1, 1, 2),
                                           c1.astype(np.float32).reshape(-1, 1, 2),
                                           method=_cv.LMEDS)
        self.apply_warp(M if M is not None else fallback)

    def apply_homography_foot(self, Hh, fallback):
        """Ground-plane application: displace the whole box by the homography's
        motion of its CONTACT POINT, taking the size change from the global
        similarity. This is UCMCTrack's mechanism -- a foot point on a ground
        plane is a per-target range measurement -- expressed as a 2D correction.

        It exists because applying a ground-plane homography to all four corners
        is wrong above the plane: an object's top edge is metres above the ground
        and the homography moves it as if it lay on it.
        """
        b = self.tlbr
        foot = np.array([[(b[0] + b[2]) / 2.0, b[3]]], float)
        p = np.concatenate([foot, np.ones((1, 1))], 1)
        q = (np.asarray(Hh, float) @ p.T).T
        w = q[:, 2:3]
        if not np.all(np.isfinite(w)) or np.any(np.abs(w) < 1e-9):
            self.apply_warp(fallback); return
        d = (q[:, :2] / w - foot).ravel()
        F = np.asarray(fallback, float).reshape(2, 3)
        s = float(np.sqrt(abs(np.linalg.det(F[:, :2]))))
        if not np.isfinite(s) or s <= 0:
            s = 1.0
        # scale about the foot point, then translate by the contact-point motion
        M = np.array([[s, 0.0, foot[0, 0] * (1 - s) + d[0]],
                      [0.0, s, foot[0, 1] * (1 - s) + d[1]]], float)
        self.apply_warp(M)

    def apply_warp(self, H):
        H = sanitize_warp(H)
        R, t = np.asarray(H)[:2, :2], np.asarray(H)[:2, 2]
        R8 = np.kron(np.eye(4), R)
        self.mean = R8.dot(self.mean)
        self.mean[:2] += t
        cov = R8.dot(self.cov).dot(R8.T)
        self.cov = 0.5 * (cov + cov.T)          # numerical symmetry for the KF Cholesky


def _corners(tlbr):
    x1, y1, x2, y2 = tlbr
    return np.array([[x1, y1], [x2, y1], [x1, y2], [x2, y2]], float)


def _camera_induced(K, R, t, pts, depth):
    Kinv = np.linalg.inv(K)
    rays = (Kinv @ np.concatenate([pts, np.ones((len(pts), 1))], 1).T).T
    X = rays * depth[:, None] / rays[:, 2:3]
    Xp = (R @ X.T).T + t
    x = (K @ Xp.T).T
    return x[:, :2] / x[:, 2:3]


def _fit_sim(src, dst):
    import cv2
    H, _ = cv2.estimateAffinePartial2D(src.astype(np.float32).reshape(-1, 1, 2),
                                       dst.astype(np.float32).reshape(-1, 1, 2),
                                       method=cv2.LMEDS)
    return H


def _box_depth_ds(dmap, tlbr, ds):
    """Median depth in the central half of the box, read from the downsampled map."""
    h, w = dmap.shape
    x1, y1, x2, y2 = np.asarray(tlbr, float) / ds
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    bw, bh = (x2 - x1) * 0.5, (y2 - y1) * 0.5
    a = max(0, int(cx - bw / 2)); b = min(w, int(cx + bw / 2) + 1)
    c = max(0, int(cy - bh / 2)); d = min(h, int(cy + bh / 2) + 1)
    if b <= a or d <= c:
        a, b = max(0, int(cx)), min(w, int(cx) + 1)
        c, d = max(0, int(cy)), min(h, int(cy) + 1)
        if b <= a or d <= c:
            return None
    patch = dmap[c:d, a:b]
    patch = patch[np.isfinite(patch) & (patch > 0.5)]
    return float(np.median(patch)) if patch.size else None


def iou_dist(tracks, dets):
    if not tracks or len(dets) == 0:
        return np.zeros((len(tracks), len(dets)))
    a = np.array([t.tlbr for t in tracks], float)
    return matching.iou_distance(a, np.asarray(dets, float))


def gt_boxes_by_frame(seq: str):
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    return {f: (np.stack([o["tlbr"] for o in v]),
                np.array([o["track_id"] for o in v])) for f, v in lab.items() if v}


def run_sequence(seq: str, mode: str, args) -> list[str]:
    det = np.load(os.path.join(DETS, f"{seq}.npz"))["det"]
    by_frame = {int(f): det[det[:, 0] == f] for f in np.unique(det[:, 0])} if len(det) else {}
    W = np.load(os.path.join(WARPS, f"{seq}.npz"))
    online, glob_or = W["online"], W["global_oracle"]

    if mode == "per_target_depth":
        # DEPLOYABLE per-target: depth from a monocular network, queried at the
        # track's OWN predicted box. Ego-motion is still ground truth -- one
        # variable is relaxed at a time.
        depth = np.asarray(W["depth"], np.float32)
        DSF = int(W["depth_ds"])
        Kmat = np.asarray(W["K"], float)
        rel = np.asarray(W["rel"], float)
        rel_by_frame = {int(r[0]): (r[1:10].reshape(3, 3), r[10:13]) for r in rel}
        per_obj = np.zeros((0, 6))
    else:
        # a warp bundle produced for the depth pipeline carries no per-object table;
        # the non-per-target modes do not need one.
        per_obj = W["per_object"] if "per_object" in W.files else np.zeros((0, 6))
    glob_hom = W["global_homography"] if "global_homography" in W.files else None
    # class-depth-anchored global similarity: the same shared 4-DOF warp, but with
    # the static grid placed at the median depth of ONE class rather than of all
    # annotated objects. Tests whether the cheap fix is "anchor at your targets'
    # depth" rather than "go per-target".
    glob_anchor = (W["global_ped"] if mode == "global_anchored_ped" and "global_ped" in W.files
                   else W["global_car"] if mode == "global_anchored_car" and "global_car" in W.files
                   else None)
    # v2 stores (dx, dy); v3 stores a full local similarity (a, b, tx, ty)
    per_full = per_obj.shape[1] >= 6
    per_by_frame: dict[int, dict[int, tuple]] = {}
    for r in per_obj:
        per_by_frame.setdefault(int(r[0]), {})[int(r[1])] = tuple(r[2:])
    gtb = (gt_boxes_by_frame(seq)
           if mode in ("per_target", "per_target_shuffled") else {})

    n_frames = len(online)
    kf = KalmanFilter()
    Track._next = 1
    tracks: list[Track] = []
    lost: list[Track] = []
    lines: list[str] = []

    for f in range(n_frames):
        for t in tracks + lost:
            t.predict()

        # ---- compensation ------------------------------------------------
        if mode == "none":
            pass
        elif mode == "online":
            H = online[f].reshape(2, 3)
            for t in tracks + lost:
                t.apply_warp(H)
        elif mode == "global_oracle":
            H = glob_or[f].reshape(2, 3)
            for t in tracks + lost:
                t.apply_warp(H)
        elif mode in ("global_anchored_ped", "global_anchored_car"):
            H = glob_anchor[f].reshape(2, 3)
            for t in tracks + lost:
                t.apply_warp(H)
        elif mode == "global_homography":
            Hh = glob_hom[f].reshape(3, 3)
            for t in tracks + lost:
                t.apply_homography(Hh, glob_or[f].reshape(2, 3))
        elif mode == "global_homography_foot":
            Hh = glob_hom[f].reshape(3, 3)
            for t in tracks + lost:
                t.apply_homography_foot(Hh, glob_or[f].reshape(2, 3))
        elif mode == "per_target_depth":
            gp = glob_or[f].reshape(2, 3)
            rt = rel_by_frame.get(f)
            dmap = depth[f - 1] if 0 < f < len(depth) + 1 and f - 1 < len(depth) else None
            for t in tracks + lost:
                Sl = None
                if rt is not None and dmap is not None:
                    R_, t_ = rt
                    z = _box_depth_ds(dmap, t.tlbr, DSF)
                    if z is not None:
                        c0 = _corners(t.tlbr)
                        c1 = _camera_induced(Kmat, R_, t_, c0, np.full(4, z))
                        Sl = _fit_sim(c0, c1)
                if Sl is not None:
                    t.apply_warp(np.asarray(Sl, float))
                else:
                    t.apply_warp(gp)
        elif mode in ("per_target", "per_target_shuffled"):
            shifts = per_by_frame.get(f, {})
            if mode == "per_target_shuffled" and len(shifts) > 1:
                # PLACEBO: the same set of per-object corrections, applied to the
                # wrong objects. Magnitude and direction distributions are exactly
                # preserved within the frame; only the object-to-correction pairing
                # -- the depth information -- is destroyed. If the gain survives
                # this, it is perturbation magnitude and not depth.
                ks = sorted(shifts)
                rng = np.random.default_rng(SHUFFLE_SEED * 1_000_003
                                            + zlib.crc32(f"{seq}:{f}".encode()))
                perm = rng.permutation(len(ks))
                while len(ks) > 1 and np.any(perm == np.arange(len(ks))):
                    perm = rng.permutation(len(ks))      # derangement
                shifts = {ks[i]: shifts[ks[perm[i]]] for i in range(len(ks))}
            gb = gtb.get(f - 1)
            H = glob_or[f].reshape(2, 3)
            for t in tracks + lost:
                dxy = None
                if gb is not None and len(shifts):
                    d = matching.iou_distance(np.array([t.tlbr], float), gb[0])
                    j = int(np.argmin(d[0]))
                    if d[0, j] < 0.7 and int(gb[1][j]) in shifts:
                        dxy = shifts[int(gb[1][j])]
                if dxy is not None:
                    if per_full:
                        a_, b_, tx_, ty_ = dxy
                        t.apply_warp(np.array([[a_, b_, tx_], [-b_, a_, ty_]]))
                    else:
                        t.apply_shift(dxy[0], dxy[1])
                else:
                    t.apply_warp(H)                         # fall back to the global oracle
        else:
            raise ValueError(mode)

        d = by_frame.get(f, np.zeros((0, 7)))
        hi = d[d[:, 5] >= args.track_high] if len(d) else d
        lo = d[(d[:, 5] >= args.track_low) & (d[:, 5] < args.track_high)] if len(d) else d

        # ---- association 1: high-score -----------------------------------
        pool = tracks + lost
        dist = iou_dist(pool, hi[:, 1:5] if len(hi) else [])
        m, u_t, u_d = matching.linear_assignment(dist, thresh=args.match_thresh)
        for it, idet in m:
            pool[it].update(hi[idet, 1:5], hi[idet, 5], f)
        matched = {id(pool[it]) for it, _ in m}
        rem = [pool[i] for i in u_t if pool[i].state == "tracked"]

        # ---- association 2: low-score ------------------------------------
        dist2 = iou_dist(rem, lo[:, 1:5] if len(lo) else [])
        m2, u_t2, _ = matching.linear_assignment(dist2, thresh=0.5)
        for it, idet in m2:
            rem[it].update(lo[idet, 1:5], lo[idet, 5], f)
            matched.add(id(rem[it]))

        # ---- bookkeeping --------------------------------------------------
        new_tracks, new_lost = [], []
        for t in pool:
            if id(t) in matched:
                new_tracks.append(t)
            else:
                t.time_since_update += 1
                t.state = "lost"
                if t.time_since_update <= args.track_buffer:
                    new_lost.append(t)
        for idet in u_d:
            if hi[idet, 5] >= args.new_track:
                new_tracks.append(Track(hi[idet, 1:5], hi[idet, 5], int(hi[idet, 6]), f, kf))
        tracks, lost = new_tracks, new_lost

        for t in tracks:
            b = t.tlbr
            if (b[2] - b[0]) * (b[3] - b[1]) < args.min_area:
                continue
            lines.append(f"{f} {t.track_id} {KITTI_NAME.get(t.cls,'Car')} -1 -1 -10 "
                         f"{b[0]:.2f} {b[1]:.2f} {b[2]:.2f} {b[3]:.2f} "
                         f"-1 -1 -1 -1000 -1000 -1000 -10 {t.score:.3f}\n")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["none", "online", "global_oracle", "global_homography",
                             "global_anchored_ped", "global_anchored_car",
                             "global_homography_foot", "per_target_shuffled",
                             "per_target", "per_target_depth"])
    ap.add_argument("--name", default=None)
    ap.add_argument("--track-high", type=float, default=0.5)
    ap.add_argument("--track-low", type=float, default=0.1)
    ap.add_argument("--new-track", type=float, default=0.6)
    ap.add_argument("--match-thresh", type=float, default=0.8)
    ap.add_argument("--track-buffer", type=int, default=10)   # KITTI is 10 fps
    ap.add_argument("--min-area", type=float, default=40)
    a = ap.parse_args()

    name = a.name or f"cmc_{a.mode}"
    out = os.path.join(OUT, name, "data")
    os.makedirs(out, exist_ok=True)
    seqs = sorted(f[:-4] for f in os.listdir(DETS) if f.endswith(".npz"))
    for s in seqs:
        lines = run_sequence(s, a.mode, a)
        with open(os.path.join(out, f"{s}.txt"), "w") as f:
            f.writelines(lines)
        print(f"  {s}  {len(lines):7d} rows", flush=True)
    print(f"[{name}] warps rejected by the plausibility guard: {WARP_REJECTS['n']}")
    print(f"[{name}] -> {out}")


if __name__ == "__main__":
    main()

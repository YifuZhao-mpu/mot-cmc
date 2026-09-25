"""
DA-CP2 M3 — measure the DOWNSTREAM effect of compensation on UAVDT.

The benchmark audit concluded that MOT17, MOT20 and UAVDT all lack the
compensation-failure regime. For MOT17 that rests on three independent lines
including an actual tracking experiment with an oracle warp. For UAVDT it rested
only on the reliability scan — the estimates are clean, but nobody checked
whether compensation changes tracking outcomes there at all.

This closes that gap with the comparison UAVDT can support. It has no
ground-truth ego-motion, so no oracle warp is possible; what is available is
`none` vs `online`, which answers "does compensation matter here?" even if it
cannot answer "would a perfect one matter more?".

Detections are UAVDT's own published FRCNN detections — fixed across both
configurations, so the only thing that varies is the warp.

Tracker: the same motion-only BoT-SORT shape used on KITTI (Kalman + two-stage
ByteTrack association + IoU gate), so the two domains are compared like for like.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys

import cv2
cv2.setNumThreads(2)
import numpy as np
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code" / "BoT-SORT"))
from tracker import matching  # noqa: E402
from tracker.kalman_filter import KalmanFilter  # noqa: E402
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC  # noqa: E402
from rac.kitti_track import Track, iou_dist, sanitize_warp, WARP_REJECTS  # noqa: E402

ROOT = p("04_experiments/data/UAVDT")
LAYOUT = f"{ROOT}/mot_layout"
DET = f"{ROOT}/UAV-benchmark-MOTD_v1.0/RES_DET/det_FRCNN"
OUT = p("04_experiments/trackers/UAVDT")


def load_dets(seq: str) -> dict[int, np.ndarray]:
    """UAVDT det: frame, -1, x, y, w, h, conf, class, -1  -> frame -> [x1,y1,x2,y2,conf]"""
    p = os.path.join(DET, f"{seq}.txt")
    a = np.loadtxt(p, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    out = {}
    for f in np.unique(a[:, 0]).astype(int):
        r = a[a[:, 0] == f]
        out[f] = np.stack([r[:, 2], r[:, 3], r[:, 2] + r[:, 4], r[:, 3] + r[:, 5], r[:, 6]], 1)
    return out


def run_sequence(seq: str, mode: str, args) -> list[str]:
    img_dir = os.path.join(LAYOUT, seq, "img1")
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".jpg"))
    dets = load_dets(seq)
    gmc = InstrumentedSparseOptFlowGMC(downscale=2, keep_inlier_xy=False)

    kf = KalmanFilter()
    Track._next = 1
    tracks: list[Track] = []
    lost: list[Track] = []
    lines: list[str] = []

    for i, fn in enumerate(files, start=1):
        img = cv2.imread(os.path.join(img_dir, fn))
        H, _ = gmc.apply(img, None, frame_id=i)
        for t in tracks + lost:
            t.predict()
        if mode == "online":
            for t in tracks + lost:
                t.apply_warp(H)

        d = dets.get(i, np.zeros((0, 5)))
        hi = d[d[:, 4] >= args.track_high] if len(d) else d
        lo = d[(d[:, 4] >= args.track_low) & (d[:, 4] < args.track_high)] if len(d) else d

        pool = tracks + lost
        dist = iou_dist(pool, hi[:, :4] if len(hi) else [])
        m, u_t, u_d = matching.linear_assignment(dist, thresh=args.match_thresh)
        for it, idet in m:
            pool[it].update(hi[idet, :4], hi[idet, 4], i)
        matched = {id(pool[it]) for it, _ in m}
        rem = [pool[j] for j in u_t if pool[j].state == "tracked"]

        d2 = iou_dist(rem, lo[:, :4] if len(lo) else [])
        m2, _, _ = matching.linear_assignment(d2, thresh=0.5)
        for it, idet in m2:
            rem[it].update(lo[idet, :4], lo[idet, 4], i)
            matched.add(id(rem[it]))

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
            if hi[idet, 4] >= args.new_track:
                new_tracks.append(Track(hi[idet, :4], hi[idet, 4], 1, i, kf))
        tracks, lost = new_tracks, new_lost

        for t in tracks:
            b = t.tlbr
            w, h = b[2] - b[0], b[3] - b[1]
            if w * h < args.min_area:
                continue
            lines.append(f"{i},{t.track_id},{b[0]:.2f},{b[1]:.2f},{w:.2f},{h:.2f},"
                         f"{t.score:.2f},-1,-1,-1\n")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["none", "online"])
    ap.add_argument("--name", default=None)
    ap.add_argument("--track-high", type=float, default=0.5)
    ap.add_argument("--track-low", type=float, default=0.1)
    ap.add_argument("--new-track", type=float, default=0.6)
    ap.add_argument("--match-thresh", type=float, default=0.8)
    ap.add_argument("--track-buffer", type=int, default=30)
    ap.add_argument("--min-area", type=float, default=40)
    a = ap.parse_args()

    name = a.name or f"uavdt_{a.mode}"
    out = os.path.join(OUT, "UAVDT-test", name, "data")
    os.makedirs(out, exist_ok=True)
    seqs = sorted(f[:-4] for f in os.listdir(DET) if f.endswith(".txt"))
    for s in seqs:
        lines = run_sequence(s, a.mode, a)
        with open(os.path.join(out, f"{s}.txt"), "w") as f:
            f.writelines(lines)
        print(f"  {s}  {len(lines):7d} rows", flush=True)
    print(f"[{name}] warps rejected: {WARP_REJECTS['n']}")
    print(f"[{name}] -> {out}")


if __name__ == "__main__":
    main()

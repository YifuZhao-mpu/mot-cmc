"""
Reliability scan over real MOT sequences.

Runs the instrumented GMC (bit-identical to BoT-SORT's) over every frame of the
given sequences and dumps one row of geometric-verification statistics per frame.

This answers the first half of SQ1: *does CMC failure occur at a non-negligible
rate on real data, and where?*  It does not yet answer attribution (I1) -- that
needs the oracle-warp contrast.

Built-in control: MOT17 contains both static- and moving-camera sequences. A
reliability estimator that flags static sequences as unreliable is producing
false alarms; that is measured here rather than assumed away.
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

# Camera status per MOT17 sequence, from the MOT16/MOT17 benchmark documentation
# (MOT17 inherits MOT16's sequences). Used only as an analysis label.
MOT17_CAMERA = {
    "MOT17-02": "static", "MOT17-04": "static", "MOT17-09": "static",
    "MOT17-05": "moving", "MOT17-10": "moving", "MOT17-11": "moving",
    "MOT17-13": "moving",
    # test split
    "MOT17-01": "static", "MOT17-03": "static", "MOT17-08": "static",
    "MOT17-06": "moving", "MOT17-07": "moving", "MOT17-12": "moving",
    "MOT17-14": "moving",
}
# MOT20 sequences are described by the benchmark as static-camera crowd scenes.
MOT20_CAMERA = {f"MOT20-{i:02d}": "static" for i in range(1, 9)}


def camera_label(seq: str) -> str:
    key = seq[:8] if seq.startswith("MOT17") else seq[:8]
    return MOT17_CAMERA.get(key, MOT20_CAMERA.get(key, "unknown"))


def load_dets(seq_dir: str) -> dict[int, np.ndarray]:
    """Public detections from det/det.txt, grouped by frame. MOT format:
    frame, id, x, y, w, h, conf, ...  -> returns tlbr+conf."""
    path = os.path.join(seq_dir, "det", "det.txt")
    if not os.path.exists(path):
        return {}
    arr = np.loadtxt(path, delimiter=",")
    if arr.ndim == 1:
        arr = arr[None, :]
    out: dict[int, np.ndarray] = {}
    for f in np.unique(arr[:, 0]).astype(int):
        rows = arr[arr[:, 0] == f]
        tlbr = np.stack([rows[:, 2], rows[:, 3],
                         rows[:, 2] + rows[:, 4], rows[:, 3] + rows[:, 5],
                         rows[:, 6]], axis=1)
        out[f] = tlbr
    return out


def scan_sequence(seq_dir: str, downscale: int = 2, use_dets: bool = True,
                  limit: int | None = None) -> pd.DataFrame:
    seq = os.path.basename(seq_dir.rstrip("/"))
    img_dir = os.path.join(seq_dir, "img1")
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png")))
    if limit:
        files = files[:limit]
    dets = load_dets(seq_dir) if use_dets else {}

    gmc = InstrumentedSparseOptFlowGMC(downscale=downscale, keep_inlier_xy=False)
    t0 = time.time()
    for i, fn in enumerate(files, start=1):
        img = cv2.imread(os.path.join(img_dir, fn))
        if img is None:
            continue
        gmc.apply(img, dets.get(i), frame_id=i)
    df = gmc.to_dataframe()
    df.insert(0, "sequence", seq)
    df.insert(1, "camera", camera_label(seq))
    print(f"  {seq:22s} {len(df):5d} frames  {time.time()-t0:6.1f}s  "
          f"cam={camera_label(seq)}", flush=True)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="e.g. .../MOT17/train")
    ap.add_argument("--out", required=True)
    ap.add_argument("--downscale", type=int, default=2)
    ap.add_argument("--filter", default="", help="substring filter on sequence name")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-dets", action="store_true")
    a = ap.parse_args()

    seqs = sorted(d for d in os.listdir(a.root)
                  if os.path.isdir(os.path.join(a.root, d, "img1")))
    if a.filter:
        seqs = [s for s in seqs if a.filter in s]
    print(f"scanning {len(seqs)} sequences from {a.root}")
    if a.workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(a.workers) as ex:
            frames = list(ex.map(scan_sequence,
                                 [os.path.join(a.root, s) for s in seqs],
                                 [a.downscale] * len(seqs),
                                 [not a.no_dets] * len(seqs),
                                 [a.limit] * len(seqs)))
    else:
        frames = [scan_sequence(os.path.join(a.root, s), a.downscale,
                                not a.no_dets, a.limit) for s in seqs]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(a.out, index=False)
    print(f"\nwrote {len(df)} rows -> {a.out}")


if __name__ == "__main__":
    main()

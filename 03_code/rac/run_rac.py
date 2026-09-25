"""
Run a RAC-Track configuration over the MOT17 half-val split using FROZEN detections.

Every ablation configuration reads the same detection .npz files, so detections are
byte-identical by construction rather than by promise (METHODOLOGY_BLUEPRINT §3.1).

Usage:
  run_rac.py --name A0_frozen                       # plain BoT-SORT behaviour
  run_rac.py --name A7_r1     --force-r 1.0 --p1 --p2 --p3   # K3 invariant: must equal A0
  run_rac.py --name A6_full   --p1 --p2 --p3 --per-target
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path as _P
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

BOT = p("03_code/BoT-SORT")
sys.path.insert(0, BOT)
sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))

from rac.rac_tracker import RACTracker, RACConfig  # noqa: E402

DATA = p("04_experiments/data/MOT17/train")
DETS = p("04_experiments/detections/MOT17-val-half")
OUT = p("04_experiments/trackers/MOT17-val-half")

# tools/track.py --default-parameters, MOT17 ablation branch
TRACK_BUFFER = {"MOT17-05-FRCNN": 14, "MOT17-13-FRCNN": 25}
TRACK_HIGH = {}


def make_args(seq: str, with_reid: bool, device: str) -> SimpleNamespace:
    high = TRACK_HIGH.get(seq, 0.6)
    return SimpleNamespace(
        track_high_thresh=high, track_low_thresh=0.1,
        new_track_thresh=high + 0.1,
        track_buffer=TRACK_BUFFER.get(seq, 30),
        match_thresh=0.8, aspect_ratio_thresh=1.6, min_box_area=10,
        mot20=False, with_reid=with_reid,
        proximity_thresh=0.5, appearance_thresh=0.25,
        cmc_method="sparseOptFlow", cmc_downscale=2,
        fast_reid_config=f"{BOT}/fast_reid/configs/MOT17/sbs_S50.yml",
        fast_reid_weights=p("04_experiments/weights/mot17_sbs_S50.pth"),
        device=device, name=seq, ablation=True, fps=30,
    )


def val_half_files(seq_dir: str) -> list[str]:
    img_dir = os.path.join(seq_dir, "img1")
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png")))
    return [os.path.join(img_dir, f) for f in files[len(files) // 2 + 1:]]


REF_WARPS = p("04_experiments/ref_warps")


def val_half_offset(seq_dir: str) -> int:
    """tracker frame 1 corresponds to original frame (offset+1)."""
    img_dir = os.path.join(seq_dir, "img1")
    n = len([f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))])
    return n // 2 + 1


def run_sequence(seq: str, cfg: RACConfig, with_reid: bool, device: str,
                 out_dir: str, log_dir: str) -> dict:
    det = np.load(os.path.join(DETS, f"{seq}.npz"))["det"]
    by_frame = {int(f): det[det[:, 0] == f][:, 1:] for f in np.unique(det[:, 0])}
    seq_dir = os.path.join(DATA, seq)
    files = val_half_files(seq_dir)

    args = make_args(seq, with_reid, device)
    tracker = RACTracker(args, frame_rate=30, cfg=cfg)
    if cfg.warp_source in ("reference", "reference_strict"):
        wp = os.path.join(REF_WARPS, f"{seq}.npz")
        if not os.path.exists(wp):
            raise FileNotFoundError(f"reference warps missing: {wp}")
        tracker.load_reference_warps(wp, frame_offset=val_half_offset(seq_dir))

    lines = []
    t0 = time.time()
    for frame_id, path in enumerate(files, start=1):
        img = cv2.imread(path)
        dets = by_frame.get(frame_id, np.zeros((0, 7), np.float32))
        targets = tracker.update(dets, img)
        for t in targets:
            tlwh = t.tlwh
            if tlwh[2] * tlwh[3] <= args.min_box_area:
                continue
            vertical = tlwh[2] / tlwh[3] > args.aspect_ratio_thresh
            if vertical:
                continue
            lines.append(f"{frame_id},{t.track_id},{tlwh[0]:.2f},{tlwh[1]:.2f},"
                         f"{tlwh[2]:.2f},{tlwh[3]:.2f},{t.score:.2f},-1,-1,-1\n")

    with open(os.path.join(out_dir, f"{seq}.txt"), "w") as f:
        f.writelines(lines)
    pd.DataFrame(tracker.log).to_csv(os.path.join(log_dir, f"{seq}.csv"), index=False)
    dt = time.time() - t0
    fb = getattr(tracker, "n_warp_fallback", 0)
    lq = getattr(tracker, "n_warp_lowq", 0)
    extra = (f"  warp_fallback={fb}  low_quality_used={lq}"
             if cfg.warp_source in ("reference", "reference_strict") else "")
    print(f"  {seq:22s} {len(files):5d} frames  {dt:6.1f}s  {len(lines):6d} rows{extra}", flush=True)
    return dict(sequence=seq, n_frames=len(files), n_rows=len(lines),
                seconds=round(dt, 1), warp_fallback=fb, warp_lowq=lq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--p1", action="store_true", help="warp shrinkage")
    ap.add_argument("--p2", action="store_true", help="covariance inflation")
    ap.add_argument("--p3", action="store_true", help="reliability-conditioned association")
    ap.add_argument("--per-target", action="store_true")
    ap.add_argument("--global-r", action="store_true", help="frame-level r only")
    ap.add_argument("--force-r", type=float, default=None)
    ap.add_argument("--placebo", action="store_true", help="I3 shuffled reliability")
    ap.add_argument("--signals", default="rho,n,eps,tau,kappa,phi")
    ap.add_argument("--theta-iou-max", type=float, default=0.8)
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--sigma-scale", type=float, default=1.0)
    ap.add_argument("--with-reid", action="store_true")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seqs", default="")
    ap.add_argument("--warp-source", default="online",
                    choices=["online", "reference", "reference_strict", "none"],
                    help="'reference' is the N2 analysis instrument, never a reported method")
    a = ap.parse_args()

    cfg = RACConfig(
        p1_shrinkage=a.p1, p2_inflation=a.p2, p3_association=a.p3,
        per_target=(a.per_target or not a.global_r),
        force_r=a.force_r, shuffle_placebo=a.placebo,
        signals=tuple(s for s in a.signals.split(",") if s),
        theta_iou_max=a.theta_iou_max, beta=a.beta, sigma_scale=a.sigma_scale,
        warp_source=a.warp_source,
    )

    out_dir = os.path.join(OUT, a.name, "data")
    log_dir = os.path.join(p("04_experiments/rac_logs"), a.name)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    seqs = a.seqs.split(",") if a.seqs else sorted(
        f[:-4] for f in os.listdir(DETS) if f.endswith(".npz"))
    print(f"[{a.name}] cfg={cfg}")
    recs = [run_sequence(s, cfg, a.with_reid, a.device, out_dir, log_dir) for s in seqs]

    json.dump(dict(name=a.name, config=cfg.__dict__, with_reid=a.with_reid,
                   sequences=recs),
              open(os.path.join(OUT, a.name, "run_config.json"), "w"), indent=1, default=str)
    print(f"[{a.name}] done -> {out_dir}")


if __name__ == "__main__":
    main()

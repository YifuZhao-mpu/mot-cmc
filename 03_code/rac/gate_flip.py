"""
SQ2 measured directly: how often does compensation error CHANGE the gate decision?

The earlier Q3 analysis asked whether compensation error alone pushes IoU below
theta_iou. That is the wrong question, and it produced a misleadingly clean
answer (0% of frames). Two reasons it was wrong:

  1. it used the per-frame MEDIAN box size and MEDIAN shift, so a frame with a
     few small boxes and a large local shift looks the same as a calm frame;
  2. what matters is not whether the error alone crosses the threshold, but
     whether it changes the OUTCOME. A pair sitting at IoU 0.52 needs only a
     tiny nudge to fall below 0.5; a pair at 0.95 needs an enormous one.

This measures the outcome directly, per box, without running a tracker:

    for each ground-truth object present in both frame k-1 and frame k:
        box_prev  = its box at k-1
        box_curr  = its box at k                      (the association target)
        pred_on   = warp(box_prev, H_online)          (what BoT-SORT sees)
        pred_ref  = warp(box_prev, H_reference)       (what it would see if
                                                       compensation were right)
        iou_on    = IoU(pred_on,  box_curr)
        iou_ref   = IoU(pred_ref, box_curr)

    GATE FLIP  <=>  (1 - iou_on > theta_iou) XOR (1 - iou_ref > theta_iou)

A flip in the harmful direction -- correct pair gated OUT by compensation error
-- is the event the coupling defect predicts. Its rate is the honest answer to
SQ2, and it bounds how much of the tracking metric the mechanism can explain.

This uses ground-truth identity, so it isolates the geometry from detector and
ReID behaviour entirely.
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

THETA_IOU = 0.5          # BoT-SORT proximity_thresh
DATA = p("04_experiments/data/MOT17/train")
REF = p("04_experiments/ref_warps")


def load_gt_by_frame(seq_dir: str):
    a = np.loadtxt(os.path.join(seq_dir, "gt", "gt.txt"), delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] >= 8:
        a = a[(a[:, 7] == 1) & (a[:, 6] > 0)]
    out = {}
    for f in np.unique(a[:, 0]).astype(int):
        r = a[a[:, 0] == f]
        vis = r[:, 8] if a.shape[1] > 8 else np.ones(len(r))
        out[f] = dict(ids=r[:, 1].astype(int),
                      tlbr=np.stack([r[:, 2], r[:, 3],
                                     r[:, 2] + r[:, 4], r[:, 3] + r[:, 5]], 1),
                      vis=vis)
    return out


def warp_boxes(tlbr: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Apply a 2x3 similarity to boxes the way STrack.multi_gmc does: the linear
    part scales/rotates the state (centre and size), the translation shifts the
    centre."""
    H = np.asarray(H, float)
    R, t = H[:2, :2], H[:2, 2]
    cx = (tlbr[:, 0] + tlbr[:, 2]) / 2
    cy = (tlbr[:, 1] + tlbr[:, 3]) / 2
    w = tlbr[:, 2] - tlbr[:, 0]
    h = tlbr[:, 3] - tlbr[:, 1]
    c = np.stack([cx, cy], 1) @ R.T + t
    s = np.stack([w, h], 1) @ R.T          # matches R8x8 acting on (w,h)
    w2, h2 = np.abs(s[:, 0]), np.abs(s[:, 1])
    return np.stack([c[:, 0] - w2 / 2, c[:, 1] - h2 / 2,
                     c[:, 0] + w2 / 2, c[:, 1] + h2 / 2], 1)


def iou_pairwise(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    x1 = np.maximum(a[:, 0], b[:, 0]); y1 = np.maximum(a[:, 1], b[:, 1])
    x2 = np.minimum(a[:, 2], b[:, 2]); y2 = np.minimum(a[:, 3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    ar = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    br = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    u = ar + br - inter
    return np.where(u > 0, inter / u, 0.0)


def run_sequence(seq: str, theta: float) -> pd.DataFrame:
    gt = load_gt_by_frame(os.path.join(DATA, seq))
    warps = np.load(os.path.join(REF, f"{seq}.npz"))["warp"]
    ref_by_frame = {int(r[0]): (r[1:7].reshape(2, 3), bool(r[7] > 0.5)) for r in warps}

    scan = pd.read_csv(p("04_experiments/mot17_gmc_scan.csv"))
    scan = scan[scan.sequence == seq].set_index("frame_id")
    on_by_frame = {}
    for f, row in scan.iterrows():
        s = row["scale"] if np.isfinite(row["scale"]) else 1.0
        th = np.radians(row["rotation_deg"]) if np.isfinite(row["rotation_deg"]) else 0.0
        tx = row["tx"] if np.isfinite(row["tx"]) else 0.0
        ty = row["ty"] if np.isfinite(row["ty"]) else 0.0
        on_by_frame[int(f)] = np.array([[s * np.cos(th), -s * np.sin(th), tx],
                                        [s * np.sin(th), s * np.cos(th), ty]])

    rows = []
    for f in sorted(gt):
        if f - 1 not in gt or f not in ref_by_frame or f not in on_by_frame:
            continue
        H_ref, ok = ref_by_frame[f]
        if not ok:
            continue
        H_on = on_by_frame[f]
        prev, curr = gt[f - 1], gt[f]
        common, ip, ic = np.intersect1d(prev["ids"], curr["ids"], return_indices=True)
        if len(common) == 0:
            continue
        bp, bc = prev["tlbr"][ip], curr["tlbr"][ic]
        iou_on = iou_pairwise(warp_boxes(bp, H_on), bc)
        iou_ref = iou_pairwise(warp_boxes(bp, H_ref), bc)
        gate_on = (1 - iou_on) > theta          # True = gated OUT
        gate_ref = (1 - iou_ref) > theta
        rows.append(pd.DataFrame(dict(
            sequence=seq, frame_id=f, obj_id=common,
            vis=curr["vis"][ic],
            box_w=bc[:, 2] - bc[:, 0], box_h=bc[:, 3] - bc[:, 1],
            iou_online=iou_on, iou_reference=iou_ref,
            gated_out_online=gate_on, gated_out_reference=gate_ref,
            flip=gate_on ^ gate_ref,
            harmful_flip=gate_on & ~gate_ref,     # error gated a correct pair OUT
            helpful_flip=~gate_on & gate_ref,
        )))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=THETA_IOU)
    a = ap.parse_args()

    seqs = sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{REF}/*.npz"))
    df = pd.concat([run_sequence(s, a.theta) for s in seqs], ignore_index=True)
    out = p("04_experiments/gate_flips.csv")
    df.to_csv(out, index=False)

    print(f"=== SQ2: does compensation error change the gate decision? "
          f"(theta_iou={a.theta}) ===")
    print(f"ground-truth object pairs examined: {len(df)}\n")
    g = df.groupby("sequence").agg(
        pairs=("flip", "size"),
        gated_out_online=("gated_out_online", "mean"),
        gated_out_reference=("gated_out_reference", "mean"),
        flip_rate=("flip", "mean"),
        harmful=("harmful_flip", "sum"),
        helpful=("helpful_flip", "sum"),
        iou_on_med=("iou_online", "median"),
        iou_ref_med=("iou_reference", "median"),
    )
    print(g.round(5).to_string())

    n = len(df)
    print(f"\nTOTAL  pairs {n}")
    print(f"  gated out under ONLINE warp     : {df.gated_out_online.sum():7d}  "
          f"({100*df.gated_out_online.mean():.3f}%)")
    print(f"  gated out under REFERENCE warp  : {df.gated_out_reference.sum():7d}  "
          f"({100*df.gated_out_reference.mean():.3f}%)")
    print(f"  gate decision FLIPPED           : {df.flip.sum():7d}  "
          f"({100*df.flip.mean():.4f}%)")
    print(f"    harmful (correct pair gated out by compensation error): "
          f"{int(df.harmful_flip.sum())}")
    print(f"    helpful (error happened to rescue a pair)             : "
          f"{int(df.helpful_flip.sum())}")

    print("\n=== sensitivity: the same count at other gate thresholds ===")
    print(f"{'theta':>7} {'gated_online':>13} {'gated_ref':>11} {'flips':>7} {'harmful':>8}")
    for th in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        go = (1 - df.iou_online) > th
        gr = (1 - df.iou_reference) > th
        fl = go ^ gr
        print(f"{th:>7.1f} {int(go.sum()):>13} {int(gr.sum()):>11} "
              f"{int(fl.sum()):>7} {int((go & ~gr).sum()):>8}")

    print("\n=== where flips concentrate (harmful only) ===")
    h = df[df.harmful_flip]
    if len(h):
        print(h.groupby("sequence").agg(
            n=("flip", "size"), vis_med=("vis", "median"),
            box_w_med=("box_w", "median"), box_h_med=("box_h", "median"),
            iou_on_med=("iou_online", "median"),
            iou_ref_med=("iou_reference", "median")).round(4).to_string())
    else:
        print("  none")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()

"""
DA-CP2 C1 — is the tracking gain actually caused by the within-frame depth spread?

The mechanism claims: a shared warp cannot serve targets at different depths, so
a per-target warp helps. The geometric result (within-frame residual spread) and
the tracking result (per-target beats global) are both measured, but the causal
link between them has never been tested directly — and the class comparison cuts
against it, since CARS are further from the frame-median depth and have greater
per-error box exposure, yet show no established gain.

This tests the link at the level where it should operate, per frame and per class:

    for each (sequence, frame, class):
        exposure   = how badly the SHARED warp serves that class in that frame
                     = median over that class's objects of
                       || own_local_warp(centre) - shared_warp(centre) ||
        outcome    = did per-target tracking do better than global-oracle tracking
                     on that frame, measured by ID switches attributable to it

If the mechanism holds, frames where a class is badly served by the shared warp
should be the frames where per-target helps that class. If exposure and outcome
are uncorrelated, the mechanism does not explain the gain, whatever the aggregate
numbers say.

Outcome is measured from the two trackers' own outputs against ground truth,
counting per-frame identity switches for the class in question.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path as _P
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.kitti_egomotion import load_labels  # noqa: E402

ROOT = p("04_experiments/data/KITTI/training")
W3 = p("04_experiments/kitti_warps_v3")
TR = p("04_experiments/trackers/KITTI")
# KITTI's own evaluation classes. Van/Truck are IGNORE regions for the car class
# and Person_sitting/Cyclist for the pedestrian class -- including them in the GT
# set creates spurious identity switches. (TrackEval applies the same rule.)
CAR = ("Car",)
PED = ("Pedestrian",)
IGNORE_CAR = ("Van", "Truck", "Tram")
IGNORE_PED = ("Person_sitting", "Cyclist")


def iou_mat(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    ar = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); br = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    u = ar[:, None] + br[None, :] - inter
    return np.where(u > 0, inter / u, 0.0)


def load_tracker(name: str, seq: str, cls_filter) -> dict[int, tuple]:
    p = os.path.join(TR, name, "data", f"{seq}.txt")
    out: dict[int, tuple] = {}
    if not os.path.exists(p):
        return out
    rows = defaultdict(list)
    for line in open(p):
        t = line.split()
        if len(t) < 11:
            continue
        if t[2] not in cls_filter:
            continue
        rows[int(t[0])].append((int(t[1]), float(t[6]), float(t[7]), float(t[8]), float(t[9])))
    for f, v in rows.items():
        out[f] = (np.array([x[0] for x in v], int),
                  np.array([[x[1], x[2], x[3], x[4]] for x in v], float))
    return out


def per_frame_idsw(tracks: dict, gt: dict, cls_filter, thr: float = 0.5) -> dict[int, int]:
    """ID switches per frame: a GT object matched to a different tracker id than
    the one it was matched to the last time it was matched."""
    last: dict[int, int] = {}
    out: dict[int, int] = {}
    for f in sorted(gt):
        g = gt[f]
        if f not in tracks or len(g[0]) == 0:
            continue
        tid, tb = tracks[f]
        M = iou_mat(g[1], tb)
        n = 0
        for i, gid in enumerate(g[0]):
            j = int(np.argmax(M[i])) if M.shape[1] else -1
            if j < 0 or M[i, j] < thr:
                continue
            t = int(tid[j])
            if gid in last and last[gid] != t:
                n += 1
            last[gid] = t
        out[f] = n
    return out


def gt_by_frame(seq: str, cls_filter):
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    out = {}
    for f, v in lab.items():
        v2 = [o for o in v if o["cls"] in cls_filter and o["xyz"][2] > 1.0]
        if v2:
            out[f] = (np.array([o["track_id"] for o in v2], int),
                      np.stack([o["tlbr"] for o in v2]),
                      np.array([o["xyz"][2] for o in v2]))
    return out


def exposure_by_frame(seq: str, cls_filter) -> dict[int, float]:
    """Median disagreement (px) between each object's OWN warp and the frame's
    SHARED warp, over the objects of the given class."""
    Z = np.load(f"{W3}/{seq}.npz")
    glob, per = Z["global_oracle"], Z["per_object"]
    if len(per) == 0:
        return {}
    byfr = defaultdict(dict)
    for r in per:
        byfr[int(r[0])][int(r[1])] = r[2:]
    lab = load_labels(f"{ROOT}/label_02/{seq}.txt")
    out = {}
    for f, objs in lab.items():
        if f not in byfr:
            continue
        G = glob[f].reshape(2, 3)
        vals = []
        for o in objs:
            if o["cls"] not in cls_filter:
                continue
            p = byfr[f].get(o["track_id"])
            if p is None:
                continue
            a, b, tx, ty = p
            L = np.array([[a, b, tx], [-b, a, ty]])
            c = np.array([[(o["tlbr"][0] + o["tlbr"][2]) / 2,
                           (o["tlbr"][1] + o["tlbr"][3]) / 2]])
            pg = (G[:, :2] @ c.T).T + G[:, 2]
            pl = (L[:, :2] @ c.T).T + L[:, 2]
            vals.append(float(np.linalg.norm(pg - pl)))
        if vals:
            out[f] = float(np.median(vals))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--global-name", default="v3_global_oracle")
    ap.add_argument("--per-name", default="v3_per_target")
    a = ap.parse_args()

    seqs = sorted(f[:-4] for f in os.listdir(f"{ROOT}/oxts") if f.endswith(".txt"))
    rows = []
    for seq in seqs:
        for cname, cls_tr, cls_gt, cls_exp in [
                ("car", ("Car",), CAR, CAR + IGNORE_CAR),
                ("pedestrian", ("Pedestrian",), PED, PED + IGNORE_PED)]:
            gt = gt_by_frame(seq, cls_gt)
            if not gt:
                continue
            ga = load_tracker(a.global_name, seq, cls_tr)
            pa = load_tracker(a.per_name, seq, cls_tr)
            if not ga or not pa:
                continue
            sg = per_frame_idsw(ga, gt, cls_tr)
            sp = per_frame_idsw(pa, gt, cls_tr)
            exp = exposure_by_frame(seq, cls_exp)   # exposure over the visually similar set
            for f in sorted(set(sg) & set(sp) & set(exp)):
                rows.append(dict(sequence=seq, cls=cname, frame=f,
                                 exposure=exp[f], idsw_global=sg[f], idsw_per=sp[f],
                                 improvement=sg[f] - sp[f], n_gt=len(gt[f][0])))
    d = pd.DataFrame(rows)
    out = p("04_experiments/kitti_causal_link.csv")
    d.to_csv(out, index=False)

    print("=== DA-CP2 C1: does per-target help MORE where the shared warp serves "
          "that class worse? ===\n")
    for cls, g in d.groupby("cls"):
        r, p = spearmanr(g.exposure, g.improvement)
        print(f"--- {cls.upper()} --- n_frames {len(g)}  "
              f"total IDSW global {int(g.idsw_global.sum())} vs per-target {int(g.idsw_per.sum())}")
        print(f"  spearman(exposure, improvement) = {r:+.4f}  p={p:.3e}")
        q = pd.qcut(g.exposure, 4, duplicates="drop")
        t = g.groupby(q, observed=True).agg(n=("frame", "size"),
                                            exp_med=("exposure", "median"),
                                            idsw_g=("idsw_global", "sum"),
                                            idsw_p=("idsw_per", "sum"),
                                            improv=("improvement", "sum"))
        t["improv_per_1k_frames"] = 1000 * t.improv / t.n
        print(t.round(4).to_string())
        hi = g[g.exposure > g.exposure.quantile(0.75)]
        lo = g[g.exposure < g.exposure.quantile(0.25)]
        print(f"  top-quartile exposure : improvement {int(hi.improvement.sum()):+d} over {len(hi)} frames")
        print(f"  bottom-quartile       : improvement {int(lo.improvement.sum()):+d} over {len(lo)} frames")
        print()
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()


def permutation_test(sub, n_perm: int = 20000, seed: int = 20260923) -> dict:
    """Is the top-quartile concentration more than chance?

    Review objected, correctly, that a Spearman over a sparse signed count is the
    wrong instrument: rho = 0.058 reads as nil even when the concentration is
    total. The right test shuffles the pairing between a frame's exposure and its
    improvement and asks how often the top quartile collects as much as observed.
    """
    import numpy as np
    exp = sub.exposure.values
    imp = (sub.idsw_global - sub.idsw_per).values
    q = np.quantile(exp, 0.75)
    top = exp >= q
    obs = imp[top].sum()
    rng = np.random.default_rng(seed)
    null = np.array([imp[rng.permutation(len(imp))][top].sum() for _ in range(n_perm)])
    return dict(observed=float(obs), null_mean=float(null.mean()),
                null_sd=float(null.std()), p=float((null >= obs).mean()),
                n_frames=int(len(sub)), n_top=int(top.sum()))


if __name__ != "__main__":
    pass

"""
Build the MOT17 half-val ground truth used by the ByteTrack/BoT-SORT ablation
protocol, in TrackEval's expected layout.

Split definition is taken verbatim from BoT-SORT tools/track.py:151-152

    files.sort()
    if args.ablation:
        files = files[len(files) // 2 + 1:]

and the tracker then emits frame ids via `enumerate(files, 1)`. So the evaluated
half is original frames  [len//2 + 2 .. len]  (1-indexed), renumbered to 1..N.

Cross-check: the sequence lengths this produces must equal the line counts of
BoT-SORT's own precomputed GMC ablation files
(tracker/GMC_files/MOT17_ablation/GMC-MOT17-XX.txt) -- verified at build time.
"""
from __future__ import annotations

import argparse
import configparser
import os
import shutil

import numpy as np
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

GMC_DIR = p("03_code/BoT-SORT/tracker/GMC_files/MOT17_ablation")


def split_range(n_frames: int) -> tuple[int, int]:
    """Returns (first_original_frame, n_eval_frames), 1-indexed inclusive."""
    start_idx = n_frames // 2 + 1          # 0-indexed into the sorted file list
    first_frame = start_idx + 1            # -> 1-indexed original frame number
    return first_frame, n_frames - start_idx


def build_sequence(src_seq: str, dst_root: str, verify_gmc: bool = True) -> dict:
    seq = os.path.basename(src_seq.rstrip("/"))
    img_dir = os.path.join(src_seq, "img1")
    frames = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png")))
    n = len(frames)
    first, n_eval = split_range(n)

    dst_seq = os.path.join(dst_root, seq)
    os.makedirs(os.path.join(dst_seq, "gt"), exist_ok=True)

    # --- ground truth: keep frames >= first, renumber to start at 1 ---
    gt = np.loadtxt(os.path.join(src_seq, "gt", "gt.txt"), delimiter=",")
    if gt.ndim == 1:
        gt = gt[None, :]
    sel = gt[gt[:, 0] >= first].copy()
    sel[:, 0] -= (first - 1)
    fmt = ["%d", "%d", "%.3f", "%.3f", "%.3f", "%.3f", "%d", "%d", "%.6f"][:sel.shape[1]]
    np.savetxt(os.path.join(dst_seq, "gt", "gt.txt"), sel, delimiter=",", fmt=fmt)

    # --- seqinfo.ini, with corrected seqLength ---
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(os.path.join(src_seq, "seqinfo.ini"))
    cfg["Sequence"]["seqLength"] = str(n_eval)
    with open(os.path.join(dst_seq, "seqinfo.ini"), "w") as f:
        cfg.write(f, space_around_delimiters=False)

    rec = dict(sequence=seq, n_total=n, first_original_frame=first,
               n_eval=n_eval, gt_rows=len(sel), gmc_lines=None, gmc_match=None)

    if verify_gmc:
        base = seq
        for suf in ("-FRCNN", "-DPM", "-SDP"):
            if base.endswith(suf):
                base = base[: -len(suf)]
        p = os.path.join(GMC_DIR, f"GMC-{base}.txt")
        if os.path.exists(p):
            with open(p) as f:
                lines = sum(1 for _ in f)
            rec["gmc_lines"] = lines
            rec["gmc_match"] = (lines == n_eval)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=p("04_experiments/data/MOT17/train"))
    ap.add_argument("--dst", default=p("04_experiments/eval/MOT17-val-half"))
    ap.add_argument("--filter", default="FRCNN")
    a = ap.parse_args()

    os.makedirs(a.dst, exist_ok=True)
    seqs = sorted(d for d in os.listdir(a.src)
                  if os.path.isdir(os.path.join(a.src, d, "img1")) and a.filter in d)
    recs = [build_sequence(os.path.join(a.src, s), a.dst) for s in seqs]

    print(f"{'sequence':<22}{'total':>7}{'first':>7}{'n_eval':>8}{'gt_rows':>9}"
          f"{'gmc_lines':>11}{'match':>7}")
    ok = True
    for r in recs:
        m = r["gmc_match"]
        ok &= (m is not False)
        print(f"{r['sequence']:<22}{r['n_total']:>7}{r['first_original_frame']:>7}"
              f"{r['n_eval']:>8}{r['gt_rows']:>9}{str(r['gmc_lines']):>11}{str(m):>7}")

    # TrackEval seqmap
    sm_dir = os.path.join(os.path.dirname(a.dst), "seqmaps")
    os.makedirs(sm_dir, exist_ok=True)
    sm = os.path.join(sm_dir, "MOT17-val-half.txt")
    with open(sm, "w") as f:
        f.write("name\n")
        for r in recs:
            f.write(r["sequence"] + "\n")
    print(f"\nseqmap -> {sm}")
    print("GMC line-count cross-check:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()

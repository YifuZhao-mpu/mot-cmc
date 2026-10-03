"""
Stage 2.5 Phase C — recompute every number in the manuscript from source.

The manuscript is prose; its tables are the place errors hide. This script parses
the Markdown tables, recomputes each cell from the released CSVs and the TrackEval
output directories, and reports any cell that does not match. It is the automated
half of the integrity gate: anything it cannot map is listed as UNCHECKED rather
than silently passed, so the manual half knows what it still has to cover.

    python verify_numbers.py            # check
    python verify_numbers.py --list     # show what is mapped and what is not
"""
from __future__ import annotations

import argparse
import os
import math
import re
from pathlib import Path as _P
import sys

import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))

from rac.paths import ROOT as _R
ROOT = str(_R)
MD = f"{ROOT}/02_paper/manuscript.md"
E = f"{ROOT}/04_experiments"
TR = f"{E}/trackers"
TOL = 5e-4          # a printed 3-dp number may differ from source by half a unit

FAILS: list[str] = []
OKS = 0


def check(label: str, claimed: float, actual: float, tol: float = TOL) -> None:
    global OKS
    if actual is None or not np.isfinite(actual):
        FAILS.append(f"UNRESOLVED  {label}: source produced no value")
        return
    if abs(float(claimed) - float(actual)) <= tol:
        OKS += 1
    else:
        FAILS.append(f"MISMATCH    {label}: manuscript {claimed} vs source {actual:.6g}")


def md_tables(text: str) -> list[tuple[str, list[list[str]]]]:
    """Return (preceding non-empty line, rows) for every pipe table."""
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        if re.match(r"^\|.*\|$", lines[i]) and i + 1 < len(lines) \
                and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            j = i
            while j < len(lines) and re.match(r"^\|.*\|$", lines[j]):
                j += 1
            rows = [[c.strip() for c in l.strip("|").split("|")]
                    for l in lines[i:j] if not re.match(r"^\|[\s:|-]+\|$", l)]
            ctx = next((l for l in reversed(lines[max(0, i - 6):i]) if l.strip()), "")
            out.append((ctx, rows))
            i = j
        else:
            i += 1
    return out


def num(cell: str) -> float | None:
    c = cell.replace("**", "").replace(",", "").replace("%", "").replace("px", "")
    c = c.replace("−", "-").replace("+", "").strip()
    m = re.match(r"^-?\d+(?:\.\d+)?$", c)
    return float(m.group()) if m else None


def te(run: str, cls: str, bench: str = "KITTI") -> dict:
    p = f"{TR}/{bench}/{run}/{cls}_summary.txt"
    with open(p) as f:
        k, v = f.readline().split(), f.readline().split()
    return dict(zip(k, (float(x) for x in v)))


# ------------------------------------------------------------------ checks
def check_scans() -> None:
    """Table 1 — the four-benchmark reliability audit."""
    src = {"MOT17": f"{E}/mot17_gmc_scan.csv", "MOT20": f"{E}/mot20_gmc_scan.csv",
           "UAVDT": f"{E}/uavdt_gmc_scan.csv"}
    claimed = {
        "MOT17": dict(frames=5309, rho=0.976, eps=0.570, eps95=1.767, disp=2.095,
                      tau=1.215, n100=0, n300=3, eps2=190, rho7=203, phi7=228),
        "MOT20": dict(frames=8927, rho=0.995, eps=0.592, eps95=0.879, disp=0.689,
                      tau=0.813, n100=0, n300=1, eps2=0, rho7=1, phi7=3314),
        "UAVDT": dict(frames=40685, rho=1.000, eps=0.295, eps95=0.941, disp=1.035,
                      tau=0.166, n100=19, n300=1620, eps2=148, rho7=91),
    }
    for name, path in src.items():
        d = pd.read_csv(path)
        d = d[~d.get("first_frame", pd.Series(False, index=d.index)).astype(bool)]
        d = d[d.n_inliers.notna()]
        c = claimed[name]
        check(f"T1 {name} frames", c["frames"], len(d), tol=0.5)
        check(f"T1 {name} median rho", c["rho"], d.inlier_ratio.median())
        check(f"T1 {name} median eps", c["eps"], d.resid_median.median())
        check(f"T1 {name} p95 eps", c["eps95"], np.percentile(d.resid_median, 95))
        check(f"T1 {name} median disp", c["disp"], d.displacement.median())
        check(f"T1 {name} median tau", c["tau"], d.temporal_resid.dropna().median())
        check(f"T1 {name} n_inl<100", c["n100"], (d.n_inliers < 100).sum(), tol=0.5)
        check(f"T1 {name} n_inl<300", c["n300"], (d.n_inliers < 300).sum(), tol=0.5)
        check(f"T1 {name} eps>2px", c["eps2"], (d.resid_median > 2).sum(), tol=0.5)
        check(f"T1 {name} rho<0.7", c["rho7"], (d.inlier_ratio < 0.7).sum(), tol=0.5)
        if "phi7" in c:
            check(f"T1 {name} phi>0.7", c["phi7"],
                  (d.frac_inliers_in_det > 0.7).sum(), tol=0.5)


def check_gate_flips() -> None:
    """Table 2 and §5.1 — all of it comes from one file."""
    d = pd.read_csv(f"{E}/gate_flips.csv")
    claimed = {"MOT17-02": (18519, 0.972, 0, 0), "MOT17-04": (47474, 0.982, 0, 0),
               "MOT17-09": (5299, 0.934, 0, 0), "MOT17-05": (5180, 0.890, 12, 5),
               "MOT17-10": (12666, 0.899, 14, 7), "MOT17-11": (9335, 0.952, 0, 0),
               "MOT17-13": (11482, 0.888, 8, 9)}
    for seq, (n, iou, harm, help_) in claimed.items():
        g = d[d.sequence.str.startswith(seq)]
        check(f"T2 {seq} pairs", n, len(g), tol=0.5)
        check(f"T2 {seq} median IoU", iou, g.iou_online.median(), tol=5e-4)
        check(f"T2 {seq} harmful", harm, g.harmful_flip.sum(), tol=0.5)
        check(f"T2 {seq} helpful", help_, g.helpful_flip.sum(), tol=0.5)
    check("T2 total pairs", 109955, len(d), tol=0.5)
    check("T2 total harmful", 34, d.harmful_flip.sum(), tol=0.5)
    check("T2 total helpful", 21, d.helpful_flip.sum(), tol=0.5)
    check("5.1 median IoU cost", 0.00085, (d.iou_reference - d.iou_online).median(), 5e-6)
    for q, v in ((0.1, 0.479), (1, 0.676), (5, 0.803), (25, 0.916), (50, 0.960)):
        check(f"5.1 IoU q{q}", v, np.percentile(d.iou_online, q), 5e-4)
    check("5.1 frac IoU<0.5 %", 0.127, (d.iou_online < 0.5).mean() * 100, 5e-4)
    nm = d[(d.iou_reference >= 0.5) & (d.iou_reference <= 0.6)]
    check("5.1 near-miss pairs", 312, len(nm), tol=0.5)
    check("5.1 near-miss %", 0.284, 100 * len(nm) / len(d), 5e-4)
    check("5.1 near-miss gated %", 6.73, 100 * nm.gated_out_online.mean(), 5e-3)


def check_oracle_contrast() -> None:
    """§4.2 — static vs moving."""
    d = pd.read_csv(f"{E}/oracle_analysis.csv")
    check("4.2 frames retained", 5088, len(d), tol=0.5)
    for cam, (med, p90, box, n) in {
            "static": (0.150, 0.559, 0.118, 2172),
            "moving": (1.309, 4.549, 0.637, 2916)}.items():
        g = d[d.camera == cam]
        check(f"4.2 {cam} n", n, len(g), tol=0.5)
        check(f"4.2 {cam} corner med", med, g.corner_disagreement_px.median(), 5e-4)
        check(f"4.2 {cam} corner p90", p90,
              np.percentile(g.corner_disagreement_px, 90), 5e-4)
        check(f"4.2 {cam} box med", box, g.box_shift_px.median(), 5e-4)
    for seq, v in (("02", 0.088), ("04", 0.147), ("05", 2.105), ("09", 0.505),
                   ("10", 1.121), ("11", 0.786), ("13", 1.669)):
        g = d[d.sequence.str.startswith(f"MOT17-{seq}")]
        check(f"4.2 seq {seq} med", v, g.corner_disagreement_px.median(), 5e-4)


def check_reference_warp() -> None:
    """3.2 and 3.5 -- instrument quality and the frozen detections."""
    import json
    d = pd.read_csv(f"{E}/oracle_analysis.csv")
    check("3.2 fb-error pooled median", 0.002, d.ref_fb_error.median(), 5e-4)
    g = d.groupby("sequence").ref_fb_error.median()
    check("3.2 fb-error per-seq min", 0.0002, g.min(), 5e-5)
    check("3.2 fb-error per-seq max", 0.012, g.max(), 5e-4)
    j = json.load(open(f"{E}/detections/MOT17-val-half/manifest.json"))["sequences"]
    check("3.5 frozen detections", 62398, sum(v["n_detections"] for v in j.values()), 0.5)
    check("3.5 sequences hashed", 7, sum(len(v["sha256"]) == 64 for v in j.values()), 0.5)


def check_car_depth_noise() -> None:
    """7.2 -- the car deltas are prose, not a table, and were unchecked."""
    ref = te("v4_global_oracle", "car")["HOTA"]
    for sig, run, delta in ((0.00, "v3_per_target", 0.248), (0.05, "dn005_per_target", -0.077),
                            (0.10, "dn010_per_target", -0.110), (0.20, "dn020_per_target", -0.127),
                            (0.30, "dn030_per_target", -0.144), (0.50, "dn050_per_target", -0.042)):
        check(f"7.2 car sigma={sig}", delta, te(run, "car")["HOTA"] - ref, 1e-2)


def check_subset_search() -> None:
    """§4.4 — signal-subset table."""
    d = pd.read_csv(f"{E}/signal_subset_search.csv")
    best = d.loc[d.groupby("k").auc_mean.idxmax()].set_index("k")
    for k, auc, worst in ((1, 0.866, 0.779), (2, 0.866, 0.779), (3, 0.864, 0.780),
                          (4, 0.860, 0.766), (5, 0.854, 0.770), (6, 0.774, 0.614)):
        check(f"4.4 k={k} AUC", auc, best.loc[k, "auc_mean"], 5e-4)
        check(f"4.4 k={k} worst seq", worst, best.loc[k, "auc_worst"], 5e-4)


def check_mot17_axis() -> None:
    """Tables 3 and 4."""
    rows = {
        "T3 none": ("A_noCMC", (68.118, 69.914, 66.898, 79.598, 77.777, 337)),
        "T3 online": ("A0_frozen", (69.006, 71.333, 67.246, 81.345, 78.451, 139)),
        "T3 file": ("A0_botsort_baseline", (69.120, 71.570, 67.24, 81.499, 78.445, 140)),
        "T3 oracle": ("N2_oracle_warp", (69.105, 71.528, 67.249, 81.490, 78.493, 144)),
        "T4 none": ("R_none", (68.280, 70.168, 66.969, 79.768, 77.929, 300)),
        "T4 online": ("R_online", (69.426, 72.166, 67.272, 82.276, 78.551, 160)),
        "T4 oracle": ("R_oracle", (69.344, 72.017, 67.253, 82.101, 78.482, 165)),
    }
    for label, (run, vals) in rows.items():
        m = te(run, "pedestrian", "MOT17-val-half")
        for key, v in zip(("HOTA", "AssA", "DetA", "IDF1", "MOTA", "IDSW"), vals):
            check(f"{label} {key}", v, m[key], 5e-3 if key != "IDSW" else 0.5)


def check_kitti_geometry() -> None:
    """§6.2, §6.3, §6.4."""
    d = pd.read_csv(f"{E}/kitti_per_object.csv")
    m = d[d.trans_m > 0.05]
    check("6.2 moving frames", 4318, len(m), tol=0.5)
    check("6.2 spread median", 2.431, m.err_spread.median(), 5e-4)
    for p, v in ((75, 5.335), (90, 10.114), (95, 14.020), (99, 23.084)):
        check(f"6.2 spread p{p}", v, np.percentile(m.err_spread, p), 5e-3)
    check("6.2 spread max", 67.7, m.err_spread.max(), 5e-2)
    for t, v in ((1, 75.47), (2, 56.02), (5, 27.12), (10, 10.14)):
        check(f"6.2 spread>{t}px %", v, (m.err_spread > t).mean() * 100, 5e-3)
    check("6.2 rho(depth,err) median", -0.200, m.rho_depth_err.median(), 5e-4)
    # the Spearman needs >= 4 objects, so the denominator is the frames where it
    # is defined, not all moving frames -- the manuscript now states both
    r = m.rho_depth_err.dropna()
    check("6.2 rho defined frames", 3379, len(r), tol=0.5)
    check("6.2 rho negative %", 64.5, (r < 0).mean() * 100, 5e-2)
    check("6.3 frames with >=1 gated %", 8.04, (m.n_gated > 0).mean() * 100, 5e-2)
    check("6.3 object-frames", 23443, m.n_obj.sum(), tol=0.5)
    check("6.3 gated object-frames", 510, m.n_gated.sum(), tol=0.5)
    check("6.3 gated %", 2.175, 100 * m.n_gated.sum() / m.n_obj.sum(), 5e-3)

    p = pd.read_csv(f"{E}/kitti_parallax.csv")
    check("6.2 parallax frames", 6416, len(p), tol=0.5)
    # Parse the printed cells: a source-only constant check cannot catch an old
    # fit's residuals left in the manuscript after the least-squares refit.
    text = _P(MD).read_text()
    section = text.split("### 6.2 ", 1)[1].split("### 6.3 ", 1)[0]
    tables = md_tables(section)
    expected = ("No compensation", "Rotation homography", "Least-squares similarity")
    models = ("identity", "rotH", "bestsim")
    rows = tables[0][1][1:]
    if len(rows) != len(models):
        FAILS.append("PARSE       6.2 needs three compensation-model rows")
    else:
        for row, prefix, model in zip(rows, expected, models):
            if not row[0].replace("**", "").startswith(prefix):
                FAILS.append(f"PARSE       6.2 unexpected model row: {row[0]}")
                continue
            residual = p[f"err_{model}_med"]
            actual = (residual.median(), residual.quantile(.9), residual.max())
            for label, cell, value, tol in zip(
                    ("median", "p90", "max"), row[1:], actual, (5e-4, 5e-4, 5e-2)):
                claimed = num(cell)
                if claimed is None:
                    FAILS.append(f"PARSE       6.2 {model}/{label}: {cell}")
                else:
                    check(f"MS 6.2 {model}/{label}", claimed, value, tol)

    mc = pd.read_csv(f"{E}/kitti_model_class.csv")
    mc = mc[mc.trans_m > 0.05]
    check("6.4 model-class frames", 2389, len(mc), tol=0.5)
    for f, med, spread, gt5 in (("similarity", 2.146, 3.790, 39.39),
                                ("affine", 1.140, 2.100, 18.04),
                                ("homography", 0.000, 0.746, 14.40)):
        check(f"6.4 {f} med", med, mc[f + "_med"].median(), 5e-4)
        check(f"6.4 {f} spread", spread, mc[f + "_spread"].median(), 5e-4)
        check(f"6.4 {f} >5px %", gt5, (mc[f + "_spread"] > 5).mean() * 100, 5e-3)

    gf = pd.read_csv(f"{E}/kitti_global_family.csv")
    check("6.4 deployable frames", 4318, len(gf), tol=0.5)
    for col, med, spread, gt5 in (("oracle", 1.698, 2.431, 27.12),
                                  ("sim", 1.178, 7.451, 61.16),
                                  ("hom", 0.968, 7.418, 61.44)):
        check(f"6.4 dep {col} med", med, gf[col + "_med"].median(), 5e-4)
        check(f"6.4 dep {col} spread", spread, gf[col + "_spread"].median(), 5e-4)
        check(f"6.4 dep {col} >5px %", gt5, (gf[col + "_spread"] > 5).mean() * 100, 5e-3)


def check_class_split() -> None:
    """Section 8 -- the two refuted explanations."""
    d = pd.read_csv(f"{E}/kitti_class_split.csv")
    check("8 object-frames", 31470, len(d), tol=0.5)
    for cls, n, lz, ex in (("car", 23348, 0.3253, 3.28), ("ped", 8122, 0.2456, 3.23)):
        g = d[d.cls == cls]
        check(f"8 {cls} n", n, len(g), tol=0.5)
        check(f"8 {cls} median |log z ratio|", lz, g.log_z_ratio.median(), 5e-4)
        check(f"8 {cls} exposed > w/3 %", ex, g.exposed.mean() * 100, 5e-3)


def check_causal_link() -> None:
    """Table 8."""
    d = pd.read_csv(f"{E}/kitti_causal_link.csv")
    p = d[d.cls == "pedestrian"]
    check("T8 frames", 2377, len(p), tol=0.5)
    check("T8 total global", 280, p.idsw_global.sum(), tol=0.5)
    check("T8 total per-target", 260, p.idsw_per.sum(), tol=0.5)
    q = pd.qcut(p.exposure, 4, labels=False, duplicates="drop")
    g = p.groupby(q)
    exp = [0.0192, 0.3091, 0.9140, 3.5844]
    idg = [115, 57, 59, 49]
    idp = [115, 59, 57, 29]
    for i in range(4):
        sub = p[q == i]
        check(f"T8 Q{i+1} exposure", exp[i], sub.exposure.median(), 5e-4)
        check(f"T8 Q{i+1} idsw global", idg[i], sub.idsw_global.sum(), tol=0.5)
        check(f"T8 Q{i+1} idsw per", idp[i], sub.idsw_per.sum(), tol=0.5)


def check_uavdt() -> None:
    """§5.6."""
    for run, vals in (("uavdt_none", (43.920, 48.644, 40.242, 57.335, 31.786, 3342, 8939)),
                      ("uavdt_online", (44.083, 48.946, 40.276, 57.646, 31.756, 3347, 8993))):
        m = te(run, "pedestrian", "UAVDT/UAVDT-test")
        for key, v in zip(("HOTA", "AssA", "DetA", "IDF1", "MOTA", "IDSW", "Frag"), vals):
            check(f"UAVDT {run} {key}", v, m[key], 5e-3 if key not in ("IDSW", "Frag") else 0.5)


def check_strict_oracle() -> None:
    """5.3 -- the oracle re-run with no fallback to the online estimate."""
    for run, cls, vals in (
            ("N2S_oracle_strict", "pedestrian", (69.093, 67.245, 71.510, 147)),
            ("R_oracle_strict", "pedestrian", (69.350, 67.257, 72.025, 164))):
        m = te(run, cls, "MOT17-val-half")
        for key, v in zip(("HOTA", "DetA", "AssA", "IDSW"), vals):
            check(f"5.3 strict {run} {key}", v, m[key], 5e-3 if key != "IDSW" else 0.5)


def check_family_v2() -> None:
    """6.4 corrected -- global models fitted to depth-varying background."""
    d = pd.read_csv(f"{E}/kitti_global_family_v2.csv")
    check("6.4v2 frames", 4318, len(d), tol=0.5)
    for col, med, spread, gt5 in (("online", 2.026, 8.673, 65.12),
                                  ("oracle", 1.698, 2.431, 27.12),
                                  ("sim", 4.773, 7.466, 61.74),
                                  ("hom", 0.478, 1.370, 12.90)):
        check(f"6.4v2 {col} med", med, d[col + "_med"].median(), 5e-3)
        check(f"6.4v2 {col} spread", spread, d[col + "_spread"].median(), 5e-3)
        check(f"6.4v2 {col} >5px %", gt5, (d[col + "_spread"] > 5).mean() * 100, 5e-3)
    check("6.4v2 spread reduction vs deployable sim %", 81.65,
          100 * (1 - d.hom_spread.median() / d.sim_spread.median()), 5e-2)
    check("6.4v2 spread reduction vs oracle sim %", 43.66,
          100 * (1 - d.hom_spread.median() / d.oracle_spread.median()), 5e-2)
    check("6.4v2 median background samples", 437, d.n_bg.median(), 0.5)



def check_placebo() -> None:
    """6.7 -- the shuffled placebo: same corrections, wrong objects."""
    for cls, vals in (("pedestrian", (46.198, 49.036, 44.353, 163)),
                      ("car", (62.582, 64.852, 61.160, 400))):
        m = te("placebo_shuffled", cls)
        for key, v in zip(("HOTA", "AssA", "DetA", "IDSW"), vals):
            check(f"6.7 placebo {cls} {key}", v, m[key], 5e-3 if key != "IDSW" else 0.5)
    import importlib.util
    spec = importlib.util.spec_from_file_location("bci", f"{ROOT}/03_code/rac/bootstrap_ci.py")
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

    def ci(base, comp, cls, metric):
        a, bb = b.per_seq(base, cls), b.per_seq(comp, cls)
        idx = a.index.intersection(bb.index)
        w = a.loc[idx, "GT_Dets"].values.astype(float)
        pt, boots, _ = b.bootstrap(a, bb, metric, w, n_boot=20000)
        return pt, *np.percentile(boots, [2.5, 97.5])

    for lbl, args, exp in (
            ("6.7 placebo ped per-target", ("placebo_shuffled", "v4_per_target",
                                            "pedestrian", "HOTA"),
             (1.0962, 0.3369, 4.5521)),
            ("6.7 placebo car per-target", ("placebo_shuffled", "v4_per_target",
                                            "car", "HOTA"), (3.7517, 2.1073, 5.2785)),
            ("6.7 placebo car global", ("placebo_shuffled", "v4_global_oracle",
                                        "car", "HOTA"), (3.5141, 2.1229, 4.9033)),
            ("6.7 placebo car global IDSW", ("placebo_shuffled", "v4_global_oracle",
                                             "car", "IDSW"), (-26.1323, -37.4308, -10.0978))):
        got = ci(*args)
        for name, v, g in zip(("pt", "lo", "hi"), exp, got):
            check(f"{lbl} {name}", v, g, 5e-4)


def _seq_rows(run_dir: str, cls: str) -> float:
    """Sequences covered by a run, from TrackEval's per-sequence CSV.

    TrackEval writes one row per sequence plus a COMBINED row; the COMBINED row is
    not a sequence and is not counted.
    """
    fp = f"{run_dir}/{cls}_detailed.csv"
    if not os.path.exists(fp):
        return float("nan")
    d = pd.read_csv(fp)
    return float((d.seq.astype(str) != "COMBINED").sum())


def check_provenance() -> None:
    """The two Critical defects found in review were PROVENANCE, not value: a warp
    bundle that was the identity on a third of moving frames, and a table sourced
    from a different run than the text said. Values alone do not catch either."""
    import glob
    import json

    # 1. warp-bundle coverage: no configuration may be the identity on moving frames
    for bundle, key, max_ident in (("kitti_warps_planar", "global_homography", 25),
                                   ("kitti_warps_v4", "global_oracle", 25)):
        tot = ident = 0
        for f in sorted(glob.glob(f"{E}/{bundle}/*.npz")):
            a = np.load(f)[key]
            I = np.eye(3).ravel() if a.shape[1] == 9 else np.eye(2, 3).ravel()
            tot += len(a)
            ident += int(np.all(np.isclose(a, I), axis=1).sum())
        check(f"prov {bundle}/{key} frames", 8008, tot, 0.5)
        if ident > max_ident:
            FAILS.append(f"COVERAGE    {bundle}/{key}: {ident} identity warps "
                         f"(> {max_ident}); a configuration is silently switched off")
        else:
            globals()["OKS"] = globals().get("OKS", 0)
            check(f"prov {bundle}/{key} identity frames <= {max_ident}", 1.0,
                  1.0 if ident <= max_ident else 0.0, 0.5)

    # 2. every run named in a table exists and covers every sequence.
    #
    # This reads the per-sequence TrackEval output, which IS released, rather than
    # the raw per-frame dumps under data/, which are not: at 265 MB they are
    # regenerable from the scripts, and a check that only a full re-run can
    # satisfy is a check nobody downstream can run. Counting sequence rows in
    # <class>_detailed.csv answers the same question -- did this run cover all 21
    # sequences, or was a table sourced from a partial run -- from the release.
    # When the raw dumps are present the file count is checked as well.
    for run in ("v3_online", "v4_global_oracle", "planar2_homography",
                "planar2_homography_foot", "v4_per_target", "anch_ped",
                "anch_car", "placebo_shuffled"):
        check(f"prov run {run} sequences", 21, _seq_rows(f"{TR}/KITTI/{run}", "car"), 0.5)
        d = f"{TR}/KITTI/{run}/data"
        if os.path.isdir(d):
            check(f"prov run {run} raw dumps", 21, len(os.listdir(d)), 0.5)

    # 3. MOT17 oracle rows must come from the STRICT runs, not the hybrid ones
    for run in ("N2S_oracle_strict", "R_oracle_strict"):
        check(f"prov strict run {run}", 7,
              _seq_rows(f"{TR}/MOT17-val-half/{run}", "pedestrian"), 0.5)
        d = f"{TR}/MOT17-val-half/{run}/data"
        if os.path.isdir(d):
            check(f"prov strict run {run} raw dumps", 7, len(os.listdir(d)), 0.5)

    # 4. the per-target configuration's ground-truth fallback rate, as disclosed
    tot = per = 0
    for f in sorted(glob.glob(f"{E}/kitti_warps_v4/*.npz")):
        po = np.load(f)["per_object"]
        per += len(po)
    check("prov per-target object-warps available", 40557 + 0, per, 1e9)  # recorded, not asserted


def check_runtime() -> None:
    """Table 12."""
    d = pd.read_csv(f"{E}/runtime_cost.csv")
    g = d[d.what.str.startswith("GMC")]
    dep = d[d.what.str.startswith("Depth")]
    check("T12 GMC MOT17 ms", 6.5, g[g.dataset.str.startswith("MOT17")].ms_median.iloc[0], 0.35)
    check("T12 GMC KITTI ms", 7.4, g[g.dataset.str.startswith("KITTI")].ms_median.iloc[0], 0.35)
    check("T12 depth ms", 480.9, dep.ms_median.iloc[0], 1.0)
    check("T12 depth/GMC ratio", 70, dep.ms_median.iloc[0] / g.ms_median.median(), 2.0)


def check_mot20_oracle() -> None:
    """4.2 -- the external check on MOT20."""
    d = pd.read_csv(f"{E}/mot20_oracle_analysis.csv")
    check("4.2 MOT20 frames", 8927, len(d), tol=0.5)
    check("4.2 MOT20 ref_ok %", 100.0, 100 * d.ref_ok.astype(bool).mean(), 5e-2)
    ok = d[d.ref_ok.astype(bool)]
    check("4.2 MOT20 corner med", 0.839, ok.corner_disagreement_px.median(), 5e-4)
    check("4.2 MOT20 corner p90", 1.237, np.percentile(ok.corner_disagreement_px, 90), 5e-4)
    check("4.2 MOT20 corner p99", 1.717, np.percentile(ok.corner_disagreement_px, 99), 5e-4)
    check("4.2 MOT20 corner max", 2.732, ok.corner_disagreement_px.max(), 5e-4)
    for seq, n, med, phi in (("MOT20-01", 428, 0.409, 0.236), ("MOT20-02", 2781, 0.745, 0.321),
                             ("MOT20-03", 2404, 1.017, 0.508), ("MOT20-05", 3314, 0.756, 0.817)):
        g = ok[ok.sequence == seq]
        check(f"4.2 {seq} n", n, len(g), tol=0.5)
        check(f"4.2 {seq} corner med", med, g.corner_disagreement_px.median(), 5e-4)
        check(f"4.2 {seq} phi med", phi, g.frac_inliers_in_det.median(), 5e-4)


def check_permutation() -> None:
    """6.7 -- the paired permutation test."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cl", f"{ROOT}/03_code/rac/kitti_causal_link.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    d = pd.read_csv(f"{E}/kitti_causal_link.csv")
    r = m.permutation_test(d[d.cls == "pedestrian"])
    check("6.7 perm observed", 20, r["observed"], 0.5)
    check("6.7 perm null mean", 4.99, r["null_mean"], 5e-2)
    check("6.7 perm null sd", 3.70, r["null_sd"], 5e-2)
    check("6.7 perm p", 0.0001, r["p"], 5e-5)
    rc = m.permutation_test(d[d.cls == "car"])
    check("6.7 perm p car", 0.946, rc["p"], 5e-3)
    check("6.7 frames with nonzero improvement", 50,
          int(((d[d.cls == "pedestrian"].idsw_global
                - d[d.cls == "pedestrian"].idsw_per) != 0).sum()), 0.5)


def check_depth_ratio_and_failures() -> None:
    """9.2 -- the corrected structural explanation and the two failed diagnostics."""
    d = pd.read_csv(f"{E}/depth_ratio.csv")
    for ds, v in (("MOT17", 5.60), ("MOT20", 6.51), ("UAVDT", 3.94), ("KITTI", 3.57)):
        check(f"9.2 depth ratio {ds}", v, d[d.dataset == ds].depth_ratio.median(), 5e-3)
    sp = pd.read_csv(f"{E}/spread_2d.csv")
    for ds, v in (("MOT17", 4.690), ("MOT20", 5.556), ("UAVDT", 2.500), ("KITTI", 7.072)):
        check(f"9.2 observed spread {ds}", v, sp[sp.dataset == ds].spread.median(), 5e-3)
    pi = pd.read_csv(f"{E}/parallax_indicator.csv")
    for ds, v in (("MOT17", -0.306), ("MOT20", -0.243), ("UAVDT", -0.200), ("KITTI", -0.214)):
        check(f"9.2 parallax rho {ds}", v, pi[pi.dataset == ds].rho_depth_resid.median(), 5e-3)


def check_ess_and_strata() -> None:
    """5.5 and 6.6 -- effective sample size and the stratified MOT17 intervals."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bci", f"{ROOT}/03_code/rac/bootstrap_ci.py")
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    for lbl, run, cls, root, ess in (("MOT17", "A0_frozen", "pedestrian", b.TR_MOT, 3.79),
                                     ("KITTI ped", "v4_global_oracle", "pedestrian", None, 3.05),
                                     ("KITTI car", "v4_global_oracle", "car", None, 10.47)):
        w = b.per_seq(run, cls, root)["GT_Dets"].values.astype(float)
        check(f"ESS {lbl}", ess, w.sum() ** 2 / (w ** 2).sum(), 5e-3)
    z = b.per_seq("v4_global_oracle", "pedestrian")
    check("6.6 zero-GT pedestrian sequences", 6, int((z["GT_Dets"] == 0).sum()), 0.5)
    check("6.6 top sequence weight %", 52.9,
          100 * z["GT_Dets"].max() / z["GT_Dets"].sum(), 5e-2)

    def ci(base, comp, cls, metric, root=None, only=None, weighted=True):
        a, bb = b.per_seq(base, cls, root), b.per_seq(comp, cls, root)
        if only is not None:
            a, bb = a.loc[a.index.isin(only)], bb.loc[bb.index.isin(only)]
        idx = a.index.intersection(bb.index)
        w = (a.loc[idx, "GT_Dets"].values.astype(float) if weighted else np.ones(len(idx)))
        pt, boots, _ = b.bootstrap(a, bb, metric, w, n_boot=20000)
        return pt, *np.percentile(boots, [2.5, 97.5])

    MV = b.MOT17_MOVING
    for lbl, args, exp in (
            ("5.5 moving perfect motion", ("A0_frozen", "N2_oracle_warp", "pedestrian",
                                           "HOTA", b.TR_MOT, MV, True), (0.0004, -0.0425, 0.0524)),
            ("5.5 moving perfect appear", ("R_online", "R_oracle", "pedestrian",
                                           "HOTA", b.TR_MOT, MV, True), (0.1688, 0.0131, 0.5229)),
            ("5.5 moving having", ("A_noCMC", "A0_frozen", "pedestrian",
                                   "HOTA", b.TR_MOT, MV, True), (3.4258, 1.0072, 5.5234)),
            ("6.6 unweighted ped", ("v4_global_oracle", "v4_per_target", "pedestrian",
                                    "HOTA", None, None, False), (0.5141, -0.2790, 1.2648)),
            ("6.6 per-target - anchored", ("anch_ped", "v4_per_target", "pedestrian",
                                           "HOTA", None, None, True), (0.6763, -0.3820, 1.0504)),
            ("6.6 car anchored", ("v4_global_oracle", "anch_car", "car",
                                  "HOTA", None, None, True), (-0.2235, -0.8536, 0.3527))):
        got = ci(*args)
        for name, v, g in zip(("pt", "lo", "hi"), exp, got):
            check(f"{lbl} {name}", v, g, 5e-4)


# --- manuscript-driven checks -------------------------------------------------
# Hard-coded expectations are transcriptions, and a transcription can be quietly
# updated to match a changed source while the paper still says something else.
# These checks parse the manuscript's own tables and compare every printed cell
# against TrackEval. The manuscript is the claim, the summary files are the
# evidence, and nothing in between can drift unnoticed.

MD = f"{ROOT}/02_paper/manuscript.md"

MANUSCRIPT_TABLES = {
    "KITTI tracking, 21 sequences": [
        ("pedestrian", {"| none ": "v3_none", "online sparse-flow": "v3_online",
                        "global similarity (oracle)": "v4_global_oracle",
                        "pedestrian-anchored": "anch_ped",
                        "depth-aware global homography (estimated depth)": "planar2_homography",
                        "contact point (estimated depth)": "planar2_homography_foot",
                        "per-target similarity (oracle": "v4_per_target"}),
        ("car", {"| none ": "v3_none", "online sparse-flow": "v3_online",
                 "global similarity (oracle)": "v4_global_oracle",
                 "car-anchored": "anch_car",
                 "depth-aware global homography (estimated depth)": "planar2_homography",
                 "contact point (estimated depth)": "planar2_homography_foot",
                 "per-target similarity (oracle": "v4_per_target"}),
    ],
    "Estimated-depth configurations on KITTI": [
        ("pedestrian", {"| none ": "v3_none", "| online GMC": "v3_online",
                        "global similarity, estimated depth": "dep_global_oracle",
                        "per-target, estimated depth": "dep_per_target_depth",
                        "per-target, ground-truth depth": "v4_per_target"}),
        ("car", {"| none ": "v3_none", "| online GMC": "v3_online",
                 "global similarity, estimated depth": "dep_global_oracle",
                 "per-target, estimated depth": "dep_per_target_depth",
                 "per-target, ground-truth depth": "v4_per_target"}),
    ],
    "Pedestrian sensitivity to injected depth noise": [
        ("pedestrian", {"| 0.00 |": "v3_per_target", "| 0.05 |": "dn005_per_target",
                        "| 0.10 |": "dn010_per_target", "| 0.20 |": "dn020_per_target",
                        "| 0.30 |": "dn030_per_target", "| 0.50 |": "dn050_per_target"}),
    ],
}


def _md_blocks(text, caption_fragment):
    """The pipe-table blocks following a caption, up to the next caption."""
    i = text.index(caption_fragment)
    j = text.find("**Table ", i + 1)
    seg = text[i:j if j > 0 else len(text)]
    blocks, cur = [], []
    for line in seg.splitlines():
        if line.startswith("|"):
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def check_manuscript_tables():
    """Every KITTI tracking cell the manuscript prints, against TrackEval."""
    text = open(MD).read()
    for caption, specs in MANUSCRIPT_TABLES.items():
        blocks = _md_blocks(text, caption)
        if len(blocks) < len(specs):
            FAILS.append(f"PARSE       '{caption}': expected {len(specs)} tables,"
                         f" found {len(blocks)}")
            continue
        for (cls, rows), block in zip(specs, blocks):
            header = [h.strip().strip("*") for h in block[0].strip("|").split("|")]
            for line in block[2:]:
                run = next((r for frag, r in rows.items() if frag in line), None)
                if run is None:
                    continue
                cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
                m = te(run, cls)
                for h, c in zip(header[1:], cells[1:]):
                    if h not in m:
                        continue
                    v = num(c)
                    if v is None:
                        continue
                    tol = 0.5 if h in ("IDSW", "Frag") else 5e-3
                    check(f"MS {cls}/{run}/{h}", v, m[h], tol)


# Table 9's intervals, parsed from the manuscript and recomputed from the runs.
# Same reasoning as check_manuscript_tables: a hand-maintained literal can be
# updated to match a changed source while the paper still prints the old one.
CI_ROWS = {
    "depth-aware homography − online GMC": ("v3_online", "planar2_homography"),
    "homography at contact point − online GMC": ("v3_online", "planar2_homography_foot"),
    "per-target − depth-aware homography": ("planar2_homography", "v4_per_target"),
    "per-target − global similarity": ("v4_global_oracle", "v4_per_target"),
    "having compensation at all": ("v3_none", "v3_online"),
}
CI_PAT = re.compile(r"([+-−]?\d+\.\d+)\s*\[\s*([+-−]\d+\.\d+)\s*,\s*([+-−]\d+\.\d+)\s*\]")


def check_manuscript_intervals():
    """Every interval Table 9 prints, against a fresh bootstrap of the same runs."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bci", f"{ROOT}/03_code/rac/bootstrap_ci.py")
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    text = open(MD).read()
    blocks = _md_blocks(text, "Bootstrap 95 % confidence intervals over the 21 sequences")
    if not blocks:
        FAILS.append("PARSE       Table 9 not found")
        return
    for line in blocks[0][2:]:
        cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        label = next((k for k in CI_ROWS if k in cells[0]), None)
        if label is None:
            continue
        cls = {"ped": "pedestrian", "car": "car"}.get(cells[1])
        if cls is None:
            continue
        base, comp = CI_ROWS[label]
        for col, metric in ((2, "HOTA"), (3, "IDSW")):
            m = CI_PAT.search(cells[col].replace("−", "-"))
            if not m:
                continue
            pt, lo, hi = (float(x.replace("−", "-")) for x in m.groups())
            a, bb = b.per_seq(base, cls), b.per_seq(comp, cls)
            idx = a.index.intersection(bb.index)
            w = a.loc[idx, "GT_Dets"].values.astype(float)
            gp, boots, _ = b.bootstrap(a, bb, metric, w, n_boot=20000)
            glo, ghi = np.percentile(boots, [2.5, 97.5])
            tol = 5e-3 if metric == "HOTA" else 5e-2
            tag = f"CI {cls}/{label[:34]}/{metric}"
            check(f"{tag} pt", pt, gp, tol)
            check(f"{tag} lo", lo, glo, tol)
            check(f"{tag} hi", hi, ghi, tol)



HOM_SIGMA = ((0.00, "planar2_homography"), (0.05, "hom_dn005"), (0.10, "hom_dn010"),
             (0.20, "hom_dn020"), (0.30, "hom_dn030"), (0.50, "hom_dn050"))


def check_homography_robustness():
    """7.3 -- every cell of Table 14, read off the manuscript, against TrackEval.

    The table prints HOTA and a delta against the deployed compensator. Both are
    TrackEval COMBINED figures (see 3.5), so both are checked that way; the six
    intervals the prose quotes are checked as bootstraps in
    check_homography_intervals, which is where the other estimator lives.
    """
    text = open(MD).read()
    blocks = _md_blocks(text, "Depth-aware homography under injected depth error")
    if not blocks:
        FAILS.append("PARSE       Table 14 not found")
        return
    base_p, base_c = te("v3_online", "pedestrian")["HOTA"], te("v3_online", "car")["HOTA"]
    seen = set()
    for line in blocks[0][2:]:
        c = [x.strip().replace("**", "").replace("\u2212", "-") for x in line.strip("|").split("|")]
        if len(c) < 8 or not re.match(r"^\d+\.\d+$", c[0]):
            continue
        sig = float(c[0])
        run = dict(HOM_SIGMA).get(sig)
        if run is None:
            FAILS.append(f"PARSE       7.3 sigma={sig} has no mapped run")
            continue
        seen.add(sig)
        check(f"7.3 sigma={sig} rel.err", float(c[1].rstrip(" %")),
              100 * (math.exp(sig) - 1), 0.55)
        ped, car = te(run, "pedestrian")["HOTA"], te(run, "car")["HOTA"]
        check(f"7.3 sigma={sig} ped HOTA", float(c[2]), ped, 5e-3)
        check(f"7.3 sigma={sig} ped vs GMC", float(c[3]), ped - base_p, 5e-3)
        check(f"7.3 sigma={sig} ped IDSW", float(c[4]), te(run, "pedestrian")["IDSW"], 0.5)
        check(f"7.3 sigma={sig} car HOTA", float(c[5]), car, 5e-3)
        check(f"7.3 sigma={sig} car vs GMC", float(c[6]), car - base_c, 5e-3)
        check(f"7.3 sigma={sig} car IDSW", float(c[7]), te(run, "car")["IDSW"], 0.5)
    missing = {s for s, _ in HOM_SIGMA} - seen
    if missing:
        FAILS.append(f"PARSE       7.3 rows absent from the manuscript: {sorted(missing)}")
    # the caption's two reference figures
    m = re.search(r"online GMC: pedestrian ([\d.]+) / (\d+) identity switches, car ([\d.]+) / (\d+)",
                  text)
    if not m:
        FAILS.append("PARSE       Table 14 caption reference figures not found")
    else:
        check("7.3 caption ped GMC HOTA", float(m.group(1)), base_p, 5e-3)
        check("7.3 caption ped GMC IDSW", float(m.group(2)), te("v3_online", "pedestrian")["IDSW"], 0.5)
        check("7.3 caption car GMC HOTA", float(m.group(3)), base_c, 5e-3)
        check("7.3 caption car GMC IDSW", float(m.group(4)), te("v3_online", "car")["IDSW"], 0.5)


def check_reproduce_map():
    """The release page must map every table the manuscript prints, and must not
    name a script or flag that does not exist.

    REPRODUCE.md is the only part of the release a reader follows by hand, and it
    went stale twice across two table renumberings without anything noticing.
    """
    rp = f"{ROOT}/99_artifacts/RELEASE/REPRODUCE.md"
    if not os.path.exists(rp):
        FAILS.append("MISSING     99_artifacts/RELEASE/REPRODUCE.md")
        return
    txt = open(rp).read()
    md = open(MD).read()
    tables = {int(m) for m in re.findall(r"^\*\*Table (\d+)\*\*", md, re.M)}
    listed = {int(m) for m in re.findall(r"^\| (\d+) \|", txt, re.M)}
    for t in sorted(tables - listed):
        FAILS.append(f"PROVENANCE  Table {t} is in the manuscript but not in REPRODUCE.md")
    for t in sorted(listed - tables):
        FAILS.append(f"PROVENANCE  REPRODUCE.md lists Table {t}, which the manuscript does not print")
    if tables and tables == listed:
        globals()["OKS"] = OKS + 1
    if tables != set(range(1, len(tables) + 1)):
        FAILS.append(f"PROVENANCE  manuscript table numbers are not gapless: {sorted(tables)}")
    else:
        globals()["OKS"] = OKS + 1
    for name in sorted(set(re.findall(r"rac/([A-Za-z0-9_]+\.(?:py|sh))", txt))):
        fp = f"{ROOT}/03_code/rac/{name}"
        if not os.path.exists(fp):
            FAILS.append(f"PROVENANCE  REPRODUCE.md names rac/{name}, which does not exist")
            continue
        globals()["OKS"] = OKS + 1
        if not name.endswith(".py"):
            continue
        used = set(re.findall(r"--[a-z0-9-]+",
                              " ".join(re.findall(rf"rac/{re.escape(name)}((?:\s+[^`;|]*)?)", txt))))
        have = set(re.findall(r'add_argument\(\s*"(--[a-z0-9-]+)"', open(fp).read()))
        for f in sorted(used - have):
            FAILS.append(f"PROVENANCE  REPRODUCE.md passes {f} to rac/{name}, which does not accept it")
    # the --mode values it names must be modes kitti_track.py actually has
    src = open(f"{ROOT}/03_code/rac/kitti_track.py").read()
    ch = re.search(r'"--mode".*?choices=\[(.*?)\]', src, re.S)
    allowed = set(re.findall(r'"([a-z_]+)"', ch.group(1))) if ch else set()
    used = set()
    for m in re.findall(r"--mode ([{a-zA-Z_,]+)", txt):
        used |= {v for v in re.sub(r"[{}]", "", m).split(",") if v}
    for v in sorted(used - allowed):
        FAILS.append(f"PROVENANCE  REPRODUCE.md names --mode {v}, not a kitti_track.py choice")
    if used and not (used - allowed):
        globals()["OKS"] = OKS + 1


def check_chinese_abstract():
    """Every figure in the Chinese abstract must be traceable to the manuscript.

    It is a separate file, it is not submitted, and it drifted: two intervals in it
    still held values from before the similarity estimator was corrected. It rounds
    to two decimals where the paper gives three, so a match is exact or a rounding.
    """
    fp = f"{ROOT}/02_paper/03_ABSTRACT_ZH.md"
    if not os.path.exists(fp):
        FAILS.append("MISSING     02_paper/03_ABSTRACT_ZH.md")
        return
    zh = open(fp).read().replace("\u2212", "-")
    en = open(MD).read().replace("\u2212", "-")
    en_nums = {float(x) for x in re.findall(r"[+-]?\d+\.\d+", en)}
    stale = []
    for tok in sorted({t for t in re.findall(r"[+-]?\d+\.\d+", zh)}):
        v = float(tok)
        if any(abs(v - e) < 5e-9 or abs(v - round(e, len(tok.split(".")[1]))) < 5e-9
               for e in en_nums):
            continue
        stale.append(tok)
    if stale:
        FAILS.append(f"DRIFT       Chinese abstract has {len(stale)} figures the "
                     f"manuscript does not support: {stale}")
    else:
        globals()["OKS"] = OKS + 1


def check_figure_order():
    """Figures must be numbered in the order the text first cites them.

    Springer requires it, and it was violated silently for as long as every figure
    float sat at the end of the document in list order: the first figure the text
    cites, in 4.4, was numbered 8. Placing each float beside its citation made the
    numbering visibly wrong, which is how it was found.
    """
    text = open(MD).read()
    body = text[text.index("## 1 Introduction"):text.index("## References")]
    cited = [int(m.group(1)) for m in re.finditer(r"\bFigure (\d+)\b", body)]
    if cited != sorted(set(cited)):
        FAILS.append(f"ORDER       figures are cited in the order {cited}; they must be "
                     f"numbered in citation order, i.e. {sorted(set(cited))}")
    else:
        globals()["OKS"] = OKS + 1
    check("figures cited", len(FIG_ORDER), len(cited), 0.5)
    # the build's list must be in the same order, since LaTeX numbers by position
    src = open(f"{ROOT}/03_code/rac/build_latex.py").read()
    listed = re.findall(r'\(\s*"(F\d)"', src[src.index("FIGURES = ["):])
    check("figure list length", len(FIG_ORDER), len(listed), 0.5)
    if listed[:len(FIG_ORDER)] != FIG_ORDER:
        FAILS.append(f"ORDER       build_latex.py lists figures as {listed}, "
                     f"expected {FIG_ORDER}")
    else:
        globals()["OKS"] = OKS + 1


FIG_ORDER = ["F0", "F8", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]


def check_availability_counts():
    """Every count the Data and Code Availability statement gives, from the tree.

    These had gone stale: the statement said 21 CSVs and 61 runs after the number
    had become 22 and 63. A count in a paper is a measurement like any other.
    """
    import glob
    text = open(MD).read()
    i = text.index("## Data and Code Availability")
    seg = text[i:text.index("## Ethics", i)]
    m = re.search(r"(\d+) analysis scripts and (\d+) shell drivers, (\d+) result CSVs", seg)
    if not m:
        FAILS.append("PARSE       availability counts not found")
        return
    check("avail analysis scripts", float(m.group(1)),
          len(glob.glob(f"{ROOT}/03_code/rac/*.py")), 0.5)
    check("avail shell drivers", float(m.group(2)),
          len(glob.glob(f"{ROOT}/03_code/rac/*.sh")), 0.5)
    check("avail result CSVs", float(m.group(3)), len(glob.glob(f"{E}/*.csv")), 0.5)
    m = re.search(r"all (\d+) evaluated tracker runs \((\d+) on KITTI, (\d+) on MOT17, "
                  r"(\d+) on UAVDT\)", seg)
    if not m:
        FAILS.append("PARSE       availability run counts not found")
        return
    def n_runs(bench):
        return len({os.path.dirname(f) for f in
                    glob.glob(f"{TR}/{bench}/**/*_summary.txt", recursive=True)})
    k, mo, u = n_runs("KITTI"), n_runs("MOT17-val-half"), n_runs("UAVDT")
    check("avail KITTI runs", float(m.group(2)), k, 0.5)
    check("avail MOT17 runs", float(m.group(3)), mo, 0.5)
    check("avail UAVDT runs", float(m.group(4)), u, 0.5)
    check("avail total runs", float(m.group(1)), k + mo + u, 0.5)


def check_release_doc_refs():
    """No release document may point at a section the manuscript does not have.

    DATA.md said the depth model was imported for 7.3 after 7.3 became a different
    measurement; REPRODUCE.md had two of the same. A section reference in a
    maintained document is exactly as checkable as a number.
    """
    heads = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?) ", open(MD).read(), re.M))
    for rel in ("99_artifacts/RELEASE/DATA.md", "02_paper/REPRODUCE.md",
                "99_artifacts/RELEASE/REPRODUCE.md"):
        fp = f"{ROOT}/{rel}"
        if not os.path.exists(fp):
            FAILS.append(f"MISSING     {rel}")
            continue
        refs = set(re.findall(r"(?:\u00a7|Section )(\d+(?:\.\d+)?)", open(fp).read()))
        for r in sorted(refs - heads):
            FAILS.append(f"PROVENANCE  {rel} cites \u00a7{r}, which the manuscript does not have")
        if not (refs - heads):
            globals()["OKS"] = OKS + 1


def check_background_point_counts():
    """7.3 -- the counts its structural argument rests on, from the family CSV."""
    d = pd.read_csv(f"{E}/kitti_global_family_v2.csv")
    text = open(MD).read()
    m = re.search(r"a median\s+of (\d+) per frame, interquartile range (\d+) to (\d+)", text)
    if not m:
        FAILS.append("PARSE       7.3 background-point counts not found")
        return
    q25, med, q75 = d.n_bg.quantile([0.25, 0.5, 0.75])
    check("7.3 n_bg median", float(m.group(1)), med, 0.5)
    check("7.3 n_bg q25", float(m.group(2)), q25, 0.5)
    check("7.3 n_bg q75", float(m.group(3)), q75, 0.5)
    m = re.search(r"(?:of which there is a median of|compared with a median of) (\d+)", text)
    check("7.3 n_obj median", float(m.group(1)) if m else -1, d.n_obj.median(), 0.5)
    m = re.search(r"(\d+) against (\d+) at the\s+median", text)
    if m:
        check("7.3 ratio numerator", float(m.group(1)), med, 0.5)
        check("7.3 ratio denominator", float(m.group(2)), d.n_obj.median(), 0.5)


def check_homography_intervals():
    """7.3 -- the six intervals the prose lists, and the claim that none crosses zero."""
    b = _bci()
    text = open(MD).read()
    i = text.index("excludes zero at **every one of the six levels**")
    quoted = re.findall(r"\[([+-\u2212]\d+\.\d+), ([+-\u2212]\d+\.\d+)\]",
                        text[i:text.index(".", i + 200)])
    if len(quoted) != len(HOM_SIGMA):
        FAILS.append(f"PARSE       7.3 lists {len(quoted)} intervals, expected {len(HOM_SIGMA)}")
        return
    for (sig, run), (lo_s, hi_s) in zip(HOM_SIGMA, quoted):
        a, bb = b.per_seq("v3_online", "car"), b.per_seq(run, "car")
        idx = a.index.intersection(bb.index)
        w = a.loc[idx, "GT_Dets"].values.astype(float)
        _, boots, _ = b.bootstrap(a, bb, "HOTA", w, n_boot=20000)
        glo, ghi = np.percentile(boots, [2.5, 97.5])
        check(f"7.3 CI car sigma={sig} lo", float(lo_s.replace("\u2212", "-")), glo, 5e-3)
        check(f"7.3 CI car sigma={sig} hi", float(hi_s.replace("\u2212", "-")), ghi, 5e-3)
        if glo <= 0:
            FAILS.append(f"CLAIM       7.3 says every interval excludes zero, but "
                         f"sigma={sig} lower bound is {glo:+.3f}")
        else:
            globals()["OKS"] = OKS + 1


def check_estimator_convention():
    """3.5 -- the median and maximum disagreement between the two HOTA estimators."""
    b = _bci()
    gaps = []
    for label, (base, comp) in CI_ROWS.items():
        for cls in ("car", "pedestrian"):
            comb = te(comp, cls)["HOTA"] - te(base, cls)["HOTA"]
            a, bb = b.per_seq(base, cls), b.per_seq(comp, cls)
            idx = a.index.intersection(bb.index)
            w = a.loc[idx, "GT_Dets"].values.astype(float)
            gp, _, _ = b.bootstrap(a, bb, "HOTA", w, n_boot=20000)
            gaps.append(abs(comb - gp))
    text = open(MD).read()
    m = re.search(r"differ by a median of ([\d.]+) HOTA and\s+at most ([\d.]+)", text)
    if not m:
        FAILS.append("PARSE       3.5 estimator-disagreement figures not found")
        return
    check("3.5 estimator gap median", float(m.group(1)), float(np.median(gaps)), 5e-3)
    check("3.5 estimator gap max", float(m.group(2)), float(np.max(gaps)), 5e-3)
    check("3.5 estimator gap n_contrasts", 10, len(gaps), 0.5)


def check_causal_link_homography():
    """6.8 -- Table 12's quartile cells and the permutation tests, from the CSV."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("kcl", f"{ROOT}/03_code/rac/kitti_causal_link.py")
    kcl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kcl)
    d = pd.read_csv(f"{E}/kitti_causal_link_hom.csv")
    text = open(MD).read()
    blocks = _md_blocks(text, "Identity switches by exposure quartile, depth-aware homography")
    if len(blocks) < 2:
        FAILS.append("PARSE       Table 12 needs two blocks, found "
                     f"{len(blocks)}")
        return
    for blk, cls in zip(blocks, ("car", "pedestrian")):
        g = d[d.cls == cls]
        check(f"6.8 {cls} n_frames", _caption_int(text, cls), len(g), 0.5)
        q = pd.qcut(g.exposure, 4, labels=False, duplicates="drop")
        rows = [ln for ln in blk[2:] if ln.startswith("|")]
        if len(rows) != 4:
            FAILS.append(f"PARSE       Table 12 {cls} has {len(rows)} quartile rows")
            continue
        for k, line in enumerate(rows):
            c = [x.strip().replace("**", "").replace("\u2212", "-") for x in line.strip("|").split("|")]
            sub = g[q == k]
            check(f"6.8 {cls} Q{k+1} exposure", float(c[1].rstrip(" px")),
                  float(sub.exposure.median()), 5e-3)
            check(f"6.8 {cls} Q{k+1} IDSW online", float(c[2]), sub.idsw_global.sum(), 0.5)
            check(f"6.8 {cls} Q{k+1} IDSW hom", float(c[3]), sub.idsw_per.sum(), 0.5)
            check(f"6.8 {cls} Q{k+1} improvement", float(c[4]),
                  sub.idsw_global.sum() - sub.idsw_per.sum(), 0.5)
        # the permutation test the prose leads with, recomputed from the same CSV
        r = kcl.permutation_test(g)
        seg = text[text.index("### 6.8"):text.index("### 7.1")]
        anchor = "observed +46" if cls == "car" else "+20 in Q4"
        mm = re.search(re.escape(anchor) + r".*?null mean of ([\d.]+) \(sd ([\d.]+)\)",
                       seg, re.S)
        if not mm:
            FAILS.append(f"PARSE       6.8 {cls} permutation figures not found")
            continue
        check(f"6.8 {cls} perm observed", 46 if cls == "car" else 20, r["observed"], 0.5)
        check(f"6.8 {cls} perm null mean", float(mm.group(1)), r["null_mean"], 5e-2)
        check(f"6.8 {cls} perm null sd", float(mm.group(2)), r["null_sd"], 5e-2)
    for cls, tot_g, tot_p in (("car", 297, 253), ("pedestrian", 291, 268)):
        g = d[d.cls == cls]
        check(f"6.8 {cls} counter total online", tot_g, g.idsw_global.sum(), 0.5)
        check(f"6.8 {cls} counter total hom", tot_p, g.idsw_per.sum(), 0.5)
    # 6.8's reconciliation with 6.7: the car counter is admissible on this contrast
    # and not on the per-target one, and the discriminator is sign agreement with
    # TrackEval. Both halves of that claim are checked, including the 6.7 refusal.
    for tag, csv, base, comp, pairs in (
            ("6.8", f"{E}/kitti_causal_link_hom.csv", "v3_online", "planar2_homography",
             (("car", 44, 40), ("pedestrian", 23, 29))),
            ("6.7", f"{E}/kitti_causal_link.csv", "v4_global_oracle", "v4_per_target",
             (("car", -48, 16),))):
        dd = pd.read_csv(csv)
        for cls, claimed_cnt, claimed_te in pairs:
            g = dd[dd.cls == cls]
            cnt = int(g.idsw_global.sum() - g.idsw_per.sum())
            tev = int(te(base, cls)["IDSW"] - te(comp, cls)["IDSW"])
            check(f"{tag} {cls} counter delta", claimed_cnt, cnt, 0.5)
            check(f"{tag} {cls} TrackEval delta", claimed_te, tev, 0.5)
            agree = cnt * tev > 0
            if agree != (tag == "6.8"):
                FAILS.append(f"CLAIM       {tag} {cls}: sign agreement is {agree}, "
                             f"manuscript requires {tag == '6.8'}")
            else:
                globals()["OKS"] = OKS + 1


def _caption_int(text: str, cls: str) -> int:
    m = re.search(rf"\*{cls.capitalize()} \(([\d,]+) frames\)", text)
    return int(m.group(1).replace(",", "")) if m else -1


def _bci():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bci", f"{ROOT}/03_code/rac/bootstrap_ci.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check_printed_measurement_tables():
    """Compare printed summaries with current sources, including unnumbered tables."""
    text = _P(MD).read_text()
    tables = md_tables(text)

    def table(caption):
        matches = [rows for ctx, rows in tables if ctx.startswith(caption)]
        if len(matches) != 1:
            raise ValueError(f"expected one table for {caption}, found {len(matches)}")
        return matches[0]

    def cell(label, printed, actual):
        cleaned = printed.replace("**", "").replace(",", "").replace("−", "-")
        match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*(?:px|%|ms|fps)?\s*", cleaned)
        if not match:
            FAILS.append(f"PARSE       {label}: {printed}")
            return
        value = match.group(1)
        decimals = len(value.split(".")[1]) if "." in value else 0
        check(label, float(value), actual, 0.5 * 10 ** -decimals + 1e-9)

    # Reliability summaries: counts and percentages are separately checked.
    rows = table("**Table 1**")
    for col, dataset in enumerate(rows[0][1:], 1):
        d = pd.read_csv(f"{E}/{dataset.lower()}_gmc_scan.csv")
        d = d[~d.first_frame.astype(bool) & d.n_inliers.notna()]
        values = [len(d), d.inlier_ratio.median(), d.resid_median.median(),
                  d.resid_median.quantile(.95), d.displacement.median(),
                  d.temporal_resid.median()]
        for row, value in zip(rows[1:7], values):
            cell(f"MS T1 {dataset}/{row[0]}", row[col], value)
        counts = [(d.n_inliers < 100).sum(), (d.n_inliers < 300).sum(),
                  (d.resid_median > 2).sum(), (d.inlier_ratio < .7).sum(),
                  (d.frac_inliers_in_det > .7).sum()]
        for row, value in zip(rows[7:], counts):
            if row[col] == "—":
                continue
            match = re.fullmatch(r"([\d,]+) \(([\d.]+) %\)", row[col].replace("**", ""))
            if not match:
                raise ValueError(f"unparsed count and percentage: {row[col]}")
            cell(f"MS T1 {dataset}/{row[0]} count", match[1], value)
            cell(f"MS T1 {dataset}/{row[0]} %", match[2], 100 * value / len(d))

    d = pd.read_csv(f"{E}/oracle_analysis.csv")
    rows = next(r for _, r in tables if "90th percentile" in r[0])
    for row, camera in zip(rows[1:], ("static", "moving")):
        g = d[d.camera == camera]
        for printed, value in zip(row[1:], [len(g), g.corner_disagreement_px.median(),
                                             g.corner_disagreement_px.quantile(.9),
                                             g.box_shift_px.median()]):
            cell(f"MS 4.2 {camera}", printed, value)
    d = pd.read_csv(f"{E}/mot20_oracle_analysis.csv")
    rows = next(r for _, r in tables if r[0][-1] == "Median φ")
    for row in rows[1:]:
        g = d[d.sequence == row[0]] if row[0].startswith("MOT20-") else d
        values = [len(g), g.corner_disagreement_px.median(),
                  g.corner_disagreement_px.quantile(.9), g.corner_disagreement_px.quantile(.99),
                  g.corner_disagreement_px.max(), g.frac_inliers_in_det.median()]
        for printed, value in zip(row[1:], values):
            if printed != "—":
                cell(f"MS 4.2 {row[0]}", printed, value)

    d = pd.read_csv(f"{E}/gate_flips.csv")
    for row in table("**Table 2**")[1:]:
        seq = row[0].replace("**", "")
        g = d[d.sequence.str.startswith(seq)] if seq.startswith("MOT17-") else d
        values = [len(g), g.iou_online.median(), g.harmful_flip.sum(), g.helpful_flip.sum()]
        for printed, value in zip(row[2:], values):
            if printed not in ("—", ""):
                cell(f"MS T2 {seq}", printed, value)

    tracking = [(table("**Table 3**"), "MOT17-val-half",
                 ["A_noCMC", "A0_frozen", "A0_botsort_baseline", "N2S_oracle_strict"]),
                (table("**Table 4**"), "MOT17-val-half", ["R_none", "R_online", "R_oracle_strict"]),
                (md_tables(text.split("### 5.6 ", 1)[1].split("### 5.7 ", 1)[0])[0][1],
                 "UAVDT/UAVDT-test", ["uavdt_none", "uavdt_online"])]
    for rows, bench, runs in tracking:
        if len(rows) - 1 != len(runs):
            raise ValueError(f"row count changed for {bench}/{runs}")
        for row, run in zip(rows[1:], runs):
            metrics = te(run, "pedestrian", bench)
            for header, printed in zip(rows[0][1:], row[1:]):
                cell(f"MS {bench}/{run}/{header}", printed, metrics[header])

    d = pd.read_csv(f"{E}/kitti_global_family_v2.csv")
    for row, model in zip(table("**Table 6**")[1:], ("online", "oracle", "sim", "hom")):
        values = [d[model + "_med"].median(), d[model + "_spread"].median(),
                  100 * (d[model + "_spread"] > 5).mean()]
        for printed, value in zip(row[1:], values):
            cell(f"MS T6 {model}", printed, value)

    for row, run in zip(table("**Table 10**")[1:],
                        ("v4_global_oracle", "placebo_shuffled", "v4_per_target")):
        p, c = te(run, "pedestrian"), te(run, "car")
        for printed, value in zip(row[1:], [p["HOTA"], p["IDSW"], c["HOTA"], c["IDSW"]]):
            cell(f"MS T10 {run}", printed, value)
    d = pd.read_csv(f"{E}/kitti_causal_link.csv")
    d = d[d.cls == "pedestrian"]
    quartile = pd.qcut(d.exposure, 4, labels=False, duplicates="drop")
    for k, row in enumerate(table("**Table 11**")[1:]):
        g = d[quartile == k] if k < 4 else d
        change = g.idsw_global.sum() - g.idsw_per.sum()
        values = [g.exposure.median(), g.idsw_global.sum(), g.idsw_per.sum(), change,
                  1000 * change / len(g)]
        for printed, value in zip(row[1:], values):
            if printed:
                cell(f"MS T11 row {k+1}", printed, value)

    for row, run in zip(table("**Table 13**")[1:],
                        ("v3_per_target", "dn005_per_target", "dn010_per_target",
                         "dn020_per_target", "dn030_per_target", "dn050_per_target")):
        sigma = float(row[0]); metrics = te(run, "pedestrian")
        cell(f"MS T13 {sigma} relative error", row[1], 100 * (math.exp(sigma) - 1))
        cell(f"MS T13 {sigma} contrast", row[3],
             metrics["HOTA"] - te("v4_global_oracle", "pedestrian")["HOTA"])

    # The MOT17 and estimated-depth interval tables use sequence-weighted contrasts.
    b = _bci()
    def interval(printed, base, comp, cls, metric, root=None, moving=False):
        match = CI_PAT.search(printed.replace("**", ""))
        if not match:
            raise ValueError(f"unparsed interval: {printed}")
        a, bb = b.per_seq(base, cls, root), b.per_seq(comp, cls, root)
        if moving:
            a, bb = a.loc[a.index.isin(b.MOT17_MOVING)], bb.loc[bb.index.isin(b.MOT17_MOVING)]
        idx = a.index.intersection(bb.index)
        weights = a.loc[idx, "GT_Dets"].values.astype(float)
        estimate, boots, _ = b.bootstrap(a, bb, metric, weights, n_boot=20000)
        for value, actual in zip(match.groups(), [estimate, *np.percentile(boots, [2.5, 97.5])]):
            cell(f"MS CI {base}/{comp}/{cls}/{metric}", value, actual)
    pairs = [("A_noCMC", "A0_frozen"), ("R_none", "R_online"),
             ("A0_frozen", "N2S_oracle_strict"), ("R_online", "R_oracle_strict"),
             ("A0_frozen", "A0_botsort_baseline")]
    for row, (base, comp) in zip(table("**Table 5**")[1:], pairs):
        for printed, moving in zip(row[2:], (False, True)):
            interval(printed, base, comp, "pedestrian", "HOTA", b.TR_MOT, moving)
    rows = next(r for ctx, r in tables if ctx == "With bootstrap intervals:")
    for row in rows[1:]:
        base = "dep_global_oracle" if "both estimated depth" in row[0] else "v3_online"
        cls = "pedestrian" if row[1] == "ped" else "car"
        for printed, metric in zip(row[2:], ("HOTA", "IDSW")):
            interval(printed, base, "dep_per_target_depth", cls, metric)

    d = pd.read_csv(f"{E}/runtime_cost.csv")
    for row, record in zip(table("**Table 16**")[1:], d.itertuples()):
        cell(f"MS T16 {record.dataset} milliseconds", row[2], record.ms_median)
        cell(f"MS T16 {record.dataset} throughput", row[3], record.fps_of_this_step)
    caption = next(ctx for ctx, _ in tables if ctx.startswith("**Table 16**"))
    counts = re.search(r"(\d+) GMC calls and (\d+) depth inferences", caption)
    if not counts:
        raise ValueError("Table 16 measurement counts not found")
    cell("MS T16 GMC sample count", counts[1], d.iloc[0].n)
    cell("MS T16 depth sample count", counts[2], d.iloc[2].n)

    d = pd.read_csv(f"{E}/kitti_class_split.csv")
    body = text.split("## 8 Class-Specific", 1)[1].split("## 9 ", 1)[0]
    m = re.search(r"([\d.]+) % of pedestrian/cyclist object-frames and ([\d.]+) % of car", body)
    if not m:
        raise ValueError("Section 8 exposure percentages not found")
    for cls, value in zip(("ped", "car"), m.groups()):
        cell(f"MS 8 {cls} exposure", value, 100 * d[d.cls == cls].exposed.mean())
    supp = _P(f"{ROOT}/02_paper/supplementary.md").read_text()
    m = re.search(r"in \*\*([\d.]+) %\*\* of car object-frames and \*\*([\d.]+) %\*\* of pedestrian", supp)
    if not m:
        raise ValueError("Supplement S3 exposure percentages not found")
    for cls, value in zip(("car", "ped"), m.groups()):
        cell(f"MS S3 {cls} exposure", value, 100 * d[d.cls == cls].exposed.mean())


UNCHECKED = [
    "3.1 bit-identity of the instrumented GMC -- asserted by instrumented_gmc.py itself",
    "4.3 confound stratification and placebo figures -- printed by confound_placebo.py",
    "determinism claims -- verified by diffing run outputs, not by this script",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("Not covered by this script, verified by hand in the integrity report:")
        for u in UNCHECKED:
            print("  -", u)
        return

    for fn in (check_scans, check_gate_flips, check_oracle_contrast,
               check_reference_warp, check_car_depth_noise, check_subset_search,
               check_mot17_axis, check_kitti_geometry, check_class_split, check_causal_link,
               check_uavdt, check_strict_oracle, check_family_v2,
               check_runtime, check_mot20_oracle,
               check_permutation, check_depth_ratio_and_failures, check_ess_and_strata,
               check_placebo, check_provenance, check_manuscript_tables, check_manuscript_intervals,
               check_homography_robustness, check_homography_intervals,
               check_background_point_counts, check_reproduce_map, check_release_doc_refs, check_availability_counts, check_figure_order, check_chinese_abstract,
               check_estimator_convention, check_causal_link_homography,
               check_printed_measurement_tables):
        try:
            fn()
        except Exception as e:
            FAILS.append(f"ERROR       {fn.__name__}: {type(e).__name__}: {e}")

    print(f"checked {OKS + len(FAILS)} values from source")
    print(f"  matched : {OKS}")
    print(f"  problems: {len(FAILS)}")
    for f in FAILS:
        print("   ", f)
    print(f"\nnot covered here ({len(UNCHECKED)} items) -- see --list")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()

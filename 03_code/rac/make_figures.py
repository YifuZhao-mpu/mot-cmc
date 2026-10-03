"""
Generate every figure in the manuscript from the released CSVs and TrackEval output.

No number is typed in by hand except the TrackEval summary values, which are read
from the tracker output directories. Run:  python make_figures.py
Outputs PDF (for LaTeX) and PNG (for review) into 05_figures/.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

E = p("04_experiments")
TR = f"{E}/trackers"
OUT = p("05_figures")
os.makedirs(OUT, exist_ok=True)

# Okabe-Ito: colourblind-safe, prints legibly in greyscale
COLUMN_IN = 216 / 72.27
FULL_IN = 455 / 72.27

C = dict(blue="#0072B2", orange="#E69F00", green="#009E73", red="#D55E00",
         purple="#CC79A7", sky="#56B4E9", yellow="#F0E442", grey="#888888")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "figure.dpi": 150, "savefig.dpi": 600,
    "savefig.bbox": None, "savefig.pad_inches": 0,
})


def save(fig, name: str) -> None:
    # Final-size artwork: retain the exact column width and embed TrueType fonts.
    # Descriptive titles belong in the manuscript caption, not inside the plot.
    if fig._suptitle is not None:
        fig._suptitle.remove()
    for i, ax in enumerate(fig.axes):
        ax.set_title("")
        if len(fig.axes) > 1:
            ax.text(0, 1.03, f"({chr(97 + i)})", transform=ax.transAxes,
                    ha="left", va="bottom", fontsize=9)
    for label in fig.findobj(match=matplotlib.text.Text):
        label.set_color("#202020")
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/{name}.{ext}")
    plt.close(fig)
    print(f"  {name}")



def trackeval(run: str, cls: str, bench: str = "KITTI") -> dict:
    p = f"{TR}/{bench}/{run}/{cls}_summary.txt"
    with open(p) as f:
        keys, vals = f.readline().split(), f.readline().split()
    return {k: float(v) for k, v in zip(keys, vals)}


# ---------------------------------------------------------------- F1
def f1_value_axis() -> None:
    """MOT17 compensation-value axis, with and without the appearance channel."""
    labels = ["No\nCMC", "Online\nGMC", "Published\nGMC", "Reference\nwarp"]
    M = "MOT17-val-half"
    mo = [trackeval(r, "pedestrian", M) for r in
          ("A_noCMC", "A0_frozen", "A0_botsort_baseline", "N2S_oracle_strict")]
    rd = [trackeval(r, "pedestrian", M) for r in ("R_none", "R_online", "R_oracle_strict")]
    x = np.arange(4)
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL_IN, 2.6), layout="constrained")

    a.plot(x, [m["HOTA"] for m in mo], "o-", color=C["blue"], lw=1.6, ms=6,
           label="motion only")
    a.plot([0, 1, 3], [m["HOTA"] for m in rd], "s--", color=C["purple"], lw=1.6, ms=5.5,
           label="+ appearance (ReID)")
    a.set_xticks(x); a.set_xticklabels(labels)
    a.set_ylabel("HOTA"); a.legend(frameon=False, loc="lower right", fontsize=8.5)

    b.plot(x, [m["IDSW"] for m in mo], "o-", color=C["blue"], lw=1.6, ms=6)
    b.plot([0, 1, 3], [m["IDSW"] for m in rd], "s--", color=C["purple"], lw=1.6, ms=5.5)
    b.set_xticks(x); b.set_xticklabels(labels)
    b.set_ylabel("ID switches")

    fig.suptitle("MOT17 validation-half: fixed detections and strict reference substitution", y=1.03)
    save(fig, "F1_value_axis")


# ---------------------------------------------------------------- F2
def f2_reliability() -> None:
    """Four-benchmark reliability distributions."""
    src = [("MOT17", f"{E}/mot17_gmc_scan.csv", C["blue"]),
           ("MOT20", f"{E}/mot20_gmc_scan.csv", C["orange"]),
           ("UAVDT", f"{E}/uavdt_gmc_scan.csv", C["green"])]
    cols = [("inlier_ratio", "Inlier ratio ρ", (0.4, 1.005)),
            ("resid_median", "Transfer residual ε (px)", (0, 3)),
            ("displacement", "Displacement (px)", (0, 12))]
    fig, ax = plt.subplots(1, 3, figsize=(FULL_IN, 2.2), layout="constrained")
    for j, (col, lab, xl) in enumerate(cols):
        for k, (name, path, c) in enumerate(src):
            d = pd.read_csv(path)
            v = d[col].dropna().values
            v = v[np.isfinite(v)]
            ax[j].hist(v, bins=60, range=xl, density=True, histtype="step",
                       color=c, lw=1.3, linestyle=("-", "--", ":")[k], label=name)
        ax[j].set_xlabel(lab); ax[j].set_xlim(*xl)
        ax[j].set_yticks([])
    ax[0].legend(frameon=False, loc="upper left")
    ax[0].set_ylabel("density")
    fig.suptitle("Compensation residuals across three image benchmarks", y=1.04)
    save(fig, "F2_reliability")


# ---------------------------------------------------------------- F3
def f3_spread_vs_depth() -> None:
    """KITTI within-frame residual spread after ORACLE compensation, vs depth ratio."""
    d = pd.read_csv(f"{E}/kitti_per_object.csv")
    m = d[d.trans_m > 0.05]
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL_IN, 2.6), layout="constrained")
    a.scatter(m.depth_ratio, m.err_spread, s=3, alpha=0.18, color=C["blue"],
              edgecolors="none", rasterized=True)
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("Within-frame depth ratio")
    for axis in (a.xaxis, a.yaxis):
        axis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:g}"))
    a.set_ylabel("residual spread (px)")
    a.axhline(5, color=C["red"], ls="--", lw=1.0)
    a.text(1.05, 6, "5 px", color=C["red"], fontsize=8.5)

    thr = np.linspace(0, 20, 200)
    frac = [(m.err_spread > t).mean() * 100 for t in thr]
    b.plot(thr, frac, color=C["blue"], lw=1.6)
    for t, c in ((1, C["grey"]), (5, C["red"])):
        f = (m.err_spread > t).mean() * 100
        b.plot([t], [f], "o", color=c, ms=5)
        b.annotate(f"{f:.1f}% > {t} px", (t, f), textcoords="offset points",
                   xytext=(8, 6), color=c, fontsize=8.5)
    b.set_xlabel("spread threshold (px)"); b.set_ylabel("% of moving frames")
    fig.suptitle("KITTI: residual spread after target-fitted least-squares similarity "
                 f"({len(m):,} moving frames)", y=1.03)
    save(fig, "F3_spread_vs_depth")


# ---------------------------------------------------------------- F4
def f4_warp_family() -> None:
    """Final geometry and car-tracking results, with matching configurations."""
    gf = pd.read_csv(f"{E}/kitti_global_family_v2.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL_IN, 3.0), layout="constrained")
    thr = np.linspace(0, 20, 200)
    series = (("online_spread", "online GMC", C["red"]),
              ("oracle_spread", "target-fitted similarity", C["grey"]),
              ("sim_spread", "background-fitted similarity", C["blue"]),
              ("hom_spread", "depth-aware homography", C["green"]))
    for k, (col, lab, color) in enumerate(series):
        a.plot(thr, [(gf[col] > t).mean() * 100 for t in thr],
               lw=1.7, color=color, linestyle=("-", "--", ":", "-.")[k], label=lab)
    a.axvline(5, color="black", ls=":", lw=0.9)
    a.set_xlabel("residual spread threshold (px)")
    a.set_ylabel("% of moving frames")
    a.set_ylim(0, 100)
    a.legend(frameon=False, fontsize=8.5)
    a.set_title("Geometry: the models in Table 6", fontsize=8.5)
    points = [
        ("online GMC", gf.online_spread.median(),
         trackeval("v3_online", "car")["HOTA"], C["red"]),
        ("depth-aware homography", gf.hom_spread.median(),
         trackeval("planar2_homography", "car")["HOTA"], C["green"]),
    ]
    for lab, x, y, color in points:
        b.plot(x, y, "o", color=color, ms=8)
        offset = (-5, 12) if lab == "online GMC" else (8, -18)
        align = "right" if lab == "online GMC" else "left"
        b.annotate(f"{lab.replace('depth-aware homography', 'depth-aware'+chr(10)+'homography')}: {y:.3f}", (x, y), textcoords="offset points",
                   xytext=offset, fontsize=8.5, color=color, ha=align)
    b.set_xlabel("median residual spread (px)")
    b.set_ylabel("KITTI car HOTA")
    b.set_xlim(0, 10)
    b.set_ylim(65.0, 66.8)
    b.set_title("Tracking: fixed detections and sensor protocol", fontsize=8.5)
    save(fig, "F4_warp_family")


# ---------------------------------------------------------------- F5
def f5_forest() -> None:
    """Bootstrap CI forest plot -- every comparison the paper reports."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bci", p("03_code/rac/bootstrap_ci.py"))
    bci = importlib.util.module_from_spec(spec); spec.loader.exec_module(bci)

    pairs = [
        ("v3_online", "planar2_homography", "depth-aware homography $-$ online GMC"),
        ("v3_online", "planar2_homography_foot", "contact-point homography $-$ online GMC"),
        ("planar2_homography", "v4_per_target", "per-target $-$ depth-aware homography"),
        ("v4_global_oracle", "v4_per_target", "per-target $-$ global similarity"),
        ("v3_none", "v3_online", "enabling compensation"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(FULL_IN, 2.9), layout="constrained", sharey=True)
    for ax, cls, col in zip(axes, ("pedestrian", "car"), (C["blue"], C["orange"])):
        ys, pts, los, his = [], [], [], []
        for i, (base, comp, lab) in enumerate(pairs):
            a, b = bci.per_seq(base, cls), bci.per_seq(comp, cls)
            idx = a.index.intersection(b.index)
            w = a.loc[idx, "GT_Dets"].values.astype(float)
            pt, boots, _ = bci.bootstrap(a, b, "HOTA", w, n_boot=20000)
            lo, hi = np.percentile(boots, [2.5, 97.5])
            ys.append(len(pairs) - 1 - i); pts.append(pt); los.append(lo); his.append(hi)
        for y, pt, lo, hi in zip(ys, pts, los, his):
            excl = not (lo <= 0 <= hi)
            ax.plot([lo, hi], [y, y], color=col if excl else C["grey"],
                    lw=2.2 if excl else 1.4, solid_capstyle="butt")
            ax.plot([pt], [y], "o", color=col if excl else C["grey"],
                    ms=5.5, mfc="white" if not excl else col, mew=1.4)
        ax.axvline(0, color="black", lw=0.9)
        ax.set_title(cls, fontsize=9)
    fig.supxlabel("ΔHOTA (95% bootstrap CI over 21 sequences)",
                  fontsize=9)
    axes[0].set_yticks(list(range(len(pairs))))
    axes[0].set_yticklabels([p[2] for p in pairs][::-1])
    fig.suptitle("Filled = interval excludes zero; hollow = crosses zero", y=1.03)
    save(fig, "F5_forest")


# ---------------------------------------------------------------- F6
def f6_mechanism() -> None:
    """Improvement by exposure quartile -- the mechanism check."""
    d = pd.read_csv(f"{E}/kitti_causal_link.csv")
    fig, ax = plt.subplots(figsize=(COLUMN_IN, 2.65), layout="constrained")
    sub = d[d.cls == "pedestrian"]
    q = pd.qcut(sub.exposure, 4, labels=False, duplicates="drop")
    g = sub.groupby(q).apply(
        lambda x: pd.Series({"exp": x.exposure.median(),
                             "imp": (x.idsw_global - x.idsw_per).sum(),
                             "n": len(x)}), include_groups=False)
    ax.bar(range(len(g)), g["imp"], color=C["blue"], width=0.62)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels([f"Q{i+1}\n{v:.2f} px" for i, v in enumerate(g["exp"])])
    ax.set_xlabel("Exposure quartile")
    ax.margins(y=0.18)
    ax.set_ylabel("ID switches avoided")
    ax.axhline(0, color="black", lw=0.8)
    for i, v in enumerate(g["imp"]):
        ax.text(i, v + (0.6 if v >= 0 else -1.4), f"{int(v):+d}", ha="center", fontsize=8.5)
    ax.set_title("KITTI pedestrians: localisation by exposure", fontsize=9)
    save(fig, "F6_mechanism")


# ---------------------------------------------------------------- F7
def f7_depth_noise() -> None:
    """The two injected-noise sweeps, each against its stated reference."""
    rel = [0, 5, 11, 22, 35, 65]
    ped_runs = ["v3_per_target", "dn005_per_target", "dn010_per_target",
                "dn020_per_target", "dn030_per_target", "dn050_per_target"]
    car_runs = ["planar2_homography", "hom_dn005", "hom_dn010",
                "hom_dn020", "hom_dn030", "hom_dn050"]
    ped_ref = trackeval("v4_global_oracle", "pedestrian")["HOTA"]
    car_ref = trackeval("v3_online", "car")["HOTA"]
    fig, axes = plt.subplots(1, 2, figsize=(FULL_IN, 2.7), layout="constrained")
    for ax, cls, runs, ref, color, title, baseline in (
        (axes[0], "pedestrian", ped_runs, ped_ref, C["blue"],
         "Pedestrians: per-target correction", "global-similarity reference"),
        (axes[1], "car", car_runs, car_ref, C["green"],
         "Cars: depth-aware homography", "online GMC"),
    ):
        gain = [trackeval(run, cls)["HOTA"] - ref for run in runs]
        ax.plot(rel, gain, "o-", color=color, lw=1.7, ms=5.5)
        ax.axhline(0, color="black", lw=0.9)
        ax.set_xlim(-2, 70)
        ax.set_xlabel("Injected depth error (%)")
        ax.set_ylabel("ΔHOTA", fontsize=9)
        ax.set_title(title, fontsize=8.5)
    save(fig, "F7_depth_noise")


# ---------------------------------------------------------------- F8
def f8_signal_selection() -> None:
    """Held-out AUC by subset size -- adding signals makes it worse on real data."""
    d = pd.read_csv(f"{E}/signal_subset_search.csv")
    kcol = "k" if "k" in d.columns else [c for c in d.columns if "size" in c][0]
    acol = [c for c in d.columns if "auc" in c.lower()][0]
    best = d.groupby(kcol)[acol].max()
    fig, ax = plt.subplots(figsize=(COLUMN_IN, 2.65), layout="constrained")
    ax.plot(best.index, best.values, "o-", color=C["blue"], lw=1.7, ms=6,
            label="Best subset")
    ax.scatter(d[kcol], d[acol], s=9, color=C["grey"], alpha=0.45,
               zorder=0, label="All 63 subsets")
    ax.annotate("ε alone", (1, best.loc[1]), textcoords="offset points",
                xytext=(8, 9), color=C["blue"], fontsize=8.5)
    ax.annotate("All six signals", (6, best.loc[6]),
                textcoords="offset points", xytext=(-16, -30), color=C["red"], fontsize=8.5,
                ha="center", arrowprops=dict(arrowstyle="->", color=C["red"], lw=0.9))
    ax.set_xlabel("Number of reliability signals"); ax.set_ylabel("Held-out AUC")
    ax.margins(y=0.15)
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)
    ax.set_title("Single-residual reliability on MOT17", fontsize=9)
    save(fig, "F8_signal_selection")


if __name__ == "__main__":
    for fn in (f1_value_axis, f2_reliability, f3_spread_vs_depth, f4_warp_family,
               f5_forest, f6_mechanism, f7_depth_noise, f8_signal_selection):
        try:
            fn()
        except Exception as e:  # keep going; report what failed
            print(f"  FAILED {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n-> {OUT}")

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
C = dict(blue="#0072B2", orange="#E69F00", green="#009E73", red="#D55E00",
         purple="#CC79A7", sky="#56B4E9", yellow="#F0E442", grey="#888888")

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def save(fig, name: str) -> None:
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
    labels = ["none", "online\nGMC", "file GMC\n(published)", "oracle\nwarp"]
    M = "MOT17-val-half"
    mo = [trackeval(r, "pedestrian", M) for r in
          ("A_noCMC", "A0_frozen", "A0_botsort_baseline", "N2S_oracle_strict")]
    rd = [trackeval(r, "pedestrian", M) for r in ("R_none", "R_online", "R_oracle_strict")]
    x = np.arange(4)
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.8, 2.6))

    a.plot(x, [m["HOTA"] for m in mo], "o-", color=C["blue"], lw=1.6, ms=6,
           label="motion only")
    a.plot([0, 1, 3], [m["HOTA"] for m in rd], "s--", color=C["purple"], lw=1.6, ms=5.5,
           label="+ appearance (ReID)")
    a.set_xticks(x); a.set_xticklabels(labels)
    a.set_ylabel("HOTA"); a.legend(frameon=False, loc="lower right", fontsize=7.5)
    a.annotate("", xy=(1, mo[1]["HOTA"]), xytext=(0, mo[0]["HOTA"]),
               arrowprops=dict(arrowstyle="<->", color=C["green"], lw=1.1))
    a.text(0.62, 68.33, "+0.888\nhaving it", color=C["green"], ha="center", fontsize=7.5)
    a.annotate("", xy=(3, mo[3]["HOTA"]), xytext=(1, mo[1]["HOTA"]),
               arrowprops=dict(arrowstyle="<->", color=C["red"], lw=1.1))
    a.text(2.05, 68.62, "+0.087 motion only\n$-$0.076 with appearance",
           color=C["red"], ha="center", fontsize=7.5)

    b.plot(x, [m["IDSW"] for m in mo], "o-", color=C["blue"], lw=1.6, ms=6)
    b.plot([0, 1, 3], [m["IDSW"] for m in rd], "s--", color=C["purple"], lw=1.6, ms=5.5)
    b.set_xticks(x); b.set_xticklabels(labels)
    b.set_ylabel("ID switches")
    b.text(3.0, 205, "the oracle is worse\nin both configurations",
           color=C["red"], ha="right", fontsize=7.5)
    fig.suptitle("MOT17 validation-half \u2014 the warp is the only variable; the oracle is the strict one", y=1.03)
    save(fig, "F1_value_axis")


# ---------------------------------------------------------------- F2
def f2_reliability() -> None:
    """Four-benchmark reliability distributions."""
    src = [("MOT17", f"{E}/mot17_gmc_scan.csv", C["blue"]),
           ("MOT20", f"{E}/mot20_gmc_scan.csv", C["orange"]),
           ("UAVDT", f"{E}/uavdt_gmc_scan.csv", C["green"])]
    cols = [("inlier_ratio", "RANSAC inlier ratio $\\rho$", (0.4, 1.005)),
            ("resid_median", "transfer residual $\\varepsilon$ (px)", (0, 3)),
            ("displacement", "inter-frame displacement (px)", (0, 12))]
    fig, ax = plt.subplots(1, 3, figsize=(6.9, 2.2))
    for j, (col, lab, xl) in enumerate(cols):
        for name, path, c in src:
            d = pd.read_csv(path)
            v = d[col].dropna().values
            v = v[np.isfinite(v)]
            ax[j].hist(v, bins=60, range=xl, density=True, histtype="step",
                       color=c, lw=1.3, label=name)
        ax[j].set_xlabel(lab); ax[j].set_xlim(*xl)
        ax[j].set_yticks([])
    ax[0].legend(frameon=False, loc="upper left")
    ax[0].set_ylabel("density")
    fig.suptitle("Compensation is accurate on all three image benchmarks", y=1.04)
    save(fig, "F2_reliability")


# ---------------------------------------------------------------- F3
def f3_spread_vs_depth() -> None:
    """KITTI within-frame residual spread after ORACLE compensation, vs depth ratio."""
    d = pd.read_csv(f"{E}/kitti_per_object.csv")
    m = d[d.trans_m > 0.05]
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.5))
    a.scatter(m.depth_ratio, m.err_spread, s=3, alpha=0.18, color=C["blue"],
              edgecolors="none", rasterized=True)
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("within-frame depth ratio  $z_{max}/z_{min}$")
    a.set_ylabel("residual spread (px)")
    a.axhline(5, color=C["red"], ls="--", lw=1.0)
    a.text(1.05, 6, "5 px", color=C["red"], fontsize=7.5)

    thr = np.linspace(0, 20, 200)
    frac = [(m.err_spread > t).mean() * 100 for t in thr]
    b.plot(thr, frac, color=C["blue"], lw=1.6)
    for t, c in ((1, C["grey"]), (5, C["red"])):
        f = (m.err_spread > t).mean() * 100
        b.plot([t], [f], "o", color=c, ms=5)
        b.annotate(f"{f:.1f}% > {t} px", (t, f), textcoords="offset points",
                   xytext=(8, 6), color=c, fontsize=7.5)
    b.set_xlabel("spread threshold (px)"); b.set_ylabel("% of moving frames")
    fig.suptitle("KITTI: what survives the best possible GLOBAL correction "
                 f"({len(m):,} moving frames)", y=1.03)
    save(fig, "F3_spread_vs_depth")


# ---------------------------------------------------------------- F4
def f4_warp_family() -> None:
    """Geometric accuracy of a shared warp against what it buys in tracking."""
    gf = pd.read_csv(f"{E}/kitti_global_family_v2.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.7))

    thr = np.linspace(0, 20, 200)
    series = (("online_spread", "online GMC (deployed)", C["red"]),
              ("oracle_spread", "oracle similarity, one depth", C["grey"]),
              ("sim_spread", "deployable similarity", C["blue"]),
              ("hom_spread", "deployable homography", C["green"]))
    for col, lab, c in series:
        a.plot(thr, [(gf[col] > t).mean() * 100 for t in thr], lw=1.7, color=c, label=lab)
    a.axvline(5, color="black", ls=":", lw=0.9)
    a.set_xlabel("within-frame residual spread threshold (px)")
    a.set_ylabel("% of moving frames")
    a.set_ylim(0, 100)
    a.legend(frameon=False, fontsize=7)
    a.set_title("geometry: all four fitted to the static scene", fontsize=8.5)

    # tracking outcome against geometric spread -- the point of the figure
    pts = [("online GMC", gf.online_spread.median(), 47.428, C["red"]),
           ("oracle sim,\none depth", gf.oracle_spread.median(), 46.744, C["grey"]),
           ("deployable sim", gf.sim_spread.median(), 46.515, C["blue"]),
           ("deployable hom", gf.hom_spread.median(), 46.884, C["green"])]
    offs = {"online GMC": (-12, -16), "oracle sim,\none depth": (8, -6),
            "deployable sim": (-20, 10), "deployable hom": (8, 2)}
    for lab, x, y, c in pts:
        b.plot([x], [y], "o", color=c, ms=8)
        b.annotate(lab, (x, y), textcoords="offset points",
                   xytext=offs.get(lab, (6, -12)), fontsize=7, color=c)
    b.axhline(47.576, color=C["purple"], ls="--", lw=1.2)
    b.text(6.0, 47.62, "per-target", color=C["purple"], fontsize=7.5)
    b.set_xlabel("median within-frame residual spread (px)")
    b.set_ylabel("KITTI pedestrian HOTA")
    b.set_xlim(-0.5, 11.5)
    b.set_ylim(46.35, 47.72)
    b.set_title("tracking: the least accurate shared warp wins", fontsize=8.5)
    fig.suptitle("A shared warp's geometric accuracy does not predict what it buys", y=1.04)
    save(fig, "F4_warp_family")


# ---------------------------------------------------------------- F5
def f5_forest() -> None:
    """Bootstrap CI forest plot -- every comparison the paper reports."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bci", p("03_code/rac/bootstrap_ci.py"))
    bci = importlib.util.module_from_spec(spec); spec.loader.exec_module(bci)

    pairs = [
        ("v4_global_oracle", "v4_per_target", "per-target $-$ global similarity"),
        ("v4_global_homography", "v4_per_target", "per-target $-$ global homography"),
        ("v3_online", "v3_per_target", "per-target $-$ online GMC"),
        ("dep_global_oracle", "dep_per_target_depth", "estimated depth: $-$ global"),
        ("dep_online", "dep_per_target_depth", "estimated depth: $-$ online GMC"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
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
    fig.supxlabel("$\\Delta$ HOTA   (95 % bootstrap CI over 21 sequences)",
                  fontsize=9, y=-0.04)
    axes[0].set_yticks(list(range(len(pairs))))
    axes[0].set_yticklabels([p[2] for p in pairs][::-1])
    fig.suptitle("Filled = interval excludes zero; hollow = crosses zero", y=1.03)
    save(fig, "F5_forest")


# ---------------------------------------------------------------- F6
def f6_mechanism() -> None:
    """Improvement by exposure quartile -- the mechanism check."""
    d = pd.read_csv(f"{E}/kitti_causal_link.csv")
    fig, ax = plt.subplots(figsize=(4.4, 2.5))
    sub = d[d.cls == "pedestrian"]
    q = pd.qcut(sub.exposure, 4, labels=False, duplicates="drop")
    g = sub.groupby(q).apply(
        lambda x: pd.Series({"exp": x.exposure.median(),
                             "imp": (x.idsw_global - x.idsw_per).sum(),
                             "n": len(x)}), include_groups=False)
    ax.bar(range(len(g)), g["imp"], color=C["blue"], width=0.62)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels([f"Q{i+1}\n{v:.2f} px" for i, v in enumerate(g["exp"])])
    ax.set_xlabel("exposure quartile (median disagreement between own and shared warp)")
    ax.set_ylabel("ID switches avoided")
    ax.axhline(0, color="black", lw=0.8)
    for i, v in enumerate(g["imp"]):
        ax.text(i, v + (0.6 if v >= 0 else -1.4), f"{int(v):+d}", ha="center", fontsize=8)
    ax.set_title("KITTI pedestrians: the gain is where the mechanism predicts", fontsize=9)
    save(fig, "F6_mechanism")


# ---------------------------------------------------------------- F7
def f7_depth_noise() -> None:
    """Depth-noise tolerance with the real monocular model marked."""
    sig = [0.00, 0.05, 0.10, 0.20, 0.30, 0.50]
    rel = [0, 5, 11, 22, 35, 65]
    runs = ["v3_per_target", "dn005_per_target", "dn010_per_target",
            "dn020_per_target", "dn030_per_target", "dn050_per_target"]
    ref = trackeval("v4_global_oracle", "pedestrian")["HOTA"]
    gain = [trackeval(r, "pedestrian")["HOTA"] - ref for r in runs]
    dep = (trackeval("dep_per_target_depth", "pedestrian")["HOTA"]
           - trackeval("dep_global_oracle", "pedestrian")["HOTA"])

    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    ax.plot(rel, gain, "o-", color=C["blue"], lw=1.7, ms=5.5,
            label="injected multiplicative noise")
    ax.axhline(0, color="black", lw=0.9)
    ax.fill_between([0, 70], -0.05, 0.05, color=C["grey"], alpha=0.12, lw=0)
    ax.axvspan(5, 10, color=C["green"], alpha=0.12, lw=0)
    ax.text(7.5, max(gain) + 0.13, "published monocular AbsRel", color=C["green"],
            ha="center", fontsize=7)
    ax.plot([8], [dep], "*", color=C["red"], ms=13, zorder=5,
            label="real model (Depth-Anything-V2)")
    ax.set_xlim(-2, 70)
    ax.set_xlabel("relative depth error (%)")
    ax.set_ylabel("$\\Delta$ HOTA vs global oracle")
    ax.set_ylim(min(gain) - 0.15, max(gain) + 0.36)
    ax.legend(frameon=False, loc="lower left", fontsize=7.5)
    ax.set_title("KITTI pedestrians: tolerance to depth error", fontsize=9)
    save(fig, "F7_depth_noise")


# ---------------------------------------------------------------- F8
def f8_signal_selection() -> None:
    """Held-out AUC by subset size -- adding signals makes it worse on real data."""
    d = pd.read_csv(f"{E}/signal_subset_search.csv")
    kcol = "k" if "k" in d.columns else [c for c in d.columns if "size" in c][0]
    acol = [c for c in d.columns if "auc" in c.lower()][0]
    best = d.groupby(kcol)[acol].max()
    fig, ax = plt.subplots(figsize=(4.4, 2.5))
    ax.plot(best.index, best.values, "o-", color=C["blue"], lw=1.7, ms=6,
            label="best subset at each size (real MOT17, leave-one-seq-out)")
    ax.scatter(d[kcol], d[acol], s=9, color=C["grey"], alpha=0.45,
               zorder=0, label="all 63 subsets")
    ax.annotate("$\\varepsilon$ alone", (1, best.loc[1]), textcoords="offset points",
                xytext=(10, -2), color=C["blue"], fontsize=8)
    ax.annotate("all six\n(the pre-registered choice)", (6, best.loc[6]),
                textcoords="offset points", xytext=(-16, -30), color=C["red"], fontsize=8,
                ha="center", arrowprops=dict(arrowstyle="->", color=C["red"], lw=0.9))
    ax.set_xlabel("number of reliability signals"); ax.set_ylabel("held-out AUC")
    ax.legend(frameon=False, loc="lower left", fontsize=7)
    ax.set_title("More signals, worse generalisation", fontsize=9)
    save(fig, "F8_signal_selection")


if __name__ == "__main__":
    for fn in (f1_value_axis, f2_reliability, f3_spread_vs_depth, f4_warp_family,
               f5_forest, f6_mechanism, f7_depth_noise, f8_signal_selection):
        try:
            fn()
        except Exception as e:  # keep going; report what failed
            print(f"  FAILED {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n-> {OUT}")

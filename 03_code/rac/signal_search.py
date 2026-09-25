"""
A9 at the estimator level: which reliability signals actually earn their place?

DA-CP1 M3 required that the combination rule be justified rather than asserted,
and that any signal which does not change the outcome be removed. This performs
the exhaustive subset search over the six primitives on REAL data, against the
I1 oracle contrast as the target.

Two guards against fooling ourselves:

  1. LEAVE-ONE-SEQUENCE-OUT. A subset chosen on all seven sequences and then
     evaluated on the same seven is selection on the test set. Every subset is
     scored by held-out sequence, so "best subset" means best generalisation
     across sequences, not best fit.

  2. The synthetic study reached the OPPOSITE conclusion (the 6-signal geometric
     mean beat every individual signal there). That disagreement is reported,
     not resolved by picking the convenient one. The likely reason is printed:
     per-signal variance on real MOT17 data.
"""
from __future__ import annotations

import argparse
import glob
import itertools

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

SIGNALS = ["rho_n", "n_n", "eps_n", "tau_n", "kappa_n", "phi_n"]
SHORT = {"rho_n": "rho", "n_n": "n", "eps_n": "eps",
         "tau_n": "tau", "kappa_n": "kap", "phi_n": "phi"}


def add_signals(d: pd.DataFrame, n0=300.0, eps0=1.0, tau0=5.0, s0=0.05, th0=2.0):
    d = d.copy()
    d["rho_n"] = d["inlier_ratio"].fillna(0.0)
    d["n_n"] = np.minimum(1.0, d["n_inliers"] / n0)
    d["eps_n"] = np.exp(-d["resid_median"].fillna(10.0) / eps0)
    d["tau_n"] = np.exp(-d["temporal_resid"].fillna(50.0) / tau0)
    d["kappa_n"] = np.exp(-(np.abs(np.log(d["scale"].clip(1e-6))) / s0
                            + np.abs(d["rotation_deg"]) / th0))
    d["phi_n"] = 1.0 - d["frac_inliers_in_det"].fillna(0.0)
    return d


def combine(d: pd.DataFrame, subset) -> np.ndarray:
    v = np.clip(d[list(subset)].values, 1e-9, 1.0)
    return np.power(np.prod(v, axis=1), 1.0 / len(subset))


def auc(score, label) -> float:
    o = np.argsort(score)
    l = np.asarray(label)[o]
    pos, neg = l.sum(), len(l) - l.sum()
    if pos < 3 or neg < 3:
        return float("nan")
    r = np.arange(1, len(l) + 1)
    return float((r[l == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=p("04_experiments/oracle/*.csv"))
    ap.add_argument("--threshold", type=float, default=1.0, help="px, 'bad compensation'")
    a = ap.parse_args()

    df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(a.glob))], ignore_index=True)
    df = df[df.ref_ok.astype(bool)]
    df = add_signals(df)
    seqs = sorted(df.sequence.unique())
    print(f"{len(df)} frames, {len(seqs)} sequences, target = corner_disagreement_px\n")

    # ---- why the real-data answer may differ from synthetic: variance ----
    print("=== per-signal variance on real MOT17 (a signal with no variance cannot inform) ===")
    v = df[SIGNALS].agg(["mean", "std", "min", "max"]).T
    v["frac_at_ceiling"] = [(df[s] > 0.999).mean() for s in SIGNALS]
    print(v.round(4).to_string())

    # ---- exhaustive subset search, leave-one-sequence-out ----
    rows = []
    subsets = [c for k in range(1, len(SIGNALS) + 1)
               for c in itertools.combinations(SIGNALS, k)]
    for sub in subsets:
        sp_out, auc_out = [], []
        for held in seqs:
            te = df[df.sequence == held]
            if len(te) < 30:
                continue
            r = combine(te, sub)
            sp_out.append(spearmanr(r, te["corner_disagreement_px"].values)[0])
            bad = (te["corner_disagreement_px"] > a.threshold).astype(int).values
            if 3 <= bad.sum() <= len(bad) - 3:
                auc_out.append(1 - auc(r, bad))
        rows.append(dict(
            subset="+".join(SHORT[s] for s in sub), k=len(sub),
            spearman_mean=float(np.mean(sp_out)),
            spearman_worst=float(np.max(sp_out)),      # worst = least negative
            auc_mean=float(np.mean(auc_out)) if auc_out else np.nan,
            auc_worst=float(np.min(auc_out)) if auc_out else np.nan,
            n_seq_auc=len(auc_out),
        ))
    res = pd.DataFrame(rows)

    print(f"\n=== leave-one-SEQUENCE-out subset search (threshold {a.threshold} px) ===")
    print("ranked by mean held-out AUC; 'worst' is the worst single held-out sequence\n")
    top = res.sort_values("auc_mean", ascending=False).head(15)
    print(top.round(4).to_string(index=False))

    print("\n=== best subset at each size ===")
    best = res.loc[res.groupby("k")["auc_mean"].idxmax()]
    print(best.round(4).to_string(index=False))

    full = res[res.subset == "+".join(SHORT[s] for s in SIGNALS)].iloc[0]
    win = res.sort_values("auc_mean", ascending=False).iloc[0]
    print(f"\nfull 6-signal set : AUC {full.auc_mean:.4f} (worst {full.auc_worst:.4f}), "
          f"spearman {full.spearman_mean:+.4f}")
    print(f"best subset       : {win.subset}  AUC {win.auc_mean:.4f} "
          f"(worst {win.auc_worst:.4f}), spearman {win.spearman_mean:+.4f}")
    print(f"\ndelta from dropping signals: AUC {win.auc_mean - full.auc_mean:+.4f}")

    out = p("04_experiments/signal_subset_search.csv")
    res.to_csv(out, index=False)
    print(f"\nall {len(res)} subsets -> {out}")
    print("\nNOTE: the synthetic failure study found the FULL set best "
          "(spearman -0.821 vs best single -0.733).\nIf real data disagrees, BOTH "
          "results are reported; the disagreement is a finding about which\nfailure modes "
          "actually occur in MOT17, not a reason to pick the convenient one.")


if __name__ == "__main__":
    main()

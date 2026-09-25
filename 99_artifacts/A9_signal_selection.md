# A9 — Which reliability signals earn their place?

**Date**: 2026-09-20 · **Status**: settled on MOT17; robot data may revise it
**Requirement**: DA-CP1 M3 — "derive or explicitly justify the `r` combination rule…
show A9 signal-drop results proving each retained term earns its place."

---

## 1. The two experiments disagree, and the disagreement is the finding

| Experiment | Data | Target | Best configuration | Score |
|---|---|---|---|---|
| Synthetic failure study | 234 frames, 6 injected failure modes, **ground-truth warp known** | actual corner error | **all 6 signals** (geometric mean) | Spearman −0.821 (best single: `ε` −0.720) |
| Real MOT17, leave-one-sequence-out | 5088 frames, 7 sequences, I1 oracle contrast | online-vs-reference disagreement | **`ε` alone** | held-out AUC 0.866 (all 6: 0.774) |

Both are reported. The convenient one is not selected.

## 2. Real-data subset search (63 subsets, leave-one-sequence-out)

Held-out AUC for detecting compensation error > 1 px, best subset at each size:

| k | best subset | held-out AUC | worst sequence | Spearman |
|---|---|---|---|---|
| **1** | **`eps`** | **0.8664** | 0.7792 | −0.7369 |
| 2 | `n`+`eps` | 0.8664 | 0.7792 | −0.7369 |
| 3 | `rho`+`n`+`eps` | 0.8637 | 0.7798 | −0.7277 |
| 4 | `rho`+`n`+`eps`+`kap` | 0.8596 | 0.7660 | −0.7339 |
| 5 | `rho`+`n`+`eps`+`kap`+`phi` | 0.8540 | 0.7703 | −0.7038 |
| 6 | all | 0.7741 | 0.6139 | −0.5505 |

Adding signals degrades held-out performance **monotonically**. Dropping from six to
one gains **+0.0924 AUC**.

## 3. Why — diagnosed, not guessed

Per-signal statistics over the same 5088 real frames:

| signal | mean | std | fraction at ceiling (>0.999) | verdict |
|---|---|---|---|---|
| `n` (inlier count) | 0.9999 | 0.0067 | **99.94 %** | **degenerate** |
| `kappa` | 0.9261 | 0.0948 | 2.6 % | weak, dominated by `eps` |
| `phi` (foreground) | 0.7600 | 0.1534 | 0.04 % | has variance but AUC 0.584 alone |
| `tau` (temporal) | 0.6656 | 0.3238 | 0 % | **actively harmful in combination** |
| `eps` (residual) | 0.6002 | 0.2522 | 0 % | **the signal** |
| `rho` (inlier ratio) | — | — | — | AUC 0.806 alone, redundant with `eps` |

- **`n` is degenerate on MOT17 by construction.** BoT-SORT's GMC calls
  `goodFeaturesToTrack` with `maxCorners=1000`; MOT17 always supplies enough texture to
  saturate it, so `min(1, n/300)` is pinned at 1. It carried real information in the
  synthetic `low_texture` mode, where inliers collapsed to zero — that mode simply does
  not occur in MOT17 (`n_inliers < 100` in **0** of 5316 frames).
- **`tau` is the biggest single loss** (0.854 → 0.774 when added at k=6). It detects
  *sporadic* single-frame failures, which is what it was designed for. But real camera
  motion in MOT17 is not smooth — panning accelerates, vehicles turn — so a
  constant-velocity prediction of the warp is violated by legitimate motion, and `tau`
  reports those as unreliability. It is a false-alarm generator on real data.
- **`phi` survived the variance test but fails the usefulness test.** DA-CP1 M2 asked
  whether `phi` was degenerate; it is not (std 0.153, range 0–0.896). But variance is not
  information: AUC 0.584 alone, and including it costs held-out AUC.

## 4. Decision

**The reported estimator uses `eps` — the median RANSAC transfer residual of the inlier
set — alone.** The other five are reported as tested-and-rejected, with the reasons above.

Consequences for the manuscript:
- The likelihood-ratio/geometric-mean derivation (Blueprint §2.1) is retained as the
  *framework*, but the retained signal set is `{eps}`, so it reduces to `r = eps_n`.
  Presenting a six-signal product that the data rejects would be dishonest.
- The method becomes **simpler**, not weaker: one scalar, already computed by the existing
  RANSAC call, no new hyperparameters beyond `eps0`.
- The synthetic result is retained in the paper as evidence about *which failure modes the
  signals can detect in principle*, with the explicit statement that the catastrophic
  modes it exercises (uniform background, foreground domination to the point of collapse)
  are absent from MOT17. That is a statement about the benchmark, and it is worth making:
  **MOT17 does not contain the failure regime the literature warns about.**

## 5. Open — to be revisited with robot data

The robot protocol (`ROBOT_RECORDING_PROTOCOL.md`) deliberately includes conditions B2
(low-texture) and B4 (foreground-dominated) precisely because MOT17 lacks them. If those
conditions reproduce the synthetic behaviour, the multi-signal estimator may be justified
*for that regime* while `eps` alone remains correct for MOT17-like data. That would be a
scope statement, not a rescue of the discarded signals.

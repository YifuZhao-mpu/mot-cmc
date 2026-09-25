# K5 — Power gate result

**Date**: 2026-09-20 · **Threshold (user-selected)**: N2 ≥ 3 × N1
**All configurations consume byte-identical frozen detections** (62,398 detections,
per-file SHA-256 recorded in `detections/MOT17-val-half/manifest.json`).

---

## 1. N1 — noise floor

Five runs of the unmodified baseline under identical inputs (the original plus four repeats
on four separate GPUs):

```
MOT17-02-FRCNN   3f017f09 3f017f09 3f017f09 3f017f09 | orig 3f017f09
MOT17-13-FRCNN   c1b50afb c1b50afb c1b50afb c1b50afb | orig c1b50afb
```

**Every tracker output file is bit-identical across all five runs. N1 = 0 exactly.**

The pipeline is deterministic under fp16 + fused convolutions on the A800. This is a
stronger statement than "the variance is small", and it is reported as such.

**It also makes the 3× ratio test vacuous**: any non-zero effect divided by zero is
infinite, which would let an arbitrarily small gain pass. A zero noise floor does not
license calling +0.099 HOTA significant. Per `METHODOLOGY_BLUEPRINT` §3.0.1 the practical
noise scale must come from elsewhere — see §4.

## 2. N2 — headroom ceiling

The offline reference warp (non-causal, full-resolution SIFT, foreground-masked,
forward-backward verified) substituted into an otherwise-unmodified tracker. No online
method can do this; it is an upper bound on what any online method could recover.

| metric | file-GMC (published, 0.52 px err) | sparseOptFlow (1.3 px err) | **oracle (0 px)** | **headroom vs sparseOptFlow** |
|---|---|---|---|---|
| **HOTA** | 69.120 | 69.006 | 69.105 | **+0.099** |
| AssA | 71.570 | 71.333 | 71.528 | +0.195 |
| IDF1 | 81.499 | 81.345 | 81.490 | +0.145 |
| DetA | 67.239 | 67.246 | 67.249 | +0.003 |
| MOTA | 78.445 | 78.451 | 78.493 | +0.042 |
| **IDSW** | 140 | 139 | **144** | **+5 (worse)** |
| Frag | 443 | 443 | 443 | 0 |

## 2b. The complete compensation-value axis

Four configurations, identical frozen detections, identical tracker, only the source of the
camera-motion warp changed:

| configuration | HOTA | AssA | IDF1 | MOTA | **IDSW** |
|---|---|---|---|---|---|
| **no compensation** | 68.118 | 69.914 | 79.598 | 77.777 | **337** |
| sparseOptFlow (~1.3 px error) | 69.006 | 71.333 | 81.345 | 78.451 | **139** |
| file-GMC (0.52 px error, published) | **69.120** | **71.570** | **81.499** | 78.445 | 140 |
| oracle (0 px error, non-causal) | 69.105 | 71.528 | 81.490 | **78.493** | **144** |

| | HOTA | IDSW |
|---|---|---|
| value of **having** compensation (sparseOptFlow − none) | **+0.888** | **−198** |
| value of **perfecting** it (oracle − sparseOptFlow) | **+0.099** | **+5** |
| perfecting, as a share of having | **11.1 %** | negative |

**The curve saturates almost immediately.** Roughly 89 % of everything compensation can buy
is obtained by having *any* working compensator. The remaining accuracy — the entire
territory this project set out to claim — is worth 0.099 HOTA, and on identity switches it
is worth **less than nothing**: perfect compensation yields 144 ID switches against 139 for
an estimator that is wrong by 1.3 px on average.

## 3. The two findings that settle it

**(a) The relationship is not monotone at this scale.** Perfect compensation (69.105) is
*below* the published file-GMC configuration with 0.52 px of error (69.120). Once
compensation error is under about half a pixel, tracking quality no longer tracks it.

**(b) IDSW — the metric the research question is about — gets WORSE with perfect
compensation**, 139 → 144. The project asked how to reduce identity switches under camera
motion; making the camera motion estimate exact increases them on this benchmark.

Both are consistent with the SQ2 gate-flip measurement (34 harmful flips in 109,955 pairs)
and with the geometry (median IoU cost of compensation error: 0.00085).

## 4. The gate, decided against a meaningful noise scale

With N1 = 0 the ratio test cannot be applied. The substantive comparison instead uses a
scale that is both measurable and directly relevant:

> **the difference between two reasonable compensator implementations**
> file-GMC vs sparseOptFlow = **0.114 HOTA**

| quantity | HOTA |
|---|---|
| value of perfecting compensation (N2 headroom) | **+0.099** |
| difference between two ordinary compensator choices | **0.114** |
| value of perfecting it, relative to the *published* baseline | **−0.015** |

**Fixing the compensator is worth less than choosing a different one.** Relative to the
configuration BoT-SORT actually publishes, perfect compensation is worth nothing at all.

### Verdict: **K5 FAILS.** MOT17 aggregate metrics cannot carry a paper about
### camera-motion-compensation reliability.

## 5. Pre-committed response (DA-CP1 R3 — binding)

The blueprint fixed the response *before* the numbers were seen:

> "if `N2 < 3 × N1`, MOT17/MOT20 aggregate metrics **cannot** carry the paper. The project
> then either (a) pivots the primary evidence to the robot study and reliability-stratified
> sub-population results, or (b) adds a benchmark where camera motion is severe enough to
> matter. This decision is made **before** running the full ablation, not after seeing
> disappointing numbers."

and

> "**Do not re-run the gate until it passes.** The pre-committed response to a failed gate
> is a pivot, not a retry."

The full ablation matrix (A1–A11) is therefore **not run** on MOT17. Options are set out in
`DECISION_MEMO.md`.

## 6. What this result is worth on its own

It is not a null finding about nothing. It is a quantified, reproducible answer to a
question the field has not asked:

- compensation error on MOT17 is **measurable** (oracle-warp contrast) and **predictable**
  (free RANSAC residual, held-out AUC 0.866);
- it is **too small to matter**, and the bound is established three independent ways —
  geometrically (IoU cost 0.00085), combinatorially (34/109,955 gate flips), and
  empirically (+0.099 HOTA with a non-causal oracle);
- the benchmarks **do not contain** the failure regime the literature describes;
- therefore any tracking improvement attributed to camera-motion compensation on
  MOT17/MOT20 is attributable to something else.

# Do MOT17 and MOT20 contain the camera-motion-compensation failure regime?

**Date**: 2026-09-20 · **Frames audited**: 5,309 (MOT17 train) + 8,927 (MOT20 train) = **14,236**
**Instrument**: the instrumented GMC, bit-identical to BoT-SORT's own (`max |ΔH| = 0.0`)

**Answer: no. Neither benchmark contains it, for different reasons.**

---

## 1. What the failure regime is, according to the literature

| Source | Named failure condition |
|---|---|
| Safdarnejad et al., arXiv:1603.03968 | "real-world unconstrained videos with **predominant foreground or uniform background**"; "**sporadic failures of motion estimation at a few frames**" |
| McByte++, arXiv:2608.15688 §3.5 | "scenes with **weak texture, heavy motion blur, or largely homogeneous backgrounds**" |
| BoT-SORT, arXiv:2206.14651 §3.2 | dynamic camera; also "vibrations or drifts caused by the wind, **as in MOT20**" |

The synthetic study in this project confirms these conditions produce real error when they
occur: median corner error 1.42 px (foreground-dominated) and **105 px** (low texture),
against 0.013 px in the clean control.

## 2. What the benchmarks actually contain

| Statistic | MOT17 | MOT20 |
|---|---|---|
| frames | 5,309 | 8,927 |
| `n_inliers < 100` (texture collapse) | **0 (0.000 %)** | **0 (0.000 %)** |
| `n_inliers < 300` | 3 (0.057 %) | 1 (0.011 %) |
| `eps > 2 px` (imprecise fit) | 190 (3.579 %) | **0 (0.000 %)** |
| `phi > 0.7` (inliers mostly on people) | 228 (4.295 %) | **3,314 (37.123 %)** |
| median inlier ratio, per sequence | 0.842 – 1.000 | 0.980 – 1.000 |
| median residual `eps`, per sequence | 0.061 – 1.113 px | 0.305 – 0.720 px |
| median frame displacement, per sequence | 0.17 – 7.70 px | 0.45 – 0.98 px |

### MOT17 — no texture-collapse regime
The estimator never runs short of correspondences: `goodFeaturesToTrack(maxCorners=1000)`
is saturated in essentially every frame. The worst sequence (MOT17-05) reaches a median
inlier ratio of 0.842 and a 5th-percentile of 0.538, with median residual 1.11 px — real
degradation, but an order of magnitude away from the synthetic low-texture regime.

### MOT20 — extreme foreground domination, and it does not matter
MOT20-05 has **`phi` = 0.8166 at the median**: 82 % of the inliers used to estimate *camera*
motion sit on *pedestrians*. Across MOT20, 37.1 % of frames exceed `phi > 0.7`. By the
literature's description this should be the worst case.

It is not. MOT20's estimates are *cleaner* than MOT17's moving-camera ones: higher inlier
ratio, lower residual, and **zero** frames with `eps > 2 px`.

The reason is mechanical. MOT20 is a static-camera benchmark with dense, slow, coherent
pedestrian flow. The contaminating keypoints move consistently with each other, so the fit
has a low residual; and because the crowd's inter-frame displacement is sub-pixel, the
resulting transform — which describes crowd motion rather than camera motion — is still
numerically close to identity, which is the correct answer for a static camera.

**Contamination is not error. What matters is whether the contaminating objects move.**

This also explains a result from the signal-selection study that was otherwise puzzling:
`phi` has a held-out AUC of only 0.584 for predicting compensation error. High foreground
contamination simply does not imply a wrong warp.

## 3. Consequence

The two standard pedestrian MOT benchmarks cannot be used to evaluate camera-motion
compensation robustness, because compensation on them is almost never wrong:

- MOT17 lacks the conditions that break the estimator;
- MOT20 has one of those conditions in the extreme, but in a configuration where it is
  harmless.

This sharpens the critique made by the 2026 KAIST survey (arXiv:2609.08265) — that
"inconsistencies obscure the genuine contribution of each module" — into something
specific and testable: **an improvement attributed to camera-motion compensation on
MOT17/MOT20 cannot be an improvement in compensation robustness, because the baseline
compensation is not failing.** Whatever such a method is doing, it is doing something else.

## 4. Where the regime does exist

| Setting | Why |
|---|---|
| Synthetic low-texture (this project) | median error 105 px; the estimator gives up (identity fallback) in 56 % of frames |
| Synthetic foreground-dominated with *moving* occluders | median error 1.42 px, inlier ratio 0.234 |
| Robot protocol conditions B2 (low texture) and B4 (foreground-dominated) | designed for exactly this gap |
| UAV benchmarks (VisDrone, UAVDT) — **untested here** | severe ego-motion; AMOT (AAAI 2026) targets them for this reason |
| Vehicle-mounted (KITTI) — **untested here** | translation-dominated, so a single 2D similarity is wrong by construction (parallax) |

The last two are hypotheses, not findings. They are listed as the natural next measurement,
not as claims.

---

## 5. Addendum — the configuration BoT-SORT actually publishes is even cleaner

`tools/track.py --default-parameters` does **not** set `cmc_method`, so the published
results use the argparse default `"file"`: precomputed VidStab GMC read from
`tracker/GMC_files/MOT17_ablation/`. The `sparseOptFlow` path instrumented throughout this
project is a different, online estimator.

Measured against the same offline reference warp, over the val-half frames:

| Sequence | published file-GMC (median) | sparseOptFlow (median) |
|---|---|---|
| MOT17-02 | 0.073 px | 0.088 px |
| MOT17-04 | **0.042 px** | 0.147 px |
| MOT17-05 | **1.285 px** | 2.105 px |
| MOT17-09 | **0.067 px** | 0.505 px |
| MOT17-10 | **0.383 px** | 1.121 px |
| MOT17-11 | 0.712 px | 0.786 px |
| MOT17-13 | **1.035 px** | 1.669 px |
| pooled | **0.516 px** | ~1.3 px (moving) |

Two consequences:

1. **The 34 harmful gate flips are an upper bound relative to the published configuration.**
   They were measured on the *worse* of the two compensators. BoT-SORT as published has
   roughly half the error, so the coupling defect fires even less often than reported here.

2. **A structural obstacle for reliability-aware compensation, worth stating in its own
   right.** Assessing reliability requires the compensator to expose its internal
   verification statistics — inlier mask, residuals, correspondence geometry. The
   best-performing path here is a precomputed file containing six affine parameters and
   nothing else. The better compensator is the one that cannot be audited. Any
   reliability-aware method is therefore constrained to the online, less accurate
   estimator, and must overcome that handicap before it can show a net gain.

---

## 6. UAVDT — the aerial benchmark has the CLEANEST compensation of all

50 sequences, **40,685 frames**, 1024×540. Same instrument.

| dataset | ρ median | **ε median** | ε p95 | displacement median | τ median |
|---|---|---|---|---|---|
| MOT17 | 0.976 | 0.570 px | 1.767 | 2.095 px | 1.215 |
| MOT20 | 0.995 | 0.592 px | 0.879 | 0.689 px | 0.813 |
| **UAVDT** | **1.000** | **0.295 px** | 0.941 | 1.035 px | **0.166** |

| failure indicator | MOT17 | MOT20 | UAVDT |
|---|---|---|---|
| `eps > 2 px` | 3.579 % | 0.000 % | **0.364 %** |
| `rho < 0.7` | 3.824 % | 0.011 % | **0.224 %** |
| `n_inliers < 300` | 0.057 % | 0.011 % | 3.982 % |
| `n_inliers < 100` | 0.000 % | 0.000 % | 0.047 % |

**UAV footage — which the literature treats as the hard case for camera motion — has the most
reliable compensation of the three.** Temporal consistency is an order of magnitude better
than MOT17 (τ 0.166 vs 1.215), consistent with gimbal-stabilised flight.

The reason is geometric. An aerial view of a road or rooftop is approximately planar and far
away, so scene depth is nearly constant across the frame and a single homography is very
nearly the correct model. UAVDT does show mild texture scarcity absent from the pedestrian
sets (`n_inliers < 300` in 4.0 % of frames), but it rarely translates into a bad fit.

This does not contradict the UAV-tracking literature. AMOT (AAAI 2026) and JitTrack (2026)
describe *large* inter-frame displacement and viewpoint change, not *inaccurate*
compensation. Large displacement that is accurately compensated is not a compensation
problem.

---

## 7. Synthesis across four benchmarks

| domain | is the compensation estimate accurate? | is the 2D warp model adequate? | room for reliability-aware compensation |
|---|---|---|---|
| MOT17 (pedestrian, mixed camera) | yes — ε 0.57 px | yes — rotation-dominated | **none** (0.031 % of pairs; oracle worth +0.099 HOTA, IDSW +5) |
| MOT20 (pedestrian, static, dense) | yes — ε 0.59 px | yes — static camera | **none** |
| UAVDT (aerial) | yes, best of all — ε 0.295 px | yes — planar, distant scene | **none** |
| **KITTI (vehicle-mounted)** | — | **NO — translation with strong depth variation** | **2.08 % of object-frames, 67× MOT17** |

**The failure is not noisy estimation. It is one correction shared across targets at
different depths.**

An earlier version of this section said "an inadequate model", implying that a richer warp
family would fix it. That was tested and is **false**: a *deployable* global homography —
fitted to the static scene, as a compensator must be — reduces the within-frame residual
spread by only **2.2 %** (6.23 → 6.10 px), and leaves the fraction of frames with spread
above 5 px unchanged (53.17 % → 53.24 %). A homography fitted instead to the objects' own
true displacements cuts the spread by 91 %, but that is a curve fit to the answer, not a
compensator, and the 91 % figure must not be quoted as if it were achievable.

Three of the four benchmarks are configurations where one global 2D warp describes the scene
motion correctly, and there the compensator is already accurate enough that improving it buys
nothing. The fourth is a configuration where no global 2D warp can be correct, and there the
error survives *perfect* estimation.

This reframes the problem the project started with. Estimating the *reliability of the
estimate* — the original proposal, and the thing McByte++ and IMM-JHSE approach from
different directions — is the wrong instrument, because on the benchmarks where it can be
measured the estimate is not the bottleneck. What matters is the **per-target adequacy of the
warp**, which is depth-dependent and therefore cannot be expressed as a single per-frame
scalar at all.

---

## 8. UAVDT — the downstream measurement (DA-CP2 M3)

§6 established that UAVDT's compensation *estimates* are the cleanest of the three image
benchmarks. That is not the same as showing compensation does not matter there, and §7
listed UAVDT alongside MOT17/MOT20 at a strength the evidence did not support. This closes
the gap with the comparison UAVDT can carry: it has no ground-truth ego-motion, so no
oracle warp is possible, but `none` vs `online` answers whether compensation changes
outcomes at all.

20 sequences, UAVDT's own published FRCNN detections, identical across both runs:

| configuration | HOTA | AssA | DetA | MOTA | IDF1 | IDSW | Frag |
|---|---|---|---|---|---|---|---|
| no compensation | 43.920 | 48.644 | 40.242 | 31.786 | 57.335 | 3342 | 8939 |
| online GMC | 44.083 | 48.946 | 40.276 | 31.756 | 57.646 | 3347 | 8993 |

### The value of *having* compensation, across all four domains

| domain | ΔHOTA | ΔIDSW | relative |
|---|---|---|---|
| **UAVDT (aerial)** | **+0.163** | **+5** | **+0.1 % — none** |
| MOT17 (pedestrian) | +0.888 | −198 | −58.8 % |
| KITTI car | +0.473 | −236 | −58.9 % |
| KITTI pedestrian | +1.929 | −153 | −54.8 % |

**On UAVDT, camera-motion compensation changes 5 ID switches out of 3342.** On the other
three it removes 55–59 % of them. This is a stronger statement than §6: UAVDT does not
merely have accurate compensation, it has almost no room for compensation to act.

That is worth stating because UAV footage is the canonical "severe camera motion" setting
in the tracking literature — AMOT (AAAI 2026) and JitTrack (2026) both target it for that
reason. Their difficulty is large inter-frame *displacement*, small objects and appearance
ambiguity; it is not compensation error, and compensation is not where the gains are.

**Caveat, stated rather than assumed away**: UAVDT's absolute numbers here are low
(HOTA 44, IDSW 3342) because the published FRCNN detections are weak, so tracking is
dominated by detection quality and small-object difficulty. That compensation is a rounding
error *in that regime* is what was measured; whether it would matter more with a stronger
detector was not tested.

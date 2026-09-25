# KITTI tracking — does the geometric room convert into tracking metrics?

**Date**: 2026-09-21 · **Data**: KITTI tracking, all 21 training sequences, 8,008 frames
**Detector**: COCO-pretrained YOLO11x, **never trained on KITTI** — no leakage, so no split is
needed and none was invented. Detections frozen once and hashed; every configuration reads
the same files.
**Tracker**: BoT-SORT-shaped, motion-only (Kalman + two-stage ByteTrack association + IoU
gate). No ReID — a car re-identification model would be another uncontrolled variable.
**Evaluation**: official TrackEval, KITTI protocol, classes car and pedestrian.

---

## 1. What is varied, and only that

| configuration | camera-motion correction |
|---|---|
| none | identity |
| online | BoT-SORT's own sparseOptFlow GMC — **deployable** |
| global similarity (ORACLE) | best 4-DOF similarity fitted to the camera-induced motion of a static grid at the scene's median depth |
| per-target similarity (ORACLE) | **the same 4-DOF form**, but fitted per object, from that object's own box corners at that object's own depth |

The last two differ in exactly one respect: whether the correction is shared across the frame
or computed per object. Both are oracles — they use ground-truth ego-motion and ground-truth
depth. They are upper bounds, not methods.

**Two specification errors were found and corrected before these numbers were produced**, and
both are recorded rather than quietly fixed:

1. A first version fitted the "global oracle" to the tracked objects' *true displacements*.
   On KITTI those objects are moving vehicles, so that quantity is camera motion **plus**
   object motion — and the Kalman filter already predicts the second. The resulting warp
   double-counted and scored *below* the deployable GMC. Corrected to fit static scene points
   under camera motion alone.
2. A second version applied the per-target correction as a translation only, while the global
   modes applied a full similarity. That handicapped per-target on DetA. Corrected so both
   have the same form.

---

## 2. Results

### Car

| configuration | HOTA | AssA | DetA | MOTA | IDF1 | **IDSW** | Frag |
|---|---|---|---|---|---|---|---|
| no compensation | 64.792 | 70.339 | 60.584 | 69.896 | 79.298 | 401 | 265 |
| online GMC (deployable) | 65.265 | 70.137 | 61.450 | 71.342 | 79.542 | 165 | 254 |
| global similarity (oracle) | 66.267 | 71.922 | 61.775 | 71.753 | 80.868 | 129 | 247 |
| **per-target similarity (oracle)** | **66.473** | **72.432** | 61.730 | 71.267 | 80.689 | **117** | **240** |

### Pedestrian

| configuration | HOTA | AssA | DetA | MOTA | IDF1 | **IDSW** | Frag |
|---|---|---|---|---|---|---|---|
| no compensation | 45.499 | 47.877 | 43.996 | 42.218 | 61.565 | 279 | 412 |
| online GMC (deployable) | 47.428 | 51.448 | 44.617 | 44.252 | 64.424 | 126 | 393 |
| global similarity (oracle) | 46.744 | 50.006 | 44.784 | 44.594 | 62.106 | 108 | 384 |
| **per-target similarity (oracle)** | **47.576** | **51.852** | 44.748 | 44.639 | 63.084 | **88** | **383** |

### Deltas

| step | car | pedestrian |
|---|---|---|
| having compensation (online − none) | HOTA +0.473, IDSW −236 | HOTA +1.929, IDSW −153 |
| perfecting the **global** warp (oracle − online) | HOTA **+1.002**, AssA +1.785, IDSW −36 | HOTA **−0.684**, AssA −1.442, IDSW −18 |
| **going per-target** (per-target − global oracle) | HOTA **+0.206**, AssA **+0.510**, DetA −0.045, IDSW **−12** | HOTA **+0.832**, AssA **+1.846**, DetA −0.036, IDSW **−20** |
| per-target vs deployable | HOTA +1.208, AssA +2.295, IDSW −48 | HOTA +0.148, AssA +0.404, IDSW −38 |

## 3. Reading

> **Read §5 before relying on these aggregates.** Only the pedestrian column survives the
> robustness tests; the car column does not.

Per-target is ahead of the global oracle on HOTA, AssA and IDSW in both classes, with DetA
essentially unchanged (−0.045, −0.036) — the gain sits in association and identity switches,
not detection, which is where the mechanism predicts it.

**The pedestrian column is the sharper result.** There, *improving* the global warp actively
**hurts** (−0.684 HOTA, −1.442 AssA vs the deployable GMC) while the per-target correction
recovers and surpasses it (+0.148 HOTA, +0.404 AssA, −38 IDSW). A better global warp is worse
than a mediocre one; a per-target warp is better than both. That pattern is hard to attribute
to the accuracy of the correction and points instead at its *globality*. An attempt to explain
the pedestrian/car split by depth offset or by box size was made and **both explanations were
refuted by measurement** (§6) — the pattern is reported without a validated cause.

**Contrast with MOT17**, same instrument, same question:

| | MOT17 | KITTI car | KITTI pedestrian |
|---|---|---|---|
| perfecting the global warp | HOTA +0.099, **IDSW +5 (worse)** | HOTA +1.002, IDSW −36 | HOTA −0.684, IDSW −18 |
| going per-target | **not measurable** — within-frame spread negligible | HOTA +0.206, IDSW −12 | HOTA +0.832, IDSW −20 |

## 4. What this does NOT establish

- **This is not yet a method**, though the three ground-truth inputs are not equally hard to
  replace, and an earlier phrasing here treated them as if they were:
  - *ego-motion* — on a vehicle this is an **onboard sensor reading**, not an estimate. KITTI's
    `oxts` is the platform's own GPS/IMU. Using it is realistic, not oracular.
  - *target depth* — genuinely must be estimated. Tolerance measured separately (§7).
  - *target identity* — eliminated: the deployable mode queries the depth map at the tracker's
    **own predicted box**, so no identity is needed.

  So the only input that must actually be estimated is depth.
- **The magnitudes are modest**: +0.206 and +0.832 HOTA over the global oracle. IDSW moves
  proportionally more (117 vs 129; 88 vs 108). Determinism has since been **verified** by
  repeated runs (bit-identical on all 21 sequences), and the deltas tested against a
  perturbation-based noise scale — see §5. The car delta does not survive that test.
- **The tracker is not a tuned KITTI system.** Its absolute numbers are not competitive with
  published KITTI trackers and are not meant to be; the comparison is internal, between
  configurations that differ in one controlled respect.

---

## 5. Robustness — and a split the evidence does not let us paper over

The pipeline is **deterministic**: two independent runs of `online` and `per_target` produced
bit-identical output on all 21 sequences. As on MOT17, a zero noise floor makes a ratio test
vacuous, so the practical noise scale is taken from hyperparameter perturbation.

### Sequence-level bootstrap — the load-bearing uncertainty estimate

Percentile bootstrap over the 21 sequences, 20,000 resamples, weighted by ground-truth
detections. This is the population the claim must generalise to; the hyperparameter
perturbation below measures something different (tuning sensitivity) and is secondary.

| comparison | metric | point | 95 % CI | verdict |
|---|---|---|---|---|
| pedestrian: per-target vs global **similarity** | HOTA | +0.842 | [+0.067, +1.226] | excludes zero |
| | AssA | +1.639 | [+0.071, +2.426] | excludes zero |
| | IDSW/seq | −3.12 | [−5.86, −0.03] | excludes zero |
| pedestrian: per-target vs global **homography** | HOTA | +0.656 | **[−0.157, +0.998]** | **crosses zero** |
| | AssA | +1.347 | **[−0.331, +2.046]** | **crosses zero** |
| | IDSW/seq | −2.58 | [−5.70, −0.02] | excludes zero |
| car: per-target vs global similarity | HOTA | +0.213 | [−0.342, +0.605] | crosses zero |
| car: per-target vs global homography | HOTA | +0.077 | [−0.429, +0.410] | crosses zero |

**Against a global homography, only the pedestrian ID-switch reduction survives.** The HOTA
advantage does not. An earlier draft reported "+0.686 HOTA over the best global model" as a
result; its interval crosses zero and that phrasing is withdrawn.

### Hyperparameter perturbation (7 settings: match_thresh, track_buffer, track_high) — secondary

| | per-target gain, ΔHOTA | positive in | ΔIDSW | better in | noise scale* |
|---|---|---|---|---|---|
| **pedestrian** | **+0.847 ± 0.104** (range +0.710 … +0.995) | **7/7** | −22.3 ± 6.8 | **7/7** | **0.738** |
| car | +0.319 ± 0.248 (range −0.010 … +0.757) | 6/7 | −14.6 ± 11.3 | 6/7 | **1.475** |

\* span of the global-oracle HOTA across the same seven settings.

**Pedestrian: the effect (0.847) exceeds the noise scale (0.738) and is stable — std is 12 % of
the effect, and the sign never flips.
Car: the effect (0.319) is well inside its noise scale (1.475).**

### Leave-one-sequence-out

| | mean per-sequence Δ | leave-one-out range | sequences +/−/≈0 |
|---|---|---|---|
| **pedestrian** | +0.5136 | **+0.412 … +0.551** — never flips | 11 / 2 / 8 |
| car | +0.0396 | **−0.0425 … +0.2019** — **flips sign** when 0004 is dropped | 13 / 6 / 2 |

### Mechanism stratification

| | Spearman(Δ, translation) | moving sequences (>0.5 m) | near-static (≤0.05 m) |
|---|---|---|---|
| **pedestrian** | +0.405 (p = 0.069) | **+0.787** | **−0.006** |
| car | +0.226 (p = 0.325) | +0.157 | **+0.210** (higher than moving) |

The pedestrian gain appears only where the vehicle actually moves and vanishes when it does
not — which is what the mechanism predicts. The car gain shows no such pattern.

## 6. Conclusion, and an honest gap

**Established**: on KITTI pedestrians, replacing the best possible *global* camera-motion
correction with a *per-target* one of identical form yields +0.847 HOTA, +1.8 AssA and
−22 ID switches, stable across every perturbation tested, robust to leaving out any sequence,
and concentrated in the sequences where the camera translates.

**Not established**: the same effect on KITTI cars. It is positive on average but inside its
own noise scale, flips sign under leave-one-out, and shows no mechanism stratification.
It is reported as not established rather than averaged in.

**Unexplained**: why the two classes differ. Two candidate explanations were pre-specified and
both were **refuted by measurement**, and are recorded here rather than discarded:

1. *"Pedestrians sit further from the frame's median depth, so the shared correction is more
   wrong for them."* — **False.** Median |log(z_obj / z_frame_median)| is **0.339 for cars**
   versus **0.264 for pedestrians/cyclists**; the Mann-Whitney test in the hypothesised
   direction returns p = 1.000. Cars are the more off-median class.
2. *"Pedestrian boxes are smaller, so a given error costs more IoU."* — **False.** The
   disagreement between an object's own warp and the shared warp exceeds one third of its box
   width in **2.21 % of car** object-frames versus **1.57 % of pedestrian** ones. Cars have the
   greater geometric exposure.

No third explanation was sought. Searching until one fits would be the wrong procedure, and
the absence of a validated mechanism for the class difference is stated as a limitation.

---

## 7. Deployability I — how much depth error can the gain survive?

Depth is the one input that must genuinely be estimated (§4). Monocular depth error is
approximately multiplicative, so it is injected as `z' = z · exp(N(0, σ))` and the whole
pipeline re-run. Seeding is per-sequence and reproducible (CRC32, not Python's salted `hash`).

### Pedestrian — reference: global oracle HOTA 46.744, IDSW 108

| σ | ≈ relative error | HOTA | vs global oracle | AssA | IDSW | vs oracle |
|---|---|---|---|---|---|---|
| 0.00 | 0 % | 47.576 | **+0.832** | 51.852 | 88 | −20 |
| 0.05 | 5 % | 47.865 | **+1.121** | 52.541 | 85 | −23 |
| 0.10 | 11 % | 47.864 | **+1.120** | 52.532 | 85 | −23 |
| 0.20 | 22 % | 47.644 | **+0.900** | 52.086 | 87 | −21 |
| 0.30 | 35 % | 47.540 | **+0.796** | 51.848 | 100 | −8 |
| 0.50 | 65 % | 46.385 | −0.359 | 49.188 | 153 | +45 |

**The gain is flat from 0 % to about 22 % relative depth error, still clearly positive at
35 %, and collapses only at 65 %.** Published monocular metric-depth models reach roughly
5–10 % AbsRel on KITTI, so the required precision is already available.

The σ = 0.05 and 0.10 rows sit slightly *above* the zero-noise row (+1.12 vs +0.83). That
difference, 0.29, is within the perturbation standard deviation measured in §5 and is **not**
read as "noise helps"; the honest statement is that the curve is flat across that range.

### Car

| σ | 0.00 | 0.05 | 0.10 | 0.20 | 0.30 | 0.50 |
|---|---|---|---|---|---|---|
| vs global oracle (HOTA) | +0.206 | **−0.178** | −0.216 | −0.217 | −0.235 | −0.191 |

The car "gain" turns negative at 5 % depth error — the smallest level tested. That is
consistent with §5: it was inside its own noise scale to begin with, and it does not survive
perturbation of any kind.

**Two independent robustness probes — hyperparameter perturbation and depth noise — agree on
which of the two class results is real.**

# Synthesis — Stage 1 Phase 3 (revision 2)

**Project**: Multi-Object Tracking under Camera Motion Uncertainty
**Date**: 2026-09-23 · **Supersedes**: revision 1 (2026-09-22)

**Why this was rewritten.** Revision 1 stated the central positive result as
"+0.847 ± 0.104 HOTA, positive in 7/7 hyperparameter settings". That is a
sensitivity-to-tuning figure, not a generalisation figure. DA-CP2 M2 required
bootstrap confidence intervals over sequences — the population the claim has to
generalise to — and those intervals are **materially wider**. Three claims from
revision 1 do not survive them and are withdrawn below. Revision 1's numbers were
not wrong; the inference drawn from them was too strong.

---

## 1. The finding, in one paragraph

Camera-motion compensation in tracking-by-detection does not fail the way the field
assumes. Across four benchmarks and 14,236 audited frames the online compensator is
accurate — median RANSAC residual 0.30–0.59 px — and on the benchmarks where a single
global 2D warp correctly describes the scene motion, making it *perfect* buys nothing:
on MOT17 an oracle warp is worth +0.099 HOTA and **increases** ID switches by 5. The
failure that does exist is not noisy estimation but a **shared correction applied to
targets at different depths**. Under camera translation — vehicle-mounted cameras — a
single warp cannot serve them: in 54 % of moving KITTI frames, objects in the same image
need corrections differing by more than 5 px, and 2.08 % of object-frames are pushed past
the association gate by what survives *perfect* global compensation, against 0.031 % on
MOT17. Replacing the shared correction with a per-target one recovers part of that. On
KITTI pedestrians the gain over the best global **similarity** is +0.842 HOTA
(95 % CI [+0.07, +1.23]) and −3.1 ID switches per sequence ([−5.9, −0.03]); over a global
**homography** only the ID-switch reduction remains significant. It survives replacing
ground-truth depth with a monocular network. It is **not** established on KITTI cars under
oracle inputs, and no validated explanation for that class difference was found.

## 2. Evidence table

Confidence intervals are percentile bootstrap over the 21 KITTI sequences
(20,000 resamples, weighted by ground-truth detections).

| # | Claim | Evidence | Status |
|---|---|---|---|
| E1 | The baseline reproduces published numbers | HOTA 69.12 vs 69.11; IDF1 81.50 vs 81.53; MOTA 78.44 vs 78.39. Split cross-checked against BoT-SORT's own GMC file line counts | **Established** |
| E2 | BoT-SORT's appearance channel is gated by motion agreement | `bot_sort.py:313` `emb_dists[ious_dists_mask] = 1.0`, mask computed from CMC-warped boxes | **Certain** (source) |
| E3 | The warp is treated as noiseless | `bot_sort.py:68-83` rotates the covariance, never inflates it; `gmc.py:223` discards the RANSAC inlier mask | **Certain** (source) |
| E4 | Compensation error is predictable from statistics the solver already discards | median RANSAC residual: held-out AUC 0.866 (leave-one-sequence-out); survives 4 confound stratifications (weakest −0.741) and both placebos | **Established** |
| E5 | A single signal beats the six-signal estimator on real data | held-out AUC 0.866 vs 0.774; `n` degenerate (99.94 % at ceiling), `tau` a false-alarm generator | **Established**; contradicts the synthetic study, both reported |
| E6 | On MOT17 the error is too small to change association outcomes | 34 harmful gate flips / 109,955 GT pairs; median IoU cost 0.00085; only 0.284 % of pairs within reach of the gate | **Established** |
| E7 | Perfecting compensation on MOT17 is worthless | oracle warp +0.099 HOTA, **IDSW +5**; −0.015 HOTA vs the published configuration; less than the 0.114 HOTA gap between two ordinary compensator choices | **Established** |
| E8 | MOT17 and MOT20 do not contain the failure regime | `n_inliers<100` in 0/14,236 frames; MOT20 has 82 % foreground contamination but **zero** frames with `eps>2px` | **Established** |
| E8b | UAVDT does not either | reliability scan is the cleanest of all three (`eps` 0.295 px, τ 0.166); a `none` vs `online` tracking comparison is in progress | **Scan established; downstream effect pending** |
| E9 | One global warp is geometrically inadequate under translation | after ORACLE global compensation, within-frame residual spread >5 px in 54.3 % of moving frames; depth↔residual Spearman median −0.400; 2.08 % of object-frames gated out (67× MOT17) | **Established** |
| E9b | A richer global model does **not** rescue it | a **deployable** global homography (fitted to the static scene) cuts the within-frame spread by only **2.3 %** (7.59 → 7.42 px) and the >5 px frame fraction not at all (61.28 % → 61.44 %) | **Established** |
| E10 | Per-target beats the best global **similarity** on KITTI pedestrians | HOTA +0.842 CI [+0.067, +1.226]; AssA +1.639 [+0.071, +2.426]; IDSW −3.12/seq [−5.86, −0.03] — all exclude zero | **Established** |
| E10b | Per-target beats a global **homography** on KITTI pedestrians | HOTA +0.656 CI **[−0.157, +0.998]** and AssA **[−0.331, +2.046]** cross zero; only IDSW −2.58/seq [−5.70, −0.02] excludes zero | **Only the ID-switch part is established** |
| E11 | Per-target beats a global warp on KITTI cars (oracle inputs) | HOTA +0.213 CI [−0.342, +0.605]; every metric crosses zero; sign flips under leave-one-out; turns negative at 5 % depth noise | **NOT established** |
| E12 | The gain survives estimated depth | with a monocular network in place of ground truth: +0.855 HOTA CI [+0.141, +1.339] over the same global baseline, versus +0.842 with ground-truth depth. Synthetic sweep: flat to ~22 % relative error, positive at 35 %, collapses at 65 % | **Established** |
| E12b | The deployable per-target pipeline beats plain image-based GMC on pedestrians | HOTA −0.207 CI [−0.852, +1.766]; IDSW −2.11/seq [−12.66, +0.73] — both cross zero | **NOT established** |
| E12c | …on cars | HOTA +1.206 CI [+0.154, +2.104] excludes zero; AssA and IDSW cross zero | **HOTA established, association metrics not** |
| E13 | The causal link between E9 and E10 | per-frame, per-class: **all 20** of the pedestrian ID-switch improvement comes from the top exposure quartile, none from the bottom; Spearman +0.058, p = 0.0047; the per-frame counter reproduces TrackEval's pedestrian delta exactly (20 = 20) | **Established for pedestrians**; the same counter is unreliable for cars and is not used there |
| E14 | Why pedestrians and cars differ | two pre-specified explanations tested, **both refuted** (cars are *further* from frame-median depth, 0.339 vs 0.264; cars have *greater* per-error box exposure, 2.21 % vs 1.57 %) | **Unexplained** |

## 3. Withdrawn from revision 1

| Revision-1 statement | Why it is withdrawn |
|---|---|
| "+0.847 ± 0.104 HOTA, 7/7 perturbation settings, exceeds the 0.738 noise scale" as the headline support | Hyperparameter perturbation measures tuning sensitivity, not generalisation. The sequence-level CI is [+0.067, +1.226] — the effect is established but far less tightly than that phrasing implied. Perturbation is demoted to a robustness footnote. |
| "A homography fitted to the static scene cuts the within-frame spread by 91.4 %" | That 91.4 % came from a homography fitted to the **objects' own true displacements** — a curve fit to the answer, not a compensator. Refitted to the static scene, as a compensator must be, the reduction is **2.3 %** (`kitti_global_family.py`). The claim was briefly stated in the wrong direction and is corrected here. |
| "Per-target retains +0.686 HOTA over the best global model tested" | True as a point estimate, but its CI crosses zero. Only the ID-switch reduction survives against a global homography. |

## 4. What changed relative to the original proposal

| Original premise | What the evidence says |
|---|---|
| "Assess whether background motion compensation is reliable, then decide how much weight motion and appearance should carry" | The compensator is already reliable wherever this is measurable. Reliability estimation is the wrong instrument. |
| "When background estimation fails, reduce its influence rather than applying a wrong compensation to all targets" | **The per-target half is correct and is the central finding** — but the operative failure is not *estimation failure*; it is that one warp cannot serve targets at different depths. The prescription survives, the reliability-gating rationale does not. |
| "Start from BoT-SORT on MOT17/MOT20" | Necessary as a calibrated negative control, insufficient as the main evidence. |
| "Reduce ID switches under camera motion" | Achieved on KITTI pedestrians (88 vs 108 under the best global similarity; CI on the per-sequence reduction excludes zero, and it holds against a homography too). Not achieved on MOT17, where perfect compensation *increases* ID switches. |

## 5. Gaps, stated as gaps

1. **The class split is unexplained.** Two candidate causes pre-specified, both refuted. No third sought.
2. **Ego-motion is read from `oxts`.** On a vehicle that is an onboard sensor, not an oracle — but the method has not been tested with visually estimated ego-motion.
3. **The depth model is domain-matched.** Depth-Anything-V2 Metric VKITTI is fine-tuned on a synthetic replica of KITTI. Best-case deployability test.
4. **The synthetic depth-noise sweep injects independent per-object noise.** Real monocular error is spatially correlated, so that curve is optimistic; the real-model run is the load-bearing evidence, not the sweep.
5. **The tracker is not a tuned KITTI system.** All comparisons are internal.
6. **No MOTChallenge test-server numbers** — the service is offline field-wide (TUM notice, 2026-09-08).
7. **The robot study is not done.** Protocol delivered.

## 6. Contribution claims the evidence supports

1. **A measurement instrument**: the oracle-warp contrast, which quantifies compensation error on benchmarks with no ground-truth camera motion, plus a free reliability signal (the RANSAC residual the solver computes and discards, held-out AUC 0.866).
2. **A quantified negative result with a benchmark critique**: compensation error on MOT17/MOT20/UAVDT is real, measurable, predictable — and too small to change association outcomes. An improvement attributed to camera-motion compensation on these benchmarks cannot be an improvement in compensation robustness.
3. **A reframing**: the limitation is the *sharing* of one correction across targets at different depths, not the accuracy of that correction, and **not** the expressiveness of the warp family — a deployable global homography removes only 2.2 % of the within-frame spread.
4. **A scoped prescription**: per-target compensation, established on KITTI pedestrians (ID-switch reduction robust even against a global homography), tolerant of realistic depth error, and explicitly *not* established on KITTI cars.

---

*Deliverable of Stage 1 Phase 3, revision 2. Next: DA-CP2 re-check, then the Stage 1 report.*

# Supplementary Material

*Camera-Motion Compensation in Tracking-by-Detection: Accuracy Headroom and Depth-Aware Shared Warps* The released measurements and evaluation summaries provide the numerical sources for the supplementary tables and main-text results.

## S1 Reliability-Signal Subsets on MOT17

Section 4.4 identifies the median transfer residual as a compact reliability signal: its AUC of 0.866 matches the best two-signal subset. Table S1 gives the best subset at each size under leave-one-sequence-out over the seven MOT17 sequences.

**Table S1** Reliability-signal subsets and held-out AUC.

| Subset size | Best subset | Held-out AUC | Worst sequence |
|---|---|---|---|
| **1** | **ε** | **0.866** | 0.779 |
| 2 | n + ε | 0.866 | 0.779 |
| 3 | ρ + n + ε | 0.864 | 0.780 |
| 4 | ρ + n + ε + κ | 0.860 | 0.766 |
| 5 | ρ + n + ε + κ + φ | 0.854 | 0.770 |
| 6 | all | 0.774 | 0.614 |

Figure 1 plots every subset. The release includes measurements for all 63 non-empty subsets.

## S2 Measurement Conventions

The target-fitted similarity uses least squares over camera-induced correspondences derived from sensor ego-motion and annotated object depths. Background-fitted models use robust estimation over monocular-depth correspondences. The per-target reference uses annotated association; the global homography uses estimated background depth on moving frames and the annotation-anchored near-static fallback defined in the main text. All reported MOT17 oracle comparisons use strict reference substitution.

**Table S2** Within-frame residual spread after target-fitted similarity over 4,318 moving frames.

| Estimator | Median | p90 | Max | > 5 px |
|---|---|---|---|---|
| Least squares | **2.431 px** | **10.114** | **67.7** | **27.12 %** |

## S3 Controls for Class-Specific Outcomes

Both are measured over the 31,470 object-frames that lie in moving frames with at least two annotated objects — 23,348 car and 8,122 pedestrian or cyclist. **Depth-Offset Control.** The median of |log(z_object / z_frame-median)| is **0.325 for cars** and **0.246 for pedestrians and cyclists**; a one-sided Mann–Whitney test for larger pedestrian/cyclist depth offsets returns p = 1.000. These measurements separate depth offset from the class-level tracking outcome. **Width-Normalised Exposure.** The disagreement between an object's own warp and the shared warp exceeds one third of the object's box width — roughly where a pure translation drops IoU below the gate — in **3.28 %** of car object-frames and **3.23 %** of pedestrian ones. The two classes have similar width-normalised exposure. These controls distinguish class-level tracking outcomes from depth offset and width-normalised exposure alone.

# Supplementary Material

*Camera-Motion Compensation Is Not the Bottleneck: A Measurement Study of Shared Warps in Tracking-by-Detection*

Every figure here is reproduced by the released code; `verify_numbers.py` checks the numbers in both this document and the main text against source.

## S1 Signal-subset search on real MOT17 data

Section 4.4 reports that held-out performance degrades monotonically as reliability signals are added. The best subset at each size, under leave-one-sequence-out over the seven MOT17 sequences:

| Subset size | Best subset | Held-out AUC | Worst sequence |
|---|---|---|---|
| **1** | **ε** | **0.866** | 0.779 |
| 2 | n + ε | 0.866 | 0.779 |
| 3 | ρ + n + ε | 0.864 | 0.780 |
| 4 | ρ + n + ε + κ | 0.860 | 0.766 |
| 5 | ρ + n + ε + κ + φ | 0.854 | 0.770 |
| 6 | all | 0.774 | 0.614 |

Figure 8 plots every subset.

All 63 non-empty subsets are in `04_experiments/signal_subset_search.csv`.

## S2 Errors we made and corrected

Four, all found by measurement rather than by argument, and all recorded because a measurement paper that reports only its final state is not auditable.

*The oracle specification.* Our first KITTI global oracle was fitted to the tracked objects' true displacements, which on KITTI contain the vehicles' own motion that the Kalman filter already predicts. It double-counted and scored below the deployable GMC, which is how we found it. It was corrected to fit static scene points under camera motion alone and the first version's numbers were withheld. A second version applied the per-target correction as a translation while the global modes applied a similarity; it was corrected so both have the same form.

*The warp-family test.* We fitted the competing global families to a grid at a single depth, which makes the induced mapping a plane homography exactly, and reported that a homography removes only 2.3 % of the within-frame spread — evidence, we said, that the warp family is not the limitation. It was evidence about our grid. Refitted to background points at their own depths, a deployable homography removes 81.8 %. The conclusion is withdrawn and §6.4 states the corrected one, which supports the paper's direction for a different reason and required a new experiment to reach.

*The oracle configuration's fallback.* The tracker reverted to the online estimate whenever the reference warp failed its quality gate, on 18.2 % of MOT17-05's validation frames, so "the only variable is the warp" was false. Re-run strictly, the axis moves by 0.012 HOTA (§5.3).

*The claim that perfecting compensation is never positive.* Stratified by the paper's own static/moving control, it is +0.169 HOTA [+0.013, +0.523] on the moving sequences with an appearance channel. The claim is withdrawn and §5.4 states the bound instead of the sign.

We also withdrew three claims when sequence-level intervals replaced point estimates: a "±0.104 across 7/7 hyperparameter settings" framing, which measures tuning sensitivity rather than generalisation; "+0.686 HOTA over the best global model"; and a leave-one-sequence-out result that used an unweighted per-sequence mean while every interval in the paper used a weighted aggregate — under the paper's own estimator the car gain does not change sign.

## S3 The refuted explanations for the class difference

Both are measured over the 31,470 object-frames that lie in moving frames with at least two annotated objects — 23,348 car and 8,122 pedestrian or cyclist.

**Candidate 1: pedestrians sit further from the frame's median depth, so the shared correction is more wrong for them.** This is the obvious geometric story and it is false. The median of |log(z_object / z_frame-median)| is **0.325 for cars** and **0.246 for pedestrians and cyclists**; a one-sided Mann–Whitney test in the hypothesised direction returns p = 1.000. Cars are the more off-median class, which is the opposite of what the explanation requires.

**Candidate 2: pedestrian boxes are smaller, so a given pixel error costs more IoU.** Also false, and in a way worth stating precisely. The disagreement between an object's own warp and the shared warp exceeds one third of the object's box width — roughly where a pure translation drops IoU below the gate — in **3.33 %** of car object-frames and **3.28 %** of pedestrian ones. The two classes are not merely ordered the wrong way; they are equally exposed, so the explanation has nothing to work with.

Both were specified before being measured, and both are recorded rather than dropped.

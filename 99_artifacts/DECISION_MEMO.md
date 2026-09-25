# Decision Memo — what this project should become

**Date**: 2026-09-20 · **Prepared for**: the Stage 1 Phase 2 checkpoint
**Status of the original plan**: the *method* claim is not supported on MOT17/MOT20.
The *measurement* work is solid and survives every adversarial test applied to it.

---

## 1. What is established, with the evidence

| Claim | Evidence | Strength |
|---|---|---|
| The baseline is reproduced | HOTA 69.12 vs published 69.11; IDF1 81.50 vs 81.53; MOTA 78.44 vs 78.39. Split independently cross-checked against BoT-SORT's own GMC file line counts | **Very strong** |
| The coupling defect exists in shipped code | `bot_sort.py:313` `emb_dists[ious_dists_mask] = 1.0`, where the mask is computed from CMC-warped boxes | **Certain** (source) |
| The warp is treated as noiseless | `bot_sort.py:68-83` rotates the covariance, never inflates it; `gmc.py:223` discards the RANSAC inlier mask | **Certain** (source) |
| Compensation error is predictable from free statistics | median RANSAC residual `eps`: held-out AUC 0.866 (leave-one-sequence-out), survives 4 confound stratifications (weakest −0.741) and both placebos | **Strong** |
| Compensation error is too small to matter on MOT17 | 34 harmful gate flips / 109,955 GT pairs; median IoU cost 0.00085; only 0.284 % of pairs within reach of the gate | **Strong** |
| Neither MOT17 nor MOT20 contains the failure regime | `n_inliers<100` in 0/14,236 frames; MOT20 has 82 % foreground contamination but zero frames with `eps>2px` | **Strong** |
| The published configuration is even cleaner than the one instrumented | file-GMC pooled median 0.516 px vs sparseOptFlow ~1.3 px | **Strong** |

Two findings that cut against the original plan and are reported as such:
- **`eps` alone beats the six-signal estimator** on real data (AUC 0.866 vs 0.774), reversing
  the synthetic result. The method gets simpler; the story about combining signals does not survive.
- **Much of the headline −0.928 correlation is between-sequence.** Within-sequence placebo
  reaches −0.748; per-sequence values are −0.60 to −0.79. The honest number to quote is the
  within-sequence one.

## 2. The three options

### Option A — publish the measurement study and the negative result as they stand

**Thesis**: camera-motion compensation error on the standard pedestrian MOT benchmarks is
measurable from statistics the tracker already computes and discards, is predictable, and is
**too small to change association outcomes** — and the benchmarks themselves do not contain
the failure regime the literature warns about.

- *Deliverables already complete*: baseline reproduction, oracle-contrast methodology,
  reliability estimator + validation, gate-flip measurement, benchmark regime audit,
  synthetic controlled study, robot protocol.
- *Remaining work*: writing only. No new experiments.
- **For**: rigorous, fully reproducible, directly extends the 2026 KAIST survey's critique into
  a specific and testable claim. Nothing in it is fragile.
- **Against**: a negative result with no method is a hard sell at Q1. Some reviewers will ask
  "so what should I do instead?" and the answer is currently "measure before you claim".
- *Venue realism*: plausible at evaluation-friendly journals; **unlikely** at Pattern
  Recognition / TCSVT without a method.

### Option B — extend to a benchmark where the regime exists, then decide (**recommended**)

Add one domain where camera motion is severe enough that compensation actually fails:

| Candidate | Why | Availability |
|---|---|---|
| **UAVDT / VisDrone-VID** | UAV ego-motion; AMOT (AAAI 2026) targets these precisely because motion is the problem | HuggingFace mirrors confirmed |
| **KITTI tracking** | vehicle-mounted, translation-dominated → a single 2D similarity is *wrong by construction* (parallax), a qualitatively different failure | source to be located |

Run the same instrument there — it is already written and validated — and measure whether
compensation error reaches the magnitude that changes association outcomes.

- **If yes**: the paper becomes *method + rigorous negative control*. "Reliability-aware
  compensation helps where compensation actually fails; here is the measurement that shows
  MOT17/MOT20 cannot test this, which is why prior work reports what it reports." That is a
  materially stronger paper than the original plan, and a realistic Q1 target.
- **If no**: Option A, with a much wider evidentiary base and a correspondingly stronger
  benchmark critique.
- *Cost*: dataset acquisition, a detector for that domain (or public detections), baseline
  reproduction in the new domain. Days, not weeks, on this hardware.
- *Risk*: the honest one — it may find the same thing again. That outcome is still publishable
  under Option A, so the downside is bounded.

### Option C — robot data first

Record the controlled dataset (protocol delivered), which supplies the one thing no public
benchmark has: ground-truth camera motion.

- **For**: the only setting where the reliability estimate can be *calibrated against true
  error* rather than against another estimate; a dataset contribution in its own right.
- **Against**: depends entirely on the user's recording timeline; a single-rig dataset may be
  dismissed as a demo unless paired with public-benchmark results.
- *Best used as*: a component of Option B, not a replacement for it.

## 3. Recommendation

**Option B**, then reassess.

Reasons:
1. The instrument is built and validated. Applying it to a new domain is cheap relative to
   what it has already cost.
2. It converts a negative result into a *scoped* result, which is what makes it publishable:
   "here is when compensation reliability matters, and here is the measurement proving it does
   not on the benchmarks everyone uses."
3. The downside is bounded — a second negative strengthens Option A rather than wasting it.
4. It directly answers the question a reviewer of Option A would ask.

## 4. What must NOT happen

Recorded so it can be checked later (DA-CP1 R3):

- **Do not re-run the power gate until it passes.** The pre-committed response to a failed
  gate is a pivot, not a retry.
- **Do not tune `theta_iou_max`, `beta`, or `sigma_scale` to manufacture a MOT17 gain.** The
  K3 invariant exists precisely to make such a gain detectable as an artefact.
- **Do not quote −0.928 as per-frame predictive power.** Quote the within-sequence figure.
- **Do not drop the synthetic result** because real data disagreed with it, or vice versa.
- **Do not present the six-signal estimator** now that the data has rejected it.

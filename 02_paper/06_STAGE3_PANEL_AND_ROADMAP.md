# Stage 3 — Five-seat review panel, and the Stage 4 revision roadmap

**Date**: 2026-09-23/24 · **Panel**: Journal-Fit, Methodology (R1), Domain (R2), Perspective (R3), Devil's Advocate
**Execution**: five independent contexts, paper-only, no access to the authors' internal records and
no sight of each other's reports. Role separation is not a claim of independent error processes.

## Verdicts

| Seat | Verdict | Headline |
|---|---|---|
| Journal-Fit | Major revision | "reframe first, then send out"; would be desk-returned on placeholder metadata alone |
| R1 Methodology | Major revision | "If findings 1–5 are addressed, I would expect to recommend acceptance" |
| R2 Domain | Major revision, **close to reject** | both headline claims substantially anticipated by uncited work |
| R3 Perspective | Major revision | "my objection is to what they concluded they were measuring" |
| Devil's Advocate | not rejection | "the central claim is half-supported, and the half that is supported is not the half the abstract leads with" |

Four of five seats independently raised the same Critical: **the positive result's comparator is worse
than the compensator the tracker already ships, and the abstract does not say so.**

---

## Part 1 — Findings tested by re-measurement

Every claim below was checked by running something, not by argument.

### R1/DA: the "oracle" configuration fell back to the online warp — **CONFIRMED, claim survives**

`rac_tracker.py` reverted to the online estimate whenever the reference failed its quality gate:
**76 of 418 val-half frames on MOT17-05** (18.2 %), the sequence where the two warps differ most.
Table 3's "the only variable is the warp" was false. A `reference_strict` mode was added and the
axis re-run with the reference used wherever it exists:

| | with fallback | strict | Δ |
|---|---|---|---|
| motion-only oracle HOTA | 69.105 | **69.093** | −0.012 |
| motion-only IDSW | 144 | **147** | +3 |
| appearance oracle HOTA | 69.344 | **69.350** | +0.006 |
| appearance IDSW | 165 | **164** | −1 |

The disclosure is required; the measurement is not affected. The strict oracle is marginally *worse*.

### DA: §6.4's warp-family test was degenerate — **CONFIRMED, and the conclusion is WITHDRAWN**

The static grid sat at **one depth**, so the induced mapping is a plane homography exactly and
`findHomography` recovered it to **6.2 × 10⁻⁶ px**. The 8-DOF model carried the same depth
information as the 4-DOF one. The 2.3 % figure was an artefact of the construction.

Refitted to background points at their **own estimated depths** (monocular depth map, annotated
objects masked out, ~422 background samples per frame, same 4,318 frames):

| Measured at object centres | online GMC | oracle sim (1 depth) | deployable sim | **deployable homography** |
|---|---|---|---|---|
| median residual | 2.026 px | 0.537 px | 4.832 px | **0.479 px** |
| median within-frame spread | 8.673 px | 5.878 px | 7.607 px | **1.388 px** |
| frames with spread > 5 px | 65.12 % | 54.31 % | 62.09 % | **13.36 %** |

**A deployable global homography removes 81.8 % of the within-frame spread**, not 2.3 %.
"A richer warp family is not the fix" is false and is withdrawn.

### …and the replacement finding is stronger

Tracking with the depth-aware homography, applied per track:

| KITTI pedestrian | HOTA | AssA | IDSW |
|---|---|---|---|
| online GMC (spread 8.67 px) | **47.428** | **51.448** | 126 |
| depth-aware global homography, four corners (spread 1.39 px) | 46.884 | 50.275 | 115 |
| depth-aware global homography, contact point only (UCMCTrack's mechanism) | 46.779 | 50.057 | 114 |
| single-depth global homography (spread 5.88 px) | 46.890 | 50.264 | 106 |
| **per-target** | **47.576** | **51.852** | **88** |

**The deployed estimator has 6.3× the within-frame residual spread of the depth-aware homography and
tracks better than it.** That is §5's thesis, established directly on KITTI against true ego-motion,
with a 6× difference rather than MOT17's sub-pixel one. The reframing survives in a sharper form:
the limitation is not the expressiveness of the shared warp — a homography demonstrably represents
the depth variation — but that a *shared* correction does not do what a per-object one does.

### R3: is the cheap fix "anchor the shared warp at your targets' depth"? — **TESTED, ruled out**

Pedestrians are systematically nearer than cars on KITTI (per-sequence medians 13.4 vs 18.9 m,
12.9 vs 57.0, 10.1 vs 18.2 …), and the all-class median sits near the car depth, so the hypothesis
was plausible. Global similarity refitted at the target class's own median depth:

| | HOTA | vs scene-median global |
|---|---|---|
| pedestrian-anchored, pedestrians | 46.948 | +0.241 [−0.031, +0.699] — crosses zero |
| car-anchored, cars | 66.029 | **−0.667 [−1.885, −0.040]** — worse |

Recovers about a quarter of the pedestrian gain and none of the car gain. The cheap alternative
is ruled out, which strengthens the per-target argument rather than weakening it.

### R1/DA: "IDSW per sequence" is mislabelled — **CONFIRMED**

It is a GT-detection-weighted mean of per-sequence deltas, not a per-sequence rate.

| | true total | true per-sequence | printed as "per sequence" |
|---|---|---|---|
| KITTI ped, per-target − global | −20 over 21 seq | **−0.95** | **−3.12** |
| MOT17, having compensation | −198 over 7 seq | **−28.29** | **−13.23** |

Wrong in both directions, and it is in the abstract.

### R1/DA: effective sample size — **CONFIRMED**

Kish ESS on the actual GT-detection weights: **MOT17 3.79 of 7** (one sequence 44.9 %);
**KITTI pedestrian 3.05 of 21** (one sequence 52.9 %, six sequences with zero pedestrian ground
truth). KITTI car 10.47 of 21. Weighted vs unweighted on the pedestrian headline:
+0.842 [+0.067, +1.226] against **+0.514 [+0.190, +0.883]**.

### DA: stratify MOT17 by the paper's own static/moving control — **CONFIRMED, and §5.4's claim is revised**

| perfecting compensation | all 7 | **moving only (4)** | static only (3) |
|---|---|---|---|
| motion-only | +0.137 [−0.042, +0.492] | **+0.0004 [−0.043, +0.052]** | +0.200 [−0.058, +1.119] |
| + appearance | −0.094 [−0.460, +0.133] | **+0.169 [+0.013, +0.523]** | −0.214 [−1.826, −0.061] |

Two consequences. The motion-only bound on the sequences that actually have camera motion is an
**order of magnitude tighter** than the pooled one — this is the strongest form of the paper's own
claim and it was not reported. And with the appearance channel enabled the moving-only interval
**excludes zero**, so §5.4's "the value of perfecting compensation is not positive in either
configuration" is **false** and is withdrawn. The effect is +0.169 HOTA, carried mostly by
MOT17-05, and the static stratum is significant in the opposite direction — which is itself
evidence that the n = 7 percentile interval is not calibrated.

### R1/DA: frame exclusion is outcome-correlated — **CONFIRMED**

| sequence | frames | excluded | rate |
|---|---|---|---|
| MOT17-02 / 04 / 09 | 2,172 | 0 | 0 % |
| **MOT17-05** | 836 | **206** | **24.6 %** |
| MOT17-10 / 11 / 13 | 2,301 | 15 | 0.7 % |

Excluded frames carry a median online residual of **1.066 px against 0.557 px** for retained ones.
§3.2 promised a per-sequence table and none exists. Mitigating, and verified by the Devil's
Advocate: adding the excluded frames back moves the gate-flip result from 0.031 % to **0.033 %**
(34 → 37 harmful). The combinatorial bound survives its own selection problem; the §4.2 magnitudes
and the §4.3 AUC do not, and must be reported both ways.

### R1/R3: the mechanism check uses the wrong statistic — **CONFIRMED, replaced**

Spearman ρ = +0.058 explains 0.34 % of variance and reads as nil. A paired permutation test over
the 2,377 pedestrian frames: observed top-quartile improvement **+20**, null mean 4.99, sd 3.70,
**p = 0.0001**. The same test on cars: −20 observed, p = 0.946 — i.e. significant in the wrong
direction, consistent with the counter being unreliable there.

### C-3 carried over from Stage 2.5: leave-one-out used a different estimator

Under the paper's own GT-weighted aggregation, neither class changes sign
(ped [+0.332, +1.025], car [+0.096, +0.393]). The "car gain flips sign" claim was already withdrawn.

### R2: MOT20's arm rests on the statistic §4.2 declares insufficient — **being closed by measurement**

The oracle contrast is running on MOT20 (`oracle_contrast.py --root .../MOT20/train`). MOT20-01
returns `ref_ok = 1.000`, median online/reference disagreement **0.409 px**. When all four
sequences finish, MOT20 will have the same external check as MOT17 and the "internal-consistency
only" objection is answered rather than conceded.

---

## Part 2 — Findings that require rewriting rather than re-measuring

### R2 (Critical): the central negative claim has far less unclaimed territory than stated

Verified from primary sources:

- **Yang et al. (2026)** — the survey this paper quotes in §2.3 for its protocol critique — states in
  its own abstract: *"Starting from a minimal baseline tracker, we fairly evaluate the contributions
  of each method across diverse datasets"*, camera motion compensation among them. Contribution 2's
  "a question the field has not posed quantitatively" is wrong as written.
- **BoT-SORT itself (2022)**: *"In scenes with a high density of dynamic objects, the estimation of the
  camera motion may fail… Wrong camera motion may lead to unexpected tracker behavior."* §2.4's
  priority attribution to McByte++ is wrong; the tracker under study said it first.
- **Deep OC-SORT (2023)**: *"CMC improves performance on MOT17-val and DanceTrack-val sets while
  providing no improvements on MOT20-val, which is captured from static cameras."*
- **UCMCTrack (AAAI 2024)**: MOT20 CMC delta exactly 0.0; **KITTI car −2.9 HOTA, pedestrian −0.9**,
  diagnosed by its authors as *"inaccuracies present in the CMC parameters"* — a published claim in
  direct tension with this paper's, and one it is well placed to rebut with true ego-motion.
- **ImprAsso (CVPRW 2023), BoostTrack (MVA 2024), Adžemović (2025)** all state or act on the MOT20
  conclusion.

*Disposition:* the surviving novel claim is the **oracle bound** — what a *perfect* warp would be
worth — which R2 and DA both confirm nobody has measured. Contribution 2 is restated to claim that
and the gate-flip instrument, not priority over the qualitative finding.

**R2 withdrew its own Finding 10** after checking BoT-SORT's Table 1: the paper's +0.888 HOTA for
having compensation reproduces BoT-SORT's published +0.94 to within 0.06. The replacement point
stands: the published value spans +0.09 to +1.53 depending on estimator and baseline, so §5.7's
injunction must be scoped to sparse-optical-flow GMC on a BoT-SORT-shaped tracker.

### R2 (Critical): EMAP substantially anticipates the prescription

**Mahdian, Jani, Soufi Enayati & Najjaran, EMAP** (arXiv:2404.03110, IROS 2024): a Kalman
reformulation that *"decouples the impact of camera rotational and translational velocity from the
object trajectories"* using *"camera motion and depth information"*, integrated with **OC-SORT, Deep
OC-SORT, ByteTrack and BoT-SORT**, evaluated on **KITTI MOT**, reporting IDSW reductions of 73 % and
21 % and HOTA gains above 5 %. Verified from the arXiv record.

*Disposition:* EMAP is cited, its position stated, and §6–§7 recast as a *controlled measurement of
why* per-object compensation helps — the per-frame exposure-quartile verification, which EMAP has
nothing equivalent to — rather than as the introduction of the idea.

### R2 (Critical): §1's covariance argument does not compose — **CONFIRMED in source**

`BoTSORT.update` uses `iou_distance` + `fuse_score` + `embedding_distance`. The Mahalanobis path
`matching.fuse_motion` is present in `tracker/matching.py` but **commented out** at `bot_sort.py:318`.
The covariance never enters the association cost, so inflating it would change the Kalman gain and
next frame's prediction, not this frame's gate. Separately, "a similarity preserves the covariance's
magnitude" is wrong — it scales it by s². §1 is rewritten around the gating coupling alone.

### R3/R1: KITTI ego-motion is a sensor estimate, not truth

An OXTS RT3003 at 10 Hz composed through the calibration chain. At f ≈ 721 px, 1 mrad ≈ 0.7 px —
larger than the 0.101 px oracle residual quoted in §6.2 and comparable to 0.537 px. §3.4's "against
truth, not against a better estimate" and §7.1's "not an estimate" are both overstated and an
error-propagation sweep is owed.

### R2: §5.6's explanation of the UAVDT null is factually wrong

UAVDT's own attributes: front 23,601 / side 17,672 / bird 10,737 images; altitude medium 24,059 /
low 14,644 / high 2,032. "High-altitude nadir-ish viewing … nearly uniform depth" describes a
minority of the data. R2's corrected mechanism favours the paper: UAVDT tracks **vehicles confined
to a road plane**, so a plane-induced homography is near-exact even under translation — the scene is
planar, not equidistant. §6.1's rotation/translation dichotomy needs the third case: **translation
over a planar scene**, which is also what §6.4's new homography result shows for KITTI.

### All seats: presentation and scope

Zero figure citations and 13 uncaptioned tables in the typeset source (fixed); figure order not by
first mention; abstract 400 words with "34 of 109,955" where 34 is the harmful subset of 55; two
estimators quoted side by side in the abstract; placeholder metadata and `[URL]` for a repository
the paper's contribution depends on; §9.3 promises a robustness note that does not exist; §9.2
cross-references §5.4 for UAVDT (it is §5.6); ~25 missing references including the entire SORT
lineage, RANSAC, Shi–Tomasi, Lucas–Kanade, ECC, plane+parallax (Irani & Anandan 1998), and the
correct KITTI citation for the oxts stream (Geiger et al., IJRR 2013).

---

## Part 3 — What the revision keeps

Per the author's decision, the per-target prescription is retained and strengthened rather than cut.
It now rests on:

1. the geometric necessity (§6.2/§6.3), unchanged and verified against true ego-motion;
2. a demonstration that the alternatives do **not** substitute for it — a depth-aware global
   homography with 6× less residual spread, a depth-anchored global similarity, and the deployed
   GMC itself all fall short, and each was tested rather than argued;
3. the per-frame mechanism verification, now with a permutation test at p = 0.0001;
4. survival under estimated depth.

and it is stated with its limits in the abstract: not established against plain image-based GMC on
pedestrians, not established on cars, and anticipated in direction by EMAP.

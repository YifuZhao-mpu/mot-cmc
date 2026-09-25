# Devil's Advocate — Checkpoint 2 (Stage 1 Phase 3)

**Agent**: `devils_advocate_agent`
**Reviews**: `SYNTHESIS.md` and every artifact in `99_artifacts/`
**Mandate**: cherry-picking check, confirmation-bias detection, logic-chain validation,
alternative explanations. Critical-severity issues block.

---

## 0. Verdict

### **REVISE** — 1 Critical, 3 Major, 3 Minor

The negative results (E6–E8) are solid and I cannot break them. The positive result (E10) has
one hole large enough that a competent reviewer will put the whole mechanism story in doubt,
and one untested alternative that could deflate the central claim.

---

## 1. CRITICAL

### C1 — Your own measurement contradicts your mechanism, and the synthesis files it under "unexplained"

The mechanism is: *a single global warp cannot serve targets at different depths, so the
correction must be per-target.* Everything in E9 supports it geometrically.

Then E13 reports, from your own data:

| | cars | pedestrians/cyclists |
|---|---|---|
| distance from the frame's median depth, median \|log(z/z̄)\| | **0.339** | 0.264 |
| own-warp vs shared-warp disagreement above ⅓ box width | **2.21 %** | 1.57 % |

**Cars are the class the mechanism predicts should benefit MORE.** They sit further from the
depth the shared warp is anchored to, and a given correction error costs them more IoU. Yet
cars show **no established gain** (E11) while pedestrians show a robust one (E10).

Filing this as "unexplained" understates it. It is not a missing footnote — **it is a direct
prediction of the stated mechanism, tested, and falsified.** As written, the paper would claim
a mechanism and then present, in its own tables, the strongest available evidence against it.

A reviewer will find this in ten minutes.

**Required, at minimum:** stop presenting the depth-spread mechanism as the explanation for the
tracking gain. The geometric result (E9) and the tracking result (E10) are both real, but the
causal link between them is **not** established, and the class comparison actively cuts against
it. The honest structure is:

- E9: a single global warp is geometrically inadequate under translation. *Measured.*
- E10: per-target compensation improves pedestrian tracking on KITTI. *Measured.*
- The inference "E10 happens **because of** E9" — **unsupported, and contradicted by the class
  comparison.**

**Or**, do the work that could rescue it: measure whether the per-frame per-class gain
correlates with that class's own within-frame residual spread *in that frame*. That is a direct
test of the causal link and it has not been run. If it correlates, the mechanism survives with
the class puzzle as a secondary anomaly. If it does not, the mechanism claim should be dropped
and the tracking gain reported as an empirical finding without a validated cause.

---

## 2. MAJOR

### M1 — "No 2D warp can be correct" was never tested against a homography

E9's entire framing is that the compensation *model* is inadequate. But only two models were
tested: a rotation-only homography and a 4-DOF similarity. **A full 8-DOF homography was never
fitted.**

This matters because a homography exactly represents the motion of *a plane* under arbitrary
camera motion, including translation. KITTI scenes are dominated by the ground plane and by
facades. UCMCTrack (AAAI 2024) is built on precisely this observation. It is entirely possible
that a per-frame homography absorbs most of what the similarity cannot, in which case the
correct conclusion is not "no 2D warp works" but "**the 4-DOF similarity that BoT-SORT happens
to use** is too weak" — a much narrower and less interesting claim.

The test is cheap: you already have ground-truth 3D points and ego-motion. Fit a homography to
the same static grid and recompute the within-frame residual spread. **Until that is run, E9's
headline is overstated.**

### M2 — The noise scale is a proxy, and the pedestrian margin is not large against it

The "noise scale" is the span of the global-oracle HOTA across seven hyperparameter settings:
0.738 for pedestrian. The pedestrian effect is 0.847. That is a **1.15× margin**, not a
comfortable one, and the comparison is not a significance test — it compares an effect to the
sensitivity of a *different* quantity to a *different* perturbation.

There is no confidence interval on any HOTA figure in this project. TrackEval reports point
estimates; a bootstrap over sequences would be straightforward and is absent.

**Required:** bootstrap the per-sequence deltas (21 sequences, resample with replacement) and
report a CI for the pedestrian gain. If the CI crosses zero, E10's status drops from
"established" to "suggestive" and the synthesis must say so.

### M3 — E8's UAVDT claim rests on a weaker instrument than the MOT17 claim

MOT17's "no room" conclusion is supported by three independent lines: geometry (IoU cost),
combinatorics (gate flips), and an actual tracking experiment with an oracle warp. **UAVDT has
only the reliability scan.** No oracle contrast, no gate-flip count, no tracking experiment.

The synthesis lists E8 as covering MOT17, MOT20 *and* UAVDT at equal strength. It does not.
Either run at least the tracking comparison on UAVDT (`none` vs `online` is available without
ground-truth ego-motion) or downgrade the UAVDT claim to "the compensation estimates are
clean; the downstream effect was not measured".

---

## 3. MINOR

- **m1** — The pedestrian result draws on 16 of 21 sequences, and 8 sequences show |Δ| ≤ 0.01.
  The effect comes from ~11 sequences and two are negative. Report n explicitly wherever the
  aggregate appears; "21 sequences" overstates the support.
- **m2** — Absolute ID-switch counts are small (88 vs 108). A 20-event difference over 8,008
  frames deserves a per-sequence breakdown in the paper, not just an aggregate.
- **m3** — The depth-noise study injects *independent* multiplicative noise per object. Real
  monocular depth error is **spatially correlated** — a whole region is wrong together. The
  tolerance curve is therefore optimistic in a way that is not stated. The real-depth-model run
  now in progress addresses this, but the synthetic curve should carry the caveat.

---

## 4. What I could not break

Stated so the criticism above is calibrated — these survived deliberate attack:

- **E1** the baseline reproduction (0.01 HOTA).
- **E2/E3** the two code-level defects — they are quotations, not interpretations.
- **E6/E7** the MOT17 negative result. Three independent methods agree, the effect is bounded
  three different ways, and the oracle makes IDSW *worse*. I tried to find a configuration where
  MOT17 shows room and there is none.
- **E5** the signal-selection reversal, with leave-one-sequence-out and a diagnosed cause.
- **The process record.** Two specification errors and two refuted hypotheses are documented
  rather than buried, and the first-version numbers were withheld. That is the correct
  behaviour and it is rare.

---

## 5. Required actions before the Stage 1 report

| # | Action | Severity |
|---|---|---|
| 1 | Either run the within-frame causal-link test, or drop the claim that E10 is caused by E9 | **CRITICAL** |
| 2 | Fit a full homography and recompute the within-frame spread; rewrite E9's headline accordingly | Major |
| 3 | Bootstrap CI over sequences for the pedestrian gain | Major |
| 4 | Downgrade the UAVDT claim or run the tracking comparison | Major |
| 5 | Report n (sequences contributing) wherever aggregates appear | Minor |
| 6 | Per-sequence IDSW breakdown | Minor |
| 7 | State the spatial-correlation caveat on the synthetic depth-noise curve | Minor |

*Checkpoint 2 verdict: **REVISE**. The Stage 1 report may not be written until item 1 is
resolved — by measurement or by retraction.*

---

## 6. C1 resolution — the causal link was tested, and it holds for pedestrians

Per (sequence, frame, class): *exposure* = median disagreement between each object's own
local warp and the frame's shared warp; *improvement* = per-frame ID switches under the
global oracle minus those under per-target. KITTI's own evaluation class sets are used
(Van/Truck are ignore regions for `car`, Person_sitting/Cyclist for `pedestrian`); an earlier
run that pooled them produced spurious switches and was discarded.

### Pedestrian — **mechanism confirmed**

| exposure quartile | median exposure | IDSW global | IDSW per-target | improvement | per 1k frames |
|---|---|---|---|---|---|
| Q1 | 0.019 px | 115 | 115 | **0** | 0.00 |
| Q2 | 0.309 px | 57 | 59 | −2 | −3.37 |
| Q3 | 0.914 px | 59 | 57 | +2 | +3.37 |
| **Q4** | **3.584 px** | 49 | 29 | **+20** | **+33.67** |

Spearman(exposure, improvement) = **+0.058, p = 0.0047**.
**All 20 of the improvement comes from the quartile where the shared warp serves pedestrians
worst; the best-served quartile gains exactly zero.**

**Counter validation**: this per-frame counter yields a total delta of 280 − 260 = **20**,
matching TrackEval's 108 − 88 = **20** exactly.

### Car — this test cannot settle it

The same counter gives 244 vs 292 (per-target worse by 48) while TrackEval gives 129 vs 117
(per-target better by 12) — **opposite signs**. The counter agrees with TrackEval on
pedestrians and disagrees on cars, and the cause is identifiable: the tracker labels COCO
car/truck/bus alike as `Car`, while KITTI treats Van/Truck as ignore regions for the car class.
TrackEval removes those with Hungarian matching plus distractor handling; this counter's greedy
argmax does not, so truck boxes steal matches from real cars and manufacture switches.

**A counter demonstrated to be unreliable for a class is not used to draw a conclusion about
that class.** The car row is recorded as **inconclusive under this test**, not as contradicting
the mechanism.

### Effect on the synthesis

E10's causal basis is no longer an inference — for pedestrians it is measured, and the gain is
concentrated exactly where the mechanism says it must be. The class difference (E13) remains
unexplained, and the car class now has three separate reasons to be reported as not
established: inside its noise scale, sign-flipping under leave-one-out, and not assessable by
this test.

---

## 7. M1 / M2 / M3 resolution

### M1 — resolved, and it overturned a claim made in the course of resolving it

A full 8-DOF homography was fitted and compared. **Two successive statements were wrong
before the correct one was reached, and both are recorded rather than quietly replaced:**

1. Original framing: *"no 2D warp can be correct under translation."*
2. First correction, after fitting a homography to the **objects' own true displacements**:
   *"a homography absorbs 91.4 % of the within-frame spread, so the limitation is just
   BoT-SORT's weak 4-DOF model."* — **wrong**, because that homography is a curve fit to the
   answer, not something a compensator could estimate.
3. Correct: a **deployable** homography, fitted to the static scene as a compensator must be,
   cuts the within-frame spread by **2.3 %** (7.59 → 7.42 px) and leaves the >5 px frame
   fraction unchanged (61.28 % → 61.44 %). Superseded note: these figures were first
   obtained ad hoc (2.2 %, 6.23 → 6.10 px on a looser frame filter); they are now produced
   by `kitti_global_family.py` on exactly the frame and object filter of the oracle study,
   so the oracle row reproduces 5.878 px exactly. The conclusion is unchanged.. In tracking it is worth +0.146 HOTA against the
   global similarity, about 18 % of the per-target gain.

**The limitation is the sharing of one correction across targets at different depths — not
the expressiveness of the warp family.** M1's concern was legitimate and the answer, once
measured correctly, supports the original direction for a different reason than originally
given.

### M2 — resolved, and it withdrew three claims

Percentile bootstrap over 21 sequences, 20,000 resamples, weighted by GT detections:

| comparison | HOTA | 95 % CI | verdict |
|---|---|---|---|
| pedestrian: per-target vs global **similarity** | +0.842 | [+0.067, +1.226] | excludes zero |
| pedestrian: per-target vs global **homography** | +0.656 | **[−0.157, +0.998]** | **crosses zero** |
| pedestrian: deployable per-target vs plain online GMC | −0.207 | **[−0.852, +1.766]** | **crosses zero** |
| car: per-target vs global similarity (oracle inputs) | +0.213 | [−0.342, +0.605] | crosses zero |
| car: deployable per-target vs plain online GMC | +1.206 | [+0.154, +2.104] | excludes zero |

ID switches survive more often than HOTA: the pedestrian reduction excludes zero against
both the similarity (−3.12/seq) and the homography (−2.58/seq).

`SYNTHESIS.md` revision 2 withdraws: the "±0.104, 7/7 settings" headline framing, the 91.4 %
homography figure, and "+0.686 HOTA over the best global model".

### M3 — resolved; the UAVDT claim is now stronger than it was, not weaker

`none` vs `online` on 20 UAVDT sequences with its own published detections: **+0.163 HOTA
and +5 ID switches out of 3342.** Compensation does essentially nothing there, against
−55…−59 % of ID switches on MOT17 and both KITTI classes. E8b is upgraded from "scan only"
to established, with the caveat that UAVDT's weak published detections dominate its absolute
numbers.

### Revised verdict: **PASS**

All four blocking and major items were resolved by measurement. Three of the four changed a
stated conclusion, and two of those changes were downward. The minor items (m1–m3) are
reporting requirements carried into the manuscript, not blockers.

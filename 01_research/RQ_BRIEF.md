# RQ Brief — Stage 1 Phase 1 (deep-research, full mode)

**Project**: Multi-Object Tracking under Camera Motion Uncertainty
**Generated**: 2026-09-20
**Agent**: `research_question_agent`
**Status**: DRAFT — pending Devil's Advocate Checkpoint 1 + user confirmation

---

## 1. Problem Statement (evidence-anchored)

Tracking-by-detection (TBD) trackers associate detections to tracks using a cost matrix built from
motion proximity and appearance similarity. When the camera moves, predicted track boxes drift in the
image plane, so most modern trackers insert a **camera motion compensation (CMC)** step — typically a
global affine/homography estimate between consecutive frames — between Kalman prediction and association.

**BoT-SORT** (Aharon et al., 2022; arXiv:2206.14651) is the canonical instance. Its §3.2 states the
motivation verbatim:

> "In a dynamic camera situation, the bounding box location in the image plane can shift dramatically,
> which might result in increasing ID switches or false-negatives […] Trackers in static camera scenarios
> can also be affected due to motion by vibrations or drifts caused by the wind, as in MOT20, and in very
> crowded scenes ID-switches can be a real concern."

It estimates the affine matrix `A^k_{k-1}` via keypoint extraction + sparse optical flow + RANSAC
(OpenCV video-stabilization GMC), then warps **every** track's predicted state by that single matrix.

### 1.1 The defect this project targets

Two facts, both documented in the primary sources, combine into a failure mode that no published method
treats quantitatively:

**(a) The compensation estimate is not always trustworthy.** Safdarnejad et al. (arXiv:1603.03968) show
sequential GMC "suffers from temporal drift […] due to either error accumulation or **sporadic failures of
motion estimation at a few frames**", and that performance "deteriorate[s] on real-world unconstrained
videos with **predominant foreground or uniform background**". MOT20's defining property — dense crowds —
is exactly the predominant-foreground regime.

**(b) BoT-SORT's fusion rule makes a bad compensation actively self-defeating.** Its association cost is
(BoT-SORT Eqs. 12–13, verbatim):

```
d̂cos_ij = 0.5 · dcos_ij   if (dcos_ij < θemb) ∧ (diou_ij < θiou)
        = 1                otherwise                                  (12)

C_ij     = min{ diou_ij , d̂cos_ij }                                   (13)
θiou = 0.5 ,  θemb = 0.25
```

The appearance cost `d̂cos` is **gated by the motion cost**: it is admitted only when `diou_ij < θiou`.
A wrong compensation pushes the warped prediction away from the true detection, so `diou_ij` rises above
`θiou`, and the appearance term is set to 1 — i.e. **rejected**. The consequence is a coupling defect:

> *When camera motion compensation fails, BoT-SORT disables the appearance channel precisely in the
> frames where appearance is the only surviving evidence.*

This is a mechanism-level hypothesis, stated so it can be falsified by measurement (see §4).

**(c) A second, independent defect: the warp is treated as noiseless.** Verified in the released code,
`bot_sort.py:68–83` (`STrack.multi_gmc`):

```python
R    = H[:2, :2];  R8x8 = np.kron(np.eye(4), R);  t = H[:2, 2]
mean = R8x8.dot(mean);  mean[:2] += t
cov  = R8x8.dot(cov).dot(R8x8.transpose())      # similarity transform — uncertainty PRESERVED
```

The covariance is *rotated*, never *inflated*. The tracker is therefore exactly as confident after a
possibly-wrong warp as it was before it, and its gating distances stay just as tight. Meanwhile
`gmc.py:223,284` calls `cv2.estimateAffinePartial2D(prevPoints, currPoints, cv2.RANSAC)` and **discards the
returned inlier mask** — the information needed to know whether the warp deserves that confidence is computed
and thrown away.

Two defects, both verified at code level: *appearance is suppressed by corrupted motion evidence* (b), and
*the corruption is never admitted into the uncertainty model* (c).

---

## 2. Research Questions

**RQ (main).** Can the *reliability of the camera-motion estimate itself* be quantified online from the
statistics the CMC solver already produces, and propagated into the association decision, so that identity
switches under camera motion, target crossing, and temporary occlusion are reduced relative to a
compensation-unaware baseline — **without changing the detector**?

**SQ1 (attribution, revised after DA-CP1).** ~~Are ID switches concentrated in low-reliability frames?~~
**How many ID switches are *causally attributable* to compensation error** — i.e. present under the online
estimate `A_k` but absent under a reference warp `A*_k` (odometry ground truth for the robot study; offline
batch alignment as an analysis-only instrument on MOT17/MOT20)? A bare correlation between low `r` and IDSW
is rejected as evidence: low-`r` frames are also blurry, fast and crowded, which raises IDSW through channels
unrelated to the warp. *(Kill-switch, see §6.)*

**SQ2 (mechanism).** Is the coupling defect in §1.1(b) real? Specifically: among ID switches occurring in
low-reliability frames, what fraction had a correct appearance match available that was suppressed by the
`diou < θiou` gate?

**SQ3 (method).** Does a continuous, spatially-varying reliability estimate — used to (i) shrink the applied
transform toward identity, (ii) inflate motion-cost uncertainty, and (iii) relax the appearance gate —
reduce IDSW and improve AssA/IDF1 over BoT-SORT under *fixed detections*, and do the gains concentrate in
low-reliability frames as the mechanism predicts?

---

## 3. Scope Boundaries

| In scope | Out of scope |
|---|---|
| Online 2D TBD association under a moving/vibrating camera | End-to-end / transformer trackers (MOTR-family) |
| CMC reliability estimation from existing solver statistics | Learning a better homography estimator |
| MOT17, MOT20 (pedestrian), fixed public detections | Detector design, detector retraining |
| Per-frame and per-target reliability | Multi-camera / 3D MOT / sensor fusion (IMU, LiDAR) |
| Controlled robot-recorded validation set (user-collected) | Real-time embedded deployment optimisation |

**Fixed-detector constraint (user-mandated, and independently supported).** The 2026 KAIST survey
(arXiv:2609.08265) makes exactly this critique of the field: modules "are often evaluated under inconsistent
protocols, with different baseline trackers, hyperparameters, and datasets. Such inconsistencies obscure the
genuine contribution of each module." All comparisons in this project hold detections byte-identical.

---

## 4. Novelty Position — HONEST ASSESSMENT

⚠️ **The claim "we are first to notice that CMC can fail" is NOT available.** It is already taken.

### 4.1 Closest prior art (verified against primary sources)

| Work | What it does | Why the gap survives |
|---|---|---|
| **McByte++** (arXiv:2608.15688, 2026-08) §3.5 "Conditional CMC" — **closest** | Verbatim: applies CMC "only when the estimated global motion satisfies a set of reliability criteria designed to prevent degenerate transformations"; criteria "ensure that the estimated affine transform is physically plausible and does not induce excessive scaling or translation"; otherwise "proceeds without applying camera motion correction". Holds last reliable estimate. | (i) **Plausibility guard, not a reliability measurement** — no inlier/residual statistics, no published formula or threshold; (ii) **binary** apply/skip, not continuous; (iii) **global per-frame**, not per-target; (iv) **never enters the cost matrix** — reliability decides only *whether to warp*, never how motion and appearance are weighed; (v) sports broadcast domain (SoccerNet/SportsMOT), not MOT17/MOT20. |
| **IMM-JHSE** (arXiv:2409.02562, Expert Syst. Appl.) | Puts the homography and its dynamics into the track state; IMM mixes **static vs. dynamic camera motion models**; removes "explicit influence of camera motion compensation techniques on predicted track position states". | Model-*selection* uncertainty (is the camera moving?), not estimate-*quality* uncertainty (is this estimate trustworthy?). Replaces CMC rather than auditing it. Reports only "competitive performance on MOT17, MOT20". |
| **UCMCTrack** (AAAI 2024, arXiv:2312.08952) | Avoids frame-by-frame CMC entirely — one uniform compensation parameter per sequence, ground-plane Kalman + Mapped Mahalanobis Distance. | Orthogonal route: *avoid* CMC. Confirms the problem matters; does not assess reliability. |
| **EMAP** (arXiv:2404.03110, IROS'24) | Reformulates the KF to decouple camera rotational/translational velocity from object trajectories. | Builds a *better* compensation; no notion of when the estimate should be distrusted. |
| **AMOT** (AAAI 2026, arXiv:2508.01730) | Appearance-guided bi-directional spatial consistency matrix (AMC) + motion-aware track continuation. | Adaptation is driven by appearance consistency, **not** by CMC reliability. UAV benchmarks (VisDrone/UAVDT/VT-MOT-UAV). |
| **TRGMC** (arXiv:1603.03968) | Temporally robust GMC via keypoint congealing. | Improves GMC; the source of our failure-rate evidence, not a competitor in association. |

### 4.2 The surviving contribution space

1. **Quantitative continuous reliability** `r ∈ [0,1]` from geometric-verification statistics the CMC solver
   already computes (inlier ratio, inlier count, residual dispersion, linear-part conditioning, temporal
   consistency, foreground contamination) — replacing ad-hoc plausibility guards with a published, ablatable formula.
2. **Spatially-varying / per-target reliability** instead of one global binary switch — directly answering
   the user's requirement that a failed estimate must not be applied identically to every target.
3. **Propagation into the association cost**, in particular *relaxing the appearance gate* to repair the
   coupling defect of §1.1(b). No prior work connects compensation reliability to the motion↔appearance
   trade-off.
4. **Reliability-stratified evaluation** — reporting gains conditioned on measured `r`, which turns the
   contribution from "a number went up" into a tested causal mechanism.

**Required framing in the manuscript**: *the harm of unconditional compensation has been recognised and
handled by ad-hoc binary guards; we give the first quantitative treatment that measures compensation
reliability continuously, spatially, and propagates it into the association decision.*

---

## 5. FINER Assessment

| Criterion | Score | Evidence-anchored justification |
|---|---|---|
| **F**easible | **HIGH** | 4×A800-80GB available; fixed public detections remove detector training; the reliability signals are byte-free by-products of the existing RANSAC call. Main risk is dataset acquisition (motchallenge.net unreachable — see §7). |
| **I**nteresting | **HIGH** | Targets an acknowledged-but-unquantified failure mode; McByte++'s unspecified criteria are an explicit invitation. |
| **N**ovel | **MODERATE** | Downgraded from HIGH after finding McByte++ §3.5. Novelty now rests on *quantitative + spatial + cost-propagating*, not on problem identification. This must be stated plainly in the paper; overclaiming here is the single largest reviewer risk. |
| **E**thical | **HIGH** | Public pedestrian benchmarks; robot recording needs a participant-consent protocol (drafted in Stage 1 Phase 2 deliverable). Dual-use (surveillance) — Responsible Use Statement required. |
| **R**elevant | **HIGH** | Moving-camera MOT underpins robotics, ADAS, UAV; the 2026 survey ranks CMC among the core TBD components. |

**Overall: PROCEED, with the novelty claim explicitly narrowed.**

---

## 6. Falsification Criteria (pre-committed)

These are declared *before* any experiment, and are binding.

| # | Test | Outcome that kills or redirects the project |
|---|---|---|
| K1 | Oracle-warp attribution (§3.0 I1) + confound conditioning (I2) + placebo (I3). | If attributable IDSWs are negligible, **or** enrichment vanishes under I2, **or** survives under placebo I3 → premise false; redirect. |
| K2 | Measure the coupling defect (SQ2). | If <10% of low-`r` IDSWs had a suppressed-but-correct appearance match → the mechanism story is wrong; the method must be re-derived or the paper reframed as pure uncertainty modelling. |
| **K5** | **Power gate** (§3.0.1): headroom ceiling vs. noise floor. | If `N2 < 3×N1`, MOT17/MOT20 aggregates cannot carry the paper → pivot to robot study + stratified results, or add a high-camera-motion benchmark. Decided **before** the ablation runs. |
| K3 | Ablation at `r ≡ 1`. | The method must reduce **exactly** to BoT-SORT. If it does not, gains are confounded by re-tuning rather than by reliability. |
| K4 | Reliability-stratified gains (SQ3). | If gains are uniform across `r` strata, the improvement is not coming from the claimed mechanism. Report this honestly rather than suppressing the stratification. |

---

## 7. Known Risks (carried into the Methodology Blueprint)

| Risk | Status | Mitigation |
|---|---|---|
| **MOTChallenge evaluation service is OFFLINE field-wide** (TUM notice, page Last-Modified 2026-09-08, verified verbatim) | **RESOLVED — reclassified** | Earlier reading of "unreachable" was a local SOCKS-proxy artefact; direct access works. The real situation: *"The evaluation server, submissions and user accounts are offline… The dataset archives remain available at their existing addresses… The leaderboards have been preserved as a static archive"* (state of 16 April 2026, incl. raw result files + per-benchmark CSV). Consequences: (a) official MOT17.zip/MOT20.zip **are** downloadable — authoritative source used instead of mirrors; (b) test-server submission is impossible **for everyone**, so half-val protocol is now the field-wide norm rather than a deficiency of this work; (c) the static archive supplies published per-sequence results for comparison without submission. |
| Novelty narrower than initially assumed | ACKNOWLEDGED (§4) | Explicit differentiation table in Related Work; do not claim problem-discovery. |
| MOT20 is largely static ⇒ small CMC effect | OPEN | BoT-SORT's own text says MOT20 has wind-induced vibration and that IDSW matters there; K1 will settle it empirically. If MOT20 shows no effect, report that as a negative result and lean on MOT17 + robot data. |
| Gains may be within seed/tuning noise | OPEN | Multi-seed runs where stochastic; report variance; K3 guards against re-tuning artefacts. |
| Robot dataset depends on user execution | ACCEPTED | Protocol + annotation spec delivered by pipeline; paper structured so the robot study is an additive section. |

---

## 8. Sub-questions → Paper Section Mapping (forward handoff)

| Sub-question | Paper section | Evidence type |
|---|---|---|
| SQ1 | §4 Experiments — *Failure prevalence analysis* | Descriptive statistics over train-half |
| SQ2 | §4 — *Mechanism analysis (coupling defect)* | Counterfactual counting of suppressed matches |
| SQ3 | §4 — *Main results + reliability-stratified ablation* | Fixed-detection comparison, K3/K4 |

---

*Deliverable of Stage 1 Phase 1. Next: `research_architect_agent` → Methodology Blueprint; then Devil's
Advocate Checkpoint 1.*

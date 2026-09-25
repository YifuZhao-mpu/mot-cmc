# Camera-Motion Compensation Is Not the Bottleneck: A Measurement Study of Shared Warps in Tracking-by-Detection

**Yifu Zhao**^1^ · **Xiaofan Zou**^2^ · **Junhao Wei**^1^ · **Yanxiao Li**^1^ · **Haochen Li**^1^ · **Sio-Kei Im**^3^ · **Yapeng Wang**^1,\*^ · **Xu Yang**^1^

^1^ Faculty of Applied Sciences, Macao Polytechnic University, Macao 999078, China
^2^ School of Mechanical and Electrical Engineering and Automation, Shanghai University, Shanghai 200444, China
^3^ Macao Polytechnic University, Macao 999078, China

\* Corresponding author: yapengwang@mpu.edu.mo

| Author | ORCID | E-mail |
|---|---|---|
| Yifu Zhao | 0009-0004-2363-9269 | p2523269@mpu.edu.mo |
| Xiaofan Zou | 0009-0005-5995-3150 | xiaofanz@shu.edu.cn |
| Junhao Wei | 0009-0006-0553-2032 | p2312195@mpu.edu.mo |
| Yanxiao Li | 0009-0008-3389-1619 | p2525981@mpu.edu.mo |
| Haochen Li | 0009-0000-8213-5854 | p2523372@mpu.edu.mo |
| Sio-Kei Im | 0000-0002-5599-4300 | marcusim@mpu.edu.mo |
| Yapeng Wang | 0000-0002-1085-5091 | yapengwang@mpu.edu.mo |
| Xu Yang | 0000-0002-7037-3609 | xuyang@mpu.edu.mo |

---

## Abstract

Tracking-by-detection trackers compensate camera motion with a single two-dimensional warp applied to every predicted track, and a recurring assumption is that handling this warp's failures would reduce identity switches. We measure what that could be worth, and find the assumption misdirected in a way that points at a better correction. On MOT17, on the sequences that actually have camera motion, replacing the online estimate with a non-causal oracle warp is worth **−0.04 HOTA (95 % CI [−0.20, +0.05])** without an appearance channel and **+0.19 [+0.05, +0.52]** with one, against **+3.43 [+1.01, +5.52]** for having a working compensator at all; the error it removes changes the association gate's decision for 55 of 109,955 ground-truth pairs, 34 of them harmfully. Against an offline reference we verify that compensation is accurate on MOT17 and MOT20 — including on the sequence that puts 82 % of its keypoints on pedestrians, where the disagreement is 0.76 px — and that its error is predictable, for free, from the RANSAC residual the solver already discards. On KITTI, where the camera translates, a shared four-degree-of-freedom warp is genuinely inadequate: after the best such warp that could be fitted to the targets themselves, objects in one frame still need corrections differing by more than 5 px in 54.3 % of moving frames. The missing argument is **depth**, not per-object treatment. A global homography fitted to background points at their monocularly estimated depths — reading no annotations — cuts the within-frame residual spread from 8.67 px to **1.37 px**, beats the compensator the tracker ships by **+1.19 HOTA [+0.26, +1.92]** on cars, and commits **85 pedestrian identity switches against 126**. A per-target correction, given ground-truth depth and ground-truth association, adds nothing on top of it (−0.01 [−0.53, +0.45] on cars, +0.42 [−0.03, +1.00] on pedestrians), while a placebo that applies the same per-object corrections to the wrong objects is worse than applying none at all — the correction carries object depth, and a global model that has depth suffices to deliver it. The cost is a depth network at 65× a compensation call. All measurement code and data are released, together with a script that recomputes the paper's numbers from source.

**Keywords** Multi-object tracking · Camera motion compensation · Evaluation methodology · Benchmark analysis · Identity switches · Reproducibility

---

## 1 Introduction

One line in a widely used tracker motivated this work.

In BoT-SORT's association step (Aharon et al., 2022), after every track's Kalman prediction has been warped by the estimated camera motion, the appearance cost is admitted only when the motion cost agrees:

```python
ious_dists      = matching.iou_distance(strack_pool, detections)   # after the CMC warp
ious_dists_mask = (ious_dists > self.proximity_thresh)             # 0.5
emb_dists[emb_dists > self.appearance_thresh] = 1.0
emb_dists[ious_dists_mask] = 1.0        # appearance rejected because motion disagreed
dists           = np.minimum(ious_dists, emb_dists)
```

If the warp is wrong, the warped prediction moves away from the true detection, `ious_dists` rises above the threshold, and the appearance term is set to 1 — rejected. The appearance channel is disabled in exactly the frames where it would be the only surviving evidence. Meanwhile the solver that produced the warp, `cv2.estimateAffinePartial2D(..., cv2.RANSAC)`, returns an inlier mask that the code discards: the information needed to judge whether the warp deserves to gate anything is computed and thrown away.

That suggests a clean hypothesis. Camera-motion compensation fails; those failures suppress the appearance channel; identity switches follow. The prescription follows too — estimate the reliability of the warp and let it modulate the association.

The hypothesis is testable, and we tested it. It is wrong, and the way it is wrong turns out to be more useful than the method would have been.

A second observation that we initially built on does not survive inspection, and we record it because it is a natural thing to believe. BoT-SORT's warp application rotates each track's covariance and never inflates it, so the filter is no less confident after a possibly-wrong warp than before. That is true as written, but it cannot reach the association gate: in the released tracker the Mahalanobis path `matching.fuse_motion` is commented out, and the cost matrix is built from IoU, a score fusion and the appearance embedding only. Inflating the covariance would change the Kalman gain, and hence the *next* frame's prediction, not this frame's gate. Trackers whose association does read the covariance — DeepSORT and its descendants, UCMCTrack, StrongSORT's motion-cost term — would behave differently, and the family already has a confidence-adaptive idiom for it in NSA-Kalman (Du et al., 2021). The coupling in the code block above is the real one, and it is the only one we build on.

### 1.1 What we found

**Compensation is accurate, by an external standard.** Across MOT17, MOT20 and UAVDT the online estimator's median transfer residual is 0.295–0.592 px, and the catastrophic regime the literature describes — degenerate fits from weak texture or foreground domination (Safdarnejad et al., 2015) — is essentially absent. A residual is an internal-consistency statistic, so we also measure both pedestrian benchmarks against an offline reference: median disagreement is 0.150 px on MOT17's static sequences, 1.309 px on its moving ones, and 0.839 px across all 8,927 frames of MOT20, whose maximum over the whole benchmark is 2.73 px. MOT20-05 puts 82 % of its inliers on pedestrians and still disagrees by 0.756 px: contamination is not error.

**Its error is predictable, from a signal that is already free.** The median transfer residual of the inlier set, which the solver computes and the tracker discards, separates high-error from low-error frames with a held-out AUC of 0.866 under leave-one-sequence-out validation, though that figure is biased downward by a frame filter we describe in §3.2.

**And it is worth little.** On MOT17 we bound the effect three ways. Geometrically, the median IoU cost of compensation error is 0.00085, and only 0.284 % of ground-truth pairs sit close enough to the gate for an error of that size to move them across. Combinatorially, the gate's decision changes for 55 of 109,955 pairs, 34 of them harmfully. Empirically, on the four sequences that have camera motion, a non-causal oracle warp is worth −0.037 HOTA with a 95 % upper bound of **+0.05** without an appearance channel and +0.189 [+0.050, +0.517] with one — against **+3.426 [+1.007, +5.523]** for having a working compensator at all.

**The same holds on UAVDT**, the canonical severe-camera-motion benchmark, where switching compensation on changes 5 identity switches out of 3,342.

**Where a shared warp really is inadequate, what it is missing is depth.** On KITTI, after the best four-degree-of-freedom warp that could be fitted to the targets themselves, objects in one frame still need corrections differing by more than 5 px in 54.3 % of moving frames, and 2.08 % of object-frames are pushed past the association gate. We initially concluded that no global family could fix this, and published that conclusion internally on an experiment whose static grid sat at a single depth — which makes the induced mapping a plane homography exactly, so an eight-degree-of-freedom model carried no more depth information than a four. §6.4 records the correction.

**A global homography that has depth removes most of it, and it is deployable.** Fitted to background points at their monocularly estimated depths, with the tracker's own detections masked out and no annotation read at any point, it reduces the within-frame residual spread from 8.673 px to **1.370 px** and the fraction of badly-served frames from 54 % to 13 %. In tracking it beats the compensator BoT-SORT ships by **+1.187 HOTA [+0.262, +1.922]** on cars, and on pedestrians it commits **97 identity switches against 126** — 85 when applied through each box's contact point, the fewest of any configuration we ran.

**Per-target correction adds nothing on top of that.** Given ground-truth depth *and* ground-truth association, a per-object correction is −0.006 [−0.530, +0.446] against the depth-aware homography on cars and +0.424 [−0.032, +1.002] on pedestrians; both cross zero, and on pedestrians it commits more identity switches than the contact-point homography. The +0.842 HOTA it enjoys over a *depth-blind* global similarity is real and is not evidence for per-object treatment; it is evidence that the shared warp was missing depth.

**The effect is depth and not perturbation.** Permuting which object's correction goes to which track within a frame — the same corrections, the same magnitudes and directions, only the pairing destroyed — is worse than applying no per-object correction at all, by 3.58 HOTA on cars [+2.20, +4.96] and 25.6 weighted identity switches per sequence. Whatever the correction carries, it is object-specific and it is what depth determines.

### 1.2 Contributions

1. **A bound on what compensation accuracy could be worth.** Not whether compensation helps — that is known, and §2 reports five published measurements — but the residual headroom once a working compensator is in place, which is what a paper proposing a more robust compensator implicitly claims. On MOT17 with camera motion present it is −0.04 HOTA with a 95 % upper bound of +0.05 motion-only and +0.52 with appearance. We know of no prior measurement of this quantity (§5).
2. **Two instruments that make it measurable**: an oracle-warp contrast that bounds compensation error on benchmarks with no ground-truth camera motion, and a gate-flip count that asks whether the error changes an association *decision* rather than how large it is (§3).
3. **A diagnosis and a deployable remedy on KITTI.** The limitation of a shared warp is that it takes no depth argument, not that it is shared. The geometry is the classical plane-plus-parallax result (Irani & Anandan, 1998); what is new is the quantification, the demonstration that supplying depth to a *global* homography removes 82 % of the residual spread, and that this converts into tracking gains over the deployed compensator without any per-object machinery (§6).
4. **A negative result about per-object correction**, which is the direction we and the prior work we cite had assumed was necessary: given the depth-aware global warp, per-object correction adds nothing measurable, and the per-object configuration that appears to win over a depth-blind baseline needs ground-truth association to do it (§6.5, §6.6).

We are not the first to observe that compensation can fail. BoT-SORT's own limitations section says it, and we quote it in §2. Nor are we the first to correct with depth: EMAP (Mahdian et al., 2024) does so on this benchmark with this base tracker, per object. What we add is the measurement that the per-object part is unnecessary.

---

## 2 Related Work

### 2.1 Where compensation entered tracking-by-detection

Tracking-by-detection associates detections to tracks through a cost matrix combining motion proximity and appearance similarity. The lineage runs from SORT (Bewley et al., 2016) — Kalman filter plus Hungarian assignment on IoU — through DeepSORT (Wojke et al., 2017), which added an appearance embedding and a Mahalanobis motion gate, to ByteTrack (Zhang et al., 2022), which recovers low-confidence detections in a second association pass, and BoT-SORT (Aharon et al., 2022), which is ByteTrack plus camera-motion compensation, a reparameterised Kalman state and an IoU–ReID fusion.

Camera motion entered this lineage as a correction inserted between the Kalman prediction and the association. BoT-SORT states the reason plainly: "predicting the correct location of the bounding box may fail due to camera motion, which leads to low overlap between the two related bounding boxes and finally to low tracker performance. We overcome this by adopting conventional image registration to estimate the camera motion."

Not every strong tracker takes that route. OC-SORT (Cao et al., 2023) reaches competitive results on MOT17, MOT20, DanceTrack and KITTI with no compensation module, absorbing camera motion through an observation-centric re-update of the track state instead.

### 2.2 The compensators that are actually deployed

Two families are in use. **Sparse-flow GMC** — Shi–Tomasi corners (Shi & Tomasi, 1994) tracked by pyramidal Lucas–Kanade (Lucas & Kanade, 1981; Bouguet, 2001) and fitted by RANSAC (Fischler & Bolles, 1981) — is what BoT-SORT and Deep OC-SORT use, and is what this paper audits. **ECC** (Evangelidis & Psarakis, 2008), a direct intensity-alignment method, is what StrongSORT (Du et al., 2023), BoostTrack (Stanojević & Todorović, 2024) and UCMCTrack (Yi et al., 2024) use. The distinction matters for §4: ECC has no RANSAC stage and therefore no inlier residual, so the free reliability signal we identify does not exist for it.

BoT-SORT's own limitations section identifies the failure mode this paper set out to exploit, in 2022, in the tracker we instrument:

> "In scenes with a high density of dynamic objects, the estimation of the camera motion may fail due to lack of background keypoints. Wrong camera motion may lead to unexpected tracker behavior."

Several papers report what compensation is worth, and the published values differ by more than an order of magnitude depending on the estimator and the baseline. BoT-SORT's Table 1 gives +0.94 HOTA and +1.62 IDF1 on MOT17 for adding its sparse-flow GMC — the figure our §5.3 reproduces to within 0.06 HOTA. Deep OC-SORT (Maggiolino et al., 2023) reports +1.53 HOTA on MOT17-val from compensation alone and states:

> "We find that CMC improves performance on MOT17-val and DanceTrack-val sets while providing no improvements on MOT20-val, which is captured from static cameras."

That is the qualitative form of our MOT20 result, published in 2023. Our contribution on MOT20 is not the sign of the effect but an external measurement of the compensator's error there, which §4.2 supplies and which no prior work reports.

### 2.3 Handling unreliable compensation

**McByte++** (Stanczyk et al., 2026, §3.5) applies compensation conditionally:

> "Camera motion compensation is applied only when the estimated global motion satisfies a set of reliability criteria designed to prevent degenerate transformations. These criteria ensure that the estimated affine transform is physically plausible and does not induce excessive scaling or translation that could collapse or explode bounding boxes. When the estimated motion does not meet these conditions, the tracker proceeds without applying camera motion correction."

This is a plausibility guard rather than a reliability measurement: no inlier or residual statistic is used, no formula or threshold is published, the decision is binary and global per frame, and it never enters the cost matrix. Its domain is sports broadcast footage.

**IMM-JHSE** (Claasen & de Villiers, 2026) places the homography and its dynamics inside the track state and uses an interacting-multiple-model filter to mix static and dynamic camera-motion models. This is model-*selection* uncertainty — is the camera moving? — rather than estimate-*quality* uncertainty.

**NSA-Kalman** (Du et al., 2021), adopted by StrongSORT and Deep OC-SORT, scales the observation noise by detection confidence. It is the family's existing confidence-adaptive idiom, and it is the reason §1 does not present covariance inflation as an unexploited gap.

### 2.4 Leaving the image plane, and depth-aware 2D tracking

The reframing in §6 belongs to a line of work that treats depth as the missing argument of a 2D correction.

**UCMCTrack** (Yi et al., 2024) abandons per-frame compensation altogether: it projects each box's contact point onto the ground plane, runs the Kalman filter in ground coordinates, associates by a mapped Mahalanobis distance, and uses one compensation parameter per sequence. A contact point on a known ground plane is already a per-target range measurement, obtained from calibration with no depth network. Its KITTI-test results are directly relevant to this paper: adding ECC compensation to it *costs* 2.9 HOTA on cars (77.1 → 74.2, AssA 77.2 → 71.7) and 0.9 on pedestrians (55.2 → 54.3), and its authors attribute this to "the inaccuracies present in the CMC parameters." Section 6 measures that attribution directly and finds against it: on KITTI a *more accurate* shared warp does not track better.

**EMAP** (Mahdian et al., 2024) is the closest prior work to our §6–§7 prescription. It reformulates the Kalman filter to decouple camera rotational and translational velocity from object trajectories using camera motion and depth, evaluates on KITTI with OC-SORT, Deep OC-SORT, ByteTrack and BoT-SORT as base trackers, and reports identity-switch reductions of 73 % and 21 % and HOTA gains above 5 %. The direction of our prescription is therefore not new. What §6 adds is the controlled comparison that isolates *sharing* as the operative variable — a per-target correction of identical functional form to the global one, against a depth-aware global homography and a target-depth-anchored global similarity — together with a per-frame verification of where the gain comes from.

On aerial footage, **AMOT** (Ma et al., 2026) adapts association using appearance-guided bidirectional spatial consistency; its adaptation is driven by appearance agreement rather than by compensation reliability, and it is the closest recent work to §5.6's benchmark. **SparseTrack** (Liu et al., 2025) and **DepthMOT** (Wu & Liu, 2024) use depth differently: the first decomposes crowded scenes into pseudo-depth bands for cascaded association, the second estimates depth and camera pose end to end and reports gains on VisDrone and UAVDT. **UTrack** (Solano-Carrillo et al., 2024) argues for homography-based compensation over the affine approximation for fast camera motion and evaluates on MOT17, MOT20, DanceTrack and KITTI.

The underlying geometry is classical. That rotation induces a depth-independent image homography while translation induces a depth-dependent residual is the plane-plus-parallax decomposition (Irani & Anandan, 1998), and the survey of moving-camera background modelling by Chapel and Bouwmans (2020) treats plane-plus-parallax as a named category. Section 6 does not rediscover this; it quantifies it on a tracking benchmark and asks whether the quantity predicts tracking outcomes.

### 2.5 Evaluation methodology

HOTA (Luiten et al., 2021) decomposes tracking quality into detection and association components and is the primary metric we report. A 2026 survey of tracking-by-detection (Yang et al., 2026) makes the methodological critique this paper acts on — that modules "are often evaluated under inconsistent protocols, with different baseline trackers, hyperparameters, and datasets", so that "such inconsistencies obscure the genuine contribution of each module" — and acts on it itself, evaluating camera-motion compensation among other modules from a minimal baseline tracker across datasets. We adopt the same discipline, with byte-identical detections across every compared configuration.

### 2.6 Our position

We are not first to observe that compensation can fail: BoT-SORT is, in the paper we instrument. We are not first to report that it contributes little on a static-camera benchmark: Deep OC-SORT is. We are not first to correct per object using depth: EMAP is, on the same benchmark and with the same base tracker.

What we contribute is a measurement none of them makes. All of the above compare *having* compensation with *not having* it. None asks what a **perfect** warp would be worth — the headroom that remains once a working compensator is in place, which is the quantity a paper proposing a more robust compensator is implicitly claiming. Section 5 bounds it, on the benchmark where camera motion is present, at +0.05 HOTA motion-only and +0.52 with an appearance channel. Section 6 then shows on KITTI that this is not a small-effect artefact of a benign benchmark: where the shared-warp residual is large, driving it down by a factor of six still does not improve tracking, and what does is making the correction per target.

## 3 Measurement Instruments

Four instruments, each built so that its own failure modes are visible.

### 3.1 Instrumented compensation

BoT-SORT's compensation call returns an inlier mask that the code discards. We reimplement the estimator so that the mask, the inlier residuals, the correspondence counts and the inlier positions are recorded, while the returned warp is unchanged.

That last property is load-bearing. Over synthetic sequences with known inter-frame motion, the instrumented estimator and the original agree to `max |ΔH| = 0.0` across every frame tested. The instrumentation observes; it does not perturb. Without that guarantee, any difference measured downstream could be an artefact of the instrument.

From the recorded statistics we form six candidate reliability signals: the RANSAC inlier ratio ρ, the inlier count, the median symmetric transfer residual ε of the inliers, a solver-specific plausibility term (the fitted scale and rotation against a temporal prior; note that the singular-value ratio commonly used for this purpose is identically unity for the four-degree-of-freedom similarity the solver fits, and carries no information), a temporal-consistency term τ comparing the current warp against a constant-velocity forward prediction, and a foreground-contamination term φ, the fraction of inliers falling inside detection boxes. §4.4 reports which of these survive.

### 3.2 The oracle-warp contrast

MOT17, MOT20 and UAVDT provide no ground-truth camera motion, so compensation error cannot be measured directly. We measure it against a deliberately stronger estimate: full-resolution SIFT features, mutual-nearest-neighbour matching with a ratio test, foreground masked out using annotation boxes, robust fitting with a tighter threshold, and forward-backward consistency verification. Its median forward-backward corner error is 0.002 px pooled, and 0.0002–0.012 px taken per sequence.

This reference is non-causal, uses information no online tracker has, and is slow. It is an analysis instrument and never enters any tracker we report. It is also **not ground truth** — it is a better estimate — so every attribution derived from it is a *lower bound* on compensation error. We state that wherever such a figure appears.

Frames where the reference itself is untrustworthy are excluded: contrasting against a bad reference measures nothing. On MOT17 that retains 5,088 of 5,309 frames (95.8 %), but the exclusions are not spread evenly and they are not random with respect to the outcome:

| | 02 / 04 / 09 | 05 | 10 | 11 | 13 |
|---|---|---|---|---|---|
| frames | 2,172 | 836 | 653 | 899 | 749 |
| excluded | 0 | **206 (24.6 %)** | 6 | 3 | 6 |

A quarter of MOT17-05 — the worst sequence, and the source of 12 of the 34 harmful gate flips in §5.2 — is removed, and the excluded frames carry a median online residual of 1.066 px against 0.557 px for the retained ones. By §4.3's own predictor these are the highest-compensation-error frames. This biases §4.2's magnitudes and §4.3's AUC downward, and we say so where those figures appear. It does not rescue §5.2: adding the excluded frames back, other than the 101 on which the reference returns identity, moves the harmful gate-flip rate from 0.031 % to 0.033 % and the count from 34 to 37.

### 3.3 Gate-flip counting

Whether compensation error changes an *outcome* is not the same as whether it is large. For every ground-truth object present in consecutive frames we warp its previous box by the online warp and by the reference warp, compute IoU against its true current box, and count pairs whose gate decision differs:

```
gate flip  ⟺  (1 − IoU_online > θ_iou)  XOR  (1 − IoU_reference > θ_iou)
```

A flip in the harmful direction — a correct pair gated out by compensation error — is the event the coupling defect of §1 predicts. Because ground-truth identity is used, detector quality and appearance-embedding behaviour are excluded entirely; what remains is geometry.

An earlier version of this analysis asked instead whether compensation error alone pushes IoU below θ, using per-frame median box sizes. That produced a misleadingly clean 0 % and answered the wrong question: what matters is not whether the error crosses the threshold unaided but whether it changes the outcome for pairs already near it.

### 3.4 Ground truth where it exists

KITTI (Geiger et al., 2012) ships per-frame GPS/IMU measurements, the full calibration chain, and 3D object annotations; the raw `oxts` stream and its calibration are documented separately (Geiger et al., 2013). Composing them gives the true inter-frame camera motion and each object's depth, so on KITTI the contrast is against truth rather than against a better estimate. This is the only part of the study not subject to the lower-bound caveat of §3.2.

For a pixel at depth z in camera frame k−1, the displacement induced by camera motion (R, t) alone is obtained by back-projection, rigid transformation and re-projection. The object's own motion is deliberately excluded: the Kalman filter already predicts that, and a correction containing it would be counted twice. An earlier specification of our oracle fitted the warp to the objects' *total* true displacements and consequently scored below the deployable estimator — the signature of that double counting. The corrected specification is the one reported.

### 3.5 Protocol discipline

Every configuration compared in this paper consumes byte-identical detections. We run the detector once, write its output to disk, and record a SHA-256 for every file; each tracker variant reads those files. On MOT17 this is 62,398 detections from the published YOLOX-X ablation weights (Ge et al., 2021; Zhang et al., 2022); on KITTI, 8,008 frames through a COCO-pretrained detector that has never seen KITTI, which is why no train/validation split is needed there and none was invented.

Determinism was verified rather than assumed: five independent runs of the MOT17 file-GMC configuration, two of the KITTI pipeline, and two of the appearance-enabled MOT17 pipeline of §5.4 produced **bit-identical** tracker output on every evaluated sequence. A zero noise floor does not license calling small differences significant, and §6.6 accordingly reports bootstrap confidence intervals over sequences rather than run-to-run variance.

All evaluation uses the official TrackEval implementation (Luiten & Hoffhues, 2020).

---
## 4 How Accurate Is Compensation?

### 4.1 Four benchmarks, 61,337 frames

We ran the instrumented estimator over every frame of MOT17 (Milan et al., 2016; 5,309 frames, 7 sequences), MOT20 (Dendorfer et al., 2020; 8,927 frames, 4 sequences), UAVDT (Yu et al., 2020; 40,685 inter-frame estimates over 50 sequences) and KITTI tracking (Geiger et al., 2012; 6,416 analysed frames, 21 sequences), recording the full statistics of §3.1 for each. Table 1 summarises what they contain.

**Table 1** Compensation-reliability audit. Percentages are of frames. "Texture collapse" is the failure mode the literature most often invokes.

| Statistic | MOT17 | MOT20 | UAVDT |
|---|---|---|---|
| Frames | 5,309 | 8,927 | 40,685 |
| Median inlier ratio ρ | 0.976 | 0.995 | 1.000 |
| Median transfer residual ε | 0.570 px | 0.592 px | 0.295 px |
| 95th-percentile ε | 1.767 px | 0.879 px | 0.941 px |
| Median inter-frame displacement | 2.095 px | 0.689 px | 1.035 px |
| Median temporal inconsistency τ | 1.215 px | 0.813 px | 0.166 px |
| `n_inliers < 100` (texture collapse) | **0 (0.000 %)** | **0 (0.000 %)** | 19 (0.047 %) |
| `n_inliers < 300` | 3 (0.057 %) | 1 (0.011 %) | 1,620 (3.982 %) |
| `ε > 2 px` (imprecise fit) | 190 (3.579 %) | **0 (0.000 %)** | 148 (0.364 %) |
| ρ < 0.7 | 203 (3.824 %) | 1 (0.011 %) | 91 (0.224 %) |
| φ > 0.7 (inliers mostly on foreground) | 228 (4.295 %) | **3,314 (37.123 %)** | — |

The estimator is accurate. Median residuals are sub-pixel everywhere. The texture-collapse regime — too few correspondences to constrain a fit — occurs in 0 of 14,236 pedestrian-benchmark frames, because `goodFeaturesToTrack(maxCorners=1000)` is saturated in essentially every frame of both. The worst MOT17 sequence, MOT17-05, reaches a median inlier ratio of 0.842 with a 5th percentile of 0.538 and a median residual of 1.11 px: real degradation, and still an order of magnitude away from the synthetic collapse regime we constructed to calibrate the instrument (§4.4).

### 4.2 The oracle contrast, and a control that could have failed

Residuals measure a fit's internal consistency, not its correctness; a confidently wrong warp has a small residual. The oracle contrast of §3.2 supplies the external check. On MOT17 it retains 5,088 of 5,309 frames after the reference-quality filter (95.8 %).

The contrast has a built-in control. Three of the seven MOT17 sequences are recorded from a static camera and four from a moving one. If the instrument is measuring compensation error, the static sequences should show near-zero disagreement and the moving ones should not.

| | Frames | Median corner disagreement | 90th percentile | Median box-centre shift |
|---|---|---|---|---|
| Static sequences (02, 04, 09) | 2,172 | 0.150 px | 0.559 px | 0.118 px |
| Moving sequences (05, 10, 11, 13) | 2,916 | 1.309 px | 4.549 px | 0.637 px |

The separation is complete at sequence level. Per-sequence medians are 0.088 (02), 0.147 (04) and 0.505 px (09) for the static cameras against 0.786 (11), 1.121 (10), 1.669 (13) and 2.105 px (05) for the moving ones: every moving sequence exceeds every static one. This is weak positive evidence that the instrument works, and would have been strong evidence against it had the ordering come out otherwise.

MOT20 deserves the same external treatment, because it is the case that should have been the worst and because a residual alone cannot settle it. MOT20-05 has φ = 0.8166 at the median: 82 % of the keypoints used to estimate *camera* motion lie on *pedestrians*, and 37.1 % of MOT20 frames exceed φ > 0.7. Foreground domination at that level is exactly what the literature warns about, and a confidently wrong warp would have a small residual. We therefore ran the oracle contrast over all 8,927 MOT20 frames:

| | Frames | Median corner disagreement | p90 | p99 | Max | Median φ |
|---|---|---|---|---|---|---|
| MOT20-01 | 428 | 0.409 px | 0.646 | — | — | 0.236 |
| MOT20-02 | 2,781 | 0.745 px | 1.274 | — | — | 0.321 |
| MOT20-03 | 2,404 | 1.017 px | 1.241 | — | — | 0.508 |
| MOT20-05 | 3,314 | 0.756 px | 1.223 | — | — | **0.817** |
| **All MOT20** | **8,927** | **0.839 px** | **1.237** | **1.717** | **2.732** | 0.512 |

The reference warp succeeded on **every** MOT20 frame, against a 24.6 % failure rate on MOT17-05. Compensation error on MOT20 sits between MOT17's static and moving sequences, and its maximum over the whole benchmark is 2.73 px. MOT20-05, with 82 % of its inliers on pedestrians, disagrees with the reference by 0.756 px at the median — *less* than MOT20-03, which has 51 % contamination. Contamination is measured here rather than argued away.

The reason is mechanical. MOT20 is a static-camera benchmark with dense, slow, coherent pedestrian flow: the contaminating keypoints move consistently with one another, so the fit has a low residual, and because the crowd's inter-frame displacement is sub-pixel the resulting transform — which describes crowd motion, not camera motion — is still close to identity, which is the correct answer for a static camera. Contamination is not error. What matters is whether the contaminating objects move.

### 4.3 Predicting the error from a statistic that is already free

Given the oracle contrast as a target, the six candidate signals of §3.1 can be validated. We evaluate by leave-one-sequence-out: fit on six MOT17 sequences, measure on the seventh, report the mean held-out area under the ROC curve for detecting compensation error above 1 px.

The median transfer residual ε of the inlier set — computed inside the existing RANSAC call and then discarded — achieves a **held-out AUC of 0.866**, worst sequence 0.779. Its raw Spearman correlation with compensation error is −0.928.

Three checks keep that from being an artefact of scene composition:

*Confound conditioning.* Stratifying into quartiles by scene density, by detection count, by camera-displacement magnitude and by keypoints tracked, the relationship holds within every stratum of every stratification. The weakest single stratum is the third camera-displacement quartile at −0.741; the weakest stratification overall is by scene density, whose densest quartile gives −0.764.

*Removing the static/moving split.* Restricted to the four moving-camera sequences only (2,916 frames), pooled Spearman is −0.771, and per sequence −0.786 (05), −0.596 (10), −0.702 (11), −0.763 (13).

*Placebo.* Recomputing the signal from statistics shuffled across frames gives a mean correlation of −0.001 over 200 permutations (range [−0.035, +0.033]) against a real value of −0.928.

### 4.4 A reversal we report rather than hide

Before touching real data we built a synthetic study: 234 frames with known ground-truth warps under six injected failure modes — clean, blur, repetitive texture, low light, foreground domination, and low texture. On that data the *six-signal* combination was best (Spearman −0.821 against actual corner error; best single signal ε at −0.720), and we pre-registered it as the estimator.

On real MOT17 data it lost. We searched all 63 non-empty subsets under leave-one-sequence-out:

Figure 8 plots all 63 subsets and Table S1 gives the best at each size. Held-out performance degrades monotonically with every signal added: the best single signal, the median transfer residual, reaches a held-out AUC of 0.866 against 0.774 for all six together. Dropping from six to one gains +0.092 AUC. The diagnosis, from per-signal statistics over the same 5,088 frames:

- **The inlier count is degenerate on MOT17** — 99.94 % of frames sit at the ceiling, because the keypoint detector's cap is saturated. It carried real information in the synthetic low-texture mode, where inliers collapsed to zero. That mode does not occur in MOT17.
- **Temporal consistency τ is the largest single loss** (0.854 → 0.774 when added at k = 6). It was designed to catch sporadic single-frame failures. But real camera motion is not smooth — panning accelerates, vehicles turn — so a constant-velocity prediction of the warp is violated by *legitimate* motion, which τ reports as unreliability. On real data it is a false-alarm generator.
- **Foreground contamination φ has variance but not information.** Its standard deviation is 0.153 over a range of 0–0.896, so it is not degenerate; its AUC alone is 0.584. §4.2 explains why: contamination without contaminant motion is harmless.
- **The plausibility term κ is dominated by ε**, and the singular-value ratio often used for this purpose is identically unity for a four-degree-of-freedom similarity and carries no information at all.

We report the reversal because the disagreement is itself the finding: the six-signal estimator is better at detecting failure modes that MOT17 does not contain. The reported estimator therefore uses ε alone — one scalar, already computed, no new hyperparameter beyond a scale. The synthetic result stands as evidence about which failure modes are detectable in principle, together with the statement that MOT17 does not contain the catastrophic ones.

### 4.5 The honest number is the within-sequence one

The raw −0.928 overstates per-frame predictive power. A placebo that shuffles statistics *within* each sequence — destroying the frame-level pairing while preserving the between-sequence structure — still reaches −0.748. Most of the headline correlation is the between-sequence fact that sequences with more camera motion have both higher error and higher residuals.

The figures that survive this are the within-sequence ones: per-sequence correlations of −0.60 to −0.79, and the leave-one-sequence-out AUC of 0.866, which is computed within each held-out sequence and is the number we quote.

---

## 5 Does That Accuracy Matter?

Section 4 establishes that compensation error is real, small, and predictable. This section asks whether predicting it would change anything. It bounds the answer three ways on MOT17 — two of them large-sample functionals of a single dataset, the third a tracking experiment that is separate evidence but has the least resolution — and then tests the most severe available camera motion.

### 5.1 Geometric bound

For each ground-truth object present in consecutive MOT17 frames, warp its previous box by the online warp and by the reference warp and compare IoU against its true current box. Over 109,955 pairs:

- Median IoU cost of compensation error: **0.00085**. Mean: 0.00003.
- IoU after the online warp, by quantile: 0.479 (0.1 %), 0.676 (1 %), 0.803 (5 %), 0.916 (25 %), 0.960 (50 %).
- Fraction of pairs with IoU below the 0.5 association gate: **0.127 %**.

The margin is the point. At a median IoU of 0.96 against a gate at 0.5, an error costing 0.00085 cannot move a pair across. Only **0.284 %** of pairs (312 of 109,955) sit in the near-miss band where reference IoU falls in [0.5, 0.6] — close enough that an error of this scale could plausibly matter. Of those, 21 are gated out (6.73 %).

### 5.2 Combinatorial bound

The geometric bound is an average. The gate-flip count of §3.3 asks directly how often the *decision* changes; Table 2 gives it per sequence.

**Table 2** Gate flips on MOT17 at θ = 0.5, over 109,955 ground-truth pairs. "Harmful" = a pair the reference warp would have admitted but the online warp gates out.

| Sequence | Camera | Pairs | Median IoU | Harmful | Helpful |
|---|---|---|---|---|---|
| MOT17-02 | static | 18,519 | 0.972 | 0 | 0 |
| MOT17-04 | static | 47,474 | 0.982 | 0 | 0 |
| MOT17-09 | static | 5,299 | 0.934 | 0 | 0 |
| MOT17-05 | moving | 5,180 | 0.890 | 12 | 5 |
| MOT17-10 | moving | 12,666 | 0.899 | 14 | 7 |
| MOT17-11 | moving | 9,335 | 0.952 | 0 | 0 |
| MOT17-13 | moving | 11,482 | 0.888 | 8 | 9 |
| **Total** | | **109,955** | | **34** | **21** |

Fifty-five flips total, 0.050 % of pairs; 34 harmful, 0.031 %. Four of seven sequences produce exactly zero — including MOT17-11, which is a moving-camera sequence. MOT17-13, also moving, is net *beneficial*: the online warp admits more correct pairs than the reference does. The direction of the effect is not consistent even across the sequences that have one.

Two details make the negative result stronger rather than weaker. Harmful flips concentrate on pairs that were already lost: the median box width at a harmful flip is 21–33 px against sequence medians of 28–124 px, and in MOT17-05 the median annotated *visibility* at a harmful flip is 0.0000 — the object is fully occluded. These are not cases an appearance channel would have rescued. And the count is not an artefact of the threshold: at θ = 0.3 there are 654 flips with 312 harmful (0.28 % of pairs), at θ = 0.4 there are 216 with 118, at θ = 0.5 there are 55 with 34, at θ = 0.6 there are 22 with 15. We report the value BoT-SORT actually uses.

Thirty-four opportunities is the entire budget available on MOT17 to a method that detects compensation failure perfectly and responds to it perfectly. For scale, the baseline commits 139 identity switches.

### 5.3 Empirical bound

The bounds above are geometric. The direct test, in Table 3, substitutes the reference warp into an otherwise unmodified tracker and measures HOTA. Four configurations, byte-identical detections (62,398 from the published YOLOX ablation weights), identical hyperparameters, identical evaluation. The configuration is BoT-SORT's own published ablation setting — Kalman filter plus compensation, no appearance model — which is the row our baseline reproduces (§3.5); §5.4 repeats the axis with the appearance channel enabled.

**Table 3** The compensation-value axis on MOT17 validation-half. The only variable is the warp.

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW |
|---|---|---|---|---|---|---|
| No compensation | 68.118 | 69.914 | 66.898 | 79.598 | 77.777 | 337 |
| Online `sparseOptFlow` | 69.006 | 71.333 | 67.246 | 81.345 | 78.451 | 139 |
| Precomputed file GMC (published default) | 69.120 | 71.570 | 67.239 | 81.499 | 78.445 | 140 |
| **Reference (oracle) warp, strict** | **69.093** | **71.510** | **67.245** | **81.500** | **78.488** | **147** |

Figure 1 plots both axes. Reading Table 3 from the bottom:

- **Having compensation is worth +0.888 HOTA and −198 identity switches.** Compensation matters.
- **Perfecting it is worth +0.087 HOTA and +8 identity switches.** Perfecting it makes identity switches *worse*.
- The axis is non-monotone in compensation quality: the oracle scores 0.027 HOTA *below* the published file-GMC configuration.
- Perfecting compensation is worth **9.8 %** of having it.
- The gap between the two ordinary compensator implementations — 0.114 HOTA — is larger than the value of making either perfect.

One implementation detail must be disclosed, because Table 3's caption is otherwise false. Our first oracle configuration reverted to the online estimate on any frame where the reference warp failed its quality gate — 76 of 418 validation frames on MOT17-05 (18.2 %), and 10 frames across the rest — so on that sequence it was a hybrid, and it was a hybrid precisely where the two warps differ most. We re-ran the axis with the reference used wherever it exists:

| | with fallback | strict | Δ |
|---|---|---|---|
| motion-only oracle HOTA | 69.105 | **69.093** | −0.012 |
| motion-only oracle IDSW | 144 | **147** | +3 |
| appearance oracle HOTA (§5.4) | 69.344 | **69.350** | +0.006 |
| appearance oracle IDSW | 165 | **164** | −1 |

The strict substitution moves HOTA by 0.012 and is marginally *worse*. **Every oracle figure in this paper is the strict one**: Tables 3, 4 and 5 and every derived interval were recomputed after the re-run, and the hybrid numbers appear only in the comparison above. The difference is not always negligible in the intervals even though it is in the point estimates — the moving-camera motion-only interval moves from +0.000 [−0.043, +0.052] under the hybrid to −0.037 [−0.201, +0.052] under the strict oracle (§5.5), with the same upper bound and a five-times wider lower one.

The determinism check of §3.5 matters too: five independent runs of the file-GMC configuration produced bit-identical output, so none of these differences is run-to-run variation. That bounds reruns and nothing else — §5.5 supplies the interval over sequences, which is the uncertainty that matters.

The +8 identity switches deserve a comment, because a worse-than-baseline oracle looks like a bug. It is not. Association is a global assignment: changing a few costs reshuffles matches elsewhere, and at this magnitude the reshuffling is noise around zero. That is precisely the claim — the effect of compensation error on MOT17 is smaller than the incidental variation of the assignment step.

### 5.4 With the appearance channel enabled

Section 5.3 uses BoT-SORT's own published ablation configuration, which has no appearance model. That configuration is the right one for reproducing the published baseline, but it leaves an objection open: §1's argument is that compensation error *suppresses the appearance channel*, and a tracker with no appearance channel cannot exhibit that. We therefore repeated the whole axis with FastReID SBS-S50 (He et al., 2020) enabled — the appearance model BoT-SORT ships — on the same frozen detections.

**Table 4** The same axis with the appearance channel on. The coupling of §1 (`emb_dists[ious_dists_mask] = 1.0`) is active in every row.

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW | Frag |
|---|---|---|---|---|---|---|---|
| No compensation | 68.280 | 70.168 | 66.969 | 79.768 | 77.929 | 300 | 488 |
| Online `sparseOptFlow` | **69.426** | **72.166** | **67.272** | **82.276** | **78.551** | **160** | **453** |
| Reference (oracle) warp, strict | 69.350 | 72.025 | 67.257 | 82.119 | 78.484 | 164 | 457 |

Table 4 shows that enabling appearance raises every configuration, as expected, and changes nothing about the shape of the axis:

- **Having compensation is worth +1.146 HOTA and −140 identity switches** — more than without appearance, because the appearance channel can only help on pairs the motion gate admits.
- **Perfecting it is worth −0.076 HOTA and +4 identity switches.** With the appearance channel enabled, the point estimate for the value of a perfect warp is *negative* on HOTA and association.

We do not claim from this that perfect compensation is harmful, and an earlier version of this section claimed more than the data support. Pooled over all seven sequences the point estimate is negative, but three of those sequences have a static camera and therefore nothing to compensate. Section 5.5 stratifies by that control and finds a small positive effect on the moving sequences, +0.189 HOTA with an interval that excludes zero. The claim that the value of perfecting compensation "is not positive in either configuration" is withdrawn. What survives is the magnitude: with the appearance channel on and camera motion present, a perfect warp is worth about a sixth of a HOTA point, against +1.146 for having a working compensator at all.

This is the objection we most expected, and turning the channel on does not change the order of magnitude: the appearance channel is present and doing work (+0.93 IDF1 and +0.42 HOTA over the motion-only configuration at the same warp), and giving it a perfect warp buys a sixth of a HOTA point.

### 5.5 What the intervals allow, and on which sequences

A negative result is only as strong as its upper bound. Tables 3 and 4 give point estimates against a verified zero run-to-run noise floor, but that floor says nothing about the seven sequences themselves. We applied the same percentile bootstrap used for the KITTI claims — 20,000 resamples over sequences, HOTA averaged over TrackEval's alpha grid, sequences weighted by ground-truth detections. (Alpha-grid averaging is not identical to TrackEval's pooled combination, so the bootstrap point estimates differ slightly from Tables 3 and 4.)

Pooling all seven sequences is the wrong thing to do, and §4.2's own instrument control says why: three of them have a static camera, so they contain no camera motion for a warp to compensate and contribute only noise to an estimate of what compensation accuracy is worth. Table 5 reports both.

We state the provenance of that stratification, because it determines how much weight it can carry. The static/moving classification is not post-hoc: it is a property of the benchmark, it is the control used in §4.2 to validate the oracle-warp instrument before any tracking experiment was run, and MOT17-11 is classified moving there on the same basis. What *was* prompted by review is the decision to apply it here. We had reported the pooled interval; a reviewer observed that an upper bound on the value of camera-motion compensation should not be computed over sequences with no camera motion. The stratum was therefore fixed in advance and the choice to use it was not, which is the weaker of the two positions and is why we report the pooled interval alongside rather than in place of it.

**Table 5** Bootstrap 95 % confidence intervals on the MOT17 compensation-value axis. The oracle rows use the strict configuration of §5.3.

| Quantity | Configuration | All 7 sequences | **Moving-camera sequences (05, 10, 11, 13)** |
|---|---|---|---|
| Value of **having** compensation | motion only | +0.928 [−0.136, +3.471] | **+3.426 [+1.007, +5.523]** |
| Value of **having** compensation | + appearance | +1.220 [+0.243, +3.720] | **+3.500 [+1.082, +4.842]** |
| Value of **perfecting** it | motion only | +0.125 [−0.062, **+0.477**] | **−0.037 [−0.201, +0.052]** |
| Value of **perfecting** it | + appearance | −0.087 [−0.453, +0.138] | **+0.189 [+0.050, +0.517]** |
| Gap between two ordinary compensators | motion only | +0.149 [−0.028, +0.504] | +0.057 [−0.015, +0.233] |

Four readings.

**The bound is an order of magnitude tighter where it should be computed.** On the sequences that actually have camera motion, the value of a perfect warp is −0.037 HOTA with a 95 % upper bound of **+0.05** in the motion-only configuration. Pooled with the static sequences it is +0.125 with an upper bound of +0.48 — and that upper bound is set by resamples loaded with MOT17-09, a static-camera sequence whose individual delta is +1.118 HOTA under a sub-pixel change of warp. An upper bound on what camera-motion compensation could be worth should not be determined by a sequence with no camera motion.

**With the appearance channel enabled the effect is small, positive and no longer indistinguishable from zero.** On the moving sequences a perfect warp is worth +0.189 HOTA [+0.050, +0.517]. It is carried mostly by MOT17-05 (+0.731; the other three give +0.002, +0.059, +0.042), and the static stratum is significant in the *opposite* direction (−0.214 [−1.826, −0.061]). Two strata of the same experiment producing opposite significant results is itself evidence that a seven-sequence percentile interval is not well calibrated, and we treat +0.52 as the defensible upper end rather than +0.19 as an effect.

**Seven sequences is fewer than seven.** The Kish effective sample size on the ground-truth-detection weights is **3.79**, with MOT17-04 alone carrying 44.9 % and the top two 63.2 %. Only C(13,6) = 1,716 distinct resamples exist at n = 7, and the run realises 1,555 unique values from 20,000 draws; the "20,000 resamples" conveys no precision beyond that. The percentile method is also the least accurate bootstrap interval at this n, and because the claim is an upper bound its undercoverage biases toward our conclusion. We therefore quote the moving-only interval, which is tight enough that method choice cannot rescue a publishable effect from it, rather than the pooled one.

**The tracking experiment is the weakest of the three bounds.** With camera motion present the value of *having* compensation is +3.426 [+1.007, +5.523] — clearly real — but pooled over seven sequences even that crosses zero on HOTA. This is a limit on what an aggregate over seven sequences can resolve, and it is why §5.1 and §5.2 carry the section: both rest on 109,955 ground-truth pairs rather than on a seven-sequence mean. The two of them are not independent of each other — they are two functionals of one dataset from one instrument — and we drop the word "independent" for them; the tracking experiment is separate evidence, and it is the one with the least resolution.

### 5.6 The benchmark the literature treats as the hard case

MOT17 and MOT20 are pedestrian benchmarks with modest camera motion, so the null result invites the objection that we tested the wrong data. UAVDT is the standard reply: aerial footage from a moving drone, the setting in which camera-motion compensation is usually held to be indispensable.

Its compensation estimates are the cleanest of the three image benchmarks (Table 1): median residual 0.295 px, median temporal inconsistency 0.166 px. High-altitude nadir-ish viewing puts almost the entire scene at nearly uniform depth, which is the condition under which a single global warp is exactly right.

Figure 2 shows how its reliability distributions compare with the pedestrian benchmarks'. Running the same motion-only tracker over the 20 UAVDT sequences that ship with published FRCNN detections, fixed across both configurations:

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW | Frag |
|---|---|---|---|---|---|---|---|
| No compensation | 43.920 | 48.644 | 40.242 | 57.335 | 31.786 | 3,342 | 8,939 |
| Online GMC | 44.083 | 48.946 | 40.276 | 57.646 | 31.756 | 3,347 | 8,993 |

Turning compensation on is worth +0.163 HOTA and changes identity switches by 5 out of 3,342 — in the wrong direction. On UAVDT compensation barely registers at all, let alone its failures.

We state the limitation that goes with this: UAVDT has no ground-truth ego-motion, so no oracle warp is possible there and we can compare only `none` against `online`. That answers "does compensation matter here?" and not "would a perfect one matter more?". Given that `none` and `online` already differ by 0.163 HOTA, the second question has little room left in it.

### 5.7 What follows for the benchmarks

Across MOT17, MOT20 and UAVDT, compensation error is measurable, predictable, and too small to change association outcomes. That has a consequence for how results are read:

> **A tracking improvement attributed to camera-motion compensation on MOT17, MOT20 or UAVDT cannot be an improvement in compensation robustness, because there is not enough compensation error on these benchmarks for robustness to recover.**

The three benchmarks support that statement with different evidence, and we distinguish them. MOT17 has all three bounds of §5.1–§5.5, including a tracking experiment with an oracle warp. UAVDT has a tracking experiment but no oracle, so it bounds what compensation is worth and not what a perfect one would add. MOT20 has no tracking experiment at all, but it does have the external oracle contrast of §4.2 over all 8,927 of its frames, which puts its compensation error at a median of 0.839 px and a maximum of 2.73 px. That is a claim about the absence of the error rather than about its consequences — the weaker of the two kinds of argument — but it is measured against an independent estimate rather than resting on the compensator's own residual.

The improvement may be real. Its mechanism is something else — a changed effective gate, altered Kalman dynamics, a different interaction with the appearance channel. This sharpens the survey critique quoted in §2.5 from a procedural complaint about inconsistent protocols into a specific, checkable claim about a specific module.

It also disposes of the hypothesis we began with. Reliability-gated association cannot help on these benchmarks, not because reliability is unmeasurable — §4 shows it is measurable for free — but because there is nothing for it to gate. Under a pre-committed decision rule we declined to run the ablation grid that would have tuned such a method into an apparent win.

---
## 6 What Actually Limits Compensation

Section 5 is a null result on three benchmarks. It does not show that camera-motion compensation is unproblematic; it shows that *estimation accuracy* is not where the problem lies on data of that kind. This section identifies where it does lie, using the one benchmark where camera motion is known rather than estimated.

### 6.1 Why KITTI is the discriminating case

A single 2D warp can serve every target in a frame only if they all need the same correction. Whether they do is a question about the camera's motion, not about the estimator.

Under pure rotation the answer is yes, exactly: the induced image motion is the homography `H = K R K⁻¹`, which is independent of scene depth. Every pixel, near or far, moves by the same rule.

Under translation the answer is no, and not approximately. The image displacement of a point at depth *z* under camera translation *t* contains a term proportional to *1/z*. A global 2D warp assigns one displacement field to the frame; objects at different depths need different ones. No choice of warp family removes a depth dependence that the warp has no argument for.

MOT17, MOT20 and UAVDT are rotation- and pan-dominated: hand-held or mounted cameras that mostly turn, and aerial footage at near-uniform depth. KITTI is a camera on a car. It translates, at speed, through scenes containing objects from 6 m to beyond 50 m.

KITTI also supplies the ground truth to measure this. Composing its oxts GPS/IMU stream with the calibration chain gives true inter-frame camera motion, and its 3D labels give each object's depth. Every figure in this section is measured against truth, not against a better estimate — the only part of the paper not subject to the lower-bound caveat of §3.2.

### 6.2 The residual is per-object, not per-frame

For each object present in consecutive frames we compute its exact image displacement from its annotated 3D position and the true camera motion, then ask three compensation models to predict it. Over 6,416 frames:

| Model | Median residual | p90 | Max |
|---|---|---|---|
| No compensation | 4.196 px | 15.367 | 127.8 |
| Rotation homography `K R K⁻¹` (true R) | 3.621 px | 12.917 | 128.6 |
| **Best-fit similarity (oracle)** | **0.101 px** | **2.146** | **48.6** |

The four-degree-of-freedom similarity that BoT-SORT's GMC estimates fits KITTI better than the geometry suggests, because forward translation produces approximately radial expansion and a uniform-scale term absorbs most of it. The rotation-only homography, by contrast, is nearly useless here: on a car, rotation is the small component.

The information is not in the median. It is in the spread, plotted in Figure 3. Here is the within-frame spread of the residual *after* the best possible global compensation, over moving frames:

| | Median | p75 | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|
| Spread across objects in one frame | **5.878 px** | 14.868 | 30.404 | 43.765 | 73.005 | **473.5** |

| Objects in the same frame disagree by more than | Share of moving frames |
|---|---|
| 1 px | 85.92 % |
| 2 px | 73.65 % |
| **5 px** | **54.31 %** |
| 10 px | 36.22 % |

In more than half of all moving frames, objects in the same image require corrections differing by more than five pixels — after the best global correction that could possibly be computed. The spread is depth-driven, as parallax predicts: the per-frame Spearman correlation between object depth and residual has median −0.400 and is negative in 75.3 % of the frames where it is defined (3,379 of the 4,318 moving frames; the statistic needs at least four objects, and 939 frames have three). Nearer objects carry the larger residual.

### 6.3 It reaches the association gate

Spread in pixels is not yet an effect on tracking. Using each object's true box size and BoT-SORT's θ_iou = 0.5:

| | KITTI (residual after the best global *similarity*) | MOT17 (compensation error) |
|---|---|---|
| Moving frames with ≥ 1 object pushed below the gate | **10.00 %** | — |
| Object-frames gated out | **488 / 23,443 = 2.082 %** | **34 / 109,955 = 0.031 %** |

Sixty-seven times the MOT17 rate — and the two numbers are not the same kind of quantity, so the ratio is indicative rather than exact. The MOT17 figure is the *total* effect of imperfect compensation. The KITTI figure is what survives the best global **similarity** that could be fitted to these objects. Section 6.4 shows that a richer family with access to depth removes most of it, so it is not irreducible; what it is irreducible to is the four-degree-of-freedom warp the tracker actually applies.

The measurement uses no images, no detector and no tracker. It is a property of the scene geometry and the compensation model.

### 6.4 Depth is the missing argument, and a homography can take it

Section 6.2 shows that one similarity cannot serve a frame's targets. The obvious question is whether a richer family can. Ground-plane modelling is the premise of a strong recent tracker (Yi et al., 2024), so the question is not idle. We got it wrong twice before getting it right, in two distinct ways, and both are instructive.

**First error: fitting to the answer.** We fitted each warp family to the objects' *own* true displacements and compared what each left behind. Over 2,389 moving frames:

| Family | DOF | Median residual | Within-frame spread | Frames with spread > 5 px |
|---|---|---|---|---|
| Similarity | 4 | 0.865 px | 8.713 px | 66.85 % |
| Affine | 6 | 0.131 px | 8.822 px | 68.02 % |
| Homography | 8 | **0.000 px** | 0.746 px | 14.40 % |

The exactly-zero residual is the tell: eight degrees of freedom interpolate five or more correspondences. This measures how expressive each family is, not what a compensator could achieve, because a compensator never sees these correspondences. We briefly read it as evidence that the family was the whole problem.

**Second error: flattening the scene.** We then fitted both families to a grid of *static scene* points, as a compensator must — but placed the grid at a single depth. The mapping induced between two views of a plane **is** a homography, so `findHomography` recovers it to 6.2 × 10⁻⁶ px and the 8-DOF model carries exactly as much depth information as the 4-DOF one: one depth. On that construction a homography reduced the within-frame spread by **2.25 %** (7.588 → 7.418 px), and we read that as evidence that the family was *not* the problem. It was evidence about our grid. The two errors point in opposite directions and neither answered the question.

**The measurement.** A compensator can have depth — a monocular network supplies it, and §7 already runs one. We refitted both families to background points carrying their **own** depths: a grid over the lower image, points inside the tracker's own **detections** masked out (not annotations — a compensator cannot read labels), a median of 437 background samples per frame, back-projected at each point's estimated depth, transformed by the true camera motion and re-projected. The ground plane is present rather than flattened away. Measured at object centres against their true induced displacement, on the same 4,318 frames as §6.2:

Figure 4 plots the distributions and sets them against what each warp produces in tracking.

**Table 6** Global compensation models on KITTI, measured at object centres against true displacement. The similarity and homography rows are fitted to the same depth-varying background points; the oracle row is fitted to the objects themselves and is an upper bound, not a method.

| | Median residual | Within-frame spread | Frames with spread > 5 px |
|---|---|---|---|
| Online sparse-flow GMC (what the tracker ships) | 2.026 px | 8.673 px | 65.12 % |
| Oracle similarity, fitted to the objects (§6.2) | 0.537 px | 5.878 px | 54.31 % |
| Deployable similarity, depth-varying background | 4.773 px | 7.466 px | 61.74 % |
| **Deployable homography, depth-varying background** | **0.478 px** | **1.370 px** | **12.90 %** |

Table 6 supports three readings.

**A similarity cannot use depth and is made worse by being shown it.** Fitted to genuinely depth-varying correspondences it reaches 4.773 px median residual, against 0.537 px for one fitted to a single depth chosen well. Four degrees of freedom have nowhere to put the information.

**A homography can.** It reduces the within-frame spread to 1.370 px — **81.6 %** below the deployable similarity's 7.466 px, and **76.7 %** below the 5.878 px that survives the best similarity that could be fitted to the objects themselves. The fraction of frames in which targets disagree by more than 5 px falls from 54.31 % to 12.90 %. This is not a subtle effect and it does not require ground truth: the depth comes from a network, the correspondences from background points the tracker could pick itself.

**The reason is that KITTI's scene is approximately a plane and its targets stand on it.** A homography is exactly the family that maps one plane to another, which is why eight degrees of freedom suffice here and why the result should not be expected to transfer to a scene without a dominant plane. It is also, restated in image coordinates, the geometry that UCMCTrack exploits by leaving the image plane altogether.

### 6.5 Converting geometry into tracking metrics

Geometric room is a bound, not a result. We therefore ran the tracking experiment with one variable at a time.

The tracker is BoT-SORT-shaped and motion-only: Kalman filter, two-stage ByteTrack association (Zhang et al., 2022), IoU gate, no appearance model. Omitting ReID is deliberate — a vehicle re-identification model would be a second uncontrolled variable — and §9.3 states what that costs the argument. Detections come from a COCO-pretrained YOLO11x that has never seen KITTI, frozen once and hashed; every configuration reads the same files. Evaluation is official TrackEval under the KITTI protocol.

**Table 7** The configurations, and what each is allowed to use.

| Configuration | Correction | Ego-motion | Depth | Reads annotations |
|---|---|---|---|---|
| none | identity | — | — | no |
| online GMC | BoT-SORT's own `sparseOptFlow` | — | — | no |
| global similarity (oracle) | 4-DOF fitted to a static grid at the scene's median annotated depth | true | true | yes |
| global similarity, target-anchored (oracle) | the same, anchored at one class's median depth | true | true | yes |
| **depth-aware global homography** | **8-DOF fitted to background points at their estimated depths, detections masked out** | **true** | **estimated** | **no** |
| **depth-aware homography, contact point** | **the same warp, applied through each box's contact point** | **true** | **estimated** | **no** |
| per-target similarity (oracle) | 4-DOF per object, from its own box corners at its own true depth | true | true | **yes** |

Table 7 lists the configurations and what each is allowed to use. Two disclosures belong here rather than in a limitations section.

*The per-target configuration reads ground truth at run time.* To decide which object's warp to apply to a track, it matches the track's predicted box against the **annotated** boxes of the previous frame (IoU distance below 0.7) and falls back to the global similarity when no match is found. Over the 21 sequences, 40,557 of 69,000 track-warp applications (58.8 %) receive a per-object warp and 28,443 (41.2 %) receive the global one. It is therefore not a deployable method, and it differs from the global configurations in more than whether the correction is shared: it also consults annotations and applies the correction selectively. We report it as an upper bound and draw no deployability conclusion from it. The two depth-aware homography rows read no annotations at all.

*Fallbacks are reported per configuration.* A single plausibility guard replaces any warp whose implied scale falls outside [0.5, 2.0] with the identity, applied identically everywhere; it fires 0 times for `online` and the global similarity, 26 times for per-target, and 889 of 68,966 applications (1.29 %) for the depth-aware homography, which is relinearised per track and therefore has more opportunity to produce an implausible local scale. Separately, on frames where too few background points survive the detection mask the homography falls back to the global similarity — 1,291 of 8,008 frames (16.1 %), almost all of them near-static. It never falls back to the identity except on the first frame of each sequence.

Two specification errors were found and corrected before these numbers were produced, and both are recorded in Supplementary S2 rather than quietly fixed.

### 6.6 Results

**Table 8** KITTI tracking, 21 sequences, 8,008 frames, byte-identical detections throughout.

*Pedestrian*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 45.499 | 47.877 | 43.996 | 279 |
| online sparse-flow GMC (deployable) | **47.428** | 51.448 | 44.617 | 126 |
| global similarity (oracle) | 46.744 | 50.006 | 44.784 | 108 |
| global similarity, pedestrian-anchored (oracle) | 46.948 | 50.385 | 44.798 | 109 |
| **depth-aware global homography (deployable)** | 47.158 | 50.834 | 44.714 | 97 |
| **depth-aware homography, contact point (deployable)** | 47.233 | 50.974 | 44.892 | **85** |
| per-target similarity (oracle, reads annotations) | **47.576** | **51.852** | 44.748 | 88 |

*Car*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 64.792 | 70.339 | 60.584 | 401 |
| online sparse-flow GMC (deployable) | 65.265 | 70.137 | 61.450 | 165 |
| global similarity (oracle) | 66.267 | 71.922 | 61.775 | 129 |
| global similarity, car-anchored (oracle) | 66.029 | 71.343 | 61.802 | 121 |
| **depth-aware global homography (deployable)** | **66.482** | **72.507** | 61.722 | 125 |
| depth-aware homography, contact point (deployable) | 66.044 | 71.659 | 61.664 | **115** |
| per-target similarity (oracle, reads annotations) | 66.473 | 72.432 | 61.730 | 117 |

Table 9 and Figure 5 give the intervals.

**Table 9** Bootstrap 95 % confidence intervals over the 21 sequences, 20,000 resamples, HOTA averaged over TrackEval's alpha grid, sequences weighted by ground-truth detections. ΔIDSW is the same weighted difference, **not** a per-sequence rate.

| Comparison | Class | HOTA | ΔIDSW (weighted) |
|---|---|---|---|
| **depth-aware homography − online GMC** | **car** | **+1.187 [+0.262, +1.922]** | −3.35 [−8.01, +0.15] |
| depth-aware homography − online GMC | ped | −0.430 [−1.030, +1.030] | −0.75 [−11.72, +2.53] |
| homography at contact point − online GMC | car | +0.757 [−0.023, +1.866] | **−4.38 [−9.06, −0.76]** |
| homography at contact point − online GMC | ped | −0.393 [−1.189, +1.968] | −1.90 [−12.64, +1.03] |
| per-target − depth-aware homography | car | −0.006 [−0.530, +0.446] | −1.08 [−2.88, +0.61] |
| per-target − depth-aware homography | ped | +0.424 [−0.032, +1.002] | +0.18 [−0.64, +1.54] |
| per-target − global similarity | ped | **+0.842 [+0.067, +1.226]** | **−3.12 [−5.86, −0.03]** |
| per-target − global similarity | car | +0.213 [−0.342, +0.605] | −1.17 [−2.48, +0.24] |
| having compensation at all | ped | **+1.875 [+0.681, +4.768]** | **−22.25 [−33.23, −0.41]** |
| having compensation at all | car | +0.528 [−0.600, +2.001] | **−14.77 [−26.52, −5.02]** |

Four readings.

**Supplying depth to the shared warp is what works, and it is deployable.** On cars the depth-aware homography beats the compensator BoT-SORT ships by **+1.187 HOTA [+0.262, +1.922]**, excluding zero, and it reads no annotations. On pedestrians its HOTA is 0.43 below the shipped compensator with an interval that crosses zero, but it commits **97 identity switches against 126**, and applied through the contact point, **85** — the fewest of any configuration in the paper, including the annotation-reading oracle.

**The per-target correction adds nothing on top of it.** Against the depth-aware homography, per-target is −0.006 [−0.530, +0.446] on cars and +0.424 [−0.032, +1.002] on pedestrians; both cross zero, and on pedestrians per-target commits *more* identity switches than the contact-point homography (88 against 85). The large +0.842 [+0.067, +1.226] that per-target enjoys over the global *similarity* is therefore not evidence that corrections must be per-object. It is evidence that the shared warp was missing depth, and a global model that has depth closes the gap — without ground-truth ego-motion at run time being any more available to one than the other, and without the annotation channel per-target needs.

**Improving a shared warp along the wrong axis can hurt.** On pedestrians, moving from the deployable GMC to the single-depth global oracle costs 0.684 HOTA: a global fit anchored at the scene's median depth is systematically wrong for the near objects pedestrians usually are, and making that fit *more accurate in its own terms* makes it more confidently wrong for them. Anchoring it at the pedestrians' own median depth recovers about a third of that (46.948), and giving it depth properly recovers all of it and more. This is the non-monotonicity §5.3 finds on MOT17, here with a mechanism and a remedy.

**Cars and pedestrians rank the two applications differently.** Applying the homography to all four box corners is better on cars (66.482 against 66.044); applying it through the contact point is better on pedestrians (47.233 against 47.158, and 85 identity switches against 97). A ground-plane homography is correct for an object's contact point and wrong above it, and pedestrians are tall relative to their footprint while cars are not. We report the split rather than choosing the winner per class.

### 6.7 Where the gain comes from, per frame

Section 6.6 leaves one question open. The depth-aware homography and the per-target correction both help, and both differ from the depth-blind global similarity in two ways at once: they know about depth, and they perturb the warp. If the gain were driven by perturbation magnitude rather than by depth, the diagnosis of §6.4 would be wrong even though its remedy works.

We answer it with a placebo, and then localise the effect.

**The placebo.** Within each frame we permute which object's correction is applied to which track, subject to no object keeping its own. The set of corrections is unchanged, so their magnitude and direction distributions are preserved exactly; the only thing destroyed is the pairing between an object and the correction its depth implies. Everything else — the ground-truth gate, the fallback to the shared warp, the plausibility guard, the frozen detections — is identical to the per-target arm. Permutations are seeded per (sequence, frame) and reproducible.

**Table 10** The shuffled placebo: the same corrections, applied to the wrong objects.

| Configuration | ped HOTA | ped IDSW | car HOTA | car IDSW |
|---|---|---|---|---|
| global similarity (no per-object correction) | 46.744 | 108 | 66.267 | 129 |
| **shuffled placebo** | **46.161** | **165** | **62.612** | **395** |
| per-target | 47.576 | 88 | 66.473 | 117 |

The placebo is not merely worse than the per-target arm — it is **worse than applying no per-object correction at all**, by 3.58 HOTA on cars [+2.20, +4.96] and by 25.6 identity switches per weighted sequence [−36.47, −10.12]. Against the per-target arm it loses 1.18 HOTA on pedestrians [+0.43, +4.64] and 3.79 on cars [+2.23, +5.26]. A perturbation matched in magnitude and direction but wrong in its assignment is actively harmful, which is what one would expect if the correction carries real per-object information and not if its benefit were perturbation magnitude.

This rules out the alternative explanation. It does not rule out every alternative: the pairing the placebo destroys is depth-derived by construction, so the test shows that *object-specific* information matters and that it is the information our per-object warp encodes, which is depth. A reader who wished to attribute the effect to some other object-specific quantity correlated with depth would need to name one.

**Where it acts.** If the effect is depth-driven it should concentrate in the frames where the shared warp serves a class worst. Exposure is computed from the same two warps that produced the two trackers, so what follows localises the intervention rather than independently confirming its cause; the placebo above is what does the latter.

We defined exposure per (sequence, frame, class) as the median absolute difference, at box centres, between an object's own depth-derived warp and the shared depth-blind one — the disagreement that depth information removes. Improvement is the per-frame identity-switch difference between the two configurations. Neither quantity was used to build either tracker.

The result is Table 10, plotted in Figure 6.

**Table 11** Pedestrian identity switches by exposure quartile, 2,377 frames.

| Quartile | Median exposure (px) | IDSW, global | IDSW, per-target | Improvement | Per 1,000 frames |
|---|---|---|---|---|---|
| Q1 (least exposed) | 0.019 | 115 | 115 | **0** | 0.00 |
| Q2 | 0.309 | 57 | 59 | −2 | −3.37 |
| Q3 | 0.914 | 59 | 57 | +2 | +3.37 |
| **Q4 (most exposed)** | **3.584** | **49** | **29** | **+20** | **+33.67** |
| Total | | 280 | 260 | 20 | |

All 20 of the improvement comes from the top exposure quartile. The bottom quartile — where the shared warp is already almost correct — yields exactly zero, although it carries more identity switches than any other quartile. The right test is a paired permutation: shuffle the pairing between a frame's exposure and its improvement and ask how often the top quartile collects as much as observed. Over 20,000 permutations the observed +20 sits against a null mean of 4.99 (sd 3.70), **p = 0.0001**. A Spearman correlation over the same data is +0.058 (p = 0.0047); we report it for completeness and do not lead with it, because a rank correlation over a sparse signed count — only 50 of the 2,377 frames have any nonzero improvement — understates a concentration this complete.

The counter is validated: its total, 280 − 260 = 20, reproduces TrackEval's independently computed pedestrian delta (108 − 88 = 20) exactly.

The same counter is *not* reliable for cars and we do not use it there. The same permutation test on cars returns p = 0.946 — significant in the opposite direction. Its car total also disagrees with TrackEval in sign, and the cause is identified: the COCO detector labels cars, trucks and buses alike as vehicles, while KITTI's evaluation protocol treats Van and Truck as ignore regions, so the per-frame counter and TrackEval are not counting the same events. Reporting a quartile table under those conditions would be reporting an artefact. The car column of §6.6 therefore stands without a verified mechanism, which is one more reason it is marked not established.

---
## 7 Deployability

The §6 comparison uses ground-truth ego-motion and ground-truth depth. It is an upper bound, and an upper bound is only interesting if something can be built underneath it. This section separates the three ground-truth inputs, because they are not equally hard to replace, and an earlier version of our own analysis treated them as if they were.

### 7.1 What each correction actually needs

The §6 comparisons use ground-truth ego-motion throughout, and the oracle rows also use ground-truth depth. The three inputs are not equally hard to replace, and the two prescriptions differ sharply in what they need.

**Ego-motion.** On a vehicle this is an onboard sensor reading. KITTI's `oxts` stream is the platform's own GPS/INS, and using it is realistic rather than oracular — with the caveat in §9.3 that it is a post-processed survey-grade unit, not a commodity one, and that we have not substituted visually estimated ego-motion. Both prescriptions need it equally.

**Depth.** This must be estimated, and §7.3 replaces it. The depth-aware homography of §6.4 already uses *estimated* depth: the background points it fits to are back-projected at monocular depths, not annotated ones. Nothing in that configuration reads ground truth.

**Target identity.** Here the two prescriptions part. The depth-aware homography needs none: it is a single warp fitted to background points, applied to every track. The per-target correction of §6.6 needs to know which object a track is, and in the configuration we report it obtains that by matching against **annotated** boxes (§6.5) — which is why we report it as an upper bound and not as a method. The `per_target_depth` pipeline below eliminates identity by querying the depth map at the tracker's own predicted box, and §7.3 evaluates that version.

So the remedy §6 arrives at needs one estimated quantity, depth, and an ego-motion source; the per-object alternative needs those plus an association the tracker does not have. That asymmetry, rather than any metric difference, is the strongest reason to prefer the global correction.

### 7.2 How much depth error the gain survives

Monocular depth error is approximately multiplicative, so we inject `z' = z · exp(N(0, σ))` and re-run the whole pipeline. Seeding is per sequence and reproducible.

Table 12 and Figure 7 give the sweep.

**Table 12** Pedestrian sensitivity to injected depth noise. Reference: global-similarity oracle, HOTA 46.744, IDSW 108.

| σ | ≈ relative error | HOTA | vs global oracle | AssA | IDSW |
|---|---|---|---|---|---|
| 0.00 | 0 % | 47.576 | **+0.832** | 51.852 | 88 |
| 0.05 | 5 % | 47.865 | **+1.121** | 52.541 | 85 |
| 0.10 | 11 % | 47.864 | **+1.120** | 52.532 | 85 |
| 0.20 | 22 % | 47.644 | **+0.900** | 52.086 | 87 |
| 0.30 | 35 % | 47.540 | **+0.796** | 51.848 | 100 |
| 0.50 | 65 % | 46.385 | −0.359 | 49.188 | 153 |

The gain is flat to roughly 22 % relative depth error, still clearly positive at 35 %, and collapses only at 65 %. Published monocular metric-depth models reach roughly 5–10 % AbsRel on KITTI, so the required precision exists.

The σ = 0.05 and 0.10 rows sit slightly above the zero-noise row. That difference, 0.29 HOTA, is a quarter of the width of the confidence interval on the gain itself (Table 8: [+0.067, +1.226]), and we do not read it as "noise helps". The honest statement is that the curve is flat across that range.

On cars the same sweep gives +0.206 at σ = 0, then −0.178 at σ = 0.05 and negative at every larger σ tested. The car effect turns negative at the smallest noise level applied, which is consistent with §6.6: it was inside its own uncertainty to begin with.

The sweep has a known optimism. Injected noise is independent per object; real monocular error is spatially correlated, so a real model's errors on two nearby objects are not independent draws. The sweep therefore maps the *shape* of the tolerance, and the load-bearing evidence is the next subsection, which uses a real model.

### 7.3 A real monocular depth model

We replaced ground-truth depth with Depth-Anything-V2 Metric (Yang et al., 2024; VKITTI outdoor checkpoint), querying the depth map at the tracker's own predicted box, and re-ran the whole ladder. Table 13 gives the result; Figure 7 marks it against the synthetic sweep.

**Table 13** The deployable ladder on KITTI. Depth is estimated throughout; ego-motion is the platform's own sensor.

*Pedestrian*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 45.499 | 47.877 | 43.996 | 279 |
| online GMC | 47.428 | 51.448 | 44.617 | 126 |
| global similarity, estimated depth | 46.518 | 49.980 | 44.449 | 117 |
| **per-target, estimated depth** | **47.394** | **51.429** | **44.796** | **85** |
| per-target, ground-truth depth (§6.6) | 47.576 | 51.852 | 44.748 | 88 |

*Car*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 64.792 | 70.339 | 60.584 | 401 |
| online GMC | 65.265 | 70.137 | 61.450 | 165 |
| global similarity, estimated depth | 65.278 | 70.382 | 61.268 | 218 |
| **per-target, estimated depth** | **66.473** | **72.011** | **62.112** | **134** |
| per-target, ground-truth depth (§6.6) | 66.473 | 72.432 | 61.730 | 117 |

The two car HOTA values in the last two rows are not a transcription error: they are 66.47275 with estimated depth and 66.47348 with ground truth, and they round to the same three decimals by coincidence.

With bootstrap intervals over the 21 sequences, against the same-depth global baseline:

| Comparison | Class | HOTA | AssA | IDSW |
|---|---|---|---|---|
| per-target − global, both estimated depth | ped | **+0.855 [+0.141, +1.339]** | **+1.293 [+0.108, +2.124]** | **−4.01 [−6.65, −0.27]** |
| per-target − global, both estimated depth | car | **+1.206 [+0.557, +1.752]** | **+1.705 [+0.509, +2.752]** | −4.35 [−11.91, +0.14] |
| per-target (estimated depth) − online GMC | ped | −0.207 [−0.852, +1.766] | −0.554 [−1.792, +2.970] | −2.11 [−12.66, +0.73] |
| per-target (estimated depth) − online GMC | car | **+1.206 [+0.154, +2.104]** | +1.850 [−0.210, +3.538] | −2.57 [−7.11, +0.74] |

The pedestrian gain over the global baseline is **+0.855** with estimated depth against **+0.842** with ground truth. Replacing the oracle costs essentially nothing, and the identity-switch reduction becomes larger rather than smaller. The core claim of §6 therefore does not depend on ground-truth depth.

Two things must be said against this result. First, the checkpoint is domain-matched: it is fine-tuned on a synthetic replica of KITTI, so this is a best-case deployability test and not a cross-domain one. Second, and more important:

**Against plain image-based GMC, the per-target pipeline with estimated depth is not established on pedestrians.** The interval is [−0.852, +1.766] on HOTA and [−12.66, +0.73] on identity switches; both cross zero. On cars its HOTA comparison against online GMC does exclude zero (+1.206 [+0.154, +2.104]) while its association metrics do not.

This is the arm §6.6 supersedes, and we keep it because the comparison is informative: the per-target pipeline needs estimated depth *and* an association to apply it, and it does not beat the shipped compensator on pedestrians, while the depth-aware global homography needs only the depth map and does beat it on cars (+1.187 [+0.262, +1.922]) while cutting pedestrian identity switches from 126 to 97. Both are built from the same monocular depth. The difference between them is what the depth is used for: fitting one better warp, or correcting each track separately.

---

### 7.4 What it costs

No published camera-motion ablation we are aware of omits the throughput cost, and ours should not either — particularly because §7.3's pipeline runs a monocular depth network on every frame. Measured on the hardware every other result in this paper was produced on:

Table 14 gives the cost of each component.

**Table 14** Per-frame cost of each component, median over 120 frames.

| Component | Input | Median | Throughput of that step alone |
|---|---|---|---|
| Sparse-flow GMC | 640 × 480 (MOT17) | 6.5 ms | 154 fps |
| Sparse-flow GMC | 1238 × 374 (KITTI) | 7.4 ms | 136 fps |
| Depth-Anything-V2 Metric ViT-L | 1238 × 374 | **480.9 ms** | **2.1 fps** |

**The depth network costs 65 times a compensation call at the same resolution.** That is the price of the §6.4 remedy, and it is the honest headline for it: the depth-aware homography buys +1.19 HOTA on cars and 41 fewer pedestrian identity switches, at 481 ms per frame rather than 7. Everything else it needs is cheap — one `findHomography` on a few hundred background points, once per frame.

Two things soften that number without excusing it. The depth map is increasingly computed anyway in the pipelines this correction would live in, in which case the marginal cost is the homography fit alone. And a cheaper depth source works: on a vehicle a ground plane from calibration gives every contact point a range for free, which is UCMCTrack's construction and is why §2.4 places it as the relevant competitor rather than as an alternative we have beaten. What we can say is that the *quantity* to supply is depth; where it comes from is an engineering choice this paper does not settle.

A second, cheaper recommendation follows from §5.5 rather than from §6, and we mark its evidence: on a static-camera sequence compensation has nothing to correct, and detecting that is trivial because the estimated inter-frame displacement is sub-pixel (0.689 px at the MOT20 median, §4.1). Deep OC-SORT reports no improvement from compensation on MOT20 and ImprAsso disables it there as published practice. We did not run a `none`-versus-`online` arm on MOT20 ourselves, so this rests on their experiments and our measurement that there is no error there to remove, not on a tracking experiment of ours.

## 8 What We Could Not Explain

The pedestrian result is established and the car result is not, on the same sequences, the same frames and the same camera motion. We do not know why, and we report the two explanations we pre-specified and then refuted.

The two explanations, their pre-specification and the measurements that refuted them are given in full in Supplementary S3. In brief: pedestrians are **not** further from the frame's median depth than cars (median |log(z/z_median)| 0.246 against 0.325; a one-sided Mann–Whitney in the hypothesised direction returns p = 1.000), and pedestrian boxes are **not** more exposed per unit of error (3.28 % of pedestrian object-frames exceed one third of the box width against 3.33 % for cars — the two classes are equally exposed, so the explanation has nothing to work with).

We did not look for a third. A class difference can always be explained by a hypothesis generated after seeing which class won and tested on the same data that produced the question; searching until one fits produces an explanation with no evidential value and a false impression of understanding. The class difference is reported as unexplained, and it is the single largest gap in the paper.

We can say what it is *not*. It is not a mechanism failure in the pedestrian result, which §6.7 verifies per frame. It is not an artefact of a single sequence in either class — under leave-one-sequence-out the pedestrian gain stays within [+0.332, +1.025] and the car gain within [+0.096, +0.393], neither changing sign. And it is not a difference in exposure to the mechanism, by candidates 1 and 2 above. What separates the two classes is the width of their confidence intervals and their behaviour under depth noise, not the influence of any one sequence.

---

## 9 Limitations and Conclusion

### 9.1 The evaluation service is offline

The MOTChallenge evaluation server has been withdrawn. `motchallenge.net` now answers HTTP 410 Gone with a notice from the benchmark's maintainers at TUM, last modified 2026-09-08 and re-verified by us on 2026-09-23:

> "This service is currently offline. The MOTChallenge benchmark website is not in operation. The evaluation server, submissions and user accounts are offline. The dataset archives remain available at their existing addresses. […] The leaderboards have been preserved as a static archive. All published results (state of 16 April 2026) with method pages, per-sequence results, result videos, raw result files and a CSV export per benchmark."

Three consequences. The dataset archives remain downloadable, so we used the authoritative source rather than a mirror. No contemporary submission can report new MOT17 or MOT20 *test-set* numbers, ours included; every MOTChallenge figure in this paper is on the standard validation-half protocol, and we report no test-set number. And the half-validation protocol is now the field-wide condition rather than a deficiency of this work — which makes the protocol discipline of §3.5 more load-bearing, not less, since cross-paper comparison through a common server is no longer available to anyone.

### 9.2 What we could not measure

**The shared-warp limitation is established on KITTI and inferred elsewhere.** This is the sharpest limit on the paper's scope and we tried twice to remove it. Measuring within-frame residual spread requires separating camera-induced motion from the objects' own, which on KITTI we do with ground-truth ego-motion and 3D labels. On MOT17, MOT20 and UAVDT neither is available, and both substitutes we built fail:

*Observed-displacement spread.* Fitting the best global similarity to objects' observed displacements and measuring the residual spread gives 4.69 px on MOT17, 5.56 on MOT20, 2.50 on UAVDT and 7.07 on KITTI — where the ground-truth figure is 5.88. The statistic is dominated by the objects' own motion, and differently so across benchmarks: pedestrians walk in all directions, vehicles follow a road. It does not discriminate.

*A depth–residual correlation as a parallax indicator.* Under pure rotation the induced motion is depth-independent whatever the depths are, so the per-frame Spearman correlation between target depth and residual should be near zero on a rotating camera and negative on a translating one. Estimating depth monocularly, the medians are −0.306 (MOT17), −0.243 (MOT20), −0.200 (UAVDT) and −0.214 (KITTI), against −0.400 for KITTI from ground truth. MOT17 is the *most* negative. The confound is that residual magnitude scales as 1/z for any image motion, including the objects' own, so nearer objects show larger residuals whether or not the camera translates. It does not discriminate either.

Both are reported because a reader should know the claim's support: on MOT17, MOT20 and UAVDT the absence of the shared-warp limitation is an inference from the compensation-value axis, which *is* measured there, together with the geometry of §6.1 — not a direct measurement of within-frame spread.

One measurement did overturn an explanation we had been using. We had attributed the pedestrian benchmarks' immunity to near-uniform target depth. Estimating within-frame target depth ratios monocularly at the contact point, the median is **5.60 on MOT17 and 6.51 on MOT20 against 3.57 on KITTI**: the pedestrian benchmarks span *more* depth variation, not less. What protects them is the absence of camera translation, under which depth-dependence vanishes however widely depths are spread. The corrected statement is narrower and more falsifiable, and it also removes the claim in an earlier draft that UAVDT is protected by near-uniform depth at altitude, which its own attribute statistics contradict.

### 9.3 Scope

*The MOT17 reference warp is a better estimate, not truth*, so every compensation-error figure on MOT17 and MOT20 is a lower bound. It also shares the online estimator's four-degree-of-freedom family and masks annotated foreground before extracting features, so model-family error cancels in the contrast: §5's bound covers methods that remain within that family, which is where every deployed compensator we know of sits, but not a compensator that changes family.

*KITTI's ego-motion is a sensor estimate, not ground truth.* It is an OXTS RT3003 GPS/INS at 10 Hz, composed through the camera calibration chain. At KITTI's focal length of about 721 px, one milliradian of attitude error is 0.7 px of image motion — larger than the 0.101 px oracle residual quoted in §6.2 and comparable to §6.4's 0.537 px. We do not propagate that error, and the two sub-pixel figures in §6 should be read as being at or below the sensor's own floor. The 5.878 px within-frame spread and the 2.08 % gate rate are an order of magnitude above it and are unaffected. On a vehicle the same stream is an onboard reading rather than an oracle, but it is a post-processed survey-grade one, not a commodity sensor, and we have not tested the method with visually estimated ego-motion.

*The depth model is domain-matched.* Depth-Anything-V2 Metric VKITTI is fine-tuned on a synthetic replica of KITTI, so §7.3 is a best-case deployability test, and §7.4 shows it costs 65× the compensation it improves.

*The depth-noise sweep injects independent per-object noise*, while real monocular error is spatially correlated. That curve is optimistic; §7.3 is the load-bearing evidence.

*The KITTI tracker is motion-only and is not a tuned KITTI system.* Its detector misses 44 % of ground-truth pedestrians and 43 % of its pedestrian detections are false positives; the whole per-target result is 20 identity-switch events out of 108. More importantly the asymmetry is against us: the *negative* MOT17 result is tested both with and without an appearance channel (§5.3, §5.4), while the *positive* KITTI result is established only in the motion-only configuration — which is the setting that most favours a motion-side intervention, and the one in which §1's motivating coupling does not exist at all. The claim is scoped to motion-only association accordingly.

*The KITTI comparison is within-sample.* No split is needed for the detector, which never saw KITTI, but the tracker hyperparameters, the plausibility guard's bounds, the moving-frame threshold and — most consequentially — two successive respecifications of the oracle were all chosen with the results visible. Both respecifications were geometrically motivated and are described in §6.5, but the stopping rule was that the oracle stopped looking wrong, on the data the result is reported on.

*UAVDT has no ground-truth ego-motion*, so §5.6 compares `none` against `online` and cannot bound what a perfect warp would be worth there. It is also the only tracking arm in the paper with no interval, on a pipeline weak enough (HOTA 43.9, 3,342 identity switches) that a floor effect cannot be excluded.

*The class difference is unexplained* (§8), and *no controlled robot study was performed*; the recording protocol is specified but not executed.

### 9.4 Changes from earlier analysis

Four measurements in this paper replace earlier ones of our own that were wrong, and three claims were withdrawn when sequence-level intervals replaced point estimates. Each is described where it occurs — the oracle specification in §6.5, the warp-family test in §6.4, the oracle configuration's fallback in §5.3, and the sign of the perfecting effect in §5.4 — and Supplementary S2 collects them with what each earlier version reported and how it was found. We summarise them rather than omit them because a measurement paper that reports only its final state is not auditable, and because two of the four were found by a reviewer rather than by us.

### 9.5 Conclusion

We set out to reduce identity switches by detecting when camera-motion compensation is unreliable and down-weighting it. The instruments built to justify that method refuted it, and three later rounds of measurement refuted three of our own replacements — including, twice, an experiment whose construction guaranteed the answer we had reached. Each is recorded in §9.4 and Supplementary S2, and the last of the three is the reason this paper's prescription is not the one we expected to write.

What stands is a bound and a diagnosis. On MOT17 with camera motion present, a perfect warp is worth −0.04 HOTA with a 95 % upper bound of +0.05 without an appearance channel and +0.52 with one, against +3.43 for having a working compensator at all. Whatever a more robust compensator can recover on that benchmark, it is bounded well below what the field routinely claims for such modules, and it is indistinguishable from the difference between two ordinary implementations of an ordinary one. Compensation *accuracy*, in the sense of estimating a better member of the family the tracker already uses, is not where the headroom is.

Where a shared warp genuinely fails, the reason is that it takes no depth argument. On KITTI, after the best four-degree-of-freedom warp that could be fitted to the targets themselves, objects in one frame still need corrections differing by more than 5 px in 54.3 % of moving frames. We spent two experiments concluding that no global family could fix this and both were wrong by construction. A global homography fitted to background points at their estimated depths cuts that spread to 1.37 px, beats the compensator the tracker ships by +1.19 HOTA on cars, and commits 85 pedestrian identity switches against 126 — and it reads no annotations, needs no per-object association, and adds one `findHomography` call to a depth map the pipeline may already be computing. A per-target correction with ground-truth depth and ground-truth association adds nothing on top of it, and a placebo that keeps those corrections but applies them to the wrong objects is worse than applying none — so what the correction carries really is object depth, and a global model that has depth is enough to deliver it.

Two lessons, one narrow and one not. The narrow one: if you compensate camera motion on a translating platform, give the warp depth rather than more degrees of freedom or a better fit within the same family — and if your scene has a dominant plane, eight degrees of freedom are the right eight. The general one is about what it takes to establish a negative. Three times in this work we concluded that something did not matter, and twice the conclusion was an artefact of how the treatment had been applied rather than of the quantity itself: a warp that was silently the online estimate on a fifth of the hardest sequence, and a homography that was silently absent on a third of moving frames. Both were found by running the released code, not by reading the manuscript. A null claim needs the treatment audited as carefully as the outcome, and the practical form of that audit is a script that recomputes the paper's numbers and fails on mismatch — which we release, and which did not catch either of these, because it checks values and not provenance.

---

## Data and Code Availability

All measurement code and all measurement data are released: 40 analysis scripts and 4 shell drivers, 21 result CSVs, the frozen detection manifests with per-file SHA-256, TrackEval output for all 61 tracker runs (44 on KITTI, 15 on MOT17, 2 on UAVDT), the script that regenerates every figure from those CSVs, the script that builds the submission LaTeX from the Markdown source, and `verify_numbers.py`, which recomputes the paper's numbers from source and exits non-zero on any mismatch. Repository: [URL, to be replaced by an archived DOI at submission]. The benchmarks themselves (MOT17, MOT20, UAVDT, KITTI) are public and are not redistributed; the artefacts each result depends on, and the SHA-256 of those whose identity affects a number, are listed in the release.

## Ethics Statement

This work uses only public computer-vision benchmarks. It involved no human subjects, no new data collection from people, and no personally identifying information beyond what those benchmarks already contain. No ethics approval was required.

## Responsible Use

Multi-object tracking of pedestrians is surveillance-adjacent, and this paper improves pedestrian tracking under vehicle motion. We note the dual use plainly: the same measurement applies to autonomous-driving safety, where losing a pedestrian's identity across an occlusion is a hazard, and to persistent tracking of individuals, where maintaining it is the harm. Most of this paper is deflationary — it removes a claimed capability from three widely used benchmarks — but the KITTI result is a genuine improvement in pedestrian identity preservation, and we state that rather than leaving it implied.

## AI-Assistance Disclosure

A large language model (Anthropic Claude) was used throughout this work as a research assistant: for literature search, for writing and debugging the measurement and analysis code, for adversarial review of the experimental design at two pre-registered checkpoints, for a five-perspective simulated review of the completed draft, and for drafting this manuscript. Every numerical result reported here was produced by executing the released code on the released data; no number was generated by a language model, and `verify_numbers.py` exists so that a reader can check that mechanically. The authors verified the instruments, specified the experiments and the pre-commitments, made every methodological decision, and are responsible for the content — including the four errors recorded in §9.4, all of which were found by measurement during that process.

## CRediT Author Statement

**Yifu Zhao**: [roles]. **Xiaofan Zou**: [roles]. **Junhao Wei**: [roles]. **Yanxiao Li**: [roles]. **Haochen Li**: [roles]. **Sio-Kei Im**: [roles]. **Yapeng Wang**: [roles]. **Xu Yang**: [roles]. All authors read and approved the final manuscript.

*To be completed by the authors before submission. The contribution taxonomy is CRediT (Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Resources, Data curation, Writing — original draft, Writing — review & editing, Visualization, Supervision, Project administration, Funding acquisition). We have not assigned roles on the authors' behalf.*

## Funding

This work is supported by the grant from Macao Polytechnic University (RP/FCA-06/2026) and the Macao Science and Technology Development Fund (FDCT-MOST: 0018/2025/AMJ).

## Competing Interests

The authors declare no competing interests.

---

## References

Aharon, N., Orfaig, R., & Bobrovsky, B.-Z. (2022). BoT-SORT: Robust associations multi-pedestrian tracking. *arXiv preprint* arXiv:2206.14651. https://doi.org/10.48550/arXiv.2206.14651

Bewley, A., Ge, Z., Ott, L., Ramos, F., & Upcroft, B. (2016). Simple online and realtime tracking. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3464–3468). https://doi.org/10.1109/ICIP.2016.7533003

Bouguet, J.-Y. (2001). *Pyramidal implementation of the affine Lucas–Kanade feature tracker: Description of the algorithm*. Intel Corporation, Microprocessor Research Labs.

Cao, J., Pang, J., Weng, X., Khirodkar, R., & Kitani, K. (2023). Observation-centric SORT: Rethinking SORT for robust multi-object tracking. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition* (pp. 9686–9696). https://doi.org/10.1109/CVPR52729.2023.00934

Chapel, M.-N., & Bouwmans, T. (2020). Moving objects detection with a moving camera: A comprehensive review. *Computer Science Review*, 38, 100310. https://doi.org/10.1016/j.cosrev.2020.100310

Claasen, P. J., & de Villiers, J. P. (2026). One homography is all you need: IMM-based joint homography and multiple object state estimation. *Expert Systems with Applications*, 302, 130562. https://doi.org/10.1016/j.eswa.2025.130562

Dendorfer, P., Rezatofighi, H., Milan, A., Shi, J., Cremers, D., Reid, I., Roth, S., Schindler, K., & Leal-Taixé, L. (2020). MOT20: A benchmark for multi object tracking in crowded scenes. *arXiv preprint* arXiv:2003.09003. https://doi.org/10.48550/arXiv.2003.09003

Du, Y., Zhao, Z., Song, Y., Zhao, Y., Su, F., Gong, T., & Meng, H. (2023). StrongSORT: Make DeepSORT great again. *IEEE Transactions on Multimedia*, 25, 8725–8737. https://doi.org/10.1109/TMM.2023.3240881

Du, Y., Wan, J., Zhao, Y., Zhang, B., Tong, Z., & Dong, J. (2021). GIAOTracker: A comprehensive framework for MCMOT with global information and optimizing strategies in VisDrone 2021. In *Proceedings of the IEEE/CVF International Conference on Computer Vision Workshops* (pp. 2809–2819). https://doi.org/10.1109/ICCVW54120.2021.00315

Evangelidis, G. D., & Psarakis, E. Z. (2008). Parametric image alignment using enhanced correlation coefficient maximization. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 30(10), 1858–1865. https://doi.org/10.1109/TPAMI.2008.113

Fischler, M. A., & Bolles, R. C. (1981). Random sample consensus: A paradigm for model fitting with applications to image analysis and automated cartography. *Communications of the ACM*, 24(6), 381–395. https://doi.org/10.1145/358669.358692

Ge, Z., Liu, S., Wang, F., Li, Z., & Sun, J. (2021). YOLOX: Exceeding YOLO series in 2021. *arXiv preprint* arXiv:2107.08430. https://doi.org/10.48550/arXiv.2107.08430

Geiger, A., Lenz, P., & Urtasun, R. (2012). Are we ready for autonomous driving? The KITTI vision benchmark suite. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 3354–3361). https://doi.org/10.1109/CVPR.2012.6248074

Geiger, A., Lenz, P., Stiller, C., & Urtasun, R. (2013). Vision meets robotics: The KITTI dataset. *The International Journal of Robotics Research*, 32(11), 1231–1237. https://doi.org/10.1177/0278364913491297

He, L., Liao, X., Liu, W., Liu, X., Cheng, P., & Mei, T. (2020). FastReID: A PyTorch toolbox for general instance re-identification. *arXiv preprint* arXiv:2006.02631. https://doi.org/10.48550/arXiv.2006.02631

Irani, M., & Anandan, P. (1998). A unified approach to moving object detection in 2D and 3D scenes. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 20(6), 577–589. https://doi.org/10.1109/34.683770

Liu, Z., Wang, X., Wang, C., Liu, W., & Bai, X. (2025). SparseTrack: Multi-object tracking by performing scene decomposition based on pseudo-depth. *IEEE Transactions on Circuits and Systems for Video Technology*. Preprint arXiv:2306.05238. https://doi.org/10.48550/arXiv.2306.05238

Lucas, B. D., & Kanade, T. (1981). An iterative image registration technique with an application to stereo vision. In *Proceedings of the 7th International Joint Conference on Artificial Intelligence* (Vol. 2, pp. 674–679).

Luiten, J., & Hoffhues, A. (2020). *TrackEval* [Computer software]. https://github.com/JonathonLuiten/TrackEval

Luiten, J., Ošep, A., Dendorfer, P., Torr, P., Geiger, A., Leal-Taixé, L., & Leibe, B. (2021). HOTA: A higher order metric for evaluating multi-object tracking. *International Journal of Computer Vision*, 129(2), 548–578. https://doi.org/10.1007/s11263-020-01375-2

Ma, J., Luo, H., Chen, Q., Qi, Y., Sun, Y., Beheshti, A., Zhang, J., & Yang, M.-H. (2026). Tracking the unstable: Appearance-guided motion modeling for robust multi-object tracking in UAV-captured videos. In *Proceedings of the AAAI Conference on Artificial Intelligence*. Preprint arXiv:2508.01730. https://doi.org/10.48550/arXiv.2508.01730

Maggiolino, G., Ahmad, A., Cao, J., & Kitani, K. (2023). Deep OC-SORT: Multi-pedestrian tracking by adaptive re-identification. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3025–3029). https://doi.org/10.1109/ICIP49359.2023.10222576

Mahdian, N., Jani, M., Soufi Enayati, A. M., & Najjaran, H. (2024). Ego-motion aware target prediction module for robust multi-object tracking. *arXiv preprint* arXiv:2404.03110. https://doi.org/10.48550/arXiv.2404.03110

Milan, A., Leal-Taixé, L., Reid, I., Roth, S., & Schindler, K. (2016). MOT16: A benchmark for multi-object tracking. *arXiv preprint* arXiv:1603.00831. https://doi.org/10.48550/arXiv.1603.00831

Safdarnejad, S. M., Liu, X., & Udpa, L. (2015). Robust global motion compensation in presence of predominant foreground. In *Proceedings of the British Machine Vision Conference* (pp. 21.1–21.11). https://doi.org/10.5244/C.29.21

Shi, J., & Tomasi, C. (1994). Good features to track. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 593–600). https://doi.org/10.1109/CVPR.1994.323794

Solano-Carrillo, E., Sattler, F., Alex, A., Klein, A., Pereira Costa, B., Bueno Rodriguez, A., & Stoppe, J. (2024). UTrack: Multi-object tracking with uncertain detections. *arXiv preprint* arXiv:2408.17098. https://doi.org/10.48550/arXiv.2408.17098

Stanczyk, T., Yoon, S., & Brémond, F. (2026). Training-free long-term multi-object tracking for sports video analytics. *arXiv preprint* arXiv:2608.15688. https://doi.org/10.48550/arXiv.2608.15688

Stanojević, V. D., & Todorović, B. T. (2024). BoostTrack: Boosting the similarity measure and detection confidence for improved multiple object tracking. *Machine Vision and Applications*, 35(3), 53. https://doi.org/10.1007/s00138-024-01531-5

Wojke, N., Bewley, A., & Paulus, D. (2017). Simple online and realtime tracking with a deep association metric. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3645–3649). https://doi.org/10.1109/ICIP.2017.8296962

Wu, J., & Liu, Y. (2024). DepthMOT: Depth cues lead to a strong multi-object tracker. *arXiv preprint* arXiv:2404.05518. https://doi.org/10.48550/arXiv.2404.05518

Yang, L., Kang, B., Huang, Z., Zhao, Z., Xu, X., Feng, J., & Zhao, H. (2024). Depth Anything V2. *arXiv preprint* arXiv:2406.09414. https://doi.org/10.48550/arXiv.2406.09414

Yang, Y., Shim, K., Ko, K., & Kim, C. (2026). Tracking-by-detection in multi-object tracking: Survey and experiments. *arXiv preprint* arXiv:2609.08265. https://doi.org/10.48550/arXiv.2609.08265

Yi, K., Luo, K., Luo, X., Huang, J., Wu, H., Hu, R., & Hao, W. (2024). UCMCTrack: Multi-object tracking with uniform camera motion compensation. In *Proceedings of the AAAI Conference on Artificial Intelligence*, 38(7), 6702–6710. https://doi.org/10.1609/aaai.v38i7.28493

Yu, H., Li, G., Zhang, W., Huang, Q., Du, D., Tian, Q., & Sebe, N. (2020). The unmanned aerial vehicle benchmark: Object detection, tracking and baseline. *International Journal of Computer Vision*, 128(5), 1141–1159. https://doi.org/10.1007/s11263-019-01266-1

Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. In *Computer Vision – ECCV 2022* (Lecture Notes in Computer Science, Vol. 13682, pp. 1–21). https://doi.org/10.1007/978-3-031-20047-2_1

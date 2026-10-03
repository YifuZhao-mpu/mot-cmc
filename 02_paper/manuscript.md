# Camera-Motion Compensation in Tracking-by-Detection: Accuracy Headroom and Depth-Aware Shared Warps

**Yifu Zhao**^1^ · **Xiaofan Zou**^2^ · **Yanxiao Li**^1^ · **Junhao Wei**^1^ · **Sio-Kei Im**^3^ · **Yapeng Wang**^1,\*^ · **Xu Yang**^1^ ^1^ Faculty of Applied Sciences, Macao Polytechnic University, Macao 999078, China ^2^ School of Mechanical and Electrical Engineering and Automation, Shanghai University, Shanghai 200444, China ^3^ Macao Polytechnic University, Macao 999078, China \* Corresponding author: yapengwang@mpu.edu.mo

| Author | ORCID | E-mail |
|---|---|---|
| Yifu Zhao | 0009-0004-2363-9269 | p2523269@mpu.edu.mo |
| Xiaofan Zou | 0009-0005-5995-3150 | xiaofanz@shu.edu.cn |
| Yanxiao Li | 0009-0008-3389-1619 | p2525981@mpu.edu.mo |
| Junhao Wei | 0009-0006-0553-2032 | p2312195@mpu.edu.mo |
| Sio-Kei Im | 0000-0002-5599-4300 | marcusim@mpu.edu.mo |
| Yapeng Wang | 0000-0002-1085-5091 | yapengwang@mpu.edu.mo |
| Xu Yang | 0000-0002-7037-3609 | xuyang@mpu.edu.mo |

---

## Abstract

Tracking-by-detection uses a shared two-dimensional warp to preserve association under camera motion. Its accuracy headroom and depth-dependent geometry require separate evaluation. We measure the headroom in compensation accuracy and identify depth-aware global correction as a way to improve tracking under camera translation. On MOT17's moving-camera sequences, replacing the online estimate with a non-causal oracle warp changes higher-order tracking accuracy (HOTA) by **−0.04 (95 % confidence interval [−0.20, +0.05])** without an appearance channel and **+0.19 [+0.05, +0.52]** with one, against **+3.43 [+1.01, +5.52]** for having a working compensator at all. On KITTI, where the camera translates, a shared four-degree-of-freedom warp leaves depth-dependent residuals: after the least-squares similarity fitted to the targets themselves, objects in one frame still need corrections differing by more than 5 px in 27.1 % of moving frames. A global homography fitted to background points at their monocularly estimated depths — using sensor ego-motion — cuts the within-frame residual spread from 8.67 px to **1.37 px**, and beats the compensator the tracker ships by **+1.19 HOTA [+0.26, +1.92]** on cars. On pedestrians it cuts identity switches from **126 to 97**, and to **85** when the same warp is applied through each box's contact point. The global model supplies this correction without per-object association. The car HOTA gain persists at 65 % injected independent depth error (+1.27 [+0.34, +2.05]). All measurement code and data are released, together with a script that recomputes the paper's numbers from source. **Keywords** Multi-object tracking · Camera motion compensation · Evaluation methodology · Benchmark analysis · Identity switches · Reproducibility

---

## 1 Introduction

Tracking-by-detection depends on motion proximity and appearance similarity to preserve object identity under camera motion. In BoT-SORT's association step [1], after every track's Kalman prediction has been warped by the estimated camera motion, the appearance cost is admitted only when the motion cost agrees. An inaccurate warp can move the prediction away from the true detection; when the IoU cost exceeds the threshold, the appearance term is rejected. The solver also returns inlier statistics that can be used to assess compensation reliability. This coupling motivates measuring the effect of compensation error on association. The relevant quantity is the headroom that remains once a working compensator is in place. We measure this headroom through reference-warp substitution and gate-flip counting, then examine depth-aware correction on a translating camera platform. In BoT-SORT, the association cost combines IoU, detection score and appearance; covariance affects the Kalman prediction rather than the current association gate. Trackers whose association reads covariance use a different coupling, including the confidence-adaptive NSA-Kalman formulation [2].

### 1.1 Main Findings

**Compensation is accurate, by an external standard.** Across MOT17, MOT20 and UAVDT the online estimator's median transfer residual is 0.295–0.592 px, and the catastrophic regime the literature describes — degenerate fits from weak texture or foreground domination [3] — is rare in the measured frames. A residual is an internal-consistency statistic, so we also measure both pedestrian benchmarks against an offline reference: median disagreement is 0.150 px on MOT17's static sequences, 1.309 px on its moving ones, and 0.839 px across all 8,927 frames of MOT20, whose maximum over the whole benchmark is 2.73 px. MOT20-05 has 82 % of its inliers on pedestrians and a reference disagreement of 0.756 px, supporting a direct residual-based reliability measurement. **Its error is predictable from existing correspondences.** The median transfer residual of the inlier set, which the solver computes and the tracker discards, separates high-error from low-error frames with a held-out AUC of 0.866 under leave-one-sequence-out validation on the reference-quality-filtered frames described in §3.2. **Compensation-Accuracy Headroom on MOT17.** On MOT17 we measure the effect three ways. Geometrically, the median IoU cost of compensation error is 0.00085, and 0.284 % of ground-truth pairs lie in the reference-IoU band [0.5, 0.6] above the gate. Combinatorially, the gate's decision changes for 55 of 109,955 pairs, 34 of them harmfully. Empirically, on the four sequences that have camera motion, a non-causal oracle warp is worth −0.037 HOTA with a 95 % upper interval endpoint of **+0.05** without an appearance channel and +0.189 [+0.050, +0.517] with one — against **+3.426 [+1.007, +5.523]** for having a working compensator at all. **Depth-Dependent Residuals under Camera Translation.** On KITTI, after the least-squares four-degree-of-freedom warp fitted to the targets themselves, objects in one frame still need corrections differing by more than 5 px in 27.1 % of moving frames, and 2.18 % of object-frames are pushed past the association gate — a geometric gate-reach measurement (§6.3). **Residual Reduction with a Depth-Aware Global Homography.** Fitted to background points at their monocularly estimated depths, with the tracker's own detections masked out and sensor ego-motion, it reduces the within-frame residual spread to **1.370 px**, against 2.431 px for the least-squares similarity fitted to the targets themselves and 8.673 px for the deployed estimator, and cuts the fraction of frames whose targets disagree by more than 5 px from 27 % to 13 %. In tracking it beats the compensator BoT-SORT ships by **+1.187 HOTA [+0.262, +1.922]** on cars, and on pedestrians it commits **97 identity switches against 126** — 85 when applied through each box's contact point. The car HOTA gain persists at 65 % injected independent depth error, consistent with a fit that combines several hundred background depths. A diagnostic counter localises the car identity-switch reduction to the highest-exposure quartile (permutation test, p < 0.0001; §6.8). **The global correction provides a compact alternative to per-target correction.** Given ground-truth depth *and* ground-truth association, the per-target HOTA contrast against the depth-aware homography is −0.073 [−0.624, +0.392] on cars and +0.366 [−0.035, +0.986] on pedestrians. The global correction supplies spatially varying compensation without per-object association. **Correct object–correction pairing carries useful information.** Permuting which object's correction goes to which track within a frame — the same corrections, the same magnitudes and directions, only the pairing destroyed — is worse than applying no per-object correction at all, by 3.51 HOTA on cars [+2.12, +4.90] and 26.1 weighted identity switches per sequence. This control isolates the value of the object-specific pairing in the depth-derived correction.

### 1.2 Contributions

**A measurement of compensation-accuracy headroom.** On MOT17 with camera motion present, the reference-warp contrast is −0.04 HOTA with a 95 % upper interval endpoint of +0.05 motion-only and +0.52 with appearance (§5). **Oracle-Warp Contrast and Gate-Flip Counting**: an oracle-warp contrast that measures disagreement with a stronger estimate on benchmarks with no ground-truth camera motion, and a gate-flip count that measures changes in association *decisions* (§3). **A diagnosis and a depth-aware global correction on KITTI.** The geometry is the classical plane-plus-parallax result [4]; the controlled comparison shows that supplying depth to a *global* homography removes 82 % of the residual spread left by a background-fitted similarity and improves car HOTA over online compensation by +1.19 [+0.26, +1.92] (§6). **Controls for the role of depth and object-specific pairing.** The warp-family comparison, shuffled-correction placebo and depth-noise sweep distinguish geometric correction, correct pairing and noise tolerance (§6.4, §6.7, §7.3). The comparison with EMAP [5], which uses depth per object on KITTI with BoT-SORT, identifies the distinct role of this study: quantifying the accuracy headroom and evaluating depth-aware correction within a shared model.

---

## 2 Related Work

### 2.1 Compensation in Tracking-by-Detection

Tracking-by-detection associates detections to tracks through a cost matrix combining motion proximity and appearance similarity. The lineage runs from SORT [6] — Kalman filter plus Hungarian assignment on IoU — through DeepSORT [7], which added an appearance embedding and a Mahalanobis motion gate, to ByteTrack [8], which recovers low-confidence detections in a second association pass, and BoT-SORT [1], which is ByteTrack plus camera-motion compensation, a reparameterised Kalman state and an IoU–ReID fusion. Camera motion entered this lineage as a correction inserted between the Kalman prediction and the association. BoT-SORT uses image registration to improve overlap between predicted and detected boxes under camera motion. OC-SORT [9] reaches competitive results on MOT17, MOT20, DanceTrack and KITTI with no compensation module, absorbing camera motion through an observation-centric re-update of the track state instead.

### 2.2 Deployed Compensation Models

Two families are in use. **Sparse-flow GMC** — Shi–Tomasi corners [10] tracked by pyramidal Lucas–Kanade [11, 12] and fitted by RANSAC [13] — is what BoT-SORT and Deep OC-SORT use, and is the estimator measured in this paper. **ECC** [14], a direct intensity-alignment method, is what StrongSORT [15], BoostTrack [16] and UCMCTrack [17] use. The residual-based reliability signal in §4 uses the inlier correspondences of sparse-flow GMC; ECC uses direct intensity alignment. BoT-SORT identifies dense dynamic foreground and a lack of background keypoints as conditions that can disrupt camera-motion estimation. Several papers report what compensation is worth, and the published values differ by more than an order of magnitude depending on the estimator and the baseline. BoT-SORT's Table 1 gives +0.94 HOTA and +1.62 IDF1 on MOT17 for adding its sparse-flow GMC — the figure our §5.3 reproduces to within 0.06 HOTA. Deep OC-SORT [18] reports +1.53 HOTA on MOT17-val from compensation alone, with gains on MOT17 and DanceTrack and unchanged performance on static-camera MOT20. Section 4.2 adds an external measurement of compensation disagreement on MOT20.

### 2.3 Compensation Reliability

**McByte++** [19] applies compensation when the estimated transform satisfies geometric plausibility criteria and otherwise retains the unwarped prediction. Its frame-level decision on sports broadcast footage concerns transform plausibility; our reliability measurement uses inlier residuals. **IMM-JHSE** [20] places the homography and its dynamics inside the track state and uses an interacting-multiple-model filter to mix static and dynamic camera-motion models. It models uncertainty about the camera-motion regime. **NSA-Kalman** [2], adopted by StrongSORT and Deep OC-SORT, scales the observation noise by detection confidence and provides a confidence-adaptive treatment of state estimation.

### 2.4 Depth-Aware 2D Tracking and Ground-Plane Models

The reframing in §6 belongs to a line of work that treats depth as the missing argument of a 2D correction. **UCMCTrack** [17] abandons per-frame compensation altogether: it projects each box's contact point onto the ground plane, runs the Kalman filter in ground coordinates, associates by a mapped Mahalanobis distance, and uses one compensation parameter per sequence. A contact point on a known ground plane is already a per-target range measurement, obtained from calibration with no depth network. Its KITTI-test results are directly relevant to this paper: adding ECC compensation to it *costs* 2.9 HOTA on cars (77.1 → 74.2, AssA 77.2 → 71.7) and 0.9 on pedestrians (55.2 → 54.3), and its authors attribute this to "the inaccuracies present in the CMC parameters." Section 6 examines the role of warp accuracy and depth under a fixed tracking configuration. **EMAP** [5] is the closest prior work to our §6–§7 prescription. It reformulates the Kalman filter to decouple camera rotational and translational velocity from object trajectories using camera motion and depth, evaluates on KITTI with OC-SORT, Deep OC-SORT, ByteTrack and BoT-SORT as base trackers, and reports identity-switch reductions of 73 % and 21 % and HOTA gains above 5 %. Section 6 adds a controlled comparison of shared and per-target corrections — a per-target correction of identical functional form to the global one, against a depth-aware global homography and a target-depth-anchored global similarity — together with per-frame localisation of the tracking gain. On aerial footage, **AMOT** [21] adapts association using appearance-guided bidirectional spatial consistency; its adaptation is driven by appearance agreement rather than by compensation reliability, and it is the closest recent work to §5.6's benchmark. **SparseTrack** [22] and **DepthMOT** [23] use depth differently: the first decomposes crowded scenes into pseudo-depth bands for cascaded association, the second estimates depth and camera pose end to end and reports gains on VisDrone and UAVDT. **UTrack** [24] argues for homography-based compensation over the affine approximation for fast camera motion and evaluates on MOT17, MOT20, DanceTrack and KITTI. The underlying geometry is classical. That rotation induces a depth-independent image homography while translation induces a depth-dependent residual is the plane-plus-parallax decomposition [4], and the survey of moving-camera background modelling by Chapel and Bouwmans [25] treats plane-plus-parallax as a named category. Section 6 quantifies this geometry on a tracking benchmark and relates it to tracking outcomes.

### 2.5 Evaluation Methodology

HOTA [26] decomposes tracking quality into detection and association components and is the primary metric we report. A 2026 survey of tracking-by-detection [27] evaluates modules, including camera-motion compensation, under a common baseline to make their contributions comparable. We adopt the same discipline, with byte-identical detections across every compared configuration.

### 2.6 Position of This Study

Prior work establishes the value of enabling compensation and of incorporating depth. Our study measures the headroom in compensation accuracy once a working estimator is in place. Section 5 measures this headroom on MOT17 with camera motion present, with 95 % upper interval endpoints of +0.05 HOTA motion-only and +0.52 with appearance. Section 6 then isolates the geometric role of depth on KITTI: a depth-aware shared homography reduces residual spread and improves car tracking without per-object association.

## 3 Measurement Instruments

The instruments connect compensation geometry, association decisions and tracking outcomes. Figure 1 shows how they fit together: one detector pass, three warps for the same frame pair, and an otherwise fixed tracker into which exactly one of them is substituted.

### 3.1 Instrumented Compensation

BoT-SORT's compensation call returns an inlier mask that the code discards. We reimplement the estimator so that the mask, the inlier residuals, the correspondence counts and the inlier positions are recorded, while the returned warp is unchanged. Over synthetic sequences with known inter-frame motion, the instrumented estimator and the original agree to $\max |\Delta H| = 0.0$ across every frame tested, preserving the warp used for downstream evaluation. From the recorded statistics we form six candidate reliability signals: the RANSAC inlier ratio ρ, the inlier count, the median symmetric transfer residual ε of the inliers, a solver-specific plausibility term based on fitted scale and rotation against a temporal prior, a temporal-consistency term τ comparing the current warp against a constant-velocity forward prediction, and a foreground-contamination term φ, the fraction of inliers falling inside detection boxes. §4.4 compares their predictive performance.

### 3.2 Oracle-Warp Contrast

MOT17, MOT20 and UAVDT provide no ground-truth camera motion, so compensation error cannot be measured directly. We measure it against a deliberately stronger estimate: full-resolution SIFT features, mutual-nearest-neighbour matching with a ratio test, foreground masked out using annotation boxes, robust fitting with a tighter threshold, and forward-backward consistency verification. Its median forward-backward corner error is 0.002 px pooled, and 0.0002–0.012 px taken per sequence. This non-causal reference uses annotated foreground masks and serves as a stronger estimate within the same warp family. Its disagreement with the online warp is a reference-based error measure; §5 substitutes it into the tracker to measure the corresponding accuracy headroom. The reference-quality filter retains 5,088 of 5,309 MOT17 frames (95.8 %). Its sequence-level coverage is:

| | 02 / 04 / 09 | 05 | 10 | 11 | 13 |
|---|---|---|---|---|---|
| frames | 2,172 | 836 | 653 | 899 | 749 |
| excluded | 0 | **206 (24.6 %)** | 6 | 3 | 6 |

MOT17-05 contributes 206 excluded frames (24.6 %); their median online residual is 1.066 px against 0.557 px for retained frames. Sections 4.2–4.3 report the retained-frame measurements. Including excluded frames except the 101 with an identity reference changes the harmful gate-flip rate from 0.031 % to 0.033 % and the count from 34 to 37.

### 3.3 Gate-Flip Counting

Gate-flip counting links compensation error to association outcomes. For every ground-truth object present in consecutive frames we warp its previous box by the online warp and by the reference warp, compute IoU against its true current box, and count pairs whose gate decision differs:

$$
\begin{aligned}
&(1-\mathrm{IoU}_{\mathrm{online}}>\theta_{\mathrm{IoU}})\\
&\quad\operatorname{XOR}\;
(1-\mathrm{IoU}_{\mathrm{reference}}>\theta_{\mathrm{IoU}}).
\end{aligned}
$$

A harmful flip is a correct pair gated out by compensation error, as described by the coupling in §1. Ground-truth identities isolate the geometric effect from detector quality and appearance embeddings. Gate-flip counting measures the effect on pairs near the association threshold.

### 3.4 Sensor and Annotation References

KITTI [28] supplies per-frame GPS/IMU measurements, the full calibration chain, and 3D object annotations; its sensor stream and calibration are documented separately [29]. Composing them gives inter-frame camera motion and each object's annotated depth for a geometry-based reference. For a pixel at depth z in camera frame k−1, the displacement induced by camera motion (R, t) alone is obtained by back-projection, rigid transformation and re-projection. The object's own motion is handled by the Kalman prediction and excluded from the compensation model.

### 3.5 Measurement Protocol

Every configuration compared in this paper consumes byte-identical detections. We run the detector once, write its output to disk, and record a SHA-256 for every file; each tracker variant reads those files. On MOT17 this is 62,398 detections from the published YOLOX-X ablation weights [8, 30]; on KITTI, 8,008 frames through a COCO-pretrained detector that has never seen KITTI. KITTI results use a fixed configuration over all 21 labelled sequences. Five independent runs of the MOT17 file-GMC configuration, two of the KITTI pipeline, and two of the appearance-enabled MOT17 pipeline of §5.4 produced **bit-identical** tracker output on every evaluated sequence. Section 6.6 reports bootstrap confidence intervals over sequences to quantify variation across scenes. All evaluation uses the official TrackEval implementation [31]. The HOTA figure in every results table is TrackEval's pooled output. The point estimate attached to every confidence interval is the detection-weighted mean of per-sequence HOTA, which is the quantity the bootstrap resamples. Across the ten KITTI tracking contrasts they differ by a median of 0.026 HOTA and at most 0.198 (the pedestrian contact-point row). We use pooled scores for configuration tables and weighted contrasts for interval-based claims. Boldface marks the configurations and quantities examined in the accompanying analysis.

---
## 4 Compensation Accuracy

### 4.1 Benchmark Coverage: 61,337 Frames

We ran the instrumented estimator over every frame of MOT17 [32] (5,309 frames, 7 sequences), MOT20 [33] (8,927 frames, 4 sequences), UAVDT [34] (40,685 inter-frame estimates over 50 sequences) and KITTI tracking [28] (6,416 analysed frames, 21 sequences), recording the full statistics of §3.1 for each. Table 1 summarises what they contain.

**Table 1** Compensation-reliability measurements. Percentages are of frames; texture collapse is defined by fewer than 100 inliers.

| Statistic | MOT17 | MOT20 | UAVDT |
|---|---|---|---|
| Frames | 5,309 | 8,927 | 40,685 |
| Median inlier ratio ρ | 0.976 | 0.995 | 1.000 |
| Median transfer residual ε | 0.570 px | 0.592 px | 0.295 px |
| 95th-percentile ε | 1.767 px | 0.879 px | 0.941 px |
| Median inter-frame displacement | 2.095 px | 0.689 px | 1.035 px |
| Median temporal inconsistency τ | 1.215 px | 0.813 px | 0.166 px |
| Inlier count < 100 (texture collapse) | **0 (0.000 %)** | **0 (0.000 %)** | 19 (0.047 %) |
| Inlier count < 300 | 3 (0.057 %) | 1 (0.011 %) | 1,620 (3.982 %) |
| ε > 2 px (imprecise fit) | 190 (3.579 %) | **0 (0.000 %)** | 148 (0.364 %) |
| ρ < 0.7 | 203 (3.824 %) | 1 (0.011 %) | 91 (0.224 %) |
| φ > 0.7 (inliers mostly on foreground) | 228 (4.295 %) | **3,314 (37.123 %)** | — |

Median residuals are sub-pixel across the three image benchmarks. The texture-collapse regime occurs in 0 of 14,236 pedestrian-benchmark frames, with the keypoint detector saturated at 1,000 corners in essentially every frame. MOT17-05 reaches a median inlier ratio of 0.842 with a 5th percentile of 0.538 and a median residual of 1.11 px.

### 4.2 Oracle Contrast and Static-Camera Control

Residuals measure a fit's internal consistency. The oracle contrast of §3.2 adds an external reference for compensation accuracy. On MOT17 it retains 5,088 of 5,309 frames after the reference-quality filter (95.8 %). The three static-camera and four moving-camera MOT17 sequences provide a control for the relationship between camera motion and reference disagreement.

| | Frames | Median corner disagreement | 90th percentile | Median box-centre shift |
|---|---|---|---|---|
| Static sequences (02, 04, 09) | 2,172 | 0.150 px | 0.559 px | 0.118 px |
| Moving sequences (05, 10, 11, 13) | 2,916 | 1.309 px | 4.549 px | 0.637 px |

The separation is complete at sequence level. Per-sequence medians are 0.088 (02), 0.147 (04) and 0.505 px (09) for the static cameras against 0.786 (11), 1.121 (10), 1.669 (13) and 2.105 px (05) for the moving ones: every moving sequence exceeds every static one. This ordering supports the static/moving control used in the tracking comparison. MOT20 tests the reference contrast under foreground domination. MOT20-05 has φ = 0.8166 at the median: 82 % of the keypoints used to estimate camera motion lie on pedestrians, and 37.1 % of MOT20 frames exceed φ > 0.7. The oracle contrast covers all 8,927 MOT20 frames:

| | Frames | Median corner disagreement | p90 | p99 | Max | Median φ |
|---|---|---|---|---|---|---|
| MOT20-01 | 428 | 0.409 px | 0.646 | — | — | 0.236 |
| MOT20-02 | 2,781 | 0.745 px | 1.274 | — | — | 0.321 |
| MOT20-03 | 2,404 | 1.017 px | 1.241 | — | — | 0.508 |
| MOT20-05 | 3,314 | 0.756 px | 1.223 | — | — | **0.817** |
| **All MOT20** | **8,927** | **0.839 px** | **1.237** | **1.717** | **2.732** | 0.512 |

The reference warp covers **every** MOT20 frame. Compensation error on MOT20 sits between MOT17's static and moving sequences, and its maximum over the whole benchmark is 2.73 px. MOT20-05, with 82 % of its inliers on pedestrians, disagrees with the reference by 0.756 px at the median — *less* than MOT20-03, which has 51 % contamination. MOT20 is a static-camera benchmark with dense pedestrian flow. Coherent foreground motion can produce a low-residual fit close to identity, which is the correct transform for a static camera. The measured disagreement shows that foreground contamination alone does not determine compensation error.

### 4.3 Error Prediction from Existing Correspondences

Given the oracle contrast as a target, the six candidate signals of §3.1 can be validated. We evaluate by leave-one-sequence-out: fit on six MOT17 sequences, measure on the seventh, report the mean held-out area under the ROC curve for detecting compensation error above 1 px. The median transfer residual ε of the inlier set — computed from the existing correspondences — achieves a **held-out AUC of 0.866**, worst sequence 0.779. The reliability score $\exp(-\varepsilon/\varepsilon_0)$, with $\varepsilon_0 = 1$ px, has a pooled Spearman correlation of −0.928 with compensation error. Three controls assess scene composition and frame-level pairing: *Confound conditioning.* Stratifying into quartiles by scene density, by detection count, by camera-displacement magnitude and by keypoints tracked, the relationship holds within every stratum of every stratification. Correlations include −0.741 in the third camera-displacement quartile and −0.764 in the densest scene-density quartile. *Removing the static/moving split.* Restricted to the four moving-camera sequences only (2,916 frames), pooled Spearman is −0.771, and per sequence −0.786 (05), −0.596 (10), −0.702 (11), −0.763 (13). *Placebo.* Recomputing the signal from statistics shuffled across frames gives a mean correlation of −0.001 over 200 permutations (range [−0.035, +0.033]) against a real value of −0.928.

### 4.4 Reliability-Signal Selection on MOT17

A synthetic calibration study covers 234 frames with known warps under six conditions — clean, blur, repetitive texture, low light, foreground domination, and low texture. It establishes the range of failure modes represented by the candidate signals. We compare all 63 non-empty signal subsets on MOT17 under leave-one-sequence-out validation: Figure 2 plots all 63 subsets and Table S1 gives the best at each size. The median transfer residual alone reaches a held-out AUC of 0.866, matching the best two-signal subset and exceeding all six together by +0.092 AUC (0.866 against 0.774). Per-signal statistics over the same 5,088 frames explain the selection: **The inlier count saturates on MOT17** — 99.94 % of frames sit at the ceiling because the keypoint detector cap is reached. The residual retains variation within this regime. **Temporal consistency τ tracks camera acceleration as well as estimation quality.** Adding it at k = 6 changes held-out AUC from 0.854 to 0.774, consistent with legitimate panning and turning departing from a constant-velocity warp prediction. **Foreground contamination φ alone gives AUC 0.584**, with standard deviation 0.153 over a range of 0–0.896. Section 4.2 relates its interpretation to foreground motion. **Residual-Based Reliability.** For the fitted four-degree-of-freedom similarity, the singular-value ratio is identically unity. The reported estimator therefore uses ε alone — one scalar from the existing correspondences, with a fixed scale. It matches the signal variation present on MOT17 and reaches the highest held-out AUC in the subset search.

### 4.5 Within-Sequence Predictive Performance

A placebo that shuffles statistics within each sequence preserves a correlation of −0.748, compared with the pooled −0.928. This control separates between-sequence structure from frame-level prediction. Frame-level performance is reported through per-sequence correlations of −0.60 to −0.79 and leave-one-sequence-out AUC of 0.866, computed within each held-out sequence.

---

## 5 Tracking Value of Compensation Accuracy

Section 4 establishes that compensation disagreement is measurable and predictable. This section connects it to association and tracking outcomes through geometry, gate-flip counting and reference-warp substitution on MOT17, followed by a compensation control on UAVDT.

### 5.1 Geometric Margin

For each ground-truth object present in consecutive MOT17 frames, warp its previous box by the online warp and by the reference warp and compare IoU against its true current box. Over 109,955 pairs, the median IoU cost of compensation error is **0.00085**, with a mean of 0.00003. IoU after the online warp, by quantile: 0.479 (0.1 %), 0.676 (1 %), 0.803 (5 %), 0.916 (25 %), 0.960 (50 %). Fraction of pairs with IoU below the 0.5 association gate: **0.127 %**. At a median IoU of 0.96 against a gate at 0.5, the margin is large relative to the median error cost of 0.00085. The reference-IoU band [0.5, 0.6] contains **0.284 %** of pairs (312 of 109,955). Of those, 21 are gated out (6.73 %).

### 5.2 Gate-Flip Frequency

The geometric margin summarises overlap. The gate-flip count of §3.3 measures the frequency of association *decision* changes; Table 2 gives it per sequence.

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

Fifty-five flips total, 0.050 % of pairs; 34 harmful, 0.031 %. Four of seven sequences produce exactly zero — including MOT17-11, which is a moving-camera sequence. MOT17-13, also moving, is net *beneficial*: the online warp admits more correct pairs than the reference does. The aggregate measures the frequency of gate changes as well as their direction. Harmful flips concentrate on small or occluded objects: the median box width is 21–33 px against sequence medians of 28–124 px, and in MOT17-05 the median annotated visibility at a harmful flip is 0.0000. Threshold sensitivity gives 654 flips with 312 harmful at θ = 0.3, 216 with 118 at θ = 0.4, 55 with 34 at θ = 0.5, and 22 with 15 at θ = 0.6. The main comparison uses BoT-SORT's θ = 0.5. The 34 harmful flips identify the ground-truth pairs affected at this gate under the reference contrast. For scale, the baseline commits 139 identity switches.

### 5.3 Reference-Warp Intervention

The geometric measurements above are complemented by the tracking comparison in Table 3, which substitutes the reference warp into an otherwise unmodified tracker and measures HOTA. Four configurations, byte-identical detections (62,398 from the published YOLOX ablation weights), identical hyperparameters, identical evaluation. The configuration is BoT-SORT's own published ablation setting — Kalman filter plus compensation, no appearance model — which is the row our baseline reproduces (§3.5); §5.4 repeats the axis with the appearance channel enabled.

**Table 3** The compensation-value axis on MOT17 validation-half. The only variable is the warp.

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW |
|---|---|---|---|---|---|---|
| No compensation | 68.118 | 69.914 | 66.898 | 79.598 | 77.777 | 337 |
| Online sparse-flow GMC | 69.006 | 71.333 | 67.246 | 81.345 | 78.451 | 139 |
| Precomputed file GMC (published default) | 69.120 | 71.570 | 67.239 | 81.499 | 78.445 | 140 |
| **Reference (oracle) warp, strict** | **69.093** | **71.510** | **67.245** | **81.500** | **78.488** | **147** |

Figure 3 plots both axes. Having compensation is worth +0.888 HOTA and −198 identity switches. Replacing the online warp with the reference changes HOTA by +0.087 and identity switches by +8; the HOTA change is 9.8 % of the gain from enabling compensation. The gap between the two ordinary compensator implementations is 0.114 HOTA. These comparisons distinguish enabling compensation from refining its estimate. Every oracle figure in Tables 3–5 uses strict reference substitution wherever the reference is available, with no fallback to the online estimate. This fixes the intervention across the motion-only and appearance-enabled comparisons. The bit-identical reruns of §3.5 establish deterministic execution; §5.5 quantifies variation across sequences. Association is a global assignment, so a geometric change can alter matches elsewhere in the cost matrix. HOTA and identity switches therefore measure complementary outcomes of the reference substitution.

### 5.4 Compensation Accuracy with Appearance Information

The appearance-enabled comparison uses FastReID SBS-S50 [35], the model shipped with BoT-SORT, on the same frozen detections. It tests the motion–appearance gate described in §1 alongside the published motion-only ablation configuration.

**Table 4** Compensation configurations with appearance information. The motion–appearance gate of §1 is active in every row.

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW | Frag |
|---|---|---|---|---|---|---|---|
| No compensation | 68.280 | 70.168 | 66.969 | 79.768 | 77.929 | 300 | 488 |
| Online sparse-flow GMC | **69.426** | **72.166** | **67.272** | **82.276** | **78.551** | **160** | **453** |
| Reference (oracle) warp, strict | 69.350 | 72.025 | 67.257 | 82.119 | 78.484 | 164 | 457 |

Table 4 shows that enabling appearance raises HOTA in every configuration. Having compensation is worth +1.146 HOTA and −140 identity switches; reference substitution changes HOTA by −0.076 and identity switches by +4 in the pooled scores. Section 5.5 separates static and moving cameras: on moving sequences, the weighted reference contrast is +0.189 HOTA [+0.050, +0.517], against +3.500 [+1.082, +4.842] for enabling compensation with the same appearance model. The appearance channel itself contributes +0.93 IDF1 and +0.42 HOTA at the online warp.

### 5.5 Sequence-Level Intervals

Tables 3 and 4 report pooled scores. Table 5 uses 20,000 percentile-bootstrap resamples over sequences, with HOTA averaged over TrackEval's alpha grid and sequences weighted by ground-truth detections, following the estimator convention in §3.5. Moving-camera sequences measure compensation where camera motion is present; static sequences provide a control. Table 5 reports both the full benchmark and the moving-camera stratum. The static/moving classification is the benchmark property used in §4.2. The tracking analysis reports this stratification alongside the pooled interval as a secondary analysis.

**Table 5** Bootstrap 95 % confidence intervals on the MOT17 compensation-value axis. The oracle rows use the strict configuration of §5.3.

| Quantity | Configuration | All 7 sequences | **Moving-camera sequences (05, 10, 11, 13)** |
|---|---|---|---|
| Value of **having** compensation | motion only | +0.928 [−0.136, +3.471] | **+3.426 [+1.007, +5.523]** |
| Value of **having** compensation | + appearance | +1.220 [+0.243, +3.720] | **+3.500 [+1.082, +4.842]** |
| Value of **refining** it | motion only | +0.125 [−0.062, **+0.477**] | **−0.037 [−0.201, +0.052]** |
| Value of **refining** it | + appearance | −0.087 [−0.453, +0.138] | **+0.189 [+0.050, +0.517]** |
| Gap between two ordinary compensators | motion only | +0.149 [−0.028, +0.504] | +0.057 [−0.015, +0.233] |

On moving-camera sequences, the motion-only reference contrast is −0.037 HOTA with a 95 % upper interval endpoint of +0.05. With appearance it is +0.189 [+0.050, +0.517], compared with +3.500 [+1.082, +4.842] for enabling compensation. The full-benchmark motion-only interval has an upper endpoint of +0.48, reflecting the different static-camera contribution. The ground-truth-detection weights give a Kish effective sample size of 3.79 across all seven sequences, with MOT17-04 carrying 44.9 %. The sequence-level intervals describe this benchmark configuration; the geometric and gate-flip measurements supply complementary evidence over 109,955 ground-truth pairs.

### 5.6 Compensation under Aerial Camera Motion

UAVDT extends the compensation control to aerial footage from a moving drone. Its compensation estimates have median residual 0.295 px and median temporal inconsistency 0.166 px (Table 1). Figure 4 shows how its reliability distributions compare with the pedestrian benchmarks'. Running the same motion-only tracker over the 20 UAVDT sequences that ship with published FRCNN detections, fixed across both configurations:

| Configuration | HOTA | AssA | DetA | IDF1 | MOTA | IDSW | Frag |
|---|---|---|---|---|---|---|---|
| No compensation | 43.920 | 48.644 | 40.242 | 57.335 | 31.786 | 3,342 | 8,939 |
| Online GMC | 44.083 | 48.946 | 40.276 | 57.646 | 31.756 | 3,347 | 8,993 |

Turning compensation on changes HOTA by +0.163 and identity switches by +5 out of 3,342 under these fixed detections. This comparison measures the value of enabling online compensation. Reference-warp headroom is evaluated on MOT17 in §5.3–§5.5.

### 5.7 Benchmark Implications

The benchmarks support complementary measurements. MOT17 connects reference-warp disagreement to gate changes and tracking outcomes; MOT20 supplies an external disagreement measurement over all 8,927 frames; UAVDT measures the value of enabling compensation in aerial footage. On MOT17, the moving-camera intervals identify estimation refinement within the shared similarity family as a smaller source of gain than enabling compensation. A robustness claim can therefore be evaluated against the measured reference contrast and the gate changes it produces.

---
## 6 Depth-Dependent Geometry of Shared Warps

Section 5 measures estimation headroom within a shared warp family. This section examines depth-dependent scene geometry on KITTI, using sensor ego-motion and 3D annotations to separate camera-induced displacement from object motion.

### 6.1 KITTI as a Translating-Camera Benchmark

A shared 2D warp represents the camera-induced displacement field across a frame. Its ability to serve targets at different depths depends on camera motion and scene geometry. Under pure rotation, the induced image motion is the homography $H = K R K^{-1}$, which is independent of scene depth. Every pixel, near or far, moves by the same rule. Under translation, the image displacement of a point at depth *z* contains a term proportional to *1/z*. A global 2D warp approximates this depth-dependent field, with accuracy determined by the scene geometry represented in its correspondences. KITTI records a camera translating on a car through scenes containing objects from 6 m to beyond 50 m, providing a setting for measuring this depth dependence. Composing the GPS/IMU stream with the calibration chain gives inter-frame camera motion, and the 3D labels give each object's depth. The geometric measurements use these sensor and annotation references (§3.4).

### 6.2 Within-Frame Residual Variation

For each eligible annotated object we compute its reference image displacement from its 3D position and sensor camera motion, then compare predictions from three compensation models. Across 6,416 frames with at least two eligible objects, the table reports the median, 90th percentile and maximum of the per-frame median residual:

| Model | Median residual | p90 | Max |
|---|---|---|---|
| No compensation | 4.196 px | 15.367 | 127.8 |
| Rotation homography $K R K^{-1}$ (sensor R) | 3.621 px | 12.917 | 128.6 |
| **Least-squares similarity (oracle)** | **0.816 px** | **5.041** | **73.0** |

The four-degree-of-freedom similarity used by BoT-SORT captures the approximately radial expansion induced by forward translation through its uniform-scale term. The rotation-only homography leaves the translational component uncompensated. Within-frame spread measures the variation across targets after the least-squares global similarity fit. This analysis uses 4,318 moving frames with at least three eligible objects and camera translation above 0.05 m, as plotted in Figure 5:

| | Median | p75 | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|
| Spread across objects in one frame | **2.431 px** | 5.335 | 10.114 | 14.020 | 23.084 | **67.7** |

| Objects in the same frame disagree by more than | Share of moving frames |
|---|---|
| 1 px | 75.47 % |
| 2 px | 56.02 % |
| **5 px** | **27.12 %** |
| 10 px | 10.14 % |

In 27 % of the evaluated moving frames, objects in the same image require corrections differing by more than five pixels — after the least-squares global similarity fitted to those objects themselves. The spread is consistent with depth-dependent parallax: the per-frame Spearman correlation between object depth and residual has median −0.200 and is negative in 64.5 % of the frames where it is defined (3,379 of the 4,318 moving frames; the statistic needs at least four objects, and the remaining 939 have exactly three). Nearer objects tend to carry the larger residual.

### 6.3 Geometric Residuals at the Association Gate

The following measurement connects residual spread to the association gate using annotated box sizes and BoT-SORT's IoU threshold of 0.5:

| | KITTI (residual after a target-fitted *similarity*) | MOT17 (compensation error) |
|---|---|---|
| Moving frames with ≥ 1 object pushed below the gate | **8.04 %** | — |
| Object-frames gated out | **510 / 23,443 = 2.175 %** | **34 / 109,955 = 0.031 %** |

The KITTI rate measures residual geometry after a target-fitted similarity; the MOT17 rate measures gate changes under reference substitution. The former identifies depth-dependent corrections that reach the gate, and §6.4 tests a depth-aware global model on the same scene geometry. The sensor and annotation references isolate the interaction between scene geometry and the compensation model.

### 6.4 Depth-Aware Global Homography

Section 6.2 measures the residual after a target-fitted similarity. The warp-family comparison fits similarity and homography models to the same depth-varying background points, following the ground-plane geometry relevant to UCMCTrack [17]. This construction tests how each family represents depth variation while keeping the correspondence source fixed. A grid over the lower image supplies background points carrying their **own** estimated depths, with points inside the tracker's **detections** masked out. A median of 437 background samples per frame is back-projected, transformed by sensor ego-motion and re-projected. Residuals are measured at object centres against annotation-derived displacement on the same 4,318 moving frames as §6.2: Figure 6 plots the distributions and sets them against what each warp produces in tracking.

**Table 6** Global compensation models on KITTI, measured at object centres against sensor- and annotation-derived displacement. The similarity and homography rows are fitted to the same depth-varying background points; the oracle row is fitted to the objects themselves and is a target-fitted geometric reference.

| | Median residual | Within-frame spread | Frames with spread > 5 px |
|---|---|---|---|
| Online sparse-flow GMC (deployed estimator) | 2.025 px | 8.673 px | 65.12 % |
| Oracle similarity, fitted to the objects (§6.2, moving frames only) | 1.698 px | 2.431 px | 27.12 % |
| Similarity, depth-varying background | 4.773 px | 7.466 px | 61.74 % |
| **Homography, depth-varying background** | **0.478 px** | **1.370 px** | **12.90 %** |

The depth-aware homography reduces the within-frame spread to 1.370 px — **81.6 %** below the background-fitted similarity's 7.466 px and **43.6 %** below the target-fitted similarity's 2.431 px. The fraction of frames in which targets disagree by more than 5 px falls from 27.12 % to 12.90 %. KITTI's approximately planar scene provides a geometric explanation: the homography models the depth variation of a dominant plane, using background correspondences at estimated depths.

### 6.5 Tracking Evaluation Protocol

The tracking comparison tests whether the geometric correction improves association under fixed detections. The tracker uses a motion-only BoT-SORT configuration: Kalman filter, two-stage ByteTrack association [8], and IoU gate. This configuration isolates the motion-side correction. Detections come from a COCO-pretrained YOLO11x that has never seen KITTI, frozen once and hashed; every configuration reads the same detections. Evaluation is official TrackEval under the KITTI protocol.

**Table 7** Tracking configurations and input requirements.

| Configuration | Correction | Ego-motion | Depth | Reads annotations |
|---|---|---|---|---|
| none | identity | — | — | no |
| online GMC | BoT-SORT sparse-flow GMC | — | — | no |
| global similarity (oracle) | 4-DOF fitted to a static grid at the scene's median annotated depth | sensor | annotated | yes |
| global similarity, target-anchored (oracle) | the same, anchored at one class's median depth | sensor | annotated | yes |
| **depth-aware global homography** | **8-DOF fitted to background points at their estimated depths, detections masked out** | **sensor** | **estimated** | **fallback only** |
| **depth-aware homography, contact point** | **the same warp, applied through each box's contact point** | **sensor** | **estimated** | **fallback only** |
| per-target similarity (oracle) | 4-DOF per object, from its box corners at its annotated depth | sensor | annotated | **yes** |

Table 7 distinguishes the input information available to each configuration. The per-target reference matches predicted track boxes to annotated boxes in the previous frame at IoU distance below 0.7, using the global similarity when no match is found. Over the 21 sequences, 40,557 of 69,000 track-warp applications (58.8 %) receive a per-object warp and 28,443 (41.2 %) receive the global one. It is an annotation-assisted reference. The depth-aware homography uses estimated background depth on moving frames; its near-static fallback is specified below. The same plausibility guard replaces any warp whose implied **scale** falls outside [0.5, 2.0] with the identity. Its activation on the runs in Table 8 is:

| Configuration | guard applications | fired | rate |
|---|---|---|---|
| online GMC | 67,923 | 0 | 0 % |
| global similarity | 67,712 | 0 | 0 % |
| per-target | 69,000 | 26 | 0.04 % |
| depth-aware homography, corners | 68,014 | 1,090 | 1.60 % |
| depth-aware homography, contact point | 67,668 | 0 | 0 % |

The corner-wise homography is relinearised per track, while the contact-point variant takes its scale from the global similarity. A translation cap of 300 px reproduces the corner arm and changes the contact-point count from 85 to 86 identity switches; at 1,000 px both reproduce the reported outputs. For camera translation below 0.05 m, the homography configuration uses the global similarity anchored at the median annotated depth. This applies to **1,270 of 8,008 frames**; 21 first frames use the identity, giving 16.1 % in total. The homography is fitted on all remaining moving frames.

### 6.6 Tracking Results

**Table 8** KITTI tracking, 21 sequences, 8,008 frames, byte-identical detections throughout.

*Pedestrian*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 45.499 | 47.877 | 43.996 | 279 |
| online sparse-flow GMC (deployable) | **47.428** | 51.448 | 44.617 | 126 |
| global similarity (oracle) | 46.775 | 49.974 | 44.841 | 108 |
| global similarity, pedestrian-anchored (oracle) | 46.823 | 50.060 | 44.825 | 111 |
| **depth-aware global homography (estimated depth)** | 47.158 | 50.834 | 44.714 | 97 |
| **depth-aware homography, contact point (estimated depth)** | 47.229 | 50.968 | 44.890 | **85** |
| per-target similarity (oracle, reads annotations) | **47.518** | **51.807** | 44.660 | 88 |

*Car*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 64.792 | 70.339 | 60.584 | 401 |
| online sparse-flow GMC (deployable) | 65.265 | 70.137 | 61.450 | 165 |
| global similarity (oracle) | 66.166 | 71.748 | 61.739 | 133 |
| global similarity, car-anchored (oracle) | 65.934 | 71.215 | 61.736 | 125 |
| **depth-aware global homography (estimated depth)** | **66.482** | **72.507** | 61.722 | 125 |
| depth-aware homography, contact point (estimated depth) | 66.044 | 71.659 | 61.664 | **115** |
| per-target similarity (oracle, reads annotations) | 66.414 | 72.618 | 61.457 | 117 |

Table 9 and Figure 7 give the intervals.

**Table 9** Bootstrap 95 % confidence intervals over the 21 sequences, 20,000 resamples, HOTA averaged over TrackEval's alpha grid, sequences weighted by ground-truth detections. ΔIDSW is the ground-truth-detection-weighted mean difference in sequence identity-switch counts.

| Comparison | Class | HOTA | ΔIDSW (weighted) |
|---|---|---|---|
| **depth-aware homography − online GMC** | **car** | **+1.187 [+0.262, +1.922]** | −3.35 [−8.01, +0.15] |
| depth-aware homography − online GMC | ped | −0.430 [−1.030, +1.030] | −0.75 [−11.72, +2.53] |
| homography at contact point − online GMC | car | +0.757 [−0.023, +1.865] | **−4.38 [−9.06, −0.76]** |
| homography at contact point − online GMC | ped | −0.397 [−1.193, +1.967] | −1.90 [−12.64, +1.03] |
| per-target − depth-aware homography | car | −0.073 [−0.624, +0.392] | −0.91 [−2.82, +0.70] |
| per-target − depth-aware homography | ped | +0.366 [−0.035, +0.986] | +0.18 [−0.64, +1.54] |
| per-target − global similarity | ped | +0.726 [−0.090, +1.096] | **−3.12 [−5.84, −0.04]** |
| per-target − global similarity | car | +0.238 [−0.405, +0.730] | −1.05 [−2.51, +0.31] |
| having compensation at all | ped | **+1.875 [+0.681, +4.768]** | **−22.25 [−33.23, −0.41]** |
| having compensation at all | car | +0.528 [−0.600, +2.001] | **−14.77 [−26.52, −5.02]** |

**Supplying depth to the shared warp improves car tracking.** The depth-aware homography improves on online compensation by **+1.187 HOTA [+0.262, +1.922]**. On pedestrians, the pooled identity-switch count changes from **126 to 97**, and to **85** with contact-point application. These are separate configurations; Table 9 reports their HOTA and identity-switch intervals. **Per-target correction provides an annotation-assisted reference.** Against the depth-aware homography, its HOTA contrast is −0.073 [−0.624, +0.392] on cars and +0.366 [−0.035, +0.986] on pedestrians. The shared model obtains its correction without per-object association under the inputs in Table 7. The interval estimates use the same weighting across configurations. The identity-switch column is a ground-truth-detection-weighted mean difference. For pedestrians, per-target correction changes the total from 108 to 88 — a reduction of **20 over 21 sequences**, or −0.95 per sequence unweighted — while the weighted difference is −3.12. Tables 8 and 9 keep totals and weighted contrasts distinct. Six of the 21 sequences contain no pedestrian ground truth and one carries 52.9 % of it; the Kish effective sample size is **3.05** for pedestrians and 10.47 for cars. The per-target contrast over global similarity is +0.514 [−0.279, +1.265] on pedestrians under equal sequence weighting, compared with +0.726 [−0.090, +1.096] under detection weighting. The weighted leave-one-sequence-out point estimates range from +0.286 to +0.944 on pedestrians and from +0.107 to +0.418 on cars. Table 9 reports 20 per-comparison 95 % intervals and §7 a further eight; these describe individual contrasts without a family-wise adjustment. **Reference Depth and Shared-Similarity Alignment.** The scene-depth similarity reaches pedestrian HOTA 46.775, while pedestrian-depth anchoring gives 46.823. The depth-aware homography reaches 47.158 by fitting spatially varying background depth, connecting the geometric result in Table 6 to the tracking comparison. **Cars and pedestrians rank the two applications differently.** Applying the homography to all four box corners is better on cars (66.482 against 66.044); applying it through the contact point is better on pedestrians (47.229 against 47.158, and 85 identity switches against 97). This pattern is consistent with contact-point application preserving ground-plane geometry for tall boxes. Both applications are reported for both classes.

### 6.7 Per-Frame Localisation of Per-Target Correction

The shuffled-correction control tests whether correct object–correction pairing matters beyond perturbation magnitude. The exposure analysis then localises the changes across frames. **The placebo.** Within each frame we permute which object's correction is applied to which track, subject to no object keeping its own. The set of corrections is unchanged, so their magnitude and direction distributions are preserved exactly; the object–correction pairing is the controlled variable. Everything else — the ground-truth gate, the fallback to the shared warp, the plausibility guard, the frozen detections — is identical to the per-target arm. Permutations are seeded per (sequence, frame) and reproducible. Table 10 gives the result.

**Table 10** Shuffled-correction control with matched correction magnitudes and directions.

| Configuration | ped HOTA | ped IDSW | car HOTA | car IDSW |
|---|---|---|---|---|
| global similarity (no per-object correction) | 46.775 | 108 | 66.166 | 133 |
| **shuffled placebo** | **46.198** | **163** | **62.582** | **400** |
| per-target | 47.518 | 88 | 66.414 | 117 |

The global-similarity reference exceeds the shuffled placebo by 3.51 HOTA on cars [+2.12, +4.90], with weighted ΔIDSW = −26.1 [−37.43, −10.10]. The correctly paired per-target arm exceeds the placebo by 1.10 HOTA on pedestrians [+0.34, +4.55] and 3.75 on cars [+2.11, +5.28]. The matched magnitude and direction distributions isolate the value of the pairing. The placebo supports the role of object-specific pairing in the depth-derived correction. The warp-family comparison in §6.4 separately measures how a shared model represents depth-varying geometry. **Per-Frame Localisation by Exposure.** Exposure is computed from the two warps being compared and localises the intervention across frames. We defined exposure per (sequence, frame, class) as the median absolute difference, at box centres, between an object's own depth-derived warp and the shared depth-blind one — the disagreement that depth information removes. Improvement is the per-frame identity-switch difference between the two configurations. Both quantities are computed after tracking for the exposure analysis. The result is Table 11, plotted in Figure 8.

**Table 11** Pedestrian identity switches by exposure quartile, 2,377 frames.

| Quartile | Median exposure (px) | IDSW, global | IDSW, per-target | Improvement | Per 1,000 frames |
|---|---|---|---|---|---|
| Q1 (least exposed) | 0.019 | 115 | 115 | **0** | 0.00 |
| Q2 | 0.309 | 57 | 59 | −2 | −3.37 |
| Q3 | 0.914 | 59 | 57 | +2 | +3.37 |
| **Q4 (most exposed)** | **3.584** | **49** | **29** | **+20** | **+33.67** |
| Total | | 280 | 260 | 20 | |

All 20 avoided switches come from the top exposure quartile. The bottom quartile yields zero, although it carries more identity switches than any other quartile. A paired permutation test shuffles frame exposure against improvement: over 20,000 permutations, the observed +20 sits against a null mean of 4.99 (sd 3.70), **p = 0.0001**. The diagnostic counter's total difference, 280 − 260 = 20, matches TrackEval's pedestrian difference, 108 − 88 = 20. The per-target localisation uses pedestrian sequences, for which the counter reproduces the TrackEval difference. Car outcomes are reported with the official KITTI class and ignore-region handling in Tables 8–9.

### 6.8 Per-Frame Localisation of the Homography Gain

The same exposure analysis localises the depth-aware homography's changes relative to online compensation. Exposure is the median disagreement at box centres between the deployed warp and the homography; improvement is the per-frame identity-switch difference between those trackers. The result is Table 12.

**Table 12** Identity switches by exposure quartile, depth-aware homography against the deployed estimator.

*Car (6,469 frames)*

| Quartile | Median exposure | IDSW, online GMC | IDSW, homography | Improvement |
|---|---|---|---|---|
| Q1 | 0.34 px | 44 | 44 | **0** |
| Q2 | 1.24 px | 60 | 64 | −4 |
| Q3 | 2.36 px | 72 | 70 | +2 |
| **Q4** | **5.48 px** | **121** | **75** | **+46** |

*Pedestrian (2,384 frames)*

| Quartile | Median exposure | IDSW, online GMC | IDSW, homography | Improvement |
|---|---|---|---|---|
| Q1 | 0.24 px | 101 | 104 | −3 |
| Q2 | 0.92 px | 75 | 77 | −2 |
| Q3 | 1.95 px | 56 | 48 | +8 |
| **Q4** | **4.09 px** | **59** | **39** | **+20** |

On cars the net improvement of 44 is more than accounted for by the top exposure quartile alone, which carries +46, while the bottom quartile yields exactly zero; a paired permutation test over the 6,469 frames puts the observed +46 against a null mean of 10.95 (sd 6.91), **p < 0.0001**. On pedestrians the top quartile gives +20 in Q4 against a null mean of 5.75 (sd 5.58), **p = 0.0071**, with the two lowest quartiles slightly negative. This diagnostic counter gives 297 → 253 switches on cars and 291 → 268 on pedestrians; TrackEval gives 165 → 125 and 126 → 97, respectively. Table 12 therefore describes the quartile pattern under the diagnostic counting protocol, while Tables 8–9 provide the official totals and intervals. Exposure is computed from the compared warps and serves to localise the intervention.

---
## 7 Depth Inputs and Computational Cost

The depth-aware homography uses estimated background depth and sensor ego-motion. This section examines its input requirements, response to depth noise and computational cost, with per-target correction as a comparison.

### 7.1 Input Requirements

The global and per-target corrections share ego-motion and depth inputs, while the per-target reference additionally uses annotated association. **Ego-motion.** KITTI provides the platform's GPS/INS measurements at 10 Hz. The experiments use this calibrated sensor stream for both global and per-target geometric corrections. **Depth.** The homography back-projects background points at monocularly estimated depths on 6,717 moving frames. On the 1,270 near-static frames it uses the annotation-anchored similarity of §6.5; those fallback warps imply a median image-centre displacement of 0.095 px and a maximum of 4.4 px. The remaining 21 first frames use identity. **Target identity.** The depth-aware homography applies one background-fitted warp to every track. The per-target reference matches tracks to annotated boxes (§6.5). The estimated-depth variant in §7.4 queries the depth map at each predicted box and removes that identity lookup. The shared correction supplies spatially varying camera compensation through background depth without requiring per-object association.

### 7.2 Per-Target Sensitivity to Depth Noise

The sensitivity experiment uses independent multiplicative depth noise, $z' = z\exp(\eta)$ with $\eta \sim \mathcal{N}(0,\sigma^2)$. The second column of each sweep table converts σ to the relative depth error at one standard deviation, $\exp(\sigma) - 1$. The per-target and homography sweeps in §7.2 and §7.3 apply this noise model to their respective depth inputs. Table 13 and Figure 9 give the sweep.

**Table 13** Pedestrian sensitivity to injected depth noise, per-target arm. Reference: global-similarity oracle, HOTA 46.775.

| σ | ≈ relative error | HOTA | vs global oracle | AssA | IDSW |
|---|---|---|---|---|---|
| 0.00 | 0 % | 47.518 | +0.743 | 51.807 | 88 |
| 0.05 | 5 % | 47.770 | +0.995 | 52.288 | 84 |
| 0.10 | 11 % | 47.771 | +0.996 | 52.257 | 85 |
| 0.20 | 22 % | 47.673 | +0.898 | 52.096 | 87 |
| 0.30 | 35 % | 47.564 | +0.789 | 51.857 | 99 |
| 0.50 | 65 % | 46.399 | −0.376 | 49.177 | 143 |

The pedestrian curve stays above the global-similarity reference through 35 % injected relative depth error; at 65 %, HOTA is 46.399. The sweep uses independent multiplicative noise per object. Section 7.3 applies the same noise model to the background depths used by the homography, and §7.4 evaluates a real monocular depth model.

### 7.3 Homography Sensitivity to Depth Noise

The homography uses the depths of many background points — a median of 437 per frame, interquartile range 379 to 522 — compared with a median of 5 object-depth lookups for per-target correction. Fitting these background correspondences can average independent pointwise depth noise. The experiment injects the same multiplicative noise into the background depths, then refits the warp and reruns the tracker at every level. Table 14 reports the homography sweep.

**Table 14** Depth-aware homography under injected depth error, against the compensator the tracker ships (online GMC: pedestrian 47.428 / 126 identity switches, car 65.265 / 165).

| σ | ≈ relative error | ped HOTA | vs GMC | ped IDSW | car HOTA | vs GMC | car IDSW |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 % | 47.158 | −0.270 | 97 | 66.482 | **+1.217** | 125 |
| 0.05 | 5 % | 47.207 | −0.221 | 94 | 66.407 | **+1.142** | 132 |
| 0.10 | 11 % | 46.947 | −0.481 | 95 | 66.587 | **+1.322** | 120 |
| 0.20 | 22 % | 46.820 | −0.608 | 97 | 66.479 | **+1.214** | 129 |
| 0.30 | 35 % | 46.807 | −0.621 | 101 | 66.643 | **+1.378** | 125 |
| 0.50 | 65 % | 46.521 | −0.907 | 106 | 66.538 | **+1.273** | 122 |

**On cars the HOTA gain persists across the tested noise levels.** It is +1.22 HOTA without injected noise and +1.27 at 65 % relative error, and the bootstrap interval excludes zero at **every one of the six levels** — in σ order [+0.262, +1.922], [+0.262, +1.852], [+0.493, +2.066], [+0.371, +1.974], [+0.487, +2.146] and [+0.338, +2.053]. The six levels describe the tested independent-noise model. On pedestrians, HOTA ranges from 46.521 to 47.207, and all six configurations retain fewer identity switches than online GMC (94–106 against 126). The homography fits many background depths — 437 against 5 target depths at the median — which averages independent pointwise perturbations. **The car HOTA gain persists with coarse perturbed depth under this noise model.** This motivates examining depth sources available in the target pipeline (§7.5).

### 7.4 Monocular Depth Estimation

The estimated-depth comparison uses Depth-Anything-V2 Metric [36] (VKITTI outdoor checkpoint), querying the depth map at the tracker's own predicted box. Table 15 compares estimated-depth configurations with their references.

**Table 15** Estimated-depth configurations on KITTI. Ego-motion is the platform sensor reference throughout; the final row uses annotated depth and association.

*Pedestrian*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 45.499 | 47.877 | 43.996 | 279 |
| online GMC | 47.428 | 51.448 | 44.617 | 126 |
| global similarity, estimated depth | **47.536** | 51.799 | 44.677 | 115 |
| per-target, estimated depth | 47.394 | 51.429 | 44.796 | **85** |
| per-target, ground-truth depth (§6.6) | 47.518 | 51.807 | 44.660 | 88 |

*Car*

| Configuration | HOTA | AssA | DetA | IDSW |
|---|---|---|---|---|
| none | 64.792 | 70.339 | 60.584 | 401 |
| online GMC | 65.265 | 70.137 | 61.450 | 165 |
| global similarity, estimated depth | 65.341 | 70.242 | 61.515 | 201 |
| **per-target, estimated depth** | **66.473** | **72.011** | 62.112 | **134** |
| per-target, ground-truth depth (§6.6) | 66.414 | 72.618 | 61.457 | 117 |

With bootstrap intervals:

| Comparison | Class | HOTA | ΔIDSW |
|---|---|---|---|
| per-target − global, both estimated depth | ped | −0.262 [−0.767, +1.214] | **−2.07 [−7.12, −0.20]** |
| per-target − global, both estimated depth | car | **+1.124 [+0.506, +1.629]** | −2.54 [−7.06, +0.36] |
| per-target − online GMC | ped | −0.207 [−0.852, +1.766] | −2.11 [−12.66, +0.73] |
| per-target − online GMC | car | **+1.206 [+0.154, +2.104]** | −2.57 [−7.11, +0.74] |

**Per-Target Tracking with Estimated Depth.** HOTA is 47.394 on pedestrians and 66.473 on cars, compared with 47.518 and 66.414 for the annotation-assisted reference. **The estimated-depth comparison is class-specific.** The global similarity reaches pedestrian HOTA 47.536; the per-target contrast is −0.262 [−0.767, +1.214], with weighted ΔIDSW = −2.07 [−7.12, −0.20]. On cars, per-target correction improves HOTA over the estimated-depth global similarity by +1.124 [+0.506, +1.629] and over online GMC by +1.206 [+0.154, +2.104]. The depth-aware homography in §6.6 supplies the separate shared-model comparison. These comparisons separate a global similarity at one representative depth from a global homography fitted to spatially varying depths.

### 7.5 Computational Cost

Per-frame component costs are measured on the same hardware as the tracking experiments. Table 16 gives the cost of each component.

**Table 16** Per-frame component costs. Medians use 119 GMC calls and 39 depth inferences after warm-up.

| Component | Input | Median | Throughput of that step alone |
|---|---|---|---|
| Sparse-flow GMC | 640 × 480 (MOT17) | 6.5 ms | 155 fps |
| Sparse-flow GMC | 1238 × 374 (KITTI) | 7.4 ms | 136 fps |
| Depth-Anything-V2 Metric ViT-L | 1238 × 374 | **480.9 ms** | **2.1 fps** |

**Depth estimation is the main computational cost.** At KITTI resolution, the evaluated network takes 480.9 ms per frame and sparse-flow GMC takes 7.4 ms, a factor of 65. The depth-aware correction additionally fits one homography to a few hundred background points per frame. When a pipeline already computes depth, the correction can reuse that map and add background sampling and a homography fit. Calibrated ground-plane geometry, as used by UCMCTrack, offers another depth source. The reported results evaluate the monocular-depth configuration.

## 8 Class-Specific Tracking Outcomes

The two classes emphasise different outcomes on the same sequences, frames and camera motion. On **cars**, the depth-aware homography improves HOTA by +1.187 [+0.262, +1.922]. On **pedestrians**, the pooled identity-switch count changes from 126 to 97, and to 85 with contact-point application; the HOTA intervals are given in Table 9. The application point also changes the class-level ranking (§6.6). Supplementary S3 tests two geometric explanations. Median |log(z/z_median)| is 0.246 for pedestrians and cyclists against 0.325 for cars; the one-sided Mann–Whitney test in the hypothesised direction gives p = 1.000. Width-normalised exposure is similar: 3.23 % of pedestrian/cyclist object-frames and 3.28 % of car object-frames exceed one third of box width. These controls separate class-level performance from depth offset and box-width exposure alone. The class-level results therefore retain separate HOTA, identity-switch and depth-noise summaries. Sequence-weighted sensitivity analyses are reported with the relevant comparisons in §6.6.

---

## 9 Discussion and Conclusion

### 9.1 Evaluation Protocol

MOT17 tracking results use the standard validation-half protocol, with frozen detections and common tracker settings across configurations. MOT20 contributes the full-sequence geometric reference contrast. These protocols support the within-study comparisons in §4–§5.

### 9.2 Measurement Scope

The shared-warp geometry is measured on KITTI using sensor ego-motion and 3D annotations to separate camera-induced displacement from object motion. MOT17 measures reference-warp disagreement and tracking headroom; MOT20 measures disagreement with an offline reference; UAVDT measures the online-compensation contrast. Each benchmark therefore supports the conclusion associated with its measurement protocol.

### 9.3 Application Conditions

The MOT17 reference is a stronger estimate within the same four-degree-of-freedom family, so the reported headroom concerns that family under the evaluated association rules. KITTI uses calibrated GPS/INS ego-motion, a motion-only tracker and fixed configurations evaluated on the labelled sequences; its geometric residuals are relative to the sensor and annotation references. The depth model is the VKITTI outdoor metric checkpoint, and the sweeps inject independent multiplicative noise. The homography uses estimated background depth on moving frames and an annotation-anchored fallback on near-static frames (§6.5). These conditions define the reported application setting.

### 9.4 Reproducibility

The release provides the final configuration definitions, frozen-detection checksums, evaluation summaries and numerical verification tools. These support reconstruction of the reported tables and figures from the measurement data.

### 9.5 Conclusion

The study connects measured compensation-accuracy headroom with depth-aware global correction. On MOT17 with camera motion present, reference substitution gives −0.04 HOTA with a 95 % upper interval endpoint of +0.05 without appearance, and +0.19 [+0.05, +0.52] with appearance. Enabling compensation gives +3.43 without appearance and +3.50 with it. These matched comparisons locate the headroom within the evaluated warp family. On KITTI, the least-squares target-fitted similarity leaves residual corrections differing by more than 5 px in 27.1 % of moving frames. A global homography fitted to background points at their estimated depths cuts the within-frame spread to 1.37 px and improves car HOTA over online compensation by +1.19 [+0.26, +1.92]. On pedestrians, it changes identity switches from 126 to 97, and to 85 with contact-point application. The shared correction delivers spatially varying compensation without per-object association under the sensor and fallback protocol of §6.5. For translating platforms with a dominant scene plane, depth-aware global geometry is a useful direction for camera-motion compensation. The measurement framework connects the choice of correction to residual spread, association-gate changes and tracking outcomes.

---

## Data and Code Availability

All measurement code and all measurement data are released: 43 analysis scripts and 4 shell drivers, 22 result CSVs, the frozen detection manifests with per-file SHA-256, TrackEval output for all 63 evaluated tracker runs (47 on KITTI, 14 on MOT17, 2 on UAVDT), the script that regenerates every figure from those CSVs, the script that builds the submission LaTeX from the Markdown source, and a numerical verification tool that recomputes the paper's numbers from source and exits non-zero on any mismatch. The release is archived at <https://doi.org/10.5281/zenodo.23092962> (all versions; v1.0.0 is 10.5281/zenodo.23092963) and developed at <https://github.com/YifuZhao-mpu/mot-cmc>. The benchmarks themselves (MOT17, MOT20, UAVDT, KITTI) are public and are not redistributed; the artefacts each result depends on, and the SHA-256 of those whose identity affects a number, are listed in the release.

## Ethics Statement

This work uses only public computer-vision benchmarks. It involved no human subjects, no new data collection from people, and no personally identifying information beyond what those benchmarks already contain. No ethics approval was required.

## Responsible Use

This work uses public tracking benchmarks relevant to autonomous driving and pedestrian identity preservation. The same capability can support persistent tracking of individuals, so application design should account for privacy and the intended use of tracking outputs.

## AI-Assistance Disclosure

A large language model (Anthropic Claude) assisted with literature search, measurement and analysis code, experimental review and drafting. OpenAI Codex assisted with editorial revision and typesetting. Numerical results were produced by executing the measurement code on the data. The authors specified the experiments, verified the instruments and retain responsibility for the manuscript.

## CRediT Author Statement

**Yifu Zhao**: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing — original draft. **Xiaofan Zou**: Methodology, Validation, Writing — review & editing. **Yanxiao Li**: Investigation, Validation, Visualization. **Junhao Wei**: Investigation, Data curation, Writing — review & editing. **Sio-Kei Im**: Resources, Funding acquisition, Supervision. **Yapeng Wang**: Conceptualization, Supervision, Project administration, Funding acquisition, Writing — review & editing. **Xu Yang**: Methodology, Supervision, Writing — review & editing. All authors read and approved the final manuscript. *The contribution taxonomy is CRediT (Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Resources, Data curation, Writing — original draft, Writing — review & editing, Visualization, Supervision, Project administration, Funding acquisition). All listed authors' roles are stated above.*

## Funding

This work is supported by the grant from Macao Polytechnic University (RP/FCA-06/2026) and the Macao Science and Technology Development Fund (FDCT-MOST: 0018/2025/AMJ).

## Competing Interests

The authors declare no competing interests.

---

## References

[1] Aharon, N., Orfaig, R., & Bobrovsky, B.-Z. (2022). BoT-SORT: Robust associations multi-pedestrian tracking. *arXiv preprint* arXiv:2206.14651. https://doi.org/10.48550/arXiv.2206.14651

[2] Du, Y., Wan, J., Zhao, Y., Zhang, B., Tong, Z., & Dong, J. (2021). GIAOTracker: A comprehensive framework for MCMOT with global information and optimizing strategies in VisDrone 2021. In *Proceedings of the IEEE/CVF International Conference on Computer Vision Workshops* (pp. 2809–2819). https://doi.org/10.1109/ICCVW54120.2021.00315

[3] Safdarnejad, S. M., Liu, X., & Udpa, L. (2015). Robust global motion compensation in presence of predominant foreground. In *Proceedings of the British Machine Vision Conference* (pp. 21.1–21.11). https://doi.org/10.5244/C.29.21

[4] Irani, M., & Anandan, P. (1998). A unified approach to moving object detection in 2D and 3D scenes. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 20(6), 577–589. https://doi.org/10.1109/34.683770

[5] Mahdian, N., Jani, M., Soufi Enayati, A. M., & Najjaran, H. (2024). Ego-motion aware target prediction module for robust multi-object tracking. *arXiv preprint* arXiv:2404.03110. https://doi.org/10.48550/arXiv.2404.03110

[6] Bewley, A., Ge, Z., Ott, L., Ramos, F., & Upcroft, B. (2016). Simple online and realtime tracking. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3464–3468). https://doi.org/10.1109/ICIP.2016.7533003

[7] Wojke, N., Bewley, A., & Paulus, D. (2017). Simple online and realtime tracking with a deep association metric. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3645–3649). https://doi.org/10.1109/ICIP.2017.8296962

[8] Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. In *Computer Vision – ECCV 2022* (Lecture Notes in Computer Science, Vol. 13682, pp. 1–21). https://doi.org/10.1007/978-3-031-20047-2_1

[9] Cao, J., Pang, J., Weng, X., Khirodkar, R., & Kitani, K. (2023). Observation-centric SORT: Rethinking SORT for robust multi-object tracking. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition* (pp. 9686–9696). https://doi.org/10.1109/CVPR52729.2023.00934

[10] Shi, J., & Tomasi, C. (1994). Good features to track. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 593–600). https://doi.org/10.1109/CVPR.1994.323794

[11] Lucas, B. D., & Kanade, T. (1981). An iterative image registration technique with an application to stereo vision. In *Proceedings of the 7th International Joint Conference on Artificial Intelligence* (Vol. 2, pp. 674–679).

[12] Bouguet, J.-Y. (2001). *Pyramidal implementation of the affine Lucas–Kanade feature tracker: Description of the algorithm*. Intel Corporation, Microprocessor Research Labs.

[13] Fischler, M. A., & Bolles, R. C. (1981). Random sample consensus: A paradigm for model fitting with applications to image analysis and automated cartography. *Communications of the ACM*, 24(6), 381–395. https://doi.org/10.1145/358669.358692

[14] Evangelidis, G. D., & Psarakis, E. Z. (2008). Parametric image alignment using enhanced correlation coefficient maximization. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 30(10), 1858–1865. https://doi.org/10.1109/TPAMI.2008.113

[15] Du, Y., Zhao, Z., Song, Y., Zhao, Y., Su, F., Gong, T., & Meng, H. (2023). StrongSORT: Make DeepSORT great again. *IEEE Transactions on Multimedia*, 25, 8725–8737. https://doi.org/10.1109/TMM.2023.3240881

[16] Stanojević, V. D., & Todorović, B. T. (2024). BoostTrack: Boosting the similarity measure and detection confidence for improved multiple object tracking. *Machine Vision and Applications*, 35(3), 53. https://doi.org/10.1007/s00138-024-01531-5

[17] Yi, K., Luo, K., Luo, X., Huang, J., Wu, H., Hu, R., & Hao, W. (2024). UCMCTrack: Multi-object tracking with uniform camera motion compensation. In *Proceedings of the AAAI Conference on Artificial Intelligence*, 38(7), 6702–6710. https://doi.org/10.1609/aaai.v38i7.28493

[18] Maggiolino, G., Ahmad, A., Cao, J., & Kitani, K. (2023). Deep OC-SORT: Multi-pedestrian tracking by adaptive re-identification. In *Proceedings of the IEEE International Conference on Image Processing* (pp. 3025–3029). https://doi.org/10.1109/ICIP49359.2023.10222576

[19] Stanczyk, T., Yoon, S., & Brémond, F. (2026). Training-free long-term multi-object tracking for sports video analytics. *arXiv preprint* arXiv:2608.15688. https://doi.org/10.48550/arXiv.2608.15688

[20] Claasen, P. J., & de Villiers, J. P. (2026). One homography is all you need: IMM-based joint homography and multiple object state estimation. *Expert Systems with Applications*, 302, 130562. https://doi.org/10.1016/j.eswa.2025.130562

[21] Ma, J., Luo, H., Chen, Q., Qi, Y., Sun, Y., Beheshti, A., Zhang, J., & Yang, M.-H. (2026). Tracking the unstable: Appearance-guided motion modeling for robust multi-object tracking in UAV-captured videos. In *Proceedings of the AAAI Conference on Artificial Intelligence*. Preprint arXiv:2508.01730. https://doi.org/10.48550/arXiv.2508.01730

[22] Liu, Z., Wang, X., Wang, C., Liu, W., & Bai, X. (2025). SparseTrack: Multi-object tracking by performing scene decomposition based on pseudo-depth. *IEEE Transactions on Circuits and Systems for Video Technology*. Preprint arXiv:2306.05238. https://doi.org/10.48550/arXiv.2306.05238

[23] Wu, J., & Liu, Y. (2024). DepthMOT: Depth cues lead to a strong multi-object tracker. *arXiv preprint* arXiv:2404.05518. https://doi.org/10.48550/arXiv.2404.05518

[24] Solano-Carrillo, E., Sattler, F., Alex, A., Klein, A., Pereira Costa, B., Bueno Rodriguez, A., & Stoppe, J. (2024). UTrack: Multi-object tracking with uncertain detections. *arXiv preprint* arXiv:2408.17098. https://doi.org/10.48550/arXiv.2408.17098

[25] Chapel, M.-N., & Bouwmans, T. (2020). Moving objects detection with a moving camera: A comprehensive review. *Computer Science Review*, 38, 100310. https://doi.org/10.1016/j.cosrev.2020.100310

[26] Luiten, J., Ošep, A., Dendorfer, P., Torr, P., Geiger, A., Leal-Taixé, L., & Leibe, B. (2021). HOTA: A higher order metric for evaluating multi-object tracking. *International Journal of Computer Vision*, 129(2), 548–578. https://doi.org/10.1007/s11263-020-01375-2

[27] Yang, Y., Shim, K., Ko, K., & Kim, C. (2026). Tracking-by-detection in multi-object tracking: Survey and experiments. *arXiv preprint* arXiv:2609.08265. https://doi.org/10.48550/arXiv.2609.08265

[28] Geiger, A., Lenz, P., & Urtasun, R. (2012). Are we ready for autonomous driving? The KITTI vision benchmark suite. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 3354–3361). https://doi.org/10.1109/CVPR.2012.6248074

[29] Geiger, A., Lenz, P., Stiller, C., & Urtasun, R. (2013). Vision meets robotics: The KITTI dataset. *The International Journal of Robotics Research*, 32(11), 1231–1237. https://doi.org/10.1177/0278364913491297

[30] Ge, Z., Liu, S., Wang, F., Li, Z., & Sun, J. (2021). YOLOX: Exceeding YOLO series in 2021. *arXiv preprint* arXiv:2107.08430. https://doi.org/10.48550/arXiv.2107.08430

[31] Luiten, J., & Hoffhues, A. (2020). *TrackEval* [Computer software]. https://github.com/JonathonLuiten/TrackEval

[32] Milan, A., Leal-Taixé, L., Reid, I., Roth, S., & Schindler, K. (2016). MOT16: A benchmark for multi-object tracking. *arXiv preprint* arXiv:1603.00831. https://doi.org/10.48550/arXiv.1603.00831

[33] Dendorfer, P., Rezatofighi, H., Milan, A., Shi, J., Cremers, D., Reid, I., Roth, S., Schindler, K., & Leal-Taixé, L. (2020). MOT20: A benchmark for multi object tracking in crowded scenes. *arXiv preprint* arXiv:2003.09003. https://doi.org/10.48550/arXiv.2003.09003

[34] Yu, H., Li, G., Zhang, W., Huang, Q., Du, D., Tian, Q., & Sebe, N. (2020). The unmanned aerial vehicle benchmark: Object detection, tracking and baseline. *International Journal of Computer Vision*, 128(5), 1141–1159. https://doi.org/10.1007/s11263-019-01266-1

[35] He, L., Liao, X., Liu, W., Liu, X., Cheng, P., & Mei, T. (2020). FastReID: A PyTorch toolbox for general instance re-identification. *arXiv preprint* arXiv:2006.02631. https://doi.org/10.48550/arXiv.2006.02631

[36] Yang, L., Kang, B., Huang, Z., Zhao, Z., Xu, X., Feng, J., & Zhao, H. (2024). Depth Anything V2. *arXiv preprint* arXiv:2406.09414. https://doi.org/10.48550/arXiv.2406.09414

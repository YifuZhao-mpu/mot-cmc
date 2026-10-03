# Cover Letter

**To**: The Editors, *International Journal of Computer Vision*
**Re**: *Camera-Motion Compensation in Tracking-by-Detection: Accuracy Headroom and Depth-Aware Shared Warps*
**Article type**: Original Paper (measurement and evaluation study)

---

Dear Editors,

We submit a measurement study of camera-motion compensation in tracking-by-detection. It quantifies the accuracy headroom of shared warps and evaluates depth-aware global correction under camera translation.

**Measurement Objective.** Published ablations measure the benefit of enabling compensation. BoT-SORT's Table 1 gives +0.94 HOTA on MOT17, which our baseline reproduces to within 0.06. We measure the headroom remaining after a working compensator is in place through a stronger reference warp, association-gate changes and matched tracking comparisons.

**Main Findings.** On the MOT17 sequences that actually have camera motion, substituting a
non-causal oracle warp is worth −0.04 HOTA with a 95 % upper interval endpoint of +0.05 without an appearance
channel and +0.19 [+0.05, +0.52] with one — against +3.43 [+1.01, +5.52] for having a working
compensator at all. Reference substitution changes the association gate's decision for 55 of 109,955 ground-truth pairs, including 34 harmful changes.

On KITTI, depth-aware global correction addresses camera translation using a shared model. A global homography fitted to background points at their monocularly estimated depths, with sensor ego-motion, cuts the within-frame residual spread from 8.67 px to 1.37 px and improves car HOTA over online compensation by +1.19 [+0.26, +1.92]. It reduces pedestrian identity switches from 126 to 97, and to 85 with contact-point application, without per-object association.

**Evaluation Conditions.** KITTI comparisons use sensor ego-motion, fixed detections and a motion-only tracker. The homography uses estimated background depth on moving frames and the annotation-anchored near-static fallback defined in the manuscript. Each benchmark supports the measurement associated with its evaluation protocol.

**Relation to Prior Work.** Section 2 relates the study to compensation ablations, depth-aware tracking and the classical plane-plus-parallax geometry. The distinct contribution is the measurement of accuracy headroom and the controlled comparison of depth-aware shared and per-target corrections.



**Reproducibility.** We release 43 analysis scripts and 4 shell drivers, 22 result CSVs, and evaluation output for 63 tracker runs. Numerical verification recomputes the reported values and checks the configuration and data sources supporting each comparison.

The study connects compensation accuracy, depth-dependent geometry and tracking outcomes, with particular value for translating platforms with a dominant scene plane.

Yours sincerely,

Yifu Zhao, Xiaofan Zou, Yanxiao Li, Junhao Wei, Sio-Kei Im, Yapeng Wang and Xu Yang

On behalf of all authors — **Yapeng Wang** (corresponding), Faculty of Applied Sciences,
Macao Polytechnic University, Macao 999078, China · yapengwang@mpu.edu.mo

---

## Statements

- **Competing interests**: none.
- **Funding**: Macao Polytechnic University (RP/FCA-06/2026) and the Macao Science and Technology Development Fund (FDCT-MOST: 0018/2025/AMJ).
- **Data and code**: available at <https://doi.org/10.5281/zenodo.23092962>.
- **AI assistance**: disclosed in the manuscript. No number in the paper was produced by a language
  model; all were produced by executing the released code.
- **Prior submission**: this manuscript has not been submitted elsewhere.

# Cover Letter

**To**: The Editors, *International Journal of Computer Vision*
**Re**: *Camera-Motion Compensation Is Not the Bottleneck: A Measurement Study of Shared Warps in Tracking-by-Detection*
**Article type**: Original Paper (measurement and evaluation study)

---

Dear Editors,

We submit a measurement study of camera-motion compensation in tracking-by-detection. It proposes
no new tracker. Its contribution is a quantity the field has not measured and a diagnosis that
follows from measuring it, and we would like to be direct about both what it establishes and what
it does not.

**The question.** A steady stream of work proposes more robust camera-motion compensation. Every
such proposal implicitly claims that accuracy in the compensator is where the remaining headroom
is. Published ablations measure *having* compensation against *not* having it — BoT-SORT's own
Table 1 gives +0.94 HOTA on MOT17, and we reproduce it to within 0.06 — but we could find no
measurement of what a **perfect** warp would be worth once a working compensator is in place. That
is the quantity a robustness claim is about, and it is the one we bound.

**What we found.** On the MOT17 sequences that actually have camera motion, substituting a
non-causal oracle warp is worth −0.04 HOTA with a 95 % upper bound of +0.05 without an appearance
channel and +0.19 [+0.05, +0.52] with one — against +3.43 [+1.01, +5.52] for having a working
compensator at all. The error a perfect warp removes changes the association gate's decision for
34 of 109,955 ground-truth pairs.

Where a shared warp genuinely does fail — on KITTI, where the camera translates — we show the
missing ingredient is **depth**, not per-object treatment. A global homography fitted to background
points at their monocularly estimated depths cuts the within-frame residual spread from 8.67 px to
1.37 px, beats the compensator BoT-SORT ships by +1.19 HOTA [+0.26, +1.92] on cars, and reduces
pedestrian identity switches from 126 to 85. A per-target correction given ground-truth depth *and*
ground-truth association adds nothing on top of it.

**What it does not establish**, stated here because it is stated in the paper: the homography's
advantage over the shipped compensator is not significant on pedestrians; the shared-warp
limitation is measured on KITTI and inferred elsewhere, because two attempts to measure it without
ground-truth ego-motion failed and we report both; and the remedy costs a depth network at 65× a
compensation call.

**On priority.** We are not first to observe that compensation can fail — BoT-SORT's own limitations
section says it. Deep OC-SORT reported in 2023 that compensation does not help on static-camera
MOT20. EMAP corrects per object using depth on this benchmark with this base tracker. The 2026
survey we cite runs its own compensation ablation. Section 2 credits all of them, and §2.6 states
precisely what is left: the bound, the instruments, and the finding that the per-object part is
unnecessary.

**On the record of this work.** The paper reports four measurements of our own that replaced earlier
measurements of our own, two of which reversed a conclusion. Two were experiments whose
construction guaranteed the answer we had reached — a homography fitted to the displacements it was
scored against, and a warp bundle that was silently the identity on a third of moving frames. Both
were found by executing the released code, and §9.4 and Supplementary S2 record what each earlier
version reported. We would rather submit a paper that shows this than one that does not.

**Reproducibility.** We release 44 scripts, 21 result CSVs, TrackEval output for all 61 tracker runs,
and `verify_numbers.py`, which recomputes 526 of the paper's numbers from source and exits non-zero
on any mismatch. It also checks provenance — which run feeds which table, and whether any
configuration is silently switched off — because both of the defects above were provenance
failures that a value-only check passes. A referee can run one command.

We believe the bound is worth publishing whether or not the KITTI remedy holds up, and we have
tried to write the paper so that a reader can tell the two apart.

Yours sincerely,

[Author names]
[Affiliation]

---

## Suggested reviewers

[To be completed by the authors. We note that the authors of BoT-SORT, UCMCTrack and EMAP are all
directly concerned by the results and would be well placed to find any remaining error.]

## Statements

- **Competing interests**: none.
- **Funding**: [placeholder].
- **Data and code**: fully released; repository DOI to be minted at acceptance.
- **AI assistance**: disclosed in the manuscript. No number in the paper was produced by a language
  model; all were produced by executing the released code.
- **Prior submission**: this manuscript has not been submitted elsewhere.

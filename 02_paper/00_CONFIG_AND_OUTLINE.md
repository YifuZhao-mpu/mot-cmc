# Paper Configuration Record + Outline with Evidence Map

**Project**: Multi-Object Tracking under Camera Motion Uncertainty
**Stage**: ARS academic-paper, Phase 0 (CONFIG) + Phase 2 (ARCHITECTURE)
**Date**: 2026-09-23

---

## Part 1 — Paper Configuration Record

| Field | Value | Source |
|---|---|---|
| Paper type | IMRaD empirical — **measurement study**, not a method paper | D10 (binding) |
| Discipline | Computer vision / multi-object tracking |  |
| Target venue | **International Journal of Computer Vision** (Springer) | D11 |
| Review model | **Single-anonymous** — author identity visible to reviewers, so **no anonymisation** | IJCV guidelines |
| Template | Springer Nature `sn-jnl`, `[iicol]` two-column | IJCV guidelines |
| Length | ~25 journal pages ≈ **10,000–12,000 words** body | IJCV regular-article guidance |
| Citation style | Springer author-year (`spbasic`); every reference carries a DOI where one exists |  |
| Body language | English |  |
| Abstract | **English in the manuscript**; a separate Simplified-Chinese abstract delivered alongside for the author's own use (independently written, not a translation) | user decision |
| Authors | **Placeholders** — `[Author Name]`, `[Affiliation]`, `[Email]`, `[ORCID]`; CRediT likewise | user decision |
| Funding / COI | **Placeholders** — `[Funding: to be completed]` | user decision |
| Code & data | **Fully open**: 25 scripts, all 13 measurement CSVs, frozen-detection SHA-256 manifests, reproduction scripts | user decision |
| Upstream | Stage 1 handoff complete — Phase 1 (literature search) **skipped** |  |

### Why "fully open" is load-bearing here

The paper's central claim is that the field cannot evaluate compensation robustness on its
standard benchmarks. A paper making that claim while withholding its own measurement code
would be refuted by its own conduct. The release is therefore part of the argument, not an
administrative afterthought.

---

## Part 2 — Title

**Primary**

> Camera-Motion Compensation Is Not the Bottleneck:
> A Measurement Study of Shared Warps in Tracking-by-Detection

**Alternates**
- One Warp for Every Target: Measuring What Actually Limits Camera-Motion Compensation in Multi-Object Tracking
- Accurate but Irrelevant: Camera-Motion Compensation on MOT17, MOT20, UAVDT and KITTI

---

## Part 3 — Contribution claims (ordered by strength of support)

| # | Claim | Evidence | Status |
|---|---|---|---|
| C1 | **A measurement instrument** — the oracle-warp contrast quantifies compensation error on benchmarks with no ground-truth camera motion; the RANSAC residual the solver already discards predicts it (held-out AUC 0.866) | E4, E5 | Established |
| C2 | **Compensation is accurate on the standard benchmarks, and perfecting it is worthless** — on MOT17 an oracle warp is worth +0.099 HOTA and makes ID switches *worse*; the gap between two ordinary compensator choices (0.114 HOTA) is larger | E6, E7, E8, E8b | Established |
| C3 | **A reframing** — the limitation is one correction *shared* across targets at different depths, not the accuracy of that correction and not the expressiveness of the warp family (a deployable global homography removes 2.2 % of the within-frame spread) | E9, E9b | Established |
| C4 | **A scoped prescription** — per-target compensation on KITTI pedestrians, mechanism verified per frame, tolerant of realistic depth error; **not** established on KITTI cars | E10, E12, E13 | Scoped |

---

## Part 4 — Outline with Evidence Map

Word targets are planning aids, not quotas. Each subsection lists the exact artefact backing it.

### 1 Introduction — ~1,200 w

| Beat | Content | Evidence |
|---|---|---|
| 1.1 | Two defects in the shipped BoT-SORT code, quoted: appearance gated by motion agreement (`bot_sort.py:313`), and the warp applied without ever inflating uncertainty (`bot_sort.py:68-83`, `gmc.py:223` discards the inlier mask) | E2, E3 |
| 1.2 | The obvious hypothesis — compensation failure causes ID switches — and why it is testable | RQ_BRIEF §1.1 |
| 1.3 | What we found instead: compensation is accurate; perfecting it is worthless; the limitation is sharing | E6–E9 |
| 1.4 | Contributions C1–C4, with the scope limits stated in the contribution list itself |  |

### 2 Related Work — ~1,500 w

| Beat | Content | Evidence |
|---|---|---|
| 2.1 | CMC in tracking-by-detection: BoT-SORT's GMC lineage | arXiv:2206.14651 §3.2 |
| 2.2 | Prior attempts to handle unreliable compensation — **McByte++ §3.5 conditional CMC** (quoted verbatim: binary plausibility guard, criteria unpublished), **IMM-JHSE** (joint homography state, static-vs-dynamic IMM), **UCMCTrack** (avoids frame-wise CMC), **AMOT** (appearance-guided, UAV) | RQ_BRIEF §4.1 |
| 2.3 | Evaluation-methodology work: the 2026 KAIST survey's critique of inconsistent protocols; HOTA | arXiv:2609.08265; IJCV 129:548 |
| 2.4 | **Our position**: we do not claim to discover that CMC can fail — McByte++ got there first. We claim to measure whether it matters, and it does not on the benchmarks used to argue that it does | RQ_BRIEF §4.2 |

### 3 Measurement Instruments — ~1,800 w

| Beat | Content | Evidence |
|---|---|---|
| 3.1 | **Instrumented GMC** — recovers the statistics the solver discards; verified bit-identical to BoT-SORT's (`max|ΔH| = 0.0`) | `instrumented_gmc.py`; verification in DA-CP1 §1 V2 |
| 3.2 | **Oracle-warp contrast** — offline reference warp (full-resolution SIFT, mutual NN, foreground-masked, forward-backward verified fb-error 0.007–0.013 px). Explicitly a **lower-bound** instrument | `reference_warp.py`; DA-CP1 R1 |
| 3.3 | **Gate-flip counting** — per-pair, using GT identity, isolating geometry from detector and ReID | `gate_flip.py`; SQ2 artefact |
| 3.4 | **Ground truth where it exists** — KITTI oxts + calibration + 3D labels give true ego-motion | `kitti_egomotion.py` |
| 3.5 | **Protocol discipline** — frozen detections with SHA-256 manifests; determinism verified bit-identically on both MOT17 and KITTI; TrackEval throughout | S2 artefact; K5 §1 |

### 4 How Accurate Is Compensation? — ~1,500 w

| Beat | Content | Evidence |
|---|---|---|
| 4.1 | Four-benchmark scan, 14,236 + 40,685 frames | `mot17/mot20/uavdt_gmc_scan.csv` |
| 4.2 | Median residual 0.295–0.59 px; static/moving control passes (ρ 0.998 vs 0.945) | benchmark_regime_audit §2, §6 |
| 4.3 | **Predicting the error**: held-out AUC 0.866 from the residual alone; survives 4 confound stratifications and both placebos | A9 artefact; `confound_placebo.py` |
| 4.4 | **A reversal we report rather than hide**: the six-signal estimator won on synthetic data and *lost* on real data (0.774 vs 0.866); `n` is degenerate (99.94 % at ceiling), `tau` is a false-alarm generator | A9 §1–§3 |
| 4.5 | The within-sequence/between-sequence decomposition — the honest number is the within-sequence one | F9 |

### 5 Does Accuracy Matter? — ~2,000 w

| Beat | Content | Evidence |
|---|---|---|
| 5.1 | **Geometric bound** — median IoU cost of compensation error 0.00085; only 0.284 % of pairs within reach of the gate | `oracle_analysis.csv` |
| 5.2 | **Combinatorial bound** — 34 harmful gate flips in 109,955 GT pairs; 4 of 7 sequences give exactly zero; MOT17-13 is net beneficial | SQ2 artefact |
| 5.3 | **Empirical bound** — the compensation-value axis: none 68.118 → online 69.006 → file-GMC 69.120 → **oracle 69.105**, non-monotone; IDSW 337 → 139 → 140 → **144** | K5 §2b |
| 5.4 | Perfecting compensation is worth 11.1 % of having it, and **negative** on ID switches | K5 §2b |
| 5.5 | **UAVDT**: +0.163 HOTA, +5 ID switches out of 3342 — compensation does essentially nothing on the benchmark the literature treats as the hard case | benchmark_regime_audit §8 |
| 5.6 | **Consequence**: an improvement attributed to CMC on these benchmarks cannot be an improvement in compensation robustness | — |

### 6 What Actually Limits It — ~2,500 w

| Beat | Content | Evidence |
|---|---|---|
| 6.1 | KITTI: true ego-motion available; the first non-lower-bound measurement in the paper | `kitti_egomotion.py` |
| 6.2 | **Within-frame spread after oracle compensation**: median 5.88 px; >5 px in 54.3 % of moving frames; max 473 px; depth↔residual Spearman −0.400 | KITTI_per_object artefact |
| 6.3 | 2.08 % of object-frames gated out by the *irreducible* residual, vs 0.031 % on MOT17 — 67× | KITTI_per_object §4 |
| 6.4 | **Is a richer warp family the fix? No.** A deployable global homography cuts the spread by 2.2 % (6.23 → 6.10 px). We also report the 91 % figure obtained by fitting a homography to the objects' own displacements and explain why that number is not achievable | `kitti_model_class.csv`; DA-CP2 §7 M1 |
| 6.5 | **Tracking experiment**, four configurations, one controlled variable | KITTI_tracking artefact |
| 6.6 | **Results with bootstrap CIs** — per-target vs global similarity: HOTA +0.842 [+0.067, +1.226], AssA +1.639 [+0.071, +2.426], IDSW −3.12/seq [−5.86, −0.03]. **Per-target vs global homography: HOTA CI [−0.157, +0.998] crosses zero; only the ID-switch reduction survives** | `bootstrap_ci.py` |
| 6.7 | **Mechanism verified per frame** — all 20 of the pedestrian ID-switch improvement comes from the top exposure quartile, none from the bottom (Spearman +0.058, p = 0.0047); the counter reproduces TrackEval's delta exactly | DA-CP2 §6 |
| 6.8 | **Cars: not established** — CI crosses zero on every metric, sign flips under leave-one-out, no stratification | E11 |

### 7 Deployability — ~1,000 w

| Beat | Content | Evidence |
|---|---|---|
| 7.1 | What must actually be estimated: ego-motion is an onboard sensor on a vehicle; identity was eliminated by querying the depth map at the tracker's own predicted box; **only depth must be estimated** | KITTI_tracking §4 |
| 7.2 | Synthetic tolerance: flat to ~22 % relative depth error, positive at 35 %, collapses at 65 % — with the caveat that injected noise is independent while real error is spatially correlated | KITTI_tracking §7; DA-CP2 m3 |
| 7.3 | **Real monocular depth** (Depth-Anything-V2 Metric VKITTI): +0.855 HOTA CI [+0.141, +1.339], versus +0.842 with ground truth — essentially no loss. Disclosure: the checkpoint is domain-matched, so this is a best-case test | E12 |
| 7.4 | Against plain image-based GMC the deployable pedestrian result is **not** significant (CI [−0.852, +1.766]) | E12b |

### 8 What We Could Not Explain — ~600 w

| Beat | Content | Evidence |
|---|---|---|
| 8.1 | The pedestrian/car split | E11, E14 |
| 8.2 | **Refutation 1** — "pedestrians sit further from the frame-median depth": false. Cars 0.339 vs pedestrians 0.264; Mann-Whitney in the hypothesised direction p = 1.000 | E14 |
| 8.3 | **Refutation 2** — "pedestrian boxes are more exposed per unit error": false. 2.21 % of car object-frames exceed w/3 versus 1.57 % for pedestrians | E14 |
| 8.4 | No third explanation was sought. Searching until one fits is the wrong procedure | — |

### 9 Limitations and Conclusion — ~900 w

| Beat | Content | Evidence |
|---|---|---|
| 9.1 | **MOTChallenge evaluation service is offline field-wide** — TUM notice, page last modified 2026-09-08, accessed 2026-09-20; verbatim quotation; no contemporary submission can report new test numbers | F3 |
| 9.2 | Both oracles use ground truth; the depth model is domain-matched; the tracker is not a tuned KITTI system; the robot study is not done | Synthesis §5 |
| 9.3 | Two specification errors found and corrected during the work, both recorded | F19–F20 |
| 9.4 | Conclusion: measure before attributing |  |

### Back matter

Data Availability (full release) · Code Availability · Ethics (public benchmarks; no human subjects) ·
CRediT (placeholder) · Funding (placeholder) · Competing Interests · **AI-Assistance Disclosure** ·
Responsible Use Statement (pedestrian tracking is surveillance-adjacent)

---

## Part 5 — Figures (8)

| # | Figure | Source |
|---|---|---|
| F1 | Compensation-value axis: HOTA and IDSW across none/online/file-GMC/oracle, MOT17 | K5 §2b |
| F2 | Four-benchmark reliability distributions (ρ, ε, displacement) | three `*_gmc_scan.csv` |
| F3 | Within-frame residual spread after oracle compensation, KITTI, by depth ratio | `kitti_per_object.csv` |
| F4 | Warp-family comparison: similarity / affine / homography, spread vs frame fraction | `kitti_model_class.csv` |
| F5 | Bootstrap CI forest plot, all reported comparisons, both classes | `bootstrap_ci.py` |
| F6 | Mechanism: improvement by exposure quartile, pedestrian vs car | `kitti_causal_link.csv` |
| F7 | Depth-noise tolerance curve with the real-model point marked | KITTI_tracking §7 |
| F8 | Signal-selection: held-out AUC by subset size, synthetic vs real | `signal_subset_search.csv` |

## Part 6 — Tables (6)

T1 four-benchmark regime audit · T2 MOT17 compensation-value axis · T3 gate flips per sequence ·
T4 KITTI four-configuration results per class · T5 bootstrap CIs · T6 depth-noise tolerance

---

## Part 7 — Claims this paper will NOT make

Recorded so the draft can be checked against it.

1. That we discovered compensation can fail — McByte++ §3.5 precedes us.
2. That per-target compensation improves tracking in general — it is established on one class of one benchmark.
3. That per-target beats a global **homography** on HOTA — that CI crosses zero.
4. That the deployable pipeline beats plain image-based GMC on pedestrians — that CI crosses zero.
5. That the car result is positive — it is not established.
6. That we can explain the class difference — we cannot.
7. Any MOTChallenge test-set number.

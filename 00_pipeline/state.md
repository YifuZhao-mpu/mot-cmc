# Pipeline State — Multi-Object Tracking under Camera Motion Uncertainty

**run_id**: `mot-cmc-20260920` (stable; never re-derived)
**Skill**: academic-pipeline v3.22.0 · **Entry**: Stage 1 (RESEARCH), no prior materials
**Mode config**: Stage 1 `full` · execution order modified by user decision (diagnostics before writing)
**Flags**: `ARS_PASSPORT_RESET` unset · `ARS_CLAIM_AUDIT` unset · `ARS_INQUIRY_LEDGER` unset
· `ARS_MODEL_TIERING` unset · `ARS_CROSS_MODEL` unset

---

## Global state: `in_progress` — Stage 1, Phase 2 (INVESTIGATION), diagnostic branch

The user elected, at the Stage 1 Phase 1 checkpoint, to run the diagnostic experiments
(S1–S3.5) **before** committing to a paper form. Stage 2 (WRITE) has not begun and must not
begin until the power gate returns.

---

## User decisions on record

| # | Decision | Value | Where |
|---|---|---|---|
| D1 | Experimental evidence source | Run real experiments on this machine | Intake |
| D2 | Target venue | Decide after Stage 1 evidence | Intake |
| D3 | Robot validation | Pipeline supplies protocol; user records and annotates | Intake |
| D4 | Stage 1 mode | `full` | Intake |
| D5 | Execution order | Diagnostics first, paper form decided after | Stage 1 Phase 1 checkpoint |
| D6 | Power-gate threshold | **3×** (N2 ≥ 3 × N1) | Stage 1 Phase 1 checkpoint |
| D7 | Response to gate FAIL | **Option A** — extend to high-camera-motion benchmarks | Stage 1 Phase 2 checkpoint |
| D8 | Which benchmarks | **Both** — UAVDT/VisDrone-VID (rotation-dominated) *and* KITTI (translation-dominated) | Stage 1 Phase 2 checkpoint |
| D9 | After the KITTI result | **Test deployability**: replace ground-truth depth with estimated depth | Stage 1 Phase 2 checkpoint |
| D10 | Paper framing | **(B) measurement + benchmark critique**, not a method paper — the bootstrap CIs falsified the strong method claim | Stage 1 exit |
| D11 | Target venue | **International Journal of Computer Vision (IJCV)** — Springer, Q1, IF 10.3, hybrid OA (APC $4,290 if OA chosen) | Stage 1 exit |

## Checkpoints

| # | Stage | Type | Outcome |
|---|---|---|---|
| 1 | Intake | FULL | 4 decisions recorded (D1–D4) |
| 2 | Stage 1 Phase 1 (SCOPING) | FULL | Devil's Advocate REVISE → revision round 1 → PASS (conditional); D5, D6 recorded |

`consecutive_continue_count`: 0 (user has made an explicit choice at every checkpoint)
Accumulated round-trips: **3** / worst-case budget ≈ 50

## Gates

| Gate | Definition | Status |
|---|---|---|
| **S2** | Reproduce published BoT-SORT half-val numbers | ✅ **PASS** — HOTA Δ+0.01, IDF1 Δ−0.03, MOTA Δ+0.05 |
| **K3** | Method reduces exactly to BoT-SORT at r≡1 | ✅ **PASS** — max diff 0.0 (numerical, re-verified after every patch) |
| **K1** | Compensation error is attributable, survives confound conditioning + placebo | ✅ **PASS** — I1 done; I2 survives all 4 stratifications (weakest −0.741) and within-moving-camera (−0.771); I3 passes global and within-sequence placebo |
| **K2** | ≥10% of low-r IDSWs have a suppressed-but-correct appearance match | ❌ **FAIL** — 34 harmful gate flips in 109,955 GT pairs (0.031%); 4 of 7 sequences give exactly zero; MOT17-13 is net beneficial |
| **K5 / power gate** | N2 ≥ 3 × N1 | ❌ **FAIL** — N1 = 0 exactly (5 runs bit-identical, ratio test vacuous); N2 = +0.099 HOTA, **IDSW +5 (worse)**; perfecting compensation = 11.1% of the value of having it, and −0.015 HOTA vs the published baseline |
| Stage 2.5 INTEGRITY | Mandatory, 5-phase + 7-mode AI-failure checklist | not reached |
| Stage 4.5 FINAL INTEGRITY | Mandatory | not reached |

## Findings that changed the plan (all recorded, none reverted silently)

| # | Finding | Effect |
|---|---|---|
| F1 | McByte++ (arXiv:2608.15688) §3.5 already proposes *conditional* CMC | Novelty downgraded HIGH→MODERATE; claim narrowed to quantitative + spatial + cost-propagating |
| F2 | Coupling defect verified in released code (`bot_sort.py:313`) and covariance never inflated (`:68-83`) | Strongest asset; two code-level defects, not inferences |
| F3 | MOTChallenge benchmark service **globally offline** (TUM notice, 2026-09-08) | Earlier "unreachable" reading was a local proxy artefact — corrected in RQ Brief and Blueprint. Test-server numbers impossible for everyone; M4 downgraded to a disclosure requirement |
| F4 | On real MOT17, `eps` alone beats the 6-signal combination (held-out AUC 0.866 vs 0.774) | Estimator simplified to `{eps}`; synthetic and real results both reported (`A9_signal_selection.md`) |
| F5 | `n_inliers < 100` occurs in **0** of 5316 MOT17 frames | The catastrophic failure regime the literature describes is absent from MOT17 |
| F6 | Per-frame-median gate-closure rate is 0.0% on all 7 sequences | Q3 as first posed was the wrong question; replaced by direct gate-flip measurement |
| F7 | **K2 fails**: 34 harmful gate flips / 109,955 GT pairs; harmful flips sit on 21–33 px boxes at median visibility 0.0 | The method claim is not supported on MOT17. The arithmetic: 1.31 px median error against 21–124 px boxes leaves IoU at 0.89–0.98, far above the 0.5 gate |
| F8 | The **measurement** contribution survives everything: I2 all strata, I3 both placebos | Predicting compensation error from the free RANSAC residual is a defensible standalone contribution |
| F9 | Within-sequence placebo reaches −0.748 of the raw −0.928 | Much of the headline correlation is between-sequence; the within-sequence signal (−0.60 to −0.79 per sequence) must be reported separately rather than quoting −0.928 as per-frame predictive power |
| F10 | **KITTI ships ground-truth ego-motion** (oxts GPS/IMU) + calibration + 3D labels | First measurement against TRUE camera motion rather than a better estimate. Everything on MOT17 was a lower bound for this reason |
| F11 | **On KITTI the residual is per-OBJECT, not per-frame.** After ORACLE 4-DOF compensation, objects in the same frame disagree by >5 px in **54.3 %** of moving frames (median spread 5.88 px, max 473 px); depth↔residual Spearman median −0.400, negative in 75.3 % of frames | A single global warp is structurally inadequate under translation. The user's original per-target premise is unmeasurable on MOT17 and dominant on KITTI |
| F12 | KITTI: **2.082 %** of object-frames gated out by the *irreducible* residual, vs **0.031 %** on MOT17 — **67×** | And the KITTI figure is what remains after *perfect* compensation, while the MOT17 figure is the total effect of imperfect compensation |
| F13 | Correction to an earlier single-sequence reading: a best-fit 4-DOF similarity absorbs most of KITTI's forward translation (median residual 0.101 px, not ~8 px) | The 8 px figure was measured against a rotation-only homography. The information is in the within-frame spread, not the median |
| F14 | **KITTI tracking: per-target beats the best global warp on PEDESTRIANS** — +0.847 ± 0.104 HOTA over 7 perturbation settings (7/7 positive), −22.3 IDSW (7/7 better), effect exceeds the perturbation noise scale (0.738), leave-one-sequence-out never flips sign, and the gain follows translation magnitude (+0.787 moving vs −0.006 static) | The per-target premise the project started from is validated — in the domain where it is measurable |
| F15 | **Same comparison on CARS is NOT established** — +0.319 ± 0.248 HOTA inside its own noise scale (1.475), sign flips under leave-one-out, no mechanism stratification | Reported as not established rather than averaged in with the pedestrian result |
| F16 | **Two explanations for the class split were pre-specified and BOTH refuted by measurement** — (a) pedestrians further from frame-median depth: false, cars are (0.339 vs 0.264, p=1.000 in the hypothesised direction); (b) pedestrian boxes more exposed per unit error: false, cars are (2.21 % vs 1.57 % above w/3) | No third explanation sought. The class difference is reported as unexplained |
| F18 | **DA-CP2 (Phase 3 adversarial review) raised 1 Critical + 3 Major; all four resolved by measurement, three of them changing a stated conclusion** | The project's own claims were revised downward twice as a result — see F19-F21 |
| F19 | **C1 resolved**: the causal link E9→E10 was tested per frame and per class. **All 20** of the pedestrian ID-switch improvement comes from the top exposure quartile, none from the bottom (Spearman +0.058, p=0.0047); the per-frame counter reproduces TrackEval's pedestrian delta exactly (20 = 20) | The mechanism is no longer an inference for pedestrians. The same counter is demonstrably unreliable for cars (opposite sign to TrackEval, cause: COCO car/truck/bus all labelled `Car` while KITTI treats Van/Truck as ignore) and is not used there |
| F20 | **M1 resolved, and it overturned a claim I had just made.** A *deployable* global homography (fitted to the static scene) cuts the within-frame spread by only **2.2 %**. An intermediate analysis reported 91.4 %, but that homography was fitted to the objects' own true displacements — a curve fit to the answer. Both the original "no 2D warp works" framing and the intermediate retraction were wrong; the correct statement is that the limitation is the *sharing*, not the warp family | Corrected in `benchmark_regime_audit.md` §7 and `SYNTHESIS.md` |
| F21 | **M2 resolved: bootstrap CIs over sequences materially widen every interval.** Per-target vs global **similarity** (pedestrian) holds on all three metrics. Per-target vs global **homography**: HOTA [−0.157, +0.998] and AssA [−0.331, +2.046] **cross zero**; only IDSW survives. Deployable per-target vs plain online GMC (pedestrian): HOTA [−0.852, +1.766] **crosses zero** | `SYNTHESIS.md` revision 2 withdraws three revision-1 statements. Hyperparameter perturbation demoted from primary support to robustness footnote |
| F22 | **Deployability established for pedestrians**: substituting Depth-Anything-V2 Metric for ground-truth depth gives +0.855 HOTA CI [+0.141, +1.339] over the same global baseline, versus +0.842 with ground-truth depth — essentially no loss | The only input that must be estimated is depth; ego-motion is an onboard sensor on a vehicle and identity was eliminated by querying the depth map at the tracker's own predicted box |
| F17 | **Depth-noise tolerance (pedestrian)**: the gain is flat from 0 to ~22 % relative depth error (+0.83 to +1.12 HOTA), still positive at 35 %, collapses at 65 %. On cars it turns negative at 5 % | Modern monocular metric depth achieves ~5-10 % AbsRel on KITTI, so the pedestrian gain is within reach of estimated depth. The car "gain" does not survive, consistent with it not being real |

## Artifacts

| Path | Content |
|---|---|
| `01_research/RQ_BRIEF.md` | RQ, sub-questions, FINER, novelty table, 5 falsification criteria |
| `01_research/METHODOLOGY_BLUEPRINT.md` | Method design, causal identification (I1–I3), power gate, 12-row ablation matrix |
| `01_research/DEVILS_ADVOCATE_CP1.md` | Adversarial review + revision re-check + 3 carried risks |
| `01_research/ROBOT_RECORDING_PROTOCOL.md` | Factorial design, sync measurement, annotation spec, pilot acceptance, ethics |
| `99_artifacts/S2_baseline_gate.md` | Baseline reproduction evidence |
| `99_artifacts/A9_signal_selection.md` | Signal subset search; synthetic vs real disagreement |
| `99_artifacts/synthetic_study_summary.json` | Controlled failure study with known ground-truth warp |
| `04_experiments/*.csv` | 234 synthetic frames · 5316 MOT17 frames · 5309 oracle-contrast frames · MOT20 scan |
| `03_code/rac/` | Instrumented GMC · reference warp · RAC-Track · freeze/run/evaluate · gate/power analysis |
| `03_code/BoT-SORT`, `03_code/TrackEval` | Upstream, with compatibility patches recorded as git commits |

## Provenance

| Item | SHA-256 (first 32) |
|---|---|
| MOT17.zip (official, 5860214001 B) | recorded in `04_experiments/data/MOT17.zip.sha256` |
| MOT20.zip (official, 5028926248 B) | recorded in `04_experiments/data/MOT20.zip.sha256` |
| `bytetrack_ablation.pth.tar` | `26cb8d2808664e5068a4c812d53becbc` |
| `mot17_sbs_S50.pth` | `eb2e83afe774c85f20b735a7fabc4236` |

## Next actions — pivot executing (D7/D8)

The MOT17 ablation matrix A1–A11 is **not run** and the gate is **not re-run** (DA-CP1 R3).

1. Acquire UAVDT / VisDrone-VID and KITTI tracking.
2. Run the existing, already-validated instrument on them:
   reliability scan -> oracle-warp contrast -> gate-flip measurement -> compensation value axis.
   The same four-point axis (none / online / better-online / oracle) is the deliverable.
3. Decide per domain whether compensation error is large enough to change association
   outcomes. Only where it is does the method become worth building.
4. Report; Stage 1 Phase 2 checkpoint for the extended evidence.

### Pivot progress

| Domain | Data | Geometry measurement | Tracking experiment |
|---|---|---|---|
| KITTI (translation-dominated) | labels/oxts/calib ✅, images downloading | ✅ **done — regime confirmed** (F11, F12) | pending images |
| UAVDT (rotation-dominated) | ✅ 50 seq / 40,735 frames | reliability scan running | pending |
| VisDrone-VID | only a sampled HF mirror found; full VID source still to locate | — | — |

### Specification error found and corrected (recorded, not silently fixed)

The first KITTI oracle fitted the "best global warp" to the tracked objects' **true
displacements**. That is wrong: on KITTI the tracked objects are moving vehicles, so their
displacement is camera motion PLUS their own motion, and the Kalman filter already predicts
the second. The resulting "oracle" scored *below* the deployable online GMC (−1.028 HOTA on
car, −0.820 on pedestrian), which is the signature of double counting, not of a real effect.

Corrected specification: compensation answers *"if this target were momentarily static, where
would camera motion alone move it?"* — back-project at the target's depth, apply (R, t),
re-project. Object motion stays with the Kalman filter. Re-run as `kitti_warps_v2` / `v2_*`.

**The numbers from the first version are not reported as findings.**

A second asymmetry remains in v2 and is being addressed: `per_target` applies a translation
only, while the global modes apply a full similarity (which also rescales the box). A clean
isolation of "global vs per-target" requires the per-target correction to be a full local
similarity derived from the object's own box corners at its own depth.

**Open and not yet established**: that a tracker exploiting F11 improves KITTI metrics; that
monocular depth is accurate enough to exploit it (the 3D labels used are ground truth); and
anything about UAV footage, which is rotation-dominated and may behave like MOT17.

## Checkpoint 3 (Stage 1 Phase 2) — recorded

FULL checkpoint. Gate result presented with the complete compensation-value axis; user chose
Option A + both benchmark families. Accumulated round-trips: **4** / worst-case ≈ 50.

---

## Stage 2 / academic-paper Phase 3–4 — DRAFT COMPLETE (2026-09-23)

| Artefact | Path | Status |
|---|---|---|
| Approved outline | `02_paper/00_CONFIG_AND_OUTLINE.md` | user-approved 2026-09-23 ("不用调整进入下一阶段") |
| Full English draft | `02_paper/manuscript.md` | **11,382 words**, 9 sections + back matter |
| Phase 4 self-score | `02_paper/01_PHASE4_SELF_SCORE.md` | PROCEED |
| Figures | `05_figures/F1–F8` (.pdf + .png) | generated from source by `make_figures.py` |

| F# | New finding this phase |
|---|---|
| F23 | **Five numbers written from memory failed source-checking during drafting and were corrected** (DetA column, gate-flip per-sequence pair counts, MOT17 camera classification, UAVDT tracking scope, release counts). Recorded in the Phase 4 self-score. The corrected camera classification (static = 02/04/09; moving = 05/10/11/13) makes the §4.2 static/moving separation *complete* at sequence level and adds a moving-camera sequence to the zero-flip set. |
| F24 | **The deployable-homography measurement is now reproducible.** `kitti_global_family.py` recomputes it on the identical frame/object filter as the oracle study (verified: its oracle row reproduces 5.878 px exactly). Spread reduction **2.3 %** (7.588 → 7.418 px), >5 px fraction 0.16 pp worse. Supersedes the ad-hoc "2.2 %, 6.23 → 6.10 px". `SYNTHESIS.md` and `DEVILS_ADVOCATE_CP2.md` updated. |

**Pending**: Phase 5a citation compliance (3 references need DOI verification: AMOT,
McByte++, the 2026 survey) · Phase 5b Simplified-Chinese abstract · Phase 6 in-pair review ·
Stage 2.5 integrity gate · Stage 3 five-seat panel · Stage 5 LaTeX/PDF via `sn-jnl`.

## Phase 5a / 5b / 7 — COMPLETE (2026-09-23)

| F# | Finding |
|---|---|
| F25 | **Two fabricated citations caught by live DOI resolution.** (a) Claasen & de Villiers was listed as *Information Fusion* 118, 102971, DOI `10.1016/j.inffus.2025.102971` — that DOI resolves to an unrelated brain–computer-interface paper; the real record is *Expert Systems with Applications* 302, 130562, DOI `10.1016/j.eswa.2025.130562`. (b) Safdarnejad et al. was listed as BMVC 2016 DOI `10.5244/C.30.31` — resolves to a face-alignment paper; the real record is BMVC **2015**, `10.5244/C.29.21`. Two further entries had the method name in place of the title. Recorded in `02_paper/02_PHASE5A_CITATION_AUDIT.md`. |
| F26 | **Eight used-but-uncited resources added** (MOT16/17, MOT20, UAVDT, YOLOX, ByteTrack, TrackEval, Depth-Anything-V2, FastReID). Reference list is now 17 entries, all resolved live, all cited. |
| F27 | **The MOT17 value axis was motion-only.** Provenance check found `with_reid: False` in every Table-3 run — correct for reproducing BoT-SORT's published ablation row, but it left §1's coupling argument untested. Re-ran the axis with FastReID SBS-S50: having compensation **+1.146 HOTA / −140 IDSW**; perfecting it **−0.082 HOTA / +5 IDSW**. With the appearance channel on, a perfect warp has *negative* point value. New §5.4 + Table 4. Determinism verified: `R_oracle` vs `R_oracle_rep` **bit-identical** on all 7 sequences. |
| F28 | MOTChallenge notice re-verified 2026-09-23: **HTTP 410 Gone**, page Last-Modified 2026-09-08, quotation extended and checked verbatim. |
| F29 | **pandoc 3.11 silently drops pipe tables that follow a `---` thematic break** — 6 of 22 survived. `build_latex.py` strips the rules before conversion; all 22 now convert. Worth knowing for any future Markdown→LaTeX run in this project. |

| Artefact | Path |
|---|---|
| Citation audit | `02_paper/02_PHASE5A_CITATION_AUDIT.md` (verdict PASS, 0 unresolved) |
| Chinese abstract | `02_paper/03_ABSTRACT_ZH.md` |
| Submission LaTeX | `02_paper/latex/manuscript.tex` (Springer `sn-jnl`, two-column) |
| **Submission PDF** | `02_paper/latex/manuscript.pdf` — **20 pages**, 9 tables, 8 figures, 17 references |
| Build script | `03_code/rac/build_latex.py` (Markdown is the single source of truth) |

**Pending**: Phase 6 in-pair review · Stage 2.5 integrity gate · Stage 3 five-seat panel ·
Stage 4 revision · Stage 5 finalize · Stage 6 process summary · open-source release packaging.

## Phase 6 + Stage 2.5 — COMPLETE (2026-09-23)

### Phase 6 in-pair review — ACCEPT after 1 revision loop (of 2)

| F# | Finding |
|---|---|
| F30 | **The paper demanded CIs of its positive result and not of its negative one.** MOT17 carried point estimates against a zero run-to-run noise floor, which bounds nothing about the 7 sequences. Bootstrapped: the 95 % **upper bound** on the value of perfect compensation is **+0.49 HOTA** motion-only and **+0.13 HOTA** with appearance — indistinguishable from the interval for switching between two ordinary compensators. New §5.5 + Table 5. The same analysis showed the *positive control* (having compensation) has a HOTA interval crossing zero at n=7 motion-only; reported, and used to argue that §5.1/§5.2 (109,955 pairs each) are the load-bearing bounds. |
| F31 | **MOT20 was being carried by MOT17's evidence** in three sentences. MOT17 has three bounds, UAVDT one, MOT20 only the scan. All three now distinguish the evidence class. |
| F32 | **Zero figure citations, 7 of 10 tables uncited.** All 18 floats now referenced in text. |

### Stage 2.5 integrity — PASS after 5 corrections

**`03_code/rac/verify_numbers.py` now recomputes 380 manuscript values from source; 380/380 match.**

| # | Defect | Resolution |
|---|---|---|
| C-1 | §6.2 "negative in 75.3 % of frames" — denominator unstated (Spearman needs ≥4 objects; 3,379 of 4,318 moving frames) | both figures now stated |
| C-2 | §3.2 fb-error "0.007–0.013 px" **does not reproduce** — actual pooled median 0.002, per-seq 0.0002–0.012 | corrected to measured |
| C-3 | **Two estimators in adjacent sentences.** Leave-one-out was computed with unweighted per-sequence means while every CI uses GT-weighted aggregation. Under the paper's own estimator the car gain **does not** flip sign (ped [+0.332, +1.025], car [+0.096, +0.393], 0 flips) | claim **withdrawn**; car remains not-established on its primary grounds (CIs cross zero, negative at 5 % depth noise, no verified mechanism); `bootstrap_ci.py --loo` added |
| C-4 | §7.2 compared against a quantity the paper reports nowhere | compared against Table 7's interval |
| C-5 | Table 10 car HOTA 66.473 twice — looks like a copy-paste error | verified 66.47275 / 66.47348, stated |

| F# | Finding |
|---|---|
| F33 | §8's two class-split refutations were also ad-hoc; now `kitti_class_split.py`. Under the reproducible computation H1 holds as before (car 0.325 vs ped 0.246, p=1.000) but **H2 changes character**: exposure above w/3 is 3.33 % car vs 3.28 % ped — the classes are *equally* exposed, not oppositely ordered. §8 rewritten accordingly. |

7-mode AI-failure checklist: all clear (modes 3 and 4 clear **after** the corrections above).

| Artefact | Path |
|---|---|
| Phase 6 review | `02_paper/04_PHASE6_REVIEW.md` |
| Integrity report | `02_paper/05_STAGE2.5_INTEGRITY.md` |
| Numeric verifier | `03_code/rac/verify_numbers.py` (380 checks) |
| **Submission PDF** | `02_paper/latex/manuscript.pdf` — **22 pages**, 10 tables, 8 figures |

**Pending**: Stage 3 five-seat panel · Stage 4 revision · Stage 3' re-review · Stage 4.5 final
integrity (Mode 2) · Stage 5 finalize · Stage 6 process summary · open-source packaging.

## Stage 3 panel + Stage 4 revision, round 1 (2026-09-23/24)

**Five-seat panel: unanimous Major revision** (R2 "close to reject"). Four seats independently
raised the same Critical: the positive result's comparator is worse than the compensator the
tracker already ships, and the abstract does not say so. Full reports and dispositions in
`02_paper/06_STAGE3_PANEL_AND_ROADMAP.md`. **User decision: full revision, keep the prescription.**

| F# | Finding |
|---|---|
| F34 | **The "oracle" configuration fell back to the online warp** on 76/418 val-half frames of MOT17-05 (18.2 %). Table 3's "only variable is the warp" was false. `reference_strict` added and re-run: HOTA 69.105→**69.093** (motion-only), 69.344→**69.350** (appearance). **Disclosure required; measurement unaffected.** |
| F35 | **§6.4's warp-family test was degenerate — conclusion WITHDRAWN.** The static grid sat at one depth, so the induced map is a plane homography and `findHomography` recovered it to 6.2e-6 px. Refitted to background points at their own estimated depths: the deployable homography removes **81.8 %** of the within-frame spread (7.61→1.39 px), not 2.3 %. "A richer warp family is not the fix" is false. |
| F36 | **The replacement finding is stronger.** On the same 4,318 KITTI moving frames, measured at object centres against true displacement: online GMC spread **8.67 px** / HOTA **47.428**; depth-aware homography spread **1.39 px** / HOTA 46.884 (corners) and 46.779 (contact point, UCMCTrack's mechanism); per-target HOTA **47.576**. **The deployed estimator has 6.3× the residual spread of the homography and tracks better.** §5's thesis, established directly on KITTI with a 6× difference instead of MOT17's sub-pixel one. |
| F37 | **The cheap alternative is ruled out.** Global similarity anchored at the target class's own median depth: pedestrians +0.241 [−0.031, +0.699] (crosses zero, ~24 % of the per-target gain); cars **−0.667 [−1.885, −0.040]**, worse. Strengthens the per-target argument. |
| F38 | **"IDSW per sequence" is a GT-weighted mean, not a per-sequence rate** — −3.12 printed against a true −0.95 (KITTI ped) and −13.23 against −28.29 (MOT17). In the abstract. |
| F39 | **Effective sample size**: Kish ESS **3.05 of 21** (KITTI ped; one sequence 52.9 %, six with zero pedestrian GT) and **3.79 of 7** (MOT17). Weighted +0.842 [+0.067, +1.226] vs unweighted **+0.514 [+0.190, +0.883]**. |
| F40 | **§5.4's claim is WITHDRAWN.** Stratified by the paper's own static/moving control: perfecting compensation on the four moving sequences is **+0.0004 [−0.043, +0.052]** motion-only (an order of magnitude tighter than pooled) but **+0.169 [+0.013, +0.523]** with appearance — **excludes zero**. "Not positive in either configuration" is false. The static stratum is significant in the opposite direction, which is itself evidence the n=7 interval is uncalibrated. |
| F41 | **Frame exclusion is outcome-correlated**: MOT17-05 loses **24.6 %** of frames, excluded frames carry 1.066 px median residual vs 0.557 retained. §3.2 promised a per-sequence table that does not exist. Mitigating: adding them back moves the gate-flip result 0.031 %→0.033 %. |
| F42 | **Mechanism check restated**: paired permutation test, observed top-quartile improvement +20, null mean 4.99 sd 3.70, **p = 0.0001** (Spearman 0.058 was the wrong instrument). Cars p = 0.946 in the wrong direction. |
| F43 | **Runtime measured for the first time**: GMC 6.5 ms (MOT17) / 7.4 ms (KITTI); Depth-Anything-V2 Metric ViT-L **480.9 ms** — **70× a GMC call** — for a +0.855 HOTA gain over a global baseline that is itself worse than the GMC. |
| F44 | **The structural explanation was wrong.** Within-frame target depth ratio (monocular, contact point): MOT17 **5.60**, MOT20 **6.51**, UAVDT 3.94, KITTI **3.57**. The pedestrian benchmarks span *more* depth variation than KITTI, so depth uniformity is not what protects them — **absence of camera translation is**. Under rotation the induced motion is depth-independent however widely depths are spread. Cleaner and more falsifiable than the old framing, and it kills §5.6's factually wrong "nadir-ish, uniform depth" sentence. |
| F45 | `spread_2d.py` is reported as **a measurement that failed to discriminate**: observed object displacements are swamped by the objects' own motion, differently across datasets (MOT17 4.69 px, MOT20 5.56, UAVDT 2.50, KITTI 7.07). Recorded rather than dropped. |
| F46 | **Prior art verified from primary sources**: the 2026 survey quoted in §2.3 states in its own abstract that it evaluates camera motion compensation from a minimal baseline; **BoT-SORT itself** (2022) wrote that camera-motion estimation "may fail… Wrong camera motion may lead to unexpected tracker behavior", so §2.4's priority attribution to McByte++ is wrong; **EMAP** (arXiv:2404.03110, IROS 2024) decouples camera rotational/translational velocity using camera motion **and depth**, on **KITTI**, with **BoT-SORT** among four base trackers. |
| F47 | **§1's covariance argument does not compose**: `matching.fuse_motion` is commented out at `bot_sort.py:318`; the covariance never enters the association cost. Also "a similarity preserves the covariance's magnitude" is wrong — it scales by s². |

**In progress**: MOT20 oracle contrast (3/4 sequences, ref_ok=1.000, per-sequence median
disagreement 0.409 / 0.745 / 1.017 px) — closes the "MOT20 rests on internal consistency only"
objection by measurement. Parallax indicator across all four benchmarks — the dimensionless
translation diagnostic that replaces the withdrawn depth-uniformity explanation.

**Then**: manuscript rewrite (§1, §2 with ~25 added references, §5, §6, §7, abstract, claims),
Stage 3' re-review, Stage 4.5 final integrity (Mode 2).

## Stage 3' re-review + Stage 4 round 2 — PRESCRIPTION CHANGED (2026-09-24)

Two re-reviewers on the revised draft: one verification pass against the fourteen panel findings
plus a hunt for newly-introduced errors, one fresh adversarial read with no knowledge of the
earlier review. **The fresh reviewer recommended Reject**, on two Critical findings it established
by running the released code. Both were correct.

| F# | Finding |
|---|---|
| F48 | **CRITICAL, my bug.** `kitti_global_family_v2.py` gated warp generation on ground-truth annotation count (`len(prev) < 3: continue`) and left the initialised **identity** in place. The "deployable homography" configuration therefore applied **no compensation on 3,690 of 8,008 frames (46.1 %)**, including **2,399 of 6,717 moving frames (35.7 %)**, with four sequences identity throughout. §6.4's replacement conclusion was measured against that. |
| F49 | **The conclusion reverses once coverage is repaired.** Mask by the tracker's own **detections**, never fall back to identity (now 21/8008 = 0.3 %, first frames only): pedestrian HOTA 46.884→**47.158**, IDSW 115→**97**; contact-point application **47.233 / IDSW 85** — the fewest of any configuration in the paper. Car **66.482 / IDSW 125**. Depth-aware homography vs shipped GMC: **car +1.187 [+0.262, +1.922], excludes zero**. |
| F50 | **The prescription changes.** Per-target vs the depth-aware homography: car **−0.006 [−0.530, +0.446]**, ped **+0.424 [−0.032, +1.002]** — both cross zero. The +0.842 per-target enjoyed over the *depth-blind* global similarity is not evidence for per-object correction; it is evidence the shared warp was missing **depth**. Paper's prescription switched from "per-target compensation" to "give the shared warp depth"; per-target demoted to an oracle upper bound. **User approved.** |
| F51 | **The per-target arm reads ground truth at run time** — matches tracks against annotated boxes (IoU < 0.7); 40,557/69,000 track-warp applications (58.8 %) get a per-object warp, 41.2 % fall back to the global. §6.5's "differ in exactly one respect" was false. Now disclosed in §6.5 and §7.1. |
| F52 | **CRITICAL.** §5.3 claimed "every figure we quote for the oracle is the strict one from here on" — **false**; Tables 3/4/5 and the abstract used the hybrid. Strict moving-camera motion-only interval is **−0.037 [−0.201, +0.052]**, not +0.000 [−0.043, +0.052]; upper bound unchanged, lower bound 5× wider. All oracle figures and `bootstrap_ci.py` defaults now strict. |
| F53 | §6.4 misattributed its own self-correction: the 0.000-residual table is `kitti_model_class.csv` (fitted to the objects' own displacements), not the single-depth grid. **Two distinct earlier errors had been conflated into one**; §6.4 now separates them. |
| F54 | Further corrections: 81.8 % attached to the wrong denominator (now 81.65 % vs deployable similarity, 76.7 % vs the oracle similarity, both stated); 70× → **65×**; "four static sequences" → three (twice); §5.7 contradicted §4.2's new MOT20 oracle arm; comparator mislabelled "best global similarity"; Table 6 row 2 relabelled; §5.7's §2.3 pointer → §2.5; F1/F4 captions still stated withdrawn conclusions. |
| F55 | **`verify_numbers.py` now checks provenance, not only values** — warp-bundle identity coverage, which run feeds which table row, and that the MOT17 oracle rows come from the strict runs. Both Critical defects were provenance failures that a value-only checker passed. **505/505.** |

**Artefacts**: `02_paper/manuscript.md` (27 pp typeset, 13 tables, 8 figures, all cross-referenced),
`02_paper/supplementary.md`, `02_paper/latex/manuscript.pdf`, `03_code/rac/verify_numbers.py` (505 checks).

**Pending**: a placebo arm for §6.7 (same gate, shared warp) · Stage 4.5 final integrity (Mode 2) ·
Stage 5 finalize · Stage 6 process summary.

## Stage 4.5 — FINAL INTEGRITY (Mode 2) — PASS (2026-09-25)

Fresh full verification, no Stage 2.5 conclusion reused. Report: `02_paper/07_STAGE4.5_FINAL_INTEGRITY.md`.

| Phase | Result |
|---|---|
| A — all 36 references re-resolved from scratch | 36/36 (23 Crossref, 10 arXiv abs pages after the API returned HTTP 406, 3 legitimately DOI-less) |
| B — every quotation re-checked against source | 9/9 verbatim |
| C — statistical + **provenance** | **526/526**, provenance checks added (warp coverage, run→table mapping, strict-oracle sourcing) |
| D — originality | clear |
| E — claim strength vs intervals; prohibited claims | 7/7 pass; 0 of 6 prohibited claims present |
| Release manifest | 277 files, 0 problems |

| F# | Finding |
|---|---|
| F56 | **Placebo run.** Within-frame permutation of per-object corrections (same set, same magnitudes and directions, pairing destroyed): pedestrian **46.161 / IDSW 165**, car **62.612 / IDSW 395** — **worse than applying no per-object correction at all** (−3.58 HOTA on cars [+2.20, +4.96]; −25.6 weighted IDSW [−36.47, −10.12]). Rules out "the gain is perturbation magnitude"; the correction carries object depth. Written into §6.7 as Table 10. |
| F57 | §3.5's determinism wording was imprecise: `N1_run1` stores 7 files, `N1_run2–5` store 21 (they also wrote the unevaluated DPM/SDP copies). On the 7 evaluated FRCNN sequences all five runs are bit-identical, and identical to the file-GMC baseline. Corrected to "every evaluated sequence". |
| F58 | Lu et al. Mode 5 (an artefact reframed as an insight) **triggered three times across the project** — the 91.4 % homography, the single-depth grid, the identity-warp coverage defect. Each is recorded with what the earlier version reported. The countermeasure that worked was an adversarial reader with execution access, not a checklist; the provenance checks now in `verify_numbers.py` exist to catch the next instance mechanically. |

**Pending**: Stage 5 finalize (cover letter, submission package) · Stage 6 process summary.

## Stage 5 + Stage 6 — COMPLETE (2026-09-25)

**Pipeline finished.** `02_paper/08_COVER_LETTER.md`, `99_artifacts/SUBMISSION/` (11 items, 1.4 MB),
`00_pipeline/STAGE6_PROCESS_SUMMARY.md`.

| Artefact | State |
|---|---|
| Submission PDF | 28 pp, 14 tables, 8 figures, sha256 `ded8e84b…` |
| LaTeX source + class + figures | compiles standalone with `tectonic -X compile manuscript.tex` |
| Supplementary | S1 subset search · S2 errors and corrections · S3 refuted class explanations |
| Release | 277 files hashed, manifest verifies, `verify_numbers.py` 526/526 + 33 provenance checks |
| Chinese abstract | `02_paper/03_ABSTRACT_ZH.md`, synced to the final English text |

**Author action before upload** (in `99_artifacts/SUBMISSION/CHECKLIST.md`): author names /
affiliation / email / ORCID, funding statement, repository DOI (Zenodo — Springer requires a
resolvable identifier, not a bare URL), suggested reviewers, and confirm IJCV's single- vs
two-column preference.

**Final claim set**: the bound (−0.04 HOTA, 95 % upper bound +0.05 motion-only, +0.52 with
appearance); the two instruments; the KITTI quantification; depth as the missing warp argument
with a deployable global-homography remedy (car +1.19 [+0.26, +1.92] over the shipped compensator,
pedestrian identity switches 126 → 85); the placebo ruling out perturbation magnitude; and the
negative result that per-object correction adds nothing on top.

**Stage 6 process finding**: three conclusions in this project were artefacts of experiment
construction, and none was caught by a checklist — two were caught by a reviewer *executing* the
released code. `verify_numbers.py` passed 486/486 while the configuration it checked was switched
off on 35.7 % of moving frames. Provenance checks were added for that reason.

## Stage 6' — review of §6.8 and §7.3, the two sections nobody had reviewed (2026-09-27)

The previous round added two sections and committed them unreviewed. This round reviewed them the
way the rounds that worked were run: by executing the code and re-deriving every printed number,
not by reading. Six findings, all fixed.

| F# | Finding |
|---|---|
| F59 | **§6.8 was placed after `## 7 Deployability`, and this was not cosmetic.** `build_latex.py` strips the Markdown's manual numbers and lets LaTeX number subsections, so in the committed PDF §6.8 was typeset as 7.1 and every subsequent subsection shifted by one — §7.1→7.2, …, §7.5→7.6. Every one of the paper's 11 `§7.x` cross-references therefore pointed at the wrong subsection of the submitted artefact. Moved to the end of §6; verified against the regenerated `.tex` ordering. |
| F60 | **Two stale cross-references** left by the renumbering: §7.1 said "§7.3 evaluates that version" of the `per_target_depth` pipeline and §7.5 said "§7.3's pipeline runs a monocular depth network on every frame". Both are §7.4. Found by a script that checks every `§N.M` in the text against the heading list, not by reading. |
| F61 | **The paper prints two estimators for one quantity and never said so.** Result-table HOTA cells are TrackEval's `COMBINED` output; every interval's point estimate is the detection-weighted mean of per-sequence HOTA, because that is what the bootstrap resamples. So the abstract's +1.19 and Table 14's +1.217 are the same contrast, and §7.3's prose printed +1.371 where its own table said +1.378. Measured the disagreement over all ten KITTI contrasts: median 0.026 HOTA, max **0.198** (pedestrian contact-point row — large enough to halve that effect). Stated the convention in §3.5, replaced §7.3's two cherry-picked intervals with all six, and checked the claim "excludes zero at every level" at all six σ (it holds). |
| F62 | **§6.8 used the car per-frame counter that §6.7 had just declared unusable**, with no reconciliation. Measured the discriminator: on the per-target contrast the car counter disagrees with TrackEval in *sign* (−48 against +16), on the homography contrast it agrees in sign and to within 4 switches of 40 (+44 against +40). It is a property of the contrast, not the class. Written into §6.8 and both halves checked. |
| F63 | **"All of the improvement is in the top quartile"** overstated the car column: the net is +44 and Q4 carries +46, so Q4 more than accounts for it. Reworded to say that. |
| F64 | **`REPRODUCE.md` was stale across two renumberings** — it stopped at Table 10 while the paper prints 16, and its Table 6/7/8/9 rows named the commands for other tables entirely. Anyone following it would have run the wrong command for most of the paper. Rewritten against the actual 16 tables; four commands in it (two inherited) named flags no script accepts (`scan_mot.py --dataset`, `uavdt_track.py --scan`, `run_rac.py --dataset`, `analyse_oracle.py --by-sequence`) and one attributed §5.6 to MOT20 when §5.6 is UAVDT. |

**Verifier**: 541 → **690** checks, 0 problems. New coverage: every cell of Tables 12 and 14 parsed
from the manuscript and recomputed (HOTA, deltas, IDSW, the `exp(σ)−1` relative-error column, the
quartile medians and the permutation null); the six §7.3 intervals as fresh bootstraps plus the
zero-exclusion claim; §3.5's estimator-disagreement figures; §7.3's background-point counts
(median 437, IQR 379–522, against 5 objects) which had been "a few hundred"; and a provenance check
that every table in the manuscript appears in `REPRODUCE.md` and that no command there names a
script, flag or `--mode` value that does not exist. Each new check was **mutation-tested** — a
deliberate error injected into the manuscript and the check confirmed to catch it — because a new
check that passes first time is indistinguishable from one that is not running. A dead
`check_kitti_axis if False else` ternary was removed; it read as a suppressed check.

| F65 | **`REPRODUCE.md` was generated from a list inside `make_release.py`**, which is why F64 happened and why my first fix was silently overwritten the next time the release was built. It is now a maintained document at `02_paper/REPRODUCE.md` that `make_release.py` copies, with `check_reproduce_map` as the mechanical guard. While fixing it: `supplementary.md` and the reproduction page were **not in the release manifest at all** — 299 files became 301. |

**Rebuilt**: 31 pages, 16 tables, 8 figures, manifest 301 files, submission package re-synced,
Chinese abstract corrected (it still conflated the two homography configurations — +1.19 at box
centres with 85 identity switches at the contact point — the defect the English abstract had already
had fixed) and extended with the coarse-depth and localisation results.

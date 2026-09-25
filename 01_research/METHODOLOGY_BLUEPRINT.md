# Methodology Blueprint — Stage 1 Phase 1

**Project**: Multi-Object Tracking under Camera Motion Uncertainty
**Agent**: `research_architect_agent`
**Consumes**: `RQ_BRIEF.md`
**Status**: DRAFT — pending Devil's Advocate Checkpoint 1 + user confirmation

---

## 1. Paradigm and Method

| Dimension | Choice | Justification |
|---|---|---|
| Paradigm | Positivist / experimental computer science | Falsifiable mechanism hypothesis with pre-committed kill-switches (RQ Brief §6) |
| Method | Controlled ablation on public benchmarks + a purpose-built controlled robot study | Public benchmarks give comparability; the robot study gives *controlled* camera-motion ground truth that MOT17/MOT20 cannot provide |
| Data strategy | Secondary (MOT17, MOT20 + published detections) + primary (robot recording, user-collected) | Fixed detections isolate the association contribution |
| Analytical frame | Reliability-stratified comparison, not aggregate-only | Aggregate deltas cannot distinguish "the mechanism works" from "something else improved" |

---

## 2. Proposed Method — CMC-Reliability-Aware Association

Working name: **RAC-Track** (Reliability-Aware Compensation). Final naming deferred to Stage 2.

### 2.1 Reliability estimator

The GMC/RANSAC step already computes everything needed; nothing extra is detected or learned.
For frame `k`, from the keypoint correspondence set and the fitted affine `A_k = [M_k | t_k]`:

**Verified availability (code-level).** `tracker/gmc.py:223,284` calls
`cv2.estimateAffinePartial2D(prevPoints, currPoints, cv2.RANSAC)` and **discards the returned inlier mask**.
Inlier ratio, count, residuals and spatial positions are therefore obtainable at zero additional cost —
the signal already exists and is thrown away.

| Signal | Definition | Failure it detects |
|---|---|---|
| `ρ` | RANSAC inlier ratio | Degenerate / contaminated correspondence set |
| `n` | absolute inlier count, mapped through `min(1, n/n₀)` | Ill-conditioned fit from too few points |
| `ε` | median symmetric transfer residual of inliers (px), mapped `exp(−ε/ε₀)` | Fit that "succeeds" but is imprecise |
| `κ` | **solver-specific** plausibility (see below) | Scale/rotation explosions — the class McByte++ guards against |
| `τ` | temporal consistency: agreement of `A_k` with a constant-velocity forward prediction from `A_{k−1}, A_{k−2}` | Sporadic single-frame failures (TRGMC's documented mode) |
| `φ` | `1 −` fraction of inliers falling inside detection boxes — **conditional, see below** | Foreground-dominated estimate (the MOT20 regime) |

**`κ` is defined per solver DOF (DA-CP1 M1).** `estimateAffinePartial2D` fits a **4-DOF similarity**
(rotation + uniform scale + translation), for which the singular values of `M` are identically equal — any
`σ₁/σ₂` term is vacuous. Therefore:

| Solver | `κ` definition |
|---|---|
| `sparseOptFlow` / `orb` / `sift` (partial affine, 4-DOF) | `exp(−(\|log s\| / s₀ + \|θ\| / θ₀))`, `s` = fitted scale, `θ` = fitted rotation, both against a temporal prior |
| full affine (6-DOF) or homography (8-DOF), if evaluated | additionally `\|σ₁/σ₂ − 1\|` and, for homography, the perspective-row magnitude |

The solver used must be stated wherever `κ` is reported; the definitions are not interchangeable.

**`φ` is conditional on demonstrated variance (DA-CP1 M2).** BoT-SORT already masks detection regions out of
the keypoint set, so residual contamination may be near-constant, and `φ` is computed from detections that
are themselves downstream of the association being modified — a mild circularity. **Decision rule:** run A1
first; if `φ` has negligible empirical variance across MOT17/MOT20 frames, **drop it** rather than retain a
decorative term. The retained signal set is reported, not assumed.

**Combination rule — derived, not asserted (DA-CP1 M3).** Treat each normalised signal `x_j ∈ (0,1]` as a
likelihood ratio for the event *"this estimate is valid"* under conditional independence given the frame.
Then the posterior odds are the product `∏_j x_j`, and

```
r_k = ( ∏_{j∈S} x_j )^{1/|S|}
```

is the geometric mean — i.e. the product rescaled so `r` stays on the same scale as its constituents and is
invariant to how many signals are retained. Conditional independence is an *approximation*, stated as such
in the paper; the empirical check is ablation A9 (signal-drop), which must show each retained signal changes
the outcome. Any signal that does not is removed. The semantics are deliberately conservative: one collapsing
signal drags `r` down.

**Per-target reliability** (the requirement that a bad estimate must not be applied uniformly):

```
r_k^(i) = r_k · s_k^(i)
s_k^(i) = local inlier support in a dilated neighbourhood of track i's predicted box,
          normalised and clipped to [s_min, 1]
```

A track surrounded by well-registered background inherits high reliability; a track embedded in a crowd
with no background support does not. This is the component with no counterpart in prior art.

### 2.2 Propagation into tracking — three coupled uses

**(P1) Transform shrinkage toward identity.** Rather than applying `A_k` or skipping it (McByte++'s binary
choice), interpolate: apply `A_k^eff(i) = Interp(I, A_k; r_k^(i))`, interpolating the linear part via the
matrix logarithm and the translation linearly. `r=1` → full compensation; `r=0` → no compensation;
intermediate `r` → partial, per-target.

**(P2) Uncertainty inflation.** Add compensation uncertainty to the Kalman covariance instead of pretending
the warp was exact:
`P_k ← P_k + (1 − r_k^(i))² · Σ_cmc(i)`, with `Σ_cmc(i)` scaled by the applied displacement magnitude.

**(P3) Reliability-conditioned association** — the core fix for the coupling defect (RQ Brief §1.1b):

```
θiou(r) = θiou_base + (1 − r) · (θiou_max − θiou_base)        # relax the gate when unreliable

d̂cos_ij = 0.5 · dcos_ij   if (dcos_ij < θemb) ∧ (diou_ij < θiou(r_i))
        = 1                otherwise

C_ij     = min{ diou_ij + β·(1 − r_i) ,  d̂cos_ij }            # distrust motion when unreliable
```

**Design invariant (K3, binding).** At `r ≡ 1`: `θiou(1) = θiou_base`, `β·(1−1) = 0`,
`Interp(I,A;1) = A`, and the covariance inflation vanishes — the method reduces **exactly** to BoT-SORT.
Any measured gain at `r ≡ 1` would indicate an implementation error or hidden re-tuning, not a contribution.

### 2.3 What is deliberately NOT done

- No new detector, no detector fine-tuning.
- No new ReID backbone — reuse BoT-SORT's FastReID SBS-S50 weights unchanged.
- No learned reliability head in the main method (a learned variant is a stretch ablation only; a hand-specified
  formula is auditable and cannot leak test information).

---

## 3. Experimental Protocol

### 3.0 Causal identification strategy (DA-CP1 C1 — **binding**)

A correlation between low reliability and ID switches is **not** evidence that compensation error causes ID
switches. Frames with fast motion, blur, low texture or crowding degrade keypoint matching *and* detection
quality *and* appearance embeddings simultaneously. The correlation is therefore fully expected even if
compensation error causes zero ID switches. SQ1/SQ2 are accordingly built on an interventional contrast:

**I1 — Oracle-warp contrast (primary).** For each frame, run the association twice: once under the online
estimate `A_k`, once under a **reference warp** `A*_k`. ID switches present under `A_k` but absent under
`A*_k` are *attributable to compensation error*. This — not the correlation — is the quantity SQ1 reports.

| Dataset | Reference warp `A*_k` |
|---|---|
| Robot study | Odometry-derived ground-truth camera motion (the reason the robot study exists) |
| MOT17 / MOT20 | Offline batch-estimated alignment: non-causal, multi-frame, dense/global. Permissible **only** as an analysis instrument; it never enters the tracker and is never part of any reported method. |

**I2 — Confound conditioning.** IDSW enrichment in low-`r` frames is reported *stratified by* mean detection
score, detection count, and appearance-embedding separability. If enrichment disappears after conditioning,
that is the reported finding.

**I3 — Placebo reliability.** Recompute `r` from a shuffled correspondence set. Enrichment that persists
under placebo `r` is confound, not mechanism. Reported either way.

Failing to pre-commit I1–I3 would make a positive SQ1 result indistinguishable from a Lu et al. (2026)
Mode 5 failure (artefact reframed as insight).

### 3.0.1 Power gate — run **before** the ablation matrix (DA-CP1 C2 — **binding kill-switch**)

BoT-SORT attributes ≈1.0–1.5 HOTA on MOT17 to *having CMC at all*. This project does not add compensation;
it repairs it on the minority of frames where it fails. If failures are ~2–5% of frames, total addressable
headroom may be ≈0.02–0.08 HOTA — inside run-to-run variance. That must be established before spending
compute on a full ablation.

| Step | Procedure | Output |
|---|---|---|
| **N1 — noise floor** | Run A0 unmodified ≥5× under every nondeterminism source present; explicitly document which stages are deterministic (if the pipeline is fully deterministic under fixed detections, state that and substitute hyperparameter-perturbation variance instead) | σ(HOTA), σ(IDF1), σ(IDSW) = minimum detectable effect |
| **N2 — headroom ceiling** | Metric delta from I1 if *every* compensation error were perfectly repaired | Upper bound on any achievable gain |

**Gate.** If `N2 < 3 × N1`, MOT17/MOT20 aggregate metrics cannot carry the paper. The project then either
(a) makes the robot study and reliability-stratified sub-population results the primary evidence, or
(b) adds a benchmark with severe camera motion (DanceTrack / VisDrone / UAVDT / KITTI).
**This decision is made before the full ablation runs — not after seeing disappointing numbers.**

### 3.1 Fixed-detection discipline (user-mandated)

Every compared configuration consumes **byte-identical detection files**. The detection source is recorded
by SHA-256 in the results manifest. Any result produced with differing detections is reported separately
and never mixed into an ablation table.

### 3.2 Splits and evaluation

| Protocol | Use | Note |
|---|---|---|
| MOT17 half-val (first half train / second half val, per BoT-SORT §4.1) | Primary development + ablation | The benchmark's own ablation protocol |
| MOT20 half-val, same construction | Crowd / predominant-foreground regime | Tests the `φ` signal directly |
| Cross-sequence split (per arXiv:2609.08265) | Generalisation check | Avoids temporal leakage between halves |
| MOT17/MOT20 **test** | ❌ **NOT AVAILABLE TO ANYONE** | The MOTChallenge evaluation server, submissions and user accounts are offline (TUM notice, 2026-09-08). This is a field-wide condition, not a limitation of this work, and is stated as such in the Evaluation Protocol subsection. |
| MOTChallenge static leaderboard archive (state 2026-04-16) | Comparison against published per-sequence results and raw result files, without submission | Preserved by TUM; exact filenames required (directory not browsable) |

**Metrics**: HOTA, AssA, DetA, IDF1, MOTA, **IDSW** (primary for the RQ), FP, FN, Frag, plus:
- *Occlusion recovery rate* — fraction of tracks correctly re-identified after an occlusion gap of ≥ N frames.
- *Reliability-stratified breakdown* — all metrics reported per `r` quartile (the K4 test).

Evaluation via **TrackEval** (the official implementation), not a re-implementation.

### 3.3 Ablation matrix

| ID | Configuration | Isolates |
|---|---|---|
| A0 | BoT-SORT, unmodified | Baseline |
| A1 | + reliability estimator, logged only (no effect on tracking) | SQ1 measurement; zero-delta sanity check |
| A2 | A0 + P1 (shrinkage) only | Value of partial compensation |
| A3 | A0 + P2 (covariance inflation) only | Value of honest uncertainty |
| A4 | A0 + P3 (association) only | Value of fixing the coupling defect |
| A5 | Full method (P1+P2+P3), global `r` only | Cost of dropping spatial reliability |
| A6 | Full method, per-target `r` | Complete proposal |
| A7 | A6 with `r ≡ 1` | **K3 invariant — must equal A0 exactly** |
| A8 | McByte++-style binary guard re-implemented on BoT-SORT | Head-to-head vs. the closest prior art |
| A9 | Signal-drop ablations (remove `ρ`, `ε`, `κ`, `τ`, `φ` one at a time) | Which reliability signals actually earn their place (DA-CP1 M3) |
| **A10** | **Constant-`θiou` control**: relax `θiou` by a fixed amount equal to the mean of `θiou(r)`, with no reliability signal | **Does `r` contribute anything beyond "relax the gate everywhere"?** (DA-CP1 §5) |
| **A11** | Covariance inflation with constant `r` | Rules out "inflation is generic regularisation" |

A8 is required: without it, reviewers will ask whether a simple binary switch captures the whole gain.
**A10 is the single cheapest and most obvious reviewer question** — if constant gate relaxation reproduces the
gain, the reliability estimator is decorative and the paper has no contribution. It is run early, not last.

**Cross-dataset caveat (DA-CP1 m1).** `bot_sort.py:306–307` applies `fuse_score` only when `not args.mot20`,
so the MOT17 and MOT20 association paths are **not the same algorithm**. Every cross-dataset statement must
either account for this or be restricted to within-dataset comparison.

### 3.4 Robot-recorded controlled study (user-executed)

Purpose: MOT17/MOT20 provide no ground-truth camera motion, so CMC reliability cannot be validated
directly — only its downstream effect can. A controlled recording closes that loop.

Design requirements delivered to the user as a separate protocol document (Stage 1 Phase 2):
- Camera motion conditions crossed with target conditions (stationary / pan / rotate / vibrate / rapid turn
  × crossing / occlusion / free).
- **Ground-truth camera motion** from robot odometry, time-synchronised with frames — this is the element
  that makes the study "controlled", is what no public benchmark offers, and supplies the reference warp
  `A*_k` for the I1 oracle contrast.
- **Synchronisation accuracy must be measured and reported** (DA-CP1 m3). An unstated camera–odometry time
  offset silently destroys the "controlled" claim. Protocol: hardware trigger or a measured offset via a
  visual-inertial alignment event, with residual jitter reported in milliseconds.
- Adversarial backgrounds: low-texture wall, repetitive pattern, predominant-foreground crowd — the three
  regimes the literature names as GMC failure causes.
- MOT-format annotation spec, consent protocol, and evaluation scripts supplied by the pipeline.

### 3.5 Statistical reporting

- Where stochasticity exists, report mean ± std over ≥3 seeds; state where the pipeline is deterministic.
- Report per-sequence results, not only dataset aggregates — aggregates hide where the method helps.
- **Pre-commit the ablation table before running it**; do not add configurations post hoc to rescue a result.
- Negative results (e.g. no MOT20 effect) are reported, not dropped.

---

## 4. Validity and Reliability

| Threat | Control |
|---|---|
| Detector improvement mistaken for tracking improvement | Byte-identical detections, SHA-256 recorded (§3.1) |
| Hyperparameter re-tuning mistaken for mechanism | K3 invariant (A7) + shared hyperparameters with A0 |
| Cherry-picked sequences | All sequences reported; aggregates plus per-sequence tables |
| Overfitting to the val half | Cross-sequence split as an independent check |
| Reliability formula tuned on the evaluation data | Constants (`n₀, ε₀, s_min, β, θiou_max`) fixed on MOT17 **train** half only; frozen before val/robot evaluation and recorded |
| Implementation bug producing plausible numbers (Lu 2026 Mode 1) | A1 zero-delta check; A7 exact-equality check; all runs log exit codes and are retained |

---

## 5. Target Venue Analysis (preliminary — to be verified in Phase 2)

Signals gathered so far, to be confirmed against current JCR/CAS data before any submission decision:

| Candidate | Signal observed | OA status seen |
|---|---|---|
| Pattern Recognition (Elsevier) | Hosts closely-related work (arXiv:2403.08018 "Preprint submitted to Pattern Recognition") | hybrid |
| Expert Systems with Applications (Elsevier) | Hosts IMM-JHSE + arXiv:2504.20234, both directly adjacent | hybrid |
| IEEE TCSVT | Classic venue for association/fusion work | hybrid |
| Complex & Intelligent Systems (Springer) | Fully OA | gold |
| Scientific Reports / Applied Sciences / Sensors / Electronics (MDPI) | DCTrack appeared in Electronics; several MOT papers seen | gold |
| CAAI Trans. Intelligence Technology | Fully OA | gold |

**Deferred decision.** Quartiles and APCs are not asserted here — they will be verified from primary
sources in Phase 2 and presented with evidence, per the user's Stage-1-decides choice.

**DA-CP1 M4 — status: DOWNGRADED from submission-blocking to a disclosure requirement.**

The original concern assumed the test server was reachable by others and not by us. That was wrong: the
earlier failures were caused by the local SOCKS proxy. Direct access shows the **MOTChallenge benchmark
service is globally offline** — verbatim from the TUM notice:

> "This service is currently offline. The MOTChallenge benchmark website is not in operation. The evaluation
> server, submissions and user accounts are offline. The dataset archives remain available at their existing
> addresses… The leaderboards have been preserved as a static archive. All published results (state of
> 16 April 2026) with method pages, per-sequence results, result videos, raw result files and a CSV export
> per benchmark."

Therefore: (a) **no contemporary paper can report new MOT17/MOT20 test-server numbers** — the half-val
protocol is the field-wide norm for any work submitted after 2026-09; (b) comparison against prior published
methods is still possible via the static archive's per-sequence results and raw result files; (c) the
manuscript must state the service status explicitly with the access date, rather than silently omitting test
results. Venue selection is no longer constrained by this, but the Evaluation Protocol subsection must
disclose it.

---

## 6. Execution Plan (Stage 1 → Stage 2 handoff)

| Step | Output | Blocking? |
|---|---|---|
| S1 | Acquire MOT17/MOT20 + published detections; verify checksums | **YES** — K1 cannot run without data |
| S2 | Reproduce BoT-SORT baseline (A0) and match published half-val numbers within tolerance | **YES** — an unreproduced baseline invalidates every delta |
| S3 | Implement + log reliability estimator (A1); run I1/I2/I3 causal battery (§3.0) → K1, K2 | **YES** — kill-switch |
| **S3.5** | **N1 noise floor + N2 headroom ceiling; apply the power gate (§3.0.1)** | **YES** — decides whether the ablation is worth running at all |
| S4 | Implement P1/P2/P3; run ablation matrix, **A10 first** | No |
| S5 | Robot protocol document → user | No (parallel) |
| S6 | Venue verification with evidence | No (parallel) |

**S2 is the true gate.** If the published BoT-SORT half-val numbers cannot be reproduced under fixed
detections, every subsequent comparison is meaningless and this is reported rather than worked around.

---

*Deliverable of Stage 1 Phase 1. Next: Devil's Advocate Checkpoint 1.*

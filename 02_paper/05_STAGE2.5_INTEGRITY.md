# Stage 2.5 — Academic Integrity Verification Report

## Verification Mode
Initial Verification (Mode 1, pre-review)

## Verdict
**PASS** — after five corrections, all applied and re-verified.

**Draft binding**: `02_paper/manuscript.md` as of 2026-09-23 · **Automated check**: `03_code/rac/verify_numbers.py`

---

## Verification Summary

| Category | Total | Passed | Issues |
|---|---|---|---|
| Reference existence (Phase A) | 17 | 17 | 0 |
| Bibliographic accuracy (Phase A) | 17 | 17 | 0 (4 fixed at Phase 5a) |
| Ghost citations | — | — | 0 orphan / 0 dangling |
| Citation context accuracy (Phase B, 5 of 5 quoted sources = 100 %) | 5 | 5 | 0 |
| **Statistical/data accuracy (Phase C)** | **380** | **380** | **2 fixed** |
| Internal consistency (Phase C) | — | Pass | **1 fixed** |
| Figure/table caption fidelity (Phase C3) | 18 | 18 | 0 |
| Experiment provenance (Phase C4) | 50 runs | 50 | 0 |
| Originality (Phase D1) | 100 % of paragraphs | — | 0 |
| Claim verification (Phase E) | all quantitative claims | — | **2 fixed** |

---

## Phase A — Reference verification

Executed at Phase 5a and re-checked here. All 17 entries resolved live: 11 against the arXiv
API, 6 against Crossref DOI resolution. Four defects were found and corrected there, two of
them **fabricated DOIs that resolved to unrelated papers**; see
`02_paper/02_PHASE5A_CITATION_AUDIT.md`. Zero entries remain in a "plausible but unconfirmed"
state, and no entry entered Phase B without an explicit Phase A verdict.

## Phase B — Citation context

Every verbatim quotation in the paper (5) was re-read against its source, not summarised from
memory. The McByte++ §3.5 quotation was checked against the retrieved HTML
(`01_research/mcbyte.html`), the MOTChallenge notice against a fresh HTTP fetch returning 410
Gone. All 5 match verbatim. No quotation is used to support a claim its source does not make:
in particular McByte++ is credited with prior identification of the problem (§1.2, §2.4), not
denied it.

## Phase C — Statistical and data accuracy

This is the phase that mattered, and it was automated rather than sampled.
`verify_numbers.py` parses the manuscript's quantitative claims, recomputes each from the
released CSVs and TrackEval output directories, and fails on any mismatch beyond printing
precision. **380 of 380 values now match.** Three items remain outside its scope and are
listed by `--list`: the instrumented-GMC bit-identity assertion (self-asserted by
`instrumented_gmc.py`), the confound and placebo figures (printed by `confound_placebo.py`,
re-run 2026-09-23), and the determinism claims (verified by diffing run outputs).

### C-1 (fixed) — an unstated denominator

§6.2 read "the per-frame Spearman correlation between depth and residual … is negative in
75.3 % of frames." The Spearman needs at least four objects, so 939 of the 4,318 moving frames
have no value; 75.3 % is the fraction over the 3,379 frames where it is defined, and over all
moving frames it is 58.9 %. The claim was true and the denominator was missing. Both figures
are now stated.

### C-2 (fixed) — a prose figure that did not reproduce

§3.2 claimed the reference warp's "median forward-backward corner error is 0.007–0.013 px".
Recomputed from `oracle_analysis.csv`: the pooled median is **0.002 px** and the per-sequence
medians span **0.0002–0.012 px**. The original range does not correspond to any statistic in
the file. Corrected to the measured values, and the check added to the verifier.

### C-3 (fixed) — **two estimators in adjacent sentences**

Every confidence interval in the paper uses a GT-detection-weighted aggregate over sequences.
The leave-one-sequence-out figures quoted in §6.6 and §8 came from an earlier analysis that
used the **unweighted mean of per-sequence deltas**. Under that estimator the car gain flipped
sign when sequence 0004 was dropped; under the paper's own estimator it does not:

| | full | leave-one-out range | sign changes |
|---|---|---|---|
| pedestrian | +0.842 | [+0.332, +1.025] | 0 |
| car | +0.213 | [+0.096, +0.393] | 0 |

The claim "the car gain flips sign under leave-one-sequence-out" is **withdrawn**: it was an
artefact of mixing estimators. The car result remains *not established* on its primary grounds
— every bootstrap interval crosses zero, it turns negative at 5 % depth noise, and §6.7 cannot
give it a verified mechanism — and §6.6 now says explicitly that leave-one-out is not what
separates the classes. `bootstrap_ci.py --loo` computes it under the paper's own weighting.

### C-4 (fixed) — a dangling comparison

§7.2 compared a 0.29 HOTA difference against "the standard deviation we measure across
hyperparameter perturbations", a quantity the paper reports nowhere (it belongs to a framing
withdrawn in §9.3). Replaced with a comparison against an interval the paper does report.

### C-5 (fixed) — two numbers that looked like a transcription error

Table 10 gives the car HOTA as 66.473 with estimated and with ground-truth depth. Verified
from per-sequence output as 66.47275 and 66.47348; a sentence now says so.

## Phase C3 — Figure and table caption fidelity

All 10 numbered tables and all 8 figures were checked against the data that produced them.
Every figure is generated by `make_figures.py` directly from the released CSVs and TrackEval
output — no figure is drawn from transcribed numbers. One figure defect was found during
generation and fixed before use (F6 was pooling both classes because the column is named
`cls`, not `class`); its published form reproduces Table 8 exactly.

## Phase C4 — Experiment provenance

| Check | Result |
|---|---|
| Detections frozen and hashed before any comparison | 62,398 MOT17 detections, 7 sequences, SHA-256 per file; KITTI frozen likewise |
| Every compared configuration reads the same detection files | yes, by construction |
| Detector checkpoint hashed | `26cb8d28…c48b1a` recorded in the manifest |
| Determinism verified, not assumed | MOT17 motion-only ×5, MOT17 appearance ×2, KITTI ×2 — all bit-identical |
| Plausibility guard applied identically to all configurations | yes (§6.5) |
| A failed gate re-run until it passed | **no** — the K5 power gate failed once and was never re-run; the MOT17 ablation matrix it would have authorised was not executed |

## Phase D — Originality

The manuscript is original prose. Five passages are deliberate verbatim quotation, each
marked as such with attribution (§2.1, §2.2 ×2, §2.3, §9.1). Two short source-code excerpts
appear in §1 as fenced blocks with their file attributed. No paragraph paraphrases a source
closely enough to require quotation and lack it. No self-plagiarism: this is the project's
first manuscript.

## Phase E — Claim verification

Every quantitative claim in the body traces to a released artefact; the automated check above
is the mechanism, and it covers claims rather than only tables because the script checks prose
figures (§5.1 quantiles, §6.2 spreads, §6.3 gate rates, §7.2 car deltas, §8 refutations) as
well as table cells. Two claim-level defects were found and are C-2 and C-3 above. No claim
was found that cites a source not supporting it.

Two further checks specific to this paper:

**The Part 7 prohibited-claim list** (7 items, fixed before drafting) was re-checked item by
item against the final text. None appears. The two that were closest to the line — "per-target
beats a global homography on HOTA" and "the deployable pipeline beats plain GMC on
pedestrians" — are both stated in the manuscript as *not* established, with their intervals.

**Negative-claim discipline.** The headline claim is a null. Phase 6 found that it rested on
point estimates while the positive claims carried intervals; §5.5 and Table 5 now give the
null a bounded upper end (+0.49 HOTA motion-only, +0.13 with appearance). A null without an
upper bound is an assertion, not a measurement.

---

## Seven-mode AI-research-failure checklist (Lu et al., 2026)

| Mode | Check | Result |
|---|---|---|
| 1 — Implementation bug producing plausible numbers | K3 invariant asserted numerically (`max_interp_diff = 0.0`, `max_apply_diff = 0.0`); instrumented GMC bit-identical to the original; per-frame IDSW counter validated against TrackEval (20 = 20) | **clear** |
| 2 — Data leakage | KITTI detector is COCO-pretrained and has never seen KITTI, so no split was needed and none was invented; MOT17 uses the published ablation weights trained on the first half and evaluated on the second | **clear** |
| 3 — Fabricated or unmeasured numbers | 380 values recomputed from source; 2 defects found and fixed | **clear after correction** |
| 4 — Overclaiming beyond evidence | 4 claims explicitly withheld in the text; 3 withdrawn during the work and recorded in §9.3; a fourth (leave-one-out sign flip) withdrawn here | **clear after correction** |
| 5 — An artefact reframed as an insight | the 91.4 % homography figure was exactly this and was caught and reversed (§6.4, §9.3); the six-signal estimator's synthetic win is reported alongside its real-data loss rather than dropped (§4.4) | **clear** |
| 6 — Selective reporting | both refuted class-split explanations reported (§8); the non-monotone compensation axis reported including the oracle scoring below the published configuration; the MOT17 "having compensation" interval crossing zero reported (§5.5) although it weakens the presentation | **clear** |
| 7 — Irreproducibility | 31 scripts, 15 CSVs, 50 hashed tracker runs, a figure script and a LaTeX build script, all released; every table regenerable by one command | **clear** |

---

## Verdict

**PASS.** Zero SERIOUS, zero MEDIUM, zero MAJOR_DISTORTION, zero UNVERIFIABLE remaining.
Five defects were found (C-1 … C-5), all corrected and re-verified; the correction that
matters is C-3, because mixing two estimators produced a robustness claim that the paper's
own method does not support.

Release to Stage 3 (five-seat review panel).

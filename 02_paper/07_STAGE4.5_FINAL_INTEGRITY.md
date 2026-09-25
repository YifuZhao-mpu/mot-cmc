# Stage 4.5 — Final Integrity Verification (Mode 2)

## Verification Mode
Final Verification (Mode 2, post-revision). Executed fresh: no Stage 2.5 conclusion was reused,
and every reference was re-resolved from scratch as if the earlier check were unavailable.

## Verdict
**PASS** — one wording imprecision corrected during the check; zero unresolved items.

**Draft binding**: `02_paper/manuscript.md` + `02_paper/supplementary.md`, 2026-09-25
**Automated surface**: `03_code/rac/verify_numbers.py` — **526 values, 526 matched, 0 problems**

---

## Verification summary

| Category | Total | Passed | Issues |
|---|---|---|---|
| Reference existence and bibliographic accuracy (Phase A, fresh) | 36 | 36 | 0 |
| Ghost citations | — | — | 0 orphan / 0 dangling |
| Citation context — every quotation (Phase B, 100 %) | 9 | 9 | 0 |
| Statistical/data accuracy (Phase C, automated) | 526 | 526 | 0 |
| **Provenance** — which run feeds which table, warp coverage | 33 | 33 | 0 |
| Internal consistency — §-references, table/figure numbering | — | Pass | 0 dangling |
| Withdrawn figures still present in text | 10 patterns | — | 0 (2 hits are the deliberate disclosure table) |
| Claim strength against intervals (Phase E) | 7 | 7 | 0 |
| Prohibited claims (re-derived for the revised paper) | 6 | — | 0 present |
| Determinism replicates | 3 | 3 | **1 wording imprecision, corrected** |
| Release manifest | 277 files | 277 | 0 |

---

## Phase A — References, fresh full verification

All 36 entries re-resolved. Twenty-three against Crossref DOIs, ten against arXiv (the API began
returning HTTP 406 partway through, so those ten were verified against their abstract pages
instead — an independent route to the same record), and three that legitimately carry no DOI:
Bouguet's 2001 Intel technical report, Lucas & Kanade's IJCAI-81 paper (no DOI exists; one must
not be invented), and TrackEval as software.

No entry resolved to a different work than claimed. The two fabricated DOIs found at Stage 2.5 —
Claasen & de Villiers listed under an *Information Fusion* DOI belonging to an unrelated paper,
and Safdarnejad under a BMVC 2016 DOI belonging to a face-alignment paper — remain corrected and
re-verified here from scratch.

## Phase B — Citation context, 100 %

Every quotation in the manuscript was re-checked character-for-character against its source, not
against notes:

| Quotation | Source checked | Result |
|---|---|---|
| BoT-SORT limitations ("the estimation of the camera motion may fail…") | arXiv LaTeX source, §Limitations | verbatim |
| BoT-SORT motivation ("predicting the correct location… may fail due to camera motion") | same source | verbatim |
| Deep OC-SORT ("CMC improves performance on MOT17-val… no improvements on MOT20-val") | arXiv LaTeX source, `main.tex:386` | verbatim |
| UCMCTrack ("the inaccuracies present in the CMC parameters") | arXiv LaTeX source, §KITTI | verbatim |
| McByte++ §3.5 (conditional CMC) | retrieved source HTML | verbatim |
| MOTChallenge shutdown notice | live fetch, HTTP 410 | verbatim |
| Survey critique, both clauses | live arXiv abstract | verbatim |
| Survey evaluates CMC from a minimal baseline | live arXiv abstract | confirmed |

No quotation is used to support a claim its source does not make. Where a source has priority over
us — BoT-SORT on the failure mode, Deep OC-SORT on MOT20, EMAP on depth-based correction — the
text concedes it (§1.2, §2.2, §2.4, §2.6).

## Phase C — Statistical, data and provenance accuracy

`verify_numbers.py` recomputes **526** quantities from the released CSVs and the 200 TrackEval
outputs and fails on any mismatch. All 526 match. Three items are declared out of scope and were
checked by hand: the instrumented-GMC bit-identity assertion (self-asserted by the instrument),
the confound and placebo figures (printed by `confound_placebo.py`), and the determinism
replicates (below).

**The verifier now checks provenance, not only values.** Both Critical defects found in review were
provenance failures that a value-only checker passes: a warp bundle that was the identity on 46 %
of frames, and a table sourced from a different experiment than the text described. The added
checks are warp-bundle identity coverage (must not exceed one frame per sequence), the existence
and sequence count of every run named in a table, and that the MOT17 oracle rows come from the
strict runs rather than the superseded hybrid ones.

### Item corrected during this check

§3.5 read "five independent runs … produced bit-identical output on **every sequence**". Diffing
the stored runs, `N1_run1` holds 7 files and `N1_run2`–`N1_run5` hold 21: the later runs also wrote
the DPM and SDP copies, which the validation-half protocol does not evaluate. On the seven FRCNN
sequences that are evaluated, all five runs are bit-identical, and all five are bit-identical to
the file-GMC baseline. The claim is true; the wording was not precise about which sequences.
Corrected to "every evaluated sequence".

### Internal consistency

Fifty section headings, thirty-four `§` cross-references, zero dangling. Three supplementary
sections, all referenced, none dangling. Fourteen tables and eight figures, numbered without gaps
or duplicates, every one cited in the text. A scan for ten withdrawn or superseded figures returned
two hits, both inside the §5.3 table that deliberately contrasts the hybrid oracle with the strict
one.

## Phase D — Originality

Original prose throughout. Nine passages are deliberate verbatim quotation, each marked and
attributed; two short source-code excerpts appear in §1 with their file named. No paragraph
paraphrases a source closely enough to require quotation and lack it. No self-plagiarism: first
manuscript from this project.

## Phase E — Claims

Every quantitative claim traces to a released artefact, and the automated surface covers prose
figures as well as table cells. Seven claim-strength checks pass: each comparison whose interval
excludes zero is claimed, each that crosses zero is stated as not established, the ground-truth
channel in the per-target arm is disclosed, and the priority concessions are present.

Six prohibited claims were re-derived for the revised paper and none appears:

| # | Prohibited | Status |
|---|---|---|
| 1 | That per-target compensation is the remedy | clear — §6.6 reports it adds nothing over the depth-aware homography |
| 2 | That the depth-aware homography beats the shipped GMC on pedestrians | clear — stated as crossing zero |
| 3 | That we discovered compensation can fail | clear — BoT-SORT credited |
| 4 | That the shared-warp limitation is *measured* outside KITTI | clear — §9.2 reports two diagnostics that failed to discriminate |
| 5 | Any MOTChallenge test-set number | clear |
| 6 | That per-object correction is unnecessary in general | clear — scoped to this benchmark and this comparison |

---

## Seven-mode AI-research-failure checklist (Lu et al., 2026)

| Mode | Result |
|---|---|
| 1 — Implementation bug producing plausible numbers | **Triggered twice and caught, both by review of released code**: a warp bundle silently the identity on 35.7 % of moving frames, and an oracle configuration silently reverting to the online estimate on 18.2 % of the hardest sequence's frames. Both re-measured; one reversed a conclusion. The verifier now carries coverage checks so the class is caught mechanically. |
| 2 — Data leakage | clear. KITTI's detector is COCO-pretrained and never saw KITTI; MOT17 uses the published ablation weights trained on the first half and evaluated on the second. §9.3 states that everything *other* than the detector was chosen with results visible. |
| 3 — Fabricated or unmeasured numbers | clear after correction. 526 values recomputed; two fabricated DOIs caught at Stage 2.5 and re-verified here. |
| 4 — Overclaiming beyond evidence | clear after correction. Six claims withdrawn across the project, four of them our own replacements for earlier withdrawn claims; all recorded in §9.4 and Supplementary S2. |
| 5 — An artefact reframed as an insight | **the central risk in this work, triggered three times.** The 91.4 % homography figure, the single-depth grid, and the identity-warp coverage defect each produced a conclusion that was an artefact of construction. All three are recorded with what each earlier version reported. |
| 6 — Selective reporting | clear. Two diagnostics that failed to discriminate are reported (§9.2); the placebo that is worse than no treatment is reported; the static stratum that is significant in the direction against us is reported; the car/pedestrian split that does not favour a single application rule is reported. |
| 7 — Irreproducibility | clear. 277 files hashed, manifest verifies, one command recomputes the paper's numbers and fails on mismatch. |

---

## Verdict

**PASS.** Zero SERIOUS, zero MEDIUM, zero MAJOR_DISTORTION, zero UNVERIFIABLE. One wording
imprecision found and corrected. Release to Stage 5.

The honest summary of this gate is that it did not find the paper's serious defects — review of
the released code did, twice, and both times the defect was that a treatment had been silently
switched off rather than that a number was wrong. Mode 5 is the one this project keeps triggering,
and the countermeasure that worked was not a checklist but an adversarial reader with execution
access. The provenance checks added here exist so that the next instance is caught by the script.

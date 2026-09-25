# Phase 4 — Draft record and self-scoring

**Date**: 2026-09-23 · **Artefact**: `02_paper/manuscript.md` (11,382 words) · **Figures**: `05_figures/F1–F8`

---

## Acceptance criteria, pre-committed before drafting (Phase 4a)

1. Every number traceable to a CSV in `04_experiments/` or a TrackEval output directory.
2. Every comparison with an interval reports the interval; every interval crossing zero is stated as not established.
3. The Part 7 "will not claim" list checked item by item against the finished draft.
4. The three self-corrections (six-signal reversal, 91.4 % homography, withdrawn CIs) appear in the body, not in an appendix.
5. No filler vocabulary; no "this section will…" openers.

`[PRE-COMMITMENT-ACKNOWLEDGED]`

---

## Numbers corrected during drafting

Five figures written from memory did not survive checking against source and were replaced
by measured values. Recorded because the point of the pre-commitment is that it must bite.

| Location | Written | Measured | Source |
|---|---|---|---|
| Table 3, DetA column | 66.83 / 67.10 / 67.21 | **66.898 / 67.246 / 67.249** | `eval_noCMC.log`, `eval_A0_frozen.log`, `eval_N2.log` |
| §5.2 per-sequence pair counts | 17,833 / 46,733 / 5,182 / 9,340 / 6,795 / 12,331 / 11,741 | **18,519 / 47,474 / 5,299 / 9,335 / 5,180 / 12,666 / 11,482** | `gate_flips.csv` |
| §4.2, §5.2 camera classification | static = 02, 04, 09, 11 | **static = 02, 04, 09; moving = 05, 10, 11, 13** | `oracle_analysis.csv` `camera` column |
| §5.4 UAVDT tracking scope | implied all 50 sequences | **20 sequences** (those with published detections) | `RES_DET/det_FRCNN` |
| Data availability counts | 26 scripts / 36 runs | **29 scripts / 46 runs / 203,564 rows** | filesystem |

The corrected sequence classification strengthens two claims rather than weakening them:
the static/moving separation in §4.2 is now *complete* at sequence level, and §5.2 now
reports that one of the four zero-flip sequences (MOT17-11) is a moving-camera sequence.

## A measurement made reproducible

The deployable-homography comparison in §6.4 was originally computed ad hoc and reported as
"2.2 % spread reduction (6.23 → 6.10 px) over 6,773 frames". It is now produced by
`kitti_global_family.py`, which uses the identical frame and object filter as the oracle
study of §6.2 — verified by the fact that its oracle row reproduces that study's 5.878 px
exactly. On that filter the figures are **7.588 → 7.418 px, a 2.3 % reduction**, with the
>5 px frame fraction 0.16 pp *worse*. The conclusion is unchanged; the number is now
reproducible. `SYNTHESIS.md` and `DEVILS_ADVOCATE_CP2.md` were updated to match.

---

## Part 7 compliance check — claims the paper was pre-committed NOT to make

| # | Prohibited claim | Where the draft forecloses it | Status |
|---|---|---|---|
| 1 | That we discovered compensation can fail | §1.2 final paragraph credits McByte++ explicitly; §2.2 quotes it verbatim | **clear** |
| 2 | That per-target helps in general | Abstract, §6.6, §9.2 all scope it to KITTI pedestrians | **clear** |
| 3 | That per-target beats a global homography on HOTA | Abstract ("only the identity-switch reduction remains significant"); §6.6 gives the interval and refuses the point estimate | **clear** |
| 4 | That the deployable pipeline beats image-based GMC on pedestrians | §7.3 final paragraph, in bold, with both intervals | **clear** |
| 5 | That the car result is positive | §6.6 and §7.2 state not established; §8 refuses to average | **clear** |
| 6 | That we can explain the class split | §8 entire section; both refutations reported | **clear** |
| 7 | Any MOTChallenge test-set number | §9.1; all MOT17 numbers are validation-half | **clear** |

## Dimension scores

| Dimension | Score | Basis |
|---|---|---|
| Evidence traceability | 5/5 | Every table regenerated from source during drafting; five discrepancies caught and fixed |
| Claim calibration | 5/5 | Four claims explicitly withheld; three previously withdrawn claims restated as withdrawn |
| Structural conformance to the approved outline | 5/5 | 9 sections, 8 figures, all beats present |
| Novelty framing | 4/5 | Positioned against three named competing approaches; the AMOT and survey references still need Phase 5a DOI verification |
| Venue fit (IJCV) | 4/5 | Measurement-study framing suits IJCV; length is at the upper end and §4 could compress if the editor asks |
| Self-correction disclosure | 5/5 | Three corrections in the body (§4.4, §6.4, §9.3), none in an appendix |

## Failure condition checks

| Condition | Result |
|---|---|
| A number appears that was not measured | **not triggered** — five caught pre-emptively, all replaced |
| A comparison is reported without its interval | **not triggered** |
| An interval crossing zero is described as a result | **not triggered** |
| A detector difference is credited to tracking | **not triggered** — detections frozen and hashed on both benchmarks |
| A failed gate is re-run until it passes | **not triggered** — the MOT17 ablation matrix was never run |

## Writer decision

**PROCEED to Phase 5.** Two items are known-incomplete and are carried forward rather than
papered over: three references (AMOT, McByte++, the 2026 survey) need full bibliographic
records and DOI verification in Phase 5a, and the Simplified-Chinese abstract is Phase 5b.

---

## Addendum — a gap found in Phase 5a and closed by measurement

Phase 5a's provenance check of the run configurations found that all three MOT17 rows of
Table 3 carry `with_reid: False`. That is correct — it is the published BoT-SORT ablation
row our baseline reproduces — but it left §1's argument untested: the coupling defect is
that compensation error *suppresses the appearance channel*, and a tracker with no
appearance channel cannot exhibit it.

The whole axis was therefore re-run with FastReID SBS-S50 enabled, on the same frozen
detections. The result is **stronger** than the motion-only one:

| | motion only | + appearance |
|---|---|---|
| value of having compensation | +0.888 HOTA, −198 IDSW | **+1.146 HOTA, −140 IDSW** |
| value of perfecting it | +0.099 HOTA, +5 IDSW | **−0.082 HOTA, +5 IDSW** |

With the channel §1 predicts would be rescued switched on, the point value of a perfect warp
is negative on every metric. Added as §5.4 and Table 4; §5.3's forward reference, the abstract,
§1.1, §9.4 and Figure F1 were updated. Determinism of the new pipeline was verified before
the numbers were used: two independent runs of `R_oracle` are **bit-identical** on all seven
sequences.

This is the single objection we most expected a reviewer to raise, and the honest way to
have found it was a provenance check rather than a reviewer.

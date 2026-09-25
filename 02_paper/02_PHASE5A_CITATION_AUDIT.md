# Phase 5a — Citation compliance audit

**Date**: 2026-09-23 · **Manuscript**: `02_paper/manuscript.md` · **Style**: Springer author–year
**Method**: every entry resolved live against the arXiv API (`export.arxiv.org/api/query`) and,
where a DOI is claimed, against Crossref (`api.crossref.org/works/<doi>`). No entry is retained
on the basis of recall.

---

## 1. Errors found and corrected

Four of the nine references in the Phase 4 draft did not survive verification.

| # | Draft entry | What verification returned | Severity |
|---|---|---|---|
| 1 | Claasen & de Villiers (2025). *Information Fusion*, 118, 102971. DOI `10.1016/j.inffus.2025.102971` | That DOI resolves to **"Explainable multi-frequency and multi-region fusion model for affective brain–computer interfaces"** (Wang et al., *Information Fusion* 118, 2025) — an unrelated paper. The real work is **"One homography is all you need: IMM-based joint homography and multiple object state estimation", *Expert Systems with Applications*, 302, 130562 (2026), DOI `10.1016/j.eswa.2025.130562`** | **Critical — fabricated DOI and venue** |
| 2 | Safdarnejad, Liu, & Udpa (2016). BMVC. DOI `10.5244/C.30.31` | That DOI resolves to **"Loglet SIFT for Part Description in Deformable Part Models"** (Zhang & Bhalerao, BMVC 2016). The real paper is BMVC **2015**, pp. 21.1–21.11, DOI **`10.5244/C.29.21`** | **Critical — wrong year and DOI** |
| 3 | Ma et al. (2026). "AMOT: Appearance-guided multi-object tracking with bidirectional spatial consistency for UAV videos" | Actual title: **"Tracking the Unstable: Appearance-Guided Motion Modeling for Robust Multi-Object Tracking in UAV-Captured Videos"** (arXiv:2508.01730v2, 8 authors, accepted AAAI-26 main track). "AMOT" is the method name, not the title | Major |
| 4 | Stanczyk et al. (2026). "McByte++: Tracking by propagating segmentation masks" | Actual title: **"Training-Free Long-Term Multi-Object Tracking for Sports Video Analytics"** (arXiv:2608.15688, Stanczyk, Yoon & Brémond). "McByte++" is the method name | Major |

Items 1 and 2 are the failure mode this audit exists to catch: a plausible-looking DOI in the
right journal family that resolves to a different paper. Both were written from recall during
Phase 4 and neither would have been caught by a reader without resolving the DOI.

## 2. Verbatim quotations re-checked against source

| Quotation | Source | Status |
|---|---|---|
| McByte++ §3.5, "Camera motion compensation is applied only when…" (§2.2) | `01_research/mcbyte.html`, paragraph beginning "McByte++ replaces unconditional camera motion correction" | **verbatim match** |
| BoT-SORT, "In a dynamic camera situation…" (§2.1) | arXiv:2206.14651 §3.2 | verbatim |
| Survey, "Many studies introduce modules such as…" (§2.3) | arXiv:2609.08265 | verbatim |
| IMM-JHSE, "the explicit influence of camera motion compensation techniques…" (§2.2) | arXiv:2409.02562 abstract | verbatim |
| MOTChallenge shutdown notice (§9.1) | motchallenge.net, page Last-Modified 2026-09-08, accessed 2026-09-20 | verbatim |

## 3. References added

The Phase 4 draft used nine works but cited nine; the audit found eight resources that were
used and not credited. All are now cited in text and listed.

| Added | Used for | Cited at |
|---|---|---|
| Milan et al. (2016) — MOT16/MOT17 | benchmark | §4.1 |
| Dendorfer et al. (2020) — MOT20 | benchmark | §4.1 |
| Yu et al. (2020) — UAVDT, IJCV 128(5) | benchmark | §4.1 |
| Ge et al. (2021) — YOLOX | frozen detector | §3.5 |
| Zhang et al. (2022) — ByteTrack, ECCV | detector weights + two-stage association | §3.5, §6.5 |
| Luiten & Hoffhues (2020) — TrackEval | all evaluation | §3.5 |
| Yang et al. (2024) — Depth Anything V2 | estimated depth | §7.3 |
| He et al. (2020) — FastReID | appearance model in the §5.6 runs | §5.6 |

## 4. Final tally

| | Count |
|---|---|
| Reference entries | 17 |
| Resolved against arXiv API | 11 |
| Resolved against Crossref DOI | 6 |
| Entries cited in text | 17 / 17 |
| In-text citations present in the list | all |
| Unresolved / placeholder entries | **0** |

**Verdict: PASS.** No entry remains that was not resolved against a live record.

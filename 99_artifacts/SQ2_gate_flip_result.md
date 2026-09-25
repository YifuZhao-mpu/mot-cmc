# SQ2 — Does compensation error change the association gate decision?

**Date**: 2026-09-20 · **Kill-switch**: K2 · **Verdict: K2 FAILS — the mechanism hypothesis
is not supported on MOT17.**

---

## 1. What was measured, and why this way

The coupling defect is real at code level. `BoT-SORT/tracker/bot_sort.py:303-314`:

```python
ious_dists      = matching.iou_distance(strack_pool, detections)   # AFTER the CMC warp
ious_dists_mask = (ious_dists > self.proximity_thresh)             # 0.5
emb_dists[emb_dists > self.appearance_thresh] = 1.0
emb_dists[ious_dists_mask] = 1.0        # appearance rejected because motion disagreed
dists           = np.minimum(ious_dists, emb_dists)
```

The hypothesis was that a wrong warp inflates `ious_dists`, trips the mask, and suppresses
appearance evidence exactly when it is most needed.

An earlier framing asked whether compensation error alone pushes IoU below `theta_iou`.
That was the wrong question (it used per-frame medians and ignored where the pair already
sat relative to the threshold) and it produced a misleadingly clean 0%. The question that
matters is whether the error **changes the outcome**:

for every ground-truth object present in consecutive frames, warp its previous box by the
online warp and by the offline reference warp, compute IoU against its true current box,
and count pairs whose gate decision differs. Ground-truth identity is used, so detector
and ReID behaviour are excluded entirely — this isolates the geometry.

## 2. Result — 109,955 ground-truth pairs, all 7 MOT17 train sequences

| Sequence | camera | pairs | flips | **harmful** | helpful | IoU med (online) |
|---|---|---|---|---|---|---|
| MOT17-02 | static | 18,519 | 0 | **0** | 0 | 0.972 |
| MOT17-04 | static | 47,474 | 0 | **0** | 0 | 0.982 |
| MOT17-09 | static | 5,299 | 0 | **0** | 0 | 0.934 |
| MOT17-11 | moving | 9,335 | 0 | **0** | 0 | 0.952 |
| MOT17-05 | moving | 5,180 | 17 | 12 | 5 | 0.890 |
| MOT17-10 | moving | 12,666 | 21 | 14 | 7 | 0.899 |
| MOT17-13 | moving | 11,482 | 17 | 8 | **9** | 0.888 |
| **TOTAL** | | **109,955** | **55 (0.050 %)** | **34** | **21** | |

**Net harmful effect: 13 events across the entire MOT17 training set.**

Threshold sensitivity — the conclusion is not an artefact of `theta_iou = 0.5`:

| theta | gated out (online) | gated out (reference) | flips | harmful |
|---|---|---|---|---|
| 0.3 | 1482 | 1512 | 654 | 312 |
| 0.4 | 459 | 439 | 216 | 118 |
| **0.5** | **140** | **127** | **55** | **34** |
| 0.6 | 46 | 38 | 22 | 15 |
| 0.7 | 14 | 9 | 7 | 6 |

Even at a far stricter gate (0.3), harmful flips are 0.28 % of pairs.

## 3. Three qualifications that make the negative result stronger, not weaker

1. **On MOT17-13 the error is net *beneficial*** (9 helpful vs 8 harmful). The direction is
   not even consistent across moving-camera sequences.
2. **Harmful flips concentrate on cases that were already lost.** Median box width at a
   harmful flip is 21–33 px (vs 28–124 px sequence medians), and in MOT17-05 the median
   *visibility* at a harmful flip is **0.0000** — the object is fully occluded. These are
   not "appearance would have saved it" cases.
3. **Four of seven sequences produce exactly zero flips**, including one moving-camera
   sequence (MOT17-11).

## 4. Why — the arithmetic, stated plainly

| Quantity | Value |
|---|---|
| Compensation error, moving-camera median (I1 oracle contrast) | **1.31 px** |
| Compensation error, moving-camera p90 | 4.55 px |
| Ground-truth box width, sequence medians | 21–124 px |
| Resulting IoU after compensation error | 0.888–0.982 |
| IoU needed to close the gate | < 0.50 |

A ~1 px error against a ~50 px box cannot move IoU from 0.9 to below 0.5. For a pure
horizontal shift the gate closes only past roughly `w/3` — 7 px on the smallest boxes,
40 px on the largest. The online estimator is simply not wrong enough on MOT17.

## 5. What this does and does not license saying

**Supported**:
- The coupling defect exists in the shipped implementation (verified in source).
- Camera-motion compensation error on MOT17 is measurable, predictable from free RANSAC
  statistics (`eps`, held-out AUC 0.866), and **too small to change association outcomes**.
- MOT17 does not contain the catastrophic compensation-failure regime the literature
  describes: `n_inliers < 100` in **0** of 5316 frames; the synthetic `low_texture` mode
  that produced 105 px median error has no MOT17 counterpart.

**Not supported**:
- That repairing compensation reliability improves tracking on MOT17.
- Any claim resting on the coupling defect firing at a material rate on this benchmark.

## 6. Bound on the achievable gain (independent of the tracker run)

34 harmful gate closures, of which the majority sit on fully- or heavily-occluded small
boxes, against a baseline of **IDSW = 140** on the half-val split. Even assuming every
harmful flip in the evaluated half caused one ID switch and every one were recovered, the
effect is single-digit ID switches. The empirical N2 measurement (reference warp
substituted into the tracker) is the confirmation, but the geometric bound already says
what it will find.

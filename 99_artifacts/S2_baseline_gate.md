# S2 Gate — BoT-SORT baseline reproduction

**Date**: 2026-09-20 · **Protocol**: MOT17 half-val (second half of each train sequence)
**Detector**: ByteTrack YOLOX-X ablation weights (CrowdHuman + MOT17 first half)
  `bytetrack_ablation.pth.tar` sha256 `26cb8d2808664e5068a4c812d53becbc948b47fd6eacf2b45db049ab40c48b1a`
**Command**: `tools/track.py <MOT17> --default-parameters --benchmark MOT17 --eval val --fp16 --fuse`
**Evaluation**: official TrackEval, `DO_PREPROC=True`, metrics HOTA+CLEAR+Identity
**Split cross-check**: per-sequence evaluated lengths (299/524/418/262/326/449/374) match
BoT-SORT's own precomputed GMC ablation file line counts exactly.

## Result

| Metric | Published (BoT-SORT paper, Table 1 row "Baseline + columns 1-3") | This reproduction | Δ |
|---|---|---|---|
| MOTA | 78.39 | **78.44** | +0.05 |
| IDF1 | 81.53 | **81.50** | −0.03 |
| HOTA | 69.11 | **69.12** | +0.01 |

Additional metrics from this run (not in the paper's table):
DetA 67.24 · AssA 71.57 · IDSW 140 · MT 204 · ML 38 · Frag 443 · IDs 441 · GT_IDs 339

### Verdict: **PASS**

HOTA agrees to 0.01, IDF1 to 0.03, MOTA to 0.05. The data split, detector, tracker and
evaluation chain are all validated. Every subsequent delta is measured against a baseline
that reproduces the published one.

## The number that governs the power gate

The same paper table isolates what camera motion compensation is worth **in total**:

| Row | MOTA | IDF1 | HOTA |
|---|---|---|---|
| Baseline + KF (no CMC) | 77.67 | 79.89 | 68.12 |
| Baseline + KF + CMC | 78.31 | 81.51 | 69.06 |
| **CMC contribution** | **+0.64** | **+1.62** | **+0.94** |

So 0.94 HOTA is the entire value of *having* compensation. This project does not add
compensation; it repairs it where it fails. The N2 headroom ceiling is therefore bounded
well below 0.94 HOTA, and the 3x power gate (N2 >= 3 x N1) is evaluated against that.

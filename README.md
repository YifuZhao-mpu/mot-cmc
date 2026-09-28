# Camera-Motion Compensation Is Not the Bottleneck

Measurement code and data for *Camera-Motion Compensation Is Not the Bottleneck: A Measurement
Study of Shared Warps in Tracking-by-Detection*.

The paper proposes no new tracker. It measures a quantity the field has not measured — what a
**perfect** camera-motion warp would be worth once a working compensator is already in place — and
reports what follows from measuring it.

## What it found

- On the MOT17 sequences that actually have camera motion, replacing the online estimate with a
  non-causal oracle warp is worth **−0.04 HOTA** (95 % CI [−0.20, +0.05]) without an appearance
  channel and **+0.19** [+0.05, +0.52] with one, against **+3.43** [+1.01, +5.52] for having a
  working compensator at all.
- The error a perfect warp removes changes the association gate's decision for **34 of 109,955**
  ground-truth pairs, harmfully.
- On KITTI, where the camera translates, a shared 4-DOF warp is genuinely inadequate — but the
  missing ingredient is **depth**, not per-object treatment. A global homography fitted to
  background points at their monocularly estimated depths cuts the within-frame residual spread
  from **8.67 px to 1.37 px**, beats the compensator BoT-SORT ships by **+1.19 HOTA** [+0.26, +1.92]
  on cars, and reduces pedestrian identity switches from **126 to 85**.
- A per-target correction given ground-truth depth *and* ground-truth association adds nothing on
  top of it.

## Verifying the paper's numbers

One command recomputes them from the released CSVs and TrackEval output, and exits non-zero on any
mismatch:

```bash
python 03_code/rac/verify_numbers.py
```

It checks **710 values and provenance properties** from a fresh clone — the provenance checks read
the released TrackEval output rather than the raw per-frame dumps, which are not redistributed, so
this command works for you and not only for us. Every cell of every table and every confidence
interval is parsed out of the manuscript itself and recomputed, so the paper cannot drift from its
own evidence; the provenance checks cover which run feeds which table, whether any configuration is
silently switched off, and whether the reproduction page still maps every table and names only
commands that exist. The provenance checks exist because the two most serious
defects found in review were of that kind: a warp bundle that was the identity on 36 % of moving
frames, and an oracle configuration that reverted to the online estimate on 18 % of the hardest
sequence. A value-only checker passed both.

```bash
python 03_code/rac/make_release.py --check   # SHA-256 of every released file
python 03_code/rac/make_figures.py           # regenerate all eight figures
python 03_code/rac/build_latex.py            # Markdown -> Springer sn-jnl LaTeX
```

Scripts resolve the project root themselves (`03_code/rac/paths.py`), from `MOTCMC_ROOT` if set and
otherwise from their own location. No `PYTHONPATH` is needed and nothing is hard-coded — check the
tree out anywhere.

## Layout

| Path | Contents |
|---|---|
| `02_paper/` | the manuscript in Markdown, supplementary material, cover letter, and the review and integrity records |
| `03_code/rac/` | 40 analysis scripts and 4 shell drivers — the whole measurement stack |
| `04_experiments/` | 21 result CSVs, detection manifests with per-file SHA-256, TrackEval summaries for all 61 tracker runs |
| `05_figures/` | the eight figures, PDF and PNG |
| `99_artifacts/RELEASE/` | SHA-256 manifest, per-artefact reproduction commands, and what is not redistributed |
| `00_pipeline/` | the running record of the work, including every claim withdrawn and why |

## Not in this repository

Benchmark images and annotations (MOT17, MOT20, UAVDT, KITTI — 64 GB), model weights (2.4 GB), and
the third-party trackers the experiments import (BoT-SORT, ByteTrack, TrackEval, Depth-Anything-V2).
All are public at their own addresses; `99_artifacts/RELEASE/DATA.md` records where to get each, the
SHA-256 of the ones whose identity affects a number in the paper, and the compatibility patches
applied to the third-party trees.

Downloaded copies of other people's papers are also excluded. Every source is cited by DOI or arXiv
id in the manuscript.

## A note on the record

`00_pipeline/state.md` and §9.4 of the manuscript record eight claims withdrawn over the course of
this work, four of them our own replacements for earlier withdrawn claims. Three were artefacts of
how an experiment was constructed rather than of the quantity being measured, and two of those were
found by a reviewer *executing* this code rather than reading the paper. The record is kept because
a measurement paper that reports only its final state is not auditable.

## Licence

Code under MIT (`LICENSE`); measurement data under CC BY 4.0 (`LICENSE-DATA`). The benchmarks and
third-party trees keep their own licences and are not redistributed.

## AI assistance

A large language model was used throughout as a research assistant — literature search, writing and
debugging the measurement code, adversarial review of the design, and drafting. Every number was
produced by executing this code on this data; `verify_numbers.py` exists so that can be checked
mechanically.

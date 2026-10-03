[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23092962.svg)](https://doi.org/10.5281/zenodo.23092962)

# Camera-Motion Compensation in Tracking-by-Detection

Measurement code and data for *Camera-Motion Compensation in Tracking-by-Detection: Accuracy Headroom and Depth-Aware Shared Warps*.

The study measures compensation-accuracy headroom through reference-warp substitution and evaluates depth-aware shared correction under camera translation. Its experiments connect geometric residuals, association-gate changes and tracking outcomes.

## Main Findings

- On the MOT17 sequences that actually have camera motion, replacing the online estimate with a
  non-causal reference warp is worth **−0.04 HOTA** (95 % CI [−0.20, +0.05]) without an appearance
  channel and **+0.19** [+0.05, +0.52] with one, against **+3.43** [+1.01, +5.52] for having a
  working compensator at all.
- The reference substitution changes the association gate's decision for **34 of 109,955**
  ground-truth pairs, harmfully.
- On KITTI, a depth-aware global homography uses sensor ego-motion and estimated background depths on moving frames, with the near-static fallback specified in the paper. It reduces within-frame residual spread from **8.67 px to 1.37 px** and improves car HOTA by **+1.19** [+0.26, +1.92] over online compensation. Pedestrian identity switches fall from **126 to 97**, or **85** with contact-point application.
- The shared model provides spatially varying correction without per-object association. The annotation-assisted per-target HOTA contrast against the homography is **−0.073 [−0.624, +0.392]** on cars and **+0.366 [−0.035, +0.986]** on pedestrians.

## Verifying the paper's numbers

One command recomputes them from the released CSVs and TrackEval output, and exits non-zero on any
mismatch:

```bash
python 03_code/rac/verify_numbers.py
```

The verifier checks numerical values and source provenance against the released CSVs, warp bundles and TrackEval output. It directly reads printed tracking, reliability and geometry tables, confidence intervals, timing samples and class-exposure percentages from the manuscript and supplementary material. It also checks which runs support the comparisons, sequence coverage and the reproduction commands. `--list` identifies three instrument and reproducibility checks handled separately.

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
| `03_code/rac/` | 43 analysis scripts and 4 shell drivers — the whole measurement stack |
| `04_experiments/` | 22 result CSVs, detection manifests with per-file SHA-256, TrackEval summaries for all 63 tracker runs |
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

`00_pipeline/state.md` records eight claims withdrawn over the course of
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

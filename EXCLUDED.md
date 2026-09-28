# What this folder does not contain, and why

The folder holds everything the project produced. It does not hold other people's data, other
people's code, or intermediates that are large and regenerable. Each is recoverable; the SHA-256 of
every artefact whose identity affects a number in the paper is in `99_artifacts/RELEASE/DATA.md`.

| Not included | Size | Why | How to get it |
|---|---|---|---|
| MOT17, MOT20 benchmark images and annotations | ~55 GB | public, not ours to redistribute | <https://motchallenge.net> |
| UAVDT | ~5 GB | same | the authors' release page |
| KITTI tracking images, `oxts`, `calib`, labels | ~4 GB | same | <https://www.cvlibs.net/datasets/kitti/eval_tracking.php> |
| YOLOX-X ablation weights, YOLO11x, FastReID, Depth-Anything-V2 checkpoints | 2.4 GB | public at their own addresses | see `DATA.md` for each, with our SHA-256 |
| BoT-SORT, ByteTrack, TrackEval, Depth-Anything-V2 source trees | ~500 MB | other people's repositories; we patched them only for modern NumPy and PyTorch, and those patches are described rather than shipped | clone upstream, apply the patches in `DATA.md` |
| raw per-frame tracker output (`04_experiments/trackers/*/*/data/`) | 265 MB | regenerable, and nothing in the paper is computed from it — every number comes from the TrackEval summaries and detailed CSVs, which **are** here | rerun the tracking commands in `REPRODUCE.md` |
| the depth-noise warp bundles (`kitti_warps_dn*`, `kitti_warps_planar_dn*`) and reference warps | 114 MB | regenerable from one command each | `REPRODUCE.md`, Tables 13 and 14 |
| the Python virtualenv | — | machine-specific | `numpy`, `pandas`, `scipy`, `opencv-python`, `torch`, `matplotlib` |
| downloaded third-party papers used for the citation and quotation checks | 27 MB | not ours to redistribute; every one is cited by DOI or arXiv id in the manuscript | the publishers |

## What this means for a reader

- **To check that the paper's numbers are what the measurements say**: nothing is missing. Run
  `python rac/verify_numbers.py` from `03_code/`. It recomputes 693 values and provenance properties
  from what is here.
- **To reproduce a measurement from the images up**: fetch the benchmark and the weights named in
  `DATA.md`, then follow `REPRODUCE.md`.

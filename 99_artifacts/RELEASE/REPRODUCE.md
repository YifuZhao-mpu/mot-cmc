# Reproducing every number in the paper

All commands run from `03_code/` with the project virtualenv active and
`PYTHONPATH=03_code:03_code/BoT-SORT`. Benchmark images and model weights are
not redistributed; see `DATA.md` for where to obtain each and which SHA-256 we used.

| Artefact in the paper | Command (from `03_code/`) |
|---|---|
| Table 1 | `python rac/scan_mot.py --dataset {MOT17,MOT20} ; python rac/uavdt_track.py (scan)` |
| Table 2, §5.1 | `python rac/gate_flip.py` |
| Table 3 | `bash rac/run_power_gate.sh ; bash rac/evaluate.sh {A_noCMC,A0_frozen,A0_botsort_baseline,N2_oracle_warp}` |
| Table 4 | `python rac/run_rac.py --name R_{none,online,oracle} --warp-source {none,online,reference} --with-reid` |
| Table 5 | `python rac/bootstrap_ci.py --mot17` |
| Table 6 | `python rac/kitti_track.py --mode {none,online,global_oracle,global_homography,per_target} ; bash rac/evaluate_kitti.sh` |
| Table 7 | `python rac/bootstrap_ci.py --pairs ...` |
| Table 8 | `python rac/kitti_causal_link.py` |
| Table 9 | `python rac/kitti_warps_v3.py --depth-sigma S ; python rac/kitti_track.py --mode per_target` |
| Table 10 | `python rac/kitti_depth_warps.py ; python rac/kitti_track.py --mode per_target_depth` |
| §4.2 | `python rac/oracle_contrast.py ; python rac/analyse_oracle.py` |
| §4.3 | `python rac/confound_placebo.py` |
| §4.4 | `python rac/signal_search.py` |
| §6.2, §6.3 | `python rac/kitti_per_object.py` |
| §6.4 | `python rac/kitti_model_class.py ; python rac/kitti_global_family.py` |
| §8 | `python rac/kitti_class_split.py` |
| §6.6 leave-one-out | `python rac/bootstrap_ci.py --loo` |
| Figures 1-8 | `python rac/make_figures.py` |
| all of the above, checked | `python rac/verify_numbers.py` |

`verify_numbers.py` is the one that matters: it recomputes the paper's numbers
from the released CSVs and TrackEval output and exits non-zero on any mismatch.

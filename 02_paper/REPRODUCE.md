# Reproducing every number in the paper

All commands run from `03_code/` with the project virtualenv active and
`PYTHONPATH=03_code:03_code/BoT-SORT`. Benchmark images and model weights are
not redistributed; see `DATA.md` for where to obtain each and which SHA-256 we used.

Set `MOTCMC_ROOT` if the tree is not at its original path; every script and shell
driver resolves its own paths from it, so nothing needs editing.

## Tables

| Table | What it reports | Command (from `03_code/`) |
|---|---|---|
| 1 | compensation-reliability audit, four benchmarks | `python rac/scan_mot.py --root <DATA>/{MOT17,MOT20}/train --out ../04_experiments/{mot17,mot20}_gmc_scan.csv` ; the same script with `--root <DATA>/UAVDT` for `uavdt_gmc_scan.csv` |
| 2 | gate flips on MOT17 | `python rac/gate_flip.py` |
| 3 | MOT17 compensation-value axis, motion only | `bash rac/run_power_gate.sh` ; `bash rac/evaluate.sh {A_noCMC,A0_frozen,A0_botsort_baseline,N2_oracle_warp,N2S_oracle_strict}` |
| 4 | the same axis with appearance on | `python rac/run_rac.py --name R_{none,online,oracle} --warp-source {none,online,reference} --with-reid` |
| 5 | MOT17 bootstrap intervals | `python rac/bootstrap_ci.py --mot17` |
| 6 | global compensation models, geometric | `python rac/kitti_global_family_v2.py` |
| 7 | what each configuration is allowed to use | (no run; it describes the configurations of Tables 8–9) |
| 8 | KITTI tracking, 21 sequences | `python rac/kitti_warps_v3.py` ; `python rac/kitti_warps_anchored.py` ; `python rac/kitti_global_family_v2.py --warp-out ../04_experiments/kitti_warps_planar` ; `python rac/kitti_track.py --mode {none,online,global_oracle,global_anchored_ped,global_anchored_car,global_homography,global_homography_foot,per_target}` ; `bash rac/evaluate_kitti.sh` |
| 9 | KITTI bootstrap intervals | `python rac/bootstrap_ci.py --pairs` |
| 10 | shuffled placebo | `python rac/kitti_track.py --mode per_target_shuffled` ; `bash rac/evaluate_kitti.sh` |
| 11 | per-target exposure quartiles (§6.7) | `python rac/kitti_causal_link.py` |
| 12 | homography exposure quartiles (§6.8) | `python rac/kitti_causal_link.py --exposure homography --global-name v3_online --per-name planar2_homography --out ../04_experiments/kitti_causal_link_hom.csv` |
| 13 | per-target depth-noise sweep (§7.2) | `python rac/kitti_warps_v3.py --depth-sigma S` for S in 0.05…0.50 ; `python rac/kitti_track.py --mode per_target` |
| 14 | homography depth-noise sweep (§7.3) | `python rac/kitti_global_family_v2.py --depth-sigma S --seed 20260926 --warp-out ../04_experiments/kitti_warps_planar_dnNNN` for S in 0.05…0.50 ; `python rac/kitti_track.py --mode global_homography` ; `bash rac/evaluate_kitti.sh` |
| 15 | the deployable ladder | `python rac/kitti_depth_warps.py` ; `python rac/kitti_track.py --mode {global_oracle,per_target_depth}` |
| 16 | per-frame cost | `python rac/runtime_cost.py` |

## Sections with measurements of their own

| Section | Command |
|---|---|
| §3.1 instrumented compensation | `python rac/instrumented_gmc.py` |
| §3.2, §4.2 reference warp and the oracle contrast | `python rac/oracle_contrast.py --root <DATA>/MOT17/train --out ../04_experiments/oracle` ; `python rac/analyse_oracle.py` |
| §4.2 the MOT20 external check | `python rac/oracle_contrast.py --root <DATA>/MOT20/train --filter '' --out ../04_experiments/oracle_mot20` |
| §4.3 error prediction, stratification and placebo | `python rac/signal_search.py` ; `python rac/confound_placebo.py` |
| §4.4 the reversal | printed per sequence by `python rac/analyse_oracle.py` |
| §5.2 synthetic failure study | `python rac/synthetic_failure_study.py` |
| §5.6 UAVDT | `python rac/uavdt_track.py --mode {none,online}` ; `bash rac/evaluate_uavdt.sh` |
| §6.2, §6.3 per-object residual and gate reach | `python rac/kitti_per_object.py` |
| §6.4 model class and the depth diagnosis | `python rac/kitti_model_class.py` ; `python rac/kitti_global_family_v2.py` |
| §6.4 two diagnostics that failed to discriminate | `python rac/spread_2d.py` ; `python rac/parallax_indicator.py` |
| §6.6 leave-one-sequence-out | `python rac/bootstrap_ci.py --loo` |
| §7.4 depth ratio scan | `python rac/depth_ratio_scan.py` |
| §8 class split | `python rac/kitti_class_split.py` |
| Figures 1–8 | `python rac/make_figures.py` |

## Support

| What | Command |
|---|---|
| frozen detections (MOT17/MOT20, KITTI) | `python rac/freeze_detections.py` ; `python rac/kitti_freeze_dets.py` |
| MOT17 validation half | `python rac/build_val_half.py` |
| refit every oracle warp after the estimator correction | `python rac/refit_warps.py` |
| LaTeX build | `python rac/build_latex.py` |
| manifest check on a fresh clone | run the LaTeX build first: `02_paper/latex/manuscript.tex` is a build product, is not committed, and *is* hashed in the manifest. The build is byte-reproducible, so the hash matches once it has been run. |
| release manifest | `python rac/make_release.py` |
| **every number above, checked against source** | `python rac/verify_numbers.py` |

`verify_numbers.py` is the one that matters: it parses the manuscript's own tables
and intervals, recomputes each from the released CSVs and TrackEval output, and
exits non-zero on any mismatch. It also checks provenance — identity-warp coverage,
which run backs which table, and that every table in the manuscript is listed on
this page. `--list` prints the three things it does not cover.

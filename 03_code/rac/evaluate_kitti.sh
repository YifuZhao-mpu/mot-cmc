#!/bin/bash
# Official TrackEval on KITTI tracking (all 21 training sequences).
# No split is used: the detector is COCO-pretrained and never saw KITTI.
set -euo pipefail
# Resolve the project root: MOTCMC_ROOT if set, else two levels above this script.
ROOT="${MOTCMC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="${MOTCMC_PY:-$ROOT/.venv/bin/python}"
TE="$ROOT/03_code/TrackEval"
GT="$ROOT/04_experiments/eval/KITTI"
TR="$ROOT/04_experiments/trackers/KITTI"
TRACKER="${1:?usage: evaluate_kitti.sh <tracker_name> [n_cores]}"
N="${2:-12}"
cd "$TE"
PYTHONPATH="$TE" "$PY" scripts/run_kitti.py \
  --GT_FOLDER "$GT" --TRACKERS_FOLDER "$TR" \
  --TRACKERS_TO_EVAL "$TRACKER" \
  --SPLIT_TO_EVAL training --CLASSES_TO_EVAL car pedestrian \
  --METRICS HOTA CLEAR Identity \
  --USE_PARALLEL True --NUM_PARALLEL_CORES "$N" \
  --PRINT_CONFIG False --OUTPUT_SUMMARY True --OUTPUT_DETAILED True --PLOT_CURVES False

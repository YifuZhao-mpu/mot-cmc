#!/bin/bash
set -euo pipefail
# Resolve the project root: MOTCMC_ROOT if set, else two levels above this script.
ROOT="${MOTCMC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="${MOTCMC_PY:-$ROOT/.venv/bin/python}"
TE="$ROOT/03_code/TrackEval"
GT="$ROOT/04_experiments/eval"
TR="$ROOT/04_experiments/trackers/UAVDT"
cd "$TE"
PYTHONPATH="$TE" "$PY" scripts/run_mot_challenge.py \
  --BENCHMARK UAVDT --SPLIT_TO_EVAL test \
  --GT_FOLDER "$GT" --TRACKERS_FOLDER "$TR" \
  --TRACKERS_TO_EVAL "$1" --DO_PREPROC False \
  --METRICS HOTA CLEAR Identity --USE_PARALLEL True --NUM_PARALLEL_CORES "${2:-10}" \
  --PRINT_CONFIG False --OUTPUT_SUMMARY True --OUTPUT_DETAILED True --PLOT_CURVES False

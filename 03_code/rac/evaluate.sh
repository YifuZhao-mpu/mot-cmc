#!/bin/bash
# Official TrackEval on the MOT17 half-val protocol.
#   GT:       <GT_FOLDER>/MOT17-val-half/<SEQ>/gt/gt.txt  (+ seqinfo.ini)
#   seqmap:   <GT_FOLDER>/seqmaps/MOT17-val-half.txt
#   trackers: <TRACKERS_FOLDER>/MOT17-val-half/<TRACKER>/data/<SEQ>.txt
# Usage: evaluate.sh <tracker_name> [n_cores]
set -euo pipefail
# Resolve the project root: MOTCMC_ROOT if set, else two levels above this script.
ROOT="${MOTCMC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="${MOTCMC_PY:-$ROOT/.venv/bin/python}"
TE="$ROOT/03_code/TrackEval"
GT="$ROOT/04_experiments/eval"
TR="$ROOT/04_experiments/trackers"
TRACKER="${1:?usage: evaluate.sh <tracker_name> [n_cores]}"
NCORES="${2:-12}"
cd "$TE"
PYTHONPATH="$TE" "$PY" scripts/run_mot_challenge.py \
  --BENCHMARK MOT17 --SPLIT_TO_EVAL val-half \
  --GT_FOLDER "$GT" --TRACKERS_FOLDER "$TR" \
  --TRACKERS_TO_EVAL "$TRACKER" \
  --DO_PREPROC True --METRICS HOTA CLEAR Identity \
  --USE_PARALLEL True --NUM_PARALLEL_CORES "$NCORES" \
  --PRINT_CONFIG False --OUTPUT_SUMMARY True --OUTPUT_DETAILED True --PLOT_CURVES False

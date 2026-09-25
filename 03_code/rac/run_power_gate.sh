#!/bin/bash
# Chain: freeze detections -> A0 baseline -> A0 with oracle warp -> evaluate -> power gate.
# Every step is idempotent: existing outputs are reused, so this can be re-run safely.
set -uo pipefail

# single-instance lock: two concurrent runs would write the same output files
LOCK=/tmp/rac_power_gate.lock
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[lock] another run_power_gate.sh is already running; refusing to start a second one"
  exit 3
fi

# Resolve the project root: MOTCMC_ROOT if set, else two levels above this script.
ROOT="${MOTCMC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="${MOTCMC_PY:-$ROOT/.venv/bin/python}"
CODE="$ROOT/03_code"
EXP="$ROOT/04_experiments"
TR=$EXP/trackers/MOT17-val-half
export PYTHONPATH=$CODE/BoT-SORT:$CODE

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ---------------------------------------------------------------- 1. detections
if [ ! -f "$EXP/detections/MOT17-val-half/manifest.json" ]; then
  log "freezing detections (YOLOX-X ablation, fp16+fuse to match the published config)"
  cd "$CODE"
  CUDA_VISIBLE_DEVICES=0 "$PY" rac/freeze_detections.py --fp16 --fuse \
      2>&1 | tail -12 || { log "FREEZE FAILED"; exit 1; }
else
  log "detections already frozen, reusing"
fi

# ---------------------------------------------------------------- 2. A0 baseline
if [ ! -f "$TR/A0_frozen/data/MOT17-13-FRCNN.txt" ]; then
  log "A0_frozen: BoT-SORT behaviour on frozen detections"
  cd "$CODE"
  CUDA_VISIBLE_DEVICES=0 "$PY" rac/run_rac.py --name A0_frozen 2>&1 | tail -10
else
  log "A0_frozen exists, reusing"
fi

# ---------------------------------------------------------------- 3. oracle warp
if [ ! -f "$TR/N2_oracle_warp/data/MOT17-13-FRCNN.txt" ]; then
  log "N2_oracle_warp: identical config, offline reference warp substituted"
  cd "$CODE"
  CUDA_VISIBLE_DEVICES=1 "$PY" rac/run_rac.py --name N2_oracle_warp \
      --warp-source reference 2>&1 | tail -10
else
  log "N2_oracle_warp exists, reusing"
fi

# ---------------------------------------------------------------- 4. no-CMC reference point
if [ ! -f "$TR/A_noCMC/data/MOT17-13-FRCNN.txt" ]; then
  log "A_noCMC: compensation disabled -- locates the baseline on the CMC value axis"
  cd "$CODE"
  CUDA_VISIBLE_DEVICES=2 "$PY" rac/run_rac.py --name A_noCMC \
      --warp-source none 2>&1 | tail -10
fi

# ---------------------------------------------------------------- 5. evaluate
for name in A0_frozen N2_oracle_warp A_noCMC; do
  if [ -d "$TR/$name/data" ] && [ ! -f "$TR/$name/pedestrian_summary.txt" ]; then
    log "evaluating $name"
    bash "$CODE/rac/evaluate.sh" "$name" 12 > "$EXP/eval_$name.log" 2>&1 \
      || log "eval $name FAILED (see $EXP/eval_$name.log)"
  fi
done

# ---------------------------------------------------------------- 6. N1 runs
for i in 2 3 4 5; do
  src=$CODE/BoT-SORT/YOLOX_outputs/N1_run$i/track_results
  dst=$TR/N1_run$i/data
  if [ -d "$src" ] && [ "$(ls "$src"/*.txt 2>/dev/null | wc -l)" -ge 7 ] && [ ! -d "$dst" ]; then
    mkdir -p "$dst" && cp "$src"/*.txt "$dst"/
    log "staged N1_run$i"
  fi
  if [ -d "$dst" ] && [ ! -f "$TR/N1_run$i/pedestrian_summary.txt" ]; then
    bash "$CODE/rac/evaluate.sh" "N1_run$i" 12 > "$EXP/eval_N1_run$i.log" 2>&1 \
      || log "eval N1_run$i FAILED"
  fi
done

# stage the original live-detection baseline as N1_run1
if [ ! -d "$TR/N1_run1/data" ] && [ -d "$TR/A0_botsort_baseline/data" ]; then
  mkdir -p "$TR/N1_run1/data" && cp "$TR/A0_botsort_baseline/data"/*.txt "$TR/N1_run1/data"/
  bash "$CODE/rac/evaluate.sh" N1_run1 12 > "$EXP/eval_N1_run1.log" 2>&1 || true
  log "staged N1_run1 from the original baseline"
fi

# ---------------------------------------------------------------- 7. the gate
log "=========== POWER GATE ==========="
cd "$CODE"
"$PY" rac/power_gate.py \
  --n1-runs N1_run1 N1_run2 N1_run3 N1_run4 N1_run5 \
  --baseline A0_frozen --oracle N2_oracle_warp --threshold 3.0 2>&1 | tail -45
log "done"

#!/bin/bash
# One-shot timed launcher for EXP-1B (official Claude-in-Chrome cold baseline).
# Sleeps until the target epoch, waits for any still-running phase-3 chain to
# finish (shared claude quota; different browser), then runs the experiment.
set -u
TARGET_EPOCH=$1
BENCH="$(cd "$(dirname "$0")" && pwd)"   # this script lives in benchmark/
LOG="$BENCH/logs/exp1b_launch.log"

log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

log "armed: will launch exp1b-cinc-cold at epoch $TARGET_EPOCH ($(date -r "$TARGET_EPOCH" +%H:%M:%S))"
while [ "$(date +%s)" -lt "$TARGET_EPOCH" ]; do sleep 20; done
log "target time reached"

# guard: never overlap the phase-3 chain (quota + orchestration hygiene)
for i in $(seq 1 90); do
  pgrep -f "runner.py run --experiment exp3" >/dev/null 2>&1 || break
  log "phase-3 chain still running, waiting (check $i)"
  sleep 60
done

cd "$BENCH"
log "preflight:"
python3 runner.py preflight >> "$LOG" 2>&1
log "launching exp1b-cinc-cold"
python3 runner.py run --experiment exp1b-cinc-cold --buffer 45 >> "$LOG" 2>&1
log "=== EXP1B COMPLETE ==="

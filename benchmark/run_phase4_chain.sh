#!/bin/bash
# Phase-4 autonomous chain:
#   experiential study (already running) -> fork-context probe -> 4A smoke ->
#   expert study (sonnet, MAX effort) -> full exp4a -> full exp4b
# Aborts hard at the first broken gate. Logs to stdout (runner keeps its own
# per-experiment logs). Reproduce any single step by running the printed
# commands manually.
set -u
cd "$(dirname "$0")"

echo "[chain] waiting for experiential study (study.json)"
while [ ! -f data/phase4/experiential_study/study.json ]; do
  if ! pgrep -f "p4study --arm experiential" >/dev/null 2>&1; then
    sleep 5
    [ -f data/phase4/experiential_study/study.json ] && break
    echo "[chain] ABORT: experiential study process died without study.json"; exit 1
  fi
  sleep 20
done
echo "[chain] experiential study complete"
sleep 30

echo "[chain] fork-context probe (throwaway fork, no tools)"
SID=$(python3 -c "import json;print(json.load(open('data/phase4/experiential_study/study.json'))['session_id'])")
WD=$(python3 -c "import json;print(json.load(open('data/phase4/experiential_study/study.json'))['workdir'])")
PROBE=$(cd "$WD" && env -u CLAUDECODE claude -p "Without using any tools: in ONE line, name the web apps you completed tasks in earlier in this session, and one concrete UI mechanic you learned in each." --resume "$SID" --fork-session --model sonnet --effort medium --output-format json --dangerously-skip-permissions 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('result','')[:400])")
echo "[chain] probe says: $PROBE"
echo "$PROBE" | grep -qi "dashdish" && echo "$PROBE" | grep -qi "zilloft" || {
  echo "[chain] ABORT: fork did not recall the study context"; exit 1; }
echo "[chain] fork context carries. Smoke rollout next."

python3 runner.py run --experiment exp4a-experiential-fork --only dashdish-1 --buffer 45 \
  || { echo "[chain] ABORT: smoke run errored"; exit 1; }
python3 - <<'PY' || { echo "[chain] ABORT: smoke rollout not completed"; exit 1; }
import json, sys
s = json.load(open("data/exp4a-experiential-fork/status.json"))
sys.exit(0 if s["outcomes"].get("dashdish-1") == "completed" else 1)
PY
echo "[chain] smoke OK"
sleep 30

echo "[chain] expert study: sonnet, MAX effort, 2h cap"
python3 runner.py p4study --arm expert --effort max --timeout 7200 \
  || { echo "[chain] ABORT: expert study failed"; exit 1; }
sleep 30

echo "[chain] full exp4a-experiential-fork (smoke task skips itself)"
python3 runner.py run --experiment exp4a-experiential-fork --buffer 45 \
  || { echo "[chain] ABORT: exp4a errored"; exit 1; }
sleep 45

echo "[chain] full exp4b-expert-fork"
python3 runner.py run --experiment exp4b-expert-fork --buffer 45 \
  || { echo "[chain] ABORT: exp4b errored"; exit 1; }

echo "[chain] ALL PHASE-4 RUNS COMPLETE"
python3 - <<'PY'
import json, glob, os
for arm in ("exp4a-experiential-fork", "exp4b-expert-fork"):
    p = 0; n = 0
    for d in sorted(glob.glob("data/%s/*_r1" % arm)):
        e = json.load(open(os.path.join(d, "evaluation.json")))
        n += 1; p += bool(e.get("passed"))
    print("[chain] %s: %d/%d PASS" % (arm, p, n))
PY

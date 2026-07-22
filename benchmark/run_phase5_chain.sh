#!/bin/bash
# Phase-5 chain: wait for recipes -> leakage audit -> wait for OCIC (Brave) ->
# atomic warm-ups -> exp5a -> exp5b -> exp5c -> exp5d. Hard-aborts on any gate.
set -u
cd "$(dirname "$0")"
GEN=~/.bench_rollouts/p5_recipegen

echo "[p5] waiting for recipe files from the isolated generator"
for i in $(seq 1 240); do
  [ -f "$GEN/RECIPE_dashdish.md" ] && [ -f "$GEN/RECIPE_zilloft.md" ] && [ -f "$GEN/RECIPE_combined.md" ] && break
  if ! pgrep -f "p5_recipegen.sh" >/dev/null 2>&1 && ! pgrep -f "cat /tmp/p5_prompt.txt" >/dev/null 2>&1; then
    # generator process gone; give the FS a beat then check once more
    sleep 5
    [ -f "$GEN/RECIPE_combined.md" ] && break
    echo "[p5] ABORT: generator died without producing all three recipes"; exit 1
  fi
  sleep 20
done
[ -f "$GEN/RECIPE_combined.md" ] || { echo "[p5] ABORT: recipes never appeared"; exit 1; }
echo "[p5] recipes present"

echo "[p5] leakage audit (test-set identifiers must not appear)"
python3 - <<'PY' || exit 1
import sys, glob
TEST_STRINGS = ["Biryani", "Mashaallah", "Souvla", "DragonEats", "Mushroom Swiss",
                "Express Delivery", "Bacon Double", "David Smith", "davidsmith",
                "555-333-7890", "150,000", "dashdish-1", "dashdish-2", "dashdish-7",
                "dashdish-8", "dashdish-10", "dashdish-11", "zilloft-2", "zilloft-3",
                "zilloft-5", "zilloft-6", "zilloft-9", "zilloft-10"]
import os
gen = os.path.expanduser("~/.bench_rollouts/p5_recipegen")
bad = []
for f in ("RECIPE_dashdish.md", "RECIPE_zilloft.md", "RECIPE_combined.md"):
    txt = open(os.path.join(gen, f)).read()
    words = len(txt.split())
    print("  %s: %d words" % (f, words))
    for s in TEST_STRINGS:
        if s.lower() in txt.lower():
            bad.append((f, s))
if bad:
    print("  LEAKAGE HITS:", bad); sys.exit(1)
print("  audit clean")
PY
echo "[p5] copying recipes into environments/recipes/"
mkdir -p environments/recipes
cp "$GEN"/RECIPE_dashdish.md "$GEN"/RECIPE_zilloft.md "$GEN"/RECIPE_combined.md environments/recipes/

echo "[p5] waiting for OCIC (Brave) to come up"
for i in $(seq 1 240); do
  python3 runner.py preflight >/tmp/p5_preflight.out 2>&1 && break
  grep -q "FAIL OCIC" /tmp/p5_preflight.out && sleep 30 || { cat /tmp/p5_preflight.out; echo "[p5] ABORT: preflight failed for a non-OCIC reason"; exit 1; }
done
python3 runner.py preflight >/dev/null 2>&1 || { echo "[p5] ABORT: preflight never passed"; exit 1; }
echo "[p5] preflight PASS"

echo "[p5] atomic warm-ups"
python3 runner.py p5warmup || { echo "[p5] ABORT: warmups failed"; exit 1; }
sleep 30

for EXP in exp5a-recipe-site exp5b-recipe-single exp5c-atomic-warmup exp5d-warmup-recipe; do
  echo "[p5] $(date '+%H:%M:%S') running $EXP"
  python3 runner.py run --experiment "$EXP" --buffer 45 || { echo "[p5] ABORT: $EXP errored"; exit 1; }
  sleep 45
done

echo "[p5] ALL PHASE-5 ARMS COMPLETE"
python3 - <<'PY'
import json, glob, os
for arm in ("exp5a-recipe-site", "exp5b-recipe-single", "exp5c-atomic-warmup", "exp5d-warmup-recipe"):
    p = n = 0; run = 0.0
    for d in sorted(glob.glob("data/%s/*_r1" % arm)):
        ev = os.path.join(d, "evaluation.json")
        if os.path.isfile(ev):
            n += 1; p += bool(json.load(open(ev)).get("passed"))
            t = json.load(open(os.path.join(d, "timing.json")))["attempts"][-1]
            run += (t["t_run_end"] - t["t_run_start"]) / 60
    print("[p5] %s: %d/%d PASS, %.0f min run" % (arm, p, n, run))
PY

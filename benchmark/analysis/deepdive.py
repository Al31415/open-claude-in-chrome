#!/usr/bin/env python3
"""Deep-dive: harness-latency paired tests, per-task diffs, failure matrix,
docs-reading behavior in 3c/3d, dashdish-8 status, amortization series."""
import json, os, itertools, statistics

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
ORDER = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))["test_order"]

def perm_p(diffs):
    n = len(diffs); obs = abs(sum(diffs) / n); cnt = 0
    for signs in itertools.product((1, -1), repeat=n):
        if abs(sum(d * g for d, g in zip(diffs, signs)) / n) >= obs - 1e-12: cnt += 1
    return cnt / 2 ** n

print("=" * 72)
print("A. HARNESS LATENCY (per-browser-action round-trip), paired by task")
for a, b, label in [("exp1a-fixed-chrome", "exp1b-cinc-cold", "fixed-chrome vs cinc (same browser)"),
                    ("exp1a-fixed-brave", "exp1b-cinc-cold", "fixed-brave vs cinc"),
                    ("exp1a-fixed-chrome", "exp1a-chrome", "fixed-chrome vs PRE-fix chrome")]:
    for metric in ("median_action_s", "total_action_s"):
        pairs = [(H[a][t].get(metric), H[b][t].get(metric)) for t in ORDER
                 if H[a][t].get(metric) is not None and H[b][t].get(metric) is not None]
        d = [x - y for x, y in pairs]
        wins = sum(1 for x in d if x < 0)
        print(f"  {label:38s} {metric:16s} n={len(d)} "
              f"A={statistics.mean([x for x,_ in pairs]):7.2f} B={statistics.mean([y for _,y in pairs]):7.2f} "
              f"diff={statistics.mean(d):+7.2f} A-faster {wins}/{len(d)} p_perm={perm_p(d):.4f}")

print()
print("=" * 72)
print("B. PER-TASK RUN-TIME DIFFS (min), key comparisons")
for a, b in [("exp1a-fixed-chrome", "exp1b-cinc-cold"), ("exp1a-fixed-brave", "exp1b-cinc-cold"),
             ("exp3c-analysis", "exp1a-fixed-brave")]:
    print(f"  -- {a} minus {b}")
    for t in ORDER:
        ra, rb = H[a][t], H[b][t]
        pa = "P" if ra["passed"] else "F"; pb = "P" if rb["passed"] else "F"
        print(f"     {t:14s} {ra['run_min']:5.1f}({pa}) vs {rb['run_min']:5.1f}({pb})  diff {ra['run_min']-rb['run_min']:+6.2f}")

print()
print("=" * 72)
print("C. FAILURE MATRIX (post-fix arms + cinc)")
arms = ["exp1a-fixed-chrome", "exp1a-fixed-brave", "exp1b-cinc-cold",
        "exp3b-brave", "exp3c-analysis", "exp3d-experiential-analysis"]
hdr = "  task           " + "  ".join(a.replace("exp", "").replace("-experiential", "-exp")[:12].ljust(12) for a in arms)
print(hdr)
for t in ORDER:
    row = f"  {t:14s} "
    for a in arms:
        row += ("  " + ("." if H[a][t]["passed"] else "FAIL").ljust(12))
    print(row)

print()
print("=" * 72)
print("D. DASHDISH-8 STATUS ACROSS ALL 12 ARMS")
for a in H:
    r = H[a].get("dashdish-8")
    if r: print(f"  {a:30s} {'PASS' if r['passed'] else 'FAIL'} run={r['run_min']}min turns={r.get('turns')}")

print()
print("=" * 72)
print("E. DOCS-READING BEHAVIOR in 3c/3d (Read of experience files, first N turns)")
for arm in ("exp3c-analysis", "exp3d-experiential-analysis"):
    reads = 0; read_before_browser = 0
    for t in ORDER:
        p = os.path.join(BENCH, "data", arm, f"{t}_r1", "trajectory.jsonl")
        seen_read = False; seen_browser = False; this_reads = False
        for line in open(p):
            try: o = json.loads(line)
            except Exception: continue
            if o.get("type") != "assistant": continue
            for bblk in (o.get("message") or {}).get("content", []):
                if not isinstance(bblk, dict) or bblk.get("type") != "tool_use": continue
                nm = bblk.get("name", ""); inp = json.dumps(bblk.get("input", {}))
                if nm == "Read" and ("ANALYSIS" in inp or "experience" in inp):
                    this_reads = True
                    if not seen_browser: seen_read = True
                if "claude-in-chrome" in nm: seen_browser = True
        reads += this_reads; read_before_browser += (this_reads and seen_read)
    print(f"  {arm:30s} read docs in {reads}/12 tasks; read BEFORE first browser action in {read_before_browser}/12")

print()
print("=" * 72)
print("F. AMORTIZATION SERIES (cumulative run_min in split order) -> analysis/amortization.json")
series = {}
for a in ["exp1a-fixed-chrome", "exp1a-fixed-brave", "exp1b-cinc-cold",
          "exp3c-analysis", "exp3d-experiential-analysis", "exp3b-brave",
          "exp1a-ocic-cold", "exp1a-chrome", "exp2a-experiential", "exp2b-expert",
          "exp3a-code", "exp3b-code-analysis"]:
    cum = 0.0; pts = []
    for t in ORDER:
        cum += H[a][t]["run_min"]; pts.append(round(cum, 2))
    series[a] = pts
json.dump({"order": ORDER, "series": series}, open(os.path.join(BENCH, "analysis", "amortization.json"), "w"), indent=1)
for a, pts in series.items(): print(f"  {a:30s} final={pts[-1]:6.1f}min")

print()
print("=" * 72)
print("G. ZILLOFT-10 in 3d (the 121-turn failure): last narration lines")
p = os.path.join(BENCH, "data", "exp3d-experiential-analysis", "zilloft-10_r1", "trajectory.jsonl")
texts = []
for line in open(p):
    try: o = json.loads(line)
    except Exception: continue
    if o.get("type") == "assistant":
        for bblk in (o.get("message") or {}).get("content", []):
            if isinstance(bblk, dict) and bblk.get("type") == "text" and bblk.get("text", "").strip():
                texts.append(" ".join(bblk["text"].split()))
print(f"  {len(texts)} narration blocks; goal + last 6:")
gp = os.path.join(BENCH, "data", "exp3d-experiential-analysis", "zilloft-10_r1", "prompt.txt")
goal = [l for l in open(gp).read().splitlines() if l.strip()][-3:]
print("  GOAL tail:", " / ".join(goal)[:200])
for s in texts[-6:]: print("   -", s[:170])

#!/usr/bin/env python3
"""Harvest per-task metrics across all benchmark arms into one tidy JSON.

Output: analysis/harvest.json
  {arm: {task: {passed, run_min, run_s, setup_s, replays, turns, steps,
                execute_code, browser_calls, mean_action_s, median_action_s,
                p90_action_s}}}

Definitions:
- run_s: final attempt t_run_end - t_run_start (the attempt that produced the
  evaluated trajectory). replays = len(attempts) - 1.
- turns: assistant messages in trajectory.jsonl.
- browser action latency: for each browser MCP tool_use, the wall time from the
  assistant message carrying the tool_use to the user message carrying the
  matching tool_result (harness round-trip incl. CDP + extension + transport,
  excludes model thinking of the NEXT turn). Timestamps from trace records.
"""
import json, os, re, statistics, sys

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BENCH, "data")
MAN = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))
ORDER = MAN["test_order"]

ARMS = [
    # post-fix core
    "exp1a-fixed-chrome", "exp1a-fixed-brave", "exp3c-analysis",
    "exp3d-experiential-analysis", "exp3b-brave",
    "exp2a-fixed-brave", "exp2b-fixed-brave",
    "exp4a-experiential-fork", "exp4b-expert-fork",
    "exp5a-recipe-site", "exp5b-recipe-single", "exp5c-atomic-warmup", "exp5d-warmup-recipe",
    # cinc comparison arm (official extension, chrome) + 2026-07-16 control
    "exp1b-cinc-cold", "exp1b-cinc-rerun", "exp1b-cinc-parity",
    # historical pre-fix
    "exp1a-ocic-cold", "exp1a-chrome", "exp2a-experiential", "exp2b-expert",
    "exp3a-code", "exp3b-code-analysis",
    # phase 7: recording-system comparison (OCIC raw recordings vs cowork
    # artifacts), same six train sessions captured simultaneously by both.
    # 7a/7b replay the phase-3 regime, 7c/7d the 5b regime.
    "exp7a-ocic-analysis", "exp7b-cowork-analysis",
    "exp7c-ocic-recipe", "exp7d-cowork-recipe",
]

BROWSER_TOOL = re.compile(r"mcp__(open-claude-in-chrome[^_]*|claude-in-chrome)__")

def parse_ts(v):
    # trace timestamps are ISO strings or epoch floats depending on writer
    if isinstance(v, (int, float)):
        return float(v) / (1000.0 if v > 1e12 else 1.0)
    if isinstance(v, str):
        try:
            import datetime as dt
            return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    return None

def traj_metrics(path, since_ts=None, run_start=None):
    """since_ts: ignore records before this epoch (fork arms: the study prefix
    is embedded in the forked transcript; slice to the rollout's own records).
    run_start: epoch for first-browser-action latency."""
    turns = 0; ec = 0
    lat = []
    pending = {}
    first_action_ts = None
    exp_reads = 0
    if not os.path.isfile(path):
        return {}
    for line in open(path):
        line = line.strip()
        if not line: continue
        try: o = json.loads(line)
        except Exception: continue
        t = o.get("type"); ts = parse_ts(o.get("timestamp"))
        if since_ts is not None and (ts is None or ts < since_ts):
            continue
        msg = o.get("message") or {}
        content = msg.get("content")
        if t == "assistant":
            turns += 1
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        name = b.get("name", "")
                        if name.endswith("__execute_code"): ec += 1
                        inp = json.dumps(b.get("input", {}) or {})
                        if name in ("Read", "Grep", "Glob") and ("experience" in inp or "notes" in inp or "ANALYSIS" in inp):
                            exp_reads += 1
                        if BROWSER_TOOL.match(name) and ts is not None:
                            pending[b.get("id")] = ts
                            if first_action_ts is None: first_action_ts = ts
        elif t == "user" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    tid = b.get("tool_use_id")
                    if tid in pending and ts is not None:
                        dt_s = ts - pending.pop(tid)
                        if 0 <= dt_s < 300: lat.append(dt_s)
    out = {"turns": turns, "execute_code_traj": ec, "browser_calls": len(lat),
           "experience_reads": exp_reads}
    if first_action_ts is not None and run_start is not None:
        out["first_action_s"] = round(first_action_ts - run_start, 1)
    if lat:
        lat.sort()
        out["mean_action_s"] = round(statistics.mean(lat), 3)
        out["median_action_s"] = round(statistics.median(lat), 3)
        out["p90_action_s"] = round(lat[int(0.9 * (len(lat) - 1))], 3)
        out["total_action_s"] = round(sum(lat), 1)
    return out

def steps_and_ec_from_log(arm):
    """steps + execute_code per task from runner logs (authoritative for ec)."""
    import glob
    res = {}
    for lg in sorted(glob.glob(os.path.join(BENCH, "logs", arm + "_*.log"))):
        cur = None
        for ln in open(lg):
            m = re.search(r"ROLLOUT \d+/\d+ (\S+) attempt", ln)
            if m: cur = m.group(1)
            m = re.search(r"teardown ok.*steps (\d+), execute_code (\d+)", ln)
            if m and cur:
                res[cur] = {"steps": int(m.group(1)), "execute_code": int(m.group(2))}
    return res

harvest = {}
for arm in ARMS:
    d = os.path.join(DATA, arm)
    if not os.path.isdir(d):
        continue
    logmeta = steps_and_ec_from_log(arm)
    arm_out = {}
    for task in ORDER + (MAN.get("train_order", []) if arm == "gen-experiential" else []):
        rd = os.path.join(d, f"{task}_r1")
        ev_p = os.path.join(rd, "evaluation.json")
        tm_p = os.path.join(rd, "timing.json")
        if not os.path.isfile(ev_p):
            continue
        row = {}
        ev = json.load(open(ev_p))
        row["passed"] = bool(ev.get("passed"))
        run_start = None
        if os.path.isfile(tm_p):
            tm = json.load(open(tm_p))
            at = tm["attempts"][-1]
            run_start = at["t_run_start"]
            row["run_s"] = round(at["t_run_end"] - at["t_run_start"], 1)
            row["run_min"] = round(row["run_s"] / 60.0, 2)
            row["setup_s"] = round(at.get("t_setup_end", 0) - at.get("t_setup_start", 0), 1)
            row["replays"] = len(tm["attempts"]) - 1
        is_fork = arm.startswith("exp4")
        since = (run_start - 30) if (is_fork and run_start) else None
        row.update(traj_metrics(os.path.join(rd, "trajectory.jsonl"),
                                since_ts=since, run_start=run_start))
        row.update(logmeta.get(task, {}))
        if is_fork:
            # log-derived steps/ec count the whole forked file (study prefix
            # included); the sliced trajectory values are the rollout's own.
            row["execute_code"] = row.get("execute_code_traj", 0)
            row["steps"] = row.get("browser_calls", row.get("steps", 0))
        arm_out[task] = row
    harvest[arm] = arm_out

out_p = os.path.join(BENCH, "analysis", "harvest.json")
json.dump(harvest, open(out_p, "w"), indent=1)
print("wrote", out_p)
for arm, rows in harvest.items():
    n = len(rows); p = sum(1 for r in rows.values() if r.get("passed"))
    rt = sum(r.get("run_s", 0) for r in rows.values()) / 60.0
    acts = [r.get("median_action_s") for r in rows.values() if r.get("median_action_s") is not None]
    ma = round(statistics.median(acts), 3) if acts else None
    print(f"  {arm:30s} n={n:2d} pass={p:2d} total_run={rt:5.1f}min med_action={ma}")

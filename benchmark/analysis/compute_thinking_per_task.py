#!/usr/bin/env python3
"""Per-task, per-arm total estimated thinking tokens, for the thinking-ratio
chart (parallel to the turns/latency ratio-decay charts). Reuses the same
residual-estimation method as thinking_breakdown.json (real output_tokens
minus estimated text/tool-use tokens, 4 chars/token), but at per-task
granularity instead of per-arm aggregate, and the same last-marker slicing
used everywhere else in this deck to drop forked/prior-session content from
4a/6a/6b.

One real turn can be split across multiple JSONL "assistant" records (one per
content block - thinking, tool_use, text each log separately) that share the
same message.id and the same (real, exact) usage.output_tokens; must group by
id and count output_tokens once per id, not once per record, or turns get
double-counted. Writes thinking_per_task.json: {arm: {task: total_think}}."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
DATA = os.path.join(BENCH, "data")

EXP_DIR = {
    "1a": "exp1b-cinc-parity", "1b": "exp1a-fixed-chrome", "1c": "exp1a-fixed-brave",
    "2a": "exp2a-fixed-brave", "2b": "exp2b-fixed-brave",
    "3a": "exp3d-experiential-analysis", "3b": "exp3c-analysis",
    "4a": "exp4a-experiential-fork", "4b": "exp4b-expert-fork",
    "5a": "exp5b-recipe-single", "5b": "exp5a-recipe-site",
    "6a": "exp5c-atomic-warmup", "6b": "exp5d-warmup-recipe",
}
TASKS = ["dashdish-11", "dashdish-10", "zilloft-3", "dashdish-7", "dashdish-1",
         "dashdish-2", "dashdish-8", "zilloft-6", "zilloft-9", "zilloft-10",
         "zilloft-5", "zilloft-2"]

def msg_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                return c.get("text", "")
    return ""

def last_marker_idx(records):
    idx = -1
    for i, d in enumerate(records):
        if d.get("type") != "user":
            continue
        t = msg_text(d.get("message", {}).get("content"))
        if t.startswith("[BENCHMARK ROLLOUT"):
            idx = i
    return idx

def task_thinking(path):
    if not os.path.exists(path):
        return None
    records = [json.loads(l) for l in open(path)]
    start = last_marker_idx(records)
    turns = {}  # msg.id -> {"out": int, "text_chars": int, "tool_chars": int}
    for i, d in enumerate(records):
        if i <= start or d.get("type") != "assistant":
            continue
        msg = d.get("message", {})
        mid = msg.get("id")
        if mid is None:
            continue
        t = turns.setdefault(mid, {"out": msg.get("usage", {}).get("output_tokens", 0),
                                    "text_chars": 0, "tool_chars": 0})
        for c in msg.get("content", []):
            if c.get("type") == "text":
                t["text_chars"] += len(c.get("text", ""))
            elif c.get("type") == "tool_use":
                t["tool_chars"] += len(json.dumps(c.get("input", {})))
    total = 0.0
    for t in turns.values():
        est = (t["text_chars"] + t["tool_chars"]) / 4
        total += max(0.0, t["out"] - est)
    return total

result = {}
for arm, expdir in EXP_DIR.items():
    result[arm] = {}
    for task in TASKS:
        path = os.path.join(DATA, expdir, f"{task}_r1", "trajectory.jsonl")
        v = task_thinking(path)
        if v is not None:
            result[arm][task] = v
    print(f"{arm:4} ({expdir}): {len(result[arm])}/12 tasks, "
          f"total think={sum(result[arm].values()):.0f}")

out_path = os.path.join(HERE, "thinking_per_task.json")
json.dump(result, open(out_path, "w"), indent=1)
print("wrote", out_path)

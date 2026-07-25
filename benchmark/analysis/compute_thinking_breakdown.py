#!/usr/bin/env python3
"""Per-arm aggregate thinking-token breakdown, for latency_thinking.png (the
100%-stacked bar: think/text/tool share of real output tokens, per arm).
Same residual-estimation method and same last-marker slicing as
compute_thinking_per_task.py, just summed to arm level instead of per-task.
There was no generator for thinking_breakdown.json in this repo (it predates
the current analysis/ layout); this reconstructs it from the identical method
so it can be regenerated whenever the underlying rollouts change.
Writes thinking_breakdown.json: {arm: {think,text,tool,real,turns}}."""
import json, os

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

def arm_breakdown(expdir):
    turns = {}  # msg.id -> {"out","text_chars","tool_chars"}, pooled across all 12 tasks
    for task in TASKS:
        path = os.path.join(DATA, expdir, f"{task}_r1", "trajectory.jsonl")
        if not os.path.exists(path):
            continue
        records = [json.loads(l) for l in open(path)]
        start = last_marker_idx(records)
        for i, d in enumerate(records):
            if i <= start or d.get("type") != "assistant":
                continue
            msg = d.get("message", {})
            mid = msg.get("id")
            if mid is None:
                continue
            key = (task, mid)  # message ids are only unique within one trajectory file
            t = turns.setdefault(key, {"out": msg.get("usage", {}).get("output_tokens", 0),
                                        "text_chars": 0, "tool_chars": 0})
            for c in msg.get("content", []):
                if c.get("type") == "text":
                    t["text_chars"] += len(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    t["tool_chars"] += len(json.dumps(c.get("input", {})))
    think = text = tool = real = 0.0
    for t in turns.values():
        text_est = t["text_chars"] / 4
        tool_est = t["tool_chars"] / 4
        think_v = max(0.0, t["out"] - text_est - tool_est)
        think += think_v; text += text_est; tool += tool_est; real += t["out"]
    return {"think": round(think, 2), "text": round(text, 2), "tool": round(tool, 2),
            "real": round(real, 1), "turns": len(turns)}

result = {}
for arm, expdir in EXP_DIR.items():
    result[arm] = arm_breakdown(expdir)
    r = result[arm]
    print(f"{arm:4} ({expdir}): think={r['think']:.0f} text={r['text']:.0f} "
          f"tool={r['tool']:.0f} real={r['real']:.0f} turns={r['turns']}")

out_path = os.path.join(HERE, "thinking_breakdown.json")
json.dump(result, open(out_path, "w"), indent=1)
print("wrote", out_path)

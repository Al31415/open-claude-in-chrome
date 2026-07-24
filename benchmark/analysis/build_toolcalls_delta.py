#!/usr/bin/env python3
"""Two side-by-side tornado charts: tool-call counts vs the cold baseline, as a
strict binary partition of every tool_use call in each rollout, classified by
exact name-prefix match, nothing inferred or eyeballed:
  - BROWSER: name starts with "mcp__open-claude-in-chrome-hybrid__" or
    "mcp__claude-in-chrome__" (computer, navigate, find, read_page, form_input,
    execute_code, ...) - an actual action taken in the browser.
  - NON-BROWSER: every other tool_use name (Bash, Read, Edit, Write,
    TaskCreate, TaskUpdate, ToolSearch, ...) - the reject set: whatever isn't
    a browser call. Not just "search"; it's the complement, whatever that
    turns out to contain.
Counts are read from the raw trajectory.jsonl for every arm x held-out-task
(see the counting pass that produced analysis/toolcalls.json), sliced to the
LAST "[BENCHMARK ROLLOUT]" marker so prep-phase activity (4a's forked prior
session, 4b's live study-session) is excluded the same way prep time is
excluded from task time in the runtime chart - this isolates task-focused
tool use from setup/internalization overhead. Both panels share the same arm
order (1a..6b) for direct row comparison; each keeps its own x-scale since
the two quantities differ by an order of magnitude. Chrome headless -> PNG."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "toolcalls.json")))
ORDER = D["order13"]
PA = D["per_arm"]
COLD_B, COLD_S = D["cold_browser"], D["cold_search"]

def deltas(key, cold):
    out = []
    for s in ORDER:
        v = PA[s][key]
        pct = (v - cold) / cold * 100 if cold else 0.0
        out.append((s, v, pct))
    return out

BROWSER = deltas("browser_mean", COLD_B)
NONBROWSER = deltas("search_mean", COLD_S)

def panel(title, sub, rows, cold_val, unit_lab):
    W = 700
    PL, PR, PT, RH, GAP = 46, 62, 78, 28, 7
    H = PT + RH * len(rows) + 42
    dmax = max(abs(p) for _, _, p in rows) * 1.12 or 1
    def X(v): return PL + (W - PL - PR) * (v + dmax) / (2 * dmax)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
    s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    s.append(f'<text x="{PL}" y="26" font-size="14.5" font-weight="700" fill="#1b1f24">{title}</text>')
    s.append(f'<text x="{PL}" y="42" font-size="10.5" fill="#8a929c">{sub}</text>')
    zx = X(0)
    s.append(f'<line x1="{zx:.1f}" y1="{PT-4}" x2="{zx:.1f}" y2="{PT+RH*len(rows)}" stroke="#c9c7c1" stroke-width="1.6"/>')
    s.append(f'<text x="{zx:.1f}" y="{PT+RH*len(rows)+16}" text-anchor="middle" font-size="10" fill="#8a929c">cold = {cold_val:.2f} {unit_lab}</text>')
    for i, (short, v, pct) in enumerate(rows):
        y = PT + i * RH
        x0, x1 = X(0), X(pct)
        pos = pct > 0
        col = "#c13a2e" if pos else "#0f8a5f"
        s.append(f'<text x="{PL-8}" y="{y+RH/2-GAP/2+4.5:.1f}" text-anchor="end" font-size="11" font-weight="700" fill="#1b1f24">{short}</text>')
        bx = min(x0, x1); bw = max(1.5, abs(x1 - x0))
        s.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{RH-GAP}" rx="2.5" fill="{col}" opacity="0.85"/>')
        lx = x1 + (5 if pos else -5)
        anchor = "start" if pos else "end"
        s.append(f'<text x="{lx:.1f}" y="{y+RH/2-GAP/2+4.5:.1f}" text-anchor="{anchor}" font-size="9.5" fill="#5b6571">{"+" if pct>0 else ""}{pct:.0f}%</text>')
    s.append('</svg>')
    return "\n".join(s)

left = panel("Browser tool calls vs. cold",
             "name starts mcp__(open-)claude-in-chrome(-hybrid)__* — an action taken in the browser, per task",
             BROWSER, COLD_B, "calls/task")
right = panel("Non-browser tool calls vs. cold",
              "everything NOT a browser call (Bash, Read, Edit, Write, TaskCreate/Update, ToolSearch), per task",
              NONBROWSER, COLD_S, "calls/task")

html = (f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff;display:flex}}'
        f'.p{{padding:0}}</style><div class="p">{left}</div><div class="p">{right}</div>')
open(os.path.join(HERE, "toolcalls_delta.html"), "w").write(html)
print("BROWSER:"); [print(f"  {s:4}{v:8.2f}  {p:+7.1f}%") for s, v, p in BROWSER]
print("NON-BROWSER:"); [print(f"  {s:4}{v:8.2f}  {p:+7.1f}%") for s, v, p in NONBROWSER]
print("wrote", os.path.join(HERE, "toolcalls_delta.html"))

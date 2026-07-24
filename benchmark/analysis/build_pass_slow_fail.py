#!/usr/bin/env python3
"""Static appendix version of the "Pass, slow, or fail" grid from
benchmark_capstone.html's accGrid() (every arm against every task). Reads the
capstone's own embedded data directly, so re-running build_capstone.py first
keeps this in sync with any upstream fix (e.g. the zilloft-10/3a rerun).
Green = passed, amber = passed but a within-arm time outlier for that arm
(robust MAD z-score > 1.5, computed per arm in build_capstone.py, not a fixed
time threshold), red = failed. Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
BY = {a["short"]: a for a in D["arms"]}
COLOR = D["dist_byleg"]["color"]
ORDER = D["dist_byleg"]["order"]
DIFF = D["diff"]
TASKS = [c["t"] for c in BY[ORDER[0]]["per_task"]]

GREEN, AMBER, RED = "#0f8a5f", "#ca8a04", "#c13a2e"
DIFFCOL = {"easy": "#0f8a5f", "medium": "#b45309", "hard": "#c13a2e"}

W = 1180
PL, PR, PT, PB = 176, 20, 108, 26
ROW_H = 27
COL_W = (W - PL - PR) / len(ORDER)
H = PT + ROW_H * len(TASKS) + PB

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="26" font-size="18" font-weight="700" fill="#1b1f24">Pass, slow, or fail: every arm against every task</text>')
s.append(f'<text x="{PL}" y="45" font-size="12.5" fill="#8a929c">Held-out test set, 12 tasks &#183; 13 arms &#183; accuracy is deterministically re-graded (see accuracy_regrade.py), not the raw LLM-judge verdict</text>')

ly = 62
legend = [(GREEN, "passed"), (AMBER, "passed, but slow for that arm (within-arm time outlier)"), (RED, "failed")]
lx = PL
for col, label in legend:
    s.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{col}"/>')
    s.append(f'<text x="{lx+16}" y="{ly}" font-size="10.5" fill="#5b6571">{label}</text>')
    lx += 26 + len(label) * 6.1 + 18

# column headers: arm short, colored, angled
hy = PT - 8
for i, short in enumerate(ORDER):
    cx = PL + i * COL_W + COL_W / 2
    s.append(f'<text x="{cx:.1f}" y="{hy}" text-anchor="start" font-size="11" font-weight="700" fill="{COLOR[short]}" transform="rotate(-40 {cx:.1f} {hy})">{short}</text>')

# gridlines between columns (faint) and row zebra striping
for i in range(len(ORDER) + 1):
    x = PL + i * COL_W
    s.append(f'<line x1="{x:.1f}" y1="{PT}" x2="{x:.1f}" y2="{PT + ROW_H*len(TASKS)}" stroke="#f2f1ed"/>')

for ti, t in enumerate(TASKS):
    y = PT + ti * ROW_H
    if ti % 2:
        s.append(f'<rect x="{PL}" y="{y:.1f}" width="{W-PL-PR:.1f}" height="{ROW_H}" fill="#faf9f6"/>')
    s.append(f'<circle cx="10" cy="{y+ROW_H/2+3.5:.1f}" r="3.5" fill="{DIFFCOL[DIFF[t]]}"/>')
    s.append(f'<text x="20" y="{y+ROW_H/2+4:.1f}" font-size="11.5" fill="#1b1f24">{t}</text>')
    for i, short in enumerate(ORDER):
        c = next(x for x in BY[short]["per_task"] if x["t"] == t)
        cx = PL + i * COL_W + COL_W / 2
        cy = y + ROW_H / 2 + 3.5
        if not c["passed"]:
            s.append(f'<text x="{cx:.1f}" y="{cy+1:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{RED}">F</text>')
        elif c.get("slow"):
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{AMBER}"><title>{short} &#183; {t}: passed, slow ({c["min"]}m)</title></circle>')
        else:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{GREEN}"><title>{short} &#183; {t}: passed ({c["min"]}m)</title></circle>')

s.append(f'<line x1="{PL}" y1="{PT}" x2="{W-PR}" y2="{PT}" stroke="#c9c7c1"/>')
s.append(f'<line x1="{PL}" y1="{PT+ROW_H*len(TASKS):.1f}" x2="{W-PR}" y2="{PT+ROW_H*len(TASKS):.1f}" stroke="#c9c7c1"/>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "pass_slow_fail.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("H =", H)
print("wrote", os.path.join(HERE, "pass_slow_fail.html"))

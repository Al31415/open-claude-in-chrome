#!/usr/bin/env python3
"""Run time per arm: preparation and task time, aligned (not stacked into one
continuous bar, and not exploded into one row per prep sub-step). Two rows per
arm instead: prep steps horizontally stacked into ONE bar (its sub-steps
concatenated, coloured by step type), directly above task time as its own
solid bar (arm colour) - both left-aligned at x=0 on the same minutes scale,
so prep duration and task duration read as directly comparable bars rather
than one offsetting the other. Prep segments use the exact same diagonal-hatch
pattern fill as the capstone's own renderPerf() (a rotated 6x6 line pattern in
the step's colour, thin solid border), so prep reads identically to how it
already reads inside benchmark_capstone.html; task time stays a normal solid
fill, the primary measured quantity. Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
COLOR = D["dist_byleg"]["color"]
SM = D["step_meta"]
ORDER = D["dist_byleg"]["order"]
BY = {a["short"]: a for a in D["arms"]}

W = 1120
PL, PR, PT, PB = 150, 100, 116, 66
BAR_H = 15
ROW_GAP = 2      # between the prep row and task row of the same arm
BLOCK_GAP = 10   # between one arm's block and the next
BLOCK_H = BAR_H * 2 + ROW_GAP
H = PT + BLOCK_H * len(ORDER) + BLOCK_GAP * (len(ORDER) - 1) + PB

xmax = max(max(a["prep_full"], a["total"]) for a in BY.values()) * 1.08
def X(v): return PL + (W - PL - PR) * v / xmax

# Phase-1 cold baseline, task time only (same "avg of 1a/1b/1c" convention used
# in every other chart in this deck - scalar_space.png, turns_delta.png, etc.)
COLD_TASK = sum(BY[s]["total"] for s in ("1a", "1b", "1c")) / 3

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# diagonal hatch pattern per prep-step type - identical technique to the
# capstone's renderPerf(): a 6x6 pattern rotated 45deg, bg #fbfbf9, a single
# diagonal line in the step colour at stroke-width 3
used_steps = []
for a in BY.values():
    for st in a["prep_steps"]:
        if st["k"] not in used_steps: used_steps.append(st["k"])
s.append('<defs>')
for k in used_steps:
    col = SM[k]["color"]
    s.append(f'<pattern id="hx-{k}" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
              f'<rect width="6" height="6" fill="#fbfbf9"/>'
              f'<line x1="0" y1="0" x2="0" y2="6" stroke="{col}" stroke-width="3"/>'
              f'</pattern>')
s.append('</defs>')

s.append(f'<text x="{PL}" y="26" font-size="18" font-weight="700" fill="#1b1f24">Run time per arm: preparation vs. task time, aligned</text>')
s.append(f'<text x="{PL}" y="45" font-size="12.5" fill="#8a929c">Both bars share one minutes scale, left-aligned at 0, so the two durations compare directly &#183; top = prep (stacked by step), bottom = task time (12 runs)</text>')

# legend: prep step types present + task-time note
lx = PL
ly = 62
for k in used_steps:
    s.append(f'<rect x="{lx:.1f}" y="{ly-9:.1f}" width="11" height="11" rx="2" fill="url(#hx-{k})" stroke="{SM[k]["color"]}" stroke-width="0.8"/>')
    s.append(f'<text x="{lx+16:.1f}" y="{ly:.1f}" font-size="10.5" fill="#5b6571">{SM[k]["label"]}</text>')
    lx += 18 + len(SM[k]["label"]) * 6.2 + 16
# task-time swatch on its own line (the prep-step row above already runs close
# to the canvas width, so appending it there clips it off-canvas)
ly2 = 80
s.append(f'<rect x="{PL:.1f}" y="{ly2-9:.1f}" width="11" height="11" rx="2" fill="#5b6571"/>')
s.append(f'<text x="{PL+16:.1f}" y="{ly2:.1f}" font-size="10.5" fill="#5b6571">task time (arm colour, solid)</text>')

# x gridlines
for g in range(0, int(xmax) + 1, 10):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT-4}" x2="{X(g):.1f}" y2="{H-PB+2}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+16}" text-anchor="middle" font-size="10" fill="#8a929c">{g}m</text>')

# Phase-1 baseline, drawn ONLY across the task-time row of each arm (not the
# prep row above it), so the reference is unambiguous: it applies to task time.
bx = X(COLD_TASK)
for i in range(len(ORDER)):
    y0 = PT + i * (BLOCK_H + BLOCK_GAP)
    y_task = y0 + BAR_H + ROW_GAP
    s.append(f'<line x1="{bx:.1f}" y1="{y_task-1.5:.1f}" x2="{bx:.1f}" y2="{y_task+BAR_H+1.5:.1f}" stroke="#b0483a" stroke-width="1.6" stroke-dasharray="4 3" opacity="0.85"/>')
s.append(f'<text x="{bx:.1f}" y="{PT-10:.1f}" text-anchor="middle" font-size="10.5" font-weight="700" fill="#b0483a">Phase-1 baseline (task time)</text>')
s.append(f'<text x="{bx:.1f}" y="{H-PB+32:.1f}" text-anchor="middle" font-size="9.5" fill="#a56a60">avg of 1a/1b/1c = {COLD_TASK:.1f}m</text>')

for i, short in enumerate(ORDER):
    a = BY[short]
    y0 = PT + i * (BLOCK_H + BLOCK_GAP)
    y_prep = y0
    y_task = y0 + BAR_H + ROW_GAP
    mid = (y_prep + y_task + BAR_H) / 2
    s.append(f'<text x="{PL-10:.1f}" y="{mid+4:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="#1b1f24">{short}</text>')

    # prep row: stacked sub-steps, left-aligned, diagonal-hatch fill (same
    # pattern technique as the capstone) so it reads distinctly from the
    # solid task-time bar below it
    x = X(0)
    for si, st in enumerate(a["prep_steps"]):
        w = X(st["m"]) - X(0)
        bw = max(1.5, w - (2 if si < len(a["prep_steps"]) - 1 else 0))
        col = SM[st["k"]]["color"]
        s.append(f'<rect x="{x:.1f}" y="{y_prep:.1f}" width="{bw:.1f}" height="{BAR_H}" rx="2" fill="url(#hx-{st["k"]})" stroke="{col}" stroke-width="0.8"/>')
        x += w
    if a["prep_steps"]:
        s.append(f'<text x="{x+5:.1f}" y="{y_prep+BAR_H-4:.1f}" font-size="10" fill="#5b6571">{a["prep_full"]:.0f}m</text>')
    else:
        s.append(f'<text x="{X(0):.1f}" y="{y_prep+BAR_H-4:.1f}" font-size="10" fill="#c9c7c1">0m</text>')

    # task row: single solid bar in arm colour
    tw = X(a["total"]) - X(0)
    s.append(f'<rect x="{X(0):.1f}" y="{y_task:.1f}" width="{max(1.2, tw):.1f}" height="{BAR_H}" rx="2" fill="{COLOR[short]}" opacity="0.9"/>')
    s.append(f'<text x="{X(0)+tw+5:.1f}" y="{y_task+BAR_H-4:.1f}" font-size="10" fill="#5b6571">{a["total"]:.1f}m</text>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "runtime_arm.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("H =", H)
for short in ORDER:
    a = BY[short]
    print(f"{short:4} prep={a['prep_full']:>5.1f}m  task={a['total']:>5.1f}m")
print("wrote", os.path.join(HERE, "runtime_arm.html"))

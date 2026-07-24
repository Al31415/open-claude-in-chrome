#!/usr/bin/env python3
"""Latency decomposition, part 1: harness overhead vs. model inference, per
turn. Harness overhead = med_action, the real measured wall-clock round-trip
for one browser action (click/screenshot/etc through the harness - program
execution + IPC hops, no model call involved). Model inference = the
remainder of the real measured seconds-per-turn (turncost.arms[].sec). One
stacked bar per arm, absolute seconds - harness renders as a thin sliver by
construction, which is the finding, not a styling choice. Chrome headless
-> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
COLOR = D["dist_byleg"]["color"]
ORDER = D["dist_byleg"]["order"]
BY = {a["short"]: a for a in D["arms"]}
TC = {a["short"]: a["sec"] for a in D["turncost"]["arms"]}
HARNESS_COL = "#8a929c"

rows = []
for s in ORDER:
    total = TC[s]
    harness = BY[s]["med_action"]
    infer = max(0.0, total - harness)
    rows.append((s, harness, infer, total))

W = 1120
PL, PR, PT, PB = 60, 190, 78, 50
BAR_H, GAP = 26, 12
H = PT + (BAR_H + GAP) * len(rows) - GAP + PB + 20
xmax = max(r[3] for r in rows) * 1.08
def X(v): return PL + (W - PL - PR) * v / xmax

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
# diagonal hatch pattern for harness overhead - same technique as the prep
# steps in runtime_arm.png (6x6, rotated 45deg, bg #fbfbf9, coloured line)
s.append('<defs><pattern id="hx-harness" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
          f'<rect width="6" height="6" fill="#fbfbf9"/>'
          f'<line x1="0" y1="0" x2="0" y2="6" stroke="{HARNESS_COL}" stroke-width="3"/>'
          f'</pattern></defs>')
s.append(f'<text x="{PL}" y="26" font-size="18" font-weight="700" fill="#1b1f24">Per-turn latency: harness overhead vs. model inference</text>')
s.append(f'<text x="{PL}" y="45" font-size="12.5" fill="#8a929c">Real measured seconds per turn, stacked &#183; harness = med_action (one browser round-trip) &#183; inference = the rest &#183; harness is the thin sliver</text>')
ly = 62
s.append(f'<rect x="{PL}" y="{ly-9}" width="11" height="11" rx="2" fill="url(#hx-harness)" stroke="{HARNESS_COL}" stroke-width="0.8"/>')
s.append(f'<text x="{PL+16}" y="{ly}" font-size="10.5" fill="#5b6571">harness overhead (program + IPC round-trip)</text>')

for g in range(0, int(xmax) + 1, 2):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT-4}" x2="{X(g):.1f}" y2="{PT + (BAR_H+GAP)*len(rows)}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{PT + (BAR_H+GAP)*len(rows) + 16}" text-anchor="middle" font-size="10" fill="#8a929c">{g}s</text>')

for i, (short, harness, infer, total) in enumerate(rows):
    y = PT + i * (BAR_H + GAP)
    s.append(f'<text x="{PL-10:.1f}" y="{y+BAR_H/2+4:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="#1b1f24">{short}</text>')
    hw = X(harness) - X(0)
    s.append(f'<rect x="{X(0):.1f}" y="{y:.1f}" width="{max(1.5,hw):.1f}" height="{BAR_H}" fill="url(#hx-harness)" stroke="{HARNESS_COL}" stroke-width="0.8"/>')
    iw = X(total) - X(harness)
    s.append(f'<rect x="{X(harness):.1f}" y="{y:.1f}" width="{max(1.5,iw):.1f}" height="{BAR_H}" rx="2" fill="{COLOR[short]}" opacity="0.9"/>')
    pct = 100 * harness / total
    s.append(f'<text x="{X(total)+6:.1f}" y="{y+BAR_H/2+4:.1f}" font-size="11" fill="#5b6571">{total:.1f}s/turn &#183; harness {pct:.1f}%</text>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "latency_harness.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
for short, harness, infer, total in rows:
    print(f"{short:4} total={total:5.2f}s  harness={harness:5.3f}s ({100*harness/total:4.1f}%)  inference={infer:5.2f}s ({100*infer/total:4.1f}%)")
print("wrote", os.path.join(HERE, "latency_harness.html"))

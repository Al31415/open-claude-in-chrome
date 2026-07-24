#!/usr/bin/env python3
"""Standalone accuracy-by-arm bar chart (tasks passed of 12) for the writeup.
Same house style as the scalar-space intro: per-leg colours, a Phase-1 baseline
reference line, honest 0-12 axis (so the saturation reads). Chrome headless -> PNG."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
# corrected, grader-verified accuracy (see accuracy_regrade.py)
C = json.load(open(os.path.join(HERE, "accuracy_corrected.json")))
ORDER = C["order"]
COLOR = C["color"]
PASS = C["passed"]
NT = C["n_tasks"]  # held-out test set size

P1 = ["1a", "1b", "1c"]
base = sum(PASS[s] for s in P1) / len(P1)

W, H = 1120, 560
PL, PR, PT, PB = 60, 160, 68, 66
def Y(v): return PT + (H - PT - PB) * (NT - v) / NT
plotw = W - PL - PR
gap = 14
bw = (plotw - gap * (len(ORDER) - 1)) / len(ORDER)

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
# y gridlines + labels
for g in range(0, NT + 1, 3):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}</text>')
# baseline reference line (Phase-1 average). Label lives in the right margin, off
# the plot entirely, since the baseline value can coincide with any bar's height.
s.append(f'<line x1="{PL}" y1="{Y(base):.1f}" x2="{W-PR}" y2="{Y(base):.1f}" stroke="#b0483a" stroke-width="1.4" stroke-dasharray="6 5" opacity="0.8"/>')
s.append(f'<circle cx="{W-PR:.1f}" cy="{Y(base):.1f}" r="3" fill="#b0483a"/>')
s.append(f'<text x="{W-PR+10:.1f}" y="{Y(base)-6:.1f}" font-size="11.5" font-weight="700" fill="#b0483a">Phase-1 baseline</text>')
s.append(f'<text x="{W-PR+10:.1f}" y="{Y(base)+9:.1f}" font-size="10.5" fill="#a56a60">avg of 1a/1b/1c</text>')
s.append(f'<text x="{W-PR+10:.1f}" y="{Y(base)+22:.1f}" font-size="10.5" fill="#a56a60">= {base:.1f}/12</text>')
# bars
for i, sh in enumerate(ORDER):
    x = PL + i * (bw + gap)
    v = PASS[sh]
    y = Y(v)
    col = COLOR[sh]
    s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{Y(0)-y:.1f}" rx="3" fill="{col}"/>')
    s.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{col}">{v}</text>')
    s.append(f'<text x="{x+bw/2:.1f}" y="{Y(0)+18:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="#1b1f24">{sh}</text>')
# axis baseline
s.append(f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{W-PR}" y2="{Y(0):.1f}" stroke="#c9c7c1" stroke-width="1.2"/>')
# titles
s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">Accuracy by arm</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">tasks passed of {NT} (held-out test set) &#183; deterministically re-graded against ground truth</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">tasks passed (of {NT})</text>')
s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "accuracy_arm.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("baseline avg = %.2f/12" % base)
print("wrote", os.path.join(HERE, "accuracy_arm.html"))

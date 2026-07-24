#!/usr/bin/env python3
"""Standalone accuracy-by-phase bar chart (mean tasks passed of 12, per phase)
for the writeup. Deterministically re-graded data (see accuracy_regrade.py).
Bars use a sequential ramp (phases are ordinal, 1->6) rather than the per-arm
categorical palette, since a phase average is a different kind of quantity than
an arm. Individual member-arm values are plotted as dots on top of each bar so
the underlying spread stays visible - description only, no interpretation is
baked into the chart itself. Chrome headless -> PNG."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "accuracy_corrected.json")))
PASS = C["passed"]
PHASES = C["phases"]  # {"P1": ["1a","1b","1c"], ...}
NT = C["n_tasks"]
PORDER = ["P1", "P2", "P3", "P4", "P5", "P6"]

# sequential ramp, light -> dark (ordinal phase index, not a magnitude encoding)
RAMP = ["#c7d7ea", "#a3bfdd", "#7fa6cf", "#5b8dc1", "#3a70a8", "#1f4e80"]
PCOLOR = dict(zip(PORDER, RAMP))

mean = {p: sum(PASS[a] for a in mem) / len(mem) for p, mem in PHASES.items()}
base = mean["P1"]

W, H = 1120, 560
PL, PR, PT, PB = 60, 160, 68, 66
def Y(v): return PT + (H - PT - PB) * (NT - v) / NT
plotw = W - PL - PR
gap = 46
bw = (plotw - gap * (len(PORDER) - 1)) / len(PORDER)

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
for g in range(0, NT + 1, 3):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}</text>')
# Phase-1 reference line
s.append(f'<line x1="{PL}" y1="{Y(base):.1f}" x2="{W-PR}" y2="{Y(base):.1f}" stroke="#b0483a" stroke-width="1.4" stroke-dasharray="6 5" opacity="0.8"/>')
s.append(f'<circle cx="{W-PR:.1f}" cy="{Y(base):.1f}" r="3" fill="#b0483a"/>')
s.append(f'<text x="{W-PR+10:.1f}" y="{Y(base)-6:.1f}" font-size="11.5" font-weight="700" fill="#b0483a">Phase 1 mean</text>')
s.append(f'<text x="{W-PR+10:.1f}" y="{Y(base)+9:.1f}" font-size="10.5" fill="#a56a60">= {base:.1f}/12</text>')

for i, p in enumerate(PORDER):
    x = PL + i * (bw + gap)
    v = mean[p]
    y = Y(v)
    col = PCOLOR[p]
    s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{Y(0)-y:.1f}" rx="4" fill="{col}"/>')
    s.append(f'<text x="{x+bw/2:.1f}" y="{y-10:.1f}" text-anchor="middle" font-size="13.5" font-weight="700" fill="#1b1f24">{v:.2f}</text>')
    # member-arm dots + short labels, jittered across the bar width
    mem = PHASES[p]
    n = len(mem)
    for j, a in enumerate(mem):
        dx = (j + 0.5) / n * bw
        av = PASS[a]
        cx, cy = x + dx, Y(av)
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="#fff" stroke="#1b1f24" stroke-width="1.6"/>')
        s.append(f'<text x="{cx:.1f}" y="{Y(0)+18:.1f}" text-anchor="middle" font-size="10.5" fill="#5b6571">{a}={av}</text>')
    s.append(f'<text x="{x+bw/2:.1f}" y="{Y(0)+36:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="#1b1f24">{p}</text>')

s.append(f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{W-PR}" y2="{Y(0):.1f}" stroke="#c9c7c1" stroke-width="1.2"/>')
s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">Accuracy by phase</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">mean tasks passed of {NT}, averaged across each phase&#8217;s arms &#183; deterministically re-graded against ground truth</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">mean tasks passed (of {NT})</text>')
s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "accuracy_phase.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
for p in PORDER:
    print(p, PHASES[p], "->", [PASS[a] for a in PHASES[p]], "mean=%.2f" % mean[p])
print("wrote", os.path.join(HERE, "accuracy_phase.html"))

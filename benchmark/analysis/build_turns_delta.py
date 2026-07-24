#!/usr/bin/env python3
"""Standalone render of the capstone's turns-vs-cold tornado chart (Section 5,
turnDelta()) for the writeup: one horizontal bar per arm, signed delta in turns
against the Phase-1 cold mean. Same data, same per-leg colour-independent
red/green convention as the capstone. Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
T = D["turns"]
COLD = T["coldmean"]
# canonical 1a..6b order, matching the two segregated tool-call charts below this
# one in the writeup, so all three read as the same row-for-row arm sequence.
ORDER13 = ["1a", "1b", "1c", "2a", "2b", "3a", "3b", "4a", "4b", "5a", "5b", "6a", "6b"]
_by_short = {a["short"]: a for a in T["arms"]}
ARMS = [_by_short[s] for s in ORDER13]

W = 1120
PL, PR, PT, RH, GAP = 96, 130, 92, 30, 8
H = PT + RH * len(ARMS) + 46

dmax = max(abs(a["delta"]) for a in ARMS) * 1.15
def X(v): return PL + (W - PL - PR) * (v + dmax) / (2 * dmax)

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Efficiency: turns spent or saved versus the cold baseline</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">each arm\'s turn count vs. the Phase-1 cold mean ({COLD} turns/task) &#183; fewer turns = a more direct path to the answer</text>')

zx = X(0)
s.append(f'<line x1="{zx:.1f}" y1="{PT-4}" x2="{zx:.1f}" y2="{PT+RH*len(ARMS)}" stroke="#c9c7c1" stroke-width="2"/>')
s.append(f'<text x="{X(-dmax*.6):.1f}" y="{PT-10}" text-anchor="middle" font-size="11" fill="#0f8a5f">&#8592; fewer turns (more direct)</text>')
s.append(f'<text x="{X(dmax*.55):.1f}" y="{PT-10}" text-anchor="middle" font-size="11" fill="#c13a2e">more turns (extra steps) &#8594;</text>')
s.append(f'<text x="{zx:.1f}" y="{PT+RH*len(ARMS)+18}" text-anchor="middle" font-size="10.5" fill="#8a929c">cold = {COLD} turns</text>')

for i, a in enumerate(ARMS):
    y = PT + i * RH
    x0, x1 = X(0), X(a["delta"])
    pos = a["delta"] > 0
    col = "#c13a2e" if pos else "#0f8a5f"
    s.append(f'<text x="{PL-12}" y="{y+RH/2-GAP/2+5:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="#1b1f24">{a["short"]}</text>')
    bx = min(x0, x1); bw = max(2, abs(x1 - x0))
    s.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{RH-GAP}" rx="3" fill="{col}" opacity="0.85"/>')
    lx = x1 + (6 if pos else -6)
    anchor = "start" if pos else "end"
    pct = a["pct"]
    s.append(f'<text x="{lx:.1f}" y="{y+RH/2-GAP/2+5:.1f}" text-anchor="{anchor}" font-size="11" fill="#5b6571">{"+" if pct>0 else ""}{pct}%</text>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "turns_delta.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("cold mean:", COLD, "turns")
for a in ARMS:
    print(f"  {a['short']:>3}  {a['turns']:>5}  delta={a['delta']:+.1f}  pct={a['pct']:+d}%")
print("wrote", os.path.join(HERE, "turns_delta.html"))

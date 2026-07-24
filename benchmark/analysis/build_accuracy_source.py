#!/usr/bin/env python3
"""Standalone accuracy-by-source bar chart (tasks passed of 12), pairing each
phase's experiential arm against its expert-sourced counterpart (2a/2b, 3a/3b,
4a/4b - the only three phases where source is the single varying factor, other
knobs held fixed). Deterministically re-graded data (see accuracy_regrade.py).
Two-level categorical colour (experiential vs expert), not the per-arm palette,
since this chart's identity axis is the source factor, not the arm. Chrome
headless -> PNG. Label is descriptive only; no claim of cause is drawn on the
chart itself."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "accuracy_corrected.json")))
PASS = C["passed"]
NT = C["n_tasks"]

PAIRS = [("Phase 2", "raw mount", "2a", "2b"),
         ("Phase 3", "+ analysis", "3a", "3b"),
         ("Phase 4", "forked into context", "4a", "4b")]
COL_EXP, COL_EXPERT = "#c2703d", "#2f7a8c"  # experiential (warm) vs expert (cool)

exp_vals = [PASS[a] for _, _, a, _ in PAIRS]
expert_vals = [PASS[b] for _, _, _, b in PAIRS]
exp_mean = sum(exp_vals) / len(exp_vals)
expert_mean = sum(expert_vals) / len(expert_vals)

GROUPS = [(lab, sub, PASS[a], PASS[b]) for lab, sub, a, b in PAIRS]
GROUPS.append(("All 3 phases", "pooled mean", exp_mean, expert_mean))

W, H = 1120, 560
PL, PR, PT, PB = 60, 40, 74, 80
def Y(v): return PT + (H - PT - PB) * (NT - v) / NT
plotw = W - PL - PR
ngroups = len(GROUPS)
gpad = 54
gw = (plotw - gpad * (ngroups - 1)) / ngroups
bw = gw * 0.38
bgap = gw * 0.06

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
for g in range(0, NT + 1, 3):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}</text>')

for i, (lab, sub, va, vb) in enumerate(GROUPS):
    gx = PL + i * (gw + gpad)
    xa, xb = gx, gx + bw + bgap
    ya, yb = Y(va), Y(vb)
    sep = (i == len(GROUPS) - 1)
    if sep:
        s.append(f'<line x1="{gx-gpad/2:.1f}" y1="{PT-6}" x2="{gx-gpad/2:.1f}" y2="{Y(0)+8:.1f}" stroke="#e4e2db" stroke-width="1.2"/>')
    s.append(f'<rect x="{xa:.1f}" y="{ya:.1f}" width="{bw:.1f}" height="{Y(0)-ya:.1f}" rx="3" fill="{COL_EXP}"/>')
    s.append(f'<text x="{xa+bw/2:.1f}" y="{ya-8:.1f}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{COL_EXP}">{va:.2f}' + ('' if isinstance(va,int) or va==int(va) else '') + '</text>')
    s.append(f'<rect x="{xb:.1f}" y="{yb:.1f}" width="{bw:.1f}" height="{Y(0)-yb:.1f}" rx="3" fill="{COL_EXPERT}"/>')
    s.append(f'<text x="{xb+bw/2:.1f}" y="{yb-8:.1f}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{COL_EXPERT}">{vb:.2f}' + '</text>')
    s.append(f'<text x="{gx+(bw*2+bgap)/2:.1f}" y="{Y(0)+22:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="#1b1f24">{lab}</text>')
    s.append(f'<text x="{gx+(bw*2+bgap)/2:.1f}" y="{Y(0)+37:.1f}" text-anchor="middle" font-size="10.5" fill="#8a929c">{sub}</text>')

# legend
lx, ly = PL, 60
s.append(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_EXP}"/>')
s.append(f'<text x="{lx+18}" y="{ly}" font-size="11.5" fill="#5b6571">Experiential source (agent\'s own past traces)</text>')
s.append(f'<rect x="{lx+330}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_EXPERT}"/>')
s.append(f'<text x="{lx+348}" y="{ly}" font-size="11.5" fill="#5b6571">Expert source (recorded human demonstrations)</text>')

s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Accuracy by source</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">tasks passed (of {NT})</text>')
s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "accuracy_source.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
for lab, sub, va, vb in GROUPS:
    print(f"{lab:14} experiential={va:.2f}  expert={vb:.2f}  gap={vb-va:+.2f}")
print("wrote", os.path.join(HERE, "accuracy_source.html"))

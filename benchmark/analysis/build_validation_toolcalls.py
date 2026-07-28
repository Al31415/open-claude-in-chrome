#!/usr/bin/env python3
"""Browser tool calls per task, expert source against experiential source,
paired by phase - the isolated view of the validation behaviour that
toolcalls_delta.png shows only against cold. Same three pairs as
accuracy_source.png (2a/2b, 3a/3b, 4a/4b: the phases where source is the one
varying factor) and the same two-level source palette, so the two charts read
as a set: that one is what the extra calls bought, this one is what they cost.
Dashed reference line is the phase-1 cold mean. Reads toolcalls.json (browser
= strict mcp__(open-)claude-in-chrome(-hybrid)__* prefix match, sliced from the
last task prompt). Chrome headless -> PNG."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "toolcalls.json")))
PER = T["per_arm"]
COLD = T["cold_browser"]

PAIRS = [("Phase 2", "raw mount", "2a", "2b"),
         ("Phase 3", "+ analysis", "3a", "3b"),
         ("Phase 4", "forked into context", "4a", "4b")]
COL_EXP, COL_EXPERT = "#c2703d", "#2f7a8c"   # experiential (warm) vs expert (cool)

GROUPS = [(lab, sub, PER[a]["browser_mean"], PER[b]["browser_mean"], a, b)
          for lab, sub, a, b in PAIRS]
ea = sum(g[2] for g in GROUPS) / len(GROUPS)
eb = sum(g[3] for g in GROUPS) / len(GROUPS)
GROUPS.append(("All 3 phases", "pooled mean", ea, eb, "", ""))

W, H = 1120, 580
PL, PR, PT, PB = 62, 132, 92, 82   # right margin parks the cold-line label clear of the bars
YMAX = 42
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / YMAX
plotw = W - PL - PR
gpad = 54
gw = (plotw - gpad * (len(GROUPS) - 1)) / len(GROUPS)
bw = gw * 0.38
bgap = gw * 0.06

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
for g in range(0, YMAX + 1, 7):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}</text>')

# phase-1 cold mean: the line every bar is being read against
s.append(f'<line x1="{PL}" y1="{Y(COLD):.1f}" x2="{W-PR+14:.1f}" y2="{Y(COLD):.1f}" '
         f'stroke="#5b6571" stroke-width="1.6" stroke-dasharray="8 5"/>')
s.append(f'<text x="{W-PR+20:.1f}" y="{Y(COLD)-2:.1f}" font-size="11" font-weight="700" fill="#5b6571">cold baseline</text>')
s.append(f'<text x="{W-PR+20:.1f}" y="{Y(COLD)+13:.1f}" font-size="11" fill="#8a929c">{COLD:.1f} calls/task</text>')

for i, (lab, sub, va, vb, aa, bb) in enumerate(GROUPS):
    gx = PL + i * (gw + gpad)
    xa, xb = gx, gx + bw + bgap
    ya, yb = Y(va), Y(vb)
    if i == len(GROUPS) - 1:
        s.append(f'<line x1="{gx-gpad/2:.1f}" y1="{PT-6}" x2="{gx-gpad/2:.1f}" y2="{Y(0)+8:.1f}" '
                 f'stroke="#e4e2db" stroke-width="1.2"/>')
    s.append(f'<rect x="{xa:.1f}" y="{ya:.1f}" width="{bw:.1f}" height="{Y(0)-ya:.1f}" rx="3" fill="{COL_EXP}"/>')
    s.append(f'<text x="{xa+bw/2:.1f}" y="{ya-8:.1f}" text-anchor="middle" font-size="12.5" '
             f'font-weight="700" fill="{COL_EXP}">{va:.1f}</text>')
    s.append(f'<rect x="{xb:.1f}" y="{yb:.1f}" width="{bw:.1f}" height="{Y(0)-yb:.1f}" rx="3" fill="{COL_EXPERT}"/>')
    s.append(f'<text x="{xb+bw/2:.1f}" y="{yb-8:.1f}" text-anchor="middle" font-size="12.5" '
             f'font-weight="700" fill="{COL_EXPERT}">{vb:.1f}</text>')
    # the gap is the finding, so it gets a bracket of its own above the pair
    top = min(ya, yb) - 30
    s.append(f'<path d="M {xa+bw/2:.1f} {top+10:.1f} L {xa+bw/2:.1f} {top:.1f} L {xb+bw/2:.1f} {top:.1f} '
             f'L {xb+bw/2:.1f} {top+10:.1f}" fill="none" stroke="#a8aeb6" stroke-width="1.2"/>')
    s.append(f'<text x="{gx+(bw*2+bgap)/2:.1f}" y="{top-6:.1f}" text-anchor="middle" font-size="12" '
             f'font-weight="700" fill="#5b6571">+{100*(vb-va)/va:.0f}%</text>')
    s.append(f'<text x="{gx+(bw*2+bgap)/2:.1f}" y="{Y(0)+22:.1f}" text-anchor="middle" font-size="13" '
             f'font-weight="700" fill="#1b1f24">{lab}</text>')
    s.append(f'<text x="{gx+(bw*2+bgap)/2:.1f}" y="{Y(0)+37:.1f}" text-anchor="middle" font-size="10.5" '
             f'fill="#8a929c">{sub}</text>')
    if aa:
        s.append(f'<text x="{xa+bw/2:.1f}" y="{Y(0)+52:.1f}" text-anchor="middle" font-size="10" '
                 f'fill="{COL_EXP}">{aa}</text>')
        s.append(f'<text x="{xb+bw/2:.1f}" y="{Y(0)+52:.1f}" text-anchor="middle" font-size="10" '
                 f'fill="{COL_EXPERT}">{bb}</text>')

lx, ly = PL, 74
s.append(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_EXP}"/>')
s.append(f'<text x="{lx+18}" y="{ly}" font-size="11.5" fill="#5b6571">Experiential source (agent\'s own past traces)</text>')
s.append(f'<rect x="{lx+330}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_EXPERT}"/>')
s.append(f'<text x="{lx+348}" y="{ly}" font-size="11.5" fill="#5b6571">Expert source (recorded human demonstrations)</text>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">'
         f'The cost of the validation behaviour: browser calls by source</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">'
         f'mean browser tool calls per task &#183; same three pairs as the accuracy-by-source chart, '
         f'source is the only factor that changes inside a pair</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" '
         f'transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">browser tool calls per task</text>')
s.append('</svg>')

open(os.path.join(HERE, "validation_toolcalls.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><title>validation tool calls</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
print(f"cold browser mean: {COLD:.2f} calls/task")
for lab, sub, va, vb, aa, bb in GROUPS:
    print(f"  {lab:14} experiential={va:5.1f} ({100*(va-COLD)/COLD:+3.0f}% vs cold)   "
          f"expert={vb:5.1f} ({100*(vb-COLD)/COLD:+3.0f}% vs cold)   pair gap={100*(vb-va)/va:+.0f}%")
print("wrote", os.path.join(HERE, "validation_toolcalls.html"))

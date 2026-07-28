#!/usr/bin/env python3
"""The agentic-search tax of phase 2, in the two places it actually shows up:
the non-browser tool calls the agent spends reading its own workspace, and how
long it takes before it touches the browser at all. Cold (phase-1 mean) against
2a and 2b, two panels on their own scales because one is a count and the other
is seconds. Reads toolcalls.json for the call counts (non-browser = every call
that is NOT a strict mcp__(open-)claude-in-chrome(-hybrid)__* match, sliced
from the last task prompt) and the capstone's per-arm first-action median for
the seconds. Per-arm palette, since this chart's identity axis is the arm.
Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
COLOR = D["dist_byleg"]["color"]
BY = {a["short"]: a for a in D["arms"]}
T = json.load(open(os.path.join(HERE, "toolcalls.json")))

COLD_CALLS = T["cold_search"]
COLD_FIRST = sum(BY[k]["first"] for k in ("1a", "1b", "1c")) / 3
COL_COLD = "#a8aeb6"

PANELS = [
    {"title": "Reading the workspace", "unit": "non-browser tool calls per task",
     "fmt": "{:.2f}", "ymax": 7.0, "step": 1.0,
     "bars": [("cold", COLD_CALLS, COL_COLD), ("2a", T["per_arm"]["2a"]["search_mean"], COLOR["2a"]),
              ("2b", T["per_arm"]["2b"]["search_mean"], COLOR["2b"])]},
    {"title": "Getting to the first browser action", "unit": "median seconds to the first browser call",
     "fmt": "{:.1f}s", "ymax": 24.0, "step": 4.0,
     "bars": [("cold", COLD_FIRST, COL_COLD), ("2a", BY["2a"]["first"], COLOR["2a"]),
              ("2b", BY["2b"]["first"], COLOR["2b"])]},
]

W, H = 1120, 540
PL, PR, PT, PB = 62, 40, 116, 86   # top margin clears the chart subtitle above the panel headers
GX = 96
PANW = (W - PL - PR - GX) / 2

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">'
         f'The agentic-search tax: what mounting the sources on disk cost</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">'
         f'phase-2 arms against the phase-1 cold mean &#183; the prior experience is in the workspace, so the agent has to go read it first</text>')

for pi, p in enumerate(PANELS):
    ox = PL + pi * (PANW + GX)
    def Y(v, p=p): return PT + (H - PT - PB) * (p["ymax"] - v) / p["ymax"]
    g = 0.0
    while g <= p["ymax"] + 1e-9:
        s.append(f'<line x1="{ox:.1f}" y1="{Y(g):.1f}" x2="{ox+PANW:.1f}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
        s.append(f'<text x="{ox-8:.1f}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="10" fill="#a8aeb6">{g:g}</text>')
        g += p["step"]
    # cold reference carried across the panel so each bar is read against it
    cold = p["bars"][0][1]
    s.append(f'<line x1="{ox:.1f}" y1="{Y(cold):.1f}" x2="{ox+PANW:.1f}" y2="{Y(cold):.1f}" '
             f'stroke="#5b6571" stroke-width="1.4" stroke-dasharray="7 5"/>')
    n = len(p["bars"])
    slot = PANW / n
    bw = slot * 0.46
    for i, (lab, val, col) in enumerate(p["bars"]):
        cx = ox + slot * (i + 0.5)
        x = cx - bw / 2
        y = Y(val)
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{Y(0)-y:.1f}" rx="3" fill="{col}"/>')
        s.append(f'<text x="{cx:.1f}" y="{y-9:.1f}" text-anchor="middle" font-size="13" '
                 f'font-weight="700" fill="{col}">{p["fmt"].format(val)}</text>')
        if i:
            mult = val / cold
            s.append(f'<text x="{cx:.1f}" y="{y-25:.1f}" text-anchor="middle" font-size="11.5" '
                     f'font-weight="700" fill="#c13a2e">{mult:.1f}&#215; cold</text>')
            s.append(f'<text x="{cx:.1f}" y="{Y(0)+38:.1f}" text-anchor="middle" font-size="10" '
                     f'fill="#8a929c">{100*(val-cold)/cold:+.0f}%</text>')
        s.append(f'<text x="{cx:.1f}" y="{Y(0)+22:.1f}" text-anchor="middle" font-size="13" '
                 f'font-weight="700" fill="#1b1f24">{lab}</text>')
    s.append(f'<text x="{ox:.1f}" y="{PT-34:.1f}" font-size="13.5" font-weight="700" fill="#1b1f24">{p["title"]}</text>')
    s.append(f'<text x="{ox:.1f}" y="{PT-18:.1f}" font-size="11" fill="#8a929c">{p["unit"]}</text>')

s.append('</svg>')
open(os.path.join(HERE, "search_tax.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><title>search tax</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
for p in PANELS:
    cold = p["bars"][0][1]
    print(p["title"] + " (" + p["unit"] + ")")
    for lab, val, _ in p["bars"]:
        extra = "" if val == cold else f"   {val/cold:.2f}x cold   {100*(val-cold)/cold:+.0f}%"
        print(f"   {lab:5} {val:8.2f}{extra}")
print("wrote", os.path.join(HERE, "search_tax.html"))

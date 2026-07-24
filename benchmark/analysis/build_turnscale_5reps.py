#!/usr/bin/env python3
"""Turn savings vs. baseline task length: one representative arm per phase
(2, 3, 4, 5), plus 6b (warm-up + recipe, the study's overall winner), linear
fit only, no separate baseline line (cold is the implicit 0% reference the
y-axis is already measured against). Representative = the more reliable
performer within each phase's pair: 2b/3b/4b (expert source, higher accuracy
than the experiential twin in each phase) and 5b (per-site recipe, the
cleaner/stronger fit of the two recipe-scope arms). Pure-python least-squares
linear fit (no numpy dependency). Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
L = D["turns"]["scale"]
COLOR = D["dist_byleg"]["color"]
ARMS = ["2b", "3b", "4b", "5b", "6b"]
LABEL = {"2b": "2b · raw mount (expert)", "3b": "3b · analysis mount (expert)",
         "4b": "4b · forked context (expert)", "5b": "5b · recipe (per-site)",
         "6b": "6b · warm-up + recipe (winner)"}

def linfit(xs, ys):
    n = len(xs)
    sx = sum(xs); sy = sum(ys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    b1 = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b0 = (sy - b1 * sx) / n
    pred = [b0 + b1 * x for x in xs]
    ybar = sy / n
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, pred))
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return b0, b1, r2

DATA = {}
for arm in ARMS:
    xs, ys = [], []
    for t in L["tasks"]:
        bt = t["bturns"]; sv = t["sv"].get(arm)
        if sv is None: continue
        xs.append(bt); ys.append(sv / bt * 100)
    b0, b1, r2 = linfit(xs, ys)
    DATA[arm] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2}
    print(f"{arm}: n={len(xs)}  slope={b1:+.3f} %/turn  intercept={b0:+.2f}%  R2={r2:.3f}")

W, H = 1300, 620
PL, PR, PT, PB = 66, 300, 70, 60
xmax = max(max(d["xs"]) for d in DATA.values()) * 1.05
ymin = min(min(d["ys"]) for d in DATA.values()) * 1.15
ymax = max(max(d["ys"]) for d in DATA.values()) * 1.15
def X(v): return PL + (W - PL - PR) * v / xmax
def Y(v): return PT + (H - PT - PB) * (ymax - v) / (ymax - ymin)

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Turns saved vs. task length: one arm per phase (2, 3, 4, 5), plus the winner (6b)</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">% turns saved vs. cold, plotted against each task\'s baseline (cold) turn count &#183; cold itself is the implicit 0% line &#183; one linear fit per arm</text>')

for g in range(0, int(xmax) + 1, 10):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="10" fill="#8a929c">{g}</text>')
ystep = 20
yg = ystep * (int(ymin) // ystep)
while yg <= ymax:
    s.append(f'<line x1="{PL}" y1="{Y(yg):.1f}" x2="{W-PR}" y2="{Y(yg):.1f}" stroke="#f7f6f2"/>')
    s.append(f'<text x="{PL-8:.1f}" y="{Y(yg)+3.5:.1f}" text-anchor="end" font-size="10" fill="#8a929c">{yg:+d}%</text>')
    yg += ystep
s.append(f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{W-PR}" y2="{Y(0):.1f}" stroke="#c9c7c1" stroke-width="1.6"/>')
s.append(f'<text x="{W-PR:.1f}" y="{Y(0)-6:.1f}" text-anchor="end" font-size="10.5" fill="#8a929c">cold (0%)</text>')
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-14}" text-anchor="middle" font-size="12" fill="#5b6571">baseline (cold) turns for the task</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">% turns saved vs. cold</text>')

for arm in ARMS:
    d = DATA[arm]; col = COLOR[arm]
    y0, y1 = d["b0"], d["b0"] + d["b1"] * xmax
    s.append(f'<line x1="{X(0):.1f}" y1="{Y(y0):.1f}" x2="{X(xmax):.1f}" y2="{Y(y1):.1f}" stroke="{col}" stroke-width="2.6" opacity="0.92"/>')
for arm in ARMS:
    d = DATA[arm]; col = COLOR[arm]
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5.5" fill="{col}" stroke="#fff" stroke-width="1.3" opacity="0.9"/>')

# line-end labels in the dedicated right margin (outside the plot), vertically
# decluttered so close endpoints stay legible
ends = []
for arm in ARMS:
    d = DATA[arm]
    y1 = d["b0"] + d["b1"] * xmax
    ends.append([arm, Y(y1)])
ends.sort(key=lambda e: e[1])
MIN_GAP = 34
for i in range(1, len(ends)):
    if ends[i][1] - ends[i - 1][1] < MIN_GAP:
        ends[i][1] = ends[i - 1][1] + MIN_GAP
for arm, ly in ends:
    d = DATA[arm]; col = COLOR[arm]
    s.append(f'<circle cx="{X(xmax)+10:.1f}" cy="{ly:.1f}" r="5" fill="{col}"/>')
    s.append(f'<text x="{X(xmax)+20:.1f}" y="{ly-5:.1f}" font-size="12.5" font-weight="700" fill="{col}">{LABEL[arm]}</text>')
    s.append(f'<text x="{X(xmax)+20:.1f}" y="{ly+10:.1f}" font-size="10.5" fill="#8a929c">R&#178;={d["r2"]:.2f}</text>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "turnscale_5reps.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("wrote", os.path.join(HERE, "turnscale_5reps.html"))

#!/usr/bin/env python3
"""Alternative of turnscale_avgsplit.png with a log-scaled x-axis (baseline
cold turn count), to check whether spreading out the dense 20-35 turn cluster
relative to the sparse tails (4, and 50-70) reads more clearly than the linear
version. The underlying fit is unchanged - still linear in x (not log-x) - so
each fit line is sampled at many x points and drawn as a curve rather than a
single straight segment, since a linear-in-x line is not straight once x
itself is log-transformed for display. Not wired into the writeup; render and
check before deciding whether to use it. Chrome headless -> PNG."""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
L = D["turns"]["scale"]
COLOR = D["dist_byleg"]["color"]
A_SIDE = ["2a", "3a", "4a"]
B_SIDE = ["2b", "3b", "4b"]
SOLO = ["5b", "6a", "6b"]
COL_A, COL_B = "#c2703d", "#2f7a8c"
LABEL_SOLO = {"5b": "5b · recipe (per-site)", "6a": "6a · atomic warm-up (no recipe)",
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

def pooled_xy(arms):
    xs, ys = [], []
    for t in L["tasks"]:
        bt = t["bturns"]
        for arm in arms:
            sv = t["sv"].get(arm)
            if sv is None: continue
            xs.append(bt); ys.append(sv / bt * 100)
    return xs, ys

POOLED = {}
xa, ya = pooled_xy(A_SIDE); b0, b1, r2 = linfit(xa, ya)
POOLED["A"] = {"xs": xa, "ys": ya, "b0": b0, "b1": b1, "r2": r2, "n": len(xa)}
xb, yb = pooled_xy(B_SIDE); b0, b1, r2 = linfit(xb, yb)
POOLED["B"] = {"xs": xb, "ys": yb, "b0": b0, "b1": b1, "r2": r2, "n": len(xb)}

SOLO_DATA = {}
for arm in SOLO:
    xs, ys = [], []
    for t in L["tasks"]:
        bt = t["bturns"]; sv = t["sv"].get(arm)
        if sv is None: continue
        xs.append(bt); ys.append(sv / bt * 100)
    b0, b1, r2 = linfit(xs, ys)
    SOLO_DATA[arm] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2}

W, H = 1300, 620
PL, PR, PT, PB = 66, 300, 70, 60
allx = POOLED["A"]["xs"] + POOLED["B"]["xs"]
ally = POOLED["A"]["ys"] + POOLED["B"]["ys"] + [y for arm in SOLO for y in SOLO_DATA[arm]["ys"]]
XLO = min(allx) * 0.85
xmax = max(allx) * 1.05
ymin = min(ally) * 1.15
ymax = max(ally) * 1.15
def X(v): return PL + (W - PL - PR) * (math.log(max(v, XLO)) - math.log(XLO)) / (math.log(xmax) - math.log(XLO))
def Y(v): return PT + (H - PT - PB) * (ymax - v) / (ymax - ymin)

def fit_path(b0, b1):
    xs = [XLO * (xmax / XLO) ** (i / 40) for i in range(41)]  # log-spaced samples
    pts = [(X(x), Y(b0 + b1 * x)) for x in xs]
    return "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Turns saved vs. task length (log x): source pooled across phases 2-4, plus 5b, 6a, 6b</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">% turns saved vs. cold, plotted against baseline (cold) turn count on a log scale &#183; dashed = pooled source average (n=36 each) &#183; solid = single arm &#183; fit is linear in x, so it curves here</text>')

for g in [4, 5, 7, 10, 15, 20, 30, 50, 70]:
    if g < XLO or g > xmax: continue
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
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-14}" text-anchor="middle" font-size="12" fill="#5b6571">baseline (cold) turns for the task (log scale)</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">% turns saved vs. cold</text>')

for arm in SOLO:
    d = SOLO_DATA[arm]; col = COLOR[arm]
    s.append(f'<path d="{fit_path(d["b0"], d["b1"])}" fill="none" stroke="{col}" stroke-width="2.2" opacity="0.85"/>')
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1" opacity="0.8"/>')

for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4" fill="{col}" opacity="0.35"/>')
for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    s.append(f'<path d="{fit_path(d["b0"], d["b1"])}" fill="none" stroke="{col}" stroke-width="3.4" stroke-dasharray="10 6" opacity="0.95"/>')

ends = []
for arm in SOLO:
    d = SOLO_DATA[arm]
    ends.append([LABEL_SOLO[arm], COLOR[arm], f'R&#178;={d["r2"]:.2f} (n=12)', Y(d["b0"] + d["b1"] * xmax)])
ends.append(["Experiential avg (2a+3a+4a)", COL_A, f'R&#178;={POOLED["A"]["r2"]:.2f} (n=36)', Y(POOLED["A"]["b0"] + POOLED["A"]["b1"] * xmax)])
ends.append(["Expert avg (2b+3b+4b)", COL_B, f'R&#178;={POOLED["B"]["r2"]:.2f} (n=36)', Y(POOLED["B"]["b0"] + POOLED["B"]["b1"] * xmax)])
ends.sort(key=lambda e: e[3])
MIN_GAP = 34
for i in range(1, len(ends)):
    if ends[i][3] - ends[i - 1][3] < MIN_GAP:
        ends[i][3] = ends[i - 1][3] + MIN_GAP
for label, col, sub, ly in ends:
    s.append(f'<circle cx="{X(xmax)+10:.1f}" cy="{ly:.1f}" r="5" fill="{col}"/>')
    s.append(f'<text x="{X(xmax)+20:.1f}" y="{ly-5:.1f}" font-size="12.5" font-weight="700" fill="{col}">{label}</text>')
    s.append(f'<text x="{X(xmax)+20:.1f}" y="{ly+10:.1f}" font-size="10.5" fill="#8a929c">{sub}</text>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "turnscale_avgsplit_logx.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("wrote", os.path.join(HERE, "turnscale_avgsplit_logx.html"))

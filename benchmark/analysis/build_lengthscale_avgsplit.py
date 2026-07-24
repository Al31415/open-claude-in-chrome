#!/usr/bin/env python3
"""Time savings vs. baseline task length (same x-axis convention as
turnscale_avgsplit.png: baseline/cold turn count for the task), but the
y-axis is now percent of TIME saved vs. cold rather than percent of turns
saved - the time-based analog of the turn-scale trend. Baseline time per
task = avg of 1a/1b/1c's per-task minutes (joined by task name), matching
the same cold triad used for every other baseline reference in this deck.
Same pooling as the turn-count version: experiential (2a+3a+4a) and expert
(2b+3b+4b) dashed pooled averages, plus solo lines for 5b, 6a, 6b. Pure-python
least-squares linear fit.

A handful of points (all from the fork arms 4a/4b, whose fixed forked-context
overhead swamps the percentage on short cold tasks) run to -560%, which would
otherwise force the whole y-axis out to fit them and flatten every fit line
into an unreadable sliver near the top. Same fix as the itemized chart in
build_capstone.py: the axis is clamped to where the real cluster of points
lives, and anything past the floor renders as a colour-matched arrow at the
bottom edge with its actual value labelled, instead of being dropped or
silently distorting the scale. Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
LS = D["lengthscale"]
COLOR = D["dist_byleg"]["color"]
BY = {a["short"]: a for a in D["arms"]}
A_SIDE = ["2a", "3a", "4a"]
B_SIDE = ["2b", "3b", "4b"]
SOLO = ["5b", "6a", "6b"]
COL_A, COL_B = "#c2703d", "#2f7a8c"
LABEL_SOLO = {"5b": "5b · recipe (per-site)", "6a": "6a · atomic warm-up (no recipe)",
              "6b": "6b · warm-up + recipe (winner)"}

# baseline seconds per task = avg of 1a/1b/1c per-task minutes * 60, joined by task name
BASE_SEC = {}
for s in ("1a", "1b", "1c"):
    for pt in BY[s]["per_task"]:
        BASE_SEC.setdefault(pt["t"], []).append(pt["min"] * 60)
BASE_SEC = {t: sum(v) / len(v) for t, v in BASE_SEC.items()}

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
    for t in LS["tasks"]:
        bt = t["bturns"]; base = BASE_SEC[t["t"]]
        for arm in arms:
            sv = t["sv"].get(arm)
            if sv is None: continue
            xs.append(bt); ys.append(sv / base * 100)
    return xs, ys

POOLED = {}
for side, arms in (("A", A_SIDE), ("B", B_SIDE)):
    xs, ys = pooled_xy(arms); b0, b1, r2 = linfit(xs, ys)
    POOLED[side] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2, "n": len(xs)}
    print(f"{side}-side pooled: n={len(xs)}  slope={b1:+.3f}  R2={r2:.3f}")

SOLO_DATA = {}
for arm in SOLO:
    xs, ys = [], []
    for t in LS["tasks"]:
        bt = t["bturns"]; base = BASE_SEC[t["t"]]; sv = t["sv"].get(arm)
        if sv is None: continue
        xs.append(bt); ys.append(sv / base * 100)
    b0, b1, r2 = linfit(xs, ys)
    SOLO_DATA[arm] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2}
    print(f"{arm}: n={len(xs)}  slope={b1:+.3f}  R2={r2:.3f}")

W, H = 1300, 620
PL, PR, PT, PB = 66, 300, 70, 60
allx = POOLED["A"]["xs"] + POOLED["B"]["xs"]
ally = POOLED["A"]["ys"] + POOLED["B"]["ys"] + [y for arm in SOLO for y in SOLO_DATA[arm]["ys"]]
xmax = max(allx) * 1.05
# floor clamped above the fork-arm (4a/4b) outliers so the fit lines - none of
# which dip below -110 - stay readable; points past the floor become arrows
YFLOOR = -140
capped = [y for y in ally if y >= YFLOOR]
ymin = YFLOOR
ymax = max(capped) * 1.15
def X(v): return PL + (W - PL - PR) * v / xmax
def Y(v): return PT + (H - PT - PB) * (ymax - v) / (ymax - ymin)
def Yc(v): return Y(max(YFLOOR, v))

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Time saved vs. task length: source pooled across phases 2-4, plus 5b, 6a, 6b</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">% task time saved vs. cold, plotted against baseline (cold) turn count &#183; dashed = pooled source average (n=36 each) &#183; solid = single arm &#183; cold itself is the implicit 0% line</text>')
s.append(f'<text x="{PL}" y="{PT-8}" font-size="10.5" fill="#8a929c">&#9660; below {YFLOOR}%: axis floor, arrow = actual value (all from 4a/4b on short cold tasks)</text>')

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
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">% task time saved vs. cold</text>')

for arm in SOLO:
    d = SOLO_DATA[arm]; col = COLOR[arm]
    y0, y1 = d["b0"], d["b0"] + d["b1"] * xmax
    s.append(f'<line x1="{X(0):.1f}" y1="{Y(y0):.1f}" x2="{X(xmax):.1f}" y2="{Y(y1):.1f}" stroke="{col}" stroke-width="2.2" opacity="0.85"/>')
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1" opacity="0.8"/>')

# points inside the floor render as normal dots; points below it become
# colour-matched arrows pinned to the bottom edge, fanned out by x-pixel so
# coincident tasks (several fall at the same baseline turn count) don't stack
outliers = []
for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    for x, y in zip(d["xs"], d["ys"]):
        if y < YFLOOR:
            outliers.append((X(x), col, y))
        else:
            s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4" fill="{col}" opacity="0.35"/>')
outliers.sort(key=lambda o: o[0])
buckets = []
for ox, col, y in outliers:
    if buckets and ox - buckets[-1][-1][0] < 45:
        buckets[-1].append((ox, col, y))
    else:
        buckets.append([(ox, col, y)])
ey = Y(YFLOOR)
SLOT = 46
for bucket in buckets:
    n = len(bucket)
    cx = sum(o[0] for o in bucket) / n
    for i, (ox, col, y) in enumerate(bucket):
        ax = cx + (i - (n - 1) / 2) * SLOT
        s.append(f'<path d="M {ax:.1f} {ey+6:.1f} L {ax-5:.1f} {ey-5:.1f} L {ax+5:.1f} {ey-5:.1f} Z" fill="{col}" opacity="0.9" stroke="#fff" stroke-width="1"/>')
        s.append(f'<text x="{ax:.1f}" y="{ey-9:.1f}" text-anchor="middle" font-size="9" font-weight="600" fill="{col}">{y:.0f}%</text>')
for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    y0, y1 = d["b0"], d["b0"] + d["b1"] * xmax
    s.append(f'<line x1="{X(0):.1f}" y1="{Y(y0):.1f}" x2="{X(xmax):.1f}" y2="{Y(y1):.1f}" stroke="{col}" stroke-width="3.4" stroke-dasharray="10 6" opacity="0.95"/>')

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
open(os.path.join(HERE, "lengthscale_avgsplit.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("wrote", os.path.join(HERE, "lengthscale_avgsplit.html"))

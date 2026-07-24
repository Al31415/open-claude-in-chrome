#!/usr/bin/env python3
"""Replaces the % time saved vs. task length chart with a direct latency
comparison. X-axis: baseline (cold) time per task, minutes, linear (avg of
1a/1b/1c, same join as before, now left in minutes instead of turns). Y-axis:
each arm's own actual time on that task, minutes, log scale - since actual
task time is always positive, log-y needs no floor/arrow workaround the way
the %-saved version did. A grey y=x diagonal marks "no time saved vs. cold".
Fit is linear regression of ln(task_min) on baseline_min per series (semi-log
fit), so it renders as a straight line on this log-y axis; same pooling as
before (experiential: 2a+3a+4a dashed, expert: 2b+3b+4b dashed, solo: 5b/6a/6b
solid). Chrome headless -> PNG."""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
COLOR = D["dist_byleg"]["color"]
BY = {a["short"]: a for a in D["arms"]}
A_SIDE = ["2a", "3a", "4a"]
B_SIDE = ["2b", "3b", "4b"]
SOLO = ["5b", "6a", "6b"]
COL_A, COL_B = "#c2703d", "#2f7a8c"
LABEL_SOLO = {"5b": "5b · recipe (per-site)", "6a": "6a · atomic warm-up (no recipe)",
              "6b": "6b · warm-up + recipe (winner)"}

BASE_MIN = {}
for s in ("1a", "1b", "1c"):
    for pt in BY[s]["per_task"]:
        BASE_MIN.setdefault(pt["t"], []).append(pt["min"])
BASE_MIN = {t: sum(v) / len(v) for t, v in BASE_MIN.items()}

ARM_MIN = {arm: {pt["t"]: pt["min"] for pt in BY[arm]["per_task"]} for arm in A_SIDE + B_SIDE + SOLO}

def semilog_fit(xs, ys):
    # OLS of ln(y) on x - a straight line here maps to a straight line on the
    # log-y axis (Y is linear in ln(y), ln(y) is linear in x)
    lys = [math.log(y) for y in ys]
    n = len(xs)
    sx = sum(xs); sy = sum(lys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, lys))
    b1 = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b0 = (sy - b1 * sx) / n
    pred = [b0 + b1 * x for x in xs]
    ybar = sy / n
    ss_res = sum((y - p) ** 2 for y, p in zip(lys, pred))
    ss_tot = sum((y - ybar) ** 2 for y in lys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return b0, b1, r2

def pooled_xy(arms):
    xs, ys = [], []
    for t, bmin in BASE_MIN.items():
        for arm in arms:
            v = ARM_MIN[arm].get(t)
            if v is None: continue
            xs.append(bmin); ys.append(v)
    return xs, ys

POOLED = {}
for side, arms in (("A", A_SIDE), ("B", B_SIDE)):
    xs, ys = pooled_xy(arms); b0, b1, r2 = semilog_fit(xs, ys)
    POOLED[side] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2, "n": len(xs)}
    print(f"{side}-side pooled: n={len(xs)}  ln(min)~x  slope={b1:+.3f}  R2={r2:.3f}")

SOLO_DATA = {}
for arm in SOLO:
    xs, ys = [], []
    for t, bmin in BASE_MIN.items():
        v = ARM_MIN[arm].get(t)
        if v is None: continue
        xs.append(bmin); ys.append(v)
    b0, b1, r2 = semilog_fit(xs, ys)
    SOLO_DATA[arm] = {"xs": xs, "ys": ys, "b0": b0, "b1": b1, "r2": r2}
    print(f"{arm}: n={len(xs)}  slope={b1:+.3f}  R2={r2:.3f}")

W, H = 1300, 620
PL, PR, PT, PB = 66, 300, 70, 60
allx = [v for v in BASE_MIN.values()]
ally = POOLED["A"]["ys"] + POOLED["B"]["ys"] + [y for arm in SOLO for y in SOLO_DATA[arm]["ys"]]
xmax = max(allx) * 1.1
YLO = min(ally) * 0.85
YHI = max(ally) * 1.2
def X(v): return PL + (W - PL - PR) * v / xmax
def Y(v): return PT + (H - PT - PB) * (math.log(YHI) - math.log(max(v, YLO))) / (math.log(YHI) - math.log(YLO))

def fit_path(b0, b1, x0, x1):
    xs = [x0 + (x1 - x0) * i / 40 for i in range(41)]
    pts = [(X(x), Y(math.exp(b0 + b1 * x))) for x in xs]
    return "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Actual task time vs. baseline task time: source pooled across phases 2-4, plus 5b, 6a, 6b</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">Each arm\'s own per-task minutes (log y-axis) vs. baseline (cold) per-task minutes (linear x-axis, avg of 1a/1b/1c) &#183; grey diagonal = y=x (no time saved vs. cold)</text>')
s.append(f'<text x="{PL}" y="{PT-8}" font-size="10.5" fill="#8a929c">dashed = pooled source fit, ln(minutes) ~ baseline minutes (n=36 each) &#183; solid = single-arm fit (n=12) &#183; points below the diagonal are faster than cold</text>')

for g in [0, 1, 2, 3, 4, 5]:
    if g > xmax: continue
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="10" fill="#8a929c">{g}m</text>')
for g in [0.2, 0.5, 1, 2, 5, 10]:
    if g < YLO or g > YHI: continue
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f7f6f2"/>')
    s.append(f'<text x="{PL-8:.1f}" y="{Y(g)+3.5:.1f}" text-anchor="end" font-size="10" fill="#8a929c">{g}m</text>')
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-14}" text-anchor="middle" font-size="12" fill="#5b6571">baseline (cold) time for the task (minutes)</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">actual task time (minutes, log scale)</text>')

# y=x reference: no time saved vs. cold
diag = "M " + " L ".join(f"{X(x):.1f} {Y(x):.1f}" for x in [i * xmax / 40 for i in range(41)] if x > 0)
s.append(f'<path d="{diag}" fill="none" stroke="#c9c7c1" stroke-width="1.6"/>')
s.append(f'<text x="{X(xmax*0.97):.1f}" y="{Y(xmax*0.97)-8:.1f}" text-anchor="end" font-size="10.5" fill="#8a929c">y=x (cold)</text>')

for arm in SOLO:
    d = SOLO_DATA[arm]; col = COLOR[arm]
    s.append(f'<path d="{fit_path(d["b0"], d["b1"], 0, xmax)}" fill="none" stroke="{col}" stroke-width="2.2" opacity="0.85"/>')
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1" opacity="0.8"/>')

for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    for x, y in zip(d["xs"], d["ys"]):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4" fill="{col}" opacity="0.35"/>')
for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    s.append(f'<path d="{fit_path(d["b0"], d["b1"], 0, xmax)}" fill="none" stroke="{col}" stroke-width="3.4" stroke-dasharray="10 6" opacity="0.95"/>')

ends = []
for arm in SOLO:
    d = SOLO_DATA[arm]
    ends.append([LABEL_SOLO[arm], COLOR[arm], f'R&#178;={d["r2"]:.2f} (n=12)', Y(math.exp(d["b0"] + d["b1"] * xmax))])
ends.append(["Experiential avg (2a+3a+4a)", COL_A, f'R&#178;={POOLED["A"]["r2"]:.2f} (n=36)', Y(math.exp(POOLED["A"]["b0"] + POOLED["A"]["b1"] * xmax))])
ends.append(["Expert avg (2b+3b+4b)", COL_B, f'R&#178;={POOLED["B"]["r2"]:.2f} (n=36)', Y(math.exp(POOLED["B"]["b0"] + POOLED["B"]["b1"] * xmax))])
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
open(os.path.join(HERE, "lengthscale_latency_logy.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("wrote", os.path.join(HERE, "lengthscale_latency_logy.html"))

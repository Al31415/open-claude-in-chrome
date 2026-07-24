#!/usr/bin/env python3
"""Experimental variant of turns_ratio_decay.png: no fit line at all - just
the raw (baseline turns, ratio) points per series, sorted left to right by
baseline turns and connected point-to-point. For the pooled series (3 arms
per task) this is inherently jagged since three points share each x; that's
expected, not a bug - it's meant to show what the literal data path looks
like without smoothing it into a trend. Same log-y axis, 1x break-even line,
and top-edge-tick-for-outliers convention as turns_ratio_decay.png. Chrome
headless -> PNG."""
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

BASE_TURNS = {}
for s in ("1a", "1b", "1c"):
    for pt in BY[s]["per_task"]:
        BASE_TURNS.setdefault(pt["t"], []).append(pt["turns"])
BASE_TURNS = {t: sum(v) / len(v) for t, v in BASE_TURNS.items()}

ARM_TURNS = {arm: {pt["t"]: pt["turns"] for pt in BY[arm]["per_task"]} for arm in A_SIDE + B_SIDE + SOLO}

def pooled_xy(arms):
    xs, ys = [], []
    for t, bturns in BASE_TURNS.items():
        for arm in arms:
            v = ARM_TURNS[arm].get(t)
            if v is None: continue
            xs.append(bturns); ys.append(v / bturns)
    return xs, ys

POOLED = {}
for side, arms in (("A", A_SIDE), ("B", B_SIDE)):
    xs, ys = pooled_xy(arms)
    POOLED[side] = {"xs": xs, "ys": ys, "n": len(xs)}

SOLO_DATA = {}
for arm in SOLO:
    xs, ys = [], []
    for t, bturns in BASE_TURNS.items():
        v = ARM_TURNS[arm].get(t)
        if v is None: continue
        xs.append(bturns); ys.append(v / bturns)
    SOLO_DATA[arm] = {"xs": xs, "ys": ys}

W, H = 1300, 620
PL, PR, PT, PB = 66, 300, 78, 60
allx = [v for v in BASE_TURNS.values()]
ally = POOLED["A"]["ys"] + POOLED["B"]["ys"] + [y for arm in SOLO for y in SOLO_DATA[arm]["ys"]]
xmax = max(allx) * 1.05
YLO = min(ally) * 0.85
YHI = 1.8
def X(v): return PL + (W - PL - PR) * v / xmax
def Y(v): return PT + (H - PT - PB) * (math.log(YHI) - math.log(max(v, YLO))) / (math.log(YHI) - math.log(YLO))

def connect_path(xs, ys):
    pts = sorted(zip(xs, ys), key=lambda p: p[0])
    return "M " + " L ".join(f"{X(x):.1f} {Y(min(y, YHI)):.1f}" for x, y in pts)

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">Task turns as a multiple of cold - raw points connected, no fit</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">Each point: (arm task turns) / (baseline cold task turns), log y-axis, vs. baseline (cold) turns, linear x-axis &#183; points connected left to right by baseline turns, no regression</text>')
s.append(f'<text x="{PL}" y="{PT-10}" font-size="10.5" fill="#8a929c">horizontal line = 1&#215; (equal to cold) &#183; dashed = pooled source (n=36 each) &#183; solid = single-arm (n=12) &#183; ticks along the top edge = points above {YHI:g}&#215;, off scale</text>')

for g in range(0, int(xmax) + 1, 10):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="10" fill="#8a929c">{g}</text>')
for g in [0.5, 0.75, 1, 1.5]:
    if g < YLO or g > YHI: continue
    hot = abs(g - 1) < 1e-9
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="{"#c9c7c1" if hot else "#f7f6f2"}" stroke-width="{1.6 if hot else 1}"/>')
    s.append(f'<text x="{PL-8:.1f}" y="{Y(g)+3.5:.1f}" text-anchor="end" font-size="10" fill="#8a929c">{g:g}&#215;</text>')
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-14}" text-anchor="middle" font-size="12" fill="#5b6571">baseline (cold) turns for the task</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">task turns / baseline turns (log scale)</text>')

ey = Y(YHI)
def top_tick(x, col, big):
    s.append(f'<line x1="{X(x):.1f}" y1="{ey:.1f}" x2="{X(x):.1f}" y2="{ey+9:.1f}" stroke="{col}" stroke-width="{2 if big else 1.6}" opacity="{0.8 if big else 0.55}"/>')

for arm in SOLO:
    d = SOLO_DATA[arm]; col = COLOR[arm]
    s.append(f'<path d="{connect_path(d["xs"], d["ys"])}" fill="none" stroke="{col}" stroke-width="2.2" opacity="0.85"/>')
    for x, y in zip(d["xs"], d["ys"]):
        if y > YHI:
            top_tick(x, col, True)
        else:
            s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1" opacity="0.8"/>')

for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    for x, y in zip(d["xs"], d["ys"]):
        if y > YHI:
            top_tick(x, col, False)
        else:
            s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4" fill="{col}" opacity="0.35"/>')
for side, col in (("A", COL_A), ("B", COL_B)):
    d = POOLED[side]
    s.append(f'<path d="{connect_path(d["xs"], d["ys"])}" fill="none" stroke="{col}" stroke-width="2.4" stroke-dasharray="8 5" opacity="0.7"/>')

ends = []
for arm in SOLO:
    d = SOLO_DATA[arm]
    last_x, last_y = max(zip(d["xs"], d["ys"]), key=lambda p: p[0])
    ends.append([LABEL_SOLO[arm], COLOR[arm], f'n=12', Y(min(last_y, YHI))])
for side, label in (("A", "Experiential avg (2a+3a+4a)"), ("B", "Expert avg (2b+3b+4b)")):
    d = POOLED[side]
    last_x, last_y = max(zip(d["xs"], d["ys"]), key=lambda p: p[0])
    ends.append([label, COL_A if side == "A" else COL_B, f'n=36', Y(min(last_y, YHI))])
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
open(os.path.join(HERE, "turns_ratio_connect.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
print("wrote", os.path.join(HERE, "turns_ratio_connect.html"))

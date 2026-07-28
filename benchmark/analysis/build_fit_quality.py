#!/usr/bin/env python3
"""Side-by-side fit quality for the two multiplier charts: ratio_decay.png
(wall-clock task time as a multiple of cold) against thinking_ratio_decay.png
(estimated thinking tokens as a multiple of cold). Same five series, same
semi-log form - ln(ratio) regressed on the baseline value for that task - so
the only thing that changes between a pair of bars is which quantity is being
tracked. R2 on the y-axis: how much of the spread the decay trend actually
accounts for. The fitted slope is printed under each bar because a high R2 on
a POSITIVE slope (6a) means a well-fitted rise, not a decay. Recomputes both
fits from source rather than quoting them, so it cannot drift from the two
parent charts. Reads thinking_per_task.json (run compute_thinking_per_task.py
first). Chrome headless -> PNG."""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
BY = {a["short"]: a for a in D["arms"]}
TPT = json.load(open(os.path.join(HERE, "thinking_per_task.json")))
A_SIDE, B_SIDE = ["2a", "3a", "4a"], ["2b", "3b", "4b"]
COL_TIME, COL_THINK = "#9aa3ad", "#5b4b8a"

# --- wall-clock minutes, exactly as build_ratio_decay.py loads them ---
BASE_MIN = {}
for s in ("1a", "1b", "1c"):
    for pt in BY[s]["per_task"]:
        BASE_MIN.setdefault(pt["t"], []).append(pt["min"])
BASE_MIN = {t: sum(v) / len(v) for t, v in BASE_MIN.items()}
ARM_MIN = {a: {pt["t"]: pt["min"] for pt in BY[a]["per_task"]} for a in BY}
# --- thinking tokens, exactly as build_thinking_ratio_decay.py loads them ---
BASE_K = {t: (sum(TPT[a][t] for a in ("1a", "1b", "1c")) / 3) / 1000 for t in TPT["1a"]}


def semilog_fit(xs, ys):
    lys = [math.log(y) for y in ys]
    n = len(xs)
    sx = sum(xs); sy = sum(lys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, lys))
    b1 = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b0 = (sy - b1 * sx) / n
    ybar = sy / n
    ss_res = sum((y - (b0 + b1 * x)) ** 2 for x, y in zip(xs, lys))
    ss_tot = sum((y - ybar) ** 2 for y in lys)
    return b1, (1 - ss_res / ss_tot if ss_tot else 0)


def fit_time(arms):
    xs, ys = [], []
    for t, b in BASE_MIN.items():
        for a in arms:
            xs.append(b); ys.append(ARM_MIN[a][t] / b)
    return semilog_fit(xs, ys)


def fit_think(arms):
    xs, ys = [], []
    for t, b in BASE_K.items():
        for a in arms:
            xs.append(b); ys.append((TPT[a][t] / 1000) / b)
    return semilog_fit(xs, ys)


SERIES = [("Experiential", "2a+3a+4a pooled · n=36", A_SIDE),
          ("Expert", "2b+3b+4b pooled · n=36", B_SIDE),
          ("5b", "recipe (per-site) · n=12", ["5b"]),
          ("6a", "atomic warm-up · n=12", ["6a"]),
          ("6b", "warm-up + recipe · n=12", ["6b"])]
ROWS = []
for name, sub, arms in SERIES:
    st, rt = fit_time(arms)
    sk, rk = fit_think(arms)
    ROWS.append({"name": name, "sub": sub, "st": st, "rt": rt, "sk": sk, "rk": rk})

print(f"{'series':14}{'time slope':>12}{'time R2':>9}{'think slope':>13}{'think R2':>10}")
for r in ROWS:
    print(f"{r['name']:14}{r['st']:>+12.4f}{r['rt']:>9.3f}{r['sk']:>+13.4f}{r['rk']:>10.3f}")

W, H = 1120, 580
PL, PR, PT, PB = 62, 40, 96, 96
YMAX = 0.72
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / YMAX
plotw = W - PL - PR
gpad = 46
gw = (plotw - gpad * (len(ROWS) - 1)) / len(ROWS)
bw = gw * 0.36
bgap = gw * 0.06

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
for g in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g:.1f}</text>')

for i, r in enumerate(ROWS):
    gx = PL + i * (gw + gpad)
    xa, xb = gx, gx + bw + bgap
    cx = gx + (bw * 2 + bgap) / 2
    for x, val, slope, col in ((xa, r["rt"], r["st"], COL_TIME), (xb, r["rk"], r["sk"], COL_THINK)):
        y = Y(val)
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{Y(0)-y:.1f}" rx="3" fill="{col}"/>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="12.5" '
                 f'font-weight="700" fill="{col}">{val:.2f}</text>')
        # sign of the slope decides whether that R2 describes a decay or a rise
        rising = slope > 0
        s.append(f'<text x="{x+bw/2:.1f}" y="{Y(0)+20:.1f}" text-anchor="middle" font-size="9.5" '
                 f'fill="{"#c13a2e" if rising else "#8a929c"}">{slope:+.3f}</text>')
        if rising:
            s.append(f'<text x="{x+bw/2:.1f}" y="{Y(0)+32:.1f}" text-anchor="middle" font-size="8.5" '
                     f'fill="#c13a2e">rising</text>')
    s.append(f'<text x="{cx:.1f}" y="{Y(0)+56:.1f}" text-anchor="middle" font-size="13" '
             f'font-weight="700" fill="#1b1f24">{r["name"]}</text>')
    s.append(f'<text x="{cx:.1f}" y="{Y(0)+71:.1f}" text-anchor="middle" font-size="10" fill="#8a929c">{r["sub"]}</text>')

lx, ly = PL, 78
s.append(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_TIME}"/>')
s.append(f'<text x="{lx+18}" y="{ly}" font-size="11.5" fill="#5b6571">Wall-clock task time (ratio_decay)</text>')
s.append(f'<rect x="{lx+300}" y="{ly-10}" width="12" height="12" rx="2" fill="{COL_THINK}"/>')
s.append(f'<text x="{lx+318}" y="{ly}" font-size="11.5" fill="#5b6571">Estimated thinking tokens (thinking_ratio_decay)</text>')
s.append(f'<text x="{W-PR}" y="{ly}" text-anchor="end" font-size="10.5" fill="#a8aeb6">'
         f'value under each bar = fitted slope</text>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">'
         f'Fit quality: the same decay, measured in minutes and in thinking tokens</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">'
         f'R&#178; of ln(ratio to cold) regressed on the task\'s baseline value &#183; identical series, identical form, '
         f'only the tracked quantity changes</text>')
s.append(f'<text x="18" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" '
         f'transform="rotate(-90 18 {(PT+H-PB)/2:.1f})">R&#178; of the semi-log fit</text>')
s.append('</svg>')

open(os.path.join(HERE, "fit_quality.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><title>fit quality</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
print("wrote", os.path.join(HERE, "fit_quality.html"))

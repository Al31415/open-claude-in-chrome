#!/usr/bin/env python3
"""Residual diagnostic for turns_ratio_decay.png. That chart fits ln(ratio) on
baseline turns for five series (experiential pooled 2a+3a+4a, expert pooled
2b+3b+4b, and 5b / 6a / 6b solo); this one plots what those fits left behind:
residual = ln(observed ratio) - fitted, against the same x-axis. A flat,
structureless band around zero means the semi-log form is the right shape and
the low R2 is just scatter; a wedge or a curve means the form itself is wrong.
Same data, same fits, same colours as the parent chart. Points in the pooled
panels are coloured by their source arm so it is visible when one arm owns the
spread. Chrome headless -> PNG."""
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

# baseline (cold) turns per task = mean of the three phase-1 arms, verbatim
# from the parent chart so the x-axis and the fits are the same objects
BASE_TURNS = {}
for s in ("1a", "1b", "1c"):
    for pt in BY[s]["per_task"]:
        BASE_TURNS.setdefault(pt["t"], []).append(pt["turns"])
BASE_TURNS = {t: sum(v) / len(v) for t, v in BASE_TURNS.items()}
ARM_TURNS = {arm: {pt["t"]: pt["turns"] for pt in BY[arm]["per_task"]}
             for arm in A_SIDE + B_SIDE + SOLO}


def semilog_fit(xs, ys):
    lys = [math.log(y) for y in ys]
    n = len(xs)
    sx = sum(xs); sy = sum(lys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, lys))
    b1 = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b0 = (sy - b1 * sx) / n
    pred = [b0 + b1 * x for x in xs]
    ybar = sy / n
    ss_res = sum((y - p) ** 2 for y, p in zip(lys, pred))
    ss_tot = sum((y - ybar) ** 2 for y in lys)
    return b0, b1, (1 - ss_res / ss_tot if ss_tot else 0)


def collect(arms):
    """(x, ratio, arm, task) for every task x arm cell, in task order."""
    out = []
    for t, bturns in BASE_TURNS.items():
        for arm in arms:
            v = ARM_TURNS[arm].get(t)
            if v is None: continue
            out.append((bturns, v / bturns, arm, t))
    return out


SERIES = [
    ("Experiential pooled", A_SIDE, COL_A, "2a + 3a + 4a"),
    ("Expert pooled", B_SIDE, COL_B, "2b + 3b + 4b"),
    ("5b · recipe (per-site)", ["5b"], COLOR["5b"], "single arm"),
    ("6a · atomic warm-up", ["6a"], COLOR["6a"], "single arm"),
    ("6b · warm-up + recipe", ["6b"], COLOR["6b"], "single arm"),
]

PANELS = []
for name, arms, col, sub in SERIES:
    rows = collect(arms)
    xs = [r[0] for r in rows]; ys = [r[1] for r in rows]
    b0, b1, r2 = semilog_fit(xs, ys)
    res = [math.log(y) - (b0 + b1 * x) for x, y in zip(xs, ys)]
    n = len(res)
    sd = math.sqrt(sum(r * r for r in res) / (n - 2))          # residual SE, 2 params
    mean_res = sum(res) / n
    # split-half slope check: mean residual in the left vs right half of x,
    # the cheapest test for "the straight line is bending"
    mid = sorted(xs)[n // 2]
    lo = [r for x, r in zip(xs, res) if x <= mid]
    hi = [r for x, r in zip(xs, res) if x > mid]
    PANELS.append({
        "name": name, "col": col, "sub": sub, "b0": b0, "b1": b1, "r2": r2,
        "rows": rows, "res": res, "sd": sd, "n": n, "mean": mean_res,
        "lo": sum(lo) / len(lo) if lo else 0, "hi": sum(hi) / len(hi) if hi else 0,
        "outliers": sorted(range(n), key=lambda i: -abs(res[i]))[:2],
    })

print(f"{'series':24}{'n':>4}{'slope':>10}{'R2':>7}{'resid SE':>10}{'x spread':>10}"
      f"{'left mean':>11}{'right mean':>12}  worst")
for p in PANELS:
    w = p["outliers"][0]
    print(f"{p['name']:24}{p['n']:>4}{p['b1']:>+10.4f}{p['r2']:>7.3f}{p['sd']:>10.3f}"
          f"{math.exp(p['sd']):>9.2f}x{p['lo']:>+11.3f}{p['hi']:>+12.3f}  "
          f"{p['rows'][w][3]} ({p['rows'][w][2]}) {p['res'][w]:+.2f} = {math.exp(p['res'][w]):.2f}x")

W, H = 1300, 790
PL, PR, PT, PB = 62, 30, 122, 52
COLS, ROWS = 3, 2
GX, GY = 66, 78
PW = (W - PL - PR - GX * (COLS - 1)) / COLS
PH = (H - PT - PB - GY * (ROWS - 1)) / ROWS
XMAX = max(BASE_TURNS.values()) * 1.06
RMAX = max(max(abs(r) for r in p["res"]) for p in PANELS) * 1.12
JIT = {a: (i - 1) * 0.85 for grp in (A_SIDE, B_SIDE) for i, a in enumerate(grp)}

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="32" font-size="18" font-weight="700" fill="#1b1f24">'
         f'Residuals of the turns-ratio fits: what the decay lines left behind</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">'
         f'residual = ln(task turns / baseline turns) &#8722; semi-log fit, plotted against the same x-axis as turns_ratio_decay '
         f'&#183; one panel per fitted series &#183; shared y-scale</text>')
s.append(f'<text x="{PL}" y="70" font-size="10.5" fill="#8a929c">'
         f'zero line = the fit &#183; shaded band = &#177;1 residual SE &#183; right axis reads the same residual as a multiple of the fit '
         f'&#183; pooled panels colour each point by its source arm &#183; the two largest residuals per panel are named</text>')


def panel(idx, p):
    r, c = divmod(idx, COLS)
    ox = PL + c * (PW + GX)
    oy = PT + r * (PH + GY)
    show_right = c == COLS - 1 or idx == len(PANELS) - 1
    X = lambda v: ox + PW * v / XMAX
    Y = lambda v: oy + PH * (RMAX - v) / (2 * RMAX)
    out = []
    out.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{PW:.1f}" height="{PH:.1f}" fill="#fcfcfa" stroke="#eceae4"/>')
    # +/-1 SE band
    out.append(f'<rect x="{ox:.1f}" y="{Y(p["sd"]):.1f}" width="{PW:.1f}" height="{(Y(-p["sd"])-Y(p["sd"])):.1f}" '
               f'fill="{p["col"]}" opacity="0.07"/>')
    for g in (p["sd"], -p["sd"]):
        out.append(f'<line x1="{ox:.1f}" y1="{Y(g):.1f}" x2="{ox+PW:.1f}" y2="{Y(g):.1f}" '
                   f'stroke="{p["col"]}" stroke-width="1" stroke-dasharray="4 4" opacity="0.5"/>')
    # x gridlines
    for g in range(0, int(XMAX) + 1, 20):
        out.append(f'<line x1="{X(g):.1f}" y1="{oy:.1f}" x2="{X(g):.1f}" y2="{oy+PH:.1f}" stroke="#f2f1ed"/>')
        out.append(f'<text x="{X(g):.1f}" y="{oy+PH+16:.1f}" text-anchor="middle" font-size="9.5" fill="#a8aeb6">{g}</text>')
    # zero line = the fit itself
    out.append(f'<line x1="{ox:.1f}" y1="{Y(0):.1f}" x2="{ox+PW:.1f}" y2="{Y(0):.1f}" stroke="#5b6571" stroke-width="1.7"/>')
    # y ticks, ln on the left, multiplicative on the right
    for g in (-0.6, -0.3, 0, 0.3, 0.6):
        if abs(g) > RMAX: continue
        if g:
            out.append(f'<line x1="{ox-4:.1f}" y1="{Y(g):.1f}" x2="{ox:.1f}" y2="{Y(g):.1f}" stroke="#c9c7c1"/>')
        out.append(f'<text x="{ox-7:.1f}" y="{Y(g)+3.2:.1f}" text-anchor="end" font-size="9.5" fill="#a8aeb6">{g:+.1f}</text>'
                   if g else
                   f'<text x="{ox-7:.1f}" y="{Y(g)+3.2:.1f}" text-anchor="end" font-size="9.5" fill="#5b6571">0</text>')
        # the multiplicative twin of the same axis, only on the panel that ends
        # its row - otherwise it lands on the next panel's ln labels
        if show_right:
            out.append(f'<text x="{ox+PW+7:.1f}" y="{Y(g)+3.2:.1f}" font-size="9" fill="#b9bec6">{math.exp(g):.2f}&#215;</text>')
    # points
    solo = len(set(a for _, _, a, _ in p["rows"])) == 1
    for i, (x, y, arm, task) in enumerate(p["rows"]):
        rv = p["res"][i]
        col = p["col"] if solo else COLOR[arm]
        px, py = X(x + JIT.get(arm, 0)), Y(max(-RMAX, min(RMAX, rv)))
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{4.6 if solo else 4.0}" fill="{col}" '
                   f'stroke="#fff" stroke-width="0.9" opacity="{0.85 if solo else 0.7}"/>')
    # name the two largest residuals; the two often sit on top of each other
    # (same task, different arm), so stack the second one clear of the first
    placed = []
    for i in p["outliers"]:
        x, y, arm, task = p["rows"][i]
        rv = p["res"][i]
        px, py = X(x + JIT.get(arm, 0)), Y(max(-RMAX, min(RMAX, rv)))
        lbl = task if solo else f"{task} · {arm}"
        anchor, tx = "middle", px
        if px > ox + PW - 74: tx, anchor = px - 6, "end"
        if px < ox + 74: tx, anchor = px + 6, "start"
        ty = py + (-9 if rv < 0 else 15)
        while any(abs(tx - qx) < 78 and abs(ty - qy) < 11 for qx, qy in placed):
            ty += 12
        placed.append((tx, ty))
        out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" '
                   f'font-size="9" fill="#8a929c">{lbl}</text>')
    # header
    out.append(f'<text x="{ox:.1f}" y="{oy-30:.1f}" font-size="13" font-weight="700" fill="{p["col"]}">{p["name"]}</text>')
    out.append(f'<text x="{ox:.1f}" y="{oy-16:.1f}" font-size="10" fill="#8a929c">'
               f'{p["sub"]} &#183; n={p["n"]} &#183; slope={p["b1"]:+.4f} &#183; R&#178;={p["r2"]:.2f} '
               f'&#183; SE={p["sd"]:.2f} ({math.exp(p["sd"]):.2f}&#215;)</text>')
    # left/right half mean residual - the "is it bending" readout
    ly = oy + PH - 10
    out.append(f'<text x="{ox+6:.1f}" y="{ly:.1f}" font-size="9" fill="#a8aeb6">'
               f'short-task mean {p["lo"]:+.2f}</text>')
    out.append(f'<text x="{ox+PW-6:.1f}" y="{ly:.1f}" text-anchor="end" font-size="9" fill="#a8aeb6">'
               f'long-task mean {p["hi"]:+.2f}</text>')
    return out


for i, p in enumerate(PANELS):
    s += panel(i, p)

# arm-colour legend, parked in the empty sixth slot
ox = PL + 2 * (PW + GX)
oy = PT + 1 * (PH + GY)
s.append(f'<text x="{ox:.1f}" y="{oy-30:.1f}" font-size="13" font-weight="700" fill="#1b1f24">Reading it</text>')
notes = [
    "Points scattered evenly above and below the zero",
    "line, with no wedge or curve, mean the semi-log",
    "form fits and the low R² is honest scatter.",
    "",
    "A left-to-right drift in the two half-means, or",
    "a band that widens with task length, means the",
    "straight line is the wrong shape — not just noisy.",
]
for i, t in enumerate(notes):
    s.append(f'<text x="{ox:.1f}" y="{oy+8+i*17:.1f}" font-size="11" fill="#5b6571">{t}</text>')
ly = oy + 8 + len(notes) * 17 + 14
s.append(f'<text x="{ox:.1f}" y="{ly:.1f}" font-size="10.5" font-weight="700" fill="#8a929c">POOLED PANEL COLOURS</text>')
for i, arm in enumerate(A_SIDE + B_SIDE):
    cx = ox + 8 + (i % 3) * 116
    cy = ly + 20 + (i // 3) * 20
    s.append(f'<circle cx="{cx:.1f}" cy="{cy-4:.1f}" r="4.5" fill="{COLOR[arm]}" opacity="0.75"/>')
    s.append(f'<text x="{cx+10:.1f}" y="{cy:.1f}" font-size="10.5" fill="#5b6571">{arm}</text>')

s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-14}" text-anchor="middle" font-size="12" fill="#5b6571">'
         f'baseline (cold) turns for the task</text>')
s.append(f'<text x="16" y="{H/2:.1f}" text-anchor="middle" font-size="12" fill="#5b6571" '
         f'transform="rotate(-90 16 {H/2:.1f})">residual, ln(ratio) &#8722; fit</text>')
s.append('</svg>')

out_html = os.path.join(HERE, "turns_ratio_residuals.html")
open(out_html, "w").write(
    f'<!doctype html><meta charset="utf-8"><title>turns ratio residuals</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
print("wrote", out_html)

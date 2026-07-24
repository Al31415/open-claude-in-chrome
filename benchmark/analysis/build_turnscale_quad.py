#!/usr/bin/env python3
"""Tests the hypothesis "turn savings accelerate with task length" (quadratic,
not just linear) for the four arms that ever help (5a, 5b, 6a, 6b - recipe and
warm-up+recipe). Small multiples: one panel per arm, %-turns-saved vs cold
plotted against baseline (cold) turns per task, with both a linear and a
quadratic (degree-2) least-squares fit overlaid, R^2 for each. Pure-python
regression (no numpy dependency) via Gaussian elimination on the normal
equations. n=12 tasks per arm - too few for a confident verdict, so this is
built to let the reader see the curvature directly, not to assert one.
Chrome headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
L = D["turns"]["scale"]
COLOR = {a: c for a, c in D["dist_byleg"]["color"].items() if a in ("5a", "5b", "6a", "6b")}
ARMS = ["5a", "5b", "6a", "6b"]

def solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for j in range(col, n + 1): M[col][j] /= pv
        for r in range(n):
            if r != col:
                f = M[r][col]
                for j in range(col, n + 1): M[r][j] -= f * M[col][j]
    return [M[i][n] for i in range(n)]

def fit_poly(xs, ys, deg):
    n = len(xs)
    XT_X = [[sum(x ** (i + j) for x in xs) for j in range(deg + 1)] for i in range(deg + 1)]
    XT_y = [sum((x ** i) * y for x, y in zip(xs, ys)) for i in range(deg + 1)]
    coefs = solve(XT_X, XT_y)
    pred = [sum(c * (x ** i) for i, c in enumerate(coefs)) for x in xs]
    ybar = sum(ys) / n
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, pred))
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return coefs, r2

DATA = {}
for arm in ARMS:
    xs, ys = [], []
    for t in L["tasks"]:
        bt = t["bturns"]; sv = t["sv"].get(arm)
        if sv is None: continue
        xs.append(bt); ys.append(sv / bt * 100)
    lin_c, lin_r2 = fit_poly(xs, ys, 1)
    quad_c, quad_r2 = fit_poly(xs, ys, 2)
    DATA[arm] = {"xs": xs, "ys": ys, "lin": lin_c, "lin_r2": lin_r2, "quad": quad_c, "quad_r2": quad_r2}

PW, PH = 500, 380
PL, PR, PT, PB = 60, 18, 44, 44
COLS = 2
W = PW * COLS
H = PH * 2

xmax = max(max(d["xs"]) for d in DATA.values()) * 1.08
ymin = min(min(d["ys"]) for d in DATA.values()) * 1.15
ymax = max(max(d["ys"]) for d in DATA.values()) * 1.15

def panel(arm, ox, oy):
    d = DATA[arm]
    col = COLOR[arm]
    def X(v): return ox + PL + (PW - PL - PR) * v / xmax
    def Y(v): return oy + PT + (PH - PT - PB) * (ymax - v) / (ymax - ymin)
    out = []
    for g in range(0, int(xmax) + 1, 20):
        out.append(f'<line x1="{X(g):.1f}" y1="{oy+PT}" x2="{X(g):.1f}" y2="{oy+PH-PB}" stroke="#f2f1ed"/>')
        out.append(f'<text x="{X(g):.1f}" y="{oy+PH-PB+16}" text-anchor="middle" font-size="9" fill="#8a929c">{g}</text>')
    ystep = 20 if ymax - ymin > 60 else 10
    yg = ystep * (int(ymin) // ystep)
    while yg <= ymax:
        out.append(f'<line x1="{ox+PL:.1f}" y1="{Y(yg):.1f}" x2="{ox+PW-PR:.1f}" y2="{Y(yg):.1f}" stroke="#f7f6f2"/>')
        out.append(f'<text x="{ox+PL-6:.1f}" y="{Y(yg)+3:.1f}" text-anchor="end" font-size="9" fill="#8a929c">{yg:+d}%</text>')
        yg += ystep
    out.append(f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(xmax):.1f}" y2="{Y(0):.1f}" stroke="#c9c7c1" stroke-width="1.2"/>')
    out.append(f'<text x="{ox+PL}" y="{oy+22}" font-size="13" font-weight="700" fill="{col}">{arm}</text>')
    out.append(f'<text x="{ox+PW-PR}" y="{oy+22}" text-anchor="end" font-size="9.5" fill="#8a929c">linear R&#178;={d["lin_r2"]:.2f} &#183; quad R&#178;={d["quad_r2"]:.2f}</text>')
    # linear fit (dashed gray)
    a0, a1 = d["lin"]
    out.append(f'<line x1="{X(0):.1f}" y1="{Y(a0):.1f}" x2="{X(xmax):.1f}" y2="{Y(a0+a1*xmax):.1f}" stroke="#8a929c" stroke-width="1.4" stroke-dasharray="5 4"/>')
    # quadratic fit (solid, arm color)
    b0, b1, b2 = d["quad"]
    n_seg = 40
    pts = []
    for i in range(n_seg + 1):
        x = xmax * i / n_seg
        y = b0 + b1 * x + b2 * x * x
        pts.append(f"{X(x):.1f},{Y(y):.1f}")
    out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="2.2"/>')
    # scatter
    for x, y in zip(d["xs"], d["ys"]):
        out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1.2" opacity="0.9"/>')
    return "\n".join(out)

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H+40}" width="{W}" height="{H+40}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H+40}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="22" font-size="15" font-weight="700" fill="#1b1f24">Does turn saving accelerate with task length? linear vs. quadratic fit, per arm</text>')
for i, arm in enumerate(ARMS):
    ox = (i % COLS) * PW
    oy = 40 + (i // COLS) * PH
    s.append(panel(arm, ox, oy))
s.append(f'<text x="{PL}" y="{H+36}" font-size="10" fill="#8a929c">x: baseline (cold) turns for the task &#183; y: % turns saved vs. cold &#183; dashed = linear fit &#183; solid = quadratic fit &#183; n=12 tasks per arm</text>')
s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "turnscale_quad.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
for arm in ARMS:
    d = DATA[arm]
    print(f"{arm}: linear R2={d['lin_r2']:.3f}  quad R2={d['quad_r2']:.3f}  quad_coef={d['quad'][2]:+.5f}")
print("wrote", os.path.join(HERE, "turnscale_quad.html"))

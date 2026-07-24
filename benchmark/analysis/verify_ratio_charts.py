#!/usr/bin/env python3
"""Independent verification of the three log-y ratio charts (time, turns,
thinking). Motivated by a fair question: on the rendered chart the pixel gap
0.5x -> 1x is NOT the same as 1x -> 1.5x, so is the axis (and therefore every
point and fit line) drawn wrong?

On a log axis the answer must be: equal RATIOS get equal pixels. 0.5x -> 1x is
a factor-2 step; 1x -> 1.5x is a factor-1.5 step, so its gap SHOULD be smaller
(by exactly ln1.5/ln2 = 0.585). The charts now use a sqrt(2) tick ladder
(0.5, 0.71, 1, 1.41, 2) where every step is the same factor, so every gap is
the same number of pixels.

This script does not trust any of that - it re-derives everything from the raw
data (capstone.json / thinking_per_task.json), recomputes the coordinate maps
and OLS fits from scratch, then parses the emitted SVG and asserts, numerically:
  1. every y gridline sits exactly where ln-interpolation puts it;
  2. successive gridline gaps are pixel-identical (the sqrt-2 ladder);
  3. the log midpoint identity Y(a)+Y(b) = 2*Y(sqrt(a*b)) holds on the axis map;
  4. every plotted point matches an independently recomputed (x, y) within
     rounding tolerance (0.06px - the SVG prints 1 decimal), and the point
     counts match exactly (including the off-scale top ticks);
  5. every fit polyline's sampled vertices match exp(b0 + b1*x) re-derived by
     a from-scratch OLS of ln(ratio) on x, at every one of its 41 samples.
Exit code 0 with a PASS table means the representation is faithful."""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
CAP = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                            open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
BY = {a["short"]: a for a in CAP["arms"]}
COLOR = CAP["dist_byleg"]["color"]
TPT = json.load(open(os.path.join(HERE, "thinking_per_task.json")))

A_SIDE = ["2a", "3a", "4a"]; B_SIDE = ["2b", "3b", "4b"]; SOLO = ["5b", "6a", "6b"]
COL_A, COL_B = "#c2703d", "#2f7a8c"
YLO, YHI = 0.45, 2.0
W, PL, PR, PT, PB, H = 1300, 66, 300, 78, 60, 620
R2 = 2 ** 0.5
TOL = 0.06  # svg prints 1 decimal -> max rounding error 0.05

def ols_ln(xs, ys):
    lys = [math.log(y) for y in ys]
    n = len(xs); sx = sum(xs); sy = sum(lys)
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, lys))
    b1 = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return (sy - b1 * sx) / n, b1

def base_map(metric):
    """(per-task baseline value, per-arm per-task value) for one metric."""
    if metric == "thinking":
        base = {t: (sum(TPT[a][t] for a in ("1a", "1b", "1c")) / 3) / 1000 for t in TPT["1a"]}
        armv = {arm: {t: TPT[arm][t] / 1000 for t in TPT[arm]} for arm in A_SIDE + B_SIDE + SOLO}
        return base, armv
    key = "min" if metric == "time" else "turns"
    base = {}
    for s in ("1a", "1b", "1c"):
        for pt in BY[s]["per_task"]:
            base.setdefault(pt["t"], []).append(pt[key])
    base = {t: sum(v) / len(v) for t, v in base.items()}
    armv = {arm: {pt["t"]: pt[key] for pt in BY[arm]["per_task"]} for arm in A_SIDE + B_SIDE + SOLO}
    return base, armv

CHARTS = [
    ("time", "ratio_decay.html", 1.1),
    ("turns", "turns_ratio_decay.html", 1.05),
    ("thinking", "thinking_ratio_decay.html", 1.08),
]

failures = []
for metric, fname, xpad in CHARTS:
    html = open(os.path.join(HERE, fname)).read()
    base, armv = base_map(metric)
    xmax = max(base.values()) * xpad
    def X(v): return PL + (W - PL - PR) * v / xmax
    def Y(v): return PT + (H - PT - PB) * (math.log(YHI) - math.log(max(v, YLO))) / (math.log(YHI) - math.log(YLO))

    # ---- 1+2: gridlines ----
    grid_y = sorted(float(m.group(1)) for m in re.finditer(
        rf'<line x1="{PL}" y1="([0-9.]+)" x2="{W-PR}" y2="[0-9.]+" stroke="#(?:c9c7c1|dedbd3)"', html))
    ladder = [2, R2, 1, 1 / R2, 0.5]
    exp_y = sorted(round(Y(g), 1) for g in ladder)
    ok_grid = len(grid_y) == 5 and all(abs(a - b) <= TOL for a, b in zip(grid_y, exp_y))
    gaps = [round(b - a, 2) for a, b in zip(grid_y, grid_y[1:])]
    ok_equal = max(gaps) - min(gaps) <= 0.11  # each endpoint rounded to 0.1
    # ---- 3: log midpoint identity on the axis map itself ----
    ok_mid = all(abs(Y(a) + Y(b) - 2 * Y(math.sqrt(a * b))) < 1e-9
                 for a, b in ((0.5, 2), (0.5, 1), (1, 2), (0.6, 1.7)))

    # ---- 4: points ----
    svg_pts = [(float(m.group(1)), float(m.group(2)), m.group(3)) for m in re.finditer(
        r'<circle cx="([0-9.]+)" cy="([0-9.]+)" r="(4|4\.5)" ', html)]
    exp_pts, exp_ticks = [], 0
    for group, r in ((SOLO, "4.5"), (A_SIDE + B_SIDE, "4")):
        for arm in group:
            for t, bv in base.items():
                v = armv[arm].get(t)
                if v is None: continue
                ratio = v / bv
                if ratio > YHI:
                    exp_ticks += 1
                else:
                    exp_pts.append((round(X(bv), 1), round(Y(ratio), 1), r))
    n_ticks = len(re.findall(r'<line x1="[0-9.]+" y1="%s" x2="[0-9.]+" y2="%s"' %
                             (f"{Y(YHI):.1f}", f"{Y(YHI)+9:.1f}"), html))
    unmatched = []
    pool = list(svg_pts)
    for ex, ey_, er in exp_pts:
        hit = next((p for p in pool if p[2] == er and abs(p[0] - ex) <= TOL and abs(p[1] - ey_) <= TOL), None)
        if hit is None:
            unmatched.append((ex, ey_, er))
        else:
            pool.remove(hit)
    ok_pts = not unmatched and not pool and n_ticks == exp_ticks

    # ---- 5: fit lines, all 41 samples per series ----
    ok_fit, fit_checked = True, 0
    series = [(arm, COLOR[arm], [(base[t], armv[arm][t] / base[t]) for t in base if t in armv[arm]])
              for arm in SOLO]
    for side, col, arms in (("A", COL_A, A_SIDE), ("B", COL_B, B_SIDE)):
        pts = [(base[t], armv[a][t] / base[t]) for t in base for a in arms if t in armv[a]]
        series.append((side, col, pts))
    for name, col, pts in series:
        b0, b1 = ols_ln([p[0] for p in pts], [p[1] for p in pts])
        m = re.search(rf'<path d="(M [0-9. L]+)" fill="none" stroke="{col}"', html)
        if not m:
            ok_fit = False; failures.append(f"{metric}: fit path missing for {name}"); continue
        verts = re.findall(r'([0-9.]+) ([0-9.]+)', m.group(1))
        for i, (vx, vy) in enumerate(verts):
            xd = xmax * i / 40
            if abs(float(vx) - X(xd)) > TOL or abs(float(vy) - Y(math.exp(b0 + b1 * xd))) > TOL:
                ok_fit = False
                failures.append(f"{metric}: fit vertex {i} of {name} off by "
                                f"({float(vx)-X(xd):+.2f},{float(vy)-Y(math.exp(b0+b1*xd)):+.2f})px")
        fit_checked += len(verts)

    for cond, msg in ((ok_grid, "gridline positions"), (ok_equal, "equal tick gaps"),
                      (ok_mid, "log midpoint identity"), (ok_pts, "point positions/counts")):
        if not cond:
            failures.append(f"{metric}: FAILED {msg}")
    print(f"{metric:9} gridlines@{grid_y} gaps={gaps} "
          f"{'PASS' if ok_grid and ok_equal else 'FAIL'} | midpoint {'PASS' if ok_mid else 'FAIL'} | "
          f"points {len(exp_pts)} matched, {exp_ticks} off-scale ticks "
          f"{'PASS' if ok_pts else 'FAIL (unmatched=%d leftovers=%d ticks=%d)' % (len(unmatched), len(pool), n_ticks)} | "
          f"fit vertices {fit_checked} {'PASS' if ok_fit else 'FAIL'}")

if failures:
    print("\nFAILURES:"); [print(" -", f) for f in failures]
    sys.exit(1)
print("\nALL CHECKS PASS: axes, points, and fit lines match the math exactly.")

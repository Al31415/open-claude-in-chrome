#!/usr/bin/env python3
"""Why forking the session into context cost what it did: per-turn latency
against the context carried per turn, one point per arm. Eleven arms sit in a
53-93k cluster at 3.2-4.7 s/turn; 4a and 4b are the two that left it. The
straight line is the univariate OLS of seconds on context across the 13 arms -
enough to show the relation is linear and steep, with the capstone's
multivariate coefficient (context held against output tokens) quoted alongside
since that is the number the writeup uses for the context-load factor. Both are
recomputed/read here rather than typed in. Chrome headless -> PNG."""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
COLOR = D["dist_byleg"]["color"]
TC = D["turncost"]
ARMS = [{"short": a["short"], "ctx": a["ctx"], "sec": a["sec"]} for a in TC["arms"]]
COEF, R2M = TC["coef"], TC["r2"]
HILITE = {"4a", "4b"}

xs = [a["ctx"] for a in ARMS]; ys = [a["sec"] for a in ARMS]
n = len(xs)
sx, sy = sum(xs), sum(ys)
b1 = (n * sum(x * y for x, y in zip(xs, ys)) - sx * sy) / (n * sum(x * x for x in xs) - sx * sx)
b0 = (sy - b1 * sx) / n
ybar = sy / n
r2 = 1 - sum((y - (b0 + b1 * x)) ** 2 for x, y in zip(xs, ys)) / sum((y - ybar) ** 2 for y in ys)
print(f"univariate: sec/turn = {b0:.2f} + {b1*100:.2f} per 100k ctx   R2={r2:.3f}  n={n}")
print(f"capstone multivariate: fixed {COEF['fixed']}s + {COEF['ctx']}s per 100k ctx "
      f"{COEF['gen']}s per 100 output tok   R2={R2M}")
cold = [a for a in ARMS if a["short"] in ("1a", "1b", "1c")]
cs = sum(a["sec"] for a in cold) / 3; cc = sum(a["ctx"] for a in cold) / 3
for s_ in ("4a", "4b"):
    a = next(x for x in ARMS if x["short"] == s_)
    print(f"  {s_}: ctx {a['ctx']}k ({a['ctx']/cc:.1f}x cold {cc:.0f}k)   "
          f"sec/turn {a['sec']} ({a['sec']/cs:.1f}x cold {cs:.2f})")

W, H = 1120, 620
PL, PR, PT, PB = 74, 210, 96, 66
XMAX, YMAX = 520, 12.6
def X(v): return PL + (W - PL - PR) * v / XMAX
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / YMAX

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="30" font-size="18" font-weight="700" fill="#1b1f24">'
         f'Context is the latency: seconds per turn against context per turn</text>')
s.append(f'<text x="{PL}" y="50" font-size="12.5" fill="#8a929c">'
         f'one point per arm, all 13 &#183; x is the tokens carried into every turn (cache reads + writes + fresh input), '
         f'y is that arm\'s real measured seconds per turn</text>')

for g in range(0, YMAX_I := 13, 2):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}</text>')
for g in range(0, XMAX + 1, 100):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{Y(0):.1f}" stroke="#f7f6f3"/>')
    s.append(f'<text x="{X(g):.1f}" y="{Y(0)+20:.1f}" text-anchor="middle" font-size="11" fill="#8a929c">{g}k</text>')

s.append(f'<path d="M {X(0):.1f} {Y(b0):.1f} L {X(XMAX):.1f} {Y(b0+b1*XMAX):.1f}" '
         f'stroke="#c9c7c1" stroke-width="2.4" stroke-dasharray="9 6" fill="none"/>')

# the eleven arms that never left the cluster, boxed once instead of eleven times
cl = [a for a in ARMS if a["short"] not in HILITE]
cx0, cx1 = min(a["ctx"] for a in cl), max(a["ctx"] for a in cl)
cy0, cy1 = min(a["sec"] for a in cl), max(a["sec"] for a in cl)
s.append(f'<rect x="{X(cx0)-16:.1f}" y="{Y(cy1)-16:.1f}" width="{X(cx1)-X(cx0)+32:.1f}" '
         f'height="{Y(cy0)-Y(cy1)+32:.1f}" rx="10" fill="none" stroke="#c9c7c1" stroke-width="1.3"/>')
s.append(f'<text x="{X(cx1)+24:.1f}" y="{Y(cy1)-8:.1f}" font-size="11.5" font-weight="700" fill="#5b6571">'
         f'the other 11 arms</text>')
s.append(f'<text x="{X(cx1)+24:.1f}" y="{Y(cy1)+8:.1f}" font-size="10.5" fill="#8a929c">'
         f'{cx0:.0f}&#8211;{cx1:.0f}k context &#183; {cy0:.2f}&#8211;{cy1:.2f} s/turn</text>')

for a in ARMS:
    big = a["short"] in HILITE
    col = COLOR[a["short"]]
    px, py = X(a["ctx"]), Y(a["sec"])
    s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{9 if big else 5}" fill="{col}" '
             f'stroke="#fff" stroke-width="{2 if big else 1}" opacity="{0.95 if big else 0.75}"/>')
    if big:
        s.append(f'<text x="{px:.1f}" y="{py-18:.1f}" text-anchor="middle" font-size="14" '
                 f'font-weight="700" fill="{col}">{a["short"]}</text>')
        s.append(f'<text x="{px:.1f}" y="{py+26:.1f}" text-anchor="middle" font-size="11" fill="#5b6571">'
                 f'{a["ctx"]:.0f}k &#183; {a["sec"]:.2f}s</text>')
        s.append(f'<text x="{px:.1f}" y="{py+40:.1f}" text-anchor="middle" font-size="10.5" fill="#c13a2e">'
                 f'{a["ctx"]/cc:.1f}&#215; context &#183; {a["sec"]/cs:.1f}&#215; s/turn</text>')

bx, by = W - PR + 16, PT + 8
s.append(f'<text x="{bx}" y="{by}" font-size="11.5" font-weight="700" fill="#5b6571">FITTED COST OF CONTEXT</text>')
lines = [(f'across these 13 arms', "#8a929c"),
         (f'+{b1*100:.2f} s/turn per 100k', "#1b1f24"),
         (f'R&#178; = {r2:.2f}', "#8a929c"),
         ("", ""),
         ('holding output tokens fixed', "#8a929c"),
         (f'+{COEF["ctx"]} s/turn per 100k', "#1b1f24"),
         (f'R&#178; = {R2M}', "#8a929c")]
for i, (t, c) in enumerate(lines):
    if not t: continue
    s.append(f'<text x="{bx}" y="{by+22+i*17:.1f}" font-size="{12 if c=="#1b1f24" else 11}" '
             f'font-weight="{700 if c=="#1b1f24" else 400}" fill="{c}">{t}</text>')

s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-16}" text-anchor="middle" font-size="12.5" fill="#5b6571">'
         f'context carried per turn (thousands of tokens)</text>')
s.append(f'<text x="20" y="{(PT+Y(0))/2:.1f}" text-anchor="middle" font-size="12.5" fill="#5b6571" '
         f'transform="rotate(-90 20 {(PT+Y(0))/2:.1f})">real measured seconds per turn</text>')
s.append('</svg>')

open(os.path.join(HERE, "context_latency.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><title>context latency</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
print("wrote", os.path.join(HERE, "context_latency.html"))

#!/usr/bin/env python3
"""Scalar space, extended with the four phase-7 arms.

Same axes, same baseline crosshair and same 13 original arms as
scalar_space.png (build_scalar_intro.py), plus the recording-system comparison
plotted on top: 7a/7b (phase-3 regime) and 7c/7d (phase-5 regime), drawn as
diamonds so they read as a different study rather than four more arms of the
original one.

Coordinates use the SAME definitions as the frozen capstone data, verified
against it: x = mean num_turns per task from result_raw.json, y = suite total
run minutes. capstone.json is not modified; the phase-7 points are computed
here from data/exp7*/ so this render stays reproducible from the rollouts.

Each pair is joined by a connector: OCIC -> cowork within one regime. The
connector IS the finding - its direction and length is the effect.

Chrome headless -> PNG.
"""
import json, math, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.load(open(os.path.join(HERE, "capstone.json")))

RENAME = {"CinC": "1a", "OCIC-Ch": "1b", "OCIC-Br": "1c", "2A": "2a", "2B": "2b",
          "3D": "3a", "3C": "3b", "4A": "4a", "4B": "4b", "5B": "5a", "5A": "5b",
          "5C": "6a", "5D": "6b"}
COLOR = {RENAME[k]: v for k, v in D["dist_byleg"]["color"].items()}
ARMS = [{"short": RENAME[a["short"]], "turns": a["turns"], "min": a["min"]}
        for a in D["rankcompare"]["arms"]]
BY = {a["short"]: a for a in ARMS}
P1 = ["1a", "1b", "1c"]
bx = sum(BY[s]["turns"] for s in P1) / len(P1)
by = sum(BY[s]["min"] for s in P1) / len(P1)

# ---- phase 7, computed from the rollouts with the capstone's own definitions
P7_ARMS = [("7a", "exp7a-ocic-analysis", "ocic", "p3"),
           ("7b", "exp7b-cowork-analysis", "cowork", "p3"),
           ("7c", "exp7c-ocic-recipe", "ocic", "p5"),
           ("7d", "exp7d-cowork-recipe", "cowork", "p5")]
P7 = {}
for short, exp, system, regime in P7_ARMS:
    turns, mins = [], 0.0
    for d in sorted(glob.glob(os.path.join(BENCH, "data", exp, "*_r1"))):
        r = json.load(open(os.path.join(d, "result_raw.json")))
        t = json.load(open(os.path.join(d, "timing.json")))["attempts"][-1]
        if r.get("num_turns"):
            turns.append(r["num_turns"])
        mins += (t["t_run_end"] - t["t_run_start"]) / 60.0
    P7[short] = {"short": short, "turns": sum(turns) / len(turns), "min": mins,
                 "system": system, "regime": regime, "n": len(turns)}

COL_OCIC, COL_COWORK = "#1d6fa5", "#c2560f"
P7COL = {"ocic": COL_OCIC, "cowork": COL_COWORK}

W, H = 1180, 720
PL, PR, PT, PB = 74, 240, 74, 74
XMIN, XMAX = 22, 42
YMIN, YMAX = 17, 60
def X(v): return PL + (W - PL - PR) * (v - XMIN) / (XMAX - XMIN)
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / (YMAX - YMIN)

LBL = {"1a": (-11, -9, "end"), "1b": (10, -6, "start"), "1c": (10, 13, "start"),
       "2a": (0, 17, "middle"), "2b": (-11, 4, "end"), "3a": (11, 1, "start"),
       "3b": (11, 4, "start"), "4a": (12, 4, "start"), "4b": (12, 4, "start"),
       "5a": (-9, -9, "end"), "5b": (10, 13, "start"), "6a": (1, -12, "middle")}
P7LBL = {"7a": (-13, 5, "end"), "7b": (0, -15, "middle"),
         "7c": (0, 19, "middle"), "7d": (13, 5, "start")}


def star(cx, cy, ro, ri, n=5):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r*math.cos(a):.2f},{cy + r*math.sin(a):.2f}")
    return "M" + "L".join(pts) + "Z"


def diamond(cx, cy, r):
    return f"M{cx:.1f} {cy-r:.1f} L{cx+r:.1f} {cy:.1f} L{cx:.1f} {cy+r:.1f} L{cx-r:.1f} {cy:.1f} Z"


s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<rect x="{PL}" y="{Y(by):.1f}" width="{X(bx)-PL:.1f}" height="{H-PB-Y(by):.1f}" '
         f'fill="#0f8a5f" fill-opacity="0.055"/>')

for g in range(25, XMAX + 1, 5):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f1f0ec"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="11" fill="#8a929c">{g}</text>')
for g in range(20, YMAX + 1, 10):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f6f5f1"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}m</text>')

s.append(f'<line x1="{X(bx):.1f}" y1="{PT}" x2="{X(bx):.1f}" y2="{H-PB}" stroke="#b0483a" '
         f'stroke-width="1.4" stroke-dasharray="6 5" opacity="0.75"/>')
s.append(f'<line x1="{PL}" y1="{Y(by):.1f}" x2="{W-PR}" y2="{Y(by):.1f}" stroke="#b0483a" '
         f'stroke-width="1.4" stroke-dasharray="6 5" opacity="0.75"/>')
s.append(f'<path d="M{X(bx):.1f} {Y(by)-7:.1f} L{X(bx)+7:.1f} {Y(by):.1f} L{X(bx):.1f} {Y(by)+7:.1f} '
         f'L{X(bx)-7:.1f} {Y(by):.1f} Z" fill="#fff" stroke="#b0483a" stroke-width="1.8"/>')
s.append(f'<text x="{X(bx)+12:.1f}" y="{PT+14:.1f}" font-size="12" font-weight="700" fill="#b0483a">Phase-1 baseline</text>')

bxx, byy = (PL + X(bx)) / 2 + 10, H - PB - 26
s.append(f'<text x="{bxx:.1f}" y="{byy:.1f}" text-anchor="middle" font-size="13" font-style="italic" '
         f'font-weight="700" fill="#0f8a5f">&#8601; better</text>')

# original 13, de-emphasised so the new points read as the foreground
for a in ARMS:
    sh = a["short"]
    cx, cy = X(a["turns"]), Y(a["min"])
    if sh == "6b":
        s.append(f'<path d="{star(cx, cy, 11, 4.6)}" fill="{COLOR[sh]}" stroke="#7a3a00" '
                 f'stroke-width="1.2" opacity="0.75"/>')
        s.append(f'<text x="{cx-14:.1f}" y="{cy+4:.1f}" text-anchor="end" font-size="12" '
                 f'font-weight="700" fill="#7a3a00" opacity="0.9">6b</text>')
        continue
    s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{COLOR[sh]}" stroke="#fff" '
             f'stroke-width="1.2" opacity="0.42"/>')
    dx, dy, anc = LBL[sh]
    s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="11" '
             f'fill="#9aa1a9">{sh}</text>')

# phase-7 pair connectors: OCIC -> cowork inside one regime. Deltas are stated
# in the legend rather than on the line - the two connectors cross the same
# crowded band and midpoint labels collided with 3b/2a.
DELTAS = []
for a_, b_ in (("7a", "7b"), ("7c", "7d")):
    A, B = P7[a_], P7[b_]
    s.append(f'<line x1="{X(A["turns"]):.1f}" y1="{Y(A["min"]):.1f}" x2="{X(B["turns"]):.1f}" '
             f'y2="{Y(B["min"]):.1f}" stroke="#6b7280" stroke-width="1.6" stroke-dasharray="5 4" opacity="0.55"/>')
    DELTAS.append((a_, b_, B["min"] - A["min"], B["turns"] - A["turns"]))

for short, p in P7.items():
    cx, cy = X(p["turns"]), Y(p["min"])
    col = P7COL[p["system"]]
    s.append(f'<path d="{diamond(cx, cy, 9)}" fill="{col}" stroke="#fff" stroke-width="1.8"/>')
    dx, dy, anc = P7LBL[short]
    s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" '
             f'font-weight="800" fill="{col}">{short}</text>')

# legend
lx, ly = W - PR + 18, PT + 6
s.append(f'<text x="{lx}" y="{ly}" font-size="12.5" font-weight="700" fill="#1b1f24">Phase 7</text>')
s.append(f'<text x="{lx}" y="{ly+16}" font-size="10.5" fill="#8a929c">same 6 sessions, two recorders</text>')
rows = [(COL_OCIC, "7a", "OCIC &#183; analysis on disk"),
        (COL_COWORK, "7b", "cowork &#183; analysis on disk"),
        (COL_OCIC, "7c", "OCIC &#183; recipe in prompt"),
        (COL_COWORK, "7d", "cowork &#183; recipe in prompt")]
for i, (col, sh, txt) in enumerate(rows):
    yy = ly + 40 + i * 26
    s.append(f'<path d="{diamond(lx+7, yy-4, 7)}" fill="{col}" stroke="#fff" stroke-width="1.4"/>')
    s.append(f'<text x="{lx+20}" y="{yy}" font-size="11.5" font-weight="700" fill="{col}">{sh}</text>')
    s.append(f'<text x="{lx+38}" y="{yy}" font-size="10.5" fill="#5b6571">{txt}</text>')
yy = ly + 40 + 4 * 26 + 10
s.append(f'<circle cx="{lx+7}" cy="{yy-4}" r="5" fill="#9aa1a9" opacity="0.5"/>')
s.append(f'<text x="{lx+20}" y="{yy}" font-size="10.5" fill="#8a929c">original 13 arms</text>')
s.append(f'<text x="{lx}" y="{yy+24}" font-size="10.5" fill="#8a929c">dashed link = OCIC &#8594; cowork,</text>')
s.append(f'<text x="{lx}" y="{yy+37}" font-size="10.5" fill="#8a929c">within one delivery regime:</text>')
for i, (a_, b_, dmin, dturn) in enumerate(DELTAS):
    s.append(f'<text x="{lx+4}" y="{yy+56+i*15}" font-size="10.5" fill="#6b7280">'
             f'<tspan font-weight="700">{a_}&#8594;{b_}</tspan>  +{dmin:.1f} min, +{dturn:.1f} turns</text>')

s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-22}" text-anchor="middle" font-size="13" fill="#5b6571">'
         f'turns per task (path length) &#8594; more</text>')
s.append(f'<text x="24" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="13" fill="#5b6571" '
         f'transform="rotate(-90 24 {(PT+H-PB)/2:.1f})">latency (minutes, suite) &#8594; slower</text>')
s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">'
         f'The recording-system comparison in the same scalar space</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">'
         f'phase-7 arms (diamonds) over the original 13 (faded) &#183; in both regimes the OCIC point sits '
         f'lower-left of its cowork twin</text>')
s.append('</svg>')

open(os.path.join(HERE, "scalar_space_p7.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><title>scalar space + phase 7</title>'
    f'<style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
print(f"baseline: turns={bx:.2f} latency={by:.2f}")
for sh, p in P7.items():
    print(f"  {sh}  turns={p['turns']:5.1f}  suite={p['min']:5.1f} min  (n={p['n']})  {p['system']}/{p['regime']}")
print("wrote", os.path.join(HERE, "scalar_space_p7.html"))

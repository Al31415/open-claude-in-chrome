#!/usr/bin/env python3
"""Standalone, intro-friendly render of the scalar-space chart (latency vs turns
for all arms). Emphasises 6b (the winner) with a star + halo, and marks the
Phase-1 average as an explicit baseline crosshair with a "better" quadrant.
Emits a self-contained HTML (inline SVG); Chrome headless turns it into a PNG."""
import json, os, math

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

# Phase-1 baseline = the average of every arm in phase 1 (1a, 1b, 1c).
P1 = ["1a", "1b", "1c"]
bx = sum(BY[s]["turns"] for s in P1) / len(P1)
by = sum(BY[s]["min"] for s in P1) / len(P1)

W, H = 1120, 690
PL, PR, PT, PB = 74, 150, 62, 66
XMIN, XMAX = 22, 42
YMIN, YMAX = 17, 60
def X(v): return PL + (W - PL - PR) * (v - XMIN) / (XMAX - XMIN)
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / (YMAX - YMIN)

# per-arm label placement (dx, dy, anchor) tuned to avoid collisions
LBL = {
    "1a": (-11, -9, "end"), "1b": (10, -6, "start"), "1c": (10, 13, "start"),
    "2a": (0, 17, "middle"), "2b": (-11, 4, "end"), "3a": (11, 1, "start"),
    "3b": (11, 4, "start"), "4a": (12, 4, "start"), "4b": (12, 4, "start"),
    "5a": (-9, -9, "end"), "5b": (10, 13, "start"), "6a": (1, -12, "middle"),
}

def star(cx, cy, ro, ri, n=5):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r*math.cos(a):.2f},{cy + r*math.sin(a):.2f}")
    return "M" + "L".join(pts) + "Z"

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')

# "better" quadrant: below-left of the baseline (fewer turns AND faster)
s.append(f'<rect x="{PL}" y="{Y(by):.1f}" width="{X(bx)-PL:.1f}" height="{H-PB-Y(by):.1f}" fill="#0f8a5f" fill-opacity="0.055"/>')

# gridlines
for g in range(25, XMAX + 1, 5):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f1f0ec"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="11" fill="#8a929c">{g}</text>')
for g in range(20, YMAX + 1, 10):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f6f5f1"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}m</text>')

# baseline crosshair
s.append(f'<line x1="{X(bx):.1f}" y1="{PT}" x2="{X(bx):.1f}" y2="{H-PB}" stroke="#b0483a" stroke-width="1.4" stroke-dasharray="6 5" opacity="0.75"/>')
s.append(f'<line x1="{PL}" y1="{Y(by):.1f}" x2="{W-PR}" y2="{Y(by):.1f}" stroke="#b0483a" stroke-width="1.4" stroke-dasharray="6 5" opacity="0.75"/>')
s.append(f'<path d="M{X(bx):.1f} {Y(by)-7:.1f} L{X(bx)+7:.1f} {Y(by):.1f} L{X(bx):.1f} {Y(by)+7:.1f} L{X(bx)-7:.1f} {Y(by):.1f} Z" fill="#fff" stroke="#b0483a" stroke-width="1.8"/>')
s.append(f'<text x="{X(bx)+12:.1f}" y="{PT+14:.1f}" font-size="12" font-weight="700" fill="#b0483a">Phase-1 baseline</text>')
s.append(f'<text x="{X(bx)+12:.1f}" y="{PT+29:.1f}" font-size="10.5" fill="#a56a60">avg of 1a / 1b / 1c</text>')

# "better" label centred in the green quadrant, clear of the 6b corner
bxx, byy = (PL + X(bx)) / 2 + 24, H - PB - 30
s.append(f'<text x="{bxx:.1f}" y="{byy:.1f}" text-anchor="middle" font-size="13" font-style="italic" font-weight="700" fill="#0f8a5f">&#8601; better</text>')
s.append(f'<text x="{bxx:.1f}" y="{byy+16:.1f}" text-anchor="middle" font-size="11" fill="#3f8f6f">fewer turns, faster</text>')

# arm dots (all but 6b). Phase-1 arms get a faint ring tying them to the baseline.
for a in ARMS:
    sh = a["short"]
    if sh == "6b":
        continue
    cx, cy = X(a["turns"]), Y(a["min"])
    col = COLOR[sh]
    if sh in P1:
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="none" stroke="#b0483a" stroke-width="1.3" stroke-dasharray="2.5 2.5" opacity="0.55"/>')
    s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{col}" stroke="#fff" stroke-width="1.4"/>')
    dx, dy, anc = LBL[sh]
    s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="12" font-weight="600" fill="#1b1f24">{sh}</text>')

# 6b: starred winner with halo
w6 = BY["6b"]; cx, cy = X(w6["turns"]), Y(w6["min"]); col = COLOR["6b"]
s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="19" fill="none" stroke="{col}" stroke-width="1.6" opacity="0.45"/>')
s.append(f'<path d="{star(cx, cy, 13.5, 5.6)}" fill="{col}" stroke="#7a3a00" stroke-width="1.5"/>')
s.append(f'<text x="{cx-19:.1f}" y="{cy-8:.1f}" text-anchor="end" font-size="14" font-weight="800" fill="#1b1f24">6b</text>')
s.append(f'<text x="{cx-19:.1f}" y="{cy+7:.1f}" text-anchor="end" font-size="10.5" font-style="italic" fill="#7a3a00">best on both axes</text>')

# axis titles + heading
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-24}" text-anchor="middle" font-size="13" fill="#5b6571">turns per task (path length) &#8594; more</text>')
s.append(f'<text x="24" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="13" fill="#5b6571" transform="rotate(-90 24 {(PT+H-PB)/2:.1f})">latency (minutes, suite) &#8594; slower</text>')
s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">The same arms in scalar space</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">each point is one arm &#183; lower-left is better &#183; the star is the winning method (6b)</text>')
s.append('</svg>')
svg = "\n".join(s)

html = f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}'
out_html = os.path.join(HERE, "scalar_space.html")
open(out_html, "w").write(html)
print("baseline: turns=%.2f  latency=%.2f" % (bx, by))
print("wrote", out_html)

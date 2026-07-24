#!/usr/bin/env python3
"""Six cartoon-annotated variants of "the same arms in scalar space"
(scalar_space.png / build_scalar_intro.py), one per phase, for the "Tying
Them All Together" recap. Same base plot every time - same 13 dots in the
same positions, same axes, same baseline crosshair - so the reader always has
the full picture; only which arms are popped vs. faded, and a phase-specific
hand-drawn-style overlay (arrows, lassos, callouts in one consistent "marker
ink" colour), changes per phase. This is deliberately more playful than the
rest of the deck's charts - big colour, a bit of swagger - because this
section is a recap, not new evidence.

Run: python3 build_phase_highlight.py (builds all 6)."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
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

W, H = 1120, 690
PL, PR, PT, PB = 74, 150, 62, 66
XMIN, XMAX = 22, 42
YMIN, YMAX = 17, 60
def X(v): return PL + (W - PL - PR) * (v - XMIN) / (XMAX - XMIN)
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / (YMAX - YMIN)

INK = "#e8491d"  # the one "cartoon marker" annotation colour, used nowhere else in the deck

LBL = {
    "1a": (-11, -9, "end"), "1b": (10, -6, "start"), "1c": (10, 13, "start"),
    "2a": (0, 17, "middle"), "2b": (-11, 4, "end"), "3a": (11, 1, "start"),
    "3b": (11, 4, "start"), "4a": (12, 4, "start"), "4b": (12, 4, "start"),
    "5a": (-9, -9, "end"), "5b": (10, 13, "start"), "6a": (1, -12, "middle"),
    "6b": (-19, -8, "end"),
}

def star(cx, cy, ro, ri, n=5):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r*math.cos(a):.2f},{cy + r*math.sin(a):.2f}")
    return "M" + "L".join(pts) + "Z"

def straight_arrow(x0, y0, x1, y1, width=3.2, color=INK, dash=None):
    ang = math.atan2(y1 - y0, x1 - x0)
    ah = 10
    a1 = ang + math.radians(150); a2 = ang - math.radians(150)
    head = (f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a1):.1f} {y1+ah*math.sin(a1):.1f} "
            f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a2):.1f} {y1+ah*math.sin(a2):.1f}")
    dasharr = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"{dasharr}/>'
            f'<path d="{head}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>')

def axis_arrows(x0, y0, x1, y1, width=3.2, color=INK):
    """A movement decomposed into its axis components, coordinate-space style:
    one horizontal arrow (the turns delta), then one vertical arrow (the
    latency delta), meeting at the elbow (x1, y0). Segments shorter than a
    few px are skipped rather than drawn as stubs."""
    out = []
    if abs(x1 - x0) >= 8:
        out.append(straight_arrow(x0, y0, x1, y0, width=width, color=color))
    if abs(y1 - y0) >= 8:
        out.append(straight_arrow(x1, y0, x1, y1, width=width, color=color))
    return "".join(out)

def wobble_circle(cx, cy, r, color=INK, width=2.6, wob=3, n=28, dash="1 0"):
    pts = []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        rr = r + (wob if i % 3 == 0 else -wob * 0.4 if i % 3 == 1 else 0)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d = "M" + " ".join(f"{'L' if i else ''}{p[0]:.1f} {p[1]:.1f}" for i, p in enumerate(pts)) + " Z"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}" stroke-linejoin="round"/>'

def note(x, y, text, size=13.5, rot=-2, anchor="start", weight=800, color=INK):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-style="italic" fill="{color}" '
            f'transform="rotate({rot} {x:.1f} {y:.1f})">{text}</text>')

def base_chart(title, subtitle, highlight):
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    s.append(f'<rect x="{PL}" y="{Y(by):.1f}" width="{X(bx)-PL:.1f}" height="{H-PB-Y(by):.1f}" fill="#0f8a5f" fill-opacity="0.05"/>')
    for g in range(25, XMAX + 1, 5):
        s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f1f0ec"/>')
        s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="11" fill="#8a929c">{g}</text>')
    for g in range(20, YMAX + 1, 10):
        s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f6f5f1"/>')
        s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}m</text>')
    s.append(f'<line x1="{X(bx):.1f}" y1="{PT}" x2="{X(bx):.1f}" y2="{H-PB}" stroke="#c9c7c1" stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
    s.append(f'<line x1="{PL}" y1="{Y(by):.1f}" x2="{W-PR}" y2="{Y(by):.1f}" stroke="#c9c7c1" stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
    s.append(f'<text x="{X(bx)+8:.1f}" y="{PT+13:.1f}" font-size="10.5" fill="#8a929c">Phase-1 baseline</text>')
    s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-24}" text-anchor="middle" font-size="13" fill="#5b6571">turns per task (path length) &#8594; more</text>')
    s.append(f'<text x="24" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="13" fill="#5b6571" transform="rotate(-90 24 {(PT+H-PB)/2:.1f})">latency (minutes, suite) &#8594; slower</text>')
    s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">{title}</text>')
    s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">{subtitle}</text>')

    for a in ARMS:
        sh = a["short"]
        if sh == "6b" and "6b" not in highlight:
            continue  # drawn later, starred
        cx, cy = X(a["turns"]), Y(a["min"])
        col = COLOR[sh]
        on = sh in highlight
        if on:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7.5" fill="{col}" stroke="#fff" stroke-width="1.6"/>')
            dx, dy, anc = LBL[sh]
            s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" font-weight="800" fill="#1b1f24">{sh}</text>')
        else:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{col}" opacity="0.28"/>')
    if "6b" in highlight:
        w6 = BY["6b"]; cx, cy = X(w6["turns"]), Y(w6["min"]); col = COLOR["6b"]
        s.append(f'<path d="{star(cx, cy, 12, 5)}" fill="{col}" stroke="#7a3a00" stroke-width="1.3"/>')
        dx, dy, anc = LBL["6b"]
        s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" font-weight="800" fill="#1b1f24">6b</text>')
    return s

def enclosing_circle(shorts, pad=16):
    pts = [(X(BY[s]["turns"]), Y(BY[s]["min"])) for s in shorts]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    r = max(math.hypot(p[0] - cx, p[1] - cy) for p in pts) + pad
    return cx, cy, r

def finish(s, name):
    s.append('</svg>')
    svg = "\n".join(s)
    open(os.path.join(HERE, f"{name}.html"), "w").write(
        f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
    print("wrote", name)

# ---------- Phase 1: tight clustering ----------
s = base_chart("Phase 1 · the control group", "official CinC vs. OCIC, cold - basically the same agent", ["1a", "1b", "1c"])
cx, cy, r = enclosing_circle(P1)
s.append(wobble_circle(cx, cy, r))
s.append(note(cx + r + 14, cy - 12, "practically on top of each other", size=14))
s.append(note(cx + r + 14, cy + 6, "harness swap barely moves the dot", size=11.5, weight=600, rot=-1))
finish(s, "phase1_highlight")

# ---------- Phase 2: 2a/2b, accuracy gain invisible on these axes ----------
s = base_chart("Phase 2 · mounting raw experience", "2a saves latency, not turns; 2b saves neither - but both get more accurate", ["2a", "2b"])
s.append(axis_arrows(X(bx), Y(by), X(BY["2a"]["turns"]), Y(BY["2a"]["min"])))
s.append(axis_arrows(X(bx), Y(by), X(BY["2b"]["turns"]), Y(BY["2b"]["min"])))
cx, cy = X(BY["2b"]["turns"]), Y(BY["2b"]["min"])
shaft_y = Y(by)
s.append(note(cx - 20, shaft_y - 29, "2b got MORE ACCURATE", size=13, anchor="end", rot=2))
s.append(note(cx - 20, shaft_y - 12, "you just can't see it on this chart", size=11, weight=600, anchor="end", rot=1))
finish(s, "phase2_highlight")

# ---------- Phase 3: turns down for both, latency surprise ----------
s = base_chart("Phase 3 · compressing the search tax", "turns drop for both - but 3a's latency doesn't beat 2a. plot twist.", ["2a", "2b", "3a", "3b"])
s.append(axis_arrows(X(BY["2a"]["turns"]), Y(BY["2a"]["min"]), X(BY["3a"]["turns"]), Y(BY["3a"]["min"])))
s.append(axis_arrows(X(BY["2b"]["turns"]), Y(BY["2b"]["min"]), X(BY["3b"]["turns"]), Y(BY["3b"]["min"])))
cx, cy = X(BY["3a"]["turns"]), Y(BY["3a"]["min"])
s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="none" stroke="{INK}" stroke-width="2.4"/>')
s.append(note(cx - 18, cy + 46, "??? still worse than 2a on latency", size=13, anchor="end"))
s.append(note(cx - 18, cy + 63, "fewer turns didn't buy back the time", size=11, weight=600, rot=-1, anchor="end"))
finish(s, "phase3_highlight")

# ---------- Phase 4: latency explosion ----------
s = base_chart("Phase 4 · forking the whole session in", "context explodes, latency follows - turns barely move to compensate", ["3a", "3b", "4a", "4b"])
s.append(axis_arrows(X(BY["3a"]["turns"]), Y(BY["3a"]["min"]), X(BY["4a"]["turns"]), Y(BY["4a"]["min"]), width=4.4))
s.append(axis_arrows(X(BY["3b"]["turns"]), Y(BY["3b"]["min"]), X(BY["4b"]["turns"]), Y(BY["4b"]["min"]), width=4.4))
cx, cy = X(BY["4a"]["turns"]), Y(BY["4a"]["min"])
s.append(note(cx - 6, cy - 18, "latency goes THROUGH THE ROOF", size=16, anchor="middle", rot=-2))
s.append(note(cx - 16, cy + 34, "turns: only a little better.", size=11.5, weight=600, anchor="end", rot=1))
s.append(note(cx - 16, cy + 49, "not worth it.", size=11.5, weight=600, anchor="end", rot=1))
finish(s, "phase4_highlight")

# ---------- Phase 5: recipe, both improve equally, negligible diff, and both
# ahead of every arm from phases 1-4 ----------
s = base_chart("Phase 5 · ditch the workspace, prompt a recipe", "biggest jump yet, and 5a vs. 5b barely matters", ["5a", "5b"])
cx, cy, r = enclosing_circle(["5a", "5b"], pad=18)
s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="{INK}" stroke-width="2.4"/>')
s.append(note(cx - r - 14, cy - 40, "same dot, basically", size=14, anchor="end"))
s.append(note(cx - r - 14, cy - 23, "single vs. per-site recipe = a wash", size=11, weight=600, rot=-1, anchor="end"))
s.append(straight_arrow(cx - r - 16, cy - 32, cx - r * 0.75, cy - r * 0.75, width=2.2))
s.append(note(cx, cy + r + 26, "and this beats EVERY arm from phases 1-4", size=13.5, anchor="middle"))
s.append(note(cx, cy + r + 43, "the whole rest of the field is up and to the right", size=11, weight=600, rot=-1, anchor="middle"))
finish(s, "phase5_highlight")

# ---------- Phase 6: 6a matches 4a's turns for a fraction of the latency; 6b beats both axes ----------
s = base_chart("Phase 6 · does warming up alone pay off?", "6a alone matches 4a's turn savings for a THIRD of the latency tax. then 6b stacks the recipe on top.", ["4a", "6a", "6b"])
s.append(axis_arrows(X(BY["4a"]["turns"]), Y(BY["4a"]["min"]), X(BY["6a"]["turns"]), Y(BY["6a"]["min"]), width=4.6))
cx, cy = X(BY["6a"]["turns"]), Y(BY["6a"]["min"])
midy = (Y(BY["4a"]["min"]) + cy) / 2
s.append(note(cx + 24, midy - 8, "wait, WHAT", size=15))
s.append(note(cx + 24, midy + 9, "1 warm-up example &#8776; the whole fork's turn savings", size=11, weight=600, rot=-1))
s.append(axis_arrows(cx, cy, X(BY["6b"]["turns"]), Y(BY["6b"]["min"]), width=3.4))
s.append(note(PL + 16, cy - 16, "and 6b just wins outright", size=12.5, rot=-2))
finish(s, "phase6_highlight")

print("all 6 written")

#!/usr/bin/env python3
"""Phase-7 variant of the "Tying Them All Together" scalar-space recap.

Same base plot and same annotation system as build_phase_highlight.py: the 13
original arms sit faded in the background, movement is decomposed into its axis
components (horizontal = turns delta, vertical = latency delta), each segment
coloured by its own direction, arrows standing off from the dots.

What differs: the phase-7 arms are drawn as DIAMONDS, because they are a
different study (different recordings) rather than four more arms of the
original one. Two movements are shown, one per delivery regime, each the same
comparison - cowork -> OCIC - so the two vectors are directly comparable and
the growth from one to the other is the finding. Both regimes' magnitudes are
labelled on their own vector. The legend is kept: without it the diamonds are
unreadable.

7e is deliberately excluded: it is not part of a pair, it is the follow-up that
swapped 6b's recipe.

Coordinates use the capstone's own definitions (x = mean num_turns from
result_raw.json, y = suite total run minutes), computed here from data/exp7*/.
capstone.json is not modified. Chrome headless -> PNG.
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

P7_SPEC = [("7a", "exp7a-ocic-analysis", "ocic"), ("7b", "exp7b-cowork-analysis", "cowork"),
           ("7c", "exp7c-ocic-recipe", "ocic"), ("7d", "exp7d-cowork-recipe", "cowork")]
P7 = {}
for short, exp, system in P7_SPEC:
    turns, mins = [], 0.0
    for d in sorted(glob.glob(os.path.join(BENCH, "data", exp, "*_r1"))):
        r = json.load(open(os.path.join(d, "result_raw.json")))
        t = json.load(open(os.path.join(d, "timing.json")))["attempts"][-1]
        if r.get("num_turns"):
            turns.append(r["num_turns"])
        mins += (t["t_run_end"] - t["t_run_start"]) / 60.0
    P7[short] = {"turns": sum(turns) / len(turns), "min": mins, "system": system}

W, H = 1120, 690
PL, PR, PT, PB = 74, 210, 62, 66
XMIN, XMAX = 22, 42
YMIN, YMAX = 17, 60
def X(v): return PL + (W - PL - PR) * (v - XMIN) / (XMAX - XMIN)
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / (YMAX - YMIN)

GOOD, BAD = "#0f8a5f", "#c13a2e"
NOTE, SUB = "#3a4148", "#5b6571"
STAND = 13
COL_OCIC, COL_COWORK = "#1d6fa5", "#c2560f"
P7COL = {"ocic": COL_OCIC, "cowork": COL_COWORK}
LBL = {"1a": (-11, -9, "end"), "1b": (10, -6, "start"), "1c": (10, 13, "start"),
       "2a": (0, 17, "middle"), "2b": (-11, 4, "end"), "3a": (11, 1, "start"),
       "3b": (11, 4, "start"), "4a": (12, 4, "start"), "4b": (12, 4, "start"),
       "5a": (-9, -9, "end"), "5b": (10, 13, "start"), "6a": (1, -12, "middle"),
       "6b": (-19, -8, "end")}
P7LBL = {"7a": (-14, 5, "end"), "7b": (0, -17, "middle"),
         "7c": (0, 21, "middle"), "7d": (14, 5, "start")}


def arrow(x0, y0, x1, y1, color, width=3.2):
    ang = math.atan2(y1 - y0, x1 - x0); ah = 9
    a1, a2 = ang + math.radians(150), ang - math.radians(150)
    head = (f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a1):.1f} {y1+ah*math.sin(a1):.1f} "
            f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a2):.1f} {y1+ah*math.sin(a2):.1f}")
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"/><path d="{head}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" fill="none"/>')


def axis_arrows(x0, y0, x1, y1, width=3.2, row_shift=0.0):
    out, yrow = [], y0 + row_shift
    if abs(x1 - x0) >= 14:
        out.append(arrow(x0 + (STAND if x1 > x0 else -STAND), yrow, x1, yrow,
                         GOOD if x1 < x0 else BAD, width))
    if abs(y1 - y0) >= 14:
        out.append(arrow(x1, yrow, x1, y1 - (STAND if y1 > y0 else -STAND),
                         GOOD if y1 > y0 else BAD, width))
    return "".join(out)


def note(x, y, text, size=13.5, rot=-2, anchor="start", weight=800, color=NOTE):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-style="italic" fill="{color}" '
            f'transform="rotate({rot} {x:.1f} {y:.1f})">{text}</text>')


def diamond(cx, cy, r):
    return f"M{cx:.1f} {cy-r:.1f} L{cx+r:.1f} {cy:.1f} L{cx:.1f} {cy+r:.1f} L{cx-r:.1f} {cy:.1f} Z"


s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<rect x="{PL}" y="{Y(by):.1f}" width="{X(bx)-PL:.1f}" height="{H-PB-Y(by):.1f}" '
         f'fill="#0f8a5f" fill-opacity="0.05"/>')
for g in range(25, XMAX + 1, 5):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f1f0ec"/>')
    s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="11" fill="#8a929c">{g}</text>')
for g in range(20, YMAX + 1, 10):
    s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f6f5f1"/>')
    s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}m</text>')
s.append(f'<line x1="{X(bx):.1f}" y1="{PT}" x2="{X(bx):.1f}" y2="{H-PB}" stroke="#c9c7c1" '
         f'stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
s.append(f'<line x1="{PL}" y1="{Y(by):.1f}" x2="{W-PR}" y2="{Y(by):.1f}" stroke="#c9c7c1" '
         f'stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
s.append(f'<text x="{X(bx)+8:.1f}" y="{PT+13:.1f}" font-size="10.5" fill="#8a929c">Phase-1 baseline</text>')
s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-24}" text-anchor="middle" font-size="13" fill="#5b6571">'
         f'turns per task (path length) &#8594; more</text>')
s.append(f'<text x="24" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="13" fill="#5b6571" '
         f'transform="rotate(-90 24 {(PT+H-PB)/2:.1f})">latency (minutes, suite) &#8594; slower</text>')
s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">'
         f'Phase 7 &#183; OCIC recordings vs Claude Cowork recordings</text>')
s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">'
         f'same six sessions, captured by both recorders at once &#183; each arrow is the ground OCIC '
         f'recovers over Cowork, inside one delivery regime</text>')

# the 13 original arms, faded to background
for a in ARMS:
    s.append(f'<circle cx="{X(a["turns"]):.1f}" cy="{Y(a["min"]):.1f}" r="4.5" '
             f'fill="{COLOR[a["short"]]}" opacity="0.26"/>')

# the two movements, axis-decomposed, drawn cowork -> OCIC so each arrow is
# the ground OCIC recovers. Both components improve, so every segment is
# green; the point of the figure is that the second is far longer.
for (src, dst), shift in ((("7b", "7a"), -7), (("7d", "7c"), +7)):
    A, B = P7[src], P7[dst]
    s.append(axis_arrows(X(A["turns"]), Y(A["min"]), X(B["turns"]), Y(B["min"]), row_shift=shift))

# per-pair magnitude labels, each parked on its own vector
mag = []
for src, dst in (("7b", "7a"), ("7d", "7c")):
    A, B = P7[src], P7[dst]
    mag.append((src, dst, A["min"] - B["min"], A["turns"] - B["turns"]))

(a3, b3, dm3, dt3), (a5, b5, dm5, dt5) = mag
# Each magnitude label hugs its OWN vector: the on-disk one sits above 7b
# (where its short arrow starts), the in-prompt one above the long arrow's
# left run. Parking both in one row read as if each labelled the other.
s.append(f'<text x="{X(35.9):.1f}" y="{Y(29.3):.1f}" text-anchor="middle" font-size="12" '
         f'font-weight="800" fill="{GOOD}">&#8722;{dt3:.1f} turns, &#8722;{dm3:.1f} min</text>')
s.append(f'<text x="{X(35.9):.1f}" y="{Y(28.6):.1f}" text-anchor="middle" font-size="10.5" '
         f'fill="{SUB}">analysis on disk (7b &#8594; 7a)</text>')
s.append(f'<text x="{X(31.9):.1f}" y="{Y(27.5):.1f}" text-anchor="middle" font-size="13" '
         f'font-weight="800" fill="{GOOD}">&#8722;{dt5:.1f} turns, &#8722;{dm5:.1f} min</text>')
s.append(f'<text x="{X(31.9):.1f}" y="{Y(26.8):.1f}" text-anchor="middle" font-size="10.5" '
         f'fill="{SUB}">recipe in prompt (7d &#8594; 7c)</text>')

# commentary, same voice as the other phase graphics
s.append(note(X(29.2), Y(37.5), "OCIC's raw recordings beat pre-distilled ones", size=13.5))
s.append(note(X(29.2), Y(35.6), "true in both regimes, and by three times as much", size=11, weight=600, rot=-1))
s.append(note(X(29.2), Y(34.2), "once the material has to carry a prompt", size=11, weight=600, rot=-1))

# phase-7 dots on top
for short, p in P7.items():
    cx, cy = X(p["turns"]), Y(p["min"])
    col = P7COL[p["system"]]
    s.append(f'<path d="{diamond(cx, cy, 9)}" fill="{col}" stroke="#fff" stroke-width="1.8"/>')
    dx, dy, anc = P7LBL[short]
    s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" '
             f'font-weight="800" fill="{col}">{short}</text>')

# legend (kept: the diamonds are unreadable without it)
lx, ly = W - PR + 14, PT + 8
s.append(f'<text x="{lx}" y="{ly}" font-size="12.5" font-weight="700" fill="#1b1f24">Phase 7</text>')
s.append(f'<text x="{lx}" y="{ly+15}" font-size="10" fill="#8a929c">same 6 sessions, two recorders</text>')
for i, (col, sh, txt) in enumerate([(COL_OCIC, "7a", "OCIC &#183; on disk"),
                                    (COL_COWORK, "7b", "cowork &#183; on disk"),
                                    (COL_OCIC, "7c", "OCIC &#183; in prompt"),
                                    (COL_COWORK, "7d", "cowork &#183; in prompt")]):
    yy = ly + 38 + i * 24
    s.append(f'<path d="{diamond(lx+7, yy-4, 7)}" fill="{col}" stroke="#fff" stroke-width="1.4"/>')
    s.append(f'<text x="{lx+20}" y="{yy}" font-size="11.5" font-weight="700" fill="{col}">{sh}</text>')
    s.append(f'<text x="{lx+38}" y="{yy}" font-size="10" fill="#5b6571">{txt}</text>')
yy = ly + 38 + 4 * 24 + 12
s.append(f'<circle cx="{lx+7}" cy="{yy-4}" r="4.5" fill="#9aa1a9" opacity="0.5"/>')
s.append(f'<text x="{lx+20}" y="{yy}" font-size="10" fill="#8a929c">the original 13 arms</text>')
s.append(f'<line x1="{lx+2}" y1="{yy+18}" x2="{lx+16}" y2="{yy+18}" stroke="{GOOD}" stroke-width="3" stroke-linecap="round"/>')
s.append(f'<text x="{lx+22}" y="{yy+22}" font-size="10" fill="#8a929c">OCIC better on that axis</text>')
s.append('</svg>')

open(os.path.join(HERE, "phase7_highlight.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{"".join(s)}')
for src, dst, dm, dt in mag:
    print(f"  {src}->{dst}: -{dm:.1f} min, -{dt:.1f} turns (OCIC advantage)")
print("wrote phase7_highlight.html")

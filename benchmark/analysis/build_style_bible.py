#!/usr/bin/env python3
"""style_bible.html: the model sheet for the per-experiment iconography.
Parametric flat-vector SVG. Monochrome by design (color is reserved).

Metaphor: an exam student. Zones, none overlapping:
  BROW mark      -> harness (logo stamped on the forehead)
  DESK           -> browser (emblem on the desk face)
  EXAM paper     -> the task (always present)
  DESK SURFACE   -> present-environment knowledge (binder=raw, +sheet=analysis)
  EXAM-CLIPPED   -> in-task knowledge (recipe printed onto the exam)
  THOUGHT BUBBLE -> already-internalized knowledge (what it read/did before)
  FACE           -> context load = tiredness (the cost)
"""
import os, base64
BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

def img_src(rel):  # reference the PNG by relative URL (HTML sits one dir above analysis/img/)
    p = os.path.join(HERE, rel)
    if not os.path.isfile(p):
        return ""
    return f"analysis/{rel}"

INK = "#2b2a27"; CREAM = "#f4f1ea"; PAPER = "#fdfbf5"; DESKC = "#efe9db"; GD = "#8f8c85"
G_FAINT = "#c9c6bf"; G_DARK = "#8f8c85"; HAIR = "#3a3833"

# ---------- glyphs ----------
# NOTE: the app under test (food-delivery vs real-estate) is NOT a tracked
# benchmark variable, so sheets carry a neutral title bar, never an app glyph.
def sheet_head(x, y, w=22):  # generic "this sheet has content" heading
    return f'<rect x="{x}" y="{y}" width="{w}" height="4" fill="{INK}"/>'

def title_bar(x, y):
    return sheet_head(x, y + 4, 22)

def distill_mark(x, y):  # tiny funnel = distilled recipe
    return (f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="1.4" fill="none">'
            f'<path d="M-4 -3 L4 -3 L1 1 L1 5 L-1 5 L-1 1 Z" fill="{PAPER}"/></g>')

# ---------- face (tiredness) ----------
HAIR_SETS = {
    "neat":  '<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR,
    "cowlick":('<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR
              + '<path d="M2 -26 Q6 -40 12 -30 Q7 -30 4 -24 Z" fill="%s"/>' % HAIR),
    "mess":  ('<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR
              + '<path d="M2 -26 Q6 -42 12 -30 Z" fill="%s"/>' % HAIR
              + '<path d="M-14 -22 Q-20 -36 -8 -30 Z" fill="%s"/>' % HAIR
              + '<path d="M14 -20 Q26 -30 18 -18 Z" fill="%s"/>' % HAIR
              + '<path d="M-2 -28 Q0 -44 6 -32 Z" fill="%s"/>' % HAIR),
}
UNDEREYE = {"none": "", "faint": G_FAINT, "dark": G_DARK}

def crest_glyph(ex, ey, harness, sw=1.6, sc=1.0):
    p = lambda v: v * sc
    if harness == "ocic":  # open-source spark (4-point outline star)
        return (f'<path d="M{ex} {ey-p(5)} L{ex+p(1.8)} {ey-p(1.8)} L{ex+p(5)} {ey} L{ex+p(1.8)} {ey+p(1.8)} '
                f'L{ex} {ey+p(5)} L{ex-p(1.8)} {ey+p(1.8)} L{ex-p(5)} {ey} L{ex-p(1.8)} {ey-p(1.8)} Z" '
                f'fill="none" stroke="{INK}" stroke-width="{sw}"/>')
    # official = filled shield
    return (f'<path d="M{ex-p(4)} {ey-p(4)} L{ex+p(4)} {ey-p(4)} L{ex+p(4)} {ey+p(1)} '
            f'Q{ex+p(4)} {ey+p(5)} {ex} {ey+p(6)} Q{ex-p(4)} {ey+p(5)} {ex-p(4)} {ey+p(1)} Z" fill="{INK}"/>')

def face(cx, cy, hair, ue, crest=None):
    s = [f'<g transform="translate({cx},{cy})">']
    s.append(f'<circle r="24" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(HAIR_SETS[hair])
    if crest:  # harness logo stamped on the brow (the "do not develop my app" mark)
        s.append(crest_glyph(0, -11, crest, sw=1.5))
    # eyes
    s.append(f'<circle cx="-8" cy="0" r="2.2" fill="{INK}"/><circle cx="8" cy="0" r="2.2" fill="{INK}"/>')
    # under-eye shadow
    col = UNDEREYE[ue]
    if col:
        s.append(f'<path d="M-12 6 Q-8 9 -4 6" stroke="{col}" stroke-width="2" fill="none" stroke-linecap="round"/>')
        s.append(f'<path d="M4 6 Q8 9 12 6" stroke="{col}" stroke-width="2" fill="none" stroke-linecap="round"/>')
    # mouth: flat for tired, tiny neutral line always
    s.append(f'<line x1="-5" y1="13" x2="5" y2="13" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    s.append('</g>')
    return "".join(s)

# ---------- torso + harness crest ----------
def torso(cx, cy, harness=None):  # body only; the harness logo now lives on the brow
    return (f'<path d="M{cx-26} {cy+34} Q{cx} {cy+14} {cx+26} {cy+34} L{cx+26} {cy+46} L{cx-26} {cy+46} Z" '
            f'fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')

# ---------- desk + browser emblem ----------
def desk(browser, W=220):
    y = 150
    s = [f'<rect x="6" y="{y}" width="{W-12}" height="6" fill="{INK}"/>',
         f'<rect x="6" y="{y+6}" width="{W-12}" height="58" fill="{CREAM}" stroke="{INK}" stroke-width="2.2"/>']
    ex, ey = W/2, y + 34
    if browser == "brave":  # lion / flame head, abstract
        s.append(f'<path d="M{ex} {ey-11} Q{ex+11} {ey-6} {ex+8} {ey+6} Q{ex} {ey+11} {ex-8} {ey+6} '
                 f'Q{ex-11} {ey-6} {ex} {ey-11} Z" fill="none" stroke="{INK}" stroke-width="1.8"/>'
                 f'<path d="M{ex-5} {ey-9} L{ex-8} {ey-14} M{ex+5} {ey-9} L{ex+8} {ey-14}" '
                 f'stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    else:  # chrome = pinwheel
        s.append(f'<circle cx="{ex}" cy="{ey}" r="10" fill="none" stroke="{INK}" stroke-width="1.8"/>'
                 f'<circle cx="{ex}" cy="{ey}" r="3.4" fill="{INK}"/>'
                 f'<path d="M{ex} {ey} L{ex} {ey-10} M{ex} {ey} L{ex+9} {ey+5} M{ex} {ey} L{ex-9} {ey+5}" '
                 f'stroke="{INK}" stroke-width="1.8"/>')
    return "".join(s)

# ---------- exam paper (task) + optional clipped recipe ----------
def exam(recipe=0, distilled=False):
    # foreshortened sheet lying on the desk in front
    s = [f'<path d="M62 150 L158 150 L150 138 L70 138 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>']
    s.append(title_bar(78, 141))
    s.append(f'<line x1="104" y1="144" x2="146" y2="144" stroke="{INK}" stroke-width="1" opacity=".5"/>')
    if recipe:  # recipe clipped ONTO the exam (in-task, unavoidable)
        # 1 combined sheet (5B) or 2 per-site sheets (5A); app is not a variable
        if recipe == 1:
            s.append(f'<g transform="translate(96,116)"><rect x="0" y="0" width="46" height="30" rx="1.5" '
                     f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
                     + sheet_head(8, 8, 30)
                     + f'<line x1="6" y1="20" x2="40" y2="20" stroke="{INK}" stroke-width="1.1"/>'
                     + f'<line x1="6" y1="24" x2="34" y2="24" stroke="{INK}" stroke-width="1.1"/>'
                     + (distill_mark(40, 5) if distilled else "")
                     + f'<rect x="20" y="-4" width="6" height="8" rx="2" fill="none" stroke="{INK}" stroke-width="1.6"/></g>')
        else:
            for i in range(2):
                xo = 84 + i * 30
                s.append(f'<g transform="translate({xo},116)"><rect x="0" y="0" width="26" height="30" rx="1.5" '
                         f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
                         + sheet_head(5, 8, 16)
                         + f'<line x1="5" y1="20" x2="21" y2="20" stroke="{INK}" stroke-width="1.1"/>'
                         + f'<line x1="5" y1="24" x2="17" y2="24" stroke="{INK}" stroke-width="1.1"/>'
                         + f'<rect x="10" y="-4" width="6" height="8" rx="2" fill="none" stroke="{INK}" stroke-width="1.6"/></g>')
    return "".join(s)

# ---------- binder (raw) + analysis sheet ----------
def binder(source, sheet=False):
    x, y = 158, 116  # right side of desk surface
    s = [f'<g transform="translate({x},{y})">']
    # closed thick book
    s.append(f'<rect x="0" y="6" width="44" height="30" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>')
    s.append(f'<rect x="0" y="6" width="8" height="30" fill="{CREAM}" stroke="{INK}" stroke-width="2.2"/>')
    if source == "own":  # scrappy: spiral rings on spine + rough scribble
        for k in range(4):
            s.append(f'<circle cx="4" cy="{11+k*7}" r="1.6" fill="none" stroke="{INK}" stroke-width="1.3"/>')
        s.append(f'<path d="M14 16 q6 -3 12 0 t12 0" stroke="{INK}" stroke-width="1.2" fill="none" opacity=".6"/>')
    else:  # expert: printed title bar
        s.append(f'<rect x="14" y="12" width="24" height="4" fill="{INK}"/>')
        s.append(f'<line x1="14" y1="22" x2="38" y2="22" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
        s.append(f'<line x1="14" y1="27" x2="34" y2="27" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    if sheet:  # analysis: a clean sheet resting ON TOP, headers, source-styled
        rot = -6 if source == "own" else 0
        s.append(f'<g transform="translate(3,-8) rotate({rot})"><rect x="0" y="0" width="40" height="20" rx="1.5" '
                 f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>' + sheet_head(6, 6, 26))
        if source == "own":
            s.append(f'<path d="M5 14 q6 -2 10 0 t10 0" stroke="{INK}" stroke-width="1.1" fill="none" opacity=".6"/>')
        else:
            s.append(f'<line x1="5" y1="14" x2="35" y2="14" stroke="{INK}" stroke-width="1.1" opacity=".55"/>')
        s.append('</g>')
    s.append('</g>')
    return "".join(s)

# ---------- thought bubble (internalized) ----------
def bubble(content, size):
    cx, cy = 158, 40
    r = 30 if size == "big" else 19
    s = [f'<circle cx="{cx-r-6}" cy="{cy+r-2}" r="3" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>',
         f'<circle cx="{cx-r-1}" cy="{cy+r+4}" r="2" fill="{PAPER}" stroke="{INK}" stroke-width="1.4"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>']
    sc = 1.0 if size == "big" else 0.7
    g = [f'<g transform="translate({cx},{cy}) scale({sc})">']
    if content == "own":  # a past task it did: a graded, filled-in task sheet
        g.append(graded_sheet(0, 0, 1.0))
    elif content == "expert":  # clean closed book
        g.append(f'<rect x="-13" y="-15" width="26" height="30" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        g.append(f'<rect x="-13" y="-15" width="6" height="30" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>')
        g.append(f'<rect x="-3" y="-9" width="14" height="4" fill="{INK}"/>')
        g.append(f'<line x1="-3" y1="1" x2="11" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    else:  # warmup: a completed practice sheet with a check
        g.append(f'<rect x="-12" y="-14" width="24" height="28" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        g.append(title_bar(-8, -10))
        g.append(f'<path d="M-7 6 l4 4 l8 -9" stroke="{INK}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    g.append('</g>')
    return "".join(s) + "".join(g)


# ---------- experiential vs expert prior glyphs (source + stacking) ----------
# Experiential reads as a PAST TASK: same shape as the task/exam paper, but filled
# in and graded (a check). Expert reads as a book. A stack = multiple rollouts /
# multiple expert sessions, which is what the internalized prior can hold.
def graded_sheet(cx=0, cy=0, sc=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({sc})">'
            f'<rect x="-13" y="-17" width="26" height="34" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
            + sheet_head(-8, -13, 16)
            + f'<line x1="-8" y1="-3" x2="8" y2="-3" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + f'<line x1="-8" y1="1" x2="3" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + f'<path d="M-7 8 l3.5 4 l7.5 -9" stroke="{INK}" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            + '</g>')

def book_glyph(cx=0, cy=0, sc=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({sc})">'
            f'<rect x="-13" y="-17" width="26" height="34" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="-13" y="-17" width="6" height="34" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="-3" y="-11" width="14" height="4" fill="{INK}"/>'
            f'<line x1="-3" y1="-1" x2="11" y2="-1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            f'<line x1="-3" y1="4" x2="7" y2="4" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + '</g>')

def prior_stack(kind, n=3, cx=0, cy=0):
    unit = graded_sheet if kind == "experiential" else book_glyph
    return "".join(unit(cx + i*7, cy - i*7, 1.0) for i in range(n-1, -1, -1))  # back-to-front

# ---------- aggregate composite (the amalgam) ----------
def _quad(cx, cy, w, h, pf):
    tw = w * (1 - pf)
    return (f"{cx-tw/2:.1f},{cy-h/2:.1f} {cx+tw/2:.1f},{cy-h/2:.1f} "
            f"{cx+w/2:.1f},{cy+h/2:.1f} {cx-w/2:.1f},{cy+h/2:.1f}")

def _label(tx, ty, x2, y2, text, anchor="start", em=False):
    dot = f'<circle cx="{x2}" cy="{y2}" r="2.4" fill="{INK}"/>'
    ln = f'<path d="M{tx} {ty} L{x2} {y2}" stroke="{GD}" stroke-width="1" fill="none" opacity=".8"/>'
    wt = "700" if em else "500"; fill = INK if em else GD
    tsp = "".join(f'<tspan x="{tx}" dy="{0 if i==0 else 12}">{l}</tspan>' for i, l in enumerate(text.split("\n")))
    return ln + dot + (f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="ui-monospace,Menlo,monospace" '
                       f'font-size="10.5" font-weight="{wt}" fill="{fill}">{tsp}</text>')

def composite_scene():
    W, H = 1000, 660
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px">', '<g transform="translate(120,0)">']
    # thought bubble: BOTH kinds of prior side by side
    bx, by = 452, 118
    for dx, dy, r in [(-54, 68, 4), (-46, 78, 3), (-40, 86, 2.2)]:
        s.append(f'<circle cx="{bx+dx}" cy="{by+dy}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<ellipse cx="{bx}" cy="{by}" rx="78" ry="54" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    # LEFT: material it READ (book + scrappy notebook)
    s.append(f'<g transform="translate({bx-30},{by-2})">'
             f'<rect x="-6" y="-20" width="30" height="38" rx="2" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="-6" y="-20" width="7" height="38" fill="{DESKC}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="5" y="-13" width="15" height="4.5" fill="{INK}"/></g>')
    s.append(f'<g transform="translate({bx-48},{by-4}) rotate(-8)">'
             f'<rect x="0" y="0" width="26" height="36" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
             + "".join(f'<circle cx="0" cy="{7+k*7}" r="1.6" fill="none" stroke="{INK}" stroke-width="1.3"/>' for k in range(4))
             + f'<path d="M6 11 q5 -3 9 0 t9 0 M6 18 q5 -3 9 0 t9 0 M6 25 q5 -3 9 0" stroke="{INK}" stroke-width="1.2" fill="none" opacity=".6"/></g>')
    # RIGHT: a practice task it DID (completed exam with a check)
    s.append(f'<g transform="translate({bx+30},{by-2})">'
             f'<rect x="-14" y="-19" width="30" height="38" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="-9" y="-13" width="16" height="4" fill="{INK}"/>'
             f'<line x1="-9" y1="-4" x2="9" y2="-4" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
             f'<line x1="-9" y1="1" x2="4" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
             f'<path d="M-7 9 l4 4 l9 -10" stroke="{INK}" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
    # torso (the harness logo now sits on the brow, not the chest)
    s.append(f'<path d="M230 300 Q285 235 340 300 L360 320 L210 320 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
    # head + face (cost)
    hx, hy = 285, 210
    s.append(f'<circle cx="{hx}" cy="{hy}" r="50" fill="{PAPER}" stroke="{INK}" stroke-width="2.8"/>')
    s.append(f'<path d="M{hx-50} {hy-8} Q{hx} {hy-70} {hx+50} {hy-8} Q{hx+24} {hy-42} {hx} {hy-42} Q{hx-24} {hy-42} {hx-50} {hy-8} Z" fill="{HAIR}"/>')
    s.append(f'<path d="M{hx+6} {hy-52} Q{hx+14} {hy-78} {hx+24} {hy-58} Q{hx+15} {hy-58} {hx+9} {hy-48} Z" fill="{HAIR}"/>')
    # harness crest stamped on the forehead (Rick-and-Morty brow mark)
    s.append(crest_glyph(hx, hy-16, "ocic", sw=2, sc=1.9))
    s.append(f'<circle cx="{hx-16}" cy="{hy+2}" r="3" fill="{INK}"/><circle cx="{hx+16}" cy="{hy+2}" r="3" fill="{INK}"/>')
    s.append(f'<path d="M{hx-24} {hy+13} Q{hx-16} {hy+18} {hx-8} {hy+13}" stroke="{G_FAINT}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    s.append(f'<path d="M{hx+8} {hy+13} Q{hx+16} {hy+18} {hx+24} {hy+13}" stroke="{G_FAINT}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    s.append(f'<line x1="{hx-10}" y1="{hy+27}" x2="{hx+10}" y2="{hy+27}" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>')
    # desk (perspective)
    s.append(f'<polygon points="150,300 470,300 560,548 60,548" fill="{DESKC}" stroke="{INK}" stroke-width="2.8"/>')
    s.append(f'<polygon points="60,548 560,548 560,592 60,592" fill="{CREAM}" stroke="{INK}" stroke-width="2.6"/>')
    ex, ey = 310, 570
    s.append(f'<path d="M{ex} {ey-11} Q{ex+11} {ey-6} {ex+8} {ey+6} Q{ex} {ey+11} {ex-8} {ey+6} Q{ex-11} {ey-6} {ex} {ey-11} Z" fill="none" stroke="{INK}" stroke-width="1.8"/>'
             f'<path d="M{ex-5} {ey-9} L{ex-8} {ey-14} M{ex+5} {ey-9} L{ex+8} {ey-14}" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    # exam (task) — content turned to face the student (heading/lines read toward the back)
    s.append(f'<polygon points="{_quad(232,452,168,128,.16)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(f'<g transform="rotate(180 232 452)">')
    for i in range(3):
        yy = 432 + i*12
        s.append(f'<line x1="164" y1="{yy}" x2="296" y2="{yy}" stroke="{INK}" stroke-width="1.1" opacity=".45"/>')
    s.append('</g>')
    # recipe clipped to exam — turned to face the student
    s.append(f'<polygon points="{_quad(232,398,132,66,.13)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(f'<g transform="rotate(180 232 398)">')
    s.append(f'<rect x="222" y="360" width="8" height="12" rx="3" fill="none" stroke="{INK}" stroke-width="2"/>')
    s.append(f'<rect x="180" y="382" width="48" height="5" fill="{INK}"/>')
    s.append(f'<line x1="180" y1="405" x2="284" y2="405" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append(f'<line x1="180" y1="412" x2="264" y2="412" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append(f'<path d="M280 372 L292 372 L288 378 L288 384 L284 384 L284 378 Z" fill="{PAPER}" stroke="{INK}" stroke-width="1.5"/>')
    s.append('</g>')
    # binder (raw) + analysis sheet — analysis sheet turned to face the student
    s.append(f'<polygon points="{_quad(430,470,130,92,.12)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
    s.append(f'<polygon points="{_quad(378,470,26,92,.12)}" fill="{DESKC}" stroke="{INK}" stroke-width="2.4"/>')
    for k in range(4):
        s.append(f'<circle cx="376" cy="{444+k*16}" r="2" fill="none" stroke="{INK}" stroke-width="1.4"/>')
    s.append(f'<path d="M398 462 q10 -4 20 0 t20 0" stroke="{INK}" stroke-width="1.3" fill="none" opacity=".55"/>')
    s.append(f'<polygon points="{_quad(432,418,110,50,.1)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>')
    s.append(f'<g transform="rotate(180 432 418)">')
    s.append(f'<rect x="392" y="404" width="40" height="4.5" fill="{INK}"/>')
    s.append(f'<line x1="392" y1="424" x2="470" y2="424" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append('</g>')
    # callouts
    s.append(_label(566, 40, 400, 70, "THOUGHT BUBBLE = prior in the head:", "start", em=True))
    s.append(_label(566, 96, 424, 118, "material it READ (fork)\n+  a practice task it DID (warm-up)", "start"))
    s.append(_label(40, 175, 258, 212, "FACE = tiredness\n= context load\nthe COST · emphasize", "start", em=True))
    s.append(_label(500, 200, 300, 194, "brow mark\n= harness (minor)", "start"))
    s.append(_label(496, 610, 320, 572, "desk brand\n= browser (minor)", "start"))
    s.append(_label(58, 470, 200, 452, "EXAM\n= the task", "end", em=True))
    s.append(_label(58, 405, 224, 398, "RECIPE\nclipped to the exam\n(in the task, forced)", "end", em=True))
    s.append(_label(586, 500, 452, 478, "BINDER\n= raw material\non the desk (optional)", "start", em=True))
    s.append(_label(586, 410, 456, 418, "ANALYSIS SHEET\nclean, on the binder", "start", em=True))
    s.append('</g></svg>')
    return "".join(s)

# ---------- full scene ----------
TIRED = {"fresh": ("neat", "none"), "lightly": ("cowlick", "none"),
         "baggy": ("cowlick", "faint"), "wrecked": ("mess", "dark")}

def scene(cfg, w=220, h=224):
    hair, ue = TIRED[cfg["tired"]]
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="inherit">']
    if cfg.get("bubble"):
        parts.append(bubble(*cfg["bubble"]))
    parts.append(torso(100, 92, cfg["harness"]))
    parts.append(face(100, 84, hair, ue, crest=cfg["harness"]))
    parts.append(desk(cfg["browser"], w))
    parts.append(exam(recipe=cfg.get("recipe", 0), distilled=cfg.get("distilled", False)))
    if cfg.get("prop") == "binder":
        parts.append(binder(cfg["source"]))
    elif cfg.get("prop") == "analysis":
        parts.append(binder(cfg["source"], sheet=True))
    parts.append('</svg>')
    return "".join(parts)

def swatch(inner, w=120, h=120):
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="inherit">{inner}</svg>'

# ---------- the 13 arms ----------
ARMS = [
 ("Cold · OCIC · Brave","OCIC-Br","cold", dict(harness="ocic",browser="brave",tired="fresh")),
 ("Cold · OCIC · Chrome","OCIC-Ch","cold", dict(harness="ocic",browser="chrome",tired="fresh")),
 ("Cold · Official CinC · Chrome","CinC","cold", dict(harness="official",browser="chrome",tired="fresh")),
 ("2A · experiential raw mount","2A","p2", dict(harness="ocic",browser="brave",tired="fresh",prop="binder",source="own")),
 ("2B · expert raw mount","2B","p2", dict(harness="ocic",browser="brave",tired="fresh",prop="binder",source="expert")),
 ("3D · experiential analysis","3D","p3", dict(harness="ocic",browser="brave",tired="fresh",prop="analysis",source="own")),
 ("3C · expert analysis","3C","p3", dict(harness="ocic",browser="brave",tired="fresh",prop="analysis",source="expert")),
 ("4A · experiential fork","4A","p4", dict(harness="ocic",browser="brave",tired="wrecked",bubble=("own","big"))),
 ("4B · expert fork","4B","p4", dict(harness="ocic",browser="brave",tired="baggy",bubble=("expert","big"))),
 ("5A · recipe · per-site","5A","p5", dict(harness="ocic",browser="brave",tired="fresh",recipe=2,distilled=True)),
 ("5B · recipe · single","5B","p5", dict(harness="ocic",browser="brave",tired="fresh",recipe=1,distilled=True)),
 ("5C · atomic warm-up fork","5C","p5", dict(harness="ocic",browser="brave",tired="lightly",bubble=("warmup","small"))),
 ("5D · warm-up + recipe","5D","p5", dict(harness="ocic",browser="brave",tired="lightly",recipe=1,distilled=True,bubble=("warmup","small"))),
]

CSS = """
:root{--bg:#f4f1ea;--ink:#2b2a27;--muted:#6b675e;--dim:#948f84;--line:#d8d3c7;--card:#fffdf6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:44px 30px 100px}
h1{font-size:28px;letter-spacing:-.01em;margin:2px 0 6px}
h2{font-size:19px;margin:48px 0 4px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:14px;margin:20px 0 8px;font-weight:700}
.eyebrow{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
.lede{font-size:16px;color:var(--muted);max-width:74ch}
p{margin:8px 0;max-width:74ch}
.zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:16px 0}
.zone{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:11px 13px}
.zone b{font-size:13px}.zone span{font-size:12.5px;color:var(--muted)}
.renders{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0 4px}
.render{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.render img{display:block;width:100%;height:auto;background:#fdfbf5}
.render figcaption{display:flex;justify-content:space-between;align-items:baseline;padding:8px 11px;
  font:600 12px ui-monospace,Menlo,monospace;border-top:1px solid var(--line)}
.render figcaption span{font-weight:400;color:var(--muted)}
@media(max-width:680px){.renders{grid-template-columns:1fr}}
.matrix{display:grid;grid-template-columns:minmax(120px,0.7fr) 1fr 1fr 1fr;gap:10px;align-items:center;margin:16px 0 4px}
.mx-corner{}
.mx-head{font:600 12px ui-monospace,Menlo,monospace;color:var(--muted);text-align:center;padding-bottom:2px}
.mx-row{padding-right:6px}
.mx-row b{display:block;font-size:13px}.mx-row span{font-size:11.5px;color:var(--muted)}
.mx-cell{background:var(--card);border:1px solid var(--line);border-radius:9px;overflow:hidden;line-height:0}
.mx-cell img{width:100%;height:auto;display:block;background:#fdfbf5}
@media(max-width:680px){.matrix{grid-template-columns:1fr 1fr}.mx-corner,.mx-head{display:none}.mx-row{grid-column:1/-1}}
.hero{margin:16px 0 4px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;max-width:560px}
.hero img{width:100%;height:auto;display:block;background:#fdfbf5}
.hero figcaption{padding:10px 13px;border-top:1px solid var(--line)}
.hero figcaption b{display:block;font:600 13px ui-monospace,Menlo,monospace}
.hero figcaption span{font-size:11.5px;color:var(--muted)}
.props{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin:16px 0 4px}
.prop{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.prop img{width:100%;height:auto;display:block;background:#fdfbf5}
.prop figcaption{padding:9px 12px;border-top:1px solid var(--line)}
.prop figcaption b{display:block;font:600 13px ui-monospace,Menlo,monospace}
.prop figcaption span{font-size:11.5px;color:var(--muted)}
.phaseband{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:22px 0 8px}
.hq{font:600 9px/1 ui-monospace,Menlo,monospace;letter-spacing:.06em;color:#fff;background:var(--ink);border-radius:3px;padding:2px 4px;vertical-align:middle;margin-left:4px}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
.gcell{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.gcell img{width:100%;height:auto;display:block;background:#fdfbf5}
.gcell figcaption{padding:8px 11px;border-top:1px solid var(--line)}
.gcell figcaption b{display:block;font:600 12.5px ui-monospace,Menlo,monospace}
.gcell figcaption span{font-size:11.5px;color:var(--muted)}
.levels{display:flex;flex-wrap:wrap;gap:14px;margin:6px 0 4px}
.lv{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:8px;text-align:center;width:132px}
.lv svg{display:block;margin:0 auto}
.lv .cap{font:600 11.5px ui-monospace,Menlo,monospace;margin-top:5px}
.lv .sub{font-size:11px;color:var(--muted);line-height:1.3;margin-top:2px}
.note{font-size:12.5px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin:14px 0}
.cell{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:8px 8px 12px}
.cell svg{display:block}
.cell .t{font:700 12px ui-monospace,Menlo,monospace;margin-top:4px}
.cell .p{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.phaseband{font:700 11px ui-monospace,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);grid-column:1/-1;margin:10px 0 -4px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:10px 0}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line)}
th{font:600 10.5px ui-monospace,Menlo,monospace;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:11.5px}
"""

def lv(inner, cap, sub):
    return f'<div class="lv">{swatch(inner)}<div class="cap">{cap}</div><div class="sub">{sub}</div></div>'

# variable level swatches
faces_html = "".join(lv(face(60, 66, *TIRED[k]),
                        {"fresh":"FRESH","lightly":"LIGHTLY","baggy":"BAGGY","wrecked":"WRECKED"}[k],
                        {"fresh":"~58k · neat, no shadow","lightly":"~99k · one cowlick",
                         "baggy":"~270k · cowlick + faint shadow","wrecked":"~488k · full mess + shadow"}[k])
                     for k in ("fresh","lightly","baggy","wrecked"))
harness_html = (lv(torso(60,50)+face(60,44,"neat","none",crest="ocic"),"OCIC","open-source spark on the brow")
              + lv(torso(60,50)+face(60,44,"neat","none",crest="official"),"OFFICIAL","filled shield on the brow"))
browser_html = (lv('<g transform="translate(-40,-96)">'+desk("brave",120)+'</g>',"BRAVE","lion emblem on desk")
              + lv('<g transform="translate(-40,-96)">'+desk("chrome",120)+'</g>',"CHROME","pinwheel emblem"))
def mini_prop(fn): return f'<g transform="translate(-120,-96)">{fn}</g>'
knowledge_html = (
    lv('', "NONE", "empty desk (cold)")
  + lv(mini_prop(binder("expert")), "RAW MOUNT", "closed binder on the desk")
  + lv(mini_prop(binder("expert", sheet=True)), "ANALYSIS", "clean sheet on the binder (must reach)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "RECIPE", "same sheet, clipped to the EXAM (in hand)"))
source_html = (
    lv(graded_sheet(60, 60, 1.45), "EXPERIENTIAL", "a graded, filled-in task sheet (a past rollout)")
  + lv(book_glyph(60, 60, 1.45), "EXPERT", "a textbook (an expert session)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "DISTILLED", "crisp recipe, funnel mark (fused)"))
prior_depth_html = (
    lv(graded_sheet(60, 60, 1.3), "ONE ROLLOUT", "a single graded task sheet")
  + lv(prior_stack("experiential", 3, 53, 67), "MANY ROLLOUTS", "a stack of graded task sheets")
  + lv(book_glyph(60, 60, 1.3), "ONE EXPERT SESSION", "a single textbook")
  + lv(prior_stack("expert", 3, 53, 67), "MANY EXPERT SESSIONS", "a stack of books"))
bubble_html = (
    lv(f'<g transform="translate(-116,4)">{bubble("own","big")}</g>', "OWN · big", "read its own notebooks (4A)")
  + lv(f'<g transform="translate(-116,4)">{bubble("expert","big")}</g>', "EXPERT · big", "read the textbooks (4B)")
  + lv(f'<g transform="translate(-116,10)">{bubble("warmup","small")}</g>', "WARM-UP · small", "did one practice task (5C/5D)"))
recipe_html = (
    lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "SINGLE", "one combined sheet, both sites (5B)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=2,distilled=True)}</g>', "PER-SITE", "one sheet per site (5A)"))

# first AI renders: the aggregate prompt, same prompt, quality sweep (gpt-image-2, 1024)
RENDERS = [("low", "~$0.006", "22s"), ("medium", "~$0.05", "55s"), ("high", "~$0.21", "140s")]
render_html = "".join(
    f'<figure class="render"><img src="{img_src(f"img/aggregate_{q}.png")}" alt="aggregate render, {q} quality"/>'
    f'<figcaption><b>{q.upper()}</b><span>{cost} · {t}</span></figcaption></figure>'
    for q, cost, t in RENDERS)

# style exploration matrix: 2 aggregates (rows) x 3 art styles (cols)
MX_STYLES = [("pencil", "Pencil stickman"), ("flat", "Flat vector"), ("ink", "Fine ink")]
MX_ROWS = [("a", "A · OCIC · Brave · expert", "book on desk + in mind, fresh"),
           ("b", "B · CinC · Chrome · experiential", "completed practice exams, tired")]
def matrix_html():
    cells = ['<div class="mx-corner"></div>']
    cells += [f'<div class="mx-head">{name}</div>' for _, name in MX_STYLES]
    for cfg, rlab, rsub in MX_ROWS:
        cells.append(f'<div class="mx-row"><b>{rlab}</b><span>{rsub}</span></div>')
        for sk, _ in MX_STYLES:
            uri = img_src(f"img/style_{sk}_{cfg}.png")
            cells.append(f'<div class="mx-cell"><img src="{uri}" alt="{sk} {cfg}"/></div>')
    return '<div class="matrix">' + "".join(cells) + '</div>'

# pencil sub-variants (same scene, config B) for the final style pick
PVARIANTS = [("clean", "Clean", "thin outline, no shading"),
             ("loose", "Loose", "gestural sketchbook"),
             ("soft", "Soft", "smooth graphite shading")]
def pvariants_html():
    return '<div class="renders">' + "".join(
        f'<figure class="render"><img src="{img_src(f"img/pv_{k}_b.png")}" alt="pencil {k}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in PVARIANTS) + '</div>'

# per-arm soft-pencil renders, grouped by phase (one image per leg)
# sub = props on the scene · context load going into the task (drives the tiredness)
ARM_GALLERY = [
    ("Cold baselines", [
        ("1a-brave", "OCIC · Brave", "bare desk · fresh (no prior context)"),
        ("1a-chrome", "OCIC · Chrome", "bare desk · fresh (no prior context)"),
        ("1b-cinc", "CinC · Chrome", "bare desk · fresh (no prior context)")]),
    ("Phase 2 · raw mount", [
        ("2a", "2A experiential", "stack of graded sheets on desk · fresh (knowledge on disk, not in context)"),
        ("2b", "2B expert", "stack of books on desk · fresh (knowledge on disk, not in context)")]),
    ("Phase 3 · analysis mount", [
        ("3d", "3D experiential", "stack + analysis sheet · fresh (knowledge on disk, not in context)"),
        ("3c", "3C expert", "books + analysis sheet · fresh (knowledge on disk, not in context)")]),
    ("Phase 4 · fork", [
        ("4a", "4A experiential fork", "stack in mind · wrecked (~499k tokens in, 476k-534k)"),
        ("4b", "4B expert fork", "stack of books in mind · baggy (~288k tokens in, 251k-325k)")]),
    ("Phase 5 · recipe & warm-up", [
        ("5a", "5A recipe per-site", "two panels on the task · fresh (small recipe in prompt)"),
        ("5b", "5B recipe single", "one panel on the task · fresh (small recipe in prompt)"),
        ("5c", "5C atomic warm-up", "one sheet in mind · lightly (~99k tokens in)"),
        ("5d", "5D warm-up + recipe", "panel on task + sheet in mind · lightly (~99k tokens in)")]),
]
def leg_best(key):
    """Best available render for a leg: medium is the working standard, then high, then low.
    Returns (src, quality_tag)."""
    for q, tag in (("medium", "MQ"), ("high", "HQ"), ("low", "")):
        s = img_src(f"img/leg_{key}_{q}.png")
        if s:
            return s, tag
    return "", ""

def gallery_html():
    out = []
    for band, arms in ARM_GALLERY:
        out.append(f'<div class="phaseband">{band}</div><div class="gallery">')
        for key, name, sub in arms:
            src, tag = leg_best(key)
            badge = f' <span class="hq">{tag}</span>' if tag else ''
            out.append(f'<figure class="gcell"><img src="{src}" alt="{name}"/>'
                       f'<figcaption><b>{name}{badge}</b><span>{sub}</span></figcaption></figure>')
        out.append('</div>')
    return "".join(out)

# prop sheets: one grid image per variable, drawn in a single pass for continuity
PROP_SHEETS = [
    ("v1-character", "V1 · The character (context load × harness)",
     "columns L→R: fresh · lightly · baggy · wrecked. rows: OCIC (top) · CinC (bottom)"),
    ("v2-position", "V2 · Knowledge form (how it reaches the task)",
     "the four delivery forms. NONE: nothing supplied (cold, bare desk). RAW: a graded source dropped on the desk, there but you must reach for it. ANALYSIS: a distinct structured, formatted write-up laid over the source, small and offset so the source underneath stays visible. RECIPE: knowledge printed straight onto the task paper, in hand and unavoidable."),
    ("task-paper", "The task paper",
     "L→R: plain task (legible TASK heading + illegible brief + answer lines) · recipe printed on top · recipe split into two sections. Only the heading is legible."),
    ("v3-source", "V3 · Source (whose material, single or stacked)",
     "top: one experiential (own graded task sheet) · one expert (textbook). bottom: a stack of each (multiple rollouts / expert sessions), which is what the internalized prior holds."),
    ("v4-prior", "V4 · Internalized prior (the bubble)",
     "a thought-bubble container; it holds any source prop, a single sheet or a stack (rollouts / books). shown holding one graded task paper."),
    ("v6-browser", "V6 · Browser (embedded on the desk)",
     "the desk with the browser logo embedded on its front face. left: Brave · right: Chrome."),
]
def props_html():
    return '<div class="props">' + "".join(
        f'<figure class="prop"><img src="{img_src(f"img/prop_{k}_labeled.png")}" alt="{title}"/>'
        f'<figcaption><b>{title}</b><span>{legend}</span></figcaption></figure>'
        for k, title, legend in PROP_SHEETS) + '</div>'

# composition exploration: how to show face + desk together (first-person feel)
COMPS = [
    ("across", "Across the desk", "baseline; face over the far edge, desk head-on"),
    ("corner", "Three-quarter corner", "seated at the corner; face + angled desk, most natural single scene"),
    ("leaning", "Leaning over", "bent over the far edge; reads a little awkward"),
    ("reflection", "Reflection", "true first-person over-the-shoulder; face in a propped mirror"),
    ("inset", "Corner inset", "pure first-person desk; face as a cameo medallion"),
]
def comps_html():
    return '<div class="gallery">' + "".join(
        f'<figure class="gcell"><img src="{img_src(f"img/comp_{k}.png")}" alt="{name}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in COMPS) + '</div>'

# first-person variants: desk in true first-person, face surfaced by a desk object
FP_COMPS = [
    ("mirror", "Mirror", "propped desk mirror; warm and natural"),
    ("monitor", "Monitor self-view", "face on a screen, on-theme with the browser world"),
    ("phone", "Phone selfie", "propped phone, front-camera self-view"),
    ("photo", "Framed photo", "a desk portrait; understated"),
    ("badge", "ID badge", "lanyard badge photo; ties to identity"),
    ("cameo", "Cameo overlay", "graphic medallion; least in-world"),
]
def fp_html():
    return '<div class="gallery">' + "".join(
        f'<figure class="gcell"><img src="{img_src(f"img/fp_{k}.png")}" alt="{name}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in FP_COMPS) + '</div>'

# arm -> channel table
def cell_summary(cfg):
    b = cfg.get("bubble"); return {
      "harness":cfg["harness"],"browser":cfg["browser"],
      "knowledge":("recipe" if cfg.get("recipe") else cfg.get("prop","none")),
      "source":cfg.get("source", "distilled" if cfg.get("recipe") else ("-" if not b else b[0])),
      "tired":cfg["tired"],"bubble":(f"{b[0]}/{b[1]}" if b else "-")}
rows = "".join(
  f'<tr><td class="mono">{s}</td><td>{c["harness"]}</td><td>{c["browser"]}</td><td>{c["knowledge"]}</td>'
  f'<td>{c["source"]}</td><td>{c["tired"]}</td><td>{c["bubble"]}</td></tr>'
  for (_,s,_,cfg) in ARMS for c in [cell_summary(cfg)])

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Experiment iconography · model sheet</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK · EXPERIMENT ICONOGRAPHY · MODEL SHEET v1</div>
<h1>The exam student: one glyph per experiment</h1>
<p class="lede">A parametric icon system. Each experiment is a seated exam student; every benchmark variable owns exactly
one visual channel, and nothing else varies. Complexity grows on its own as configurations stack channels. Monochrome
on purpose: color is reserved. This document is the encoding, the swatches below are generated by the same functions
that draw the final scenes.</p>

<h2>1 &middot; Design brief <span class="note" style="font-weight:400">(the channels we manage)</span></h2>
<p>The encoding first: every benchmark variable is bound to exactly one visual channel, and nothing else varies.</p>
<div class="zones">
<div class="zone"><b>Brow mark</b> <span>= harness (OCIC vs official)</span></div>
<div class="zone"><b>Desk</b> <span>= browser (Brave vs Chrome, monochrome)</span></div>
<div class="zone"><b>Exam paper</b> <span>= the task (always present)</span></div>
<div class="zone"><b>Desk surface</b> <span>= present-environment knowledge (binder / +sheet)</span></div>
<div class="zone"><b>Clipped to the exam</b> <span>= in-task knowledge (the recipe)</span></div>
<div class="zone"><b>Thought bubble</b> <span>= already-internalized knowledge (what it read/did)</span></div>
<div class="zone"><b>Face</b> <span>= context load = tiredness (the cost)</span></div>
</div>
<p class="note"><b>The core distinction, desk vs exam:</b> the analysis sheet and the recipe are the same content. On the
<b>desk</b> (on the binder) it is available but must be reached for, the environment version, mostly unread. Clipped to
the <b>exam</b> it is unavoidable, handed to you with the task. Position is the isomorphism for "on disk, optional" vs
"in the prompt, forced." And the <b>desk is the present</b>; the <b>thought bubble is the past</b> (what was already read).</p>

<h3 style="margin-top:30px">1.1 &middot; Concept sketches <span class="note" style="font-weight:400">(lo-fi roughs, one per channel)</span></h3>
<h3>Variable 1 · Context load = tiredness <span class="note" style="font-weight:400">(the one continuous magnitude)</span></h3>
<p>Two co-varying sub-cues, monotonic with tokens carried per turn. Fresh has no cue; the three tired states escalate.</p>
<div class="levels">{faces_html}</div>

<h3>Variable 2 · Knowledge form <span class="note" style="font-weight:400">(where it lives)</span></h3>
<div class="levels">{knowledge_html}</div>

<h3>Variable 3 · Source <span class="note" style="font-weight:400">(whose material, by rendering style, not color)</span></h3>
<div class="levels">{source_html}</div>

<h3>Variable 3b · Prior depth <span class="note" style="font-weight:400">(one rollout / session, or a stack)</span></h3>
<p>Experience is not a single item. An agent can carry many graded rollouts of its own, or many expert sessions.
Experiential stacks as filled, graded task sheets; expert stacks as books. This is the count that the internalized
prior (Variable 4) can hold.</p>
<div class="levels">{prior_depth_html}</div>

<h3>Variable 4 · Internalized prior <span class="note" style="font-weight:400">(thought bubble = what it already read)</span></h3>
<p>Bubble size scales with how much was crammed (big = full study, small = one warm-up task). Content shows the source.</p>
<div class="levels">{bubble_html}</div>

<h3>Variable 5 · Harness <span class="note" style="font-weight:400">(the mark on the student's brow)</span></h3>
<div class="levels">{harness_html}</div>

<h3>Variable 6 · Browser <span class="note" style="font-weight:400">(the desk's emblem, monochrome)</span></h3>
<div class="levels">{browser_html}</div>

<h3>Variable 7 · Recipe scope <span class="note" style="font-weight:400">(sub-variable of recipe)</span></h3>
<div class="levels">{recipe_html}</div>

<h3 style="margin-top:30px">1.2 &middot; The aggregate <span class="note" style="font-weight:400">(one rough amalgam, every channel at once)</span></h3>
<p>Not a real arm. A composite carrying every component together so we agree on the aggregate before we vary anything.
Front-and-above camera, angled down onto the desk, because the desk and its items are the key information and the angle
spreads them out instead of stacking them. <b>Primary:</b> the desk + its items, and the face + thought bubble.
<b>Minor:</b> brow mark (harness) and desk brand (browser, monochrome).</p>
<div class="card">{composite_scene()}</div>
<p class="note"><b>Two kinds of prior in the head:</b> the bubble holds both what it <b>READ</b> (a fork: material studied,
book + notebook) and a practice task it <b>DID</b> (a warm-up: a completed exam with a check). Reading and doing are
different priors; the amalgam shows both.</p>

<h2>2 &middot; Look development <span class="note" style="font-weight:400">(finding the style)</span></h2>
<h3>2.1 &middot; Render test <span class="note" style="font-weight:400">(resolution, cost vs fidelity)</span></h3>
<p>The SVG above is the lo-fi scaffold; this is the same scene as an actual render. One constant prompt (the model sheet
compressed into text), square, held to a single monochrome line style. Only the quality knob moves, low to high, so the
row doubles as a cost-vs-fidelity read. Materials face the student, so their text reads away from us.</p>
<div class="renders">{render_html}</div>

<h3>2.2 &middot; Style exploration <span class="note" style="font-weight:400">(2 aggregates &times; 3 art styles)</span></h3>
<p>Two aggregates that between them show both sides of the varying components: <b>A</b> is OCIC on Brave with an expert
source (a book, on the desk and in the mind), fresh; <b>B</b> is CinC on Chrome with an experiential source (a stack of
completed practice exams), tired. Browser logos (Brave, Chrome) keep their real shape so they read as themselves, but
are drawn monochrome like everything else; color stays reserved. The harness is the plain word (OCIC or CinC) stamped
on the student's brow, not a logo.
Everything else is a concept, so it is abstracted to the style. The cheat sheet is printed onto the exam as a
boxed area; the analysis is a clean sheet on the source; the book and the practice exams stay consistent between desk
and thought bubble.</p>
{matrix_html()}

<h3>2.3 &middot; Style variants <span class="note" style="font-weight:400">(pencil family, pick one)</span></h3>
<p>Pencil stickman is the chosen family. Three treatments of the same frame (B: CinC on Chrome, experiential, tired),
so the choice is only about the pencil handling: <b>clean</b> is a thin outline with no shading, <b>loose</b> is a
gestural sketchbook hand, <b>soft</b> is smooth graphite shading. Pick one and it becomes the house style for the
per-arm glyphs.</p>
{pvariants_html()}

<h2>3 &middot; Prop design <span class="note" style="font-weight:400">(props built to the style guide)</span></h2>
<p>The props: one sheet per variable, every permutation of that variable drawn together in one image so the whole set
comes out of a single hand at a single scale. That is what buys continuity, and it is the master reference each leg is
built against, everything on-model, nothing off. Each cell is labeled on the sheet itself (a title band plus a tag per
cell) so the set stays legible when the sheets are later assembled into one master image.</p>
{props_html()}
<h3 style="margin-top:28px">3.1 &middot; The master sheet <span class="note" style="font-weight:400">(all props on one reference)</span></h3>
<p>All six sheets composited into one master reference, every prop for every variable on a single image. This is the
one reference handed to the key-art step.</p>
<figure class="hero" style="max-width:100%"><img src="{img_src('img/prop_master.png')}" alt="prop design master sheet"/>
<figcaption><b>PROP DESIGN · MASTER SHEET</b><span>V1 character · V2 knowledge form · task paper · V3 source · V4 prior · V6 browser</span></figcaption></figure>

<h2>4 &middot; Layout <span class="note" style="font-weight:400">(staging the scene, before the hero)</span></h2>
<h3>4.1 &middot; Composition exploration <span class="note" style="font-weight:400">(how to show face + desk, first-person feel)</span></h3>
<p>The face is essential but a true first-person desk view cannot show it, so these are ways to keep both: the desk seen
as one's own AND the face readable. Same minimal content in every frame (the reverted simpler stickman, the exam now
titled EXAM under the cheat panel), only the camera and pose change. Pick one and it becomes the framing for the whole set.</p>
{comps_html()}

<h3>4.2 &middot; First-person variants <span class="note" style="font-weight:400">(desk as your own; face via a desk object)</span></h3>
<p>Committing to true first-person: we look down at the character's own desk, so the face has to arrive through
something sitting on the desk. Each variant is a different device for that, same first-person desk and titled exam
underneath. Pick the device and it becomes the house framing.</p>
{fp_html()}

<h2>5 &middot; Key art <span class="note" style="font-weight:400">(the hero, scaffolded from channels, grounded on the master sheet)</span></h2>
<p>The scaffolding: a leg is a set of variable instantiations, each mapped to a NAMED cell on the master sheet
(5D: character <span class="mono">LIGHTLY · OCIC</span>, desk <span class="mono">BRAVE</span>, task
<span class="mono">+ RECIPE</span>, bubble holding <span class="mono">EXPERIENTIAL</span>). The template assembles a
numbered prop list from those cells, and the master sheet is passed to the image edits endpoint as the reference so the
model copies its style and props. Grounding fixed the Brave mark (the flat logo, not an ornamental lion) and holds the
stickman on-model. The same scaffolding produces every other leg.</p>
<figure class="hero"><img src="{leg_best('5d')[0]}" alt="key art, leg 5D, grounded on master sheet"/>
<figcaption><b>5D &middot; warm-up + recipe{f' <span class=\"hq\">{leg_best("5d")[1]}</span>' if leg_best('5d')[1] else ''}</b><span>character LIGHTLY·OCIC · desk BRAVE · task +RECIPE · bubble EXPERIENTIAL</span></figcaption></figure>
<h3 style="margin-top:24px">5.1 &middot; Baseline <span class="note" style="font-weight:400">(the neutral scene the channels build on)</span></h3>
<p>The neutral scene every leg builds on: a fresh student, the plain task paper, an unbranded desk. No forehead word,
no browser logo, no supplied knowledge; the variables are what get added to this.</p>
<figure class="hero" style="max-width:420px"><img src="{leg_best('baseline')[0]}" alt="baseline scene"/>
<figcaption><b>BASELINE{f' <span class=\"hq\">{leg_best("baseline")[1]}</span>' if leg_best('baseline')[1] else ''}</b><span>fresh · plain task · unbranded desk</span></figcaption></figure>

<h2>Reference &middot; channel map</h2>
<div style="overflow-x:auto"><table><thead><tr><th>arm</th><th>harness</th><th>browser</th><th>knowledge</th>
<th>source</th><th>tiredness</th><th>bubble</th></tr></thead><tbody>{rows}</tbody></table></div>

<h2>6 &middot; Final frames <span class="note" style="font-weight:400">(the thirteen legs, medium quality)</span></h2>
<p>Every leg from the same scaffolding as the 5D key art: its channels map to named cells on the master sheet, the
template assembles the prop list, and each frame is generated with the master sheet as the grounding reference so the
whole set stays on-model. The forehead word is the harness (OCIC / CinC), the desk logo is the browser, the face is
the context load, and the knowledge shows up where the leg puts it, on the desk (raw or under an analysis sheet),
printed onto the task (recipe), or in the thought bubble (a single warm-up, a stack of rollouts, or a stack of books).</p>
{gallery_html()}

<p class="note" style="margin-top:30px">Model sheet generated by <span class="mono">analysis/build_style_bible.py</span>.
The component functions (face, torso, desk, exam, binder, bubble) are the reusable asset library for the final renders.</p>
</div></body></html>"""

out = os.path.join(BENCH, "style_bible.html")
open(out, "w").write(html)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

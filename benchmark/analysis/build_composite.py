#!/usr/bin/env python3
"""composite.html: ONE amalgam frame (not a real arm) showing every variable at
once, from a front-and-above camera. Lo-fi SVG to align on the aggregate vision.
Emphasis: the desk + its items (the key information) and the face + thoughts.
Minor: shirt crest (harness) and desk brand (browser)."""
import os
BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK="#2b2a27"; CREAM="#f4f1ea"; PAPER="#fdfbf5"; DESKC="#efe9db"; G="#b7b2a6"; GD="#8f8c85"; HAIR="#3a3833"

def quad(cx, cy, w, h, p):
    """flat sheet in perspective: top edge narrower than bottom (receding)."""
    tw = w * (1 - p)
    return (f"{cx-tw/2:.1f},{cy-h/2:.1f} {cx+tw/2:.1f},{cy-h/2:.1f} "
            f"{cx+w/2:.1f},{cy+h/2:.1f} {cx-w/2:.1f},{cy+h/2:.1f}")

def fork(x, y, s=1):
    return (f'<g transform="translate({x},{y}) scale({s})" stroke="{INK}" stroke-width="1.8" fill="none" stroke-linecap="round">'
            f'<line x1="0" y1="-6" x2="0" y2="1"/><line x1="3.5" y1="-6" x2="3.5" y2="1"/><line x1="7" y1="-6" x2="7" y2="1"/>'
            f'<path d="M0 1 h7 v3 q0 3 -3.5 3 q-3.5 0 -3.5 -3 z" fill="{INK}"/><line x1="3.5" y1="7" x2="3.5" y2="13"/></g>')

def house(x, y, s=1):
    return (f'<g transform="translate({x},{y}) scale({s})" stroke="{INK}" stroke-width="1.8" fill="none" stroke-linejoin="round">'
            f'<path d="M-7 0 L0 -7 L7 0 Z"/><rect x="-5" y="0" width="10" height="8"/></g>')

def headers(x, y, s=1):
    return fork(x, y, s) + house(x + 15*s, y - 1, s)

def label(tx, ty, x2, y2, text, anchor="start", em=False):
    dot = f'<circle cx="{x2}" cy="{y2}" r="2.4" fill="{INK}"/>'
    ln = f'<path d="M{tx} {ty} L{x2} {y2}" stroke="{GD}" stroke-width="1" fill="none" opacity=".8"/>'
    w = "700" if em else "500"
    fill = INK if em else GD
    lines = text.split("\n")
    tsp = "".join(f'<tspan x="{tx}" dy="{0 if i==0 else 12}">{l}</tspan>' for i,l in enumerate(lines))
    return ln + dot + (f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="ui-monospace,Menlo,monospace" '
                       f'font-size="10.5" font-weight="{w}" fill="{fill}">{tsp}</text>')

W, H = 800, 660
s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" font-family="ui-monospace,Menlo,monospace">', '<g transform="translate(90,0)">']

# ---- thought bubble (internalized prior) : a studied stack, both sources ----
bx, by = 452, 120
for dx, dy, r in [(-52, 66, 4), (-44, 76, 3), (-38, 84, 2.2)]:
    s.append(f'<circle cx="{bx+dx}" cy="{by+dy}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>')
s.append(f'<ellipse cx="{bx}" cy="{by}" rx="64" ry="52" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
# clean book behind + scrappy spiral notebook front (the amalgam: it read both)
s.append(f'<g transform="translate({bx-4},{by-2})">'
         f'<rect x="-6" y="-22" width="34" height="42" rx="2" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>'
         f'<rect x="-6" y="-22" width="8" height="42" fill="{DESKC}" stroke="{INK}" stroke-width="2"/>'
         f'<rect x="6" y="-14" width="18" height="5" fill="{INK}"/></g>')
s.append(f'<g transform="translate({bx-28},{by-4}) rotate(-8)">'
         f'<rect x="0" y="0" width="30" height="40" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
         + "".join(f'<circle cx="0" cy="{8+k*7}" r="1.7" fill="none" stroke="{INK}" stroke-width="1.3"/>' for k in range(4))
         + f'<path d="M7 12 q6 -3 10 0 t10 0 M7 20 q6 -3 10 0 t10 0 M7 28 q6 -3 10 0" stroke="{INK}" stroke-width="1.3" fill="none" opacity=".65"/></g>')

# ---- torso + harness crest (minor) ----
s.append(f'<path d="M230 300 Q285 235 340 300 L360 320 L210 320 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
cx, cy = 285, 288
s.append(f'<path d="M{cx} {cy-7} L{cx+3} {cy-2} L{cx+8} {cy} L{cx+3} {cy+2} L{cx} {cy+7} L{cx-3} {cy+2} L{cx-8} {cy} L{cx-3} {cy-2} Z" '
         f'fill="none" stroke="{INK}" stroke-width="1.8"/>')

# ---- head + face (COST channel), seen slightly from above, moderately tired ----
hx, hy = 285, 210
s.append(f'<circle cx="{hx}" cy="{hy}" r="50" fill="{PAPER}" stroke="{INK}" stroke-width="2.8"/>')
# hair mass (big, since top-down) + one cowlick
s.append(f'<path d="M{hx-50} {hy-8} Q{hx} {hy-70} {hx+50} {hy-8} Q{hx+24} {hy-42} {hx} {hy-42} Q{hx-24} {hy-42} {hx-50} {hy-8} Z" fill="{HAIR}"/>')
s.append(f'<path d="M{hx+6} {hy-52} Q{hx+14} {hy-78} {hx+24} {hy-58} Q{hx+15} {hy-58} {hx+9} {hy-48} Z" fill="{HAIR}"/>')
# eyes + faint under-eye shadow + mouth
s.append(f'<circle cx="{hx-16}" cy="{hy+2}" r="3" fill="{INK}"/><circle cx="{hx+16}" cy="{hy+2}" r="3" fill="{INK}"/>')
s.append(f'<path d="M{hx-24} {hy+13} Q{hx-16} {hy+18} {hx-8} {hy+13}" stroke="{G}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
s.append(f'<path d="M{hx+8} {hy+13} Q{hx+16} {hy+18} {hx+24} {hy+13}" stroke="{G}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
s.append(f'<line x1="{hx-10}" y1="{hy+27}" x2="{hx+10}" y2="{hy+27}" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>')

# ---- DESK (perspective, the primary surface) ----
s.append(f'<polygon points="150,300 470,300 560,548 60,548" fill="{DESKC}" stroke="{INK}" stroke-width="2.8"/>')
# desk front face + brand emblem (browser, minor)
s.append(f'<polygon points="60,548 560,548 560,592 60,592" fill="{CREAM}" stroke="{INK}" stroke-width="2.6"/>')
ex, ey = 310, 570
s.append(f'<path d="M{ex} {ey-11} Q{ex+11} {ey-6} {ex+8} {ey+6} Q{ex} {ey+11} {ex-8} {ey+6} Q{ex-11} {ey-6} {ex} {ey-11} Z" '
         f'fill="none" stroke="{INK}" stroke-width="1.8"/>'
         f'<path d="M{ex-5} {ey-9} L{ex-8} {ey-14} M{ex+5} {ey-9} L{ex+8} {ey-14}" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')

# ---- items on the desk (perspective quads) ----
# EXAM (task) center-front
s.append(f'<polygon points="{quad(232,452,168,128,.16)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
for i in range(3):
    yy = 432 + i*12
    s.append(f'<line x1="164" y1="{yy}" x2="296" y2="{yy}" stroke="{INK}" stroke-width="1.1" opacity=".45"/>')
# RECIPE clipped to the exam (in-task) with paperclip + distill mark
s.append(f'<polygon points="{quad(232,398,132,66,.13)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
s.append(f'<rect x="222" y="360" width="8" height="12" rx="3" fill="none" stroke="{INK}" stroke-width="2"/>')  # clip
s.append(f'<rect x="180" y="382" width="48" height="5" fill="{INK}"/>')
s.append(f'<line x1="180" y1="405" x2="284" y2="405" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
s.append(f'<line x1="180" y1="412" x2="264" y2="412" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
s.append(f'<path d="M280 372 L292 372 L288 378 L288 384 L284 384 L284 378 Z" fill="{PAPER}" stroke="{INK}" stroke-width="1.5"/>')  # funnel
# BINDER (raw material) right side + spiral (scrappy = experiential) + ANALYSIS sheet on top
s.append(f'<polygon points="{quad(430,470,130,92,.12)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
s.append(f'<polygon points="{quad(378,470,26,92,.12)}" fill="{DESKC}" stroke="{INK}" stroke-width="2.4"/>')
for k in range(4):
    s.append(f'<circle cx="376" cy="{444+k*16}" r="2" fill="none" stroke="{INK}" stroke-width="1.4"/>')
s.append(f'<path d="M398 462 q10 -4 20 0 t20 0" stroke="{INK}" stroke-width="1.3" fill="none" opacity=".55"/>')
s.append(f'<polygon points="{quad(432,418,110,50,.1)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>')  # analysis sheet
s.append(f'<rect x="392" y="404" width="40" height="4.5" fill="{INK}"/>')
s.append(f'<line x1="392" y1="424" x2="470" y2="424" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')

# ---- callouts ----
s.append(label(566, 44, 470, 78, "THOUGHT BUBBLE\nwhat it ALREADY read\n(internalized prior)", "end", em=True))
s.append(label(40, 175, 258, 212, "FACE = tiredness\n= context load\nthe COST  ·  emphasize", "start", em=True))
s.append(label(500, 275, 296, 288, "shirt crest\n= harness (minor)", "start"))
s.append(label(496, 585, 320, 572, "desk brand\n= browser (minor)", "start"))
s.append(label(58, 470, 200, 452, "EXAM\n= the task", "end", em=True))
s.append(label(58, 405, 224, 398, "RECIPE\nclipped to the exam\n(in the task, forced)", "end", em=True))
s.append(label(576, 500, 452, 478, "BINDER\n= raw material\non the desk\n(optional, unread)", "start", em=True))
s.append(label(576, 410, 456, 418, "ANALYSIS SHEET\nclean, on the binder", "start", em=True))
s.append('</g>')
s.append('</svg>')
svg = "".join(s)

CSS = """
:root{--bg:#f4f1ea;--ink:#2b2a27;--muted:#6b675e;--dim:#948f84;--line:#d8d3c7;--card:#fffdf6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:44px 30px 90px}
.eyebrow{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
h1{font-size:25px;letter-spacing:-.01em;margin:2px 0 6px}
.lede{font-size:15.5px;color:var(--muted);max-width:70ch}
.frame{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:18px 0}
.em{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.tag{font:600 11.5px ui-monospace,Menlo,monospace;border:1px solid var(--line);border-radius:20px;padding:4px 11px;background:var(--card)}
.tag.pri{border-color:var(--ink)}
.note{font-size:12.5px;color:var(--muted);max-width:70ch}
"""
html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Composite frame · aggregate vision</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK · ICONOGRAPHY · AGGREGATE COMPOSITE</div>
<h1>One amalgam frame: every variable at once</h1>
<p class="lede">Not a real arm. A composite that carries every component together so we can agree on the aggregate
before we vary anything. Front-and-above camera, angled down onto the desk, because the desk and its items are the key
information and the angle spreads them out instead of stacking them.</p>
<div class="em">
<span class="tag pri">PRIMARY · the desk + its items</span>
<span class="tag pri">PRIMARY · the face + the thought bubble</span>
<span class="tag">minor · shirt crest (harness)</span>
<span class="tag">minor · desk brand (browser)</span>
</div>
<div class="frame">{svg}</div>
<p class="note">Reading it: the <b>face</b> carries the cost (tiredness = context load). The <b>thought bubble</b> is the
past (what it already read). The <b>desk</b> is the present environment: the exam is the task, the recipe is clipped onto
the exam (in the task, unavoidable), the binder is raw material sitting on the desk (available, optional), and the clean
analysis sheet rests on the binder. Harness (shirt) and browser (desk brand) are deliberately small. Lo-fi encoding only;
the final render is an OpenAI image model driven by the prompt this frame defines.</p>
</div></body></html>"""
out = os.path.join(BENCH, "composite.html")
open(out, "w").write(html)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

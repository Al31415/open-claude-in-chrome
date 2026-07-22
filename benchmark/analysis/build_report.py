#!/usr/bin/env python3
"""Generate benchmark_report.html from analysis JSONs.

Inputs : analysis/harvest.json, analysis/stats.json, analysis/amortization.json,
         archive/benchmark_report_pre_fix.html (dashdish-8 exhibits, ported)
Output : benchmark_report.html (self-contained)

Reproduce: python3 analysis/harvest.py && python3 analysis/stats.py &&
           python3 analysis/deepdive.py && python3 analysis/build_report.py
"""
import json, os, re, statistics, html as htmlmod

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
S = json.load(open(os.path.join(BENCH, "analysis", "stats.json")))
AM = json.load(open(os.path.join(BENCH, "analysis", "amortization.json")))
ORDER = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))["test_order"]
OLD = open(os.path.join(BENCH, "archive", "benchmark_report_pre_fix.html")).read()

# ---- palette (validated: dataviz six checks, light surface #fbfbf9) ---------
ARM_META = {  # label, color, prep_min (source-material + analysis authoring)
    "exp1a-fixed-chrome":          ("1A-fixed · Chrome, cold",        "#3b82f6", 0.0),
    "exp1a-fixed-brave":           ("1A-fixed · Brave, cold",         "#0d9488", 0.0),
    "exp1b-cinc-cold":             ("1B · official CinC, cold",       "#d97706", 0.0),
    "exp2a-fixed-brave":           ("2A-fixed · experiential raw",    "#db2777", 26.1),
    "exp2b-fixed-brave":           ("2B-fixed · expert raw",          "#10b981", 17.0),
    "exp3b-brave":                 ("3B · expert analysis + code",    "#7c3aed", 20.5),
    "exp3c-analysis":              ("3C · expert analysis, silent",   "#10b981", 20.5),
    "exp3d-experiential-analysis": ("3D · experiential analysis",     "#db2777", 32.6),
}
# raw-trace arms share their source's hue (emerald = expert, pink = experiential)
# and are drawn hollow/dashed; compressed-analysis arms are solid.
RAW_ARMS = {"exp2a-fixed-brave", "exp2b-fixed-brave"}
# only fully-run arms enter the report (2B-fixed may still be mid-flight)
ARM_META = {a: v for a, v in ARM_META.items() if len(H.get(a, {})) == 12}
PREFIX_ARMS = ["exp1a-ocic-cold", "exp1a-chrome", "exp2a-experiential",
               "exp2b-expert", "exp3a-code", "exp3b-code-analysis"]
PREFIX_LABEL = {
    "exp1a-ocic-cold": "1A · OCIC Brave, cold", "exp1a-chrome": "1A · OCIC Chrome, cold",
    "exp2a-experiential": "2A · raw self traces", "exp2b-expert": "2B · raw expert recordings",
    "exp3a-code": "3A · expert raw + code", "exp3b-code-analysis": "3B · expert analysis + code",
}
PREFIX_PREP = {"exp2a-experiential": 26.1, "exp2b-expert": 17.0, "exp3a-code": 17.0,
               "exp3b-code-analysis": 20.5, "exp1a-ocic-cold": 0.0, "exp1a-chrome": 0.0}

def esc(s): return htmlmod.escape(str(s))

def arm_stats(a):
    rows = H[a]
    n = len(rows); p = sum(1 for r in rows.values() if r["passed"])
    run = sum(r["run_s"] for r in rows.values()) / 60.0
    med_act = statistics.mean([r["median_action_s"] for r in rows.values() if r.get("median_action_s")])
    tot_act = statistics.mean([r.get("total_action_s", 0) for r in rows.values()])
    turns = statistics.mean([r["turns"] for r in rows.values()])
    repl = sum(r.get("replays", 0) for r in rows.values())
    ec = sum(r.get("execute_code", r.get("execute_code_traj", 0)) for r in rows.values())
    return dict(n=n, passed=p, run_min=run, med_act=med_act, tot_act=tot_act,
                turns=turns, replays=repl, ec=ec)

A = {a: arm_stats(a) for a in list(ARM_META) + PREFIX_ARMS}

def get_test(frag):
    for t in S:
        if frag in t["time"]["comparison"]: return t
    raise KeyError(frag)

T_CHROME = get_test("fixed (Chrome) vs CinC")
T_BRAVE = get_test("fixed (Brave) vs CinC")
T_3C = get_test("expert-analysis (3c) vs cold baseline")
T_3D = get_test("experiential-analysis (3d) vs cold baseline")
T_3C3D = get_test("(3c) vs experiential-analysis (3d)")

def fmt_p(p): return ("%.4f" % p).rstrip("0").rstrip(".") if p >= 0.001 else "%.4f" % p

# ---- svg helpers -------------------------------------------------------------
def svg_open(w, h): return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="inherit" role="img">'

def paired_dot_chart():
    """Chart A: per-task median action round-trip, OCIC-fixed-chrome vs CinC (same browser)."""
    w, hrow, pad_l, pad_t = 660, 21, 128, 30
    hgt = pad_t + hrow * 12 + 34
    xmax = 0.42
    def X(v): return pad_l + (w - pad_l - 18) * min(v, xmax) / xmax
    out = [svg_open(w, hgt)]
    for gx in (0.1, 0.2, 0.3, 0.4):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pad_t-8}" x2="{X(gx):.0f}" y2="{hgt-30}" stroke="#e7e6e1"/>'
                   f'<text x="{X(gx):.0f}" y="{hgt-16}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}s</text>')
    for i, t in enumerate(ORDER):
        y = pad_t + i * hrow + 10
        a = H["exp1a-fixed-chrome"][t]["median_action_s"]; b = H["exp1b-cinc-cold"][t]["median_action_s"]
        out.append(f'<text x="{pad_l-10}" y="{y+4}" text-anchor="end" font-size="11" fill="#5b6571">{t}</text>')
        out.append(f'<line x1="{X(a):.1f}" y1="{y}" x2="{X(b):.1f}" y2="{y}" stroke="#e7e6e1" stroke-width="2"/>')
        out.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="4.5" fill="#d97706"><title>{t} · CinC {b:.2f}s</title></circle>')
        out.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="4.5" fill="#3b82f6"><title>{t} · OCIC-fixed {a:.2f}s</title></circle>')
    y0 = pad_t - 14
    out.append(f'<circle cx="{pad_l+6}" cy="{y0}" r="4.5" fill="#3b82f6"/><text x="{pad_l+15}" y="{y0+4}" font-size="11" fill="#5b6571">OCIC fixed (Chrome)</text>')
    out.append(f'<circle cx="{pad_l+166}" cy="{y0}" r="4.5" fill="#d97706"/><text x="{pad_l+175}" y="{y0+4}" font-size="11" fill="#5b6571">official CinC (Chrome)</text>')
    out.append("</svg>")
    return "".join(out)

def totals_chart():
    """Chart B (preserved): total time, preparation stacked onto runs."""
    arms = list(ARM_META)
    w, hrow, pad_l, pad_t = 660, 34, 208, 14
    hgt = pad_t + hrow * len(arms) + 36
    xmax = 76.0
    def X(v): return pad_l + (w - pad_l - 88) * min(v, xmax) / xmax
    out = [svg_open(w, hgt)]
    for gx in (15, 30, 45, 60, 75):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pad_t-4}" x2="{X(gx):.0f}" y2="{hgt-30}" stroke="#e7e6e1"/>'
                   f'<text x="{X(gx):.0f}" y="{hgt-16}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}m</text>')
    for i, a in enumerate(arms):
        lbl, col, prep = ARM_META[a]; st = A[a]
        y = pad_t + i * hrow + 4; bh = 17
        out.append(f'<text x="{pad_l-10}" y="{y+13}" text-anchor="end" font-size="11.5" fill="#1b1f24">{esc(lbl)}</text>')
        x = pad_l
        if prep > 0:
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{X(prep)-pad_l:.1f}" height="{bh}" rx="3" fill="#8a929c" opacity="0.45"><title>{esc(lbl)} · preparation {prep:.1f}m</title></rect>')
            x = X(prep) + 2
        rw = X(prep + st["run_min"]) - x
        style = (f'fill="#fbfbf9" stroke="{col}" stroke-width="2"' if a in RAW_ARMS
                 else f'fill="{col}"')
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(rw,2):.1f}" height="{bh}" rx="3" {style}><title>{esc(lbl)} · 12 runs {st["run_min"]:.1f}m</title></rect>')
        tot = prep + st["run_min"]
        out.append(f'<text x="{X(tot)+6:.1f}" y="{y+13}" font-size="11" fill="#5b6571" font-variant-numeric="tabular-nums">{tot:.0f}m · {st["passed"]}/12</text>')
    out.append(f'<rect x="{pad_l}" y="{hgt-12}" width="11" height="11" rx="2" fill="#8a929c" opacity="0.45"/>'
               f'<text x="{pad_l+16}" y="{hgt-3}" font-size="10.5" fill="#5b6571">one-time preparation (recording / generation + analysis authoring)</text>')
    out.append("</svg>")
    return "".join(out)

def amortization_chart():
    """Chart C (preserved): cumulative time vs number of tasks, prep offsets included."""
    arms = list(ARM_META)
    w, hgt, pad_l, pad_t, pad_b, pad_r = 660, 330, 52, 16, 30, 118
    ymax = 75.0
    def X(i): return pad_l + (w - pad_l - pad_r) * i / 12.0
    def Y(v): return hgt - pad_b - (hgt - pad_t - pad_b) * min(v, ymax) / ymax
    out = [svg_open(w, hgt)]
    for gy in (0, 25, 50, 75):
        out.append(f'<line x1="{pad_l}" y1="{Y(gy):.0f}" x2="{w-pad_r}" y2="{Y(gy):.0f}" stroke="#e7e6e1"/>'
                   f'<text x="{pad_l-6}" y="{Y(gy)+4:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy}m</text>')
    for i in range(0, 13, 2):
        out.append(f'<text x="{X(i):.0f}" y="{hgt-12}" text-anchor="middle" font-size="10" fill="#8a929c">{i}</text>')
    out.append(f'<text x="{(pad_l+w-pad_r)/2:.0f}" y="{hgt-1}" text-anchor="middle" font-size="10.5" fill="#5b6571">tasks completed (test-split order)</text>')
    lab_ys = []
    for a in arms:
        lbl, col, prep = ARM_META[a]
        cum = 0.0; series = []
        for t in ORDER:
            cum += H[a][t]["run_min"]; series.append(cum)
        pts = [(0, prep)] + [(i + 1, prep + c) for i, c in enumerate(series)]
        d = " ".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in pts)
        dash = ' stroke-dasharray="6 4"' if a in RAW_ARMS else ""
        out.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="2"{dash}><title>{esc(lbl)}</title></polyline>')
        if prep > 0:
            out.append(f'<circle cx="{X(0):.1f}" cy="{Y(prep):.1f}" r="3.5" fill="#fbfbf9" stroke="{col}" stroke-width="2"><title>{esc(lbl)} · prep {prep:.1f}m</title></circle>')
        ex, ey = X(12), Y(pts[-1][1])
        while any(abs(ey - o) < 12 for o in lab_ys): ey -= 12
        lab_ys.append(ey)
        out.append(f'<circle cx="{X(12):.1f}" cy="{Y(pts[-1][1]):.1f}" r="3.5" fill="{col}"/>')
        SHORT = {"exp1a-fixed-chrome": "1A-fx Chrome", "exp1a-fixed-brave": "1A-fx Brave",
                 "exp1b-cinc-cold": "1B CinC", "exp2a-fixed-brave": "2A-fx raw",
                 "exp2b-fixed-brave": "2B-fx raw", "exp3b-brave": "3B",
                 "exp3c-analysis": "3C", "exp3d-experiential-analysis": "3D"}
        short = SHORT.get(a, lbl.split("\u00b7")[0].strip())
        out.append(f'<text x="{ex+7:.1f}" y="{ey+4:.1f}" font-size="10.5" fill="{col}">{esc(short)} {pts[-1][1]:.0f}m</text>')
    out.append("</svg>")
    return "".join(out)

def bridge_chart():
    """Chart D: the fix absorbed the pre-training effect (accuracy + pace panels)."""
    groups = [
        ("cold", "pre-fix", "exp1a-ocic-cold"), ("expert raw", "pre-fix", "exp2b-expert"),
        ("cold", "post-fix", "exp1a-fixed-brave"), ("expert analysis", "post-fix", "exp3c-analysis"),
        ("experiential analysis", "post-fix", "exp3d-experiential-analysis"),
    ]
    w, hgt = 660, 278
    out = [svg_open(w, hgt)]
    def panel(x0, title, val, vmax, fmt):
        pw = 292; bw = 40; gap = 16
        out.append(f'<text x="{x0}" y="18" font-size="12" font-weight="600" fill="#1b1f24">{title}</text>')
        base_y = 218
        for i, (lbl, era, arm) in enumerate(groups):
            v = val(arm); bh = (base_y - 40) * v / vmax
            x = x0 + i * (bw + gap)
            col = ARM_META.get(arm, (None, None))[1] or {"exp1a-ocic-cold": "#9fb2c8", "exp2b-expert": "#c7b3ee"}[arm]
            op = "0.55" if era == "pre-fix" else "1"
            out.append(f'<rect x="{x}" y="{base_y-bh:.1f}" width="{bw}" height="{bh:.1f}" rx="4" fill="{col}" opacity="{op}"><title>{esc(lbl)} ({era}): {fmt(v)}</title></rect>')
            out.append(f'<text x="{x+bw/2:.0f}" y="{base_y-bh-6:.0f}" text-anchor="middle" font-size="11.5" font-weight="600" fill="#1b1f24">{fmt(v)}</text>')
            for j, word in enumerate(lbl.split(" ")):
                out.append(f'<text x="{x+bw/2:.0f}" y="{base_y+13+j*11}" text-anchor="middle" font-size="9.5" fill="#5b6571">{esc(word)}</text>')
    panel(20, "accuracy (tasks passed of 12)", lambda a: A[a]["passed"], 12, lambda v: f"{v}")
    panel(360, "pace (mean minutes per task)", lambda a: A[a]["run_min"] / 12, 4.5, lambda v: f"{v:.1f}m")
    out.append(f'<line x1="330" y1="10" x2="330" y2="244" stroke="#e7e6e1"/>')
    out.append(f'<text x="20" y="272" font-size="10.5" fill="#8a929c">faded bars = pre-fix harness (throttled inputs) · solid = post-fix · both cold arms are the same prompt on the same tasks</text>')
    out.append("</svg>")
    return "".join(out)

def accuracy_grid():
    """Preserved: pass/fail identity grid, post-fix arms + CinC, pre-fix arms appended muted."""
    arms = list(ARM_META) + PREFIX_ARMS
    heads = "".join(
        f'<th style="min-width:74px{";opacity:.55" if a in PREFIX_ARMS else ""}">{esc((ARM_META.get(a) or (PREFIX_LABEL[a],))[0])}</th>'
        for a in arms)
    rows = []
    for t in ORDER:
        cells = []
        for a in arms:
            r = H[a][t]
            mut = "opacity:.55;" if a in PREFIX_ARMS else ""
            if r["passed"]:
                cells.append(f'<td style="{mut}text-align:center;color:#0f8a5f" title="{esc(t)} · {r["run_min"]}min">●</td>')
            else:
                cells.append(f'<td style="{mut}text-align:center" title="{esc(t)} · {r["run_min"]}min"><span style="font-size:10px;font-weight:700;color:#c13a2e">FAIL</span></td>')
        rows.append(f'<tr><td class="mono" style="white-space:nowrap">{esc(t)}</td>{cells}</tr>'.replace("{cells}", "".join(cells)))
    body = "".join(f'<tr><td class="mono" style="white-space:nowrap">{esc(t)}</td>' + "".join(
        (lambda r, mut: f'<td style="{mut}text-align:center;color:#0f8a5f" title="{r["run_min"]}min">●</td>' if r["passed"]
         else f'<td style="{mut}text-align:center" title="{r["run_min"]}min"><span style="font-size:10px;font-weight:700;color:#c13a2e">FAIL</span></td>')
        (H[a][t], "opacity:.55;" if a in PREFIX_ARMS else "") for a in arms) + "</tr>" for t in ORDER)
    foot = "<tr><td style='font-weight:600'>passed</td>" + "".join(
        f'<td style="text-align:center;font-weight:700{";opacity:.55" if a in PREFIX_ARMS else ""}">{A[a]["passed"]}/12</td>' for a in arms) + "</tr>"
    return f'<div class="scroll"><table><thead><tr><th>task</th>{heads}</tr></thead><tbody>{body}{foot}</tbody></table></div>'

def stat_table(tests):
    rows = []
    for label, t in tests:
        r = t["time"]; al = r["all"]; pb = r["pass_both"]; acc = r["accuracy"]
        rows.append(
            f"<tr><td>{esc(label)}</td>"
            f"<td class='num'>{al['mean_a']:.2f} vs {al['mean_b']:.2f}</td>"
            f"<td class='num'>{al['mean_diff']:+.2f}</td><td class='num'>{fmt_p(al['p_perm'])}</td>"
            f"<td class='num'>{pb.get('mean_diff', float('nan')):+.2f} (n={pb['n']})</td>"
            f"<td class='num'>{fmt_p(pb['p_perm']) if 'p_perm' in pb else '·'}</td>"
            f"<td class='num'>{acc['pass_a']} vs {acc['pass_b']}</td><td class='num'>{fmt_p(acc['p_mcnemar'])}</td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>comparison (A vs B)</th><th>mean min/task</th>"
            "<th>Δ all 12</th><th>p</th><th>Δ pass-both</th><th>p</th><th>accuracy</th><th>p</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _pearson(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0

def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r

def _spearman(xs, ys): return _pearson(_rank(xs), _rank(ys))

def savings_chart():
    """Per-task time saved vs task length (cold-run duration), pre-fix and
    post-fix panels. Hue = experience source; hollow = raw, solid = analysis."""
    PINK, EMERALD = "#db2777", "#10b981"
    panels = [
        ("pre-fix pairs (cold = 1A Brave)", "exp1a-ocic-cold", [
            ("2A raw self traces", "exp2a-experiential", PINK, False),
            ("2B raw expert recordings", "exp2b-expert", EMERALD, False),
        ]),
        ("post-fix pairs (cold = 1A-fixed Brave)", "exp1a-fixed-brave", [
            ("2A-fixed experiential raw", "exp2a-fixed-brave", PINK, False),
            ("3D experiential analysis", "exp3d-experiential-analysis", PINK, True),
            ("2B-fixed expert raw", "exp2b-fixed-brave", EMERALD, False),
            ("3C expert analysis", "exp3c-analysis", EMERALD, True),
        ]),
    ]
    w, hgt = 660, 330
    pw = 296; pad_l = 46; pad_t = 34; pad_b = 46
    xmax, ymin, ymax = 11.0, -10.0, 7.0
    out = [svg_open(w, hgt)]
    stats_rows = []
    for pi, (title, cold, arms) in enumerate(panels):
        x0 = 10 + pi * (pw + 34)
        def X(v, x0=x0): return x0 + pad_l + (pw - pad_l - 8) * min(v, xmax) / xmax
        def Y(v): return pad_t + (hgt - pad_t - pad_b) * (ymax - max(min(v, ymax), ymin)) / (ymax - ymin)
        out.append(f'<text x="{x0+pad_l}" y="20" font-size="12" font-weight="600" fill="#1b1f24">{esc(title)}</text>')
        for gy in (-10, -5, 0, 5):
            wgt = 2 if gy == 0 else 1
            colr = "#c9c7c1" if gy == 0 else "#e7e6e1"
            out.append(f'<line x1="{x0+pad_l}" y1="{Y(gy):.0f}" x2="{x0+pw}" y2="{Y(gy):.0f}" stroke="{colr}" stroke-width="{wgt}"/>'
                       f'<text x="{x0+pad_l-5}" y="{Y(gy)+4:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy:+d}m</text>')
        for gx in (3, 6, 9):
            out.append(f'<text x="{X(gx):.0f}" y="{hgt-28}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}m</text>')
        out.append(f'<text x="{x0+pad_l+(pw-pad_l)/2:.0f}" y="{hgt-14}" text-anchor="middle" font-size="10.5" fill="#5b6571">task length: cold-run minutes on the task</text>')
        for lbl, arm, col, solid in arms:
            if arm not in H or len(H[arm]) < 12: continue
            xs = [H[cold][t]["run_min"] for t in ORDER]
            ys = [H[cold][t]["run_min"] - H[arm][t]["run_min"] for t in ORDER]
            rho = _spearman(xs, ys); r = _pearson(xs, ys)
            stats_rows.append((title.split(" (")[0], lbl, r, rho))
            fill = col if solid else "#fbfbf9"
            for t, xv, yv in zip(ORDER, xs, ys):
                clip = "" if ymin <= yv <= ymax else " (point clipped to border)"
                out.append(f'<circle cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="4.2" fill="{fill}" fill-opacity="0.9" stroke="{col}" stroke-width="1.8"><title>{esc(lbl)} · {esc(t)}: cold {xv:.1f}m, saved {yv:+.1f}m{clip}</title></circle>')
    out.append("</svg>")
    tab = "".join(f"<tr><td>{esc(p)}</td><td>{esc(l)}</td><td class=\"num\">{r:+.2f}</td><td class=\"num\">{rho:+.2f}</td></tr>"
                  for p, l, r, rho in stats_rows)
    table = ("<div class=\"scroll\"><table><thead><tr><th>era</th><th>pre-trained arm vs its cold baseline</th>"
             "<th>Pearson r</th><th>Spearman \u03c1</th></tr></thead><tbody>" + tab + "</tbody></table></div>")
    return "".join(out), table

# dashdish-8 exhibits ported verbatim from the archived report
SAV_SVG, SAV_TABLE = savings_chart()

figs = re.findall(r'<figure class="shot">.*?</figure>', OLD, re.S)
assert len(figs) == 3, f"expected 3 dd8 exhibits, found {len(figs)}"

acts = {a: A[a]["med_act"] for a in ("exp1a-fixed-chrome", "exp1a-fixed-brave", "exp1b-cinc-cold")}
speedup = acts["exp1b-cinc-cold"] / statistics.mean([acts["exp1a-fixed-chrome"], acts["exp1a-fixed-brave"]])
repl_total = sum(A[a]["replays"] for a in list(ARM_META))

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · post-fix studies</title>
<style>{re.search(r"<style>(.*?)</style>", OLD, re.S).group(1)}</style></head><body><div class="wrap">

<div class="eyebrow">OCIC BENCHMARK · REAL WEBCLONES · POST-FIX STUDIES · 2026-07-15</div>
<h1>The harness is what got faster: OCIC beats the official stack on every task's round-trip, and a healthy harness absorbs the pre-training effect</h1>
<p class="lede">Two paired studies on the same 12 held-out REAL webclone tasks (dashdish, zilloft), sonnet at medium effort,
one fresh tab per rollout, deterministic + judged evaluation. Study 1 compares the fixed OCIC extension against official
Claude in Chrome. Study 2 asks what compressed prior experience (expert vs the agent's own) is still worth once the
harness is healthy. All tests are exact paired permutation tests; accuracy is the guardrail everywhere.</p>

<div class="kpis">
<div class="kpi"><div class="n">0.12s vs 0.26s</div><div class="l">median browser-action round-trip, OCIC-fixed vs official CinC ({speedup:.1f}x)</div></div>
<div class="kpi"><div class="n">12/12 · p=.0005</div><div class="l">tasks where OCIC's per-action median beats CinC on the same browser (exact floor at n=12)</div></div>
<div class="kpi"><div class="n">&minus;0.65 min/task</div><div class="l">run time, Brave arm vs CinC on tasks both passed (p=.008)</div></div>
<div class="kpi"><div class="n">11/12 cold</div><div class="l">post-fix baseline accuracy with no prior experience at all</div></div>
<div class="kpi"><div class="n">0/12 arms</div><div class="l">dashdish-8 passes nowhere; verdict unchanged from the pre-fix deep dive</div></div>
</div>

<h2>1 &middot; Study 1: OCIC vs official Claude in Chrome</h2>
<p><span class="verdict v-conf">H1 CONFIRMED</span><strong>Hypothesis: OCIC performs no worse than the official stack, possibly marginally better.</strong>
It is never worse, and where the comparison is powered it is significantly faster. The cleanest signal is harness
round-trip time, which excludes model thinking: OCIC's per-task median action latency beats CinC on 12 of 12 tasks on the
same browser (Chrome), p=.0005, the smallest p an exact paired test can produce at n=12. In-harness time per task is
{A['exp1a-fixed-chrome']['tot_act']:.0f}s vs {A['exp1b-cinc-cold']['tot_act']:.0f}s (p=.021).</p>

<div class="card"><h3 style="margin-top:2px">per-task median action round-trip, same browser (Chrome)</h3>{paired_dot_chart()}
<p class="note">One row per test task; the connecting bar is the gap. OCIC-fixed is left of CinC on every row.
Round-trip = tool_use to tool_result wall time across all browser MCP calls in the rollout trajectory.</p></div>

<h3>Task completion time and accuracy</h3>
{stat_table([("OCIC fixed (Chrome) vs CinC, same browser", T_CHROME), ("OCIC fixed (Brave) vs CinC", T_BRAVE)])}
<p>Whole-task time is mostly model thinking, so harness gains dilute: the same-browser comparison is directionally faster
(&minus;1.29 min/task) but not significant (p=.14), dominated by outliers on failed tasks. The Brave arm is significant on all 12
(p=.007) and stays significant restricted to tasks both arms passed (&minus;0.65 min/task, 8/8 tasks faster, p=.008).
Accuracy never favors CinC: every discordant task flips toward OCIC (3+/0&minus; on Brave, 2+/1&minus; on Chrome), though
n=12 has no power to certify accuracy gaps (McNemar p&ge;.25). CinC's 18-minute zilloft-9 failure is the single largest
time entry in the whole dataset.</p>

<div class="callout"><strong>Caveats, stated plainly.</strong> CinC ran three weeks earlier than the fixed arms (same model,
same CLI family, same tasks, same evaluator; the OCIC fix does not touch the official extension). The Brave-vs-CinC
comparison crosses browsers; the same-browser Chrome comparison is the primary and its per-action result carries the
conclusion. zilloft-10's LLM-judged verdict is noisy: it accepted answers of 12, 13, and one of two 160s; zilloft-5 shows the same
pattern (a bare '3 results' fails, '3 shown but only 1 in San Jose' passes). Treat those cells as grading noise plus a
test of noticing the location-filter mirage, not pure capability signal.</div>

<h2>2 &middot; Study 2: what is pre-training + analysis still worth?</h2>
<p><span class="verdict v-deb">H2 NOT SUPPORTED POST-FIX</span><strong>Hypothesis: compressed prior experience makes runs faster, more effective, higher-accuracy.</strong>
That was true on the broken harness; the fix absorbed it. Pre-fix, priors lifted accuracy from 8/12 (cold) to 11/12
(expert). Post-fix, the cold baseline alone reaches 11/12 at {A['exp1a-fixed-brave']['run_min']/12:.1f} min/task, and neither analysis arm moves
either number: expert analysis is +0.05 min/task (p=.81) with literally zero discordant tasks against baseline; the
experiential arm is one task behind (10/12, McNemar p=1.0). The accuracy guardrail holds, with no regressions anywhere, but the measured benefit is gone.</p>

<div class="card"><h3 style="margin-top:2px">the fix absorbed the prior: accuracy and pace, before vs after</h3>{bridge_chart()}</div>

{stat_table([("3C expert analysis vs cold baseline (both Brave)", T_3C), ("3D experiential analysis vs cold baseline", T_3D), ("3C expert vs 3D experiential", T_3C3D)])}

<p><strong>Expert vs experiential source.</strong> The two analysis docs were produced by the same method from different
raw material (operator demonstrations vs the agent's own train-split rollouts). They are statistically indistinguishable
(p=.47 on time; one discordant task on accuracy). Self-distilled experience is as good as expert demonstrations once
compressed, and it is the cheaper pipeline, since it needs no operator.</p>

<p><strong>Why no effect? The agent barely consults the prior, and no longer needs it.</strong> 3C read its analysis docs in
7/12 rollouts, 3D in only 3/12 (always before acting when read at all). The one task where the doc's recipe demonstrably
mattered cut both ways: on zilloft-10, 3C read the doc and answered from the filtered header count (pass); 3D skipped the
doc, hand-paginated 160 listings across 4 pages for 121 turns, and failed with 158. The knowledge is right; compliance is
the bottleneck, and a healthy harness makes the floor high enough that skipping the docs usually costs nothing.
execute_code tells the same story it told pre-fix: encouragement inflates usage (32 calls in 3B) but silence nearly
eliminates it (4 in 3C, 7 in 3D) with identical outcomes. It is a red herring for performance.</p>

<div class="card"><h3 style="margin-top:2px">total time, preparation stacked onto runs (preserved view)</h3>{totals_chart()}
<p class="note">Preparation = source material + analysis authoring: 17m operator recording + 3.5m authoring for the expert
arms; 26.1m of agent train-split runs + 6.5m authoring for the experiential arm (file-timestamp measured). Cold arms pay nothing.</p></div>

<div class="card"><h3 style="margin-top:2px">amortization: cumulative time vs number of tasks (preserved view)</h3>{amortization_chart()}
<p class="note">Hollow markers are the one-time preparation offset. Post-fix, the prior-experience lines never catch the
cold baselines within the 12-task horizon: there is nothing left to amortize against. Pre-fix (archived report), the
gap they had to close was 2x wider.</p></div>

<div class="card"><h3 style="margin-top:2px">does the prior save more time on longer tasks?</h3>{SAV_SVG}
<p class="note">One point per test task per arm. x = the cold baseline of that era's minutes on the task (task length);
y = minutes the pre-trained arm saved on the same task (above the zero line = prior was faster). Hue = experience source
(pink experiential, emerald expert); hollow = raw traces, solid = compressed analysis. Off-scale points are clipped to
the border; hover any point for exact values.</p>
{SAV_TABLE}
<p class="note">Read: the correlation is positive in both eras but it is substantially a one-task story. zilloft-9, the
marathon (rightmost points), carries most of the savings; on the other eleven tasks the differences hover within about a
minute of zero. The prior pays off roughly in proportion to task length, and only the longest task in the suite is long
enough for it to matter.</p></div>

<h2>3 &middot; Accuracy grid (preserved view)</h2>
<p>Pass/fail identity for every arm; muted columns are the archived pre-fix arms. The post-fix suite is near-ceiling:
most current arms sit at 10&ndash;11 of 12 (the raw-traces arm dips to 9), and the failures concentrate in three
tasks: dashdish-8 (universal, below) and the two location-mirage counts, zilloft-5 and zilloft-10 (judged tasks that
reward noticing the app's location filter barely filters; bare header-count answers fail).</p>
{accuracy_grid()}

<h2 id="dd8">4 &middot; Deep dive: dashdish-8, still the task no arm can pass</h2>
<p>Ported from the pre-fix report and re-verified against the six current arms: <strong>0 of 12 arms have ever passed
dashdish-8</strong>, and the failure signature is identical post-fix: every arm answers fast (0.13&ndash;0.35 min,
3&ndash;9 turns) and wrong. The task: <em>"What are first three categories of deliverable food displayed on the
homepage?"</em> The rubric wants the first three curated collection rows ("Under $1 delivery fee", "Best of lunch",
"The Infatuation's picks"), verified post-hoc as literally the first three section headers in both DOM and visual
order. Every arm instead answers from the cuisine icon carousel at the top (Breakfast / Fast Food / Coffee). The same
taxonomy misreading, twelve independent times, across both harnesses, every experience condition, and with code
forbidden, permitted, and unmentioned. Neither analysis doc prevents it: both note the cuisine bar is a separate
taxonomy from the collections, but neither says which one "categories" means, and the ambiguity wins every time.
The three exhibits below are the original evidence, unchanged.</p>
{''.join(figs)}

<h2>5 &middot; The pre-fix record, corrected and archived</h2>
<p>The earlier report attributed OCIC's slow clicks to a Brave-specific debugger-ack quirk. That was wrong. The root cause
was <strong>background-tab input throttling</strong>: any Chromium stalls synthesized input ~5s to a non-visible tab
(measured live: 0.001s foreground vs 5.13s background for the same click on Chrome). The fix activates the workspace tab
once at creation, never stealing OS focus, and cut mean in-harness time per task from {A['exp1a-chrome']['tot_act']:.0f}s to
{A['exp1a-fixed-chrome']['tot_act']:.0f}s on Chrome (p=.032, 7x). OS focus is irrelevant to latency (verified: 0.002s with
Chrome visible but unfocused). Six pre-fix arms are preserved in the
<a href="archive/benchmark_report_pre_fix.html">archived report</a>; their totals appear muted in the grid above.</p>

<div class="scroll"><table><thead><tr><th>pre-fix arm</th><th>passed</th><th>12-run time</th><th>note</th></tr></thead><tbody>
{''.join(f"<tr><td>{esc(PREFIX_LABEL[a])}</td><td class='num'>{A[a]['passed']}/12</td><td class='num'>{A[a]['run_min']:.0f}m</td><td>{esc(n)}</td></tr>" for a, n in [
    ("exp1a-ocic-cold", "headline baseline, throttled inputs"),
    ("exp1a-chrome", "same, Chrome; the arm that exposed the 67-minute wall clock"),
    ("exp2a-experiential", "raw self-traces mounted; +2 tasks over cold"),
    ("exp2b-expert", "raw expert recordings; +3 tasks over cold"),
    ("exp3a-code", "expert raw + execute_code encouraged"),
    ("exp3b-code-analysis", "first compressed-analysis arm; fastest pre-fix"),
])}
</tbody></table></div>

<h2>6 &middot; Methods &amp; data integrity</h2>
<ul>
<li><strong>Pipeline.</strong> Per rollout: fresh tab &rarr; navigate &rarr; clear cache &rarr; /config seed &rarr; verify clean /finish &rarr;
detached <span class="mono">claude -p --model sonnet --effort medium</span> &rarr; capture /finish &rarr; close tab &rarr; evaluate
(REAL WebCloneEvaluator: jmespath deterministic checks + rubric-judged retrieval). Artifacts per rollout: prompt, raw result,
trajectory, finish state, evaluation, timing.</li>
<li><strong>Statistics.</strong> Exact paired sign-flip permutation test on mean per-task difference (4096 patterns at n=12),
exact Wilcoxon signed-rank alongside (agrees everywhere), exact McNemar for accuracy. Time comparisons reported twice:
all 12 pairs and the pass-both subset (a failed run's duration measures something else). Six planned comparisons, nominal p values.</li>
<li><strong>Replays.</strong> {repl_total} timeout-exceeded replays occurred within the six current arms; every scored trajectory is a clean single attempt. Pre-fix replay counts live in the archived report.</li>
<li><strong>Taint handling.</strong> One 3D rollout (zilloft-9) was interrupted and operator-touched mid-run; it was discarded and
rerun clean along with the three tasks behind it. The rerun passed all six checks.</li>
<li><strong>Known grading noise.</strong> zilloft-10 (LLM-judged) accepted 12, 13, and one of two 160-answers across arms;
zilloft-5 rewards acknowledging the location-filter mirage (bare counts fail). dashdish-8's rubric contradiction is
section 4. All affect every arm symmetrically.</li>
<li><strong>Earlier false alarm.</strong> Pre-fix runs paused on spurious rate-limit detections (a 429 regex matching inside JSON numbers);
detection is now failure-gated with digit boundaries. No current-arm rollout hit a real throttle.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py && python3 analysis/stats.py && python3 analysis/deepdive.py && python3 analysis/build_report.py</span></li>
</ul>

<p class="note" style="margin-top:40px">OCIC benchmark · REAL webclones (dashdish, zilloft) · 12 held-out test tasks ·
sonnet, medium effort · exact paired tests · generated {__import__('datetime').date.today().isoformat()} ·
archived pre-fix report: <a href="archive/benchmark_report_pre_fix.html">archive/benchmark_report_pre_fix.html</a></p>
</div></body></html>"""

out_p = os.path.join(BENCH, "benchmark_report.html")
open(out_p, "w").write(page)
print("wrote", out_p, f"({os.path.getsize(out_p)/1024:.0f} KB)")

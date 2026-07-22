#!/usr/bin/env python3
"""benchmark_report.html v2: phases 1-4 post-fix, interactive, small-n-honest.

Statistical stance: n=12 paired tasks. Evidence is presented as (1) all raw
pairs shown, (2) paired effect sizes with 10k-resample bootstrap CIs,
(3) task-level win/loss/tie records, (4) replication across independent
comparisons, (5) mechanism decomposition. Exact permutation p-values are kept
as footnotes, not headlines.

Reproduce: harvest.py -> stats.py -> build_report_v2.py
"""
import json, os, random, statistics, html as H

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARV = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
STATS = json.load(open(os.path.join(BENCH, "analysis", "stats.json")))
FAILS = json.load(open(os.path.join(BENCH, "analysis", "fail_answers.json")))
FOCUS = json.load(open(os.path.join(BENCH, "analysis", "focus_adjusted.json")))
MAN = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))
ORDER = MAN["test_order"]; TASKS = MAN["tasks"]

# ---- arm registry ------------------------------------------------------------
# (label, short, color, family, delivery, prep_min)
ARMS = {
    "exp1a-fixed-brave":           ("Cold · Brave",             "cold",     "#0d9488", "cold",         "none",     0.0),
    "exp1a-fixed-chrome":          ("Cold · Chrome",            "cold-ch",  "#3b82f6", "cold",         "none",     0.0),
    "exp1b-cinc-cold":             ("CinC original (June)",     "cinc-old", "#d97706", "cold",         "none",     0.0),
    "exp1b-cinc-rerun":            ("CinC control (Jul 16)",    "cinc-ctl", "#b45309", "cold",         "none",     0.0),
    "exp1b-cinc-parity":           ("CinC parity (scripted)",   "cinc-par", "#f59e0b", "cold",         "none",     0.0),
    "exp2a-fixed-brave":           ("Experiential raw mount",   "2A",       "#db2777", "experiential", "raw",      26.1),
    "exp2b-fixed-brave":           ("Expert raw mount",         "2B",       "#10b981", "expert",       "raw",      17.0),
    "exp3d-experiential-analysis": ("Experiential analysis",    "3D",       "#db2777", "experiential", "analysis", 32.6),
    "exp3c-analysis":              ("Expert analysis",          "3C",       "#10b981", "expert",       "analysis", 20.5),
    "exp3b-brave":                 ("Expert analysis + code",   "3B",       "#7c3aed", "expert",       "analysis", 20.5),
    "exp4a-experiential-fork":     ("Experiential fork",        "4A",       "#9d174d", "experiential", "fork",     37.0),
    "exp4b-expert-fork":           ("Expert fork",              "4B",       "#047857", "expert",       "fork",     44.1),
}
DEFAULT_ON = ["exp1a-fixed-brave", "exp1b-cinc-rerun", "exp1b-cinc-parity",
              "exp3c-analysis", "exp4b-expert-fork"]

def arm_summary(a):
    rows = HARV[a]
    run = sum(r["run_s"] for r in rows.values()) / 60.0
    passed = sum(1 for r in rows.values() if r["passed"])
    turns = statistics.mean(r["turns"] for r in rows.values())
    per_turn = sum(r["run_s"] for r in rows.values()) / max(1, sum(r["turns"] for r in rows.values()))
    act = statistics.mean(r["median_action_s"] for r in rows.values() if r.get("median_action_s"))
    ec = sum(r.get("execute_code", r.get("execute_code_traj", 0)) for r in rows.values())
    fa = [r.get("first_action_s") for r in rows.values() if r.get("first_action_s") is not None]
    er = sum(r.get("experience_reads", 0) for r in rows.values())
    lbl, short, col, fam, dlv, prep = ARMS[a]
    return dict(arm=a, label=lbl, short=short, color=col, family=fam, delivery=dlv,
                prep=prep, passed=passed, run_min=round(run, 1),
                mean_task=round(run / 12, 2), turns=round(turns, 1),
                per_turn_s=round(per_turn, 2), med_action_s=round(act, 3),
                ec=ec, first_action_s=round(statistics.median(fa), 1) if fa else None,
                exp_reads=er)

SUM = {a: arm_summary(a) for a in ARMS}

# ---- paired evidence: effect size + bootstrap CI + win/loss ------------------
random.seed(1789)
def paired_evidence(a, b, metric="run_s", scale=1/60.0):
    diffs = [(HARV[a][t][metric] - HARV[b][t][metric]) * scale for t in ORDER]
    mean = statistics.mean(diffs)
    bs = []
    for _ in range(10000):
        s = [random.choice(diffs) for _ in diffs]
        bs.append(statistics.mean(s))
    bs.sort()
    lo, hi = bs[249], bs[9749]
    wins = sum(1 for d in diffs if d < -1e-9)   # a faster
    loss = sum(1 for d in diffs if d > 1e-9)
    ties = len(diffs) - wins - loss
    return dict(mean=round(mean, 2), lo=round(lo, 2), hi=round(hi, 2),
                wl=f"{wins}-{loss}" + (f"-{ties}" if ties else ""),
                diffs=[round(d, 2) for d in diffs])

def stat_p(frag):
    for t in STATS:
        if frag in t["time"]["comparison"]:
            return t["time"]["all"]["p_perm"], t["accuracy"] if "accuracy" in t["time"] else t["time"]["accuracy"]
    return None, None

COMPARISONS = [  # (id, label, a, b, study)
    ("s1chrome", "OCIC fixed Chrome vs CinC original (same browser)", "exp1a-fixed-chrome", "exp1b-cinc-cold", "S1"),
    ("s1brave",  "OCIC fixed Brave vs CinC original", "exp1a-fixed-brave",  "exp1b-cinc-cold", "S1"),
    ("s1control", "OCIC fixed vs CinC CONTROL (fresh rerun)", "exp1a-fixed-brave", "exp1b-cinc-rerun", "S1"),
    ("s1parity",  "OCIC fixed vs CinC PARITY (scripted preamble)", "exp1a-fixed-brave", "exp1b-cinc-parity", "S1"),
    ("s1pc",      "CinC parity vs CinC control", "exp1b-cinc-parity", "exp1b-cinc-rerun", "S1"),
    ("s2_2a", "Experiential raw vs cold",  "exp2a-fixed-brave", "exp1a-fixed-brave", "S2"),
    ("s2_2b", "Expert raw vs cold",        "exp2b-fixed-brave", "exp1a-fixed-brave", "S2"),
    ("s2_3d", "Experiential analysis vs cold", "exp3d-experiential-analysis", "exp1a-fixed-brave", "S2"),
    ("s2_3c", "Expert analysis vs cold",   "exp3c-analysis", "exp1a-fixed-brave", "S2"),
    ("s3_4a", "Experiential fork vs cold", "exp4a-experiential-fork", "exp1a-fixed-brave", "S3"),
    ("s3_4b", "Expert fork vs cold",       "exp4b-expert-fork", "exp1a-fixed-brave", "S3"),
    ("s3_4b3c", "Expert fork vs expert analysis", "exp4b-expert-fork", "exp3c-analysis", "S3"),
    ("s3_4b2b", "Expert fork vs expert raw", "exp4b-expert-fork", "exp2b-fixed-brave", "S3"),
    ("s3_4a3d", "Exp. fork vs exp. analysis", "exp4a-experiential-fork", "exp3d-experiential-analysis", "S3"),
    ("s3_4a2a", "Exp. fork vs exp. raw", "exp4a-experiential-fork", "exp2a-fixed-brave", "S3"),
    ("s3_4b4a", "Expert fork vs experiential fork", "exp4b-expert-fork", "exp4a-experiential-fork", "S3"),
]
EV = {}
for cid, lbl, a, b, study in COMPARISONS:
    e = paired_evidence(a, b)
    e_turns = paired_evidence(a, b, metric="turns", scale=1.0)
    p, acc = stat_p(SUM[a]["label"].split(" ·")[0][:10]) if False else (None, None)
    EV[cid] = dict(label=lbl, a=a, b=b, study=study, time=e, turns=e_turns,
                   pass_a=SUM[a]["passed"], pass_b=SUM[b]["passed"])
# attach exact p from stats.json by matching arm ids
for t in STATS:
    ta, tb = t["time"]["a"], t["time"]["b"]
    for cid, e in EV.items():
        if e["a"] == ta and e["b"] == tb:
            e["p_time"] = t["time"]["all"]["p_perm"]
            e["p_acc"] = t["time"]["accuracy"]["p_mcnemar"]

# ---- per-task payload for interactivity --------------------------------------
TASK_PAYLOAD = {}
for t in ORDER:
    row = {"goal": TASKS[t]["goal"], "difficulty": TASKS[t]["difficulty"], "arms": {}}
    for a in ARMS:
        r = HARV[a][t]
        row["arms"][a] = {
            "passed": r["passed"], "min": round(r["run_min"], 2), "turns": r["turns"],
            "ec": r.get("execute_code", r.get("execute_code_traj", 0)),
            "fa": r.get("first_action_s"),
            "fail": FAILS.get(a, {}).get(t, "") if not r["passed"] else "",
        }
    TASK_PAYLOAD[t] = row

DATA = {
    "order": ORDER, "arms": {a: SUM[a] for a in ARMS}, "defaultOn": DEFAULT_ON,
    "tasks": TASK_PAYLOAD, "ev": EV,
}

CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:40px 28px 110px}
h1{font-size:29px;line-height:1.16;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:21px;letter-spacing:-.01em;margin:54px 0 6px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:26px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:16.5px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
th.sortable{cursor:pointer}th.sortable:hover{color:var(--ink)}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .n{font-size:22px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted)}
.note{font-size:12.5px;color:var(--muted)}
ul{margin:8px 0;padding-left:20px}li{margin:4px 0}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #3b82f6;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.verdict{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 9px;border-radius:12px;margin-right:8px}
.v-conf{background:#0f8a5f1a;color:var(--green)}.v-deb{background:#c13a2e14;color:var(--red)}.v-part{background:#d977061a;color:#9a5a06}
.togglebar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.tg{display:inline-flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--line);border-radius:14px;padding:3px 10px;cursor:pointer;user-select:none;background:var(--surface)}
.tg input{margin:0}
.tg .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.matrix{display:grid;grid-template-columns:130px 1fr 1fr;gap:8px;margin:12px 0}
.mcell{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:var(--surface);cursor:pointer}
.mcell:hover{border-color:var(--dim)}
.mcell .big{font-size:19px;font-weight:700}
.mcell .s{font-size:11px;color:var(--muted)}
.mhead{align-self:center;font-size:12px;color:var(--muted);font-weight:600}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.06);padding:12px 18px;display:none;max-height:44vh;overflow:auto}
#detail.open{display:block}
#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px;line-height:1}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
.evrow td{font-size:12.5px}
.ci{color:var(--muted);font-size:11.5px}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
"""

# ---- static SVG helpers (python-rendered) ------------------------------------
def slope_chart(a, b, w=330, hgt=300, title=""):
    """Paired per-task slope chart: every task a line from arm B (left) to arm A (right)."""
    la, lb = SUM[a], SUM[b]
    pad_t, pad_b, pad_l, pad_r = 26, 30, 46, 46
    vals = [(HARV[b][t]["run_min"], HARV[a][t]["run_min"], t) for t in ORDER]
    vmax = max(max(v[0], v[1]) for v in vals) * 1.06
    def Y(v): return pad_t + (hgt - pad_t - pad_b) * (1 - v / vmax)
    x0, x1 = pad_l, w - pad_r
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit" role="img">']
    out.append(f'<text x="{w/2:.0f}" y="14" text-anchor="middle" font-size="11.5" font-weight="600" fill="#1b1f24">{H.escape(title)}</text>')
    for gy in range(0, int(vmax) + 1, 3):
        out.append(f'<line x1="{x0}" y1="{Y(gy):.1f}" x2="{x1}" y2="{Y(gy):.1f}" stroke="#f3f2ee"/>')
        out.append(f'<text x="{x0-5}" y="{Y(gy)+3:.1f}" text-anchor="end" font-size="9" fill="#8a929c">{gy}m</text>')
    for vb, va, t in vals:
        worse = va > vb + 1e-9
        col = "#c13a2e" if worse else "#0f8a5f"
        out.append(f'<line x1="{x0}" y1="{Y(vb):.1f}" x2="{x1}" y2="{Y(va):.1f}" stroke="{col}" stroke-width="1.6" opacity="0.75"><title>{t}: {lb["short"]} {vb:.1f}m &#8594; {la["short"]} {va:.1f}m</title></line>')
        out.append(f'<circle cx="{x0}" cy="{Y(vb):.1f}" r="2.6" fill="#5b6571"/>')
        out.append(f'<circle cx="{x1}" cy="{Y(va):.1f}" r="2.6" fill="{col}"/>')
    out.append(f'<text x="{x0}" y="{hgt-8}" text-anchor="middle" font-size="10.5" fill="#5b6571">{H.escape(lb["short"])}</text>')
    out.append(f'<text x="{x1}" y="{hgt-8}" text-anchor="middle" font-size="10.5" fill="#5b6571">{H.escape(la["short"])}</text>')
    out.append('</svg>')
    return "".join(out)

def ladder_chart():
    """First-action latency ladder + per-turn pace: the mechanism panel."""
    rows = [("exp1a-fixed-brave",), ("exp3c-analysis",), ("exp2b-fixed-brave",),
            ("exp4b-expert-fork",), ("exp4a-experiential-fork",)]
    w, rh, pad_l, pad_t = 660, 30, 190, 26
    hgt = pad_t + rh * len(rows) * 2 + 46
    fmax = 26.0; pmax = 8.0
    half = (w - pad_l - 30) / 2
    def X1(v): return pad_l + half * min(v, fmax) / fmax
    def X2(v): return pad_l + half + 26 + (half - 26) * min(v, pmax) / pmax
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit">']
    out.append(f'<text x="{pad_l}" y="14" font-size="11.5" font-weight="600" fill="#1b1f24">median seconds to FIRST browser action</text>')
    out.append(f'<text x="{pad_l+half+26}" y="14" font-size="11.5" font-weight="600" fill="#1b1f24">seconds of run per model turn</text>')
    y = pad_t
    for (a,) in rows:
        s = SUM[a]
        out.append(f'<text x="{pad_l-8}" y="{y+13}" text-anchor="end" font-size="11.5" fill="#1b1f24">{H.escape(s["label"])}</text>')
        fa = s["first_action_s"] or 0
        out.append(f'<rect x="{pad_l}" y="{y}" width="{X1(fa)-pad_l:.1f}" height="16" rx="3" fill="{s["color"]}" opacity="0.85"><title>{H.escape(s["label"])}: {fa}s to first action</title></rect>')
        out.append(f'<text x="{X1(fa)+5:.1f}" y="{y+12}" font-size="10.5" fill="#5b6571">{fa:.0f}s</text>')
        pt = s["per_turn_s"]
        out.append(f'<rect x="{pad_l+half+26}" y="{y}" width="{X2(pt)-(pad_l+half+26):.1f}" height="16" rx="3" fill="{s["color"]}" opacity="0.85"><title>{H.escape(s["label"])}: {pt}s per turn</title></rect>')
        out.append(f'<text x="{X2(pt)+5:.1f}" y="{y+12}" font-size="10.5" fill="#5b6571">{pt:.1f}s</text>')
        y += rh + 8
    out.append(f'<text x="{pad_l}" y="{y+18}" font-size="10.5" fill="#8a929c">Forks pay before they move, then pay again on every turn. Cold and mounted arms stay light.</text>')
    out.append('</svg>')
    return "".join(out)

def scatter_turns_time():
    """One point per post-fix arm: mean turns vs mean min/task. The fork story in one look."""
    arms = list(ARMS)
    w, hgt, pl, pt, pb, pr = 660, 330, 56, 18, 42, 150
    xmax = max(SUM[a]["turns"] for a in arms) * 1.12
    ymax = max(SUM[a]["mean_task"] for a in arms) * 1.14
    def X(v): return pl + (w - pl - pr) * v / xmax
    def Y(v): return hgt - pb - (hgt - pt - pb) * v / ymax
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit">']
    for gx in range(0, int(xmax) + 1, 15):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pt}" x2="{X(gx):.0f}" y2="{hgt-pb}" stroke="#f3f2ee"/><text x="{X(gx):.0f}" y="{hgt-pb+14}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}</text>')
    for gy in range(0, int(ymax) + 1):
        out.append(f'<line x1="{pl}" y1="{Y(gy):.0f}" x2="{w-pr}" y2="{Y(gy):.0f}" stroke="#f3f2ee"/><text x="{pl-6}" y="{Y(gy)+3:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy}m</text>')
    out.append(f'<text x="{(pl+w-pr)/2:.0f}" y="{hgt-8}" text-anchor="middle" font-size="11" fill="#5b6571">mean model turns per task</text>')
    out.append(f'<text x="14" y="{(pt+hgt-pb)/2:.0f}" font-size="11" fill="#5b6571" transform="rotate(-90 14 {(pt+hgt-pb)/2:.0f})" text-anchor="middle">mean minutes per task</text>')
    lab_used = []
    for a in arms:
        s = SUM[a]
        x, y = X(s["turns"]), Y(s["mean_task"])
        hollow = s["delivery"] == "raw"
        dash = s["delivery"] == "fork"
        fill = "#fbfbf9" if hollow else s["color"]
        extra = f' stroke-dasharray="3 2"' if dash else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{fill}" stroke="{s["color"]}" stroke-width="2"{extra}><title>{H.escape(s["label"])}: {s["turns"]} turns, {s["mean_task"]}m/task, {s["passed"]}/12</title></circle>')
        ly = y
        while any(abs(ly - u) < 13 for u in lab_used): ly -= 13
        lab_used.append(ly)
        out.append(f'<text x="{x+10:.1f}" y="{ly+4:.1f}" font-size="10.5" fill="{s["color"]}">{H.escape(s["short"])} · {s["passed"]}/12</text>')
    out.append('</svg>')
    return "".join(out)

# ---- HTML assembly ------------------------------------------------------------

def focus_table():
    rows = []
    for r in FOCUS:
        rows.append(
            f"<tr><td>{H.escape(r['label'])}</td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{r['flagged']}</td><td>{H.escape(r['top'])}</td>"
            f"<td class='num'>{r['raw_tool']:.2f} &rarr; {r['adj_tool']:.2f}</td>"
            f"<td class='num'>{r['med']:.3f} &rarr; {r['med_adj']:.3f}</td>"
            f"<td class='num'><b>{r['raw_total']:.1f} &rarr; {r['adj_total']:.1f}</b></td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>arm</th><th>browser calls</th><th>flagged &gt;1.5s</th>"
            "<th>top flagged tool</th><th>tool min (as-run &rarr; adj)</th><th>median s (as-run &rarr; adj)</th>"
            "<th>12-task total min (as-run &rarr; adj)</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

def ev_table(ids, note=""):
    rows = []
    for cid in ids:
        e = EV[cid]; t = e["time"]
        p = e.get("p_time"); ps = (" · p=" + (("%.4f" % p).rstrip("0").rstrip(".")) if p is not None else "")
        rows.append(
            f"<tr class='evrow'><td>{H.escape(e['label'])}</td>"
            f"<td class='num'>{e['pass_a']} vs {e['pass_b']}</td>"
            f"<td class='num'>{t['mean']:+.2f} <span class='ci'>[{t['lo']:+.2f}, {t['hi']:+.2f}]</span></td>"
            f"<td class='num'>{t['wl']}</td>"
            f"<td class='num'>{e['turns']['mean']:+.1f}</td>"
            f"<td class='ci'>{ps.lstrip(' ·')}</td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>comparison (A vs B)</th><th>accuracy</th>"
            "<th>&Delta; min/task <span style='text-transform:none'>[95% bootstrap CI]</span></th>"
            "<th>A faster&ndash;slower</th><th>&Delta; turns</th><th>exact p (footnote)</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
            + (f"<p class='note'>{note}</p>" if note else ""))

kpi = f"""
<div class="kpis">
<div class="kpi"><div class="n">18 arms · 0</div><div class="l">arms that ever passed dashdish-8 (the rubric-ambiguity task)</div></div>
<div class="kpi"><div class="n">12/12 · 2.2x</div><div class="l">tasks where OCIC beats CinC on action round-trip, reproduced in 3 CinC runs</div></div>
<div class="kpi"><div class="n">24.5 &asymp; 23.4m</div><div class="l">CinC under setup parity vs OCIC: whole-task dead heat (p=.44)</div></div>
<div class="kpi"><div class="n">+1.5 to +2.9 m/task</div><div class="l">context tax of forked sessions, replicated in 4 of 4 comparisons</div></div>
<div class="kpi"><div class="n">6&#8594;10&#8594;14&#8594;24s</div><div class="l">first-action latency ladder: cold &#8594; mounted &#8594; expert fork &#8594; experiential fork</div></div>
</div>"""

matrix_js_cells = json.dumps({
    "raw": {"experiential": "exp2a-fixed-brave", "expert": "exp2b-fixed-brave"},
    "analysis": {"experiential": "exp3d-experiential-analysis", "expert": "exp3c-analysis"},
    "fork": {"experiential": "exp4a-experiential-fork", "expert": "exp4b-expert-fork"},
})

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · phases 1-4</title>
<style>{CSS}</style></head><body><div class="wrap">

<div class="eyebrow">OCIC BENCHMARK · REAL WEBCLONES · PHASES 1&ndash;4 · POST-FIX · 2026-07-16</div>
<h1>A healthy harness beats every form of experience we tried: mounted, compressed, and forked into context</h1>
<p class="lede">Eighteen arms over the same 12 held-out tasks (dashdish + zilloft), sonnet at medium effort, fresh seeded
tab per rollout, deterministic + judged grading. Phase 1 fixed the harness; phases 2&ndash;4 handed the agent experience
three ways: raw material on disk, compressed analysis on disk, and a checkpointed session forked so the experience sits
in context. At n=12 we argue by showing every pair, effect sizes with bootstrap CIs, task-level win/loss records, and
replication across independent contrasts; exact permutation p-values are footnotes.</p>
{kpi}

<h2>0 &middot; The scorecard</h2>
<div class="card">
<p><span class="verdict v-part">H1 REVISED BY CONTROLS</span><strong>OCIC's real win is per-action latency and orchestration capability; under setup parity, whole-task time and accuracy are equivalent.</strong>
The per-action claim is robust: 0.12s vs 0.27-0.30s median round-trip, OCIC faster on 12/12 tasks in all three CinC runs.
The original whole-task gap was two parts artifact: a fresh control re-run of the June baseline scored 11/12 (was 8/12,
three judged flips, none the other way) and cut the time gap in half; a parity arm that scripts CinC's mandatory
tab-bootstrap preamble closed the rest (24.5 vs 23.4 min raw; 22.6 vs 23.2 excluding the preamble; p=.44). What remains
architectural: the official extension's session-scoped tab groups PROHIBIT orchestrator-prepared tabs (verified live),
so its agent must always self-bootstrap; OCIC accepts orchestrated setup.</p>
<p><span class="verdict v-deb">H2 NOT SUPPORTED</span><strong>Mounted priors do not move a healthy harness.</strong>
Cold is 11/12 at 1.95 min/task. Raw mounts: 9/12 and 11/12, &plusmn;0.5 min/task with mixed win/loss records. Compressed
analysis: 11/12 and 10/12, +0.05 min/task (6-6 record) for the expert version. Nothing separates from baseline.</p>
<p><span class="verdict v-deb">H3 REFUTED, WITH A MECHANISM</span><strong>Forked in-context experience is strictly worse here: it cannot be ignored, so it taxes every turn.</strong>
Both forks lose time on 11 or 12 of 12 tasks against cold (+1.96 and +2.76 min/task; CIs exclude zero by a wide margin)
with no accuracy gain (10/12, 8/12 vs 11/12). The mechanism is visible at three levels: forks start acting 2-4x later,
run fewer turns, and pay more seconds per turn.</p>
<p><span class="verdict v-part">H4 SOURCE MATTERS ONLY WHEN DELIVERY IS HEAVY</span><strong>Expert vs experiential: indistinguishable when compressed, decisive when forked.</strong>
As analysis docs the two sources tie (11 vs 10, one discordant task). As forks, the expert checkpoint (all-positive
study, max effort) beats the experiential one (carries 3 failed train segments): 10/12 vs 8/12, faster on 8-4 tasks,
and it flipped two of the experiential fork's three real failures. In-context delivery amplifies prior quality, both ways.</p>
</div>

<h2>1 &middot; The delivery matrix (click any cell)</h2>
<p>The experiment is a 3&times;2 grid: how experience is delivered &times; where it came from, all against the same cold
baseline. Pass count, mean minutes per task, and the one-time preparation cost.</p>
<div id="matrix" class="matrix"></div>
<p class="note">Amortization never arrives: at 12 tasks, no experience arm has repaid its preparation, and the fork arms
also pay a per-task context tax with no accuracy return. Cold reference: <b>11/12 · 1.95 m/task · 0 prep</b> (OCIC Brave) /
9/12 · 2.21 (OCIC Chrome) / CinC control 11/12 · 2.73 / CinC parity 9/12 · 2.04 (both parity fails are judge-phrasing
noise; the June CinC original, 8/12 · 3.50, did not reproduce and is retained only as history).</p>

<h2>2 &middot; Study 1: the harness (OCIC vs official CinC), with controls</h2>
<div class="card">
<p style="margin-top:0"><strong>Three CinC runs tell the story in layers.</strong> The June original (8/12, 42 min) does
not reproduce: an identical fresh control scored 11/12 in 32.8 min (three judged tasks flipped F&rarr;P, none P&rarr;F;
its 18-minute zilloft-9 churn was an episode, not a property). A second control adds setup parity: the official
topology forces the agent to create its own session-scoped tab group and navigate to the app inside the timed run, so
the parity arm scripts that preamble deterministically. Result: whole-task dead heat with OCIC.</p>
{ev_table(["s1chrome", "s1brave", "s1control", "s1parity", "s1pc"],
"Positive &Delta; = A slower. Rows 1-2 use the unrepresentative June baseline and OVERSTATE the gap; row 3 is the honest topology-default comparison; row 4 is the setup-parity comparison (dead heat); row 5 isolates the preamble-scripting effect itself.")}
<p><strong>What stays true across all three CinC runs:</strong> per-action round-trip medians of 0.26-0.30s vs OCIC's
0.12s (screenshots 0.34s vs 0.07s; find 2.4s vs 0.02s), OCIC faster on 12/12 tasks each time. A focus-adjustment
heuristic (calls &gt;1.5s replaced by the tool's clean median, applied symmetrically) moves CinC's mechanical time only
3.3&rarr;2.7 min and flags find-search calls, not input events: zero of 141 control clicks stalled, so background-tab
throttling does NOT explain the per-action gap. And an architectural finding from the failed persistent-tab design:
the official extension scopes tab control to a per-session tab group; a tab created by one session cannot be driven by
another (javascript_tool and get_page_text refuse; verified live, twice). Orchestrated setup is impossible for the
official system by design, which is exactly the capability OCIC's spawnable server adds.</p>
<h3>As-run vs focus-adjusted (the active-tab question, quantified)</h3>
<p class="note" style="margin-top:2px">During these runs the acted-on tab was not guaranteed to be the active/visible
tab, and background tabs are known to throttle synthesized input. Adjustment heuristic, applied identically to every
arm: any browser call with round-trip &gt;1.5s is treated as a possible visibility artifact and replaced by that tool's
own clean (&le;1.5s) median; the adjusted 12-task total subtracts the difference. This is deliberately generous: it
assumes EVERY slow call was a focus artifact.</p>
{focus_table()}
<p class="note">The adjustment moves no arm by more than 0.9 min and changes no ranking: the parity dead heat and the
per-action gap both stand. The flagged calls are dominated by find (element search, not input dispatch); input events
show no stall signature (0 of 141 control clicks &gt;1.5s), which is how genuine background-tab throttling would present.
Conclusion: tab visibility cannot account for the observed differences.</p>
<div class="callout"><strong>Judge sensitivity, exposed by the controls.</strong> The parity arm's two non-dashdish-8
fails are phrasing lotteries: zilloft-2's answer "147" is the same number the cold baseline PASSED with (phrasing
omitted "exactly"), and zilloft-10's "160" passed in one arm and failed in two others. The &plusmn;2-3 task noise floor
this implies applies to every single-run arm in this report.</div>
</div>

<h2>3 &middot; Study 2: mounted experience (raw and compressed)</h2>
<div class="card">
<p style="margin-top:0">Four arms mount experience on disk next to the task. None separates from cold: effect sizes are
within &plusmn;0.5 min/task with straddling CIs and near-even records. The agent barely opens the material (expert
analysis read in 7/12 rollouts, experiential in 3/12, raw mounts near zero on a healthy harness).</p>
{ev_table(["s2_2a", "s2_2b", "s2_3d", "s2_3c"])}
</div>

<h2>4 &middot; Study 3: forked experience, and the context tax</h2>
<div class="card">
<p style="margin-top:0"><strong>Every fork comparison, same direction.</strong> Against cold and against their own
mounted counterparts, both forks lose wall-clock on nearly every task. The effect replicates in four independent
contrasts; the accuracy column never compensates.</p>
{ev_table(["s3_4a", "s3_4b", "s3_4b3c", "s3_4b2b", "s3_4a3d", "s3_4a2a", "s3_4b4a"],
"The one positive: within forks, the expert checkpoint beats the experiential one on time (8-4) and accuracy (+2 tasks), the delivery-amplifies-quality result.")}
<h3>Every pair, shown</h3>
<div style="display:flex;flex-wrap:wrap;gap:10px">
{slope_chart("exp4b-expert-fork", "exp1a-fixed-brave", title="cold → expert fork (min/task)")}
{slope_chart("exp4a-experiential-fork", "exp1a-fixed-brave", title="cold → experiential fork")}
{slope_chart("exp4b-expert-fork", "exp3c-analysis", title="expert analysis → expert fork")}
</div>
<p class="note">Red lines rise (fork slower), green fall. No aggregation: each line is one task. The pattern needs no test.</p>
<h3>The mechanism</h3>
{ladder_chart()}
<h3>Turns down, time up</h3>
{scatter_turns_time()}
<p class="note">Hollow = raw mount, solid = analysis mount, dashed ring = fork. Forks sit upper-LEFT: fewer turns
(the knowledge does reduce search) at far higher minutes (context processed on every one of them). Neither fork
consulted its on-disk materials even once (0 reads; the mounted-analysis arm read its docs 13 times), so the effect is
purely in-context. First-turn cost alone: cold 6s, expert fork 14s, experiential fork 24s.</p>
</div>

<h2>5 &middot; Per-task explorer</h2>
<p>Toggle arms, click a row for the full per-arm breakdown of a task (verdicts, minutes, turns, failing answers).</p>
<div class="togglebar" id="togglebar"></div>
<div class="scroll"><table id="taskgrid"></table></div>

<h2>6 &middot; Arm census (sortable)</h2>
<div class="scroll"><table id="census"></table></div>
<p class="note">per-turn s = total run seconds / total turns. first-action = median seconds from run start to the first
browser tool call. reads = opens of ./experience or notes files during test rollouts. ec = execute_code calls (never
mentioned in any post-fix prompt except 3B's encouragement; violations impossible, usage free).</p>

<h2>7 &middot; Failure anatomy</h2>
<div class="card">
<ul>
<li><strong>dashdish-8, 0 of 16 arms ever.</strong> "First three categories of deliverable food": every arm answers
from the cuisine carousel; the rubric wants the curated collection rows. No harness, prior, or delivery mode touches it:
task-specification failure. Exhibits in the <a href="archive/benchmark_report_postfix_v1.html#dd8">archived deep dive</a>.</li>
<li><strong>The location-mirage pair (zilloft-5, zilloft-10).</strong> The app's location search barely filters; judged
answers that acknowledge the mirage pass, bare header counts fail. These two account for most non-dashdish-8 failures
across arms, including two of the experiential fork's three misses.</li>
<li><strong>zilloft-2 in both forks.</strong> Filter semantics ("exactly 3 bd" vs "3+ bd"): both forks skipped the
exact-match toggle that the expert material demonstrates, cold passed it. The expert fork's scored attempt ran clean and
post-reset (its two rate-limited attempts were quarantined, never scored, evidence on disk).</li>
<li><strong>The experiential fork's checkpoint carries failure.</strong> Its study session failed 3 of 6 train segments
(uncurated by design); its forks then under-performed the all-positive expert checkpoint by 2 tasks and 0.8 min/task.
Context is not ignorable: bad experience in-context is worse than no experience.</li>
</ul>
</div>

<h2>8 &middot; Methods &amp; integrity</h2>
<div class="card"><ul>
<li><strong>Pipeline.</strong> Fresh tab &rarr; clear &rarr; /config seed &rarr; clean /finish assert &rarr; detached
<span class="mono">claude -p</span> (sonnet, medium) &rarr; gate &rarr; byte-exact /finish + trajectory capture &rarr; tab closed &rarr;
REAL evaluator (jmespath + sonnet-judged rubric). Fork rollouts additionally restore the study workdir snapshot at the
study's own absolute path and run <span class="mono">--resume &lt;sid&gt; --fork-session</span>.</li>
<li><strong>Small-n stance.</strong> 12 paired tasks per arm. Primary evidence: paired effect sizes with 10k-resample
bootstrap CIs, task-level win/loss records, full-pair slope charts, and replication across independent contrasts.
Exact sign-flip permutation and McNemar p-values are retained as footnotes (they agree with the CIs everywhere).</li>
<li><strong>Fork accounting.</strong> Forked transcripts embed the study prefix; all fork metrics are sliced from the
rollout's own run-start timestamp. num_turns is fork-local. Study prep: experiential 37.0 min (its six train segments);
expert 17 min operator demos + 27.1 min max-effort study (the one effort deviation, study only).</li>
<li><strong>Controls (2026-07-16).</strong> The June CinC baseline was re-run twice under suspicion of drift: an
identical control (11/12, 32.8 min; three judged flips vs the original, none reversed) and a setup-parity arm whose
header scripts the mandatory tab-bootstrap preamble (9/12 with two judge-phrasing fails, 24.5 min; whole-task dead heat
with OCIC, p=.44). Setup-prefix accounting: time to the first completed navigate, reported separately (CinC arms ~10s per
rollout; OCIC ~0 by construction). Focus-adjustment heuristic: browser calls &gt;1.5s replaced by that tool's clean median,
both systems; it shifts CinC by 0.66 min total and flags only find-search calls, ruling out background-tab throttling.
A persistent-tab parity design failed twice with "tab not in this session's group": official tab control is
session-scoped, so orchestrator-prepared tabs are impossible by design.</li>
<li><strong>Rate limits.</strong> One session-limit event during the expert fork's final rollout: two attempts
quarantined (never scored, evidence files kept), third attempt ran post-reset and is the scored one. One judge-side
throttle during the fork smoke, absorbed by a 15-min retry.</li>
<li><strong>External interruptions.</strong> Three background-chain kills during phase 4 (cause external to the runner);
recovery via completed-artifact skip logic, final leg run in a detached session. No scored rollout spans an interruption.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py &amp;&amp; python3 analysis/stats.py &amp;&amp;
python3 analysis/build_report_v2.py</span> · archived editions: <a href="archive/benchmark_report_pre_fix.html">pre-fix</a> ·
<a href="archive/benchmark_report_postfix_v1.html">post-fix v1</a>.</li>
</ul></div>

<div id="detail"><span class="x" onclick="closeDetail()">&times;</span><div id="detailbody"></div></div>

<script>
const DATA = {json.dumps(DATA)};
const CELLS = {matrix_js_cells};
const fmt = (x, d=1) => x == null ? "·" : x.toFixed(d);

// ---- matrix ----
function renderMatrix() {{
  const m = document.getElementById("matrix");
  let h = '<div class="mhead"></div><div class="mhead">experiential (self)</div><div class="mhead">expert (operator)</div>';
  const names = {{raw: "raw mount", analysis: "analysis mount", fork: "forked session"}};
  for (const dlv of ["raw", "analysis", "fork"]) {{
    h += `<div class="mhead">${{names[dlv]}}</div>`;
    for (const fam of ["experiential", "expert"]) {{
      const a = CELLS[dlv][fam], s = DATA.arms[a];
      h += `<div class="mcell" onclick="showArm('${{a}}')" style="border-top:3px solid ${{s.color}}">
        <div class="big">${{s.passed}}/12</div>
        <div class="s">${{s.mean_task.toFixed(2)}} m/task · prep ${{s.prep.toFixed(0)}}m</div>
        <div class="s">${{s.label}}</div></div>`;
    }}
  }}
  m.innerHTML = h;
}}

// ---- toggles + task grid ----
let ON = new Set(DATA.defaultOn);
function renderToggles() {{
  const bar = document.getElementById("togglebar");
  bar.innerHTML = Object.keys(DATA.arms).map(a => {{
    const s = DATA.arms[a];
    return `<label class="tg"><input type="checkbox" ${{ON.has(a) ? "checked" : ""}} onchange="tgArm('${{a}}',this.checked)">
      <span class="sw" style="background:${{s.color}}"></span>${{s.short}}</label>`;
  }}).join("");
}}
function tgArm(a, on) {{ on ? ON.add(a) : ON.delete(a); renderGrid(); }}
function renderGrid() {{
  const arms = Object.keys(DATA.arms).filter(a => ON.has(a));
  let h = "<thead><tr><th>task</th><th>difficulty</th>" +
    arms.map(a => `<th style="color:${{DATA.arms[a].color}}">${{DATA.arms[a].short}}</th>`).join("") + "</tr></thead><tbody>";
  for (const t of DATA.order) {{
    const row = DATA.tasks[t];
    h += `<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td><td>${{row.difficulty}}</td>`;
    for (const a of arms) {{
      const c = row.arms[a];
      h += `<td class="num" title="${{c.turns}} turns">${{c.passed ? "" : "<span class='badge b-fail'>F</span> "}}${{fmt(c.min)}}m</td>`;
    }}
    h += "</tr>";
  }}
  h += "</tbody>";
  document.getElementById("taskgrid").innerHTML = h;
}}

// ---- census (sortable) ----
let sortKey = "passed", sortDir = -1;
const CENSUS_COLS = [["label","arm",0],["passed","pass",1],["run_min","12-run min",1],["mean_task","m/task",1],
  ["turns","turns",1],["per_turn_s","per-turn s",1],["med_action_s","action s",1],["first_action_s","first-action s",1],
  ["ec","ec",1],["exp_reads","reads",1],["prep","prep m",1]];
function renderCensus() {{
  const arms = Object.values(DATA.arms).slice().sort((x,y) => {{
    const a = x[sortKey], b = y[sortKey];
    if (a == null) return 1; if (b == null) return -1;
    return (a < b ? -1 : a > b ? 1 : 0) * sortDir;
  }});
  let h = "<thead><tr>" + CENSUS_COLS.map(([k, lbl]) =>
    `<th class="sortable" onclick="sortBy('${{k}}')">${{lbl}}${{sortKey===k ? (sortDir<0?" ▾":" ▴") : ""}}</th>`).join("") + "</tr></thead><tbody>";
  for (const s of arms) {{
    h += `<tr><td><span class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{s.color}};margin-right:6px"></span>${{s.label}}</td>
      <td class="num">${{s.passed}}/12</td><td class="num">${{s.run_min.toFixed(1)}}</td><td class="num">${{s.mean_task.toFixed(2)}}</td>
      <td class="num">${{s.turns.toFixed(1)}}</td><td class="num">${{s.per_turn_s.toFixed(2)}}</td><td class="num">${{s.med_action_s.toFixed(3)}}</td>
      <td class="num">${{s.first_action_s==null?"·":s.first_action_s.toFixed(0)}}</td><td class="num">${{s.ec}}</td><td class="num">${{s.exp_reads}}</td><td class="num">${{s.prep.toFixed(0)}}</td></tr>`;
  }}
  document.getElementById("census").innerHTML = h + "</tbody>";
}}
function sortBy(k) {{ if (sortKey === k) sortDir *= -1; else {{ sortKey = k; sortDir = -1; }} renderCensus(); }}

// ---- detail panel ----
function openDetail(html) {{
  document.getElementById("detailbody").innerHTML = html;
  document.getElementById("detail").classList.add("open");
}}
function closeDetail() {{ document.getElementById("detail").classList.remove("open"); }}
function showTask(t) {{
  const row = DATA.tasks[t];
  let h = `<h3 style="margin:2px 0 2px">${{t}} <span class="note">(${{row.difficulty}})</span></h3>
    <p class="note" style="margin:2px 0 8px">${{row.goal}}</p><div class="scroll"><table><thead>
    <tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>ec</th><th>first-action</th><th>failing answer</th></tr></thead><tbody>`;
  for (const a of Object.keys(DATA.arms)) {{
    const c = row.arms[a], s = DATA.arms[a];
    h += `<tr><td>${{s.label}}</td><td>${{c.passed ? '<span class="badge b-pass">PASS</span>' : '<span class="badge b-fail">FAIL</span>'}}</td>
      <td class="num">${{fmt(c.min)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.ec}}</td>
      <td class="num">${{c.fa==null?"·":c.fa+"s"}}</td><td class="note">${{c.fail || ""}}</td></tr>`;
  }}
  openDetail(h + "</tbody></table></div>");
}}
function showArm(a) {{
  const s = DATA.arms[a];
  let h = `<h3 style="margin:2px 0 6px"><span class="sw" style="display:inline-block;width:11px;height:11px;background:${{s.color}};border-radius:3px;margin-right:7px"></span>${{s.label}}
    <span class="note">· ${{s.passed}}/12 · ${{s.run_min.toFixed(1)}} min total · prep ${{s.prep.toFixed(0)}} min</span></h3>
    <div class="scroll"><table><thead><tr><th>task</th><th>verdict</th><th>min</th><th>turns</th><th>failing answer</th></tr></thead><tbody>`;
  for (const t of DATA.order) {{
    const c = DATA.tasks[t].arms[a];
    h += `<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td>
      <td>${{c.passed ? '<span class="badge b-pass">PASS</span>' : '<span class="badge b-fail">FAIL</span>'}}</td>
      <td class="num">${{fmt(c.min)}}</td><td class="num">${{c.turns}}</td><td class="note">${{c.fail || ""}}</td></tr>`;
  }}
  openDetail(h + "</tbody></table></div>");
}}

renderMatrix(); renderToggles(); renderGrid(); renderCensus();
</script>
</div></body></html>"""

out = os.path.join(BENCH, "benchmark_report.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

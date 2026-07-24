#!/usr/bin/env python3
"""benchmark_capstone.html: the full post-fix story, cold baselines through
phase 5. Per-arm descriptions, accuracy + performance comparisons, and
hypothesis-verdict graphics. Self-contained, interactive (vanilla JS SVG)."""
import json, os, statistics, html as HH

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(BENCH, "analysis", "capstone.json")))

# --- canonical arm renaming to the writeup's 6-phase scheme (1a-6b) ---
# Rename-only: upstream ids stay put. We relabel EVERY occurrence of an arm short
# across the whole data blob (dict keys, list elements, and any {"short": ...}
# field, at any depth) so nested structures like turns.scale.fits and *.tasks[].sv
# stay consistent with the charts. Recipe swap preserved: 5A (per-site) -> 5b,
# 5B (single) -> 5a.
RENAME = {"CinC": "1a", "OCIC-Ch": "1b", "OCIC-Br": "1c", "2A": "2a", "2B": "2b",
          "3D": "3a", "3C": "3b", "4A": "4a", "4B": "4b", "5B": "5a", "5A": "5b",
          "5C": "6a", "5D": "6b"}
NEWORDER = ["1a", "1b", "1c", "2a", "2b", "3a", "3b", "4a", "4b", "5a", "5b", "6a", "6b"]
_OLD = set(RENAME)  # domain and range are disjoint, so remap is idempotent-safe
# The scalar-space scatter read a stale theme palette; snap rankcompare to the
# canonical per-leg palette (keyed by OLD short, before the recursive rename).
_canon = D["dist_byleg"]["color"]
for _a in D["rankcompare"]["arms"]:
    _a["color"] = _canon.get(_a["short"], _a.get("color"))
def _remap(o):
    if isinstance(o, dict):
        return {RENAME.get(k, k): (RENAME[v] if k == "short" and v in _OLD else _remap(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [RENAME[x] if isinstance(x, str) and x in _OLD else _remap(x) for x in o]
    return o
D = _remap(D)
# display-order lists -> scheme order (left-to-right reads 1a..6b)
D["dist_byleg"]["order"] = NEWORDER[:]
_rank = {s: i for i, s in enumerate(NEWORDER)}
D["arms"].sort(key=lambda a: _rank.get(a["short"], 99))

ARMS = D["arms"]; ORDER = D["order"]; DIFF = D["diff"]
BY = {a["id"]: a for a in ARMS}
COLD = BY["exp1a-fixed-brave"]

# --- deterministic accuracy correction (see accuracy_regrade.py) ---
# capstone.json's accuracy came straight from REAL's llm_boolean judge, which
# disagreed with itself on identical answers (verified by reading every run's
# evaluation.json). Only 3 of 12 held-out tasks vary across arms at all; the
# other 9 pass/fail identically everywhere and dashdish-8 fails everywhere
# regardless of grading, so this only touches those 3 tasks' pass/fail + the
# rollups that are computed from them (per-arm .passed, dist_byleg.acc, the
# per-theme accuracy column).
_ACC = json.load(open(os.path.join(BENCH, "analysis", "accuracy_corrected.json")))
for _a in ARMS:
    _sh = _a["short"]
    _a["passed"] = _ACC["passed"][_sh]
    for _c in _a["per_task"]:
        if _c["t"] in _ACC["swing"]:
            _c["passed"] = _ACC["matrix"][_sh][_c["t"]]
            _c["fail"] = "" if _c["passed"] else _ACC["answer_text"][_c["t"]][_sh]
D["dist_byleg"]["acc"] = dict(_ACC["passed"])
for _t in D["themes"]:
    _members = [a for a in _t["arms"] if a in _ACC["passed"]]
    if _members:
        _t["acc"] = round(sum(_ACC["passed"][a] for a in _members) / len(_members), 1)

# within-arm "slow but passed": a passed task whose run time is an upper outlier
# RELATIVE TO THIS ARM's own task times. Robust modified z-score (MAD-based,
# handles the right-skew): flag if 0.6745*(t - median)/MAD > 1.5. This is per
# arm, not per task: it says "this task underperformed for THIS arm."
for _a in ARMS:
    _ts = [c["min"] for c in _a["per_task"] if c["passed"]]
    if len(_ts) >= 4:
        _med = statistics.median(_ts)
        _mad = statistics.median([abs(m - _med) for m in _ts]) or 0.01
        for c in _a["per_task"]:
            c["slow"] = bool(c["passed"] and 0.6745 * (c["min"] - _med) / _mad > 1.5)
    else:
        for c in _a["per_task"]:
            c["slow"] = False

PHASES = {
    "cold": ("Cold baselines", "No prior experience. What the agent does knowing only the task."),
    "p2":   ("Phase 2 · mounted raw", "Raw traces / recordings placed on disk at ./experience/."),
    "p3":   ("Phase 3 · mounted analysis", "Compressed per-site analysis docs on disk."),
    "p4":   ("Phase 4 · forked session", "A full study session checkpointed and forked into context."),
    "p5":   ("Phase 5 · recipe & atomic warm-up", "Leakage-free recipe in the prompt, and a single-task warm-up forked."),
}
PHASE_ORDER = ["cold", "p2", "p3", "p4", "p5"]

CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f;--amber:#b45309}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 28px 120px}
h1{font-size:30px;line-height:1.14;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:22px;margin:56px 0 8px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:16.5px;margin:26px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:17px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
th.sortable{cursor:pointer}th.sortable:hover{color:var(--ink)}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.kpi .n{font-size:22px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:3px}
.note{font-size:12.5px;color:var(--muted)}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #2563eb;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.verdict{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 9px;border-radius:12px;margin-right:8px}
.v-yes{background:#0f8a5f1a;color:var(--green)}.v-no{background:#c13a2e14;color:var(--red)}.v-part{background:#b453091a;color:var(--amber)}
.armrow{display:flex;gap:12px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--line2,var(--soft))}
.sw{width:12px;height:12px;border-radius:3px;flex:0 0 12px;margin-top:5px}
.armrow .nm{font-weight:600;font-size:13.5px}
.armrow .meta{font-size:11.5px;color:var(--dim);font-family:"SF Mono",monospace}
.armrow .d{font-size:12.5px;color:var(--muted)}
.phasehdr{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);margin:16px 0 4px}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.07);padding:12px 18px;display:none;max-height:46vh;overflow:auto}
#detail.open{display:block}#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px}
.ctl{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin:2px 0 12px;font-size:13px}
.ctl label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;user-select:none}
.ctl .sep{width:1px;height:16px;background:var(--line)}
.plegend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 2px;font-size:11.5px;color:var(--muted)}
.plegend .k{display:inline-flex;align-items:center;gap:6px}
.plegend .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.plegend .sw.hatch{background:repeating-linear-gradient(45deg,#fbfbf9 0 2px,var(--c) 2px 4.2px);border:1px solid var(--line)}
svg text{font-family:inherit}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:212px;overflow-y:auto;background:var(--surface);border-right:1px solid var(--line);padding:14px 12px 40px;z-index:60;font-size:12px;transition:transform .2s}
.sidebar .brand{font-weight:700;font-size:12.5px;letter-spacing:-.01em;color:var(--ink)}
.sidebar .brandsub{font-size:10px;color:var(--dim);margin-bottom:6px}
.sidebar h4{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);margin:15px 0 5px;font-weight:700}
.sidebar a.navlink{display:block;color:var(--muted);text-decoration:none;padding:2px 5px;border-radius:4px;line-height:1.3}
.sidebar a.navlink:hover{background:var(--soft);color:var(--ink)}
.sidebar a.navlink .n{color:var(--dim);font-family:"SF Mono",monospace;font-size:10px;margin-right:5px}
.legrow{display:flex;align-items:baseline;gap:6px;padding:2px 5px;font-size:11px;color:var(--muted);line-height:1.3}
.legrow .sw{width:11px;height:11px;border-radius:3px;flex:0 0 11px;position:relative;top:1px}
.legrow b{color:var(--ink);font-family:"SF Mono",monospace;font-size:10px;flex:0 0 46px}
body{padding-left:234px;transition:padding-left .2s}
.navtoggle{position:fixed;top:10px;left:220px;z-index:70;background:var(--surface);border:1px solid var(--line);border-radius:6px;width:26px;height:26px;line-height:23px;text-align:center;cursor:pointer;font-size:13px;color:var(--muted);transition:left .2s;user-select:none}
body.navhidden .sidebar{transform:translateX(-100%)}
body.navhidden{padding-left:0}
body.navhidden .navtoggle{left:8px}
.charttitle{font-size:13.5px;font-weight:700;color:var(--ink);letter-spacing:-.01em;margin:14px 0 2px}
.charttitle .sub{font-weight:400;color:var(--dim);font-size:11.5px;letter-spacing:0}
"""

def arm_registry_html():
    out = []
    for ph in PHASE_ORDER:
        title, sub = PHASES[ph]
        out.append(f'<div class="phasehdr">{HH.escape(title)} &middot; <span style="text-transform:none;font-weight:400;letter-spacing:0">{HH.escape(sub)}</span></div>')
        for a in [x for x in ARMS if x["phase"] == ph]:
            prep = f"{a['prep_full']:.0f}m prep" if a.get('prep_full') else "0 prep"
            out.append(
                f'<div class="armrow"><span class="sw" style="background:{a["color"]}"></span>'
                f'<div><div class="nm">{HH.escape(a["label"])} '
                f'<span class="meta">&middot; {a["passed"]}/12 &middot; {a["total"]:.1f}m &middot; {prep} &middot; {a["ktok"]:.0f}k tok/turn</span></div>'
                f'<div class="d">{HH.escape(a["desc"])}</div></div></div>')
    return "".join(out)

# ---- headline KPIs ----
best_time = min(ARMS, key=lambda a: a["total"])
kpis = f"""<div class="kpis">
<div class="kpi"><div class="n">13 arms &middot; 60 tasks-eq</div><div class="l">post-fix configurations over the same 12 held-out tasks</div></div>
<div class="kpi"><div class="n">8/12 &middot; 23.4m</div><div class="l">the cold OCIC baseline every method has to beat</div></div>
<div class="kpi"><div class="n">5D &middot; 20.9m</div><div class="l">only arm faster than cold (warm-up + recipe), on the hard tasks</div></div>
<div class="kpi"><div class="n">8 to 11 of 12</div><div class="l">accuracy is narrow but not flat; 7 of 39 borderline grader verdicts were overturned against ground truth (&sect;2)</div></div>
<div class="kpi"><div class="n">480k &rarr; 92k</div><div class="l">shrinking the fork's context (P4&rarr;P5) flipped it from worst to a tie</div></div>
</div>"""

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark &middot; post-fix capstone</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK &middot; POST-FIX CAPSTONE &middot; COLD BASELINES THROUGH PHASE 5 &middot; 2026-07-17</div>
<h1>Every way we tried to beat a cold browser agent, and the one that finally did</h1>
<p class="lede">Thirteen post-fix configurations on the same 12 held-out REAL webclone tasks (dashdish, zilloft), sonnet at
medium effort, fresh seeded tab per rollout, deterministic + judged grading. This report walks each arm in order: the
three cold baselines, then four ways of delivering prior experience. It asks two questions of each: is it more
accurate, and is it faster. The answer is a story about delivery, not knowledge.</p>
{kpis}

<h2>1 &middot; The arms, in order</h2>
<div class="card">{arm_registry_html()}</div>
<p class="note">Prep = one-time cost to produce the experience (recording, generation, study, or recipe authoring),
excluded from the per-task run times below and reported separately. tok/turn = context carried per model turn, the
lever that turned out to matter most.</p>

<h2>2 &middot; Accuracy</h2>
<div class="card">
<div class="charttitle">Accuracy by arm <span class='sub'>tasks passed of 12</span></div>
<div id="c_acc"></div>
<p class="note">Tasks passed of 12, deterministically re-graded. <b>Two grading problems, corrected separately.</b>
First, dashdish-8 is a broken rubric: all 13 arms give the cuisine-carousel answer, and the rubric's ground-truth answer
is the curated collection rows, which no arm produces. The single judged pass (5D) was re-evaluated to check consistency
and came back <b>3 pass / 2 fail over 5 runs</b>, confirming the LLM judge is a coin flip on the identical answer, so we
fall back to the rubric ground truth and mark dashdish-8 fail for all 13 (the original judged verdict is preserved on
disk). Second, three tasks (zilloft-2, zilloft-5, zilloft-10) ask for an exact listing count, and the same judge disagreed
with itself there too: reading every run's actual reported number against the rubric's stated correct count overturned
<b>7 of the 39 arm&times;task verdicts on those three tasks alone, all of them false positives</b> (the grader passed a
wrong count, never failed a right one). Every arm's score above is the corrected count. Accuracy still cannot separate
the methods cleanly, the corrected range is a narrow 8 to 11 of 12, but it is no longer flat, and it is no longer
trustworthy to read off the raw judged verdicts.</p>
<div class="charttitle">Pass, slow, or fail <span class='sub'>every arm against every task</span></div>
<div id="c_accgrid"></div>
<p class="note"><b style="color:#0f8a5f">&#9679;</b> pass &nbsp; <b style="color:#ca8a04">&#9679;</b> passed but
<b>slow for that arm</b> (a within-arm upper outlier: its time is a robust outlier against that arm's own task times,
so it flags "this task underperformed here", independent of how long the task is elsewhere) &nbsp; <b style="color:#c13a2e">F</b> fail.
The failures concentrate in four tasks: dashdish-8 (broken rubric, universal) and the location-mirage counts zilloft-2 /
zilloft-5 / zilloft-10 (grader-inconsistent; corrected against the rubric's ground-truth count, &sect;2 above). The yellow
marks vary by arm and are the more interesting signal: 4B's slow spot is zilloft-5 (not the usual marathon), 3D's is
dashdish-10, and <b>5A has none</b> (uniformly efficient). Cold does not solve everything solvable (it ties the floor at
8/12), so accuracy separates the methods a little, but within-arm slowness is still the sharper signal.</p>
<div class="charttitle">Accuracy per leg <span class='sub'>tasks passed of 12; one value per leg, toggle to focus</span></div>
<div class="ctl" id="ov_acc_ctl"></div>
<div id="c_dist_acc"></div>
<p class="note">Accuracy is a single value per leg (a pass count of 12), not a per-task spread, so instead of a curve each
selected leg is a dot on the score axis (ties stacked). The ceiling is <b>11/12</b> (4 of 13 legs: 2b, 3b, 5b, 6b) and the
floor is <b>8/12</b>, tied four ways by all three cold baselines and 4a. Toggle legs to isolate. The spread is narrow
enough (8 to 11) that accuracy separates the methods only weakly; the whole story is in performance.</p>
</div>

<h2>3 &middot; Performance</h2>
<div class="card">
<div class="ctl">
  <label><input type="checkbox" id="t_task" checked onchange="renderPerf()"> Task time (12 runs)</label>
  <label><input type="checkbox" id="t_prep" checked onchange="renderPerf()"> Preparation steps</label>
  <span class="sep"></span>
  <label><input type="radio" name="lay" value="stacked" checked onchange="renderPerf()"> Stacked (total)</label>
  <label><input type="radio" name="lay" value="aligned" onchange="renderPerf()"> Aligned (compare)</label>
</div>
<div class="charttitle">Run time per arm <span class='sub'>task time and preparation, toggleable</span></div>
<div id="c_perf"></div>
<div id="perf_legend" class="plegend"></div>
<p class="note"><b>Stacked</b> lays every segment end-to-end so the bar length is the true total cost (prep, then the
12 task runs). <b>Aligned</b> gives each segment its own bar from a shared left edge, so you compare magnitudes directly.
Preparation is now broken into its real steps with a consistent color per step type: producing the source material
(experiential runs, expert recordings) is a shared, reused cost shown for full provenance. The recipe arms carry the
longest prep chain because a recipe is distilled from BOTH raw sources plus one shared authoring session, yet their task
time is near cold. The forks invert it: cheap-ish prep, heavy task time. <b>Preparation is hatched, task time is solid</b>, so the two never blend.</p>
<div class="charttitle">Time saved or lost versus cold <span class='sub'>minutes per arm</span></div>
<div id="c_deltas"></div>
<p class="note">Mean minutes saved vs cold per task (positive = faster than cold). Ordered by phase. The recipe and
atomic-warmup arms hover at zero; the full forks lose 2-3 minutes/task; 5D alone is clearly negative (faster). Every
arm's win, where it has one, comes from the hard tasks.</p>
<div class="charttitle">Latency distribution, per leg <span class='sub'>density of each leg's 12 task times; toggle legs to overlay</span></div>
<div class="ctl" id="ov_lat_ctl"></div>
<div id="c_dist_lat"></div>
<p class="note">Each curve is one leg's distribution over its 12 task times; toggle any legs to overlay them (the default
shows a contrasting few, with a rug of the raw 12 points under each). The shapes diverge: cold is a moderate hump around
one to two minutes; the <b>fork (4A) shifts far right and spreads wide</b>; the <b>warm-up (5D) is tight and pulled
left</b>, the most concentrated; the <b>analysis mount (3D) carries a right tail</b> from one hard task (dashdish-10). Pooled
across all 156 runs the median is 1.9 min, but the per-leg curves are where the methods actually separate.</p>
<div class="charttitle">Consistency, per leg <span class='sub'>mean vs standard deviation of latency; distance from the line is the signal</span></div>
<div id="c_reliability"></div>
<p class="note"><b>Standard deviation on its own is misleading, because it tracks the mean</b> (correlation <b>+0.87</b>
across arms): slow arms simply vary more. The dashed line is what "typical" spread looks like (SD = <b>0.63</b> times the
mean, the median coefficient of variation). What matters is <b>distance from that line</b>, not height. Three readings
fall out, and they revise the mean-only story. <b>The forks sit right on the line:</b> their large SD is entirely a
consequence of their large mean (CV ~0.63, same as cold), so they are <i>uniformly</i> ~2x slow, predictable, not chaotic.
On reliability the fork is not the villain. <b>The recipe and warm-up sit below the line</b> (5A at CV 0.49, 5D at 0.54):
they tighten the relative spread, so run times cluster predictably, a reliability gain stacked on top of the speed gain.
<b>3D sits above it</b> (CV <b>0.90</b>): the analysis mount is fast on most tasks but still has a real tail, a
dashdish-10 run runs 7.7 minutes against a ~1-3 minute norm elsewhere, so its risk is concentrated in a minority of
tasks rather than spread evenly. And this is one underlying leg property: an arm's latency CV and its turn CV correlate
<b>+0.93</b>, a leg that is erratic in time is erratic in path length too.</p>
</div>

<h2>4 &middot; The mechanism: context weight owns latency</h2>
<div class="card">
<p style="margin-top:0">One number explains the entire performance ranking: how many tokens each arm's agent carries
per turn. Cold and mounted arms carry ~54-61k (the task + page). The forks carry the whole checkpoint on every turn.</p>
<div class="charttitle">Context carried per turn <span class='sub'>thousands of tokens, by arm</span></div>
<div id="c_ktok"></div>
<p class="note">Context carried per turn. The phase-4 forks (480k, 251k) are 5-9x everything else, not because they
reason more, but because the entire study transcript is re-processed on every call. Phase 5's atomic warm-up (5C/5D)
cut this to ~92k by keeping only one task of history.</p>
<div class="charttitle">The turn-latency law <span class='sub'>seconds per turn versus tokens carried</span></div>
<div id="c_lawscatter"></div>
<p class="note"><b>The turn-latency law.</b> Each dot is an arm: context carried per turn vs the resulting per-task time
penalty against cold. The line is tight (heavier context, slower). This is why the phase-4 forks lost and why shrinking
the checkpoint (P4&rarr;P5) recovered almost all of it: the loss was delivery weight, never the knowledge itself.</p>
<h3 style="margin-top:26px">Once context is divided out: thinking is flat, turns is the only thing that moves</h3>
<p>Per-turn latency is context, and that is just transformer physics. So we divided context out and asked what else
varies between experiments. There are only two candidates: how much the model <b>generates</b> per turn (its deliberation)
and how many <b>turns</b> it takes. Measured on the SDK's real per-task turn count, the answer is clean and a little
deflating: thinking per turn barely moves at all, and the only behavioral variable is the step count.</p>
<div class="charttitle">Thinking per turn, by experiment <span class='sub'>output tokens per turn: nearly flat across every arm</span></div>
<div id="c_thinkbar"></div>
<p class="note"><b>Thinking per turn is not a lever.</b> Every arm generates ~130 to 170 output tokens per turn (a short
reasoning span plus the tool call), a spread of about &plusmn;7% around cold's ~135. Reading experience (mounts, recipe)
leaves it at cold; the forks nudge slightly higher (148, 168), a mild side-effect of having a whole session to reconcile;
the warm-up is cold-like (128, 136). Whatever prior experience does, it does not change how much the model deliberates per
step. Since total time varies 2.5x while thinking-per-turn holds flat, the time differences cannot be thinking, they are
context, confirmed from the other direction.</p>
<p class="note"><b>What does move is the turn count.</b> A recipe or warm-up cuts steps below cold; raw or analysed docs
on disk push it up (the agent spends turns reading). But turn count is <b>orthogonal to total time</b> (correlation
<b>0.00</b>): taking fewer turns does not make you faster, because per-turn cost varies more than step count does, and
per-turn cost is context. That makes turns a separate axis from latency, a <i>precision</i> axis rather than a speed one,
so we give it its own treatment next in <b>Section 5</b>. The one-liner for this section: thinking is flat, context is
the cost, and turns is a behavior worth measuring on its own.</p>
</div>

<h2>5 &middot; Turns taken: the precision axis</h2>
<div class="card">
<p style="margin-top:0">Latency is one cost of a browser agent; <b>imprecision is another</b>. Every turn is an action on a
live, stateful page, and a wrong action, a filter mis-set, a wrong listing opened, a form half-submitted, has downstream
consequences the agent then has to notice and unwind. The most direct path to the answer is also the one with the
smallest blast radius. Turn count is our measurable proxy for that path length, and, as Section 4 established, it is
<b>independent of latency</b> (correlation 0.00 with time), so a method can make the agent more precise without making it
faster, and the two must be judged separately.</p>

<div class="callout" style="border-left-color:#b45309">
<h4 style="margin:0 0 6px;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;color:#5b6571">How we count turns</h4>
<p style="margin:0;font-size:13px">A <b>turn</b> is one model step: a single round-trip in which the agent observes the
page, reasons, and emits an action (a tool call). We count turns with the Agent SDK's authoritative per-task
<span class="mono">num_turns</span>, <b>not</b> the raw trajectory length. This matters because the forked warm-up arms
(5C, 5D) resume a prior session, so the warm-up's transcript rides in the trajectory and inflates the raw count by
<b>~7 to 8x</b> (versus a steady ~1.5x for every other arm). The same contamination hits every trajectory-derived action
count (tool calls, browser calls, steps), so <span class="mono">num_turns</span> is the only path-length metric that is
clean for these arms. An earlier version of this report used the raw count and drew the wrong conclusion; this section is
built on the corrected metric.</p>
</div>

<div class="charttitle">Turns versus cold, by method <span class='sub'>fewer = more direct path (green); more = extra steps (red)</span></div>
<div id="c_turndelta"></div>
<p class="note"><b>Carrying knowledge in-context shortens the path; making the agent retrieve it from disk lengthens it.</b>
The warm-up (5D) runs the most direct route, <b>26% fewer turns</b> than cold; recipe and even the fork run ~14 to 19%
fewer, because the knowledge is already in the window and the agent wastes fewer exploratory moves. The disk mounts go the
other way, up to <b>+24%</b>: agentic retrieval is itself navigation, and every file the agent opens is another step that
can go wrong. Note the fork here: it takes among the <i>fewest</i> turns (most direct) yet is the slowest arm overall,
the clearest proof that precision and speed are different axes.</p>

<div class="charttitle">Turn savings versus task length <span class='sub'>turns saved vs cold against naive baseline turns; toggle legs</span></div>
<div class="ctl" id="ts_ctl"></div>
<div id="c_turnscale"></div>
<p class="note"><b>And the path-shortening grows with the task.</b> For the warm-up (5D) the turns saved correlate
<b>+0.86</b> with how many turns the task naively takes; on the longest task in the suite it removes <b>~28 turns</b>, more
than a third of the naive path. Recipe scales the same way (+0.77). The disk mount does the opposite (it adds steps, and
tends to add more on longer tasks). So the precision benefit concentrates exactly where the risk is highest: on long,
multi-step tasks with the most opportunities for a consequential wrong move. The efficient methods do not just finish in
fewer steps, they widen that lead as the task gets longer.</p>
<div class="charttitle">Turn-count distribution, per leg <span class='sub'>density of each leg's 12 task turn-counts; toggle legs to overlay</span></div>
<div class="ctl" id="ov_turns_ctl"></div>
<div id="c_dist_turns"></div>
<p class="note">Each curve is one leg's path-length distribution across its 12 tasks; toggle legs to compare. The
<b>warm-up (5D) sits left and narrow</b> (short, consistent paths), the <b>raw mount (2B) sits right</b> (longer paths),
and cold falls in between; the fork is left-of-cold but with a wider spread. Pooled median is 28.5 turns.</p>
</div>

<h2>6 &middot; Two rankings that disagree: turns vs latency</h2>
<div class="card">
<p style="margin-top:0">We now have two efficiency metrics that measure different things: <b>turns</b> (path directness, Section 5)
and <b>latency</b> (wall-clock time, Section 3). If they ranked the arms the same way, one would be redundant. They do
not. The rank correlation between them is only <b>+0.30</b> (Spearman), so knowing an arm is turn-efficient tells you
almost nothing about whether it is fast. This section puts the two orderings side by side and reads the arms that move.</p>

<div class="charttitle">The reshuffle <span class='sub'>vertical height is proportional to the actual value (turns left, minutes right); crossings = disagreement</span></div>
<div id="c_slope"></div>
<p class="note"><b>Red lines fall, green lines rise.</b> The story lives in the crossings. <b>4A, the experiential fork,
is the whole point</b>: it takes the 2nd-most-direct path of any arm (rank 2 on turns) yet finishes dead last on latency
(rank 13), a plunge of eleven places, because every one of its few, direct turns drags ~365k of context. Efficiency of
path and efficiency of time are not the same thing, and the fork is the proof. Mirroring it, <b>2A, the raw disk mount,
rises seven places</b> (rank 9 on turns to rank 2 on latency): it wanders down a long path, but each of those turns is
cheap, so the wandering is nearly free. Only <b>5D sits at rank 1 on both</b>, the one arm that is both the most direct
and the fastest.</p>

<div class="charttitle">The same arms in scalar space <span class='sub'>turns vs minutes; the bottom-left corner is the goal</span></div>
<div id="c_rankscatter"></div>
<p class="note">Ranks flatten magnitude, so here are the raw values, and the arms fall into <b>three groups that the delivery
mechanism draws for you</b>. <b>Prompt-embedded</b> (green: recipe and warm-up) clusters in the bottom-left prize corner,
few turns and fast, because the knowledge is in the window and costs almost nothing to carry. <b>Cold and on-disk
retrieval</b> (blue: the cold legs plus the raw and analysis mounts) sits just to the right, still fast but on a longer
path, cheap per turn, yet the agent spends extra steps because it has no in-window guidance or must go read files.
<b>In-context forks</b> (red) break away to the top: the context tax strands them there regardless of turn count, 4A
lands in the worst corner despite a near-best path. The asymmetry underneath it all: turns span just <b>1.7x</b> (24 to 40)
while latency spans <b>2.7x</b> (21 to 57 minutes), so being a few turns more direct buys a little, but being context-heavy
costs enormously. Judge a method on turns and latency separately; a good position on one axis is no guarantee on the
other.</p>
</div>

<h2>7 &middot; Hypotheses, tested</h2>
<div class="card">
<p><span class="verdict v-yes">H1 SUPPORTED</span><strong>OCIC is at least as good as the official extension.</strong>
Cold OCIC-Brave, official CinC (setup-parity), and OCIC-Chrome all tie at 8/12 once the grader's inconsistent verdicts
are corrected against ground truth (an earlier apparent OCIC-Brave accuracy edge was two flaky judge passes on wrong
answers, &sect;2). OCIC leads on per-action latency (0.12s vs 0.27s median round-trip); whole-task time is a tie under
setup parity. The big early gap was an unrepresentative old CinC run plus a setup-parity artifact, both corrected.</p>
<p><span class="verdict v-no">H2 REFUTED</span><strong>Mounted prior experience improves a healthy harness.</strong>
Raw mounts 9/12 and 11/12; analysis mounts 10/12 and 11/12; every mean within &plusmn;1 min/task of cold, records
near-even. The agent barely opens the files, and the healthy harness leaves nothing for them to fix.</p>
<p><span class="verdict v-no">H3 REFUTED (with a mechanism)</span><strong>Forking the experience into context helps.</strong>
The full forks are the worst arms in the benchmark: 8/12 and 10/12, +2-3 min/task, because each turn re-reads a
250-490k-token prefix. In-context knowledge cut search (fewer turns) but paid an ~8x reading tax on delivery.</p>
<p><span class="verdict v-part">H4 SUPPORTED (the corollary)</span><strong>The fork's loss is delivery weight, not the
knowledge.</strong> Phase 5's atomic warm-up shrank the checkpoint 480k&rarr;92k and the fork flipped from worst arm to a
tie with cold (11/12, +0.13 min/task). Exactly what the turn-latency law predicts.</p>
<p><span class="verdict v-part">H5 SUPPORTED (narrowly)</span><strong>A cheap, non-distracting recipe can beat cold.</strong>
The recipe alone lands 10/12 and 11/12, at or above cold's 8/12, but its fixed reading cost cancels most of the time
benefit on this easy-heavy suite.
Combined with the atomic warm-up (5D), it is the first arm faster than cold: 20.9 vs 23.4m, faster on 7/12 tasks, the
gains concentrated in the hard tasks, the difficulty effect paying off.</p>
<div class="callout"><strong>The one-line conclusion.</strong> Knowledge never hurt and rarely helped; <em>delivery</em>
decided everything. On disk it is ignored (free, useless); forked whole it is a per-turn tax (expensive, harmful);
distilled to a recipe plus one task of warm-up it is finally net-positive (5D). And it only shows up on hard tasks , 
this suite is at ceiling, so the honest headline is a modest time win, not an accuracy breakthrough.</div>
</div>

<h2>8 &middot; Difficulty is where the wins live</h2>
<div class="card">
<div class="charttitle">Time benefit versus cold, by task difficulty <span class='sub'>easy, medium, hard tiers</span></div>
<div id="c_diffbars"></div>
<p class="note">Mean time benefit vs cold, split by task difficulty, for the arms that ever help. Every positive bar is
in the hard tier; easy tasks show flat-to-negative (the fixed cost of any delivery exceeds the tiny task). This is the
consistent thread across all phases: prior experience pays in proportion to task difficulty, and this suite has too few
hard tasks for it to dominate the totals.</p>
<h3 style="margin-top:26px">The longer the naive task, the more the winning method pays</h3>
<p>Every task carries a baseline latency: what it costs to hand a browser agent the task cold, which grows with the
number of turns the task naively takes. The question that matters for continual learning is whether its benefit grows
with that baseline. It does, and cleanly.</p>
<div class="charttitle">Time saved versus baseline task length <span class='sub'>seconds saved vs cold against naive turn count; toggle legs</span></div>
<div class="ctl" id="ls_ctl"></div>
<div id="c_lengthscale"></div>
<p class="note"><b>The prompt-embedded method (5D, warm-up + recipe) saves more the longer the task is</b> (correlation
<b>+0.73</b> between seconds saved and baseline turn count; 5A recipe alone +0.66). On the shortest tasks it is roughly
break-even, the fixed cost of carrying the recipe eats the gain, but on the longest task in the suite (zilloft-9, ~69
naive turns) 5D returns <b>~106 seconds</b>. The fork runs the other way (correlation <b>&minus;0.42</b>): the longer the
task, the deeper it sinks, because its per-turn context tax compounds over every additional turn. So the two families
diverge with length, prompt-embedded expertise pays off increasingly, in-context history costs increasingly. This suite
is only medium-length; the trend lines say the gap widens on anything longer.</p>
<p class="note" style="margin-top:10px"><b>Accuracy does not scale much, and the dataset is the reason.</b> Every arm lands at
8 to 11 of 12; cold sits at the floor (8/12, tied across all three baseline arms) and most later-phase arms sit a little
above it, up to a 11/12 ceiling reached by four arms. The two things that keep any arm off a perfect score are a broken
rubric (dashdish-8, universal) and, before correction, an inconsistent LLM judge on three count-based tasks (&sect;2).
The suite sits near its accuracy ceiling either way, so it can measure <i>latency</i> gains from continual learning far
more cleanly than <i>accuracy</i> gains. Whether these methods lift success on genuinely hard tasks is a question this
data leaves open; it would need a harder, un-capped suite to answer.</p>
</div>

<h2>9 &middot; How each leg scales with difficulty</h2>
<div class="card">
<p style="margin-top:0"><b>Difficulty is defined per task as an equal blend of its classification (easy/medium/hard)
and its denoised baseline time</b> (the mean run time across the three phase-1 cold legs, averaged to cancel
single-run noise), scaled 0&ndash;10. Then each leg's per-task time is measured against that same 3-leg baseline, and we
ask how that performance moves as difficulty rises.</p>
<div class="charttitle">Difficulty sensitivity <span class='sub'>does each leg hold up as tasks get harder?</span></div>
<div id="c_sens"></div>
<p class="note"><b>Difficulty sensitivity</b> = the slope of (minutes vs baseline) against difficulty, per leg. Negative
(green) = the leg holds up or improves as tasks get harder; positive (red) = it degrades. The picture is unambiguous:
the <b>forks are difficulty-fragile</b> (4A +0.44 min per difficulty point, Spearman +0.58; 4B +0.12/+0.44) because
their per-turn context tax compounds with the extra turns hard tasks demand. Every <b>recipe / warm-up-recipe</b> leg is
flat-to-negative (5D &minus;0.09, 5A/5B ~&minus;0.08): difficulty-robust. Mounts are largely flat overall.</p>
<div class="ctl" id="sc_ctl"></div>
<div class="charttitle">Performance versus difficulty <span class='sub'>per task and leg, with trends</span></div>
<div id="c_diffscatter2"></div>
<p class="note">Each dot is one task at its difficulty (x) against that leg's minutes saved or lost vs the denoised
baseline (y, below zero = faster than baseline). Dashed lines are per-leg trends; toggle legs above. The fork trends
tilt UP with difficulty (they bleed time on the hard tasks); the recipe and 5D trends stay flat or tilt gently down.
The answer to the question: <b>a leg's delivery mechanism decides its difficulty behavior</b>. Carrying knowledge
in-context is a tax that grows with difficulty, while a recipe on the page is a fixed near-zero cost that lets its small
hard-task savings survive.</p>
</div>

<h3>Long is not the same as hard: two axes underneath "difficulty"</h3>
<div class="card">
<p style="margin-top:0">The blend above leans on time, and time hides a fork in the road. A task can eat minutes because it
is <b>long</b> (many routine steps) or because it is <b>cognitively hard</b> (the agent stalls, backtracks, and
sometimes fails outright). Those are different problems, and across the suite they turn out to be nearly independent:
duration and failure rate correlate just <b>&minus;0.24</b>. Worse for the composite, the time-blended difficulty score
tracks duration (<b>+0.67</b>) while staying almost blind to failure (<b>+0.06</b>): it measures <i>how long</i>, not
<i>how hard</i>.</p>
<div class="charttitle">Task landscape <span class='sub'>duration versus failure rate</span></div>
<div id="c_landscape"></div>
<p class="note"><b>x = denoised cold duration; y = failure rate across all 22 arms.</b> Dot color is the hand
classification (easy / medium / hard). The two axes pull the four hard tasks apart: <b>zilloft-9 is the marathon</b>
(longest task, 118 turns, yet fails only 5%: long, not hard), while <b>zilloft-10 is the trap</b> (middling length but
fails 32%: the genuinely hard one). Failure is not even confined to the hard label, zilloft-2 and zilloft-5 are
medium-classified and fail ~30%. And dashdish-8 sits alone at 100% failure with near-zero duration: not hard, just a
broken, judge-random rubric. The time-blend crowns the marathon as "hardest" (score 10.0) and rates the real trap only
6.5. If we want a difficulty axis that predicts <i>failure</i>, it has to be built from failures, not from the clock.</p>
</div>

<h2>10 &middot; Itemized: every task against its phase-1 baseline</h2>
<div class="card">
<p style="margin-top:0">The granular view underneath every average above. One row per task, sorted by baseline duration.
The baseline is the <b>mean of the three phase-1 cold legs</b> for that task (the gray diamond in absolute mode, the
darker 0 line otherwise); each colored dot is one other leg on that same task. Toggle legs to keep it readable, and pick
one of three views: minutes vs baseline, <b>percent faster or slower than baseline</b>, or absolute minutes.</p>
<div class="ctl" id="it_mode"></div>
<div class="ctl" id="it_ctl"></div>
<div class="charttitle">Every task against its phase-1 baseline <span class='sub'>per leg, granular</span></div>
<div id="c_itemized"></div>
<p class="note">The <b>percent view is the higher-signal one</b>: it normalizes each gap by the task's own length, so a
minute saved counts for little on a long task and a lot on a short one. It exposes what the minute view flattens: the
fork legs are <i>relatively</i> catastrophic on short tasks (4A runs +556% on zilloft-10, +368% on dashdish-1), points
that ride off the right edge with their true value labeled, while on the long tasks that same fork looks mild. The
recipe and warm-up legs sit within a tight band around the baseline everywhere. Hover any mark for the exact minutes,
the percent, and the times-faster/slower factor. The dashed vertical line for each leg is its average across all twelve
tasks, with the value labeled underneath.</p>
</div>

<h2>11 &middot; Thematic patterns: how the knowledge is delivered</h2>
<div class="card">
<p style="margin-top:0">Set aside the phase numbers and group the arms by their <b>delivery mechanism</b> instead: where the
prior knowledge physically lives when the agent runs. Six themes fall out, and they behave as families.</p>
<div class="scroll"><table id="themetab"></table></div>
<p class="note" style="margin-top:12px">Three patterns unravel once you group this way. <b>One: context weight is the whole story
for time</b> (correlation between tokens-per-turn and time-vs-cold is <b>+0.91</b>; against seconds-per-turn, also <b>+0.91</b>).
The two disk-mount themes and the recipe theme keep tokens-per-turn near cold (~54&ndash;61k) and land near cold time;
the forked-session theme balloons to ~365k and pays <b>+27 minutes</b>. <b>Two: neither turns nor thinking is a lever.</b>
Turn count sits in a narrow band (25 to 40 across every theme) and correlates <b>0.00</b> with time; per-turn thinking is
flat too (~130 to 170 output tokens). The warm-up takes the <i>fewest</i> turns (25) and the disk mounts the most (37),
yet both land near cold, because what decides time is not how many turns or how hard each thinks, it is how much context
each turn drags. <b>Three: accuracy is theme-invariant, and cold is the outlier, not the ceiling.</b> Corrected against
ground truth, cold sits lowest at 8.0/12 and every other theme sits at 9.0&ndash;10.5, a tight band with no separation
between them; the delivery mechanism changes what the run costs, not what it can solve. (An earlier reading of this
chart had cold artificially tied for the top on the strength of two flaky judge verdicts, &sect;2; corrected, the honest
story is that <i>any</i> prior knowledge, regardless of delivery, edges out none at all, but recipe and warm-up do not
distinctly outperform the disk-mount or fork themes on accuracy the way they do on time.)</p>
<div class="charttitle">Where the time goes <span class='sub'>turns versus per-turn cost, by theme</span></div>
<div id="c_theme"></div>
<p class="note">Each dot is one arm placed by how it spends its time: turns (x) against real seconds per turn (y). Color is
the theme. The faint curves are lines of constant per-task time (turns times seconds-per-turn, labeled in per-task
minutes), with the cold baseline curve drawn heavier. The vertical axis is what decides the winner: the forks sit near
the top (every turn crushed by history) and are stranded on a high-time curve; the warm-up sits just above and to the
left of cold, fewer turns but each a touch heavier from its cached prefix, netting a hair below cold's curve; the disk
mounts drift right, more turns but light ones, landing right on cold. Nobody wins by taking the fewest or the cheapest
turns; the winner is whoever keeps per-turn context lowest. The channel you deliver through, disk or prompt or context,
decides the cost far more than the content you deliver.</p>
</div>

<h2>12 &middot; Per-arm &amp; per-task explorer</h2>
<p>Click any arm row for its 12-task breakdown; click a task for the cross-arm view.</p>
<div class="scroll"><table id="census"></table></div>

<h2>13 &middot; Methods &amp; integrity</h2>
<div class="card"><ul>
<li><strong>Pipeline.</strong> Fresh tab &rarr; clear &rarr; /config seed &rarr; clean /finish assert &rarr; detached
<span class="mono">claude -p</span> (sonnet, medium) &rarr; gate &rarr; byte-exact /finish + trajectory &rarr; close &rarr; REAL
evaluator (jmespath deterministic + sonnet-judged rubric). Forks add a workdir-snapshot restore + <span class="mono">--resume --fork-session</span>.</li>
<li><strong>Leakage discipline (phase 5).</strong> Recipes authored by an ISOLATED Fable-5 agent seeing only the
train-derived material; audited against test-set identifiers before use; never edited by the orchestrating session.</li>
<li><strong>Known grading noise + the dashdish-8 consistency decision.</strong> dashdish-8 is judge-nondeterministic:
5D's carousel answer, identical to what all 13 arms give, re-evaluated 3 pass / 2 fail over 5 runs. Because the rubric's
ground-truth answer is the collection rows (which no arm produced) and the judge verdict on the shared answer is a coin
flip, we mark dashdish-8 fail for all 13 arms for consistency (original judged verdicts preserved on disk under
evaluation_original_judge.json). zilloft-5/10 show the same judge sensitivity (mirage-aware phrasing passes, bare counts
fail). The &plusmn;2-3 task noise floor applies to every single-run arm.</li>
<li><strong>Metrics.</strong> tok/turn from per-rollout usage (cache reads + writes + fresh input). first-action =
median seconds to the first browser call. All per-task times are run-only, prep excluded. Full statistical treatment
(paired permutation, bootstrap CIs, win/loss) is in the archived deep-dive and main reports.</li>
<li><strong>Recipe prep attribution (caveat).</strong> All recipe variants were authored in ONE isolated Fable-5
session (~8.1 min compute; longer wall clock because it slept on a scheduled wakeup mid-run). The transcript splits into
a study/analysis phase (~4.9 min, reading BOTH sources and working out the app mechanics) and a writing phase (~3.2 min).
<b>Per-site (5A) and single (5B) recipes are shown with equal prep on purpose:</b> the dominant cost is the shared
cross-source analysis, which is incurred whether the output is two site recipes or one combined, so their totals are
legitimately near-identical (this is the answer to why they benchmarked the same). The writing phase did touch zilloft
more than dashdish and the combined least, but write-op count is a weak proxy for authoring effort, and the difference is
marginal, so we do not split the writing per variant. Upstream source-material steps (experiential runs, expert
recordings) are shown for full provenance but are a shared, reused cost, not re-incurred per arm. No rollouts were
re-run; only the prep accounting changed.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py &amp;&amp; python3 analysis/build_capstone.py</span>.
Companion reports: <a href="benchmark_report.html">main (studies 1-3)</a> &middot;
<a href="benchmark_deep_dive.html">deep dive (fork forensics, difficulty)</a>.</li>
</ul></div>

<div id="detail"><span class="x" onclick="document.getElementById('detail').classList.remove('open')">&times;</span><div id="detailbody"></div></div>

<script>
const D = {json.dumps(D)};
const A = D.arms, ORDER = D.order, DIFF = D.diff;
const BY = {{}}; A.forEach(a=>BY[a.id]=a);
const S='http://www.w3.org/2000/svg';
function sv(w,h){{const s=document.createElementNS(S,'svg');s.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);s.setAttribute('width','100%');s.style.maxWidth=w+'px';return s}}
function E(n,at,tx){{const e=document.createElementNS(S,n);for(const k in at)e.setAttribute(k,at[k]);if(tx!=null)e.textContent=tx;return e}}
function tip(e,t){{e.appendChild(E('title',{{}},t));return e}}
const COLD=BY['exp1a-fixed-brave'];

function accChart(){{
  const w=1060,h=270,pl=40,pb=60,pt=20;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vmax=12;const Y=v=>h-pb-(h-pt-pb)*v/vmax;const s=sv(w,h);
  for(let g=0;g<=12;g+=3){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(COLD.passed),x2:w-10,y2:Y(COLD.passed),stroke:'#c9c7c1','stroke-dasharray':'6 4','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-12,y:Y(COLD.passed)-4,'text-anchor':'end','font-size':10,fill:'#8a929c'}},`cold ${{COLD.passed}}/12`));
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),y=Y(a.passed);
    s.appendChild(tip(E('rect',{{x,y,width:bw,height:Y(0)-y,rx:3,fill:a.color}}),`${{a.label}}: ${{a.passed}}/12`));
    s.appendChild(E('text',{{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':11,'font-weight':700,fill:a.color}},a.passed));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_acc').appendChild(s);
}}
function accGrid(){{
  let h='<div class="scroll"><table><thead><tr><th>task</th><th>diff</th>'+A.map(a=>`<th style="color:${{a.color}}" title="${{a.label}}">${{a.short}}</th>`).join('')+'</tr></thead><tbody>';
  ORDER.forEach(t=>{{h+=`<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td><td>${{DIFF[t]}}</td>`+
    A.map(a=>{{const c=a.per_task.find(x=>x.t===t);
      const dot = c.passed ? (c.slow
        ? `<span style="color:#ca8a04" title="passed but slow for ${{a.short}} (${{c.min}}m)">●</span>`
        : `<span style="color:#0f8a5f" title="passed (${{c.min}}m)">●</span>`)
        : '<span class="badge b-fail">F</span>';
      return `<td style="text-align:center">${{dot}}</td>`}}).join('')+'</tr>';}});
  document.getElementById('c_accgrid').innerHTML=h+'</tbody></table></div>';
}}
const SM=D.step_meta;
function renderPerf(){{
  const showTask=document.getElementById('t_task').checked;
  const showPrep=document.getElementById('t_prep').checked;
  const layout=document.querySelector('input[name=lay]:checked').value;
  // legend (only the step types present, plus task)
  const usedSteps=[...new Set(A.flatMap(a=>a.prep_steps.map(s=>s.k)))];
  let leg='';
  if(showPrep) usedSteps.forEach(k=>{{leg+=`<span class="k"><span class="sw hatch" style="--c:${{SM[k].color}}"></span>${{SM[k].label}}</span>`}});
  if(showTask) leg+=`<span class="k"><span class="sw" style="background:#5b6571"></span>task time (SOLID, arm color)</span>`;
  document.getElementById('perf_legend').innerHTML=leg;
  // build per-arm segment lists (in draw order)
  const seg=a=>{{
    let segs=[];
    if(showPrep) a.prep_steps.forEach(st=>segs.push({{v:st.m,c:SM[st.k].color,lab:SM[st.k].label,k:st.k,prep:true}}));
    if(showTask) segs.push({{v:a.total,c:a.color,lab:'task time',prep:false}});
    return segs;
  }};
  const alignedMax=Math.max(...A.flatMap(a=>seg(a).map(s=>s.v)),1);
  const totalMax=Math.max(...A.map(a=>seg(a).reduce((p,s)=>p+s.v,0)),1);
  const w=1060,pl=150,pr=64;
  const rh=layout==='stacked'?30:(6+ (Math.max(...A.map(a=>seg(a).length),1))*8 +8);
  const hgt=20+rh*A.length+30;
  const xmax=(layout==='stacked'?totalMax:alignedMax)*1.03;
  const X=v=>pl+(w-pl-pr)*v/xmax;const s=sv(w,hgt);
  const defs=E('defs',{{}});usedSteps.forEach(k=>{{const pat=E('pattern',{{id:'hx-'+k,width:6,height:6,patternTransform:'rotate(45)',patternUnits:'userSpaceOnUse'}});pat.appendChild(E('rect',{{width:6,height:6,fill:'#fbfbf9'}}));pat.appendChild(E('line',{{x1:0,y1:0,x2:0,y2:6,stroke:SM[k].color,'stroke-width':3}}));defs.appendChild(pat);}});s.appendChild(defs);
  const fillOf=sg=>sg.prep?('url(#hx-'+sg.k+')'):sg.c;
  const strokeOf=sg=>sg.prep?SM[sg.k].color:'none';
  for(let g=0;g<=xmax;g+=15){{s.appendChild(E('line',{{x1:X(g),y1:14,x2:X(g),y2:hgt-24,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:hgt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'))}}
  // cold task-time reference (only meaningful when task shown, stacked)
  if(showTask&&layout==='stacked'&&!showPrep){{s.appendChild(E('line',{{x1:X(COLD.total),y1:14,x2:X(COLD.total),y2:hgt-24,stroke:'#0d9488','stroke-dasharray':'5 3'}}));s.appendChild(E('text',{{x:X(COLD.total),y:12,'text-anchor':'middle','font-size':9,fill:'#0d9488'}},'cold 23.4m'))}}
  A.forEach((a,i)=>{{const y0=18+i*rh;const segs=seg(a);
    s.appendChild(E('text',{{x:pl-8,y:y0+(layout==='stacked'?13:11),'text-anchor':'end','font-size':11.5,fill:'#1b1f24'}},a.label));
    if(layout==='stacked'){{
      let x=X(0);let tot=0;
      segs.forEach((sg,si)=>{{const wpx=X(sg.v)-pl;
        s.appendChild(tip(E('rect',{{x,y:y0,width:Math.max(1.5,wpx-(si<segs.length-1?2:0)),height:17,rx:2.5,fill:fillOf(sg),stroke:strokeOf(sg),'stroke-width':sg.prep?0.8:0}}),`${{a.label}} · ${{sg.lab}}: ${{sg.v}}m`));
        x+=wpx;tot+=sg.v;}});
      if(segs.length) s.appendChild(E('text',{{x:x+5,y:y0+13,'font-size':10.5,fill:'#5b6571'}},`${{tot.toFixed(0)}}m`));
    }} else {{ // aligned: each segment its own left-aligned mini-bar
      let yy=y0;
      segs.forEach(sg=>{{
        s.appendChild(tip(E('rect',{{x:X(0),y:yy,width:Math.max(1.5,X(sg.v)-pl),height:6,rx:1.5,fill:fillOf(sg),stroke:strokeOf(sg),'stroke-width':sg.prep?0.6:0}}),`${{a.label}} · ${{sg.lab}}: ${{sg.v}}m`));
        yy+=8;}});
    }}
  }});
  const host=document.getElementById('c_perf');host.innerHTML='';host.appendChild(s);
}}
function deltaChart(){{
  const w=1060,h=300,pl=40,pb=60;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vals=A.map(a=>a.mean_delta);const vmax=Math.max(...vals.map(Math.abs),0.5)*1.15;
  const Y=v=>34+(h-94)*(vmax-v)/(2*vmax);const s=sv(w,h);
  for(let g=-Math.ceil(vmax);g<=Math.ceil(vmax);g++){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g))}}
  s.appendChild(E('text',{{x:pl,y:16,'font-size':11,fill:'#5b6571'}},'slower than cold ▲ / ▼ faster than cold  (min per task)'));
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),v=a.mean_delta,y0=Y(0),y1=Y(v);
    s.appendChild(tip(E('rect',{{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:3,fill:v<=0?'#0f8a5f':'#c13a2e',opacity:.85}}),`${{a.label}}: ${{v>0?'+':''}}${{v}}m/task, faster on ${{a.faster_vs_cold}}/12`));
    s.appendChild(E('text',{{x:x+bw/2,y:v<=0?y1-4:y1+12,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'}},(v>0?'+':'')+v));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_deltas').appendChild(s);
}}
function ktokChart(){{
  const w=1060,h=280,pl=44,pb=60;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vmax=Math.max(...A.map(a=>a.ktok))*1.1;const Y=v=>h-pb-(h-30-pb)*v/vmax;const s=sv(w,h);
  for(let g=0;g<=vmax;g+=100){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'k'))}}
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),y=Y(a.ktok);
    s.appendChild(tip(E('rect',{{x,y,width:bw,height:Y(0)-y,rx:3,fill:a.color}}),`${{a.label}}: ${{a.ktok}}k tokens/turn`));
    s.appendChild(E('text',{{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},a.ktok+'k'));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_ktok').appendChild(s);
}}
function lawScatter(){{
  const w=1060,h=330,pl=56,pb=44,pr=30,pt=20;
  const xmax=Math.max(...A.map(a=>a.ktok))*1.08,ymin=Math.min(...A.map(a=>a.mean_delta))-0.2,ymax=Math.max(...A.map(a=>a.mean_delta))*1.15;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=100){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'k'))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}}));
  for(let g=Math.ceil(ymin);g<=ymax;g++){{s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'m'))}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'context carried per turn (k tokens)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'time penalty vs cold (min/task)'));
  const xs=A.map(a=>a.ktok),ys=A.map(a=>a.mean_delta);
  const mx=xs.reduce((p,c)=>p+c)/xs.length,my=ys.reduce((p,c)=>p+c)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((p,c)=>p+c)/xs.map(x=>(x-mx)**2).reduce((p,c)=>p+c),a0=my-b*mx;
  s.appendChild(E('line',{{x1:X(40),y1:Y(a0+b*40),x2:X(xmax*.96),y2:Y(a0+b*xmax*.96),stroke:'#5b6571','stroke-width':2,'stroke-dasharray':'7 5'}}));
  A.forEach(a=>{{const x=X(a.ktok),y=Y(a.mean_delta);
    s.appendChild(tip(E('circle',{{cx:x,cy:y,r:6,fill:a.color}}),`${{a.label}}: ${{a.ktok}}k/turn, ${{a.mean_delta>0?'+':''}}${{a.mean_delta}}m/task`));
    s.appendChild(E('text',{{x:x+9,y:y+3,'font-size':10,fill:a.color}},a.short));
  }});
  document.getElementById('c_lawscatter').appendChild(s);
}}

const D_LAND=D.landscape;
const DIFF_LEGS=A.filter(a=>!['exp1a-fixed-chrome','exp1b-cinc-parity'].includes(a.id)); // drop redundant cold legs
let SCON=new Set(['exp1a-fixed-brave','exp4a-experiential-fork','exp4b-expert-fork','exp5d-warmup-recipe','exp3c-analysis']);
function sensBar(){{
  const rows=DIFF_LEGS.slice().sort((x,y)=>x.diff_slope-y.diff_slope);
  const w=1060,rh=26,pl=150;const hgt=20+rh*rows.length+26;
  const smax=Math.max(...rows.map(a=>Math.abs(a.diff_slope)),0.1)*1.15;
  const X=v=>pl+((w-pl-90)/2)*(1+v/smax);const s=sv(w,hgt);
  s.appendChild(E('line',{{x1:X(0),y1:14,x2:X(0),y2:hgt-16,stroke:'#c9c7c1','stroke-width':2}}));
  s.appendChild(E('text',{{x:X(-smax*.6),y:12,'text-anchor':'middle','font-size':10,fill:'#0f8a5f'}},'← robust (improves w/ difficulty)'));
  s.appendChild(E('text',{{x:X(smax*.6),y:12,'text-anchor':'middle','font-size':10,fill:'#c13a2e'}},'degrades w/ difficulty →'));
  rows.forEach((a,i)=>{{const y=18+i*rh;const v=a.diff_slope;const x0=X(0),x1=X(v);
    s.appendChild(E('text',{{x:pl-8,y:y+13,'text-anchor':'end','font-size':11.5,fill:'#1b1f24'}},a.label));
    s.appendChild(tip(E('rect',{{x:Math.min(x0,x1),y,width:Math.max(2,Math.abs(x1-x0)),height:17,rx:2.5,fill:v<=0?'#0f8a5f':'#c13a2e',opacity:.85}}),`${{a.label}}: slope ${{v>0?'+':''}}${{v}} min/difficulty-pt, Spearman ${{a.diff_spear>0?'+':''}}${{a.diff_spear}}`));
    s.appendChild(E('text',{{x:x1+(v>=0?5:-5),y:y+13,'text-anchor':v>=0?'start':'end','font-size':10,fill:'#5b6571'}},`${{v>0?'+':''}}${{v}}`));
  }});
  const h=document.getElementById('c_sens');h.innerHTML='';h.appendChild(s);
}}
function diffScatterCtl(){{
  const bar=document.getElementById('sc_ctl');bar.innerHTML='';
  DIFF_LEGS.forEach(a=>{{const l=document.createElement('label');l.innerHTML=`<input type="checkbox" ${{SCON.has(a.id)?'checked':''}}><span class="sw" style="background:${{a.color}}"></span>${{a.short}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?SCON.add(a.id):SCON.delete(a.id);diffScatter2();}};bar.appendChild(l);}});
}}
function diffScatter2(){{
  const legs=DIFF_LEGS.filter(a=>SCON.has(a.id));
  const w=1060,h=360,pl=56,pb=44,pr=30,pt=22;
  const xs=A[0].perf_pts.map(p=>p.x);const xmax=Math.max(...xs)*1.04;
  const ally=legs.flatMap(a=>a.perf_pts.map(p=>p.y));
  const ymin=Math.min(-0.5,...ally),ymax=Math.max(0.5,...ally)*1.08;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=2){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}}));
  for(let g=Math.ceil(ymin);g<=ymax;g+=2){{s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'m'))}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'task difficulty (0-10: classification + denoised baseline time)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'minutes vs baseline (below 0 = faster)'));
  legs.forEach(a=>{{
    a.perf_pts.forEach(p=>s.appendChild(tip(E('circle',{{cx:X(p.x),cy:Y(p.y),r:3.4,fill:a.color,opacity:.62}}),`${{a.label}} · ${{p.t}} (${{p.cls}}, diff ${{p.x}}): ${{p.y>0?'+':''}}${{p.y}}m`)));
    const px=a.perf_pts.map(p=>p.x),py=a.perf_pts.map(p=>p.y);const mx=px.reduce((q,c)=>q+c)/px.length,my=py.reduce((q,c)=>q+c)/py.length;
    const b=px.map((x,i)=>(x-mx)*(py[i]-my)).reduce((q,c)=>q+c)/px.map(x=>(x-mx)**2).reduce((q,c)=>q+c),a0=my-b*mx;
    s.appendChild(E('line',{{x1:X(0.1),y1:Y(a0+b*0.1),x2:X(xmax*.97),y2:Y(a0+b*xmax*.97),stroke:a.color,'stroke-width':2.2,'stroke-dasharray':'6 4'}}));
  }});
  let ly=30;legs.forEach(a=>{{s.appendChild(E('circle',{{cx:w-176,cy:ly,r:4,fill:a.color}}));s.appendChild(E('text',{{x:w-167,y:ly+4,'font-size':10,fill:a.color}},a.short));ly+=14;}});
  const hh=document.getElementById('c_diffscatter2');hh.innerHTML='';hh.appendChild(s);
}}


const IT_LEGS=A.filter(a=>a.phase!=='cold');       // the non-phase-1 legs
const IT_BASE={{}};D.landscape.forEach(r=>IT_BASE[r.t]=r.dur);
let ITON=new Set(['exp3c-analysis','exp4a-experiential-fork','exp5d-warmup-recipe']);
let ITMODE='delta';                                 // 'abs' | 'delta'
function itMode(){{
  const b=document.getElementById('it_mode');b.innerHTML='';
  [['delta','vs baseline (minutes)'],['rel','vs baseline (% faster/slower)'],['abs','absolute minutes']].forEach(m=>{{
    const l=document.createElement('label');
    l.innerHTML=`<input type="radio" name="itm" ${{ITMODE===m[0]?'checked':''}}>${{m[1]}}`;
    l.querySelector('input').onchange=()=>{{ITMODE=m[0];itemized();}};b.appendChild(l);
  }});
}}
function itCtl(){{
  const b=document.getElementById('it_ctl');b.innerHTML='';
  IT_LEGS.forEach(a=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{ITON.has(a.id)?'checked':''}}><span class="sw" style="background:${{a.color}}"></span>${{a.short}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?ITON.add(a.id):ITON.delete(a.id);itemized();}};b.appendChild(l);}});
}}
function itemized(){{
  const legs=IT_LEGS.filter(a=>ITON.has(a.id));
  const tasks=D.landscape.slice().sort((x,y)=>x.dur-y.dur);
  const rh=32, pl=168, pr=150, pt=16, w=1060;
  const val=(a,t)=>{{const c=a.per_task.find(c=>c.t===t);return c?c.min:null;}};
  const CAP=150; // % clamp for rel mode; points beyond render as an edge marker
  const pv=(v,b)=> ITMODE==='abs'? v : ITMODE==='delta'? v-b : 100*(v-b)/b;
  let xmin,xmax;
  if(ITMODE==='abs'){{xmin=0;xmax=Math.max(...tasks.map(t=>Math.max(t.dur,...legs.map(a=>val(a,t.t)||0))))*1.06||1;}}
  else{{const ds=[];tasks.forEach(t=>legs.forEach(a=>{{const v=val(a,t.t);if(v!=null)ds.push(pv(v,t.dur));}}));
        if(!ds.length)ds.push(0);
        if(ITMODE==='rel'){{let lo=Math.min(...ds),hi=Math.min(Math.max(...ds),CAP);
          xmin=Math.min(lo*1.08,-10);xmax=Math.max(hi*1.08,10);}}
        else{{const mx=Math.max(0.5,...ds.map(Math.abs));xmin=-mx*1.08;xmax=mx*1.08;}}}}
  const X=v=>pl+(w-pl-pr)*(v-xmin)/(xmax-xmin);
  // per-leg average across all tasks (in the current mode); pack labels into lanes
  const avgs=[];
  legs.forEach(a=>{{const vs=tasks.map(t=>{{const v=val(a,t.t);return v==null?null:pv(v,t.dur);}}).filter(v=>v!=null);
    if(vs.length)avgs.push({{a,m:vs.reduce((p,c)=>p+c,0)/vs.length}});}});
  avgs.forEach(r=>r.x=X(Math.max(xmin,Math.min(xmax,r.m))));
  avgs.sort((p,q)=>p.x-q.x);
  const lanes=[];avgs.forEach(r=>{{let L=0;while(lanes[L]!=null&&r.x-lanes[L]<95)L++;lanes[L]=r.x;r.lane=L;}});
  const nlane=Math.max(1,lanes.length);
  const PB=pt+rh*tasks.length+6, h=PB+30+nlane*12+8;
  const s=sv(w,h);
  // x grid + axis labels
  const tset=ITMODE==='abs'?[0,2,4,6,8,10,12]:ITMODE==='delta'?[-6,-4,-2,0,2,4,6]:[-50,-25,0,25,50,75,100,125,150];
  const unit=ITMODE==='rel'?'%':'m';
  tset.filter(g=>g>=xmin&&g<=xmax).forEach(g=>{{
    s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:PB,stroke:g===0?'#c9c7c1':'#f5f4f0','stroke-width':g===0?1.5:1}}));
    s.appendChild(E('text',{{x:X(g),y:PB+13,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},(ITMODE!=='abs'&&g>0?'+':'')+g+unit));
  }});
  const axl=ITMODE==='abs'?'run time (minutes)':ITMODE==='delta'?'time vs phase-1 baseline (left = faster)':'relative to phase-1 baseline, % (left = faster)';
  s.appendChild(E('text',{{x:pl+(w-pl-pr)/2,y:h-4,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},axl));
  const CLR={{easy:'#0f8a5f',medium:'#b45309',hard:'#c13a2e'}};
  tasks.forEach((t,i)=>{{
    const y=pt+i*rh+rh/2;
    if(i%2)s.appendChild(E('rect',{{x:pl-6,y:y-rh/2,width:w-pl-pr+12,height:rh,fill:'#faf9f6'}}));
    s.appendChild(E('circle',{{cx:14,cy:y,r:4,fill:CLR[t.cls],opacity:.8}}));
    s.appendChild(E('text',{{x:24,y:y+4,'font-size':11.5,fill:'#1b1f24'}},t.t));
    s.appendChild(E('text',{{x:pl-12,y:y+4,'text-anchor':'end','font-size':10,fill:'#8a929c','font-family':'"SF Mono",monospace'}},'base '+t.dur.toFixed(1)+'m'));
    // baseline anchor: abs = per-row diamond; delta/rel = the darker 0 gridline
    if(ITMODE==='abs'){{const bx=X(t.dur);
      s.appendChild(E('line',{{x1:bx,y1:y-11,x2:bx,y2:y+11,stroke:'#b8b6b0','stroke-width':1.2}}));
      s.appendChild(tip(E('path',{{d:`M ${{bx}} ${{y-6}} L ${{bx+6}} ${{y}} L ${{bx}} ${{y+6}} L ${{bx-6}} ${{y}} Z`,fill:'#8a929c'}}),`${{t.t}} phase-1 baseline: ${{t.dur.toFixed(2)}}m`));
    }}
    // leg marks
    legs.forEach(a=>{{const v=val(a,t.t);if(v==null)return;
      const raw=pv(v,t.dur), pct=100*(v-t.dur)/t.dur;
      const fac=v>=t.dur?(v/t.dur).toFixed(1)+'x slower':(t.dur/v).toFixed(1)+'x faster';
      const tt=ITMODE==='rel'
        ?`${{a.short}} · ${{t.t}}: ${{pct>=0?'+':''}}${{pct.toFixed(0)}}% (${{fac}}), ${{v.toFixed(2)}}m vs ${{t.dur.toFixed(2)}}m base`
        :`${{a.short}} · ${{t.t}}: ${{v.toFixed(2)}}m (${{v-t.dur>=0?'+':''}}${{(v-t.dur).toFixed(2)}}m vs base)`;
      if(ITMODE==='rel' && raw>xmax){{const ex=X(xmax);
        s.appendChild(tip(E('path',{{d:`M ${{ex+4}} ${{y}} L ${{ex-4}} ${{y-5}} L ${{ex-4}} ${{y+5}} Z`,fill:a.color,opacity:.9,stroke:'#fff','stroke-width':1}}),tt));
        s.appendChild(E('text',{{x:ex-9,y:y+3.5,'text-anchor':'end','font-size':9,fill:a.color}},`+${{Math.round(pct)}}%`));
      }} else {{
        s.appendChild(tip(E('circle',{{cx:X(raw),cy:y,r:5,fill:a.color,opacity:.82,stroke:'#fff','stroke-width':1.1}}),tt));
      }}
    }});
  }});
  // per-leg average lines across all tasks, with the value labeled underneath
  avgs.forEach(r=>{{
    s.appendChild(E('line',{{x1:r.x,y1:pt,x2:r.x,y2:PB,stroke:r.a.color,'stroke-width':1.4,'stroke-dasharray':'5 4',opacity:.9}}));
    const lab=ITMODE==='abs'?r.m.toFixed(1)+'m':ITMODE==='rel'?(r.m>=0?'+':'')+Math.round(r.m)+'%':(r.m>=0?'+':'')+r.m.toFixed(1)+'m';
    s.appendChild(E('text',{{x:r.x,y:PB+24+r.lane*12,'text-anchor':'middle','font-size':9,'font-weight':600,fill:r.a.color}},`${{r.a.short}} avg ${{lab}}`));
  }});
  // legend (right gutter)
  let ly=pt+8;legs.forEach(a=>{{s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:4.5,fill:a.color}}));s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10.5,fill:'#5b6571'}},a.short));ly+=17;}});
  ly+=4;
  if(ITMODE==='abs')s.appendChild(E('path',{{d:`M ${{w-pr+22}} ${{ly-4}} L ${{w-pr+27}} ${{ly}} L ${{w-pr+22}} ${{ly+4}} L ${{w-pr+17}} ${{ly}} Z`,fill:'#8a929c'}}));
  else s.appendChild(E('line',{{x1:w-pr+22,y1:ly-5,x2:w-pr+22,y2:ly+5,stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10,fill:'#8a929c'}},ITMODE==='abs'?'phase-1 base':'phase-1 base (0)'));
  const hh=document.getElementById('c_itemized');hh.innerHTML='';hh.appendChild(s);
}}

function themeTable(){{
  const T=D.themes;const cold=D.coldtotal;
  let html='<thead><tr><th>Theme</th><th>Arms</th><th class="num">tok/turn</th><th class="num">s/turn</th><th class="num">total min</th><th class="num">vs cold</th><th class="num">turns</th><th class="num">accuracy</th></tr></thead><tbody>';
  T.forEach(t=>{{
    const d=t.dtime;const dc=d<=-0.5?'#0f8a5f':d>=3?'#c13a2e':'#5b6571';
    html+=`<tr><td><span class="sw" style="display:inline-block;background:${{t.color}}"></span> ${{t.label}}<div class="note" style="margin:2px 0 0">${{t.desc}}</div></td>`+
      `<td class="mono" style="font-size:11px">${{t.arms.join(', ')}}</td>`+
      `<td class="num">${{t.ktok}}k</td><td class="num">${{t.secturn}}</td><td class="num">${{t.total}}</td>`+
      `<td class="num" style="color:${{dc}};font-weight:600">${{d>0?'+':''}}${{d}}</td>`+
      `<td class="num">${{t.turns}}</td><td class="num">${{t.acc}}/12</td></tr>`;
  }});
  html+='</tbody>';document.getElementById('themetab').innerHTML=html;
}}
function themeScatter(){{
  const T=D.themes, cold=D.coldtask_min;  // cold per-task minutes (highlighted iso curve)
  const TCsec={{}}; D.turncost.arms.forEach(a=>TCsec[a.short]=a.sec);  // real per-turn latency
  const arms=A.map(a=>({{...a, secturn:(TCsec[a.short]!=null?TCsec[a.short]:a.total*60/a.turns), color:(T.find(t=>t.key===a.theme)||{{}}).color||'#8a929c'}}));
  const w=1060,h=440,pl=58,pr=150,pt=20,pb=46;
  const xmax=Math.max(...arms.map(a=>a.turns))*1.1, ymax=Math.max(...arms.map(a=>a.secturn))*1.14;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  // iso-time curves: seconds/turn = (per-task minutes)*60 / turns
  [1.5,2,2.5,3,4,5].forEach(tm=>{{
    let d='';for(let tn=Math.max(1,tm*60/ymax);tn<=xmax;tn+=1){{const sc=tm*60/tn;if(sc>ymax)continue;d+=(d?'L':'M')+X(tn).toFixed(1)+' '+Y(sc).toFixed(1)+' ';}}
    const hot=Math.abs(tm-cold)<0.35;
    s.appendChild(E('path',{{d,fill:'none',stroke:hot?'#b8b6b0':'#e2e0da','stroke-width':hot?1.6:1,'stroke-dasharray':hot?'':'3 3'}}));
    const tn=xmax*0.96,sc=tm*60/tn;if(sc<ymax&&sc>0)s.appendChild(E('text',{{x:X(tn)+3,y:Y(sc)+3,'font-size':9,fill:hot?'#8a929c':'#b0aea8'}},tm+'m'));
  }});
  // axes
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('line',{{x1:pl,y1:pt,x2:pl,y2:h-pb,stroke:'#c9c7c1'}}));
  for(let g=0;g<=xmax;g+=20)s.appendChild(E('text',{{x:X(g),y:h-pb+15,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));
  for(let g=0;g<=ymax;g+=1)s.appendChild(E('text',{{x:pl-7,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'s'));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'turns (steps taken)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'seconds per turn (real per-turn latency)'));
  // arm dots
  arms.forEach(a=>{{const cx=X(a.turns),cy=Y(a.secturn);
    s.appendChild(tip(E('circle',{{cx,cy,r:6,fill:a.color,opacity:.85,stroke:'#fff','stroke-width':1.3}}),`${{a.short}} (${{a.label}}): ${{a.turns}} turns, ${{a.secturn.toFixed(2)}}s/turn, ${{(a.turns*a.secturn/60).toFixed(1)}}m/task, ${{a.total.toFixed(1)}}m suite`));
    s.appendChild(E('text',{{x:cx+(a.turns>xmax*0.7?-9:9),y:cy+3,'text-anchor':a.turns>xmax*0.7?'end':'start','font-size':9,fill:'#1b1f24'}},a.short));
  }});
  // theme legend
  let ly=pt+6;T.forEach(t=>{{s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:t.color,opacity:.85}}));s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10,fill:'#5b6571'}},t.label));ly+=17;}});
  const hh=document.getElementById('c_theme');hh.innerHTML='';hh.appendChild(s);
}}

function thinkBar(){{
  const T=D.thinking, arms=T.arms, cold=T.coldmean;
  const w=1060,pl=64,pr=90,pt=16,rh=26,gap=8;const h=pt+rh*arms.length+34;
  const xmax=Math.max(...arms.map(a=>a.outturn))*1.08;
  const X=v=>pl+(w-pl-pr)*v/xmax;const s=sv(w,h);
  for(let g=0;g<=xmax;g+=25){{s.appendChild(E('line',{{x1:X(g),y1:pt-4,x2:X(g),y2:pt+rh*arms.length,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:pt+rh*arms.length+16,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  // cold reference line
  s.appendChild(E('line',{{x1:X(cold),y1:pt-4,x2:X(cold),y2:pt+rh*arms.length,stroke:'#8a929c','stroke-width':1.5,'stroke-dasharray':'5 4'}}));
  s.appendChild(E('text',{{x:X(cold),y:pt-7,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'}},`cold ~${{cold}}`));
  s.appendChild(E('text',{{x:pl+(w-pl-pr)/2,y:h-3,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},'output tokens generated per turn'));
  arms.forEach((a,i)=>{{const y=pt+i*rh;
    s.appendChild(E('text',{{x:pl-10,y:y+rh/2-gap/2+4,'text-anchor':'end','font-size':11,fill:'#1b1f24','font-weight':600}},a.short));
    s.appendChild(tip(E('rect',{{x:X(0),y:y,width:Math.max(1,X(a.outturn)-X(0)),height:rh-gap,rx:2.5,fill:a.color,opacity:.88}}),`${{a.short}}: ${{a.outturn}} tokens/turn (sd ${{a.sd}}), ${{a.turns}} turns/task`));
    s.appendChild(E('text',{{x:X(a.outturn)+7,y:y+rh/2-gap/2+4,'font-size':10,fill:'#5b6571'}},a.outturn));
  }});
  const hh=document.getElementById('c_thinkbar');hh.innerHTML='';hh.appendChild(s);
}}
function turnDelta(){{
  const T=D.turns, arms=T.arms;  // sorted ascending by delta (most-negative first)
  const w=1060,pl=64,pr=120,pt=18,rh=26,gap=8;const h=pt+rh*arms.length+34;
  const dmax=Math.max(...arms.map(a=>Math.abs(a.delta)),1)*1.15;
  const X=v=>pl+((w-pl-pr))*(v+dmax)/(2*dmax);const s=sv(w,h);
  s.appendChild(E('line',{{x1:X(0),y1:pt-4,x2:X(0),y2:pt+rh*arms.length,stroke:'#c9c7c1','stroke-width':2}}));
  s.appendChild(E('text',{{x:X(-dmax*.6),y:pt-6,'text-anchor':'middle','font-size':10,fill:'#0f8a5f'}},'← fewer turns (more direct)'));
  s.appendChild(E('text',{{x:X(dmax*.55),y:pt-6,'text-anchor':'middle','font-size':10,fill:'#c13a2e'}},'more turns (extra steps) →'));
  s.appendChild(E('text',{{x:X(0),y:pt+rh*arms.length+16,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},`cold = ${{T.coldmean}} turns`));
  arms.forEach((a,i)=>{{const y=pt+i*rh;const x0=X(0),x1=X(a.delta);const pos=a.delta>0;
    s.appendChild(E('text',{{x:pl-10,y:y+rh/2-gap/2+4,'text-anchor':'end','font-size':11,fill:'#1b1f24','font-weight':600}},a.short));
    s.appendChild(tip(E('rect',{{x:Math.min(x0,x1),y:y,width:Math.max(2,Math.abs(x1-x0)),height:rh-gap,rx:2.5,fill:pos?'#c13a2e':'#0f8a5f',opacity:.82}}),`${{a.short}}: ${{a.turns}} turns, ${{a.delta>0?'+':''}}${{a.delta}} vs cold (${{a.pct>0?'+':''}}${{a.pct}}%)`));
    s.appendChild(E('text',{{x:x1+(pos?5:-5),y:y+rh/2-gap/2+4,'text-anchor':pos?'start':'end','font-size':10,fill:'#5b6571'}},`${{a.pct>0?'+':''}}${{a.pct}}%`));
  }});
  const hh=document.getElementById('c_turndelta');hh.innerHTML='';hh.appendChild(s);
}}
function turnScale(){{
  const L=D.turns.scale, C=D.dist_byleg.color, sel=D.dist_byleg.order.filter(k=>TSsel.has(k));
  const w=1060,h=360,pl=56,pr=112,pt=20,pb=48;
  const xmax=Math.max(...L.tasks.map(t=>t.bturns))*1.06;
  const ally=sel.flatMap(k=>L.tasks.map(t=>t.sv[k]).filter(v=>v!=null));
  const ymin=Math.min(...ally,-6)*1.12, ymax=Math.max(...ally,6)*1.12;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=10){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+4,y:Y(0)+3,'font-size':9,fill:'#8a929c'}},'cold'));
  for(let g=Math.ceil(ymin/10)*10;g<=ymax;g+=10){{if(g===0)continue;s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'baseline task length (naive cold turns)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'turns saved vs cold (up = shorter path)'));
  if(!sel.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  sel.forEach(k=>{{const col=C[k], f=L.fits[k];
    L.tasks.forEach(t=>{{const v=t.sv[k];if(v==null)return;
      s.appendChild(tip(E('circle',{{cx:X(t.bturns),cy:Y(v),r:4,fill:col,opacity:.72}}),`${{k}} · ${{t.t}} (${{t.cls}}, ${{t.bturns}} base turns): ${{v>0?'+':''}}${{v}} turns saved`));}});
    s.appendChild(E('line',{{x1:X(1),y1:Y(f.intercept+f.slope*1),x2:X(xmax*.98),y2:Y(f.intercept+f.slope*xmax*.98),stroke:col,'stroke-width':2.4,'stroke-dasharray':'6 4'}}));}});
  let ly=pt+8;sel.forEach(k=>{{const cc=L.fits[k].corr;
    s.appendChild(E('circle',{{cx:w-pr+14,cy:ly,r:4.5,fill:C[k]}}));
    s.appendChild(E('text',{{x:w-pr+22,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));
    s.appendChild(E('text',{{x:w-pr+52,y:ly+3.5,'font-size':9,fill:cc>0?'#0f8a5f':'#c13a2e'}},`${{cc>0?'+':''}}${{cc}}`));ly+=16;}});
  const hh=document.getElementById('c_turnscale');hh.innerHTML='';hh.appendChild(s);
}}
let LSsel=new Set(['6b','5b','4a']);
let TSsel=new Set(['6b','5b','2b']);
function scaleCtl(ctlId,sel,redraw){{
  const bar=document.getElementById(ctlId);bar.innerHTML='';
  D.dist_byleg.order.forEach(k=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{sel.has(k)?'checked':''}}><span class="sw" style="background:${{D.dist_byleg.color[k]}}"></span>${{k}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?sel.add(k):sel.delete(k);redraw();}};bar.appendChild(l);}});
}}
function lengthScale(){{
  const L=D.lengthscale, C=D.dist_byleg.color, sel=D.dist_byleg.order.filter(k=>LSsel.has(k));
  const w=1060,h=380,pl=60,pr=112,pt=20,pb=48;
  const xmax=Math.max(...L.tasks.map(t=>t.bturns))*1.06;
  const ymin=-210,ymax=120;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(ymax-Math.max(ymin,Math.min(ymax,v)))/(ymax-ymin);
  const s=sv(w,h);
  for(let g=0;g<=xmax;g+=10){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+4,y:Y(0)+3,'font-size':9,fill:'#8a929c'}},'cold'));
  for(let g=-180;g<=ymax;g+=60){{if(g===0)continue;s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'s'));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'baseline task length (naive cold turns)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'seconds saved vs cold (up = faster)'));
  s.appendChild(E('text',{{x:X(1),y:Y(ymax)+2,'font-size':9,'font-style':'italic',fill:'#0f8a5f'}},'saves time'));
  s.appendChild(E('text',{{x:X(1),y:Y(ymin)+6,'font-size':9,'font-style':'italic',fill:'#c13a2e'}},'loses time'));
  if(!sel.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  sel.forEach(k=>{{const col=C[k], f=L.fits[k];
    L.tasks.forEach(t=>{{const v=t.sv[k];if(v==null)return;const off=v<ymin;
      const node=off?E('path',{{d:`M ${{X(t.bturns)}} ${{Y(ymin)+7}} L ${{X(t.bturns)-5}} ${{Y(ymin)-1}} L ${{X(t.bturns)+5}} ${{Y(ymin)-1}} Z`,fill:col,opacity:.85,stroke:'#fff','stroke-width':1}})
                        :E('circle',{{cx:X(t.bturns),cy:Y(v),r:4,fill:col,opacity:.72}});
      s.appendChild(tip(node,`${{k}} · ${{t.t}} (${{t.cls}}, ${{t.bturns}} base turns): ${{v>0?'+':''}}${{v}}s vs cold${{off?' (off-scale)':''}}`));}});
    s.appendChild(E('line',{{x1:X(1),y1:Y(f.intercept+f.slope*1),x2:X(xmax*.98),y2:Y(f.intercept+f.slope*xmax*.98),stroke:col,'stroke-width':2.4,'stroke-dasharray':'6 4'}}));}});
  let ly=pt+8;sel.forEach(k=>{{const cc=L.fits[k].corr;
    s.appendChild(E('circle',{{cx:w-pr+14,cy:ly,r:4.5,fill:C[k]}}));
    s.appendChild(E('text',{{x:w-pr+22,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));
    s.appendChild(E('text',{{x:w-pr+52,y:ly+3.5,'font-size':9,fill:cc>0?'#0f8a5f':'#c13a2e'}},`${{cc>0?'+':''}}${{cc}}`));ly+=16;}});
  const hh=document.getElementById('c_lengthscale');hh.innerHTML='';hh.appendChild(s);
}}

function slopeChart(){{
  const R=D.rankcompare, arms=R.arms;
  const tmin=R.turns_spread[0], tmax=R.turns_spread[1];
  const mmin=R.lat_spread[0], mmax=R.lat_spread[1];
  const w=1060,pt=52,pb=34,h=470,H=h-pt-pb, xL=452,xR=608;
  const yT=v=>pt+H*(v-tmin)/(tmax-tmin);   // fewest turns at top
  const yM=v=>pt+H*(v-mmin)/(mmax-mmin);   // fastest at top
  const s=sv(w,h);
  s.appendChild(E('text',{{x:xL,y:pt-22,'text-anchor':'middle','font-size':11,'font-weight':700,fill:'#1b1f24'}},'turns'));
  s.appendChild(E('text',{{x:xL,y:pt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},'height \u221d turns (fewest on top)'));
  s.appendChild(E('text',{{x:xR,y:pt-22,'text-anchor':'middle','font-size':11,'font-weight':700,fill:'#1b1f24'}},'latency'));
  s.appendChild(E('text',{{x:xR,y:pt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},'height \u221d minutes (fastest on top)'));
  // axis lines + value scale anchors
  [[xL,yT,tmin,tmax,'t'],[xR,yM,mmin,mmax,'m']].forEach(([x,yfn,lo,hi,u])=>{{
    s.appendChild(E('line',{{x1:x,y1:pt,x2:x,y2:pt+H,stroke:'#ececE6','stroke-width':1}}));
    s.appendChild(E('line',{{x1:x,y1:pt,x2:x,y2:pt+H,stroke:'#e7e6e1','stroke-width':1}}));
    [lo,(lo+hi)/2,hi].forEach(v=>{{s.appendChild(E('line',{{x1:x-3,y1:yfn(v),x2:x+3,y2:yfn(v),stroke:'#c9c7c1'}}));}});
  }});
  // connecting lines colored by which side is relatively worse (value-normalized)
  arms.forEach(a=>{{const y1=yT(a.turns),y2=yM(a.min);
    const pT=(a.turns-tmin)/(tmax-tmin), pM=(a.min-mmin)/(mmax-mmin);
    const col=pM>pT+0.03?'#c13a2e':pM<pT-0.03?'#0f8a5f':'#b8b6b0';
    s.appendChild(tip(E('line',{{x1:xL,y1,x2:xR,y2,stroke:col,'stroke-width':Math.abs(a.drank)>=5?2.6:1.6,opacity:.8}}),`${{a.short}}: ${{a.turns}} turns (rank ${{a.rt}}) -> ${{a.min}}m (rank ${{a.rl}}), moves ${{a.drank>0?'+':''}}${{a.drank}} places`));
    s.appendChild(E('circle',{{cx:xL,cy:y1,r:4,fill:a.color,stroke:'#fff','stroke-width':1.2}}));
    s.appendChild(E('circle',{{cx:xR,cy:y2,r:4,fill:a.color,stroke:'#fff','stroke-width':1.2}}));
  }});
  // de-collide labels vertically (dots stay at true positions; leaders connect)
  const gap=15;
  function place(items,yfn,key){{const so=[...items].sort((p,q)=>yfn(p)-yfn(q));let last=-1e9;
    so.forEach(a=>{{a[key]=Math.max(yfn(a),last+gap);last=a[key];}});
    const over=last-(pt+H);if(over>0){{let sh=over;so.slice().reverse().forEach(a=>{{}});so.forEach(a=>{{a[key]=Math.max(pt+6,a[key]-sh);}});}}
  }}
  place(arms,a=>yT(a.turns),'ylL'); place(arms,a=>yM(a.min),'ylR');
  arms.forEach(a=>{{const y1=yT(a.turns),y2=yM(a.min);
    if(Math.abs(a.ylL-y1)>2) s.appendChild(E('line',{{x1:xL-7,y1:a.ylL,x2:xL-1,y2:y1,stroke:'#d8d5cd','stroke-width':1}}));
    s.appendChild(E('text',{{x:xL-11,y:a.ylL+3.5,'text-anchor':'end','font-size':10,fill:'#1b1f24'}},`${{a.turns}}t \u00b7 ${{a.short}}`));
    if(Math.abs(a.ylR-y2)>2) s.appendChild(E('line',{{x1:xR+1,y1:y2,x2:xR+7,y2:a.ylR,stroke:'#d8d5cd','stroke-width':1}}));
    s.appendChild(E('text',{{x:xR+11,y:a.ylR+3.5,'font-size':10,fill:'#1b1f24'}},`${{a.short}} \u00b7 ${{a.min}}m`));
  }});
  s.appendChild(E('text',{{x:80,y:pt+H+18,'font-size':10,fill:'#0f8a5f'}},'green rises = faster than its turn count suggests'));
  s.appendChild(E('text',{{x:w-80,y:pt+H+18,'text-anchor':'end','font-size':10,fill:'#c13a2e'}},'red falls = slower than its turn count suggests'));
  const hh=document.getElementById('c_slope');hh.innerHTML='';hh.appendChild(s);
}}
function rankScatter(){{
  const R=D.rankcompare, arms=R.arms;
  const w=1060,h=436,pl=58,pr=30,pt=30,pb=50;
  const xmax=Math.max(...arms.map(a=>a.turns))*1.08, xmin=Math.min(...arms.map(a=>a.turns))-3;
  const ymax=Math.max(...arms.map(a=>a.min))*1.06, ymin=Math.min(...arms.map(a=>a.min))-2;
  const X=v=>pl+(w-pl-pr)*(v-xmin)/(xmax-xmin), Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);
  const s=sv(w,h);
  for(let g=25;g<=xmax;g+=5){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-32,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  for(let g=20;g<=ymax;g+=10){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f8f7f3'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'m'));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'turns per task (path length)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'latency (minutes, suite)'));
  // discovered groupings: delivery mechanism carves the plane. Drawn behind the dots.
  const GROUPS=[
    {{lab:'Prompt-embedded',sub:'recipe + warm-up: few turns, fast',col:'#0f8a5f',ms:['5a','5b','6a','6b'],lp:'above'}},
    {{lab:'Cold + on-disk retrieval',sub:'cheap context, but a longer path',col:'#3f6ea8',ms:['1c','1b','1a','2a','2b','3b'],lp:'above'}},
    {{lab:'In-context forks',sub:'context tax: slow at any turn count',col:'#c13a2e',ms:['4a','4b'],lp:'below'}}
  ];
  const by={{}}; arms.forEach(a=>by[a.short]=a);
  GROUPS.forEach(g=>{{
    const pts=g.ms.map(m=>by[m]).filter(Boolean).map(a=>[X(a.turns),Y(a.min)]);
    const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
    const cx=(Math.min(...xs)+Math.max(...xs))/2, cy=(Math.min(...ys)+Math.max(...ys))/2;
    const rx=(Math.max(...xs)-Math.min(...xs))/2+30, ry=(Math.max(...ys)-Math.min(...ys))/2+24;
    s.appendChild(E('ellipse',{{cx,cy,rx,ry,fill:g.col,'fill-opacity':.06,stroke:g.col,'stroke-width':1.4,'stroke-dasharray':'6 4'}}));
    const ly=g.lp==='above'?cy-ry-13:cy+ry+14;
    s.appendChild(E('text',{{x:cx,y:ly,'text-anchor':'middle','font-size':10.5,'font-weight':700,fill:g.col}},g.lab));
    s.appendChild(E('text',{{x:cx,y:ly+11,'text-anchor':'middle','font-size':9,fill:'#5b6571'}},g.sub));
  }});
  // arm dots
  arms.forEach(a=>{{const cx=X(a.turns),cy=Y(a.min);
    s.appendChild(tip(E('circle',{{cx,cy,r:5.5,fill:a.color,opacity:.9,stroke:'#fff','stroke-width':1.3}}),`${{a.short}}: ${{a.turns}} turns, ${{a.min}}m`));
    s.appendChild(E('text',{{x:cx+(a.turns>xmax-6?-9:9),y:cy+3.5,'text-anchor':a.turns>xmax-6?'end':'start','font-size':9.5,fill:'#1b1f24'}},a.short));
  }});
  const hh=document.getElementById('c_rankscatter');hh.innerHTML='';hh.appendChild(s);
}}

const OVsel={{lat:new Set(['1c','4a','6b','3a']),turns:new Set(['1c','6b','2b','4a']),acc:new Set(D.dist_byleg.order)}};
function ovCtl(kind,ctlId){{
  const B=D.dist_byleg,sel=OVsel[kind],bar=document.getElementById(ctlId);bar.innerHTML='';
  B.order.forEach(k=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{sel.has(k)?'checked':''}}><span class="sw" style="background:${{B.color[k]}}"></span>${{k}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?sel.add(k):sel.delete(k);ovDraw(kind);}};bar.appendChild(l);}});
}}
function ovDraw(kind){{
  if(kind==='acc')return accDots();
  const B=D.dist_byleg,series=B[kind],sel=OVsel[kind];
  const o=kind==='lat'?{{lo:0,hi:12,bw:0.55,tickstep:2,unit:'m',xlabel:'per-task latency (minutes)',cid:'c_dist_lat'}}:{{lo:0,hi:125,bw:6,tickstep:20,unit:'',xlabel:'per-task turn count (num_turns)',cid:'c_dist_turns'}};
  const w=1060,h=236,pl=48,pr=132,pt=16,pb=42;
  const active=B.order.filter(k=>sel.has(k));
  const grid=[],step=(o.hi-o.lo)/220;for(let x=o.lo;x<=o.hi+1e-9;x+=step)grid.push(x);
  const sq=Math.sqrt(2*Math.PI);
  const curves=active.map(k=>{{const data=series[k],n=data.length,cst=1/(n*o.bw*sq);
    return {{k,dens:grid.map(x=>data.reduce((sm,v)=>sm+Math.exp(-.5*((x-v)/o.bw)**2),0)*cst)}};}});
  const ymax=Math.max(0.02,...curves.flatMap(c=>c.dens))*1.16;
  const X=v=>pl+(w-pl-pr)*(v-o.lo)/(o.hi-o.lo),Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  for(let g=o.lo;g<=o.hi+1e-9;g+=o.tickstep){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:X(g),y:h-25,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+o.unit));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},o.xlabel));
  s.appendChild(E('text',{{x:13,y:(pt+h-pb)/2,'font-size':9.5,fill:'#8a929c','text-anchor':'middle',transform:`rotate(-90 13 ${{(pt+h-pb)/2}})`}},'density'));
  if(!active.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  curves.forEach((c,ci)=>{{const col=B.color[c.k];let d='';
    c.dens.forEach((yv,i)=>{{d+=(d?'L':'M')+X(grid[i]).toFixed(1)+' '+Y(Math.min(yv,ymax)).toFixed(1)+' ';}});
    s.appendChild(tip(E('path',{{d,fill:'none',stroke:col,'stroke-width':2.1,opacity:.92}}),`${{c.k}}: mean ${{(series[c.k].reduce((a,b)=>a+b,0)/series[c.k].length).toFixed(1)}}${{o.unit}}, n=${{series[c.k].length}}`));
    series[c.k].forEach(v=>s.appendChild(E('line',{{x1:X(v),y1:h-pb+2+ci*2,x2:X(v),y2:h-pb+5+ci*2,stroke:col,'stroke-width':1,opacity:.55}})));
  }});
  let ly=pt+8;active.forEach(k=>{{s.appendChild(E('line',{{x1:w-pr+12,y1:ly,x2:w-pr+30,y2:ly,stroke:B.color[k],'stroke-width':2.6}}));s.appendChild(E('text',{{x:w-pr+35,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));ly+=15;}});
  document.getElementById(o.cid).innerHTML='';document.getElementById(o.cid).appendChild(s);
}}
function accDots(){{
  const B=D.dist_byleg,sel=OVsel.acc,order=B.order.filter(k=>sel.has(k));
  const w=1060,h=214,pl=48,pr=24,pt=18,pb=40,lo=7.5,hi=12;
  const X=v=>pl+(w-pl-pr)*(v-lo)/(hi-lo);const s=sv(w,h);
  for(let g=8;g<=12;g++){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-24,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'/12'));}}
  const byscore={{}};order.forEach(k=>{{const sc=B.acc[k];(byscore[sc]=byscore[sc]||[]).push(k);}});
  Object.keys(byscore).forEach(sc=>{{byscore[sc].forEach((k,i)=>{{const cy=pt+14+i*17,cx=X(+sc);
    s.appendChild(tip(E('circle',{{cx,cy,r:6,fill:B.color[k],opacity:.9,stroke:'#fff','stroke-width':1.3}}),`${{k}}: ${{sc}}/12`));
    s.appendChild(E('text',{{x:cx+11,y:cy+3.5,'font-size':9.5,fill:'#1b1f24'}},k));}});}});
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},'accuracy per leg (tasks passed of 12)'));
  document.getElementById('c_dist_acc').innerHTML='';document.getElementById('c_dist_acc').appendChild(s);
}}
function initDist(){{ovCtl('lat','ov_lat_ctl');ovDraw('lat');ovCtl('turns','ov_turns_ctl');ovDraw('turns');ovCtl('acc','ov_acc_ctl');accDots();}}
function reliabilityScatter(){{
  const R=D.reliability, arms=R.arms, k=R.kcv;
  const w=1060,h=340,pl=56,pr=150,pt=22,pb=48;
  const xmax=Math.max(...arms.map(a=>a.lm))*1.12, ymax=Math.max(...arms.map(a=>a.ls))*1.15;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  for(let g=1;g<=xmax;g+=1){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'));}}
  for(let g=1;g<=ymax;g+=1){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f8f7f3'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'m'));}}
  // reference line SD = k * mean
  const xe=xmax, ye=Math.min(ymax,k*xmax);
  s.appendChild(E('line',{{x1:X(0),y1:Y(0),x2:X(xe),y2:Y(ye),stroke:'#8a929c','stroke-width':1.6,'stroke-dasharray':'6 4'}}));
  s.appendChild(E('text',{{x:X(xe)-4,y:Y(ye)-6,'text-anchor':'end','font-size':9,'font-style':'italic',fill:'#8a929c'}},`typical spread (SD = ${{k}} x mean)`));
  s.appendChild(E('text',{{x:X(0.15),y:Y(ymax*.94),'font-size':9.5,'font-style':'italic',fill:'#c13a2e'}},'above = erratic (spread beyond what speed predicts)'));
  s.appendChild(E('text',{{x:X(xmax*.98),y:Y(0.12),'text-anchor':'end','font-size':9.5,'font-style':'italic',fill:'#0f8a5f'}},'below = consistent (tighter than its speed predicts)'));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'mean latency per task (minutes)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'SD of latency (minutes)'));
  arms.forEach(a=>{{const cx=X(a.lm),cy=Y(a.ls);const erratic=a.lcv>k+0.03;
    s.appendChild(tip(E('circle',{{cx,cy,r:5.5,fill:a.color,opacity:.88,stroke:'#fff','stroke-width':1.3}}),`${{a.short}}: mean ${{a.lm}}m, SD ${{a.ls}}m, CV ${{a.lcv}} (turn CV ${{a.tcv}})`));
    s.appendChild(E('text',{{x:cx+(a.lm>xmax*.72?-9:9),y:cy+3.5,'text-anchor':a.lm>xmax*.72?'end':'start','font-size':9.5,'font-weight':a.lcv>0.9||a.lcv<0.52?'700':'400',fill:'#1b1f24'}},`${{a.short}}`));
  }});
  let ly=pt+8;const seen={{}};
  const hh=document.getElementById('c_reliability');hh.innerHTML='';hh.appendChild(s);
}}
function landscape(){{
  const L=D_LAND;const w=1060,h=430,pl=64,pb=52,pr=140,pt=26;
  const CLR={{easy:'#0f8a5f',medium:'#b45309',hard:'#c13a2e'}};
  const xmax=Math.max(...L.map(r=>r.dur))*1.12, ymax=1.0;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  const xmed=[...L.map(r=>r.dur)].sort((a,b)=>a-b)[Math.floor(L.length/2)];
  const yth=0.15;
  // quadrant guides
  s.appendChild(E('line',{{x1:X(xmed),y1:pt,x2:X(xmed),y2:h-pb,stroke:'#e7e6e1','stroke-dasharray':'4 4'}}));
  s.appendChild(E('line',{{x1:pl,y1:Y(yth),x2:w-pr,y2:Y(yth),stroke:'#e7e6e1','stroke-dasharray':'4 4'}}));
  const ql=[[X(xmed)-8,Y(yth)+16,'end','quick & safe','#8a929c'],
            [X(xmed)+8,Y(yth)+16,'start','long haul','#8a929c'],
            [X(xmed)-8,pt+12,'end','brittle / traps','#c13a2e'],
            [X(xmed)+8,pt+12,'start','long AND brittle','#c13a2e']];
  ql.forEach(q=>s.appendChild(E('text',{{x:q[0],y:q[1],'text-anchor':q[2],'font-size':10,'font-style':'italic',fill:q[4]}},q[3])));
  // axes ticks
  for(let g=0;g<=xmax;g+=1){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:X(g),y:h-34,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'))}}
  [0,.25,.5,.75,1].forEach(g=>s.appendChild(E('text',{{x:pl-8,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},Math.round(g*100)+'%')));
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('line',{{x1:pl,y1:pt,x2:pl,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-10,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'duration: denoised cold-baseline minutes (how long)'));
  s.appendChild(E('text',{{x:18,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 18 ${{(pt+h-pb)/2}})`}},'failure rate across 22 arms (how hard)'));
  // dots
  const ann={{'zilloft-9':'the marathon','zilloft-10':'the trap','dashdish-8':'broken rubric'}};
  // selective labels: annotate the narrative tasks only; the low-failure "safe
  // pile" clusters near 2m and would collide, so those are dots-plus-hover.
  const LABEL=new Set(['zilloft-9','zilloft-10','dashdish-8','zilloft-2','zilloft-5','dashdish-1']);
  L.forEach(r=>{{
    const cx=X(r.dur),cy=Y(r.fail);const rad=r.broken?7:6.5;
    const c=E('circle',{{cx,cy,r:rad,fill:CLR[r.cls],opacity:r.broken?0.35:0.82,stroke:r.broken?'#c13a2e':'#fff','stroke-width':r.broken?1.6:1.2}});
    if(r.broken)c.setAttribute('stroke-dasharray','2 2');
    s.appendChild(tip(c,`${{r.t}} (${{r.cls}}): ${{r.dur}}m, ${{r.turns}} turns, fails ${{Math.round(r.fail*100)}}% (${{r.nfail}}/${{r.n}}) · diff-score ${{r.diffscore}}`));
    if(!LABEL.has(r.t))return;
    const lab=ann[r.t]?`${{r.t}} · ${{ann[r.t]}}`:r.t;
    const dx=(r.dur>xmed?-10:10), ta=(r.dur>xmed?'end':'start');
    s.appendChild(E('text',{{x:cx+dx,y:cy+(r.fail>0.85?16:3.5),'text-anchor':ta,'font-size':9.5,fill:ann[r.t]?(r.broken?'#8a929c':'#1b1f24'):'#5b6571','font-weight':ann[r.t]?'600':'400'}},lab));
  }});
  s.appendChild(E('text',{{x:X(2.05),y:Y(0)+30,'text-anchor':'middle','font-size':9.5,'font-style':'italic',fill:'#8a929c'}},'the quick & reliable pile (7 tasks, hover for detail)'));
  // legend
  let ly=pt+6;[['easy','#0f8a5f'],['medium','#b45309'],['hard','#c13a2e']].forEach(k=>{{
    s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:k[1],opacity:.82}}));
    s.appendChild(E('text',{{x:w-pr+32,y:ly+4,'font-size':10.5,fill:'#5b6571'}},k[0]));ly+=18;}});
  ly+=6;
  s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:'none',stroke:'#c13a2e','stroke-dasharray':'2 2','stroke-width':1.4}}));
  s.appendChild(E('text',{{x:w-pr+32,y:ly+4,'font-size':10,fill:'#8a929c'}},'broken rubric'));
  const hh=document.getElementById('c_landscape');hh.innerHTML='';hh.appendChild(s);
}}
function diffBars(){{
  // arms that help somewhere: recipe + warmup + analysis + 5D
  const pick=['exp3c-analysis','exp5a-recipe-site','exp5c-atomic-warmup','exp5d-warmup-recipe','exp4b-expert-fork'];
  const tiers=['easy','medium','hard'];
  const w=1060,h=300,pl=48;const cw=(w-pl-20)/pick.length;const bw=Math.min(30,(cw-30)/3);
  const cell={{}};pick.forEach(id=>{{const a=BY[id];cell[id]={{}};tiers.forEach(tr=>{{
    const ts=ORDER.filter(t=>DIFF[t]===tr);
    cell[id][tr]=ts.reduce((s,t)=>s+(COLD.per_task.find(x=>x.t===t).min - a.per_task.find(x=>x.t===t).min),0)/ts.length;}});}});
  const vmax=Math.max(...pick.flatMap(id=>tiers.map(tr=>Math.abs(cell[id][tr]))),0.5)*1.15;
  const Y=v=>34+(h-96)*(vmax-Math.max(-vmax,Math.min(vmax,v)))/(2*vmax);const s=sv(w,h);
  s.appendChild(E('text',{{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'}},'time benefit vs cold by task difficulty (min/task saved; + = faster than cold)'));
  for(let g=-Math.ceil(vmax);g<=vmax;g++){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g))}}
  pick.forEach((id,pi)=>{{const a=BY[id];const x0=pl+14+pi*cw;
    tiers.forEach((tr,ti)=>{{const v=cell[id][tr];const x=x0+ti*(bw+6),y0=Y(0),y1=Y(v);
      const shade={{easy:.4,medium:.68,hard:1}}[tr];
      s.appendChild(tip(E('rect',{{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:2.5,fill:v>=0?'#0f8a5f':'#c13a2e',opacity:shade}}),`${{a.label}} · ${{tr}}: ${{v>0?'+':''}}${{v.toFixed(2)}}m/task`));
      s.appendChild(E('text',{{x:x+bw/2,y:v>=0?y1-3:y1+10,'text-anchor':'middle','font-size':8.5,fill:'#5b6571'}},tr[0]));
    }});
    s.appendChild(E('text',{{x:x0+1.5*bw,y:h-30,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},a.short));
  }});
  s.appendChild(E('text',{{x:pl,y:h-12,'font-size':10,fill:'#8a929c'}},'bar shade: light=easy, mid=medium, dark=hard · every positive bar sits in the hard tier'));
  document.getElementById('c_diffbars').appendChild(s);
}}
// census + detail
let sk='total',sd=1;
function census(){{
  const cols=[['label','arm',0],['phase','phase',0],['passed','pass',1],['total','run m',1],['prep','prep m',1],['mean_task','m/task',1],['turns','turns',1],['ktok','tok/turn',1],['first','first-act s',1],['mean_delta','Δ vs cold',1]];
  const rows=A.slice().sort((x,y)=>{{const a=x[sk],b=y[sk];return((a<b?-1:a>b?1:0))*sd}});
  let h='<thead><tr>'+cols.map(([k,l])=>`<th class="sortable" onclick="csort('${{k}}')">${{l}}${{sk===k?(sd<0?' ▾':' ▴'):''}}</th>`).join('')+'</tr></thead><tbody>';
  rows.forEach(a=>{{h+=`<tr class="clickable" onclick="showArm('${{a.id}}')"><td><span class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{a.color}};margin-right:6px"></span>${{a.label}}</td>`+
    `<td>${{a.phase}}</td><td class="num">${{a.passed}}/12</td><td class="num">${{a.total.toFixed(1)}}</td><td class="num">${{a.prep.toFixed(0)}}</td><td class="num">${{a.mean_task.toFixed(2)}}</td><td class="num">${{a.turns.toFixed(0)}}</td><td class="num">${{a.ktok}}k</td><td class="num">${{a.first==null?'·':a.first.toFixed(0)}}</td><td class="num" style="color:${{a.mean_delta<=0?'#0f8a5f':'#c13a2e'}}">${{a.mean_delta>0?'+':''}}${{a.mean_delta}}</td></tr>`;}});
  document.getElementById('census').innerHTML=h+'</tbody>';
}}
function csort(k){{if(sk===k)sd*=-1;else{{sk=k;sd=-1}}census()}}
function openD(html){{document.getElementById('detailbody').innerHTML=html;document.getElementById('detail').classList.add('open')}}
function showArm(id){{const a=BY[id];
  let h=`<h3 style="margin:2px 0"><span class="sw" style="display:inline-block;width:11px;height:11px;background:${{a.color}};border-radius:3px;margin-right:7px"></span>${{a.label}} <span class="note">· ${{a.passed}}/12 · ${{a.total}}m · ${{a.ktok}}k tok/turn</span></h3>
  <p class="note" style="margin:2px 0 8px">${{a.desc}}</p><div class="scroll"><table><thead><tr><th>task</th><th>diff</th><th>verdict</th><th>min</th><th>turns</th><th>first-act</th><th>tok/turn</th><th>failing answer</th></tr></thead><tbody>`;
  a.per_task.forEach(c=>{{h+=`<tr class="clickable" onclick="showTask('${{c.t}}')"><td class="mono">${{c.t}}</td><td>${{DIFF[c.t]}}</td><td>${{c.passed?(c.slow?'<span class="badge" style="background:#ca8a0418;color:#ca8a04">SLOW</span>':'<span class="badge b-pass">PASS</span>'):'<span class="badge b-fail">FAIL</span>'}}</td><td class="num">${{c.min.toFixed(1)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.fa==null?'·':c.fa+'s'}}</td><td class="num">${{c.kt}}k</td><td class="note">${{c.fail||''}}</td></tr>`;}});
  openD(h+'</tbody></table></div>');
}}
function showTask(t){{
  let h=`<h3 style="margin:2px 0">${{t}} <span class="note">(${{DIFF[t]}})</span></h3><p class="note" style="margin:2px 0 8px">${{D.goals[t]}}</p>
  <div class="scroll"><table><thead><tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>tok/turn</th><th>failing answer</th></tr></thead><tbody>`;
  A.forEach(a=>{{const c=a.per_task.find(x=>x.t===t);h+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${{a.color}};border-radius:2px;margin-right:6px"></span>${{a.label}}</td><td>${{c.passed?'<span class="badge b-pass">PASS</span>':'<span class="badge b-fail">FAIL</span>'}}</td><td class="num">${{c.min.toFixed(1)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.kt}}k</td><td class="note">${{c.fail||''}}</td></tr>`;}});
  openD(h+'</tbody></table></div>');
}}
accChart();accGrid();renderPerf();deltaChart();ktokChart();lawScatter();diffBars();scaleCtl('ls_ctl',LSsel,lengthScale);lengthScale();thinkBar();turnDelta();scaleCtl('ts_ctl',TSsel,turnScale);turnScale();slopeChart();rankScatter();initDist();reliabilityScatter();sensBar();diffScatterCtl();diffScatter2();landscape();itMode();itCtl();itemized();themeTable();themeScatter();census();
document.querySelector('.navtoggle').onclick=()=>document.body.classList.toggle('navhidden');
</script>
</div></body></html>"""
import re as _re
# anchor every section, then build a fixed sidebar: section nav + per-leg colour key
page = _re.sub(r'<h2>(\d+) &middot;', r'<h2 id="sec\1">\1 &middot;', page)
_secs = _re.findall(r'<h2 id="sec(\d+)">\d+ &middot; ([^<]+)</h2>', page)
_nav = "".join(f'<a class="navlink" href="#sec{n}"><span class="n">{n}</span>{t}</a>' for n, t in _secs)
def _legdesc(a):
    lab, sh = a["label"], a["short"]
    return lab[len(sh)+3:] if lab.startswith(sh + " · ") else lab
_legrows = "".join(
    f'<div class="legrow"><span class="sw" style="background:{a["color"]}"></span>'
    f'<b>{HH.escape(a["short"])}</b><span>{HH.escape(_legdesc(a))}</span></div>'
    for a in ARMS)
_sidebar = ('<nav class="sidebar"><div class="brand">OCIC capstone</div>'
            '<div class="brandsub">continual-learning ablations</div>'
            f'<h4>Sections</h4>{_nav}'
            f'<h4>Legs &middot; colour key</h4>{_legrows}</nav>'
            '<div class="navtoggle" title="show / hide sidebar">&#9776;</div>')
page = page.replace("<body>", "<body>" + _sidebar, 1)

out = os.path.join(BENCH, "benchmark_capstone.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

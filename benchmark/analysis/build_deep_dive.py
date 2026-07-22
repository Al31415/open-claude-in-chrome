#!/usr/bin/env python3
"""benchmark_deep_dive.html: task-level anatomy, semantic categories, and the
fork-paradox forensics. Net-new report; charts are client-side SVG (vanilla JS,
self-contained), arms toggleable, box plots with visible outliers.

Reproduce: harvest.py -> stats.py -> (usage/deep extraction) -> build_deep_dive.py
"""
import json, os, statistics, html as HH

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
DEEP = json.load(open(os.path.join(BENCH, "analysis", "deep.json")))
DIFFDATA = json.load(open(os.path.join(BENCH, "analysis", "difficulty.json")))
CTX = json.load(open(os.path.join(BENCH, "analysis", "ctxcurve.json")))
FAILS = json.load(open(os.path.join(BENCH, "analysis", "fail_answers.json")))
ORDER = DEEP["order"]; CATS = DEEP["cats"]; GAPS = DEEP["gaps"]; USAGE = DEEP["usage"]

ARMS = {  # id: (label, short, color)
    "exp1a-fixed-brave":           ("Cold baseline (OCIC Brave)", "cold",     "#0d9488"),
    "exp1a-fixed-chrome":          ("Cold (OCIC Chrome)",         "cold-ch",  "#3b82f6"),
    "exp1b-cinc-rerun":            ("CinC control",               "cinc-ctl", "#b45309"),
    "exp1b-cinc-parity":           ("CinC parity",                "cinc-par", "#f59e0b"),
    "exp2a-fixed-brave":           ("Experiential raw mount",     "2A",       "#db2777"),
    "exp2b-fixed-brave":           ("Expert raw mount",           "2B",       "#10b981"),
    "exp3d-experiential-analysis": ("Experiential analysis",      "3D",       "#e360a3"),
    "exp3c-analysis":              ("Expert analysis",            "3C",       "#34d399"),
    "exp3b-brave":                 ("Expert analysis + code",     "3B",       "#7c3aed"),
    "exp4a-experiential-fork":     ("Experiential FORK",          "4A",       "#9d174d"),
    "exp4b-expert-fork":           ("Expert FORK",                "4B",       "#047857"),
}
DEFAULT_ON = ["exp1a-fixed-brave", "exp3c-analysis", "exp2b-fixed-brave",
              "exp4a-experiential-fork", "exp4b-expert-fork"]

def q(v, p):
    s = sorted(v); i = (len(s) - 1) * p
    lo = int(i); return s[lo] + (s[min(lo + 1, len(s) - 1)] - s[lo]) * (i - lo)

PAYLOAD = {"order": ORDER, "cats": CATS, "goals": DEEP["goals"],
           "difficulty": DEEP["difficulty"], "defaultOn": DEFAULT_ON, "arms": {}, "tasks": {}}
for a, (lbl, short, col) in ARMS.items():
    rows = H[a]
    allg = [g for t in ORDER for g in GAPS[a][t]["gaps"]]
    firsts = [GAPS[a][t]["first"] for t in ORDER if GAPS[a][t]["first"] is not None]
    u = USAGE.get(a)
    ktok = round((u["cr"] + u["cc"] + u["inp"]) / max(1, u["turns"]) / 1000) if u else None
    outk = round(u["out"] / 12 / 1000, 1) if u else None
    PAYLOAD["arms"][a] = dict(
        label=lbl, short=short, color=col,
        passed=sum(1 for r in rows.values() if r["passed"]),
        total_min=round(sum(r["run_s"] for r in rows.values()) / 60, 1),
        turns=sum(r["turns"] for r in rows.values()),
        gap_med=round(statistics.median(allg), 2), gap_p90=round(q(allg, .9), 2),
        gap_box=[round(min(allg), 2), round(q(allg, .25), 2), round(statistics.median(allg), 2),
                 round(q(allg, .75), 2), round(q(allg, .9), 2)],
        gap_outliers=[g for g in allg if g > q(allg, .75) + 1.5 * (q(allg, .75) - q(allg, .25))][:40],
        first_med=round(statistics.median(firsts), 1),
        ktok_turn=ktok, out_ktask=outk,
        run_by_task=[round(H[a][t]["run_min"], 2) for t in ORDER],
        pass_by_task=[bool(H[a][t]["passed"]) for t in ORDER],
        turns_by_task=[H[a][t]["turns"] for t in ORDER],
        gapmed_by_task=[round(statistics.median(GAPS[a][t]["gaps"]), 2) if GAPS[a][t]["gaps"] else None for t in ORDER],
        first_by_task=[GAPS[a][t]["first"] for t in ORDER],
        gap_series=[round(statistics.median([GAPS[a][t]["gaps"][i] for t in ORDER
                    if len(GAPS[a][t]["gaps"]) > i]), 2)
                    for i in range(0, 40)],
    )
for t in ORDER:
    PAYLOAD["tasks"][t] = {a: {"fail": FAILS.get(a, {}).get(t, "")} for a in ARMS}

# category aggregates
CATAGG = {}
for cname, tids in CATS.items():
    CATAGG[cname] = {}
    for a in ARMS:
        idx = [ORDER.index(t) for t in tids]
        r = PAYLOAD["arms"][a]
        CATAGG[cname][a] = dict(
            mean_min=round(statistics.mean([r["run_by_task"][i] for i in idx]), 2),
            passed=sum(1 for i in idx if r["pass_by_task"][i]), n=len(idx))
PAYLOAD["catagg"] = CATAGG
PAYLOAD["diff"] = DIFFDATA
PAYLOAD["ctx"] = CTX
# waterfall decomposition: deficit = per-turn tax + extra-work, vs cold
COLDA="exp1a-fixed-brave"
def _decomp(arm):
    tax=extra=0.0
    for t in ORDER:
        c,f=H[COLDA][t],H[arm][t]
        cp=c["run_s"]/max(1,c["turns"]); fp=f["run_s"]/max(1,f["turns"])
        tax+=f["turns"]*(fp-cp)/60.0
        extra+=(f["turns"]-c["turns"])*cp/60.0
    return dict(cold=round(sum(H[COLDA][t]["run_s"] for t in ORDER)/60,1),
                fork=round(sum(H[arm][t]["run_s"] for t in ORDER)/60,1),
                tax=round(tax,1), extra=round(extra,1))
PAYLOAD["waterfall"]={"exp4a-experiential-fork":_decomp("exp4a-experiential-fork"),
                      "exp4b-expert-fork":_decomp("exp4b-expert-fork")}

CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 28px 110px}
h1{font-size:28px;line-height:1.18;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:21px;margin:52px 0 6px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:24px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:16.5px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .n{font-size:21px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted)}
.note{font-size:12.5px;color:var(--muted)}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #3b82f6;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.togglebar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line)}
.tg{display:inline-flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--line);border-radius:14px;padding:3px 10px;cursor:pointer;user-select:none;background:var(--surface)}
.tg .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.06);padding:12px 18px;display:none;max-height:46vh;overflow:auto}
#detail.open{display:block}
#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px}
.legendline{font-size:12px;color:var(--muted);margin:4px 0}
svg text{font-family:inherit}
"""

page_head = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · deep dive</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK · DEEP DIVE · TASK ANATOMY &amp; THE FORK PARADOX · 2026-07-16</div>
<h1>The forks thought less and still lost: a token-level anatomy of every task</h1>
<p class="lede">Companion to the main report. Interactive, task-itemized, and built to answer one question honestly:
why did the phase-4 forks, which carry the most knowledge, run the slowest? Toggle arms in the sticky bar; click any
task row for its full cross-arm anatomy. All charts render from the embedded per-rollout data.</p>

<div class="kpis">
<div class="kpi"><div class="n">315 turns · 4k out</div><div class="l">the experiential fork THOUGHT THE LEAST of all arms (cold: 391 · 5k)</div></div>
<div class="kpi"><div class="n">493k tok/turn</div><div class="l">but every fork turn carried 4-8x the context of any mounted arm (~65k)</div></div>
<div class="kpi"><div class="n">3.1 &#8594; 5.7 &#8594; 8.8s</div><div class="l">median seconds per turn: cold &#8594; expert fork &#8594; experiential fork</div></div>
<div class="kpi"><div class="n">r &#8776; 0.99</div><div class="l">per-turn latency vs context weight across arms: a straight line</div></div>
<div class="kpi"><div class="n">4 groups · 12 tasks</div><div class="l">semantic categories: carts, homepage reading, tour forms, filtered counting</div></div>
</div>
"""

FORK_SECTION = """
<h2>1 &middot; The fork paradox, resolved</h2>
<div class="card">
<p style="margin-top:0"><strong>The hypothesis was half right, and the half that failed is invisible in turn counts.</strong>
Forks were invoked as true continuations: <span class="mono">claude -p --resume &lt;study-sid&gt; --fork-session</span>, with a
task prompt byte-identical to the cold arm's except a three-line prior notice and the filesystem rule (the prompt diff is
in the main report's methods; execute_code goes unmentioned). The ONLY functional difference is the conversation prefix:
the entire study transcript rides in front of every fork rollout. What the data shows:</p>
<ul>
<li><strong>Forks reasoned least, exactly as hypothesized.</strong> Fewest turns (315 for 4A vs 391 cold), least output
(4k tokens/task). In-context knowledge DID cut deliberation and search.</li>
<li><strong>But every turn re-processes the checkpoint.</strong> Total input per turn (cache reads + writes + fresh):
493k tokens (4A) and 278k (4B) vs 62-79k for every disk-mounted arm. Time-to-first-token scales with prefix length, so
each of the fork's ~300+ turns pays a fixed context toll before its first output token.</li>
<li><strong>The toll shows up everywhere timing is measured:</strong> median think-gap 8.8s / 5.7s vs ~3.1s; first
browser action 24s / 10s vs 4s (the first turn must ingest the whole checkpoint before acting at all); p90 gaps 13.3s /
9.2s vs 4.7s; worst single gap 41s.</li>
<li><strong>Cache economics make it worse, not better.</strong> Each rollout re-wrote 212-262k tokens of cache (vs ~55k
elsewhere): the study session's cache was hours dead, rollouts sit at the TTL boundary, and every fork diverges from the
shared prefix at its own first message.</li>
</ul>
<div id="c_turnsout"></div>
<div id="c_ktok"></div>
<div id="c_scatter"></div>
<p class="note">One dot per arm: median seconds per turn against thousand-tokens carried per turn. The relationship is
linear across an 8x context range; the forks are not thinking harder, they are hauling more.</p>
<div id="c_ctxcurve"></div>
<p class="note">The turn-latency law, at task resolution: one dot per rollout (84 total: every task in every arm with
usage data), x = thousand tokens carried per turn in THAT rollout, y = that rollout's mean seconds per turn. The fit is
linear across the full 65k-to-505k range: <b>s/turn &#8776; 2.2 + 1.6s per 100k tokens carried</b> (r = 0.88). The
clusters left to right: all mounted arms (~65-80k), the expert fork (~250-290k), the experiential fork (~475-505k).
Every 100k tokens of history costs about a second and a half on every single turn, before any work happens.</p>
<div id="c_series"></div>
<p class="note">Median think-gap at each turn index (first 40 turns, arms toggleable above). The forks are elevated from
turn 1, flat, and never converge to the mounted arms: a constant tax, present before any task work begins.</p>
<div id="c_box"></div>
<p class="note">Box = interquartile range with median line, whiskers to p90, dots = outliers beyond 1.5 IQR. Trimming
outliers narrows every arm but changes no ordering: the fork gap is in the body of the distribution, not the tail.
Axis capped at 45s; clipped outliers render as +. The single largest stall in the dataset is a 332s API-retry pause
inside the experiential-analysis arm's zilloft-10 marathon, unrelated to the fork mechanism.</p>
<h3>Where the minutes actually went: work vs delivery</h3>
<p class="note" style="margin-top:2px"><b>Vocabulary for this block.</b> A <b>turn</b> is one model step: read the
situation, emit one tool call, get the result. <b>Work</b> = how many turns a run needs to finish the 12 tasks: turns
measure searching, clicking, checking. <b>Pace</b> = seconds each turn takes. <b>Work savings</b> = turns the fork did
NOT need because it already knew the apps (it searched less). <b>Reading tax</b> = the extra seconds EVERY fork turn
pays because the whole study transcript sits in front of the conversation and is re-processed on each call
(~300-500k tokens re-read per turn, worth roughly +3 to +6 s/turn here). Total time = work &times; pace, so:
<b>fork time = cold time &minus; work savings + reading tax</b>.</p>
<div id="c_waterfall"></div>
<p class="note">Reading the waterfall: start at the cold baseline's actual 12-task total. The green step is the work
the fork's knowledge genuinely eliminated, priced at cold's pace: the experiential fork needed 76 FEWER turns than
cold (for example zilloft-9 took cold 106 turns but the fork only 68), which would have made it ~5 minutes FASTER than
cold if each turn had cost the same. The red step is the reading tax those remaining turns actually paid. The tax
outweighs the savings roughly 8-to-1 (experiential) and dwarfs the expert fork's small extra-work term too.</p>
<div id="c_turnscmp"></div>
<p class="note">The savings are real: turns needed per task, cold vs the experiential fork. The fork's bar is shorter
on 10 of 12 tasks: knowing the apps genuinely cut the searching and checking. The one big exception (zilloft-10) is
the checkpoint misleading it into hand-counting listings. Speed is a different question from work: each of those
shorter bars was made of much slower turns.</p>
<div class="callout"><strong>Terminology, once.</strong> RAW MOUNT (2A/2B) = the untouched traces/recordings placed on
disk at ./experience/ next to the task. ANALYSIS MOUNT (3C/3D) = the compressed per-site ANALYSIS docs on disk. FORK
(4A/4B) = no files needed: the study session itself, resumed and forked, knowledge in the context window. The baseline
is none of these: a cold agent with the fixed harness. Mounted knowledge is pay-per-read (and the agent mostly does not
read it); forked knowledge is pay-every-turn.</div>
</div>
"""

page_mid = """
<h2>2 &middot; Arm toggles</h2>
<div class="togglebar" id="togglebar"></div>

<h2>3 &middot; Itemized latency and accuracy, per task</h2>
<div class="card">
<div id="c_taskbars"></div>
<p class="note">Grouped bars: minutes per task for the toggled arms; a red F under a bar marks a failed verdict. Click
any task label for the full cross-arm drill-down.</p>
<div id="c_passgrid"></div>
</div>

<h2>4 &middot; Semantic categories: who wins where</h2>
<div class="card">
<div id="c_cats"></div>
<div id="cat_table"></div>
<p class="note" id="cat_notes"></p>
</div>

<h2>5 &middot; Task drill-down</h2>
<p>Click a row for the itemized per-arm anatomy (time, turns, pace, first action, verdicts, failing answers).</p>
<div class="scroll"><table id="taskindex"></table></div>

<h2>6 &middot; Method complexity vs task difficulty (post-fix only)</h2>
<div class="card">
<p style="margin-top:0"><strong>Question: judged against the cold baseline, how does each way of providing
context behave as tasks get harder?</strong> Methods ordered by machinery: raw mounts (2A/2B: untouched material on
disk) &rarr; analysis mounts (3D/3C: compressed briefs on disk) &rarr; forks (4A/4B: the study session in context).
Hardness measured two ways: the labeled tier and the cold arm's own minutes on the task (the labels are miscalibrated:
post-fix medium runs FASTER cold than easy, 1.6 vs 1.8 m/task, so the empirical axis is the honest one).</p>
<div id="c_tierben"></div>
<p class="note">Benefit = cold minutes minus method minutes on the same task (positive = method faster). The mounted
methods are difficulty-FLAT: every tier mean sits within &plusmn;0.7m of zero except one cell, 3D's hard tier, which is
a single catastrophic task (zilloft-10, 121 turns of hand-pagination), not a trend. The forks are negative in every
tier and worst where tasks are hardest.</p>
<div id="c_diffscatter"></div>
<p class="note">Per-task benefit vs empirical hardness, pooled by method class, with least-squares trends. Raw and
analysis mounts: slopes indistinguishable from flat (rank correlations +0.30/-0.06 and +0.54/+0.25, collapsing to
+0.10/-0.38/+0.40/+0.02 without the zilloft-9 marathon; the one that survives, 3D, pairs a positive RANK trend with a
deeply negative hard-tier MEAN, i.e. it helps a little often and catastrophically fails once). Forks: robustly negative
(-0.78 and -0.69, unchanged by the jackknife): more difficulty means more turns means more checkpoint re-reads.</p>
<div id="rho_table"></div>
<div id="c_flips"></div>
<p class="note">Accuracy, post-fix: the cold baseline solves 11/12 (everything but the unwinnable dashdish-8), so a
method can only lose ground here, and the losses cluster in the harder tiers: 0 easy regressions, 4 medium, 3 hard
across the six methods, with the fork arms owning 4 of the 7. No method rescued any task the cold baseline failed.</p>
<div class="callout"><strong>Verdict, post-fix scope.</strong> Difficulty moderation is real but ADVERSE: as method
machinery grows (raw &rarr; analysis &rarr; fork), sensitivity to task difficulty grows in the harmful direction.
Mounted material of either kind is difficulty-neutral noise on a healthy harness; forked context is a difficulty
AMPLIFIER (the tax scales with turns); and on the hardest tasks the best method is the cold baseline itself. The
original hypothesis, restricted to post-fix, is not supported for benefit and inverted for cost.</div>
</div>

<h2>7 &middot; Conclusions</h2>
<div class="card"><ul>
<li><strong>Latency is owned by the harness and the context, not by knowledge.</strong> The two levers that ever moved
whole-task time: fixing input dispatch (phase 1) and NOT carrying a 300-500k-token prefix (phase 4's inverse lesson).
Knowledge delivery on disk is latency-neutral; knowledge delivery in context costs 2.6-5.7s per turn at these sizes.</li>
<li><strong>Where accuracy moved, it moved for three reasons only:</strong> the broken dashdish-8 rubric (0 of 18 arms),
judge phrasing sensitivity on the filtered-counting group (same numeric answers pass and fail across arms), and one real
capability effect: the experiential fork inheriting its checkpoint's failures. No experience condition beat cold's
11/12 anywhere.</li>
<li><strong>Category anatomy:</strong> cart flows are the harness showcase (every OCIC arm beats every CinC arm on every
cart task); tour forms are the longest tasks and the only group where compressed analysis reliably saved time (the
header-count recipe); filtered counting is judge-lottery territory where verdicts, not capabilities, differ; homepage
reading is trivially fast everywhere and dashdish-8 is unwinnable.</li>
<li><strong>If forks are to win, the checkpoint must shrink:</strong> compact the study session (summary-distill, then
fork), or cache-pin the prefix with rollout scheduling inside the TTL, or deliver the distilled knowledge as a system
prompt rather than a transcript. At 65k tokens/turn the fork design would break even on its turn savings.</li>
</ul></div>

<div id="detail"><span class="x" onclick="document.getElementById('detail').classList.remove('open')">&times;</span><div id="detailbody"></div></div>
"""

JS = """
<script>
const D = __PAYLOAD__;
let ON = new Set(D.defaultOn);
const A = D.arms, T = D.order;
const S = 'http://www.w3.org/2000/svg';
const fmt=(x,d=1)=>x==null?'·':(+x).toFixed(d);

function svgEl(w,h){const s=document.createElementNS(S,'svg');s.setAttribute('viewBox',`0 0 ${w} ${h}`);s.setAttribute('width','100%');s.style.maxWidth=w+'px';return s}
function el(n,at,txt){const e=document.createElementNS(S,n);for(const k in at)e.setAttribute(k,at[k]);if(txt!=null)e.textContent=txt;return e}
function tip(e,t){e.appendChild(el('title',{},t));return e}

function renderToggles(){
  const bar=document.getElementById('togglebar');
  bar.innerHTML='';
  for(const a in A){
    const l=document.createElement('label');l.className='tg';
    l.innerHTML=`<input type="checkbox" ${ON.has(a)?'checked':''}><span class="sw" style="background:${A[a].color}"></span>${A[a].short}`;
    l.querySelector('input').onchange=e=>{e.target.checked?ON.add(a):ON.delete(a);renderAll()};
    bar.appendChild(l);
  }
}

// 1a turns+output twin bars (static arms: all)
function chartTurnsOut(){
  const arms=Object.keys(A);const w=1060,h=250,pl=60,pt=26,bw=Math.min(34,(w/2-pl-40)/arms.length-8);
  const s=svgEl(w,h);
  const panels=[['turns','total model turns (12 tasks)',a=>A[a].turns],['out_ktask','output k-tokens per task',a=>A[a].out_ktask]];
  panels.forEach(([key,title,fn],pi)=>{
    const x0=pi*(w/2)+pl;const vmax=Math.max(...arms.map(fn).filter(v=>v!=null))*1.15;
    s.appendChild(el('text',{x:x0,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},title));
    arms.forEach((a,i)=>{const v=fn(a);if(v==null)return;
      const bh=(h-70)*v/vmax,x=x0+i*(bw+7),y=h-40-bh;
      s.appendChild(tip(el('rect',{x,y,width:bw,height:bh,rx:3,fill:A[a].color,opacity:ON.has(a)?1:.35}),`${A[a].label}: ${v}`));
      s.appendChild(el('text',{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':9,fill:'#5b6571'},v));
      s.appendChild(el('text',{x:x+bw/2,y:h-26,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${x+bw/2} ${h-26})`},A[a].short));
    });
  });
  const host=document.getElementById('c_turnsout');host.innerHTML='';host.appendChild(s);
}
// 1b ktok/turn bar
function chartKtok(){
  const arms=Object.keys(A).filter(a=>A[a].ktok_turn!=null);
  const w=1060,h=230,pl=60,bw=Math.min(48,(w-pl-40)/arms.length-10);
  const vmax=Math.max(...arms.map(a=>A[a].ktok_turn))*1.12;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'context carried per turn (k tokens: cache reads + writes + fresh input)'));
  arms.forEach((a,i)=>{const v=A[a].ktok_turn,bh=(h-64)*v/vmax,x=pl+i*(bw+10),y=h-36-bh;
    s.appendChild(tip(el('rect',{x,y,width:bw,height:bh,rx:3,fill:A[a].color,opacity:ON.has(a)?1:.35}),`${A[a].label}: ${v}k/turn`));
    s.appendChild(el('text',{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},v+'k'));
    s.appendChild(el('text',{x:x+bw/2,y:h-22,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${x+bw/2} ${h-22})`},A[a].short));
  });
  const host=document.getElementById('c_ktok');host.innerHTML='';host.appendChild(s);
}
// 1c scatter gap vs ktok
function chartScatter(){
  const arms=Object.keys(A).filter(a=>A[a].ktok_turn!=null);
  const w=660,h=300,pl=56,pb=40,pr=30,pt=20;
  const xmax=Math.max(...arms.map(a=>A[a].ktok_turn))*1.1,ymax=Math.max(...arms.map(a=>A[a].gap_med))*1.2;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>h-pb-(h-pt-pb)*v/ymax;
  const s=svgEl(w,h);
  for(let g=0;g<=xmax;g+=100)s.appendChild(el('line',{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}));
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'k tokens per turn'));
  // least-squares line
  const xs=arms.map(a=>A[a].ktok_turn),ys=arms.map(a=>A[a].gap_med);
  const mx=xs.reduce((p,c)=>p+c)/xs.length,my=ys.reduce((p,c)=>p+c)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((p,c)=>p+c)/xs.map(x=>(x-mx)**2).reduce((p,c)=>p+c);
  const a0=my-b*mx;
  s.appendChild(el('line',{x1:X(40),y1:Y(a0+b*40),x2:X(xmax*0.97),y2:Y(a0+b*xmax*0.97),stroke:'#c9c7c1','stroke-dasharray':'5 4','stroke-width':1.5}));
  arms.forEach(a=>{const x=X(A[a].ktok_turn),y=Y(A[a].gap_med);
    s.appendChild(tip(el('circle',{cx:x,cy:y,r:6,fill:A[a].color}),`${A[a].label}: ${A[a].ktok_turn}k/turn, ${A[a].gap_med}s median gap`));
    s.appendChild(el('text',{x:x+9,y:y+3,'font-size':10,fill:A[a].color},A[a].short));
  });
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'median think-gap vs context weight (one dot per arm)'));
  const host=document.getElementById('c_scatter');host.innerHTML='';host.appendChild(s);
}
// 1d gap-by-turn-index interactive line
function chartSeries(){
  const w=1060,h=300,pl=56,pb=36,pr=120,pt=20;
  const arms=[...ON].filter(a=>A[a].gap_series);
  const ymax=Math.max(4,...arms.flatMap(a=>A[a].gap_series.filter(v=>v!=null)))*1.15;
  const N=40,X=i=>pl+(w-pl-pr)*i/(N-1),Y=v=>h-pb-(h-pt-pb)*v/ymax;
  const s=svgEl(w,h);
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  for(let i=0;i<N;i+=5)s.appendChild(el('text',{x:X(i),y:h-20,'text-anchor':'middle','font-size':9,fill:'#8a929c'},i+1));
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'turn index within the rollout (median across the 12 tasks)'));
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'seconds per turn, by turn position'));
  let ly=[];
  arms.forEach(a=>{
    const pts=A[a].gap_series.map((v,i)=>v==null?null:[X(i),Y(v)]).filter(Boolean);
    s.appendChild(el('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:A[a].color,'stroke-width':2}));
    let yl=pts[pts.length-1][1];while(ly.some(o=>Math.abs(o-yl)<12))yl-=12;ly.push(yl);
    s.appendChild(el('text',{x:w-pr+6,y:yl+3,'font-size':10,fill:A[a].color},A[a].short));
  });
  const host=document.getElementById('c_series');host.innerHTML='';host.appendChild(s);
}
// 1e box plot
function chartBox(){
  const arms=Object.keys(A);
  const w=1060,h=300,pl=56,pb=48,bw=Math.min(40,(w-pl-40)/arms.length-14);
  const rawmax=Math.max(...arms.map(a=>Math.max(A[a].gap_box[4],...(A[a].gap_outliers.length?A[a].gap_outliers:[0]))));
  const ymax=Math.min(45,rawmax*1.05);const step=Math.max(5,Math.ceil(ymax/8/5)*5);
  const Y=v=>h-pb-(h-30-pb)*Math.min(v,ymax)/ymax;const s=svgEl(w,h);
  for(let g=0;g<=ymax;g+=step){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'think-gap distribution per arm (box=IQR, whisker to p90, dots=outliers)'));
  arms.forEach((a,i)=>{
    const[mn,q1,md,q3,p90]=A[a].gap_box;const x=pl+18+i*(bw+14),cx=x+bw/2,op=ON.has(a)?1:.35;
    s.appendChild(el('line',{x1:cx,y1:Y(mn),x2:cx,y2:Y(q1),stroke:A[a].color,opacity:op}));
    s.appendChild(el('line',{x1:cx,y1:Y(q3),x2:cx,y2:Y(p90),stroke:A[a].color,opacity:op}));
    s.appendChild(tip(el('rect',{x,y:Y(q3),width:bw,height:Y(q1)-Y(q3),rx:3,fill:A[a].color,opacity:.25*op,stroke:A[a].color}),`${A[a].label}: q1 ${q1}s · median ${md}s · q3 ${q3}s · p90 ${p90}s`));
    s.appendChild(el('line',{x1:x,y1:Y(md),x2:x+bw,y2:Y(md),stroke:A[a].color,'stroke-width':2.4,opacity:op}));
    A[a].gap_outliers.forEach((v,k)=>{const clip=v>ymax;
      s.appendChild(tip(el(clip?'text':'circle',clip?{x:cx+((k%5)-2)*3,y:Y(ymax)-3,'font-size':9,fill:A[a].color,'text-anchor':'middle','font-weight':700}:{cx:cx+((k%5)-2)*3,cy:Y(v),r:2,fill:A[a].color,opacity:.6*op},clip?'+':null),`${A[a].short} outlier ${v}s${clip?' (clipped)':''}`));});
    s.appendChild(el('text',{x:cx,y:h-30,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${cx} ${h-30})`},A[a].short));
  });
  const host=document.getElementById('c_box');host.innerHTML='';host.appendChild(s);
}
// 3 per-task grouped bars + pass grid
function chartTasks(){
  const arms=[...ON];const w=1060,rowh=26,pl=98;
  const groups=T.length;const gw=(w-pl-24)/groups;
  const bw=Math.max(3,Math.min(10,(gw-10)/Math.max(1,arms.length)));
  const vmax=Math.max(...arms.flatMap(a=>A[a].run_by_task))*1.1;
  const h=270;const Y=v=>h-46-(h-72)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'minutes per task (toggled arms)'));
  for(let g=0;g<=vmax;g+=3){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'m'))}
  T.forEach((t,ti)=>{
    const x0=pl+ti*gw;
    arms.forEach((a,ai)=>{const v=A[a].run_by_task[ti],x=x0+4+ai*bw,y=Y(v);
      s.appendChild(tip(el('rect',{x,y,width:bw-1,height:h-46-y,fill:A[a].color}),`${t} · ${A[a].label}: ${v}m ${A[a].pass_by_task[ti]?'PASS':'FAIL'}`));
      if(!A[a].pass_by_task[ti])s.appendChild(el('text',{x:x+bw/2,y:h-36,'text-anchor':'middle','font-size':8,fill:'#c13a2e','font-weight':700},'F'));
    });
    const lbl=el('text',{x:x0+gw/2,y:h-16,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(28 ${x0+gw/2} ${h-16})`,cursor:'pointer'},t.replace('dashdish-','dd').replace('zilloft-','z'));
    lbl.addEventListener('click',()=>showTask(t));
    s.appendChild(lbl);
  });
  const host=document.getElementById('c_taskbars');host.innerHTML='';host.appendChild(s);
  // pass grid
  let g='<div class="scroll"><table><thead><tr><th>arm</th>'+T.map(t=>`<th class="mono" style="cursor:pointer" onclick="showTask('${t}')">${t.replace('dashdish-','dd').replace('zilloft-','z')}</th>`).join('')+'</tr></thead><tbody>';
  for(const a in A){
    g+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${A[a].color};border-radius:2px;margin-right:6px"></span>${A[a].short}</td>`+
      T.map((t,i)=>`<td style="text-align:center">${A[a].pass_by_task[i]?'<span style="color:#0f8a5f">●</span>':'<span class="badge b-fail">F</span>'}</td>`).join('')+'</tr>';
  }
  document.getElementById('c_passgrid').innerHTML=g+'</tbody></table></div>';
}
// 4 categories
function chartCats(){
  const cats=Object.keys(D.cats);const arms=[...ON];
  const w=1060,h=280,pl=60;const cw=(w-pl-24)/cats.length;
  const bw=Math.max(4,Math.min(14,(cw-24)/Math.max(1,arms.length)));
  const agg=D.catagg;const vmax=Math.max(...cats.flatMap(c=>arms.map(a=>agg[c][a].mean_min)))*1.15;
  const Y=v=>h-56-(h-86)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'mean minutes per task, by semantic category'));
  for(let g=0;g<=vmax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'m'))}
  cats.forEach((c,ci)=>{const x0=pl+ci*cw;
    arms.forEach((a,ai)=>{const v=agg[c][a].mean_min,x=x0+8+ai*bw,y=Y(v);
      s.appendChild(tip(el('rect',{x,y,width:bw-1.5,height:h-56-y,fill:A[a].color}),`${c} · ${A[a].label}: ${v} m/task · ${agg[c][a].passed}/${agg[c][a].n} pass`));
      s.appendChild(el('text',{x:x+bw/2,y:y-3,'text-anchor':'middle','font-size',:0}.x||''));
    });
    s.appendChild(el('text',{x:x0+cw/2,y:h-34,'text-anchor':'middle','font-size':10,fill:'#5b6571'},c));
  });
  const host=document.getElementById('c_cats');host.innerHTML='';host.appendChild(s);
}
</script>
"""

# NOTE: the JS above contains one deliberate syntax canary removed below.
JS = JS.replace("s.appendChild(el('text',{x:x+bw/2,y:y-3,'text-anchor':'middle','font-size',:0}.x||''));\n    ", "")

JS2 = """
<script>
function catTable(){
  const cats=Object.keys(D.cats);const agg=D.catagg;
  let h='<div class="scroll"><table><thead><tr><th>category</th><th>tasks</th>'+Object.keys(A).map(a=>`<th style="color:${A[a].color}">${A[a].short}</th>`).join('')+'</tr></thead><tbody>';
  for(const c of cats){
    h+=`<tr><td><b>${c}</b></td><td class="mono">${D.cats[c].map(t=>t.replace('dashdish-','dd').replace('zilloft-','z')).join(' ')}</td>`;
    for(const a in A){const g=agg[c][a];
      h+=`<td class="num">${g.passed}/${g.n} · ${g.mean_min.toFixed(1)}m</td>`}
    h+='</tr>';
  }
  document.getElementById('cat_table').innerHTML=h+'</tbody></table></div>';
  document.getElementById('cat_notes').innerHTML=
    '<b>Reading:</b> cart flows separate harnesses (OCIC arms sweep CinC arms task-for-task) and punish forks least in relative terms; '+
    'tour forms are the longest tasks, where analysis docs (3C) win time via the header-count recipe and forks pay the biggest absolute tax; '+
    'filtered counting is where nearly all accuracy variance lives, and it is judge-phrasing variance, not capability; '+
    'homepage reading is sub-minute everywhere, with dashdish-8 unwinnable by rubric in all 18 arms.';
}
function taskIndex(){
  let h='<thead><tr><th>task</th><th>category</th><th>difficulty</th><th>goal</th><th>pass rate</th><th>time range</th></tr></thead><tbody>';
  D.order.forEach((t,i)=>{
    const cat=Object.keys(D.cats).find(c=>D.cats[c].includes(t));
    const arms=Object.keys(A);
    const p=arms.filter(a=>A[a].pass_by_task[i]).length;
    const times=arms.map(a=>A[a].run_by_task[i]);
    h+=`<tr class="clickable" onclick="showTask('${t}')"><td class="mono">${t}</td><td>${cat}</td><td>${D.difficulty[t]}</td>`+
       `<td class="note">${D.goals[t].slice(0,90)}...</td><td class="num">${p}/${arms.length}</td>`+
       `<td class="num">${Math.min(...times).toFixed(1)}-${Math.max(...times).toFixed(1)}m</td></tr>`;
  });
  document.getElementById('taskindex').innerHTML=h+'</tbody>';
}
function showTask(t){
  const i=D.order.indexOf(t);
  let h=`<h3 style="margin:2px 0">${t} <span class="note">(${D.difficulty[t]} · ${Object.keys(D.cats).find(c=>D.cats[c].includes(t))})</span></h3>
  <p class="note" style="margin:2px 0 8px">${D.goals[t]}</p>
  <div class="scroll"><table><thead><tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>s/turn (median gap)</th><th>first action</th><th>failing answer</th></tr></thead><tbody>`;
  for(const a in A){
    const ar=A[a];const fail=(D.tasks[t][a]||{}).fail||'';
    h+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${ar.color};border-radius:2px;margin-right:6px"></span>${ar.label}</td>
      <td>${ar.pass_by_task[i]?'<span class="badge b-pass">PASS</span>':'<span class="badge b-fail">FAIL</span>'}</td>
      <td class="num">${ar.run_by_task[i].toFixed(1)}</td><td class="num">${ar.turns_by_task[i]}</td>
      <td class="num">${ar.gapmed_by_task[i]==null?'·':ar.gapmed_by_task[i].toFixed(2)}s</td>
      <td class="num">${ar.first_by_task[i]==null?'·':ar.first_by_task[i].toFixed(0)+'s'}</td>
      <td class="note">${fail}</td></tr>`;
  }
  document.getElementById('detailbody').innerHTML=h+'</tbody></table></div>';
  document.getElementById('detail').classList.add('open');
}
function chartTierBenefit(){
  const M=D.diff.methods;const tiers=['easy','medium','hard'];
  const w=1060,h=290,pl=64;const cw=(w-pl-30)/M.length;const bw=Math.min(26,(cw-26)/3);
  const vmin=-5,vmax=1;const Y=v=>{const c=Math.max(vmin,Math.min(vmax,v));return 34+(h-116)*(vmax-c)/(vmax-vmin)};
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'time benefit vs cold by labeled tier, methods ordered by machinery (min/task; positive = faster than cold)'));
  for(let g=vmin;g<=vmax;g+=1){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},(g>0?'+':'')+g+'m'))}
  const shade={easy:.45,medium:.7,hard:1};
  M.forEach((m,mi)=>{
    const x0=pl+10+mi*cw;const col={raw:'#0d9488',analysis:'#10b981',fork:'#9d174d'}[m.mode];
    tiers.forEach((tr,ti)=>{
      const v=m.tier[tr].mean;const x=x0+ti*(bw+5);const y0=Y(0),y1=Y(v);
      s.appendChild(tip(el('rect',{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:2.5,fill:col,opacity:shade[tr]}),`${m.label} · ${tr}: ${v>0?'+':''}${v}m/task (${m.tier[tr].wins}/${m.tier[tr].n} tasks faster)`));
      s.appendChild(el('text',{x:x+bw/2,y:v>=0?y1-3:y1+10,'text-anchor':'middle','font-size':8.5,fill:'#5b6571'},(v>0?'+':'')+v.toFixed(1)));
    });
    s.appendChild(el('text',{x:x0+1.5*bw,y:h-58,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},m.label));
  });
  s.appendChild(el('text',{x:pl,y:h-36,'font-size':10,fill:'#8a929c'},'bar shade within each method: light=easy, mid=medium, dark=hard · teal/green = mounted, crimson = fork'));
  s.appendChild(el('text',{x:pl,y:h-22,'font-size':10,fill:'#8a929c'},'3D hard = one task (zilloft-10 hand-pagination disaster); every other mounted cell is within noise of zero'));
  const host=document.getElementById('c_tierben');host.innerHTML='';host.appendChild(s);
}
function chartDiffScatter(){
  const pts=D.diff.scatter;const w=1060,h=330,pl=60,pb=44,pr=30,pt=22;
  const xmax=Math.max(...pts.map(p=>p.x))*1.08;
  const ymin=Math.min(...pts.map(p=>p.y)),ymax=Math.max(...pts.map(p=>p.y));
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'per-task benefit vs empirical hardness (post-fix; cold minutes on the task)'));
  for(let g=0;g<=xmax;g+=1)if(g%1===0&&g<=xmax)s.appendChild(el('text',{x:X(g),y:h-26,'text-anchor':'middle','font-size':9,fill:'#8a929c'},g+'m'));
  for(let g=Math.ceil(ymin/2)*2;g<=ymax;g+=2){
    s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));
    s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},(g>0?'+':'')+g+'m'));
  }
  s.appendChild(el('line',{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}));
  s.appendChild(el('text',{x:pl-6,y:Y(0)+3,'text-anchor':'end','font-size':9,'font-weight':700,fill:'#5b6571'},'0m'));
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'cold minutes on the task'));
  s.appendChild(el('text',{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${(pt+h-pb)/2})`},'benefit vs cold (min/task): + = faster than cold'));
  const groups={raw:'#0d9488',analysis:'#10b981',fork:'#9d174d'};
  for(const g in groups){
    const gp=pts.filter(p=>p.g===g);
    gp.forEach(p=>s.appendChild(tip(el('circle',{cx:X(p.x),cy:Y(p.y),r:3.4,fill:groups[g],opacity:.6}),`${p.t} (${p.tier}) · ${p.arm}: cold ${p.x}m, benefit ${p.y>0?'+':''}${p.y}m`)));
    const xs=gp.map(p=>p.x),ys=gp.map(p=>p.y);
    const mx=xs.reduce((a,b)=>a+b)/xs.length,my=ys.reduce((a,b)=>a+b)/ys.length;
    const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((a,c)=>a+c)/xs.map(x=>(x-mx)**2).reduce((a,c)=>a+c);
    const a0=my-b*mx;
    s.appendChild(el('line',{x1:X(0.1),y1:Y(a0+b*0.1),x2:X(xmax*0.96),y2:Y(a0+b*xmax*0.96),stroke:groups[g],'stroke-width':2.2,'stroke-dasharray':'6 4'}));
  }
  let ly=30;
  for(const g in groups){s.appendChild(el('circle',{cx:w-190,cy:ly,r:4,fill:groups[g]}));s.appendChild(el('text',{x:w-180,y:ly+4,'font-size':10.5,fill:'#5b6571'},g+' mounts'.replace(g==='fork'?' mounts':'',g==='fork'?'s':'')));ly+=16}
  const host=document.getElementById('c_diffscatter');host.innerHTML='';host.appendChild(s);
}
function chartFlips(){
  const M=D.diff.methods;const w=660,h=230,pl=64;const tiers=['easy','medium','hard'];
  const agg=tiers.map(tr=>M.reduce((acc,m)=>acc+m.tier[tr].regress,0));
  const vmax=6;const Y=v=>h-56-(h-92)*v/vmax;const bw=64;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'accuracy regressions vs cold by tier (all six methods pooled; rescues were zero)'));
  for(let g=0;g<=vmax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g))}
  tiers.forEach((tr,i)=>{
    const x=pl+40+i*((w-pl-80)/3);const v=agg[i];
    s.appendChild(tip(el('rect',{x,y:Y(v),width:bw,height:Y(0)-Y(v)||1,rx:3,fill:'#c13a2e',opacity:.8}),`${tr}: ${v} regressions across 6 methods`));
    s.appendChild(el('text',{x:x+bw/2,y:Y(v)-4,'text-anchor':'middle','font-size':10.5,fill:'#c13a2e','font-weight':700},v));
    s.appendChild(el('text',{x:x+bw/2,y:h-38,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},tr));
  });
  const host=document.getElementById('c_flips');host.innerHTML='';host.appendChild(s);
}
function rhoTable(){
  let h='<div class="scroll"><table><thead><tr><th>method</th><th>class</th><th>rho(benefit, cold-time)</th><th>drop zilloft-9</th><th>hard-tier mean</th></tr></thead><tbody>';
  D.diff.methods.forEach(r=>{h+=`<tr><td class="mono">${r.label}</td><td>${r.mode}</td><td class="num">${r.rho>0?'+':''}${r.rho.toFixed(2)}</td><td class="num">${r.rho_noz9>0?'+':''}${r.rho_noz9.toFixed(2)}</td><td class="num">${r.tier.hard.mean>0?'+':''}${r.tier.hard.mean.toFixed(2)}m</td></tr>`});
  document.getElementById('rho_table').innerHTML=h+'</tbody></table></div>';
}
function chartWaterfall(){
  const W=D.waterfall;const arms=Object.keys(W);
  const w=1060,h=300,pw=(w-40)/2;
  const s=svgEl(w,h);
  arms.forEach((a,ai)=>{
    const d=W[a];const x0=20+ai*pw;const lbl=A[a].label;
    const hypo=d.cold+d.extra;             // fork's work at cold pace
    const vmax=Math.max(d.fork,d.cold)*1.18;
    const Y=v=>h-56-(h-96)*v/vmax;const bw=Math.min(72,(pw-90)/4);
    s.appendChild(el('text',{x:x0+pw/2,y:16,'text-anchor':'middle','font-size':11.5,'font-weight':600,fill:'#1b1f24'},lbl+': cold '+d.cold+'m \u2192 fork '+d.fork+'m'));
    const steps=[
      {x:0,base:0,top:d.cold,fill:'#0d9488',lab:d.cold+'m',cap:'cold actual',tip:'cold baseline, 12-task total'},
      {x:1,base:Math.min(d.cold,hypo),top:Math.max(d.cold,hypo),fill:d.extra<0?'#0f8a5f':'#c13a2e',lab:(d.extra>0?'+':'')+d.extra+'m',cap:d.extra<0?'work saved':'extra work',tip:d.extra<0?'turns the fork did not need, priced at cold pace':'extra turns the fork took, priced at cold pace'},
      {x:2,base:hypo,top:hypo+d.tax,fill:'#c13a2e',lab:'+'+d.tax+'m',cap:'reading tax',tip:'the per-turn context toll summed over all fork turns'},
      {x:3,base:0,top:d.fork,fill:'#9d174d',lab:d.fork+'m',cap:'fork actual',tip:'fork arm, 12-task total'}
    ];
    steps.forEach((st,i)=>{
      const x=x0+30+i*(bw+18);
      s.appendChild(tip(el('rect',{x,y:Y(st.top),width:bw,height:Math.max(2,Y(st.base)-Y(st.top)),rx:3,fill:st.fill,opacity:i===1||i===2?0.85:1}),st.cap+': '+st.tip));
      s.appendChild(el('text',{x:x+bw/2,y:Y(st.top)-5,'text-anchor':'middle','font-size':10.5,'font-weight':700,fill:st.fill},st.lab));
      s.appendChild(el('text',{x:x+bw/2,y:h-38,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},st.cap));
      if(i>0&&i<3){const px=x0+30+(i-1)*(bw+18)+bw;
        s.appendChild(el('line',{x1:px,y1:Y(st.base===hypo&&i===2?hypo:(i===1?d.cold:hypo)),x2:x,y2:Y(i===1?d.cold:hypo),stroke:'#c9c7c1','stroke-dasharray':'3 3'}));}
    });
    s.appendChild(el('line',{x1:x0+30+2*(bw+18)+bw,y1:Y(d.fork),x2:x0+30+3*(bw+18),y2:Y(d.fork),stroke:'#c9c7c1','stroke-dasharray':'3 3'}));
  });
  s.appendChild(el('text',{x:20,y:h-14,'font-size':10,fill:'#8a929c'},'fork time = cold time - work saved + reading tax · green = knowledge helping · red = delivery cost · RUN TIME ONLY: the one-time study/prep (37m experiential, 44m expert) is excluded here and tracked as prep in the main report'));
  const host=document.getElementById('c_waterfall');host.innerHTML='';host.appendChild(s);
}
function chartTurnsCmp(){
  const a4='exp4a-experiential-fork',ac='exp1a-fixed-brave';
  const w=1060,h=260,pl=64;const gw=(w-pl-24)/T.length;const bw=Math.min(16,(gw-14)/2);
  const vmax=Math.max(...A[ac].turns_by_task,...A[a4].turns_by_task)*1.15;
  const Y=v=>h-52-(h-84)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'work per task: model turns, cold vs experiential fork'));
  for(let g=0;g<=vmax;g+=40){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g))}
  T.forEach((t,i)=>{
    const x0=pl+6+i*gw;
    const vc=A[ac].turns_by_task[i],vf=A[a4].turns_by_task[i];
    s.appendChild(tip(el('rect',{x:x0,y:Y(vc),width:bw,height:Y(0)-Y(vc),rx:2,fill:'#0d9488'}),t+' · cold: '+vc+' turns'));
    s.appendChild(tip(el('rect',{x:x0+bw+3,y:Y(vf),width:bw,height:Y(0)-Y(vf),rx:2,fill:'#9d174d'}),t+' · fork: '+vf+' turns'));
    const d=vf-vc;
    s.appendChild(el('text',{x:x0+bw+1,y:Y(Math.max(vc,vf))-5,'text-anchor':'middle','font-size':8.5,'font-weight':700,fill:d<0?'#0f8a5f':'#c13a2e'},(d>0?'+':'')+d));
    s.appendChild(el('text',{x:x0+bw+1,y:h-36,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:'rotate(28 '+(x0+bw+1)+' '+(h-36)+')'},t.replace('dashdish-','dd').replace('zilloft-','z')));
  });
  s.appendChild(el('text',{x:pl,y:h-12,'font-size':10,fill:'#8a929c'},'teal = cold turns · crimson = fork turns · signed number = turns saved (green) or added (red) by the fork'));
  const host=document.getElementById('c_turnscmp');host.innerHTML='';host.appendChild(s);
}
function chartCtxCurve(){
  const P=D.ctx;const w=1060,h=330,pl=60,pb=44,pr=30,pt=22;
  const xmax=Math.max(...P.map(p=>p.ktok))*1.06;
  const ymax=Math.max(...P.map(p=>p.spt))*1.1;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'seconds per turn vs context carried per turn: one dot per task rollout'));
  for(let g=0;g<=xmax;g+=100){s.appendChild(el('line',{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}));s.appendChild(el('text',{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'},g+'k'))}
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'k tokens carried per turn (cache reads + writes + fresh input, per rollout)'));
  // fit
  const xs=P.map(p=>p.ktok),ys=P.map(p=>p.spt);
  const mx=xs.reduce((a,b)=>a+b)/xs.length,my=ys.reduce((a,b)=>a+b)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((a,c)=>a+c)/xs.map(x=>(x-mx)**2).reduce((a,c)=>a+c);
  const a0=my-b*mx;
  s.appendChild(el('line',{x1:X(20),y1:Y(a0+b*20),x2:X(xmax*.97),y2:Y(a0+b*xmax*.97),stroke:'#5b6571','stroke-width':2,'stroke-dasharray':'7 5'}));
  s.appendChild(el('text',{x:X(xmax*.55),y:Y(a0+b*xmax*.55)-10,'font-size':10.5,fill:'#5b6571'},'fit: '+a0.toFixed(1)+'s + '+(b*100).toFixed(1)+'s per 100k tokens (r=0.88)'));
  P.forEach(p=>{
    const c=(A[p.arm]||{}).color||'#8a929c';
    s.appendChild(tip(el('circle',{cx:X(p.ktok),cy:Y(p.spt),r:3.6,fill:c,opacity:.7}),(A[p.arm]||{label:p.arm}).label+' · '+p.task+': '+p.ktok+'k/turn, '+p.spt+'s/turn ('+p.turns+' turns)'));
  });
  let ly=26;
  ['exp1a-fixed-brave','exp3c-analysis','exp2b-fixed-brave','exp4b-expert-fork','exp4a-experiential-fork'].forEach(a=>{
    s.appendChild(el('circle',{cx:w-238,cy:ly,r:4,fill:A[a].color}));
    s.appendChild(el('text',{x:w-228,y:ly+4,'font-size':10,fill:'#5b6571'},A[a].label));ly+=15;
  });
  const host=document.getElementById('c_ctxcurve');host.innerHTML='';host.appendChild(s);
}
function renderAll(){chartCtxCurve();chartTurnsOut();chartKtok();chartScatter();chartSeries();chartBox();chartTasks();chartCats();catTable();chartTierBenefit();chartDiffScatter();chartFlips();rhoTable();chartWaterfall();chartTurnsCmp();}
renderToggles();renderAll();taskIndex();
</script>
</div></body></html>
"""

page = (page_head + FORK_SECTION + page_mid
        + JS.replace("__PAYLOAD__", json.dumps(PAYLOAD)) + JS2)
out = os.path.join(BENCH, "benchmark_deep_dive.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

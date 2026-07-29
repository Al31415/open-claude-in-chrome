#!/usr/bin/env python3
"""Phase-7 distillations: author the four artifacts the new comparison arms consume.

Two sources, each recorded over the SAME six train tasks in the same sessions:
  ocic    - open-claude-in-chrome recordings: raw 4-track trace.json per task
            (behavior / cursor / cognitive narration / frames), nothing distilled.
  cowork  - Claude cowork artifacts: ONE generated markdown artifact per task,
            already analyzed at capture time by that system. No raw layer exists.

Two purposes, mirroring the two regimes the study already ran:
  p3  - ANALYSIS_<site>.md, reference documents that sit ON DISK in the rollout
        workspace (the phase-3 regime; agent reads them before acting).
  p5  - RECIPE_<site>.md, terse artifacts SPLICED INTO the task prompt
        (the phase-5 regime, site-routed exactly as 5b/6b do).

Every session is isolated: its cwd is a workspace containing ONLY its own
source material under experience/, and the prompt hard-bounds it to that
directory. No repo, no manifests, no test tasks, no evaluators, no other arm's
material - the leakage guarantee is structural, not just prompt-enforced.

Distiller model is claude-fable-5 at max effort for all four, matching the one
documented precedent in this study (the 5b/6b recipe author, see
6b_reproduction/recipe_generation_prompt.md). Every executor rollout stays
Sonnet medium: deliberate strong-to-weak transfer.

Usage:  python3 run_p7_distill.py [--only p3_ocic,p5_cowork] [--timeout 3600]
"""
import argparse, json, os, subprocess, sys, time

BENCH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.expanduser("~/.bench_rollouts")
MODEL = "claude-fable-5"
EFFORT = "max"

# ---- source descriptions: the ONLY per-arm difference in the prompts --------
SRC = {
    "ocic": "(its README.md explains the source: an expert operator's browser "
            "recordings, four tracks on one clock, covering 6 earlier tasks)",
    "cowork": "(its README.md explains the source: one generated markdown "
              "artifact per task, produced automatically by the recording "
              "system at capture time, covering 6 earlier tasks)",
}

# ---- p3: reference documents that live on disk in the rollout workspace -----
P3_PROMPT = """[EXPERIENCE ANALYSIS SESSION]
You are analyzing prior experience material for autonomous browser agents that
will complete tasks in two demo web apps: dashdish (food delivery) and zilloft
(real estate). You have that material at ./experience/ {src}. Study it
thoroughly, every task, before writing anything.

Then write EXACTLY two files in the current directory:

1. ANALYSIS_dashdish.md - analysis of dashdish only
2. ANALYSIS_zilloft.md  - analysis of zilloft only

Requirements for both documents:
- These are REFERENCE DOCUMENTS that will sit on disk in a later agent's
  workspace. That agent is instructed to read the one for its site BEFORE it
  starts acting, and it is intended to be sufficient on its own, so that agent
  should not need to study the raw material itself.
- Capture how each site ACTUALLY behaves: page map and routes, which controls
  are real versus decorative/inert, search and filter mechanics, how results
  are counted and read, cart/form/checkout mechanics, and the fastest reliable
  route through each.
- Include tool tactics where the material shows them mattering (for example
  when text extraction beats screenshots, when a direct form-value set beats
  clicking a native control), described generally.
- GENERAL procedures and mechanics only. Do NOT include answers, counts,
  prices, names, or any value specific to the earlier tasks. An agent reading
  the analysis must learn HOW the apps behave, never WHAT some earlier answer
  was.
- Keep only what RECURS or is STRUCTURAL. Compression is the point: no
  narration, no task-by-task retelling. At most ~700 words per document.
- Plain markdown, no links, no images.

Boundary: this working directory is your ONLY filesystem environment. Do not
read, list, write, or search any path outside it.

When the two files are written, end your reply with the single line
"ANALYSIS COMPLETE"."""

# ---- p5: terse artifacts spliced into the task prompt (verbatim 5b prompt,
# ---- adapted only for the single source and the two site files) -------------
P5_PROMPT = """[RECIPE AUTHORING SESSION]
You are preparing OPERATING RECIPES for autonomous browser agents that will
complete tasks in two demo web apps: dashdish (food delivery) and zilloft
(real estate). You have prior experience material at ./experience/ {src}.
Study it thoroughly, every task, before writing anything.

Then write EXACTLY two files in the current directory:

1. RECIPE_dashdish.md  - recipe for dashdish only
2. RECIPE_zilloft.md   - recipe for zilloft only

Requirements for every recipe:
- EXPERT quality: the distilled operating knowledge a top operator would hand
  a new agent. What actually works, what silently fails, and the fastest
  reliable route through each app's mechanics (search, filters, forms, carts,
  counting, reading results).
- Include tool tactics where the material shows them mattering (for example
  when text extraction beats screenshots, when a direct form-value set beats
  clicking a native control), described generally.
- GENERAL procedures and mechanics only. Do NOT include answers, counts,
  prices, names, or any value specific to the earlier tasks. An agent reading
  the recipe must learn HOW the apps behave, never WHAT some earlier answer was.
- NON-DISTRACTING: this text rides inside a task prompt. Short imperative
  bullets, tight sections, zero narration or filler. Site recipes at most
  ~600 words each.
- Plain markdown, no links, no images.

Boundary: this working directory is your ONLY filesystem environment. Do not
read, list, write, or search any path outside it.

When the two files are written, end your reply with the single line
"RECIPES COMPLETE"."""

JOBS = {}
for _src in ("ocic", "cowork"):
    JOBS["p3_" + _src] = {"workspace": os.path.join(ROOT, "p7_p3_" + _src),
                          "prompt": P3_PROMPT.format(src=SRC[_src]),
                          "expect": ["ANALYSIS_dashdish.md", "ANALYSIS_zilloft.md"],
                          "sentinel": "ANALYSIS COMPLETE"}
    JOBS["p5_" + _src] = {"workspace": os.path.join(ROOT, "p7_p5_" + _src),
                          "prompt": P5_PROMPT.format(src=SRC[_src]),
                          "expect": ["RECIPE_dashdish.md", "RECIPE_zilloft.md"],
                          "sentinel": "RECIPES COMPLETE"}


def child_env():
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("CLAUDECODE") or k.startswith("CLAUDE_CODE"):
            env.pop(k, None)
    return env


def run(name, job, timeout):
    ws, out = job["workspace"], os.path.join(job["workspace"], "distill_result.json")
    print(f"\n=== {name}  ({MODEL}, effort={EFFORT})\n    cwd {ws}")
    for f in job["expect"]:                       # never silently reuse a stale artifact
        p = os.path.join(ws, f)
        if os.path.exists(p):
            os.remove(p); print(f"    removed stale {f}")
    cmd = ["claude", "-p", job["prompt"], "--model", MODEL, "--effort", EFFORT,
           "--output-format", "json", "--dangerously-skip-permissions"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=ws, env=child_env(), text=True,
                          capture_output=True, timeout=timeout)
    dur = time.time() - t0
    parsed = None
    try:
        parsed = json.loads(proc.stdout)
    except Exception:
        pass
    result = (parsed or {}).get("result", "") or proc.stdout[-2000:]
    written = [f for f in job["expect"] if os.path.exists(os.path.join(ws, f))]
    rec = {"job": name, "model": MODEL, "effort": EFFORT, "seconds": round(dur, 1),
           "exit": proc.returncode, "sentinel_ok": job["sentinel"] in result,
           "files_written": written, "files_expected": job["expect"],
           "num_turns": (parsed or {}).get("num_turns"),
           "session_id": (parsed or {}).get("session_id"),
           "cost_usd": (parsed or {}).get("total_cost_usd"),
           "words": {f: len(open(os.path.join(ws, f)).read().split()) for f in written}}
    json.dump(rec, open(out, "w"), indent=1)
    ok = proc.returncode == 0 and len(written) == len(job["expect"])
    print(f"    {'OK ' if ok else 'FAIL'} {dur/60:.1f} min, {rec['num_turns']} turns, "
          f"${rec['cost_usd'] or 0:.2f}, sentinel={rec['sentinel_ok']}")
    for f in written:
        print(f"      {f}: {rec['words'][f]} words")
    missing = [f for f in job["expect"] if f not in written]
    if missing:
        print(f"      MISSING: {missing}")
        print(f"      tail: {result[-400:]}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma list of job names")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    names = [n.strip() for n in a.only.split(",") if n.strip()] or list(JOBS)
    bad = [n for n in names if n not in JOBS]
    if bad:
        sys.exit("unknown job(s): %s ; known: %s" % (bad, list(JOBS)))
    results = {n: run(n, JOBS[n], a.timeout) for n in names}
    print("\n=== summary")
    for n, ok in results.items():
        print(f"  {'OK  ' if ok else 'FAIL'} {n}")
    sys.exit(0 if all(results.values()) else 1)

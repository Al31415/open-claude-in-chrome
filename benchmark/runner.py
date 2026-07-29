"""benchmark/runner.py -- production rollout orchestrator.

Runs one experiment (a batch of rollouts) against the REAL webclone apps.
Per rollout, the five-stage unit:

  SETUP     reset browser state (clear localStorage -> /config -> assert clean /finish)
  RUN       detached `claude -p` (never a subagent), experiment header + task prompt
  GATE      exit code + non-empty answer + minimum tool activity + throttle detection
  TEARDOWN  capture /finish byte-exact; copy the ~/.claude transcript verbatim
  EVALUATE  REAL's WebCloneEvaluator (jmespath exact; llm_boolean judged via claude)

Everything is timed (setup, run, teardown, eval; run is the headline number).
Artifacts per rollout: prompt.txt, result_raw.json, trajectory.jsonl, finish.json,
evaluation.json, timing.json. Logs are written for a human to tail.

Rate-limit policy (Claude Max 20x, shared 5h window + weekly caps): fixed buffer
between rollouts, reactive throttle detection with a parsed-or-default wait, and
throttled attempts re-queued rather than scored.

Usage:
  python3 runner.py preflight
  python3 runner.py run --experiment gen-experiential [--only TASK_ID] [--buffer 45]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time

BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BENCH)
from harness import OC, read_finish_text, _diff_nonempty, _load_real_evaluator  # noqa: E402

MANIFEST = os.path.join(BENCH, "tasks_manifest.json")
DATA = os.path.join(BENCH, "data")
LOGS = os.path.join(BENCH, "logs")
WORKROOT = os.path.expanduser("~/.bench_rollouts")  # outside any git repo: no project context leaks in

AGENT_MODEL = "sonnet"
AGENT_EFFORT = "medium"
JUDGE_MODEL = "sonnet"          # llm_boolean judge (REAL default is gpt-4o; no OPENAI_API_KEY here)
ROLLOUT_TIMEOUT_S = 1200        # hard cap per claude run
MIN_TOOL_CALLS = 3              # lazy-run gate
THROTTLE_RE = re.compile(
    r"usage limit|rate.?limit|limit (?:will )?reset|limit reached|overloaded|"
    r"weekly limit|too many requests|(?<!\d)429(?!\d)", re.I)
RESET_HINT_RE = re.compile(r"reset(?:s|ting)?\s+(?:at\s+)?([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)", re.I)
THROTTLE_DEFAULT_WAIT_S = 20 * 60
THROTTLE_MAX_WAIT_S = 65 * 60

# ---- experiment definitions -------------------------------------------------
# The HEADER is the per-experiment constant scaffolding; the task goal is
# appended per rollout. Phases 1 and 2 forbid execute_code explicitly.

OCIC_NOCODE_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "open-claude-in-chrome-hybrid" MCP server tools
(Open Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first. Work ONLY in tabId {tab}. That tab is already open on
{app_name} at {app_url} (a self-contained demo web app; you are already
logged in).

Rules:
- Act only in tabId {tab}. Do not create tabs. Do not visit any other website.
- Never navigate to a URL containing "/config" or "/finish".
- Never read or write localStorage/sessionStorage or inject state directly.
- You are NOT allowed to use the execute_code tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app).
- Work autonomously to completion. If a click misses, look again and retry.
  Do not stop early. Do not ask questions.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# Phase 2 adds prior experience mounted on disk at ./experience/ and a
# filesystem boundary. Everything else (execute_code forbidden, browser jail)
# is identical to phase 1. The %s slots are filled at import; {tab}/{app_name}/
# {app_url}/{goal} stay for per-rollout .format().
_FS_RULE = """- This working directory is your ONLY filesystem environment. You may read the
  files under ./experience/ (that is why they are there). Do NOT read, list,
  write, or search any path outside this directory, and do not run shell
  commands that escape it (no `..`, no absolute paths elsewhere, no `cd /`)."""

_PRIOR_EXPERIENTIAL = """Prior experience: you (this same agent) have already completed several similar
tasks in THIS SAME environment. Your own past runs are saved on disk at
./experience/ as traces extracted directly from a Claude Code session — the
normal trace format you already understand. One folder per task (trace.jsonl +
images/). The only change from a raw session: inline screenshots are stored as
image files, referenced in the trace as `[screenshot -> images/NNNN.jpg]`; open
that file to view the frame. BEFORE you start clicking, read
./experience/README.md, open the past run whose goal is closest to your task,
and reuse the UI flow that already worked. This is memory to adapt, not a script."""

_PRIOR_EXPERT = """Prior experience: an expert operator recorded themselves completing several
similar tasks in THIS SAME environment. Their demonstrations are on disk at
./experience/ (one folder per task; README.md lists them, SCHEMA_v0.md explains
the recording format, each task folder has a trace.json with the
behavior/cursor/narration track and an images/ folder of frames). BEFORE you
start clicking, read ./experience/README.md, study the demonstration whose goal
is closest to your task, and follow the same UI flow. Adapt it to the current task."""

def _phase2_header(prior):
    base = OCIC_NOCODE_HEADER
    # inject the prior-experience block after the "logged in)." intro paragraph
    base = base.replace("logged in).\n\nRules:", "logged in).\n\n%s\n\nRules:" % prior)
    # append the filesystem boundary as the last hard rule before the autonomy line
    base = base.replace(
        "- Work autonomously to completion.",
        _FS_RULE + "\n- Work autonomously to completion.")
    return base

OCIC_EXPERIENTIAL_HEADER = _phase2_header(_PRIOR_EXPERIENTIAL)
OCIC_EXPERT_HEADER = _phase2_header(_PRIOR_EXPERT)

# Phase 3 flips the execute_code clause from forbidden to permitted (usage is
# tracked, not capped). 3A keeps the plain expert experience; 3B mounts the
# analyzed environment and its prior block points at the ANALYSIS docs first.
_NOCODE_CLAUSE = """- You are NOT allowed to use the execute_code tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app)."""

_CODE_CLAUSE = """- You MAY use the execute_code tool in this experiment, and you are encouraged
  to lean on it where it helps: it runs JavaScript with the other browser tools
  exposed as functions (chrome.computer, chrome.find, chrome.navigate, ...), so
  a deterministic multi-step sequence can run in ONE call instead of many.
  Batch what is predictable; look first (screenshot) where the next move
  depends on what the page shows."""

_PRIOR_EXPERT_ANALYZED = """Prior experience: an expert operator recorded themselves completing several
similar tasks in THIS SAME environment, and those demonstrations have ALREADY
been analyzed for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The raw recordings (one folder per task: trace.json + SCHEMA_v0.md +
  images/), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

_PRIOR_EXPERIENTIAL_ANALYZED = """Prior experience: you (this same agent) have already completed several similar
tasks in THIS SAME environment, and your own past runs have ALREADY been
analyzed for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  distilled from your own attempts (page map, what worked vs what stalled,
  search and filter mechanics, recipes, gotchas). Read the one for your task's
  site FIRST; it is intended to be sufficient on its own.
- The raw runs (one folder per task: trace.jsonl + images/), only if you need
  to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

def _phase3_header(prior):
    return _phase2_header(prior).replace(_NOCODE_CLAUSE, _CODE_CLAUSE)

def _phase3_silent_header(prior):
    # No execute_code clause at all — neither forbidden nor encouraged. The tool
    # is available (execute_code_allowed=True); whether to use it is left
    # entirely to the model, with zero prompt steering either way.
    return _phase2_header(prior).replace(_NOCODE_CLAUSE + "\n", "")

OCIC_EXPERT_CODE_HEADER = _phase3_header(_PRIOR_EXPERT)
OCIC_ANALYZED_CODE_HEADER = _phase3_header(_PRIOR_EXPERT_ANALYZED)
OCIC_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_EXPERT_ANALYZED)

# ---- Phase 7 prior blocks: same phase-3 regime, one per recording system.
# Deliberately parallel in structure and length so the ONLY prompt difference
# is what the underlying source material actually is; the analysis filename
# and the read-this-first instruction are identical in both.
_PRIOR_OCIC_NEW_ANALYZED = """Prior experience: an expert operator was recorded completing several similar
tasks in THIS SAME environment, and those recordings have ALREADY been analyzed
for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The raw recordings (one folder per task: trace.json + SCHEMA_v0.md +
  images/), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

_PRIOR_COWORK_ANALYZED = """Prior experience: an expert operator was recorded completing several similar
tasks in THIS SAME environment, and those recordings have ALREADY been analyzed
for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The per-task artifacts the recording system generated (one markdown file per
  task), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

OCIC_NEW_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_OCIC_NEW_ANALYZED)
COWORK_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_COWORK_ANALYZED)
# Experiential twin of the analyzed-silent header: same silent (no execute_code
# mention) phase-3 prompt, but the prior block points at analysis distilled from
# the agent's OWN past runs rather than the expert recordings.
OCIC_EXPERIENTIAL_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_EXPERIENTIAL_ANALYZED)

# EXP-1B: the official Claude-in-Chrome extension in the user's CHROME.
# Mirrors OCIC_NOCODE_HEADER with three deliberate differences, all forced by
# the official topology and documented as caveats: (1) the MCP is
# "claude-in-chrome"; (2) there is no orchestrator-assigned tab (the session
# owns its own tab group), so the agent opens ONE tab itself; (3) the no-code
# bullet bans javascript_tool (the official MCP has no execute_code).
CINC_NOCODE_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "claude-in-chrome" MCP server tools
(Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first. Get the tab context (create the tab group if needed),
open ONE new tab, and navigate it to {app_url} ({app_name}, a self-contained
demo web app; you are already logged in).

Rules:
- Work ONLY in that one tab. Do not open more tabs. Do not visit any other
  website.
- Never navigate to a URL containing "/config" or "/finish".
- Never read or write localStorage/sessionStorage or inject state directly.
- You are NOT allowed to use the javascript_tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app).
- Work autonomously to completion. If a click misses, look again and retry.
  Do not stop early. Do not ask questions.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# ---- Phase 4: fork-and-resume from a checkpoint session ---------------------
# Phase 3 mounted a library next to the task ("here are the docs, go read
# them"); phase 4 has ALREADY read the library: a one-time study/experience
# session is checkpointed, and every test rollout FORKS that session
# (claude -p --resume <sid> --fork-session) with the study's working directory
# restored VERBATIM at the SAME absolute path (forks only resolve from the
# session's own project cwd; verified empirically). execute_code is never
# mentioned in any phase-4 prompt; using it is neither encouraged nor a
# violation. Model/effort are the global AGENT_MODEL/AGENT_EFFORT (sonnet,
# medium) for study, train segments, and forks alike.

_P4_SILENT_BASE = OCIC_NOCODE_HEADER.replace(_NOCODE_CLAUSE + "\n", "")

_P4_FS_RULE = """- This working directory is your ONLY filesystem environment. It contains
  whatever it contained earlier in this session (any notes or materials,
  including ./experience/ if present). Do NOT read, list, write, or search any
  path outside this directory, and do not run shell commands that escape it
  (no `..`, no absolute paths elsewhere, no `cd /`)."""

def _p4_fork_header(prior_line):
    base = _P4_SILENT_BASE
    base = base.replace("logged in).\n\nRules:", "logged in).\n\n%s\n\nRules:" % prior_line)
    base = base.replace("- Work autonomously to completion.",
                        _P4_FS_RULE + "\n- Work autonomously to completion.")
    return base

P4A_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you completed several similar
tasks in this same environment yourself. Draw on that experience directly —
you already know how these apps work.""")

P4B_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you studied expert
demonstrations of similar tasks in this same environment and internalized how
these apps work. Draw on that understanding directly.""")

# 4A study: the first train segment uses the standard silent header + the
# phase-4 FS rule; segments 2..6 continue the SAME session with a short
# next-task message (new tab, fresh seeded state, same rules).
P4_TRAIN_HEADER = _P4_SILENT_BASE.replace(
    "- Work autonomously to completion.",
    _P4_FS_RULE + "\n- Work autonomously to completion.")

P4_TRAIN_CONT = """[BENCHMARK ROLLOUT — NEXT TASK]
The previous task is finished. A NEW task follows in the same app family.
Your workspace is now tabId {tab}, already open on {app_name} at {app_url}
(fresh, reset state; you are already logged in). The same rules as before
apply unchanged: act only in tabId {tab}; do not create tabs; never navigate
to a URL containing "/config" or "/finish"; never read or write
localStorage/sessionStorage; your working directory remains your ONLY
filesystem environment. Work autonomously to completion.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# 4B study: thorough internalization of the expert recordings. Deliberately
# says NOTHING about the browser (neither offered nor forbidden — the model's
# own discretion) and nothing about execute_code. Only the filesystem boundary
# is stated. App state cannot be polluted: every test rollout re-seeds and
# asserts a clean /finish before the agent starts.
P4_EXPERT_STUDY_PROMPT = """[BENCHMARK STUDY SESSION]
You are preparing to work in a pair of demo web apps (dashdish, a food
delivery app; zilloft, a real-estate app). An expert operator recorded
themselves completing several tasks in these exact apps. The recordings are
on disk at ./experience/ (README.md lists them; SCHEMA_v0.md explains the
format; one folder per task holds trace.json and an images/ folder of frames).

Your job in this session is to STUDY those demonstrations and internalize how
these apps actually work. This is deep preparation, not a skim:
- Work through EVERY recording, action by action, alongside its frames.
- Reconstruct what the operator did and, more importantly, WHY it worked:
  page structure, which controls are real vs decorative, search and filter
  mechanics, form flows, quirks and gotchas of each app.
- Cross-check your understanding across the recordings until the apps'
  behavior is predictable to you — until you could complete similar tasks
  yourself without consulting the recordings again.
Take the time this needs. Do not stop at a summary of file contents; the goal
is that you INTERNALIZE the mechanics of these environments.

Boundary: this working directory is your ONLY filesystem environment. Do NOT
read, list, write, or search any path outside it, and do not run shell
commands that escape it (no `..`, no absolute paths elsewhere, no `cd /`).

You may organize the session however serves the goal; anything you leave in
the working directory stays available to you later. When you are done, end
your reply with a line starting "STUDY COMPLETE:" followed by one sentence on
the depth of understanding you reached."""

# Setup-parity CinC header, v2. The official extension scopes tab control to a
# per-session tab group (verified 2026-07-16: a tab created by one session
# cannot be driven by another; javascript_tool/get_page_text refuse foreign
# tabs), so an orchestrator-prepared persistent tab is impossible and the
# agent MUST create its own group/tab. Parity is therefore achieved by
# (a) scripting that preamble deterministically (two fixed actions, zero
# deliberation) and (b) tagging the setup prefix in analysis so times are
# reported raw and setup-excluded. State seeding stays orchestrator-side and
# was never a parity issue (localStorage is origin-scoped, shared across tabs).
CINC_PARITY_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "claude-in-chrome" MCP server tools
(Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first.

SETUP PREAMBLE (do these two actions first, exactly, no exploration):
1. tabs_context with createIfEmpty true (a tab group with one tab appears).
2. Navigate that tab to {app_url} ({app_name}, a self-contained demo web app;
   you are already logged in; its state is pre-seeded and ready).
The preamble is expected overhead, not part of the task. After it, begin the
task immediately in that same tab.

Rules:
- Work ONLY in that one tab. Do not open more tabs. Do not visit any other
  website.
- Never navigate to a URL containing "/config" or "/finish".
- Never read or write localStorage/sessionStorage or inject state directly.
- You are NOT allowed to use the javascript_tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app).
- Work autonomously to completion. If a click misses, look again and retry.
  Do not stop early. Do not ask questions.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# ---- Phase 5: leakage-free recipes + atomic warm-ups ------------------------
# Recipes are authored by an ISOLATED Fable-5 session that saw ONLY the raw
# train-derived material (experiential traces + expert recordings); the
# orchestrating session (which carries test knowledge) never writes recipe
# content. 5A/5B append a recipe to the COLD header (execute_code stays
# forbidden: the recipe text is the only delta vs the cold baseline).
# 5C forks a website-matched single-task warm-up checkpoint (silent header,
# phase-4 convention). 5D = 5C's fork + 5A's site recipe.
RECIPES_DIR = os.path.join(BENCH, "environments", "recipes")
# Phase 7 recipe sets: same site routing as 5b/6b, one set per recording
# system, each authored from that system's material only.
RECIPES_DIR_OCIC_NEW = os.path.join(BENCH, "environments", "recipes_ocic_new")
RECIPES_DIR_COWORK = os.path.join(BENCH, "environments", "recipes_cowork")

_P5_RECIPE_BLOCK = """Field notes for {app_name}, compiled by an earlier agent from prior runs on
similar tasks in this same app (use what helps; ignore what does not):

{recipe}"""

P5_RECIPE_HEADER = OCIC_NOCODE_HEADER.replace(
    "logged in).\n\nRules:", "logged in).\n\n" + _P5_RECIPE_BLOCK + "\n\nRules:")

P5_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you completed a similar task
on this same website. Draw on that experience directly.""")

P5D_FORK_RECIPE_HEADER = P5_FORK_HEADER.replace(
    "logged in).\n\nPrior experience:",
    "logged in).\n\n" + _P5_RECIPE_BLOCK + "\n\nPrior experience:")

def load_recipe(kind, app, recipe_dir=None):
    """kind: site|single. Site recipes are RECIPE_<app>.md; single is
    RECIPE_combined.md. Authored by the isolated generator; read-only here.
    recipe_dir overrides RECIPES_DIR so an arm can carry its own recipe set
    (phase 7 runs one recipe set per recording system, same site routing)."""
    name = "RECIPE_combined.md" if kind == "single" else "RECIPE_%s.md" % app
    with open(os.path.join(recipe_dir or RECIPES_DIR, name)) as f:
        return f.read().strip()

EXPERIMENTS = {
    # Experiential-experience generation: phase-1 pipeline over the TRAIN set.
    "gen-experiential": {
        "system": "ocic", "split": "train_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Phase 1
    "exp1a-ocic-cold": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    "exp1b-cinc-cold": {
        "system": "cinc", "split": "test_order", "header": CINC_NOCODE_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Control re-run of the official-CinC cold baseline (2026-07-16), identical
    # config to exp1b-cinc-cold. The original ran ~3 weeks earlier in a
    # different environment epoch (older CLI, pre-fix era); this re-run checks
    # that the large OCIC-vs-CinC gap is not an artifact of environmental
    # drift. New arm name preserves the original data.
    "exp1b-cinc-rerun": {
        "system": "cinc", "split": "test_order", "header": CINC_NOCODE_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Setup-parity CinC arm, v2 (2026-07-16): the official topology forces the
    # agent to create its own session-scoped tab group (see CINC_PARITY_HEADER
    # note), so parity = a deterministically scripted two-action preamble plus
    # setup-excluded accounting in analysis. Seed/teardown use the original
    # orchestrator-side adapter (state is origin-scoped; always was correct).
    # Fresh per-rollout tabs self-activate in their window: keep the Chrome
    # window visible and every rollout runs in an active tab.
    "exp1b-cinc-parity": {
        "system": "cinc", "split": "test_order", "header": CINC_PARITY_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Phase 2: same OCIC pipeline + prior experience mounted at ./experience/.
    "exp2a-experiential": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERIENTIAL_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "experiential",
    },
    "exp2b-expert": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "expert",
    },
    # Post-fix re-run of 2A (raw experiential traces, execute_code forbidden) on
    # Brave with the tab-activation fix. New arm name so the pre-fix
    # exp2a-experiential data stays intact for historical comparison. Completes
    # the post-fix matrix: cold / expert-analysis / experiential-analysis /
    # experiential-raw.
    "exp2a-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERIENTIAL_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "experiential",
    },
    # Post-fix re-run of 2B (raw expert recordings, execute_code forbidden) on
    # Brave. New arm name so the pre-fix exp2b-expert data stays intact. Fills
    # the last cell of the post-fix matrix: expert-raw.
    "exp2b-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "expert",
    },
    # 1A repeated with OCIC connected to CHROME instead of Brave (post ack-fix,
    # v2 extension). Identical header/pipeline; browser selection is operational
    # (extension enabled only in Chrome). Verify identity before running.
    "exp1a-chrome": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Post-fix (tab-activation) re-runs of the cold baseline, one per browser.
    # Same OCIC no-code pipeline; the browser is whichever is primary at run
    # time (Chrome, or Brave after switch_browser). Windows sized to the
    # standard 1512x948 so results compare to the earlier arms.
    "exp1a-fixed-chrome": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    "exp1a-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Phase 3: execute_code permitted (usage tracked). Control = exp2b-expert.
    "exp3a-code": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert",
    },
    "exp3b-code-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # Post-fix re-run of 3b on Brave (analysis env, execute_code encouraged).
    "exp3b-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # 3c: same analysis env, but the prompt makes NO mention of execute_code —
    # the tool is available and the model decides on its own whether to use it.
    "exp3c-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # 3d: the experiential twin of 3c. Same silent phase-3 pipeline (execute_code
    # available, no prompt mention), same Brave browser, same analysis-doc format
    # — the ONLY difference from 3c is the source of the analysis: docs distilled
    # from the agent's OWN past runs instead of the expert recordings. Isolates
    # "experiential vs expert" as the source of the compressed knowledge.
    "exp3d-experiential-analysis": {
        "system": "ocic", "split": "test_order",
        "header": OCIC_EXPERIENTIAL_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "experiential_analyzed",
    },
    # Phase 4: every rollout forks the checkpointed study session (see the
    # phase-4 block above). Requires `runner.py p4study --arm <arm>` to have
    # produced data/phase4/<arm>_study/{study.json, workdir_snapshot.tar.gz}.
    "exp4a-experiential-fork": {
        "system": "ocic", "split": "test_order", "header": P4A_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "phase4": "experiential",
    },
    "exp4b-expert-fork": {
        "system": "ocic", "split": "test_order", "header": P4B_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "phase4": "expert",
    },
    # Phase 5 (see block above). 5A/5B: cold + recipe in the prompt.
    "exp5a-recipe-site": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False, "recipe": "site",
    },
    "exp5b-recipe-single": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False, "recipe": "single",
    },
    # 5C: fork the website-matched atomic warm-up checkpoint.
    "exp5c-atomic-warmup": {
        "system": "ocic", "split": "test_order", "header": P5_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
    },
    # 5D: 5C's routed fork + 5A's site recipe in the prompt.
    "exp5d-warmup-recipe": {
        "system": "ocic", "split": "test_order", "header": P5D_FORK_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
        "recipe": "site",
    },
    # ---- Phase 7: recording-system comparison (OCIC raw vs cowork artifacts).
    # Both systems captured the SAME six train sessions simultaneously, so the
    # underlying events are held constant and only the representation differs.
    # 7A/7B replay the phase-3 regime (analysis + sources mounted on disk);
    # 7C/7D replay the 5b regime (site-routed recipe spliced into the prompt).
    # Within each pair the header, flags and delivery are identical.
    "exp7a-ocic-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_NEW_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "ocic_new_analyzed",
    },
    "exp7b-cowork-analysis": {
        "system": "ocic", "split": "test_order", "header": COWORK_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "cowork_analyzed",
    },
    "exp7c-ocic-recipe": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
        "recipe": "site", "recipe_dir": RECIPES_DIR_OCIC_NEW,
    },
    "exp7d-cowork-recipe": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
        "recipe": "site", "recipe_dir": RECIPES_DIR_COWORK,
    },
    # 7E = 6b's exact design (same warm-up checkpoints, same fork routing, same
    # header) with ONLY the recipe swapped for the phase-7 OCIC one. Isolates
    # the recipe's contribution against the study's winning arm.
    "exp7e-ocic-warmup-recipe": {
        "system": "ocic", "split": "test_order", "header": P5D_FORK_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
        "recipe": "site", "recipe_dir": RECIPES_DIR_OCIC_NEW,
    },
}

# Phase-2 experience sources (built from phase-1 train runs / operator demos).
# experiential = Claude Code session traces with image-bytes swapped for frame
# references (build_experiential_env.py); expert = operator OCIC recordings.
ENV_EXPERIENTIAL = os.path.join(BENCH, "environments", "experiential", "mounted")
ENV_EXPERT = os.path.join(BENCH, "environments", "expert", "recordings")
ENV_EXPERT_ANALYZED = os.path.join(BENCH, "environments", "expert_analyzed", "mounted")
ENV_EXPERIENTIAL_ANALYZED = os.path.join(BENCH, "environments", "experiential_analyzed", "mounted")
# Phase 7: two recording systems captured the SAME six train sessions
# simultaneously. ocic_new = raw 4-track recordings (nothing distilled at
# capture time); cowork = one generated markdown artifact per task, already
# analyzed at capture time by that system (no raw layer is retained by it).
# Both analyzed environments carry per-site ANALYSIS docs authored from their
# own sources only, by the same isolated Fable-5 distiller.
ENV_OCIC_NEW_ANALYZED = os.path.join(BENCH, "environments", "ocic_new_analyzed", "mounted")
ENV_COWORK_ANALYZED = os.path.join(BENCH, "environments", "cowork_analyzed", "mounted")

def populate_experience(workdir, kind, log):
    """Copy the read-only prior-experience environment VERBATIM into
    <workdir>/experience/ so it lives INSIDE the agent's cwd (no --add-dir,
    tight jail). Rebuilt disposably each rollout. Each environment is fully
    defined on disk (data + its own README.md); this is a pure copy, no
    per-rollout generation. No finish/evaluation artifacts exist in either
    source (ground-truth leak). Both arms keep viewable frames; they differ
    only in the source of experience."""
    src = {"experiential": ENV_EXPERIENTIAL, "expert": ENV_EXPERT,
           "expert_analyzed": ENV_EXPERT_ANALYZED,
           "experiential_analyzed": ENV_EXPERIENTIAL_ANALYZED,
           "ocic_new_analyzed": ENV_OCIC_NEW_ANALYZED,
           "cowork_analyzed": ENV_COWORK_ANALYZED}.get(kind)
    if not src:
        raise ValueError("unknown experience kind: %s" % kind)
    dst = os.path.join(workdir, "experience")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    nfiles = sum(len(fs) for _, _, fs in os.walk(dst))
    log("  experience mounted: %s, %d file(s) under ./experience/ (verbatim copy)" % (kind, nfiles))

# ---- small utils ------------------------------------------------------------

def now(): return time.time()

def ts(): return datetime.datetime.now().strftime("%H:%M:%S")

class Log:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a", buffering=1)
    def __call__(self, msg):
        line = "[%s] %s" % (ts(), msg)
        self.f.write(line + "\n")
        print(line, flush=True)

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)

def child_env():
    """Env for nested claude: strip the CLAUDECODE markers or the child refuses/nests wrong."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("CLAUDECODE") or k.startswith("CLAUDE_CODE"):
            env.pop(k, None)
    return env

def claude_json(prompt, extra_args=None, timeout=ROLLOUT_TIMEOUT_S, cwd=None,
                model=AGENT_MODEL, effort=AGENT_EFFORT):
    """Run one detached `claude -p` and return (parsed_result_dict, raw_stdout, stderr, exit, dur_s)."""
    cmd = ["claude", "-p", prompt, "--model", model, "--effort", effort,
           "--output-format", "json", "--dangerously-skip-permissions"]
    cmd += (extra_args or [])
    t0 = now()
    proc = subprocess.Popen(cmd, cwd=cwd, env=child_env(), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception: pass
        out, err = proc.communicate()
        return None, out or "", (err or "") + "\n[runner] TIMEOUT after %ss" % timeout, -9, now() - t0
    dur = now() - t0
    parsed = None
    try:
        parsed = json.loads(out)
    except Exception:
        m = re.search(r"\{.*\}", out or "", re.S)
        if m:
            try: parsed = json.loads(m.group(0))
            except Exception: pass
    return parsed, out or "", err or "", proc.returncode, dur

def throttled(*texts):
    return any(t and THROTTLE_RE.search(t) for t in texts)

def throttle_wait_s(*texts):
    """Parse a reset-time hint if present, else default. Capped."""
    for t in texts:
        if not t: continue
        m = RESET_HINT_RE.search(t)
        if m:
            try:
                hint = m.group(1).replace(" ", "")
                nowdt = datetime.datetime.now()
                fmt = "%I:%M%p" if ":" in hint else "%I%p"
                tgt = datetime.datetime.strptime(hint.upper(), fmt).replace(
                    year=nowdt.year, month=nowdt.month, day=nowdt.day)
                if tgt <= nowdt: tgt += datetime.timedelta(days=1)
                return min(max((tgt - nowdt).total_seconds() + 120, 300), THROTTLE_MAX_WAIT_S)
            except Exception:
                pass
    return THROTTLE_DEFAULT_WAIT_S

# ---- browser (OCIC adapter) --------------------------------------------------

def _tab_attachable(oc, tab):
    """A wedged tab (crashed page or a browser interstitial) rejects debugger
    attach; probe before trusting it."""
    try:
        r = oc.js(tab, "'ok'") or ""
        return "ok" in r and "attach" not in r.lower()
    except Exception:
        return False

def ocic_fresh_tab(oc, app_url):
    """Create a FRESH tab for every rollout — never reuse. A freshly created
    tab is the active/selected tab of its window, so it renders and its input
    is not throttled. Reuse is what caused the ~5s-per-click stalls: the
    extension now activates a tab only on creation, so a reused tab that has
    since been backgrounded (another origin's tab became active) drives slow.
    Fresh-per-rollout also removes any risk of adopting a stale/interstitial
    tab. The caller closes it on teardown (ocic_close_tab)."""
    made = oc.call("tabs_create_mcp", {})
    m = re.search(r"Tab ID:\s*(\d+)", made or "")
    if not m:
        raise RuntimeError("could not create a workspace tab: %r" % (made or "")[:200])
    # Do NOT probe attachability here: a fresh tab is on chrome://newtab, which
    # the debugger cannot attach to. ocic_seed navigates it to the app origin
    # (attachable) right after; a genuine failure surfaces there and the setup
    # retry handles it.
    return int(m.group(1))

def ocic_close_tab(oc, tab):
    """Best-effort close of a rollout's tab on teardown, so tabs do not pile up
    and nothing is left to reuse."""
    if tab is None:
        return
    try:
        oc.call("tabs_close_mcp", {"tabId": tab})
    except Exception:
        pass

def ocic_seed(oc, tab, app_url, run_id, task_id, log):
    """Full reset: root -> clear -> /config -> assert /finish clean -> back to root."""
    oc.navigate(tab, app_url + "/"); time.sleep(1.4)
    oc.js(tab, "localStorage.clear(); 'ok'"); time.sleep(0.4)
    oc.navigate(tab, "%s/config?run_id=%s&task_id=%s&latency=0" % (app_url, run_id, task_id)); time.sleep(1.8)
    txt = read_finish_text(oc, tab, app_url)
    env = json.loads(txt)
    dirty = _diff_nonempty(env)
    if dirty:
        log("  WARN seed found dirty buckets %s, clearing again" % dirty)
        oc.navigate(tab, app_url + "/"); time.sleep(1.0)
        oc.js(tab, "localStorage.clear(); 'ok'"); time.sleep(0.4)
        oc.navigate(tab, "%s/config?run_id=%s&task_id=%s&latency=0" % (app_url, run_id, task_id)); time.sleep(1.8)
        txt = read_finish_text(oc, tab, app_url)
        env = json.loads(txt)
        dirty = _diff_nonempty(env)
        if dirty:
            raise RuntimeError("environment not fresh after two resets: %s" % dirty)
    oc.navigate(tab, app_url + "/"); time.sleep(1.2)
    return True

def ocic_capture_finish(oc, tab, app_url, out_path):
    txt = read_finish_text(oc, tab, app_url)
    json.loads(txt)  # must be valid
    with open(out_path, "wb") as f:
        f.write(txt.encode("utf-8"))
    env = json.loads(txt)
    oc.navigate(tab, app_url + "/"); time.sleep(0.8)
    return env, len(txt)

# ---- browser (official Claude-in-Chrome adapter, EXP-1B) ---------------------
# The official extension has no spawnable MCP server, so seed/teardown run as
# tiny detached `claude --chrome` orchestration calls (chosen over an
# AppleScript toggle or a CDP relaunch). Documented caveat: /finish capture is
# model-mediated (the orchestration agent copies the JSON out), validated by
# json.loads + run_id + diff-structure checks, not byte-exact like OCIC's
# MCP read.

CINC_ORCH_DIR = os.path.join(WORKROOT, "_cinc_orchestration")
_FINISH_RE = re.compile(r"<FINISH_JSON>\s*(\{.*\})\s*</FINISH_JSON>", re.S)

def cinc_orch_call(prompt, timeout=300):
    os.makedirs(CINC_ORCH_DIR, exist_ok=True)
    parsed, out, err, code, dur = claude_json(
        prompt, extra_args=["--chrome"], timeout=timeout, cwd=CINC_ORCH_DIR,
        model=AGENT_MODEL, effort="low")
    return (parsed or {}).get("result") or "", code, out, err, dur

def cinc_seed(app_url, run_id, task_id, log):
    prompt = """I'm testing my own demo web app and need its browser state reset before a
test run. Please do this with the "claude-in-chrome" browser tools (load them
with one ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true) and create a fresh tab.
2. In that tab, open %s/
3. Clear the app's storage: run localStorage.clear(); sessionStorage.clear()
   with javascript_tool.
4. Open %s/config?run_id=%s&task_id=%s&latency=0
   (this URL seeds the app's test fixture; it is part of the app).
5. After ~2 seconds, open %s/finish and read the JSON it shows (get_page_text).
6. Check both: config.run_id equals "%s", and every bucket under
   "differences" has empty added/deleted/updated. If any bucket is dirty,
   repeat steps 2-5 once.
7. Close the tab you created.

End your reply with the single line "SEED OK" if the check passed, otherwise
"SEED FAIL: <one-line reason>.""" % (app_url, app_url, run_id, task_id, app_url, run_id)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    if code != 0 or "SEED OK" not in text or "SEED FAIL" in text:
        tail = (text.strip().splitlines() or [""])[-1]
        raise RuntimeError("cinc seed failed (exit %s): %s" % (code, (tail or err)[:200]))
    return True

_CINC_TAB_CACHE = os.path.join(DATA, "exp1b-cinc-parity", "workspace_tab.json")

def cinc_ensure_tab(app_url, log, force_new=False):
    """Parity setup: ONE persistent workspace tab for the whole experiment.
    Returns its tabId. Reuses the cached tab when possible; the seed step
    verifies it is actually usable (a dead tab fails the seed, and the retry
    path calls this again with force_new=True). The tab is created ONCE so the
    operator can manually focus it and it stays the window's active tab for
    every rollout (no tab churn, no visibility ambiguity)."""
    if not force_new and os.path.isfile(_CINC_TAB_CACHE):
        try:
            tab = json.load(open(_CINC_TAB_CACHE))["tab"]
            log("  cinc parity: reusing workspace tab %s" % tab)
            return tab
        except Exception:
            pass
    prompt = """I'm setting up a browser test. Using the "claude-in-chrome" browser tools
(load them with one ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true).
2. If the tab group already has a tab, pick the FIRST one and navigate it to
   %s/ . Otherwise create ONE new tab and navigate it to %s/ .
3. Do not create any additional tabs. Do not close anything.

End your reply with the single line "TAB_ID: <number>" for the tab you used.""" % (app_url, app_url)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    m = re.search(r"TAB_ID:\s*(\d+)", text or "")
    if code != 0 or not m:
        raise RuntimeError("cinc parity tab setup failed (exit %s): %s" % (code, (text or err)[-200:]))
    tab = int(m.group(1))
    os.makedirs(os.path.dirname(_CINC_TAB_CACHE), exist_ok=True)
    write_json(_CINC_TAB_CACHE, {"tab": tab, "created": datetime.datetime.now().isoformat(timespec="seconds")})
    log("  cinc parity: workspace tab %d ready on %s" % (tab, app_url))
    return tab

def cinc_seed_parity(tab, app_url, run_id, task_id, log):
    """Seed IN the persistent workspace tab; never create or close tabs.
    Leaves the tab parked on the app root, ready for the agent."""
    prompt = """I'm testing my own demo web app and need its browser state reset before a
test run. Use the "claude-in-chrome" browser tools (load them with one
ToolSearch call if they are deferred). Work ONLY in the existing tab with
tabId %d. Do NOT create, close, or switch tabs.

1. Navigate tabId %d to %s/
2. Clear the app's storage there: run localStorage.clear(); sessionStorage.clear()
   with javascript_tool.
3. Navigate to %s/config?run_id=%s&task_id=%s&latency=0
   (this URL seeds the app's test fixture; it is part of the app).
4. After ~2 seconds, navigate to %s/finish and read the JSON shown (get_page_text).
5. Check both: config.run_id equals "%s", and every bucket under
   "differences" has empty added/deleted/updated. If any bucket is dirty,
   repeat steps 1-4 once.
6. Navigate tabId %d back to %s/ and stop.

End your reply with the single line "SEED OK" if the check passed, otherwise
"SEED FAIL: <one-line reason>.""" % (tab, tab, app_url, app_url, run_id, task_id,
                                     app_url, run_id, tab, app_url)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    if code != 0 or "SEED OK" not in text or "SEED FAIL" in text:
        tail = (text.strip().splitlines() or [""])[-1]
        raise RuntimeError("cinc parity seed failed (exit %s): %s" % (code, (tail or err)[:200]))
    return True

def cinc_capture_finish_parity(tab, app_url, out_path, run_id):
    """Read /finish IN the persistent workspace tab, then park it back on the
    app root. The tab is never closed."""
    prompt = """I'm testing my own demo web app and need to read its end-of-run state.
Use the "claude-in-chrome" browser tools (load them with one ToolSearch call
if they are deferred). Work ONLY in the existing tab with tabId %d. Do NOT
create, close, or switch tabs.

1. Navigate tabId %d to %s/finish and read the JSON it shows with
   get_page_text (if it is not valid JSON yet, wait 2 seconds and read again).
2. Give me back the COMPLETE raw JSON exactly as shown, character for
   character, no commentary and no truncation, wrapped like this:
<FINISH_JSON>
{ ...the json... }
</FINISH_JSON>
3. Navigate tabId %d back to %s/ and stop.""" % (tab, tab, app_url, tab, app_url)
    last_text = ""
    for attempt in (1, 2):
        text, code, out, err, _dur = cinc_orch_call(prompt)
        last_text = text or err
        m = _FINISH_RE.search(text or "")
        if m:
            try:
                env = json.loads(m.group(1))
                if (env.get("config") or {}).get("run_id") == run_id:
                    raw = m.group(1)
                    open(out_path, "wb").write(raw.encode("utf-8"))
                    return env, len(raw)
            except Exception:
                pass
        time.sleep(4)
    raise RuntimeError("cinc parity finish capture failed twice: %s" % last_text[-200:])

def cinc_capture_finish(app_url, out_path, run_id):
    prompt = """I'm testing my own demo web app and need to read its end-of-run state.
Please do this with the "claude-in-chrome" browser tools (load them with one
ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true) and create a fresh tab.
2. Open %s/finish in it and read the JSON it shows with get_page_text (if it
   is not valid JSON yet, wait 2 seconds and read again).
3. Give me back the COMPLETE raw JSON exactly as shown, character for
   character, no commentary and no truncation, wrapped like this:
<FINISH_JSON>
{ ...the json... }
</FINISH_JSON>
4. Close the tab you created.""" % app_url
    last_text = ""
    for attempt in (1, 2):
        text, code, out, err, _dur = cinc_orch_call(prompt)
        last_text = text or err
        m = _FINISH_RE.search(text or "")
        if m:
            try:
                env = json.loads(m.group(1))
                if (env.get("config") or {}).get("run_id") == run_id:
                    raw = m.group(1)
                    open(out_path, "wb").write(raw.encode("utf-8"))
                    return env, len(raw)
            except Exception:
                pass
        time.sleep(4)
    raise RuntimeError("cinc finish capture failed twice: %s" % last_text[-200:])

# ---- transcript --------------------------------------------------------------

def find_transcript(session_id, timeout_s=30):
    """Locate <session_id>.jsonl under ~/.claude/projects (slug-independent)."""
    root = os.path.expanduser("~/.claude/projects")
    deadline = now() + timeout_s
    while now() < deadline:
        for dirpath, _dirs, files in os.walk(root):
            if session_id + ".jsonl" in files:
                return os.path.join(dirpath, session_id + ".jsonl")
        time.sleep(1.5)
    return None

def trajectory_stats(path):
    steps = 0; exec_code = 0; js_tool = 0; model = None
    try:
        for line in open(path, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            msg = rec.get("message") or {}
            if rec.get("type") == "assistant":
                model = msg.get("model") or model
                for b in (msg.get("content") or []):
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        steps += 1
                        name = b.get("name") or ""
                        if "execute_code" in name:
                            exec_code += 1
                        elif "javascript_tool" in name:
                            js_tool += 1
    except FileNotFoundError:
        pass
    return {"tool_calls": steps, "execute_code_calls": exec_code,
            "javascript_tool_calls": js_tool, "model": model}

# ---- evaluation --------------------------------------------------------------

_EVAL_CACHE = {}

def evaluate(task_id, env_state, model_response):
    """REAL's evaluator, exact code; llm_boolean judged through claude."""
    if "cls" not in _EVAL_CACHE:
        TaskConfig, WebCloneEvaluator = _load_real_evaluator()
        evmod = sys.modules["agisdk.REAL.browsergym.webclones.evaluate"]
        def judge(prompt="", model=None, **kw):
            parsed, out, err, code, _d = claude_json(
                prompt + "\n\nAnswer with only the number.",
                extra_args=[], timeout=120, model=JUDGE_MODEL, effort="low")
            if throttled(out, err):
                raise RuntimeError("JUDGE_THROTTLED")
            txt = (parsed or {}).get("result", "") if isinstance(parsed, dict) else ""
            m = re.search(r"[01](?:\.\d+)?", txt or "")
            if not m:
                raise RuntimeError("judge returned no number: %r" % (txt or out)[:120])
            return m.group(0)
        evmod.generate_from_model = judge
        _EVAL_CACHE["cls"] = (TaskConfig, WebCloneEvaluator)
    TaskConfig, WebCloneEvaluator = _EVAL_CACHE["cls"]
    import io, contextlib
    tc = TaskConfig(task_id)
    ev = WebCloneEvaluator(task_config=tc)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reward, done, message, info = ev.evaluate(env_state=env_state, model_response=model_response)
    evals = tc.get_evals(); results = info.get("results", [])
    crit = []
    for i, e in enumerate(evals):
        r = results[i] if i < len(results) else (None, None)
        detail = r[1]
        if isinstance(detail, tuple): detail = list(detail)
        crit.append({"description": getattr(e, "description", ""), "type": e.type,
                     "query": getattr(e, "query", ""), "rubric": getattr(e, "rubric", ""),
                     "expected_value": e.expected_value, "passed": bool(r[0])})
    return {"task_id": task_id, "evaluator": "agisdk.REAL WebCloneEvaluator",
            "judge_model": "claude:" + JUDGE_MODEL + " (REAL default gpt-4o unavailable, no OPENAI_API_KEY)",
            "reward": reward, "passed": all(c["passed"] for c in crit) and bool(crit),
            "message": message, "model_response": model_response,
            "criteria": crit, "grader_stdout": buf.getvalue()}

# ---- the rollout unit ---------------------------------------------------------

def run_rollout(exp_name, exp, task, idx, total, log, buffer_s):
    task_id = task["id"]
    rollout_dir = os.path.join(DATA, exp_name, "%s_r1" % task_id)
    if os.path.exists(os.path.join(rollout_dir, "timing.json")) and \
       os.path.exists(os.path.join(rollout_dir, "evaluation.json")):
        log("ROLLOUT %d/%d %s SKIP (artifacts complete)" % (idx, total, task_id))
        return "skipped"
    os.makedirs(rollout_dir, exist_ok=True)
    fork_args = []
    if exp.get("phase4") or exp.get("p5route"):
        # Fork rollout: restore the study session's workdir VERBATIM at the
        # SAME absolute path (forks only resolve from the session's own
        # project cwd), then fork the checkpointed session. Wiped and
        # re-restored per rollout: independent rollouts, identical start.
        # phase4: fixed study env. p5route: website-matched atomic warm-up.
        if exp.get("p5route"):
            sdir = os.path.join(DATA, "phase5", "warmup_%s" % task["app"])
        else:
            sdir = os.path.join(DATA, "phase4", exp["phase4"] + "_study")
        study = json.load(open(os.path.join(sdir, "study.json")))
        workdir = study["workdir"]
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        with tarfile.open(os.path.join(sdir, "workdir_snapshot.tar.gz")) as tf:
            try:
                tf.extractall(workdir, filter="data")
            except TypeError:  # older python without the filter parameter
                tf.extractall(workdir)
        fork_args = ["--resume", study["session_id"], "--fork-session"]
        log("  fork of %s (%s), workdir snapshot restored" %
            (study["session_id"][:8],
             ("warmup_%s" % task["app"]) if exp.get("p5route") else exp["phase4"] + " study"))
    else:
        workdir = os.path.join(WORKROOT, exp_name, "%s_r1" % task_id)
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        if exp.get("experience"):
            populate_experience(workdir, exp["experience"], log)
    run_id = "%s_%s_r1" % (exp_name, task_id)
    T = {"task_id": task_id, "experiment": exp_name, "run_id": run_id, "attempts": []}

    attempt = 0
    while True:
        attempt += 1
        A = {"attempt": attempt}
        log("ROLLOUT %d/%d %s attempt %d (%s | %s | %s)" %
            (idx, total, task_id, attempt, task["difficulty"], task["challengeType"], task["grading"]))

        # 1 SETUP (transient page/MCP hiccups get one retry before the task errors out)
        A["t_setup_start"] = now()
        if exp["system"] == "cinc":
            tab = None
            try:
                if exp.get("cinc_parity"):
                    tab = cinc_ensure_tab(task["url"], log, force_new=(attempt > 1))
                    cinc_seed_parity(tab, task["url"], run_id, task_id, log)
                else:
                    cinc_seed(task["url"], run_id, task_id, log)
            except Exception as e:
                if attempt < 2:
                    log("  setup failed (%r), retrying rollout" % e)
                    A["outcome"] = "setup_failed"; T["attempts"].append(A)
                    time.sleep(15)
                    continue
                raise
        else:
            oc = OC()
            try:
                tab = ocic_fresh_tab(oc, task["url"])
                ocic_seed(oc, tab, task["url"], run_id, task_id, log)
            except Exception as e:
                if attempt < 2:
                    log("  setup failed (%r), retrying rollout" % e)
                    A["outcome"] = "setup_failed"; T["attempts"].append(A)
                    oc.close()
                    time.sleep(15)
                    continue
                raise
            finally:
                oc.close()
        A["t_setup_end"] = now()
        log("  setup ok, %s fresh, %.1fs" % ("chrome (cinc seed)" if tab is None else "tab %d" % tab,
                                             A["t_setup_end"] - A["t_setup_start"]))

        # 2 RUN
        fmt_kw = {}
        if exp.get("recipe"):
            # recipe text is passed as a format VALUE (its own braces, if any,
            # are never re-processed); authored by the isolated generator.
            fmt_kw["recipe"] = load_recipe(exp["recipe"], task["app"],
                                           exp.get("recipe_dir"))
        prompt = exp["header"].format(tab=tab, app_name=task["app"], app_url=task["url"],
                                      goal=task["goal"], **fmt_kw)
        open(os.path.join(rollout_dir, "prompt.txt"), "w").write(prompt)
        log("  claude launched (model=%s effort=%s)" % (AGENT_MODEL, AGENT_EFFORT))
        A["t_run_start"] = now()
        parsed, out, err, code, dur = claude_json(prompt, extra_args=exp["claude_args"] + fork_args, cwd=workdir)
        A["t_run_end"] = now()
        open(os.path.join(rollout_dir, "result_raw.json"), "w").write(out)
        if err.strip():
            open(os.path.join(rollout_dir, "claude_stderr.log"), "w").write(err)

        result_text = (parsed or {}).get("result") or ""
        session_id = (parsed or {}).get("session_id")
        num_turns = (parsed or {}).get("num_turns")
        is_error = bool((parsed or {}).get("is_error"))

        # throttle -> wait and retry, never scored. ONLY checked when the run
        # actually failed: a successful exit-0 run with a result is never a
        # throttle, and matching its stdout JSON invites false positives
        # (numbers like ttft_ms=1429 once matched a bare '429' pattern and
        # discarded a good rollout). Persist the RAW evidence (what matched,
        # full stdout/stderr/result) to a non-overwritten path so every event
        # is verifiable: real usage cap, 429 burst, 529 overload, or regex FP.
        run_failed = (code != 0) or is_error or not result_text.strip()
        if run_failed and throttled(out, err, result_text):
            wait = throttle_wait_s(out, err, result_text)
            blob = "%s\n%s\n%s" % (out or "", err or "", result_text or "")
            mm = THROTTLE_RE.search(blob)
            matched = mm.group(0) if mm else "?"
            evdir = os.path.join(BENCH, "throttle_evidence")
            os.makedirs(evdir, exist_ok=True)
            evp = os.path.join(evdir, "%s_%s_%s.txt" % (
                exp_name, task_id, datetime.datetime.now().strftime("%H%M%S")))
            open(evp, "w").write(
                "matched: %r\nexit=%s is_error=%s\n\n=== STDOUT ===\n%s\n\n=== STDERR ===\n%s\n\n=== RESULT ===\n%s\n"
                % (matched, code, is_error, out, err, result_text))
            log("  THROTTLED (regex matched %r). Waiting %dm then retrying. Attempt not scored. Evidence: %s"
                % (matched, wait // 60, os.path.relpath(evp, BENCH)))
            A["outcome"] = "throttled"; T["attempts"].append(A)
            time.sleep(wait)
            continue

        # 3 GATE
        gate = []
        if code != 0: gate.append("exit=%s" % code)
        if is_error: gate.append("is_error")
        if not result_text.strip(): gate.append("empty result")
        log("  run done, exit %s, %.1fmin, turns %s" % (code, dur / 60.0, num_turns))
        if gate and attempt < 2:
            log("  GATE FAILED (%s), one retry" % ", ".join(gate))
            A["outcome"] = "gate_failed:" + ",".join(gate); T["attempts"].append(A)
            time.sleep(20)
            continue

        # 4 TEARDOWN
        A["t_teardown_start"] = now()
        if exp["system"] == "cinc":
            if exp.get("cinc_parity"):
                env_state, fbytes = cinc_capture_finish_parity(
                    tab, task["url"], os.path.join(rollout_dir, "finish.json"), run_id)
            else:
                env_state, fbytes = cinc_capture_finish(task["url"],
                                                        os.path.join(rollout_dir, "finish.json"), run_id)
        else:
            oc = OC()
            try:
                env_state, fbytes = ocic_capture_finish(oc, tab, task["url"],
                                                        os.path.join(rollout_dir, "finish.json"))
                ocic_close_tab(oc, tab)  # teardown: remove the rollout's tab
            finally:
                oc.close()
        traj = find_transcript(session_id) if session_id else None
        stats = {"tool_calls": 0, "execute_code_calls": 0, "model": None}
        if traj:
            shutil.copyfile(traj, os.path.join(rollout_dir, "trajectory.jsonl"))
            stats = trajectory_stats(os.path.join(rollout_dir, "trajectory.jsonl"))
        else:
            log("  WARN transcript not found for session %s" % session_id)
        A["t_teardown_end"] = now()
        if stats["tool_calls"] < MIN_TOOL_CALLS:
            gate.append("suspect_lazy(tool_calls=%d)" % stats["tool_calls"])
        if stats["execute_code_calls"] and not exp["execute_code_allowed"]:
            gate.append("VIOLATION:execute_code_used=%d" % stats["execute_code_calls"])
        # cinc's header bans javascript_tool (its execute_code analog)
        if exp["system"] == "cinc" and stats["javascript_tool_calls"] and not exp["execute_code_allowed"]:
            gate.append("VIOLATION:javascript_tool_used=%d" % stats["javascript_tool_calls"])
        log("  teardown ok, finish %dB, steps %d, execute_code %d%s" %
            (fbytes, stats["tool_calls"], stats["execute_code_calls"],
             (", GATE FLAGS: " + ",".join(gate)) if gate else ""))

        # 5 EVALUATE
        A["t_eval_start"] = now()
        try:
            ev = evaluate(task_id, env_state, result_text)
        except RuntimeError as e:
            if "JUDGE_THROTTLED" in str(e):
                log("  judge throttled, waiting 15m and re-evaluating")
                time.sleep(900)
                ev = evaluate(task_id, env_state, result_text)
            else:
                ev = {"task_id": task_id, "error": str(e)}
        except Exception as e:
            ev = {"task_id": task_id, "error": str(e)}
        A["t_eval_end"] = now()
        write_json(os.path.join(rollout_dir, "evaluation.json"), ev)
        passed = ev.get("passed")
        log("  eval %s (%s)" % ("PASS" if passed else ("FAIL" if passed is False else "ERROR"),
            ", ".join("%s:%s" % (c["description"][:28], "ok" if c["passed"] else "X")
                      for c in ev.get("criteria", [])) or ev.get("error", "")[:80]))

        A["outcome"] = "completed"
        T["attempts"].append(A)
        T.update({
            "gate_flags": gate, "session_id": session_id, "exit_code": code,
            "num_turns": num_turns, "tool_calls": stats["tool_calls"],
            "execute_code_calls": stats["execute_code_calls"],
            "javascript_tool_calls": stats["javascript_tool_calls"], "agent_model": stats["model"],
            "passed": passed,
            "durations_s": {
                "setup": round(A["t_setup_end"] - A["t_setup_start"], 2),
                "run": round(A["t_run_end"] - A["t_run_start"], 2),
                "teardown": round(A["t_teardown_end"] - A["t_teardown_start"], 2),
                "eval": round(A["t_eval_end"] - A["t_eval_start"], 2),
                "rollout_total": round(A["t_eval_end"] - A["t_setup_start"], 2),
            },
        })
        write_json(os.path.join(rollout_dir, "timing.json"), T)
        log("  rollout total %.1fmin (run %.1fmin). artifacts -> %s" %
            (T["durations_s"]["rollout_total"] / 60.0, T["durations_s"]["run"] / 60.0,
             os.path.relpath(rollout_dir, BENCH)))
        return "completed"

# ---- commands ------------------------------------------------------------------

def cmd_run(a):
    manifest = json.load(open(MANIFEST))
    exp = EXPERIMENTS[a.experiment]
    if exp["system"] not in ("ocic", "cinc"):
        sys.exit("experiment %s: no adapter for system %s" % (a.experiment, exp["system"]))
    order = list(manifest[exp["split"]])
    if a.only:
        wanted = [x.strip() for x in a.only.split(",") if x.strip()]
        order = [t for t in order if t in wanted]
        if not order: sys.exit("task(s) %s not in %s" % (a.only, exp["split"]))
    if a.limit: order = order[:a.limit]
    tasks = manifest["tasks"]

    logpath = os.path.join(LOGS, "%s_%s.log" % (a.experiment, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    log = Log(logpath)
    log("EXPERIMENT %s: %d rollout(s), model=%s effort=%s, buffer=%ds" %
        (a.experiment, len(order), AGENT_MODEL, AGENT_EFFORT, a.buffer))
    log("log file: %s" % logpath)
    t0 = now()
    outcomes = {}
    for i, tid in enumerate(order, 1):
        try:
            outcomes[tid] = run_rollout(a.experiment, exp, tasks[tid], i, len(order), log, a.buffer)
        except Exception as e:
            # A rollout failure must never kill the experiment: log, mark, move on.
            log("  ERROR rollout %s: %r. Continuing with the next task." % (tid, e))
            outcomes[tid] = "error"
        write_json(os.path.join(DATA, a.experiment, "status.json"),
                   {"experiment": a.experiment, "done": i, "total": len(order),
                    "outcomes": outcomes, "updated": datetime.datetime.now().isoformat(timespec="seconds")})
        if i < len(order) and outcomes[tid] != "skipped":
            log("  buffer %ds (rate-limit headroom)" % a.buffer)
            time.sleep(a.buffer)
    total_min = (now() - t0) / 60.0
    completed = [t for t, o in outcomes.items() if o == "completed"]
    summary = {"experiment": a.experiment, "started": datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
               "wall_clock_min": round(total_min, 2), "rollouts": outcomes,
               "completed": len(completed), "skipped": len(order) - len(completed)}
    write_json(os.path.join(DATA, a.experiment, "summary.json"), summary)
    log("EXPERIMENT %s DONE in %.1fmin (%d completed, %d skipped). summary.json written."
        % (a.experiment, total_min, summary["completed"], summary["skipped"]))

def cmd_preflight(_a):
    ok = True
    def chk(name, fn):
        nonlocal ok
        try:
            v = fn()
            print("  OK  %-34s %s" % (name, v if v is not True else ""))
        except Exception as e:
            ok = False
            print("  FAIL %-34s %s" % (name, e))
    print("preflight:")
    chk("manifest", lambda: "%d train / %d test" % (
        len(json.load(open(MANIFEST))["train_order"]), len(json.load(open(MANIFEST))["test_order"])))
    chk("claude CLI", lambda: subprocess.run(["claude", "--version"], capture_output=True, text=True,
                                             env=child_env()).stdout.strip())
    chk("effort flag", lambda: "--effort" in subprocess.run(["claude", "--help"], capture_output=True,
                                                            text=True, env=child_env()).stdout or exec('raise ValueError("missing")'))
    def _tabs():
        oc = OC()
        try:
            first = (oc.tabs() or "").strip().split("\n")[0]
            return "OCIC alive, %d tab(s)" % len(json.loads(first).get("availableTabs", []))
        finally:
            oc.close()
    chk("OCIC MCP (Brave)", _tabs)
    import urllib.request
    apps = {}
    try:
        man = json.load(open(MANIFEST))
        apps = {t["app"]: t["url"] for t in man["tasks"].values()}
    except Exception:
        pass
    for app, url in sorted(apps.items()):
        chk("app " + app, lambda u=url: urllib.request.urlopen(u, timeout=15).status)
    chk("jmespath", lambda: __import__("jmespath").__name__)
    chk("evaluator loads", lambda: bool(_load_real_evaluator()))
    chk("workroot", lambda: os.makedirs(WORKROOT, exist_ok=True) or WORKROOT)
    print("preflight:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

def _tab_ids(oc):
    """Set of tab ids currently in the MCP group (best-effort)."""
    try:
        return set(int(x) for x in re.findall(r'"tabId":\s*(\d+)', oc.tabs() or ""))
    except Exception:
        return set()

def cmd_p4study(a):
    """Phase-4 study session: build the checkpoint that fork rollouts resume.

    --arm expert       one session, expert recordings mounted at ./experience/,
                       deep-internalization prompt; browser at its own
                       discretion (never mentioned); duration tracked.
    --arm experiential one session that PERFORMS the 6 train tasks
                       sequentially (standard per-task setup/seed/teardown;
                       plain --resume between segments keeps one session id).

    Output: data/phase4/<arm>_study/{study.json, trajectory.jsonl,
    workdir_snapshot.tar.gz, result artifacts}. Model/effort: the global
    AGENT_MODEL/AGENT_EFFORT — identical to every other experiment.
    """
    man = json.load(open(MANIFEST))
    arm = a.arm
    outdir = os.path.join(DATA, "phase4", "%s_study" % arm)
    os.makedirs(outdir, exist_ok=True)
    log = Log(os.path.join(LOGS, "p4study_%s_%s.log" % (
        arm, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))))
    workdir = os.path.join(WORKROOT, "p4_%s_study" % arm)
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)
    # Study effort is configurable (--effort); the expert internalization study
    # runs at "max" by request. Model is ALWAYS the global AGENT_MODEL (sonnet).
    # Train segments (experiential arm) and all fork rollouts stay at the
    # uniform AGENT_EFFORT (medium).
    study_effort = a.effort
    study = {"arm": arm, "workdir": workdir, "model": AGENT_MODEL,
             "effort": study_effort if arm == "expert" else AGENT_EFFORT,
             "started": datetime.datetime.now().isoformat(timespec="seconds")}
    t0 = now()

    if arm == "expert":
        populate_experience(workdir, "expert", log)
        oc = OC()
        try: tabs_before = _tab_ids(oc)
        finally: oc.close()
        log("expert study launched (model=%s effort=%s, timeout %ds); browser at its discretion"
            % (AGENT_MODEL, study_effort, a.timeout))
        parsed, out, err, code, dur = claude_json(
            P4_EXPERT_STUDY_PROMPT, cwd=workdir, timeout=a.timeout,
            effort=study_effort)
        open(os.path.join(outdir, "result_raw.json"), "w").write(out)
        if err.strip():
            open(os.path.join(outdir, "claude_stderr.log"), "w").write(err)
        sid = (parsed or {}).get("session_id")
        result = (parsed or {}).get("result") or ""
        if code != 0 or not sid or not result.strip():
            sys.exit("study session failed: exit=%s sid=%s empty_result=%s"
                     % (code, sid, not result.strip()))
        study.update(session_id=sid, study_run_s=round(dur, 1),
                     num_turns=(parsed or {}).get("num_turns"))
        # close any tabs the study opened (browser use was its own choice)
        oc = OC()
        try:
            opened = _tab_ids(oc) - tabs_before
            for t in sorted(opened):
                try: oc.call("tabs_close_mcp", {"tabId": t})
                except Exception: pass
        finally:
            oc.close()
        study["tabs_opened_during_study"] = len(opened)
        log("study done: %.1fmin, %s turns, sid %s, %d tab(s) opened by the agent"
            % (dur / 60.0, study["num_turns"], sid, len(opened)))
    elif arm == "experiential":
        tasks = man["tasks"]; order = list(man["train_order"])
        sid = None; segments = []
        for i, tid in enumerate(order, 1):
            task = tasks[tid]
            run_id = "p4study_%s" % tid
            oc = OC()
            try:
                tab = ocic_fresh_tab(oc, task["url"])
                ocic_seed(oc, tab, task["url"], run_id, tid, log)
            finally:
                oc.close()
            log("SEGMENT %d/%d %s (tab %d)" % (i, len(order), tid, tab))
            if sid is None:
                prompt = P4_TRAIN_HEADER.format(tab=tab, app_name=task["app"],
                                                app_url=task["url"], goal=task["goal"])
                extra = []
            else:
                prompt = P4_TRAIN_CONT.format(tab=tab, app_name=task["app"],
                                              app_url=task["url"], goal=task["goal"])
                extra = ["--resume", sid]
            parsed, out, err, code, dur = claude_json(prompt, extra_args=extra, cwd=workdir)
            open(os.path.join(outdir, "%s_result_raw.json" % tid), "w").write(out)
            if err.strip():
                open(os.path.join(outdir, "%s_stderr.log" % tid), "w").write(err)
            new_sid = (parsed or {}).get("session_id")
            result = (parsed or {}).get("result") or ""
            if code != 0 or not new_sid or not result.strip():
                sys.exit("segment %s failed: exit=%s sid=%s empty_result=%s"
                         % (tid, code, new_sid, not result.strip()))
            if sid is None:
                sid = new_sid
            elif new_sid != sid:
                sys.exit("session id changed on resume (%s -> %s); aborting" % (sid, new_sid))
            oc = OC()
            try:
                env_state, _ = ocic_capture_finish(
                    oc, tab, task["url"], os.path.join(outdir, "%s_finish.json" % tid))
                ocic_close_tab(oc, tab)
            finally:
                oc.close()
            try:
                ev = evaluate(tid, env_state, result)
            except Exception as e:
                ev = {"task_id": tid, "error": str(e)}
            write_json(os.path.join(outdir, "%s_evaluation.json" % tid), ev)
            segments.append({"task": tid, "passed": ev.get("passed"),
                             "run_s": round(dur, 1),
                             "num_turns": (parsed or {}).get("num_turns")})
            log("  segment done %.1fmin, eval %s" % (dur / 60.0, ev.get("passed")))
            if i < len(order):
                time.sleep(20)
        study.update(session_id=sid, segments=segments)
    else:
        sys.exit("unknown arm %r" % arm)

    traj = find_transcript(study["session_id"])
    if traj:
        shutil.copyfile(traj, os.path.join(outdir, "trajectory.jsonl"))
    else:
        log("WARN study transcript not found for %s" % study["session_id"])
    snap = os.path.join(outdir, "workdir_snapshot.tar.gz")
    with tarfile.open(snap, "w:gz") as tf:
        tf.add(workdir, arcname=".")
    study["duration_s"] = round(now() - t0, 1)
    study["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_json(os.path.join(outdir, "study.json"), study)
    log("STUDY %s COMPLETE in %.1fmin: sid=%s. study.json + snapshot written to %s"
        % (arm, study["duration_s"] / 60.0, study["session_id"], os.path.relpath(outdir, BENCH)))

P5_WARMUP_TASKS = {"dashdish": "dashdish-4", "zilloft": "zilloft-8"}

def cmd_p5warmup(a):
    """Phase-5 atomic warm-ups: per website, ONE train task performed in ONE
    session (standard seed/teardown, silent single-task header), checkpointed
    for website-routed forking. Chosen tasks: dashdish-4 (broadest cart and
    checkout coverage) and zilloft-8 (broadest filter coverage); train set only.
    Output: data/phase5/warmup_<app>/{study.json, workdir_snapshot.tar.gz,
    trajectory.jsonl, finish/evaluation artifacts}."""
    man = json.load(open(MANIFEST))
    log = Log(os.path.join(LOGS, "p5warmup_%s.log" %
                           datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    for app, tid in P5_WARMUP_TASKS.items():
        outdir = os.path.join(DATA, "phase5", "warmup_%s" % app)
        if os.path.isfile(os.path.join(outdir, "study.json")) and not a.force:
            log("warmup_%s already exists, skipping (use --force to redo)" % app)
            continue
        os.makedirs(outdir, exist_ok=True)
        task = man["tasks"][tid]
        workdir = os.path.join(WORKROOT, "p5_warmup_%s" % app)
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        run_id = "p5warmup_%s" % tid
        # A warm-up checkpoint must contain CLEAN experience: retry once on
        # any infrastructure failure (browser drop, dead tab, capture error)
        # and require the task to actually PASS. A session whose memory is
        # "the browser broke" would poison every fork that resumes it.
        ev = None; sid = None
        for attempt in (1, 2):
            workdir_ok = True
            shutil.rmtree(workdir, ignore_errors=True)
            os.makedirs(workdir, exist_ok=True)
            try:
                oc = OC()
                try:
                    tab = ocic_fresh_tab(oc, task["url"])
                    ocic_seed(oc, tab, task["url"], run_id, tid, log)
                finally:
                    oc.close()
                log("WARMUP %s: task %s attempt %d (tab %d)" % (app, tid, attempt, tab))
                prompt = P4_TRAIN_HEADER.format(tab=tab, app_name=task["app"],
                                                app_url=task["url"], goal=task["goal"])
                parsed, out, err, code, dur = claude_json(prompt, cwd=workdir)
                open(os.path.join(outdir, "result_raw.json"), "w").write(out)
                if err.strip():
                    open(os.path.join(outdir, "stderr.log"), "w").write(err)
                sid = (parsed or {}).get("session_id")
                result = (parsed or {}).get("result") or ""
                if code != 0 or not sid or not result.strip():
                    raise RuntimeError("run gate: exit=%s sid=%s" % (code, sid))
                oc = OC()
                try:
                    env_state, _ = ocic_capture_finish(oc, tab, task["url"],
                                                       os.path.join(outdir, "finish.json"))
                    ocic_close_tab(oc, tab)
                finally:
                    oc.close()
                ev = evaluate(tid, env_state, result)
                write_json(os.path.join(outdir, "evaluation.json"), ev)
                # A clean completion is valid warm-up experience whether or not
                # it PASSED: the fork inherits the experience of ATTEMPTING the
                # task (phase-4 kept its failed segments too). Retry only on
                # INFRASTRUCTURE failure (handled by the exceptions above:
                # browser drop, teardown error, empty result, exit != 0).
                log("  warmup %s completed (eval passed=%s) - accepting as experience"
                    % (app, ev.get("passed")))
                break
            except Exception as e:
                log("  warmup %s attempt %d failed: %r" % (app, attempt, e))
                if attempt == 2:
                    sys.exit("warmup %s failed twice; aborting" % app)
                time.sleep(60)
        traj = find_transcript(sid)
        if traj:
            shutil.copyfile(traj, os.path.join(outdir, "trajectory.jsonl"))
        snap = os.path.join(outdir, "workdir_snapshot.tar.gz")
        with tarfile.open(snap, "w:gz") as tf:
            tf.add(workdir, arcname=".")
        write_json(os.path.join(outdir, "study.json"),
                   {"arm": "warmup_%s" % app, "task": tid, "workdir": workdir,
                    "session_id": sid, "model": AGENT_MODEL, "effort": AGENT_EFFORT,
                    "run_s": round(dur, 1), "num_turns": (parsed or {}).get("num_turns"),
                    "passed": ev.get("passed"),
                    "created": datetime.datetime.now().isoformat(timespec="seconds")})
        log("WARMUP %s DONE: %.1fmin, %s turns, eval %s, sid %s" %
            (app, dur / 60.0, (parsed or {}).get("num_turns"), ev.get("passed"), sid))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight"); p.set_defaults(fn=cmd_preflight)
    r = sub.add_parser("run")
    r.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    r.add_argument("--only", default=None)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--buffer", type=int, default=45)
    r.set_defaults(fn=cmd_run)
    s4 = sub.add_parser("p4study")
    s4.add_argument("--arm", required=True, choices=["expert", "experiential"])
    s4.add_argument("--timeout", type=int, default=5400,
                    help="hard cap for the expert study session (s)")
    s4.add_argument("--effort", default=AGENT_EFFORT,
                    choices=["low", "medium", "high", "xhigh", "max"],
                    help="effort for the expert STUDY session only "
                         "(train segments and fork rollouts stay at %s)" % AGENT_EFFORT)
    s4.set_defaults(fn=cmd_p4study)
    s5 = sub.add_parser("p5warmup")
    s5.add_argument("--force", action="store_true")
    s5.set_defaults(fn=cmd_p5warmup)
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()

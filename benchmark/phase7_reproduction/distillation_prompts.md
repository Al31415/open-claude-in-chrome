# The phase-7 distillation prompts (verbatim)

All four artifact sets were authored by isolated `claude -p` sessions, one per
set, before any phase-7 arm ran. This file preserves those prompts verbatim.

## Session facts

- Model: `claude-fable-5`, max effort, for all four sets. Every benchmark
  rollout arm ran Sonnet medium; the distiller was deliberately the stronger
  model, matching the 5b/6b precedent in `../6b_reproduction/`.
- Working directory per set: `~/.bench_rollouts/p7_<regime>_<system>/`,
  containing ONLY `experience/` - that system's six sources plus a README
  describing the format. No repo, no manifests, no test tasks, no evaluator,
  no other arm's material.
- Driver: `../run_p7_distill.py`. Environments assembled by
  `../build_p7_envs.py`, which also runs the leakage audit.
- Outputs: `distilled/<system>_ANALYSIS_<site>.md` and
  `distilled/<system>_RECIPE_<site>.md`.

The ONLY difference between the OCIC and Cowork runs of each prompt is the
parenthetical describing the source material, substituted at `{src}`:

- OCIC: `(its README.md explains the source: an expert operator's browser
  recordings, four tracks on one clock, covering 6 earlier tasks)`
- Cowork: `(its README.md explains the source: one generated markdown artifact
  per task, produced automatically by the recording system at capture time,
  covering 6 earlier tasks)`

Everything else - the requirements, the generality rule, the word budgets, the
filesystem boundary, the completion sentinel - is identical across systems.

## Phase-3 regime: the analysis documents (verbatim)

These are reference documents mounted on disk in the rollout workspace; the
agent is told to read the one for its site before acting.

```
[EXPERIENCE ANALYSIS SESSION]
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
"ANALYSIS COMPLETE".
```

## Phase-5 regime: the recipes (verbatim)

These ride inside the task prompt, site-routed exactly as 5b and 6b do. This
prompt is the 5b recipe-authoring prompt, adapted only for the single source
and for two files instead of three (the combined recipe is used by 5a, which
phase 7 does not reproduce). The generality rule, the non-distracting rule and
the word budget are unchanged from the original.

```
[RECIPE AUTHORING SESSION]
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
"RECIPES COMPLETE".
```

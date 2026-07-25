# The recipe-generation prompt (verbatim)

The recipe used by 6b (and 5b) was authored ONCE, before any phase-5/6 arm ran,
by an isolated Claude Code session. This file preserves that session's prompts
verbatim, plus the session facts needed to reproduce or audit it.

## Session facts

- Model: `claude-fable-5` (max effort), while every benchmark rollout arm ran
  Sonnet medium. The distiller was deliberately a stronger model than the
  executor.
- Working directory: `~/.bench_rollouts/p5_recipegen/` containing ONLY the
  `experience/` material (see `workspace_contents.md`). The prompt confines the
  session to that directory; it never touched the benchmark repo, the target
  sites, or a browser.
- Outputs: `RECIPE_dashdish.md` (633 words), `RECIPE_zilloft.md` (645 words),
  `RECIPE_combined.md` (846 words), written in place, then copied by
  `run_phase5_chain.sh` into `environments/recipes/` after an independent
  leakage audit passed.
- Session stats: 17 turns, 8.1 minutes, $28.15, ~36k output tokens,
  ~1.49M cache-read tokens.
- Full transcript:
  `~/.claude/projects/-Users-seb--bench-rollouts-p5-recipegen/b84737cf-c640-49e9-ad15-f9ce73087d5e.jsonl`
- Runner integration: `runner.py` `load_recipe(kind, app)`; 5b and 6b use
  `kind="site"` (per-app file picked at rollout time), 5a uses `kind="single"`.

## What the session actually did (from the transcript)

1. Inventoried `experience/`, read all three READMEs and the expert
   `SCHEMA_v0.md`, sampled both raw trace formats.
2. Fanned out six parallel subagents, one per train task, each told to study
   BOTH sources (its own trace + the expert recording) for that task and
   report the app's operating mechanics. The per-task analyst prompt is below;
   this is the "analysis over the workspace" step.
3. Spot-checked four screenshots itself across both apps.
4. Wrote the three recipes, then self-audited: word counts against the
   budgets and a grep leak-scan for train-task identifiers, followed by
   several tightening edit passes and a final re-scan.

## The main prompt (verbatim)

```
[RECIPE AUTHORING SESSION]
You are preparing OPERATING RECIPES for autonomous browser agents that will
complete tasks in two demo web apps: dashdish (food delivery) and zilloft
(real estate). You have prior experience material at ./experience/ (its
README.md explains the two sources: an AI agent's own traces and a human
operator's recordings, covering 6 earlier tasks). Study it thoroughly, both
sources, every task, before writing anything.

Then write EXACTLY three files in the current directory:

1. RECIPE_dashdish.md  - recipe for dashdish only
2. RECIPE_zilloft.md   - recipe for zilloft only
3. RECIPE_combined.md  - ONE recipe covering both apps

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
  ~600 words each; combined at most ~900 words.
- Plain markdown, no links, no images.

Boundary: this working directory is your ONLY filesystem environment. Do not
read, list, write, or search any path outside it.

When the three files are written, end your reply with the single line
"RECIPES COMPLETE".
```

## The per-task trace-analyst subagent prompt (verbatim, dashdish-3 instance)

Six of these ran in parallel, differing only in the task line and paths.

```
You are a trace analyst. Study TWO recordings of the same browser task and extract the OPERATING MECHANICS of the web app, for me to distill into an operating recipe. Do NOT write any files; return your report as your final message. Only read paths under /Users/seb/.bench_rollouts/p5_recipegen/experience/ — nothing else on the filesystem.

TASK RECORDED (earlier benchmark task): dashdish-3 — "How many restaurants in the 'Light & fresh' category offer delivery?" on the demo food-delivery app dashdish (https://evals-dashdish.vercel.app).

SOURCE 1 — AI agent's own session (Claude Code JSONL):
/Users/seb/.bench_rollouts/p5_recipegen/experience/experiential/dashdish-3/trace.jsonl
Each line is a JSON object (user/assistant messages, tool_use, tool_result). Screenshots were replaced with text refs like "[screenshot → images/NNNN.jpg]"; the image files live in the sibling images/ dir. Parse it with python3: for each line print message role, any tool_use blocks (tool name + full input), tool_result content (truncate very long ones to ~1500 chars but KEEP page-text outputs long enough to see the app's text/DOM structure), and assistant text/thinking (these contain reasoning about failures and retries). The browser tools are mcp__...__screenshot/computer, navigate, find, read_page, get_page_text, form_input, etc.

SOURCE 2 — human expert recording of the same task:
/Users/seb/.bench_rollouts/p5_recipegen/experience/expert/dashdish-3/trace.json
One JSON object with parallel tracks on one clock (ms since started_at): behavior[] = discrete actions, each with a replayable "command" (tool+input, viewport-px coordinates), plus "anchor" (selector/role/name/text of the element clicked) and "effect" (what changed after); cursor[] = pointer samples (attention); cognitive[] = transcribed narration (the operator's spoken reasoning — the WHY; quote the useful parts); images[] = 240p frame refs. Use python3 to walk behavior[] in time order printing t, action, command.input, anchor.name/text/selector, effect summary — and interleave cognitive[] segments by t. Events flagged "inferred": true (hover/drag) are heuristic; trust clicks/type/key/scroll/navigate. For a same-position click burst (left_click then double_click), the last event is what really happened.

You may open a FEW image files (Read tool renders .jpg) if the text leaves a layout genuinely ambiguous — max ~8 images total, prefer the AI trace's screenshots (higher res).

EXTRACT AND REPORT (structured markdown, exhaustive on mechanics, terse on narrative):
1. APP MECHANICS — URL routes seen (base URL, paths, query params), homepage layout, how categories are found/selected (chips? scroll? URL?), what a restaurant card shows and how DELIVERY availability is signaled per restaurant (badge text? toggle? fee line? "Pickup only" markers?), any result-count text the app itself displays, pagination/lazy-load/scrolling behavior, any Delivery/Pickup toggle affecting the listing.
2. ROUTE TAKEN — the AI's actual step sequence (tools + what each accomplished), then the expert's step sequence, then the KEY DIVERGENCES (who was faster/more reliable and why).
3. TOOL TACTICS — where text extraction (get_page_text / read_page / find) beat screenshots or vice versa, especially for COUNTING items; scroll tactics; anything about coordinate clicks missing and what fixed it.
4. FAILURE MODES / SILENT TRAPS — anything that failed, misled, or silently didn't apply (e.g., category click not filtering, hidden items requiring scroll, counting duplicates, off-screen elements), and the fix.
5. EXPERT NARRATION INSIGHTS — quote/paraphrase every generalizable piece of operator know-how from cognitive[].
6. OUTCOME — did each run reach a confident answer? How did they VERIFY the count (method, not the number)?
7. TASK-SPECIFIC VALUES (quarantine section, keep minimal) — the specific category name, counts, restaurant names involved, so I know what to EXCLUDE from the recipe.

Generic UI labels (e.g. "Delivery", "Pickup", button captions, filter names) are mechanics — report them verbatim. Be precise and complete; this report is my only view into these traces.
```

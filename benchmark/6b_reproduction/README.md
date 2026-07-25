# 6b reproduction

6b (`exp5d-warmup-recipe`) is the study's winning arm: a website-routed atomic
warm-up fork PLUS the per-site recipe injected into the task prompt. This
directory documents how its two ingredients were made, verbatim, and offers
hypotheses for why the recipe worked and what warm-up design should work best.

Files here:

- `recipe_generation_prompt.md` - the exact prompt(s) that authored the
  recipe, plus session facts and what the generator session actually did.
- `workspace_contents.md` - what the generator could see: the experience
  material, its formats, and its byte-level provenance.

The three recipes themselves live at `environments/recipes/RECIPE_*.md`
(dashdish 633 words, zilloft 645, combined 846). 6b and 5b load the per-site
file at rollout time (`load_recipe("site", app)` in `runner.py`); 5a loads the
combined file. Same files, generated once, shared across all recipe arms.

## How 6b assembles at rollout time

1. Warm-up checkpoints (made once, before the arms): per site, ONE train task
   run in one session under the silent single-task header - dashdish-4
   (45 turns, 2.9 min, passed) and zilloft-8 (34 turns, 2.2 min, passed),
   chosen for broadest cart/checkout and filter coverage respectively.
   Session id + workdir snapshot saved (`data/phase5/warmup_<app>/`).
2. Per test rollout: the warm-up workdir is restored verbatim at the same
   absolute path, the checkpointed session is forked
   (`--resume <sid> --fork-session`), routed by the task's website.
3. The task prompt uses the fork header plus the recipe block: "Field notes
   for {app}, compiled by an earlier agent from prior runs on similar tasks
   in this same app (use what helps; ignore what does not)" followed by the
   site recipe text.

So the agent starts with ~99k tokens of its own recent successful experience
on that site in context, and the distilled mechanics of that site in the
prompt. Result: 24.1 turns/task and 20.9 min suite (cold triad: 32.9 turns,
24.8 min), 11/12 accuracy, best of all 13 arms on both axes.

## Hypotheses: what made the recipe effective

**The workspace content.** Two independent perspectives on the same 6 tasks.
The agent's own traces contain the failure modes: retries, dead ends, and the
reasoning around them - which is exactly the "what silently fails" knowledge
that generalizes. The expert recordings contain the efficient routes plus a
narration track, the only place where intent is written next to action; the
validation habit that later showed up across expert-derived arms ("I'm just
going to double check") lives there. One source alone shows what happened;
two let the distiller triangulate what is a stable mechanic of the app versus
a one-off fluke. Deliberate exclusions mattered as much: no finish/evaluation
artifacts, no test tasks, so the recipe could not memorize answers even in
principle and was forced to be about mechanics.

**The prompt.** Four load-bearing constraints:
- The generality rule (no answers, counts, prices, names) doubles as leakage
  control AND as a forcing function toward transferable knowledge. Told "HOW
  the apps behave, never WHAT some earlier answer was", the model must write
  mechanics.
- The consumption context is stated ("this text rides inside a task prompt")
  with hard word budgets. That produced a terse imperative artifact that
  informs without distracting - phase 2/3 showed that undigested experience
  costs turns to consume; the budgets prevent the recipe from becoming that.
- An explicit quality bar ("what a top operator would hand a new agent") and
  an explicit ask for tool tactics (when text extraction beats screenshots,
  when direct form-value set beats clicking) pull out the cross-cutting
  advice that pays on every task.
- A clean contract: exactly three files, a completion sentinel, a hard
  filesystem boundary.

**The model.** The distiller was Fable 5 at max effort while every executor
ran Sonnet medium: a strong-to-weak transfer where the expensive model spends
its capability once ($28, 8 minutes) and the cheap model benefits on every
rollout. The transcript shows the strong model earning that: it fanned out
six parallel trace-analyst subagents (one per task, both sources each),
synthesized their reports, then self-audited word counts and ran its own
leak-scan greps before the pipeline's independent audit, iterating with
tightening edits until clean.

Ranked guess at contribution: prompt constraints > dual-source content >
distiller model strength. The same content with a lax prompt would have
produced a long narrative digest (phase 3 already showed digests underperform
prompts); a weaker distiller with the same prompt would likely have produced
a recipe, just a blunter one.

## Hypothesis: what type of warm-up would be most effective

What the data show: the single-task warm-up captured essentially ALL of the
full 6-task fork's turn savings (6a: 26.4 turns vs 4a: 26.2) at a fraction of
the context (~99k vs ~365k tokens) and none of its latency catastrophe
(25.0 min vs 56.5). But warm-up alone did not beat cold on latency: fewer
turns were cancelled by a higher per-turn cost (4.72 s/turn vs ~3.6 cold).
Only with the recipe on top (6b: 4.38 s/turn, 24.1 turns) did total time
collapse. And the ratio charts show 6a is the one arm whose relative cost
RISES with task length, while recipe arms fall.

Reading: a warm-up buys procedural fluency (a fast, confident start; the
session "knows" the site), and its value per token saturates after roughly
one task, while its context tax is paid on every turn forever. The recipe
buys declarative mechanics that keep paying as tasks get longer. They are
complements, not substitutes.

So the most effective warm-up should maximize mechanic coverage per token of
retained context. Concretely, ranked predictions:

1. **A trimmed checkpoint.** Take the existing single-task warm-up and prune
   the transcript before checkpointing: drop screenshot payloads and bulky
   tool results, keep the action-observation-reasoning skeleton. If ~99k
   compresses to ~25k with the procedure intact, per-turn latency should
   drop most of the way back to cold while keeping 6a's turn savings; 6b
   rebuilt on that checkpoint should beat current 6b outright.
2. **A purpose-built guided tour.** Instead of an organic task, one scripted
   warm-up that touches each core mechanic exactly once (search, filter,
   count results, fill a form, validate an unresponsive control). An organic
   task exercises one path; a tour maximizes coverage per token. Slightly
   riskier: it is synthetic experience, and the fork's value may partly come
   from the memory of a real completed success.
3. **Mechanic-matched routing.** Route the fork not just by site but by task
   type (counting/filter tasks vs cart/form tasks), so the in-context episode
   is the most similar prior procedure available. Costs one extra checkpoint
   per site.
4. **What NOT to do: more tasks.** 4a is the limit case - six warmup tasks,
   ~365k tokens, best-in-study turn count, worst-in-study latency. Volume
   adds tax faster than it adds fluency.

In all cases, keep two invariants from the current design: the warm-up must
end in a clean completion (a session whose memory is "the browser broke"
poisons every fork), and it must be train-set only.

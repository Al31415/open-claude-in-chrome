# Phase 7 reproduction

Phase 7 asks one question: does OCIC's way of recording an expert demonstration
carry more usable signal than Claude Cowork's? Both recorders captured **the
same six train-set sessions simultaneously**, so the underlying events are held
constant and only the representation differs.

The two representations are not symmetric, and that asymmetry is the subject:

- **OCIC** writes a raw four-track `trace.json` per task (behavior / cursor /
  cognitive narration / frames) and nothing else. Nothing is interpreted at
  capture time; the primitives are kept.
- **Cowork** runs an analysis at capture time, whether or not you want it, and
  emits one generated markdown artifact per task. The underlying capture is not
  retained afterwards - the artifact is the only thing that persists.

So the OCIC sources here are pointers to recordings, while the Cowork sources
are the artifacts themselves. There is no rawer Cowork layer to ship.

Everything in this directory is committed because
`benchmark/environments/` and `benchmark/data/` are gitignored (486 MB of
trajectories and frames). Without these copies the phase is not reproducible
from a clone.

## Files

- `sources_cowork/` - the six Cowork artifacts, verbatim, byte-identical to
  what arms 7b and 7d mounted. These are Cowork's only persisted output.
- `sources_ocic.md` - the six OCIC recordings by task and recording id, under
  `~/.config/open-claude-in-chrome/recordings/`. The recordings themselves are
  ~6 MB of JSON plus frames and are not committed.
- `distillation_prompts.md` - the exact prompts that produced everything in
  `distilled/`, plus session facts.
- `distilled/` - the eight artifacts the four arms actually consumed:
  `<system>_ANALYSIS_<site>.md` (mounted on disk, phase-3 regime) and
  `<system>_RECIPE_<site>.md` (spliced into the task prompt, phase-5 regime).

## The four arms

| Arm | Source | Delivery | Mirrors |
| :--- | :--- | :--- | :--- |
| 7a | OCIC recordings | analysis + sources on disk | 3b |
| 7b | Cowork artifacts | analysis + sources on disk | 3b |
| 7c | OCIC recordings | per-site recipe in the prompt | 5b |
| 7d | Cowork artifacts | per-site recipe in the prompt | 5b |

Within a pair the header, flags, split and delivery are identical - verified by
diff, the phase-3 headers differ in exactly the two lines that describe what the
source material is, and the phase-5 header is byte-identical to 5b's. The only
variable is which recording system produced the material.

Arm definitions live in `runner.py` (`EXPERIMENTS`); the environments are built
by `build_p7_envs.py`, which also runs the leakage audit.

## How the artifacts were made

One isolated `claude -p` session per artifact set, four in total, each with a
working directory containing **only its own six sources** under `experience/`.
No repo, no manifests, no test tasks, no evaluator, no other arm's material -
the boundary is structural, not just prompt-enforced, and the prompt states it
as well.

Distiller: **`claude-fable-5` at max effort** for all four, matching the one
documented precedent in this study (the 5b/6b recipe author, see
`../6b_reproduction/recipe_generation_prompt.md`). Every executor rollout stays
Sonnet medium - a deliberate strong-to-weak transfer, where the expensive model
spends its capability once and the cheap model benefits on every rollout.

| Set | Time | Turns | Cost | Output |
| :--- | ---: | ---: | ---: | :--- |
| OCIC analysis | 10.4 min | 46 | $7.76 | 768 / 752 words |
| Cowork analysis | 4.7 min | 21 | $2.86 | 731 / 707 words |
| OCIC recipes | 7.6 min | 28 | $5.19 | 610 / 610 words |
| Cowork recipes | 4.2 min | 15 | $2.41 | 634 / 612 words |

27.0 minutes and $18.22 in total. Reproduce with
`python3 run_p7_distill.py`, then `python3 build_p7_envs.py`.

Note the read cost, which is a finding in itself: distilling the raw OCIC
recordings took roughly twice as long as distilling the Cowork artifacts, in
both regimes, because there is materially more to read.

## Leakage

Every produced artifact was audited against the same blocklist the phase-5 chain
used (test-set answer entities plus every test task id) and **all eight passed**.

The mounted raw sources are a different matter and were reported rather than
blocked, deliberately: they are what each system actually produced and are
mounted verbatim by design. Both carry incidental test-set entity mentions,
because the demo sites draw train and test tasks from one small fixed catalog -
the OCIC traces carry more of them (`Bacon Double`, `Souvla`, `150,000`) than
the Cowork artifacts (`Souvla`, in one file), since a raw recording captures
whatever was on screen while an eager distillation drops most specifics.

Separately, the Cowork artifacts contain concrete answers, counts and names,
which the OCIC recipe prompt explicitly forbade for its own output. That is a
real difference between the two methods rather than a defect in the comparison,
and it favours Cowork if anything, so it is left in and noted.

## A caveat worth carrying

Cowork's capture-time analysis costs **790s for six recordings** (mean 132s
each) and scales linearly with the number of recordings, since every recording
is analysed independently. OCIC's analysis is deferred and ran once over all six
trajectories. The comparison is therefore not only about which representation
performs better, but about when the reduction happens and what it forecloses:
a per-recording reduction cannot draw a cross-trajectory inference, because by
the time you would ask the question the raw evidence is gone.

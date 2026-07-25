# What was in the generator's workspace

The recipe author saw exactly one thing: a 20 MB `experience/` directory. No
repo code, no task manifests, no evaluation artifacts, no browser. This file
records what that directory contained and where every byte came from.

## Layout

```
~/.bench_rollouts/p5_recipegen/
└── experience/
    ├── README.md                  top-level: explains the two sources
    ├── experiential/              the agent's OWN prior sessions
    │   ├── README.md              format notes + the 6 task goals
    │   └── {dashdish-3,4,5, zilloft-4,7,8}/
    │       ├── trace.jsonl        raw Claude Code session trace
    │       └── images/            screenshots referenced from the trace
    └── expert/                    human operator recordings, same 6 tasks
        ├── README.md              format notes + the 6 task goals
        └── {dashdish-3,4,5, zilloft-4,7,8}/
            ├── trace.json         4-track recording (one clock)
            ├── SCHEMA_v0.md       the trace.json format spec
            └── images/            captured frames
```

Sizes: experiential tasks 1.2-2.4 MB each; expert tasks 0.5-3.6 MB each;
19 MB total under `experience/`.

## The two sources, precisely

**experiential/** - trajectories from the `gen-experiential` experiment: the
phase-1 pipeline run over the 6 train tasks (OCIC on Brave, Sonnet medium,
execute_code forbidden). Per its manifest, these are "trajectories only;
finish/evaluation artifacts deliberately excluded (ground-truth leak)". The
only transformation from the raw session: inline screenshot bytes replaced
with `[screenshot -> images/NNNN.jpg]` references. Failures, retries, and
dead ends are all still in the traces.

**expert/** - the operator's recordings, copied verbatim from the recorder.
Each `trace.json` carries four parallel tracks on one clock: `behavior`
(discrete UI actions), `cursor` (pointer path), `images` (frame refs), and
`cognitive` (spoken narration, transcribed). The narration is the only place
in the whole benchmark where human intent is written down next to actions.

## The 6 train tasks (test set never present)

- dashdish-3: How many restaurants in the "Light & fresh" category offer delivery?
- dashdish-4: Schedule a delivery order from "Taco Bell" adding a "Classic Cheeseburger" large size for later and add the note "Leave at the front door".
- dashdish-5: Add three "Loaded Bacon Cheese Fries" to the cart from "Man vs. Fries", checkout, select "Pickup".
- zilloft-4: What is the price of the cheapest home in San Francisco with at least 4 bedrooms?
- zilloft-7: How many "Manufactured" homes are available in San Francisco under $1,000,000?
- zilloft-8: Filter 3 bed / 2 bath / $600k-$800k / zipcode 92114. How many results?

## Provenance (the "export at that point in time")

Verified by byte-level diff: the workspace's `experience/experiential/*` task
dirs are identical to the repo's `environments/experiential/mounted/*`, and
`experience/expert/*` to `environments/expert/recordings/*`. In other words,
the recipe generator studied EXACTLY the material that phases 2a/2b mounted
on disk for the rollout agents, minus the manifests, re-wrapped under a
neutral `experience/` root with orientation READMEs. Workspace assembled
2026-07-17 02:51; recipes written 03:17-03:19; phase-5/6 arms ran after
03:20 the same night. The upstream copies have not changed since (same
bytes today).

Nothing else was present. The generator had no way to see test tasks, ground
truths, evaluators, or the runner - the leakage guarantee is structural, not
just prompt-enforced.

#!/usr/bin/env python3
"""Assemble the four phase-7 environments from the distillation workspaces.

  environments/ocic_new_analyzed/mounted/  6 raw recordings + 2 ANALYSIS + README
  environments/cowork_analyzed/mounted/    6 artifacts      + 2 ANALYSIS + README
  environments/recipes_ocic_new/           RECIPE_<site>.md x2
  environments/recipes_cowork/             RECIPE_<site>.md x2

Sources are copied from the isolated distillation workspaces, so what the
rollout agent sees is byte-identical to what the distiller saw. Each env gets a
manifest.json recording distiller model/effort/seconds and source provenance.

Leakage audit, run over every artifact:
  - HARD on the produced ANALYSIS/RECIPE files: the authoring prompt forbade
    answers, counts, prices and names, so a test-identifier hit there is a bug.
  - REPORTED on the mounted raw sources: those are what each system actually
    produced and are mounted verbatim by design; the cowork artifacts are known
    to carry concrete values, which is itself a finding, not something to hide.
"""
import json, os, re, shutil, sys

BENCH = os.path.dirname(os.path.abspath(__file__))
WS = os.path.expanduser("~/.bench_rollouts")
ENVS = os.path.join(BENCH, "environments")
MAN = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))
TRAIN = MAN["train_order"]
TEST = MAN["test_order"]
GOALS = {t: MAN["tasks"][t]["goal"] for t in TRAIN}

# same blocklist the phase-5 chain audited against, plus every test task id
TEST_STRINGS = ["Biryani", "Mashaallah", "Souvla", "DragonEats", "Mushroom Swiss",
                "Express Delivery", "Bacon Double", "David Smith", "davidsmith",
                "555-333-7890", "150,000"] + sorted(TEST)

SRC_DESC = {
    "ocic": ("open-claude-in-chrome browser recordings", "raw 4-track trace.json "
             "per task (behavior / cursor / cognitive narration / frames)"),
    "cowork": ("Claude cowork generated artifacts", "one markdown artifact per "
               "task, produced automatically by that system at capture time"),
}

READ_FIRST = """# Prior experience, already analyzed for you

An expert operator was recorded completing six tasks in this same browser
environment. Those recordings have ALREADY been analyzed; the compressed
takeaways are in two documents, one per site:

- **ANALYSIS_dashdish.md** - how dashdish actually works: page map, which
  controls are real vs. decorative, search semantics, recipes, gotchas.
- **ANALYSIS_zilloft.md** - the same for zilloft: the search-then-filter
  workflow, exact filter mechanics, environment realities.

Read the analysis for your task's site BEFORE acting. It is intended to be
sufficient on its own; you should not need to study the raw material.

{raw_note}

## Demonstrated tasks
"""

RAW_NOTE = {
    "ocic": """The raw recordings remain below if you want to verify a detail: one folder
per task, each with `trace.json` (behavior / cursor / narration tracks on one
clock), `SCHEMA_v0.md` (the format), and `images/` (the captured frames).""",
    "cowork": """The per-task artifacts the recording system generated remain below if you
want to verify a detail: one markdown file per task, each opening with a YAML
frontmatter block followed by prose instructions for that kind of task.""",
}


def audit(path, text, hard):
    hits = sorted({s for s in TEST_STRINGS if s.lower() in text.lower()})
    tag = "FAIL" if (hits and hard) else ("note" if hits else "ok  ")
    print(f"    [{tag}] {os.path.relpath(path, BENCH):66} {hits if hits else ''}")
    return not (hits and hard)


def build_analyzed(source):
    ws = os.path.join(WS, f"p7_p3_{source}", "experience")
    dest_root = os.path.join(ENVS, f"{'ocic_new' if source=='ocic' else 'cowork'}_analyzed")
    mounted = os.path.join(dest_root, "mounted")
    shutil.rmtree(dest_root, ignore_errors=True)
    os.makedirs(mounted)

    # sources, byte-identical to what the distiller read
    for t in TRAIN:
        src = os.path.join(ws, t) if source == "ocic" else os.path.join(ws, t + ".md")
        dst = os.path.join(mounted, t) if source == "ocic" else os.path.join(mounted, t + ".md")
        (shutil.copytree if source == "ocic" else shutil.copyfile)(src, dst)

    # the produced analysis
    for f in ("ANALYSIS_dashdish.md", "ANALYSIS_zilloft.md"):
        shutil.copyfile(os.path.join(WS, f"p7_p3_{source}", f), os.path.join(mounted, f))

    with open(os.path.join(mounted, "README.md"), "w") as fh:
        fh.write(READ_FIRST.format(raw_note=RAW_NOTE[source]))
        for t in TRAIN:
            fh.write(f"- **{t}** - {GOALS[t]}\n")

    res = json.load(open(os.path.join(WS, f"p7_p3_{source}", "distill_result.json")))
    label, shape = SRC_DESC[source]
    json.dump({
        "kind": f"{source}-recordings-analyzed",
        "for_experiment": "exp7a-ocic-analysis" if source == "ocic" else "exp7b-cowork-analysis",
        "source": f"{label}: {shape}; six train sessions, captured simultaneously "
                  f"with the other system's recording of the same sessions",
        "analysis": {
            "documents": ["mounted/ANALYSIS_dashdish.md", "mounted/ANALYSIS_zilloft.md"],
            "method": "isolated session, workspace contained ONLY this system's six "
                      "sources; general mechanics only, task-specific values excluded",
            "distiller_model": res["model"], "distiller_effort": res["effort"],
            "analysis_generation_seconds": res["seconds"],
            "turns": res["num_turns"], "cost_usd": res["cost_usd"],
            "words": res["words"],
        },
        "tasks": TRAIN,
    }, open(os.path.join(dest_root, "manifest.json"), "w"), indent=1)

    print(f"  {os.path.relpath(dest_root, BENCH)}")
    ok = True
    for f in ("ANALYSIS_dashdish.md", "ANALYSIS_zilloft.md"):
        p = os.path.join(mounted, f)
        ok &= audit(p, open(p).read(), hard=True)
    for t in TRAIN:  # mounted raw sources: reported, not enforced
        p = os.path.join(mounted, t + ".md") if source == "cowork" else os.path.join(mounted, t, "trace.json")
        audit(p, open(p, errors="ignore").read(), hard=False)
    return ok


def build_recipes(source):
    ws = os.path.join(WS, f"p7_p5_{source}")
    dest = os.path.join(ENVS, f"recipes_{'ocic_new' if source=='ocic' else 'cowork'}")
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    for f in ("RECIPE_dashdish.md", "RECIPE_zilloft.md"):
        shutil.copyfile(os.path.join(ws, f), os.path.join(dest, f))
    res = json.load(open(os.path.join(ws, "distill_result.json")))
    label, shape = SRC_DESC[source]
    json.dump({
        "kind": f"{source}-recipes",
        "for_experiment": "exp7c-ocic-recipe" if source == "ocic" else "exp7d-cowork-recipe",
        "source": f"{label}: {shape}",
        "distiller_model": res["model"], "distiller_effort": res["effort"],
        "generation_seconds": res["seconds"], "turns": res["num_turns"],
        "cost_usd": res["cost_usd"], "words": res["words"],
    }, open(os.path.join(dest, "manifest.json"), "w"), indent=1)
    print(f"  {os.path.relpath(dest, BENCH)}")
    ok = True
    for f in ("RECIPE_dashdish.md", "RECIPE_zilloft.md"):
        p = os.path.join(dest, f)
        ok &= audit(p, open(p).read(), hard=True)
    return ok


if __name__ == "__main__":
    print("building phase-7 environments\n")
    ok = True
    for s in ("ocic", "cowork"):
        ok &= build_analyzed(s)
    for s in ("ocic", "cowork"):
        ok &= build_recipes(s)
    print("\nleakage audit:", "PASS (no test identifiers in any produced artifact)" if ok
          else "FAIL - a produced artifact contains a test identifier")
    sys.exit(0 if ok else 1)

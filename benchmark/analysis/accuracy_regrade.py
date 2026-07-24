#!/usr/bin/env python3
"""Deterministic re-grade of the held-out accuracy, removing LLM-judge noise.

The REAL evaluator's llm_boolean judge (Sonnet fallback, gpt-4o unavailable) gave
inconsistent verdicts: it passed several answers that were numerically wrong. Only
three tasks vary across arms (zilloft-2, -5, -10); the rest are constant. For those
three we re-grade by exact count match against the rubric's ground-truth number,
read straight from each run's evaluation.json (the source of truth for what the
agent actually answered). Writes accuracy_corrected.json for the chart builders."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.load(open(os.path.join(HERE, "capstone.json")))
REN = {"CinC": "1a", "OCIC-Ch": "1b", "OCIC-Br": "1c", "2A": "2a", "2B": "2b",
       "3D": "3a", "3C": "3b", "4A": "4a", "4B": "4b", "5B": "5a", "5A": "5b",
       "5C": "6a", "5D": "6b"}
ID = {REN[a["short"]]: a["id"] for a in D["arms"]}
ORDER = ["1a", "1b", "1c", "2a", "2b", "3a", "3b", "4a", "4b", "5a", "5b", "6a", "6b"]

# 12 held-out tasks. 8 pass for every arm; dashdish-8 fails for every arm (its
# correct answer is the curated carousels, not the cuisine categories every agent
# returned - a genuine, consistent universal fail, not judge noise). The 3 swing
# tasks are re-graded from the model's actual numeric answer.
CONSTANT_PASS = ["dashdish-11", "dashdish-10", "zilloft-3", "dashdish-7",
                 "dashdish-1", "dashdish-2", "zilloft-6", "zilloft-9"]
ALWAYS_FAIL = ["dashdish-8"]
SWING = {"zilloft-2": 16, "zilloft-5": 1, "zilloft-10": 13}

# The count each arm actually reported, read by hand from every run's
# evaluation.json FINAL ANSWER (regex extraction is unsafe here - answers embed
# prices like "$500K" and bed/bath counts that a naive "first number" grabs).
REPORTED = {
    "zilloft-2":  {"1a": 147, "1b": 147, "1c": 147, "2a": 16, "2b": 16, "3a": 16,
                   "3b": 16, "4a": 147, "4b": 36, "5a": 36, "5b": 16, "6a": 16, "6b": 16},
    "zilloft-5":  {"1a": 3, "1b": 3, "1c": 3, "2a": 3, "2b": 1, "3a": 1, "3b": 1,
                   "4a": 3, "4b": 1, "5a": 1, "5b": 1, "6a": 1, "6b": 1},
    "zilloft-10": {"1a": 160, "1b": 160, "1c": 160, "2a": 160, "2b": 13, "3a": 160,
                   "3b": 13, "4a": 160, "4b": 13, "5a": 13, "5b": 13, "6a": 160, "6b": 13},
}

def evalfile(arm, task):
    return json.load(open(f"{BENCH}/data/{ID[arm]}/{task}_r1/evaluation.json"))

def reported_count(arm, task):
    return REPORTED[task][arm]

def fail_text(arm, task):
    # same truncation style as the original capstone.json per_task.fail field:
    # strip the "FINAL ANSWER:" preamble, then cut to 150 chars.
    r = evalfile(arm, task)["model_response"]
    seg = re.split(r"FINAL ANSWER:?\s*", r, maxsplit=1, flags=re.I)[-1].strip()
    return seg[:150]

matrix = {}   # arm -> {task: bool}
audit = []    # overturned grader verdicts
answer_text = {t: {} for t in SWING}  # task -> arm -> truncated answer text
for arm in ORDER:
    row = {t: True for t in CONSTANT_PASS}
    for t in ALWAYS_FAIL:
        row[t] = False
    for t, correct in SWING.items():
        n = reported_count(arm, t)
        grader = bool(evalfile(arm, t)["passed"])
        real = (n == correct)
        row[t] = real
        answer_text[t][arm] = fail_text(arm, t)
        if real != grader:
            audit.append({"arm": arm, "task": t, "answer": n, "correct": correct,
                          "grader": "PASS" if grader else "fail",
                          "corrected": "PASS" if real else "fail"})
    matrix[arm] = row

passed = {arm: sum(1 for v in matrix[arm].values() if v) for arm in ORDER}
PHASES = {"P1": ["1a", "1b", "1c"], "P2": ["2a", "2b"], "P3": ["3a", "3b"],
          "P4": ["4a", "4b"], "P5": ["5a", "5b"], "P6": ["6a", "6b"]}
phase_avg = {ph: round(sum(passed[a] for a in mem) / len(mem), 3) for ph, mem in PHASES.items()}

out = {"n_tasks": 12, "order": ORDER, "passed": passed, "matrix": matrix,
       "phases": PHASES, "phase_avg": phase_avg, "swing": SWING, "audit": audit,
       "answer_text": answer_text,
       "color": {REN[k]: v for k, v in D["dist_byleg"]["color"].items()}}
json.dump(out, open(os.path.join(HERE, "accuracy_corrected.json"), "w"), indent=1)

# ---- audit report ----
print("OVERTURNED GRADER VERDICTS (%d):" % len(audit))
print(f"  {'arm':<4}{'task':<12}{'answer':>7}{'correct':>9}   {'grader':>6} -> {'corrected'}")
for a in audit:
    print(f"  {a['arm']:<4}{a['task']:<12}{a['answer']:>7}{a['correct']:>9}   {a['grader']:>6} -> {a['corrected']}")
print("\nPER-ARM passed (of 12):  raw -> corrected")
raw = {REN[a["short"]]: a["passed"] for a in D["arms"]}
for a in ORDER:
    flag = "  <-- changed" if raw[a] != passed[a] else ""
    print(f"  {a}: {raw[a]:>2} -> {passed[a]:>2}{flag}")
print("\nPHASE AVERAGES (corrected):")
for ph, v in phase_avg.items():
    print(f"  {ph}: {v}")
print("\nwrote accuracy_corrected.json")

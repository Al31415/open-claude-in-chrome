#!/usr/bin/env python3
"""Significance tests over harvest.json.

All tests are PAIRED by task (same 12 held-out tasks in every arm).

- Time / turns: exact paired sign-flip permutation test (two-sided) on the
  mean difference. n=12 -> 4096 sign patterns, fully exact, no distributional
  assumptions. Wilcoxon signed-rank (exact, same enumeration over signed
  ranks) reported alongside.
- Accuracy: exact McNemar (two-sided binomial on discordant pairs).
- Each time comparison run twice: all 12 pairs, and the pass-in-both subset
  (duration of a failed run measures something else; report both).
"""
import json, os, itertools, math, statistics

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
ORDER = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))["test_order"]

def perm_p(diffs):
    """Exact two-sided sign-flip permutation p on mean(diffs)."""
    n = len(diffs); obs = abs(sum(diffs) / n)
    cnt = 0; total = 2 ** n
    for signs in itertools.product((1, -1), repeat=n):
        s = sum(d * g for d, g in zip(diffs, signs)) / n
        if abs(s) >= obs - 1e-12: cnt += 1
    return cnt / total

def wilcoxon_exact_p(diffs):
    """Exact two-sided Wilcoxon signed-rank via sign-flip enumeration."""
    d = [x for x in diffs if abs(x) > 1e-12]
    n = len(d)
    if n == 0: return 1.0
    ranks = {}
    sd = sorted(range(n), key=lambda i: abs(d[i]))
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[sd[j + 1]]) == abs(d[sd[i]]): j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1): ranks[sd[k]] = r
        i = j + 1
    Wobs = sum(ranks[i] for i in range(n) if d[i] > 0)
    T = sum(ranks.values())
    mid = T / 2
    obs_dev = abs(Wobs - mid)
    cnt = 0; total = 2 ** n
    rvals = [ranks[i] for i in range(n)]
    for signs in itertools.product((0, 1), repeat=n):
        W = sum(r for r, s in zip(rvals, signs) if s)
        if abs(W - mid) >= obs_dev - 1e-12: cnt += 1
    return cnt / total

def mcnemar_p(b, c):
    """Exact two-sided McNemar: binomial(b; b+c, .5)."""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return min(1.0, p)

def compare(name, arm_a, arm_b, metric="run_s", scale=1/60.0, unit="min"):
    A, B = H[arm_a], H[arm_b]
    rows = [(t, A[t].get(metric), B[t].get(metric),
             A[t]["passed"], B[t]["passed"]) for t in ORDER
            if A.get(t, {}).get(metric) is not None and B.get(t, {}).get(metric) is not None]
    out = {"comparison": name, "a": arm_a, "b": arm_b, "metric": metric, "unit": unit}
    for label, subset in (("all", rows), ("pass_both", [r for r in rows if r[3] and r[4]])):
        if len(subset) < 4:
            out[label] = {"n": len(subset), "note": "too few pairs"}; continue
        diffs = [(ra - rb) * scale for _, ra, rb, _, _ in subset]
        out[label] = {
            "n": len(subset),
            "mean_a": round(statistics.mean([ra * scale for _, ra, _, _, _ in subset]), 2),
            "mean_b": round(statistics.mean([rb * scale for _, _, rb, _, _ in subset]), 2),
            "mean_diff": round(statistics.mean(diffs), 2),
            "median_diff": round(statistics.median(diffs), 2),
            "p_perm": round(perm_p(diffs), 4),
            "p_wilcoxon": round(wilcoxon_exact_p(diffs), 4),
        }
    # accuracy (always over all 12)
    b = sum(1 for _, _, _, pa, pb in rows if pa and not pb)
    c = sum(1 for _, _, _, pa, pb in rows if pb and not pa)
    out["accuracy"] = {
        "pass_a": sum(1 for _, _, _, pa, _ in rows if pa),
        "pass_b": sum(1 for _, _, _, _, pb in rows if pb),
        "a_only": b, "b_only": c, "p_mcnemar": round(mcnemar_p(b, c), 4),
    }
    return out

TESTS = [
    # Study 1: harness (OCIC vs official CinC)
    ("S1 primary: OCIC fixed (Chrome) vs CinC (Chrome)", "exp1a-fixed-chrome", "exp1b-cinc-cold"),
    ("S1 secondary: OCIC fixed (Brave) vs CinC (Chrome)", "exp1a-fixed-brave", "exp1b-cinc-cold"),
    ("S1 context: OCIC pre-fix (Brave) vs CinC (Chrome)", "exp1a-ocic-cold", "exp1b-cinc-cold"),
    ("S1c: OCIC fixed (Brave) vs CinC control", "exp1a-fixed-brave", "exp1b-cinc-rerun"),
    ("S1p: OCIC fixed (Brave) vs CinC parity", "exp1a-fixed-brave", "exp1b-cinc-parity"),
    ("S1pc: CinC parity vs CinC control", "exp1b-cinc-parity", "exp1b-cinc-rerun"),
    # Study 2: pre-training + analysis vs cold baseline (all Brave, post-fix)
    ("S2: expert-analysis (3c) vs cold baseline (fixed-brave)", "exp3c-analysis", "exp1a-fixed-brave"),
    ("S2: experiential-analysis (3d) vs cold baseline (fixed-brave)", "exp3d-experiential-analysis", "exp1a-fixed-brave"),
    ("S2: expert-analysis (3c) vs experiential-analysis (3d)", "exp3c-analysis", "exp3d-experiential-analysis"),
    # Study 2 additions: raw mounts post-fix
    ("S2r: experiential-raw (2a-fixed) vs cold baseline", "exp2a-fixed-brave", "exp1a-fixed-brave"),
    ("S2r: expert-raw (2b-fixed) vs cold baseline", "exp2b-fixed-brave", "exp1a-fixed-brave"),
    # Study 3: phase-4 forks
    ("S3: experiential-fork (4a) vs cold baseline", "exp4a-experiential-fork", "exp1a-fixed-brave"),
    ("S3: expert-fork (4b) vs cold baseline", "exp4b-expert-fork", "exp1a-fixed-brave"),
    ("S3: expert-fork (4b) vs experiential-fork (4a)", "exp4b-expert-fork", "exp4a-experiential-fork"),
    ("S3: expert-fork (4b) vs expert-analysis mounted (3c)", "exp4b-expert-fork", "exp3c-analysis"),
    ("S3: expert-fork (4b) vs expert-raw mounted (2b-fixed)", "exp4b-expert-fork", "exp2b-fixed-brave"),
    ("S3: experiential-fork (4a) vs experiential-analysis mounted (3d)", "exp4a-experiential-fork", "exp3d-experiential-analysis"),
    ("S3: experiential-fork (4a) vs experiential-raw mounted (2a-fixed)", "exp4a-experiential-fork", "exp2a-fixed-brave"),
]

results = []
for name, a, b in TESTS:
    r = compare(name, a, b)
    r_turns = compare(name + " [turns]", a, b, metric="turns", scale=1.0, unit="turns")
    results.append({"time": r, "turns": r_turns})
    t = r["all"]; tp = r["pass_both"]; acc = r["accuracy"]
    print(f"== {name}")
    print(f"   time all n={t['n']}: {t['mean_a']} vs {t['mean_b']} {r['unit']} "
          f"(diff {t['mean_diff']:+}, median {t['median_diff']:+}) p_perm={t['p_perm']} p_wx={t['p_wilcoxon']}")
    if "n" in tp and "p_perm" in tp:
        print(f"   time pass-both n={tp['n']}: {tp['mean_a']} vs {tp['mean_b']} "
              f"(diff {tp['mean_diff']:+}) p_perm={tp['p_perm']} p_wx={tp['p_wilcoxon']}")
    tt = r_turns["all"]
    print(f"   turns all: {tt['mean_a']} vs {tt['mean_b']} (diff {tt['mean_diff']:+}) p_perm={tt['p_perm']}")
    print(f"   accuracy: {acc['pass_a']}/12 vs {acc['pass_b']}/12, discordant {acc['a_only']}+/{acc['b_only']}-, p_mcnemar={acc['p_mcnemar']}")

json.dump(results, open(os.path.join(BENCH, "analysis", "stats.json"), "w"), indent=1)
print("\nwrote analysis/stats.json")

#!/usr/bin/env python3
"""The three log-y ratio scatter charts (time, turns, thinking tokens as a
multiple of cold), rebuilt on matplotlib so the axis mapping, log scale, and
point placement come from a standard, battle-tested library rather than
hand-rolled SVG math. Supersedes the SVG builders (build_ratio_decay.py,
build_turns_ratio_decay.py, build_thinking_ratio_decay.py) as the source of
the writeup's PNGs; writes straight into writeup/images/ (and analysis/
copies) under the same filenames, no Chrome step involved.

Same data, same semantics as before: each point is (arm value / cold-baseline
value) for one held-out task, on a plain continuous linear y-axis fixed to
[0.4, 2] with ordinary 0.25-step ticks; linear x-axis = the cold baseline's
own value for that task. Dashed lines are pooled-source OLS fits of
ln(ratio) on x (n=36) drawn as their exponential curves; solid lines are
single-arm fits (n=12); points above 2x render as '|' ticks pinned to the
top edge. Line-end labels sit in the right margin, decluttered vertically.

Run: ~/.venvs/charts/bin/python build_ratio_charts_mpl.py"""
import json, math, os, re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import blended_transform_factory

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
OUT_DIRS = [os.path.join(BENCH, "writeup", "images"), HERE]

CAP = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                            open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
BY = {a["short"]: a for a in CAP["arms"]}
COLOR = CAP["dist_byleg"]["color"]
TPT = json.load(open(os.path.join(HERE, "thinking_per_task.json")))

A_SIDE = ["2a", "3a", "4a"]; B_SIDE = ["2b", "3b", "4b"]; SOLO = ["5b", "6a", "6b"]
COL_A, COL_B = "#c2703d", "#2f7a8c"
LABEL_SOLO = {"5b": "5b · recipe (per-site)", "6a": "6a · atomic warm-up (no recipe)",
              "6b": "6b · warm-up + recipe (winner)"}
YLO, YHI = 0.4, 2.0
TICKS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
TICK_LABELS = ["0.5×", "0.75×", "1×", "1.25×", "1.5×", "1.75×", "2×"]
INK, MUTED, DIM, GRID_SOFT, GRID_HOT = "#1b1f24", "#5b6571", "#8a929c", "#dedbd3", "#c9c7c1"

def base_and_arm_values(metric):
    if metric == "thinking":
        base = {t: (sum(TPT[a][t] for a in ("1a", "1b", "1c")) / 3) / 1000 for t in TPT["1a"]}
        armv = {arm: {t: TPT[arm][t] / 1000 for t in TPT[arm]} for arm in A_SIDE + B_SIDE + SOLO}
        return base, armv
    key = "min" if metric == "time" else "turns"
    base = {}
    for s in ("1a", "1b", "1c"):
        for pt in BY[s]["per_task"]:
            base.setdefault(pt["t"], []).append(pt[key])
    base = {t: sum(v) / len(v) for t, v in base.items()}
    armv = {arm: {pt["t"]: pt[key] for pt in BY[arm]["per_task"]} for arm in A_SIDE + B_SIDE + SOLO}
    return base, armv

def ols_ln(xs, ys):
    b1, b0 = np.polyfit(np.asarray(xs, float), np.log(np.asarray(ys, float)), 1)
    pred = b0 + b1 * np.asarray(xs, float)
    lys = np.log(np.asarray(ys, float))
    ss_res = float(np.sum((lys - pred) ** 2)); ss_tot = float(np.sum((lys - lys.mean()) ** 2))
    return b0, b1, (1 - ss_res / ss_tot if ss_tot else 0.0)

CHARTS = {
    "time": dict(
        fname="ratio_decay.png",
        title="Task time as a multiple of cold: source pooled across phases 2-4, plus 5b, 6a, 6b",
        sub="Each point: (arm task time) / (baseline cold task time), vs. baseline (cold) task time in minutes",
        xlabel="baseline (cold) time for the task (minutes)",
        ylabel="task time / baseline time",
        xfmt=lambda v: f"{v:g}m", xstep=1, xpad=1.1, fitfmt="baseline minutes"),
    "turns": dict(
        fname="turns_ratio_decay.png",
        title="Task turns as a multiple of cold: source pooled across phases 2-4, plus 5b, 6a, 6b",
        sub="Each point: (arm task turns) / (baseline cold task turns), vs. baseline (cold) turns for the task",
        xlabel="baseline (cold) turns for the task",
        ylabel="task turns / baseline turns",
        xfmt=lambda v: f"{v:g}", xstep=10, xpad=1.05, fitfmt="baseline turns"),
    "thinking": dict(
        fname="thinking_ratio_decay.png",
        title="Thinking tokens as a multiple of cold: source pooled across phases 2-4, plus 5b, 6a, 6b",
        sub="Each point: (arm task thinking tokens) / (baseline cold task thinking tokens), vs. baseline thinking tokens (thousands)",
        xlabel="baseline (cold) thinking tokens for the task (thousands)",
        ylabel="task thinking tokens / baseline",
        xfmt=lambda v: f"{v:g}k", xstep=2, xpad=1.08, fitfmt="baseline k-tokens"),
}

for metric, cfg in CHARTS.items():
    base, armv = base_and_arm_values(metric)
    xmax = max(base.values()) * cfg["xpad"]

    fig = plt.figure(figsize=(13, 6.2), dpi=200)
    ax = fig.add_axes([0.051, 0.097, 0.72, 0.71])  # generous right margin for line-end labels
    ax.set_xlim(0, xmax)
    ax.set_ylim(YLO, YHI)
    ax.set_yticks(TICKS); ax.set_yticklabels(TICK_LABELS, fontsize=9, color=DIM)
    ax.minorticks_off()
    xticks = np.arange(0, xmax + 1e-9, cfg["xstep"])
    ax.set_xticks(xticks); ax.set_xticklabels([cfg["xfmt"](v) for v in xticks], fontsize=9, color=DIM)
    ax.tick_params(length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in ("top", "bottom"))
        ax.spines[side].set_color(GRID_HOT)
    for g in TICKS:
        ax.axhline(g, color=GRID_HOT if abs(g - 1) < 1e-9 else GRID_SOFT,
                   lw=1.4 if abs(g - 1) < 1e-9 else 0.9, zorder=1)
    for gx in xticks:
        ax.axvline(gx, color="#f2f1ed", lw=0.9, zorder=0)
    ax.set_xlabel(cfg["xlabel"], fontsize=10.5, color=MUTED)
    ax.set_ylabel(cfg["ylabel"], fontsize=10.5, color=MUTED)

    fig.text(0.051, 0.955, cfg["title"], fontsize=14.5, fontweight="bold", color=INK, ha="left")
    fig.text(0.051, 0.915, cfg["sub"], fontsize=9.5, color=DIM, ha="left")
    fig.text(0.051, 0.878,
             f"horizontal line = 1× (equal to cold) · dashed = pooled source fit, ln(ratio) ~ {cfg['fitfmt']} (n=36 each) · "
             f"solid = single-arm fit (n=12) · | ticks on the top edge = points above 2×, off scale",
             fontsize=8.4, color=DIM, ha="left")

    series = []
    for arm in SOLO:
        pts = [(base[t], armv[arm][t] / base[t]) for t in base if t in armv[arm]]
        series.append(dict(name=LABEL_SOLO[arm], col=COLOR[arm], pts=pts, dashed=False, n=len(pts)))
    for side_name, col, arms in (("Experiential avg (2a+3a+4a)", COL_A, A_SIDE),
                                 ("Expert avg (2b+3b+4b)", COL_B, B_SIDE)):
        pts = [(base[t], armv[a][t] / base[t]) for t in base for a in arms if t in armv[a]]
        series.append(dict(name=side_name, col=col, pts=pts, dashed=True, n=len(pts)))

    xs_line = np.linspace(0, xmax, 200)
    for sr in series:
        xs = [p[0] for p in sr["pts"]]; ys = [p[1] for p in sr["pts"]]
        b0, b1, r2 = ols_ln(xs, ys)
        sr["b0"], sr["b1"], sr["r2"] = b0, b1, r2
        inr = [(x, y) for x, y in sr["pts"] if y <= YHI]
        outr = [x for x, y in sr["pts"] if y > YHI]
        if sr["dashed"]:
            ax.scatter([p[0] for p in inr], [p[1] for p in inr], s=26, c=sr["col"], alpha=0.35,
                       linewidths=0, zorder=3)
            ax.plot(xs_line, np.exp(b0 + b1 * xs_line), color=sr["col"], lw=2.6,
                    dashes=(4, 2.2), alpha=0.95, zorder=4)
        else:
            ax.scatter([p[0] for p in inr], [p[1] for p in inr], s=34, c=sr["col"], alpha=0.85,
                       edgecolors="white", linewidths=0.8, zorder=5)
            ax.plot(xs_line, np.exp(b0 + b1 * xs_line), color=sr["col"], lw=1.9, alpha=0.9, zorder=4)
        if outr:
            ax.plot(outr, [YHI] * len(outr), linestyle="none", marker="|", ms=9,
                    markeredgewidth=1.8 if not sr["dashed"] else 1.4, color=sr["col"],
                    alpha=0.8 if not sr["dashed"] else 0.55, clip_on=False, zorder=6)

    # line-end labels in the right margin, decluttered in log space
    fig.canvas.draw()
    min_gap = (YHI - YLO) * 0.088  # ~ two text lines of clearance
    ends = sorted(series, key=lambda sr: math.exp(sr["b0"] + sr["b1"] * xmax))
    prev = None
    for sr in ends:
        yv = min(max(math.exp(sr["b0"] + sr["b1"] * xmax), YLO + 0.04), YHI - 0.04)
        if prev is not None and yv - prev < min_gap:
            yv = prev + min_gap
        prev = yv
        tr = blended_transform_factory(ax.transAxes, ax.transData)
        ax.plot([1.012], [yv], transform=tr, marker="o", ms=6, color=sr["col"], clip_on=False, zorder=7)
        ax.annotate(sr["name"], xy=(1.024, yv), xycoords=tr, fontsize=10, fontweight="bold",
                    color=sr["col"], va="bottom", annotation_clip=False)
        ax.annotate(f"R²={sr['r2']:.2f} (n={sr['n']})", xy=(1.024, yv), xycoords=tr, fontsize=8.2,
                    color=DIM, va="top", annotation_clip=False)

    for out_dir in OUT_DIRS:
        fig.savefig(os.path.join(out_dir, cfg["fname"]), facecolor="white")
    plt.close(fig)
    fits = ", ".join(f"{sr['name'].split(' ·')[0].split(' (')[0]}: slope={sr['b1']:+.4f} R²={sr['r2']:.2f}" for sr in series)
    print(f"{metric:9} -> {cfg['fname']}  [{fits}]")

print("done; PNGs written to writeup/images/ and analysis/")

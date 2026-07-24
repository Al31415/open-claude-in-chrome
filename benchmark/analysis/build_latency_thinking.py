#!/usr/bin/env python3
"""Latency decomposition, part 2: within model inference, what generates the
output tokens - thinking, tool-use (acting), or the assistant-facing text
message. Thinking text itself is redacted in these logs (only an opaque
signature remains), so thinking tokens are estimated as a residual:
implied_thinking = real_output_tokens - len(text)/4 - len(tool_use_json)/4,
summed across all turns of all 12 rollouts per arm (fork-contaminated arms
already marker-sliced upstream in thinking_breakdown.json). One 100%-stacked
bar per arm - the share, not the absolute count, is the point: it should look
almost identical across every arm regardless of what the arm does. Chrome
headless -> PNG."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});\s*\n',
                          open(os.path.join(BENCH, "benchmark_capstone.html")).read(), re.S).group(1))
ORDER = D["dist_byleg"]["order"]
TB = json.load(open(os.path.join(HERE, "thinking_breakdown.json")))

COL_THINK, COL_TOOL, COL_TEXT = "#4c3575", "#1f7a5c", "#c78a2e"

rows = []
for s in ORDER:
    t = TB[s]
    real = t["think"] + t["text"] + t["tool"]  # renormalize to the three measured parts
    p_think = 100 * t["think"] / real
    p_tool = 100 * t["tool"] / real
    p_text = 100 * t["text"] / real
    rows.append((s, p_think, p_tool, p_text))

W = 1120
PL, PR, PT, PB = 60, 40, 100, 46
BAR_H, GAP = 26, 12
H = PT + (BAR_H + GAP) * len(rows) - GAP + PB + 20
def X(pct): return PL + (W - PL - PR) * pct / 100

s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
s.append(f'<text x="{PL}" y="26" font-size="18" font-weight="700" fill="#1b1f24">Within model inference: what generates the output tokens</text>')
s.append(f'<text x="{PL}" y="45" font-size="12.5" fill="#8a929c">Share of output tokens per turn &#183; thinking is a residual estimate (redacted in logs: real output tokens minus est. text/tool-use tokens) &#183; 156 rollouts, 13 arms</text>')

ly = 66
legend = [("thinking (estimated)", COL_THINK), ("acting (tool-use)", COL_TOOL), ("assistant text", COL_TEXT)]
lx = PL
for label, col in legend:
    s.append(f'<rect x="{lx:.1f}" y="{ly-9}" width="11" height="11" rx="2" fill="{col}"/>')
    s.append(f'<text x="{lx+16:.1f}" y="{ly}" font-size="10.5" fill="#5b6571">{label}</text>')
    lx += 20 + len(label) * 6.3 + 22

for g in range(0, 101, 20):
    s.append(f'<line x1="{X(g):.1f}" y1="{PT-4}" x2="{X(g):.1f}" y2="{PT + (BAR_H+GAP)*len(rows)}" stroke="#f2f1ed"/>')
    s.append(f'<text x="{X(g):.1f}" y="{PT + (BAR_H+GAP)*len(rows) + 16}" text-anchor="middle" font-size="10" fill="#8a929c">{g}%</text>')

for i, (short, p_think, p_tool, p_text) in enumerate(rows):
    y = PT + i * (BAR_H + GAP)
    s.append(f'<text x="{PL-10:.1f}" y="{y+BAR_H/2+4:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="#1b1f24">{short}</text>')
    x = X(0)
    w = X(p_think) - X(0)
    s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR_H}" fill="{COL_THINK}"/>')
    s.append(f'<text x="{x+w/2:.1f}" y="{y+BAR_H/2+4:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">{p_think:.0f}%</text>')
    x += w
    w2 = X(p_think + p_tool) - X(p_think)
    s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w2:.1f}" height="{BAR_H}" fill="{COL_TOOL}"/>')
    x += w2
    w3 = X(100) - x
    s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w3:.1f}" height="{BAR_H}" fill="{COL_TEXT}"/>')

s.append('</svg>')
svg = "\n".join(s)
open(os.path.join(HERE, "latency_thinking.html"), "w").write(
    f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
for short, p_think, p_tool, p_text in rows:
    print(f"{short:4} think={p_think:5.1f}%  tool={p_tool:4.1f}%  text={p_text:4.1f}%")
print("wrote", os.path.join(HERE, "latency_thinking.html"))

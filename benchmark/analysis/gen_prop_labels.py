#!/usr/bin/env python3
"""Overlay labels onto the base prop sheets so each permutation is identified ON the
image itself (a title band on top + a tag near each cell). Baked-in labels survive
into the eventual assembled master image. Writes img/prop_<key>_labeled.png.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
BAND = 138          # top band: title + description
CREAM = (244, 241, 234)
INK = (28, 27, 24)
MUTED = (108, 103, 94)

def font(size, bold=True):
    p = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(p, size)

# each sheet: (title, description, tags[(text, cx_frac, cy_frac) in the ORIGINAL image])
SHEETS = {
 "v1-character": ("V1 · THE CHARACTER",
    "the exam student: context load left→right, harness (OCIC / CinC) top→bottom", [
    ("FRESH · OCIC", 0.135, 0.09), ("LIGHTLY · OCIC", 0.375, 0.09),
    ("BAGGY · OCIC", 0.625, 0.09), ("WRECKED · OCIC", 0.865, 0.09),
    ("FRESH · CinC", 0.135, 0.55), ("LIGHTLY · CinC", 0.375, 0.55),
    ("BAGGY · CinC", 0.625, 0.55), ("WRECKED · CinC", 0.865, 0.55)]),
 "v2-position": ("V2 · KNOWLEDGE FORM",
    "how supplied knowledge reaches the task: none · raw · analysis · recipe", [
    ("NONE", 0.28, 0.07), ("RAW", 0.72, 0.07),
    ("ANALYSIS", 0.28, 0.53), ("RECIPE", 0.72, 0.53)]),
 "task-paper": ("THE TASK PAPER",
    "the task, and the recipe printed onto it: plain · one panel · two panels", [
    ("PLAIN TASK", 0.18, 0.16), ("+ RECIPE", 0.5, 0.16), ("+ RECIPE ×2", 0.82, 0.16)]),
 "v3-source": ("V3 · SOURCE",
    "graded task sheet (experiential) vs textbook (expert), one or a stack", [
    ("EXPERIENTIAL", 0.28, 0.07), ("EXPERT", 0.72, 0.07),
    ("EXPERIENTIAL ×N", 0.28, 0.53), ("EXPERT ×N", 0.72, 0.53)]),
 "v4-prior": ("V4 · INTERNALIZED PRIOR",
    "already-internalised knowledge: a bubble holding any source prop", [
    ("BUBBLE = container", 0.5, 0.04)]),
 "v6-browser": ("V6 · BROWSER",
    "the browser, embedded on the desk front: Brave vs Chrome", [
    ("BRAVE", 0.27, 0.12), ("CHROME", 0.73, 0.12)]),
}

def label(key, title, desc, tags):
    base = Image.open(os.path.join(IMG, f"prop_{key}.png")).convert("RGB")
    W, H = base.size
    canvas = Image.new("RGB", (W, H + BAND), CREAM)
    canvas.paste(base, (0, BAND))
    d = ImageDraw.Draw(canvas, "RGBA")
    d.text((W / 2, 50), title, font=font(40), fill=INK, anchor="mm")
    d.text((W / 2, 100), desc, font=font(24, bold=False), fill=MUTED, anchor="mm")
    tf = font(27)
    for text, cx, cy in tags:
        x, y = cx * W, BAND + cy * H
        l, t, r, b = d.textbbox((x, y), text, font=tf, anchor="mm")
        pad = 9
        d.rounded_rectangle([l - pad, t - pad, r + pad, b + pad], radius=7,
                            fill=(253, 251, 245, 236), outline=(28, 27, 24, 255), width=2)
        d.text((x, y), text, font=tf, fill=INK, anchor="mm")
    out = os.path.join(IMG, f"prop_{key}_labeled.png")
    canvas.save(out)
    print("wrote", os.path.basename(out), canvas.size)

if __name__ == "__main__":
    for key, (title, desc, tags) in SHEETS.items():
        label(key, title, desc, tags)

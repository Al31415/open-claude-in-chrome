#!/usr/bin/env python3
"""Assemble the six labeled prop sheets into ONE master reference image: every prop
for every variable on a single sheet. This is what gets fed to the key-art step.
Writes img/prop_master.png.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
CREAM = (244, 241, 234)
INK = (28, 27, 24)
MUTED = (108, 103, 94)
KEYS = ["v1-character", "v2-position", "task-paper", "v3-source", "v4-prior", "v6-browser"]

def font(size, bold=True):
    p = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(p, size)

def main():
    imgs = [Image.open(os.path.join(IMG, f"prop_{k}_labeled.png")).convert("RGB") for k in KEYS]
    cw, ch = imgs[0].size
    cols, rows = 3, 2
    margin, gap, title_h = 48, 40, 150
    W = margin * 2 + cols * cw + (cols - 1) * gap
    H = margin * 2 + title_h + rows * ch + (rows - 1) * gap
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)
    d.text((W / 2, margin + 44), "PROP DESIGN · MASTER SHEET", font=font(66), fill=INK, anchor="mm")
    d.text((W / 2, margin + 104), "every prop for every variable, one reference for the key art",
           font=font(34, bold=False), fill=MUTED, anchor="mm")
    for i, im in enumerate(imgs):
        r, c = divmod(i, cols)
        x = margin + c * (cw + gap)
        y = margin + title_h + r * (ch + gap)
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + cw, y + ch], outline=(200, 196, 186), width=2)
    out = os.path.join(IMG, "prop_master.png")
    canvas.save(out)
    print("wrote", os.path.basename(out), canvas.size)

if __name__ == "__main__":
    main()

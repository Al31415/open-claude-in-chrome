#!/usr/bin/env python3
"""First-person composition variants: we look down at the character's OWN desk
through their eyes, so the face must arrive via something on the desk. Each variant
is a different device for surfacing the face. Same first-person desk + titled exam.

Writes img/fp_<key>.png. Run: python3 gen_fp.py [KEY]
"""
import os, sys
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = ("Art style: a soft graphite pencil drawing on warm off-white paper, smooth confident shading with rich "
    "tonal contrast, minimal hard outlines, soft edges. Monochrome graphite grey only. Crafted and consistent.")

POV = ("This is a strict FIRST-PERSON point of view: we look down at the character's own desk as if through their "
    "own eyes. We do NOT see the character's body. The desk surface fills the frame at a natural downward angle.")

EXAM = ("On the desk, facing us and readable, lies a single sheet of exam paper with blank ruled answer lines; near "
    "the top is a small printed box of many tiny dense lines (a cheat panel), and directly beneath it the word "
    "\"EXAM\" is printed clearly as the title.")

BRAND = "A small monochrome grey Brave lion emblem is visible somewhere on the desk (a little sticker or a mug), minor."

# the face is the simpler stickman head; it appears inside each variant's device
FACE = ("a simple round stick-figure head with two small dot eyes and a short straight mouth, plain and minimal, "
    "the word \"OCIC\" stamped across its forehead in small block capitals")

DEVICE = {
 "cameo":   f"In the top-right corner of the image, overlaid like a framed coin medallion, is a small round cameo showing {FACE}, facing out.",
 "mirror":  f"A small upright mirror stands on the desk; in its reflection we clearly see {FACE}.",
 "photo":   f"A small standing framed photo sits on the desk, a portrait of {FACE}.",
 "phone":   f"A smartphone is propped upright on the desk in selfie mode; on its screen, as a front-camera selfie, is {FACE}.",
 "monitor": f"A computer monitor sits on the desk; on its screen, as a video-call self-view, is {FACE}.",
 "badge":   f"An ID badge on a lanyard lies on the desk; its photo shows {FACE}.",
}

def build(key):
    return "\n\n".join([STYLE, POV, EXAM, DEVICE[key], BRAND,
        "The only text anywhere is the forehead word OCIC (inside the device) and the exam title EXAM. No other labels. "
        "Square format, an almost bare desk with only the exam and the one face-device on it."])

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    failed = []
    for key in DEVICE:
        if only and key != only:
            continue
        out = os.path.join(HERE, f"img/fp_{key}.png")
        print(f"[{key:8s}] {len(build(key))} chars")
        try:
            generate(client, build(key), "gpt-image-2", "low", "1024x1024", out)
        except Exception as e:
            print(f"  FAILED: {str(e)[:120]}"); failed.append(key)
    if failed:
        print("failed:", ", ".join(failed))

if __name__ == "__main__":
    main()

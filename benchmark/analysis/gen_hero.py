#!/usr/bin/env python3
"""Key art / hero: leg 5D, the busiest valid configuration, built from the FINAL
prop vocabulary (titled TASK paper + printed recipe, warm-up graded sheet in the
bubble, Brave embedded on the desk, simpler stickman, OCIC brow, lightly tired).

Across-the-desk framing so the face, the thought bubble AND the desk all read (5D
has a bubble, which needs a head above the desk).

Run: python3 gen_hero.py [quality]   (low default; medium/high for a final)
"""
import os, sys
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = ("Art style: a soft graphite pencil drawing on warm off-white paper, smooth confident shading with rich "
    "tonal contrast, minimal hard outlines, soft edges. Monochrome graphite grey only. Crafted and consistent with "
    "a hand-drawn prop sheet.")

COMP = ("COMPOSITION: across the desk, seen front-and-above. The character sits behind the desk facing us; we look "
    "from the near side and slightly downward, so the wide desk surface fills the foreground and the character's "
    "face is clearly visible above the far edge.")

CHAR = ("The character is a plain simple STICK FIGURE: a round head with two small dot eyes and a short straight "
    "mouth, a small torso and thin line arms, minimal and clean, not cute and not big-eyed. It looks LIGHTLY TIRED: "
    "faint shadows under the eyes, slightly messy hair. Across its forehead the word \"OCIC\" is stamped in small "
    "plain block capitals.")

BUBBLE = ("Above the character's head is a small cloud-shaped THOUGHT BUBBLE with two trailing circles, and inside it "
    "sits a single graded task paper: a filled-in sheet headed \"TASK\" with a check mark (one warm-up already done).")

DESK = ("On the desk, turned to FACE THE STUDENT, lies the task paper: the word \"TASK\" printed at the top as a "
    "heading, a few lines of illegible scribbled brief beneath it, and blank ruled answer lines; and near the top a "
    "single bordered box of illegible scribbled text is printed directly onto the paper (the recipe, printed on the "
    "task itself). On the vertical FRONT FACE of the desk, the real Brave browser logo is embedded in monochrome grey: "
    "the flat, geometric, stylised lion-head mark made of simple angular shapes (the actual brand logo), NOT a "
    "realistic or ornamental lion.")

KEYART = ("This is the KEY ART, the hero frame of the whole set: the most polished and carefully composed image, "
    "centred and balanced, a little more finished and confident than the rest, using EXACTLY the same props and "
    "soft-pencil style as the prop sheets so every other frame stays on-model against it. The only legible text is "
    "\"OCIC\" on the forehead and \"TASK\" on the papers; everything else is illegible scribble; no other labels, "
    "no extra objects, the rest of the desk bare.")

def main():
    quality = sys.argv[1] if len(sys.argv) > 1 else "low"
    prompt = "\n\n".join([STYLE, COMP, CHAR, BUBBLE, DESK, KEYART])
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    out = os.path.join(HERE, f"img/hero_{quality}.png")
    print(f"[hero {quality}] leg 5D, {len(prompt)} chars")
    generate(client, prompt, "gpt-image-2", quality, "1024x1024", out)

if __name__ == "__main__":
    main()

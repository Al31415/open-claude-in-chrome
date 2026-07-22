#!/usr/bin/env python3
"""Composition exploration: how to show the character's FACE and the DESK together
while keeping the first-person feel of looking at one's own desk. Same minimal
content in every frame; only the camera/pose changes. Also carries the reverted
simpler stickman and the titled exam ("EXAM" under the cheat panel).

Writes img/comp_<key>.png. Run: python3 gen_compositions.py [KEY]
"""
import os, sys
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = ("Art style: a soft graphite pencil drawing on warm off-white paper, smooth confident shading with rich "
    "tonal contrast, minimal hard outlines, soft edges. Monochrome graphite grey only. Crafted and consistent.")

# the simpler earlier stickman (NOT the rounder big-eyed one)
CHAR = ("The character is a plain, simple STICK FIGURE: a round head with two small dot eyes and a short straight "
    "mouth line, a small simple torso and thin line arms, minimal and clean, not cute and not big-eyed. Across its "
    "forehead the word \"OCIC\" is stamped in small plain block capitals. Its face is fresh, alert and calm.")

# the titled exam: cheat panel, and the word EXAM printed right under it as the title
EXAM = ("On the desk lies a single sheet of exam paper with blank ruled answer lines; near the top of the sheet is a "
    "small printed box filled with many tiny dense lines (a cheat panel), and directly BENEATH that box the word "
    "\"EXAM\" is printed clearly as the sheet's title.")

DESK = ("On the vertical front face of the desk is the Brave browser lion-head logo, drawn in monochrome grey. The "
    "only text anywhere is the forehead word \"OCIC\" and the exam title \"EXAM\"; no other labels.")

COMPS = {
 "across": ("COMPOSITION, across the desk: the character sits on the far side of the desk facing us; we look from the "
    "near side and slightly downward, so the desk surface fills the foreground as a first-person view of the desk and "
    "the character's face is clearly visible above the far edge. This is the natural interview-across-a-desk framing."),
 "corner": ("COMPOSITION, three-quarter corner: we sit at a corner of the desk, so the desk recedes diagonally into "
    "the frame as a first-person angled view. The character is seated at the adjacent side with its body and face "
    "turned three-quarters toward us, so we see both the angled desk and the face at once, a natural seated angle."),
 "leaning": ("COMPOSITION, leaning over: the character stands and leans forward over the far edge of the desk with "
    "both hands on it, looking down at the desk surface; we view the desk from the near side in first person, and "
    "because the character is bent forward over the desk its face tilts down into view toward us."),
 "reflection": ("COMPOSITION, reflection: a true first-person over-the-shoulder view, we are just behind and above the "
    "character seeing the back of its round head with the desk spread out below in first person. The character's face "
    "is shown as a reflection in a small upright mirror standing on the desk, so we get both the first-person desk and "
    "the face."),
 "inset": ("COMPOSITION, corner inset: the whole frame is the first-person view of the desk as seen from the "
    "character's own eyes, just the desk surface and the exam from above, no body. In one corner sits a small round "
    "framed cameo inset showing the character's face looking out, like a portrait medallion overlaid on the scene."),
}

def build(comp_key):
    return "\n\n".join([STYLE, COMPS[comp_key], CHAR, EXAM, DESK,
        "Square format, balanced composition, generous quiet space, an almost bare desk with only the exam on it."])

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    failed = []
    for key in COMPS:
        if only and key != only:
            continue
        prompt = build(key)
        out = os.path.join(HERE, f"img/comp_{key}.png")
        print(f"[{key:11s}] {len(prompt)} chars")
        try:
            generate(client, prompt, "gpt-image-2", "low", "1024x1024", out)
        except Exception as e:
            print(f"  FAILED: {str(e)[:120]}"); failed.append(key)
    if failed:
        print("failed:", ", ".join(failed))

if __name__ == "__main__":
    main()

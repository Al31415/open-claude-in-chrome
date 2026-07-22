#!/usr/bin/env python3
"""Generate the V1 character prop sheet by GROUNDING on real leg sample images,
so the character's style is copied from the actual scenes (cold baselines, phase 2,
phase 4) rather than described in words. The samples are passed to the edits
endpoint as visual context.

Run: python3 gen_char.py [quality]   (writes img/prop_v1-character.png)
"""
import os, sys
from gen_image import load_key, generate_edit
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

# the samples the user pointed to as authentic character style
SAMPLES = [
    "img/leg_1a-brave_low.png",   # cold baseline, fresh
    "img/leg_1a-chrome_low.png",  # cold baseline, fresh
    "img/leg_2a_low.png",         # phase 2, fresh
    "img/leg_4a_low.png",         # phase 4, tired (fewer body shadows)
]

PROMPT = (
"The attached images are SAMPLE scenes that define the EXACT art style and the EXACT character to use. Study the "
"character in them closely: the round head, the plain simple blank body, the light soft pencil linework, the gentle "
"minimal shading. You must match that character and that style EXACTLY, same line weight, same light shading, not "
"heavier, not more 3D.\n\n"
"Draw a PROP SHEET of that SAME character in that SAME exact style. Lay it out as a 2-row by 4-column grid of eight "
"equal panels, divided by thin straight pencil lines, on one off-white sheet. Every panel shows the same character "
"(identical head, body and proportions) from the upper body up, front view, drawn exactly like the samples. Only two "
"things change:\n"
"(a) the TIREDNESS on the face, increasing left to right across the four columns: column 1 fresh and alert with neat "
"hair and no eye shadows; column 2 slightly tired, faint under-eye shadows, a little messy hair; column 3 clearly "
"tired, darker baggy under-eye shadows, messier hair; column 4 utterly exhausted, heavy dark under-eye shadows, very "
"messy hair.\n"
"(b) the WORD stamped on the forehead in small plain block capitals: the TOP ROW says OCIC on every forehead, the "
"BOTTOM ROW says CinC on every forehead.\n\n"
"The tiredness lives only in the FACE and HAIR; the body stays the same plain light body as in the samples in all "
"eight panels. The only text anywhere is the forehead words (OCIC and CinC). No other labels.")

def main():
    quality = sys.argv[1] if len(sys.argv) > 1 else "low"
    paths = [os.path.join(HERE, s) for s in SAMPLES]
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    out = os.path.join(HERE, "img/prop_v1-character.png")
    print(f"[char {quality}] {len(paths)} samples, {len(PROMPT)} chars")
    generate_edit(client, PROMPT, paths, "gpt-image-2", quality, "1024x1024", out)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Three sub-variants of the chosen pencil-stickman style, same scene (config B),
so the pick is purely about the pencil treatment. Writes img/pv_<variant>_b.png.

Run: python3 gen_pencil_variants.py [variant]   (variant optional filter)
"""
import os, sys
from gen_image import load_key, generate
from gen_styles import scene, CONFIGS
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
OPTS = dict(crest_loc="forehead", mono_browser=True)  # forehead word + grey logo

VARIANTS = {
    "clean": ("Art style: an ULTRA-CLEAN minimal pencil line drawing. Thin, even, tidy graphite "
              "outlines and NO shading at all, lots of clean white space. The person is a plain "
              "stick figure (line limbs, round head). Everything is one monochrome pencil grey, "
              "including the browser logo (kept in its real recognisable shape, just grey). Calm, "
              "crisp, uncluttered."),
    "loose":  ("Art style: a LOOSE, energetic hand-drawn pencil sketch. Quick gestural scribbly "
               "strokes, visible construction lines, slightly overlapping and imperfect, a rough "
               "sketchbook feel. The person is a plain stick figure. Everything is monochrome "
               "pencil grey, including the browser logo (real recognisable shape, grey). Lively "
               "and hand-made, not neat."),
    "soft":   ("Art style: a SOFT graphite pencil drawing with smooth gentle tonal shading and "
               "light volume, minimal hard outlines, soft edges, like a carefully shaded sketch. "
               "The person is a plain stick figure. Everything is monochrome graphite grey, "
               "including the browser logo (real recognisable shape, grey). Quiet and tactile."),
}

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    c = CONFIGS["b"]
    body = scene(c["source_desk"], c["source_mind"], c["browser"], c["face"],
                 c["harness_word"], **OPTS)
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    for v, style in VARIANTS.items():
        if only and v != only:
            continue
        prompt = style + "\n\n" + body
        out = os.path.join(HERE, f"img/pv_{v}_b.png")
        print(f"[{v}] {len(prompt)} chars")
        generate(client, prompt, "gpt-image-2", "low", "1024x1024", out)

if __name__ == "__main__":
    main()

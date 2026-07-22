#!/usr/bin/env python3
"""One soft-pencil render per benchmark arm (leg), assembled from a template so
every image is the same scene with only that arm's channels changed.

Channels -> visuals (locked house style = soft graphite pencil stickman):
  harness (ocic/official) -> word stamped on the forehead (OCIC / CinC)
  browser (brave/chrome)  -> real monochrome logo on the desk front
  tired                   -> the face (context load = the cost)
  the task                -> a blank final-exam paper on the desk (always)
  recipe (distilled)      -> cheat-sheet box PRINTED on the exam (in-task)
  prop=binder  (phase 2)  -> the source object on the desk, raw
  prop=analysis(phase 3)  -> the source object + a clean analysis sheet on top
  bubble       (phase 4/5)-> the source internalised, in a thought bubble
  source own/expert       -> experiential = completed practice exams / expert = a book

Run: python3 gen_arms.py [KEY]   (KEY optional: only render one arm, e.g. 4a)
"""
import os, sys
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

# the 13 arms, verbatim from build_style_bible.py (source of truth)
ARMS = [
 ("Cold · OCIC · Brave", "1a-brave", dict(harness="ocic", browser="brave", tired="fresh")),
 ("Cold · OCIC · Chrome", "1a-chrome", dict(harness="ocic", browser="chrome", tired="fresh")),
 ("Cold · Official CinC · Chrome", "1b-cinc", dict(harness="official", browser="chrome", tired="fresh")),
 ("2A · experiential raw mount", "2a", dict(harness="ocic", browser="brave", tired="fresh", prop="binder", source="own")),
 ("2B · expert raw mount", "2b", dict(harness="ocic", browser="brave", tired="fresh", prop="binder", source="expert")),
 ("3D · experiential analysis", "3d", dict(harness="ocic", browser="brave", tired="fresh", prop="analysis", source="own")),
 ("3C · expert analysis", "3c", dict(harness="ocic", browser="brave", tired="fresh", prop="analysis", source="expert")),
 ("4A · experiential fork", "4a", dict(harness="ocic", browser="brave", tired="wrecked", bubble=("own", "big"))),
 ("4B · expert fork", "4b", dict(harness="ocic", browser="brave", tired="baggy", bubble=("expert", "big"))),
 ("5A · recipe · per-site", "5a", dict(harness="ocic", browser="brave", tired="fresh", recipe=2, distilled=True)),
 ("5B · recipe · single", "5b", dict(harness="ocic", browser="brave", tired="fresh", recipe=1, distilled=True)),
 ("5C · atomic warm-up fork", "5c", dict(harness="ocic", browser="brave", tired="lightly", bubble=("warmup", "small"))),
 ("5D · warm-up + recipe", "5d", dict(harness="ocic", browser="brave", tired="lightly", recipe=1, distilled=True, bubble=("warmup", "small"))),
]

SOFT_STYLE = ("Art style: a soft graphite pencil drawing with smooth gentle tonal shading and light "
    "volume, minimal hard outlines, soft edges, like a carefully shaded sketch on off-white paper. "
    "The person is a plain STICK FIGURE with a round head. Everything is one monochrome graphite grey, "
    "including the browser logo, which keeps its real recognisable shape but is drawn in grey. Quiet and tactile.")

# hard constraints: the model otherwise pads the desk with props and labels everything
RULES = ("STRICT RULES. Draw ONLY the objects listed below and nothing else; the desk is otherwise bare. "
    "Add no extra books, folders, boxes, pencils, cups, or papers. Write NO words, titles, headings, or "
    "labels on any object or anywhere in the picture; every object is recognised by its SHAPE alone. The "
    "single and only piece of text in the whole image is the short word stamped on the forehead.")

HARNESS_WORD = {"ocic": "OCIC", "official": "CinC"}
BROWSER_NAME = {"brave": "Brave", "chrome": "Google Chrome"}
FACE = {
    "fresh":   "The student looks fresh and alert, calm, neat, no signs of tiredness.",
    "lightly": "The student looks slightly tired, faint shadows under the eyes, a little messy hair.",
    "baggy":   "The student looks tired, baggy eyes with clear dark shadows, messy hair.",
    "wrecked": "The student looks utterly exhausted and drained, heavy dark shadows under the eyes, very messy hair, slumped and worn out.",
}
# sources described by SHAPE only (no trigger words that induce labels/moderation)
SRC_OBJECT = {  # on the desk
    "own":    "a small neat stack of paper sheets, each filled in with a few answer lines and bearing a check mark",
    "expert": "a single closed hardcover book, lying flat",
    "warmup": "a single paper sheet filled in with a check mark",
}
SRC_MIND = {  # in the thought bubble
    "own":    "a tall stack of paper sheets, each filled in with answer lines and a check mark",
    "expert": "a single closed hardcover book",
    "warmup": "a single filled-in paper sheet with a check mark",
}

def scene(cfg):
    parts = [RULES]
    parts.append("A single student seated at a desk, seen from front-and-above: the camera looks in from the "
        "front and tilts down over the top of the desk toward the student, so the wide desk surface is the "
        "largest part of the picture.")
    # student + forehead + face
    parts.append(f"The student sits behind the desk facing us. {FACE[cfg['tired']]} Across the student's "
        f"FOREHEAD, in small plain block-capital letters like a stamp, is the word "
        f"\"{HARNESS_WORD[cfg['harness']]}\".")
    # thought bubble (internalised prior: forks + warm-ups)
    if cfg.get("bubble"):
        kind, size = cfg["bubble"]
        big = "a large" if size == "big" else "a small"
        parts.append(f"Above the student's head is {big} thought bubble containing {SRC_MIND[kind]}, "
            f"and nothing else in the bubble.")
    # desk: the blank test page, an optional printed reference panel, an optional source object
    panel = ""
    if cfg.get("recipe"):
        n = "two small rectangles side by side are" if cfg["recipe"] == 2 else "a small rectangle is"
        panel = (f"; near the top of that page {n} printed directly onto it, filled with many tiny dense "
                 f"lines (a compact printed reference panel that is part of the page itself)")
    desk = ("On the desk every sheet is turned to FACE THE STUDENT, so any lines read upside down from the "
        f"camera. On the LEFT lies a single sheet of paper printed with blank ruled answer lines and empty "
        f"answer boxes{panel}.")
    prop = cfg.get("prop")
    if prop == "binder":
        desk += f" On the RIGHT sits {SRC_OBJECT[cfg['source']]}. Nothing else is on the desk."
    elif prop == "analysis":
        desk += (f" On the RIGHT sits {SRC_OBJECT[cfg['source']]}, and resting flat on top of it is one clean, "
                 f"completely blank sheet of plain paper. Nothing else is on the desk.")
    else:
        desk += " The right half of the desk is completely empty. Nothing else is on the desk."
    parts.append(desk)
    # browser logo
    parts.append(f"On the vertical FRONT FACE of the desk is the real {BROWSER_NAME[cfg['browser']]} logo, "
        f"drawn in monochrome grey in its genuine recognisable shape (this logo is the only brand mark).")
    parts.append("Composition: balanced and centred, square format, generous quiet space around an almost "
        "bare desk. Remember: no text or labels anywhere except the one word on the forehead.")
    return SOFT_STYLE + "\n\n" + "\n\n".join(parts)

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    missing_only = "--missing" in sys.argv
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    failed = []
    for label, key, cfg in ARMS:
        if only and only != "--missing" and key != only:
            continue
        out = os.path.join(HERE, f"img/arm_{key}.png")
        if missing_only and os.path.isfile(out):
            continue
        prompt = scene(cfg)
        print(f"[{key:9s}] {label:32s} {len(prompt)} chars")
        try:
            generate(client, prompt, "gpt-image-2", "low", "1024x1024", out)
        except Exception as e:
            print(f"  FAILED: {str(e)[:120]}")
            failed.append(key)
    if failed:
        print("failed:", ", ".join(failed))

if __name__ == "__main__":
    main()

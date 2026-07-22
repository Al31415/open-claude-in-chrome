#!/usr/bin/env python3
"""Style-exploration matrix: 2 aggregates x 3 art styles = 6 low-quality renders.

The scene (concepts) stays constant; only STYLE and CONFIG vary. Brands (Brave,
Chrome, Claude) are drawn as their REAL logos; every other object is an abstract
concept and is simplified to the chosen style.

  Aggregate A = Claude crest + Brave  + expert source (book)
  Aggregate B = Claude crest + Chrome + experiential source (completed practice exams)

Run: python3 gen_styles.py         (writes img/style_<style>_<cfg>.png)
"""
import os
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- the constant scene, parameterised by source/browser/tiredness ----
def scene(source_desk, source_mind, browser, face, harness_word, crest_loc="chest", mono_browser=False):
    crest = (f'Written across the student\'s FOREHEAD in small plain block-capital letters, like a stamp, '
             f'is the word "{harness_word}" (just those letters, nothing else).'
             if crest_loc == "forehead" else
             f'On the student\'s chest is a small plain label reading "{harness_word}" in block capitals.')
    blogo = (f"the real {browser} logo drawn in MONOCHROME: a single-colour grey/black version of "
             f"the recognisable {browser} logo shape, no brand colours"
             if mono_browser else
             f"the real {browser} logo, drawn as the genuine recognisable brand logo")
    return f"""A single exam student seated at a desk, seen from front-and-above: the camera looks in from the front and tilts down over the top of the desk toward the student, so the wide desk surface and everything on it is the largest, most detailed part of the picture.

The student sits behind the desk facing us. {face} {crest}

Above the student's head is a thought bubble (rising from small circles). Inside the bubble: {source_mind}. This is the knowledge the student has already internalised.

On the desk, every paper is turned to FACE THE STUDENT, so its text and marks are oriented away from us and read upside down from the camera. On the left lies a single blank final-exam paper; printed directly onto that exam, in a distinct outlined box sitting just ABOVE the exam's title line, is a small cheat-sheet box (a boxed area of dense little lines, like a cheat sheet printed on the test itself). On the right sits {source_desk}, and resting flat on top of it is one clean, blank sheet of plain paper (a clear analysis summary sheet).

On the vertical front face of the desk is {blogo}.

Composition: balanced and centred, square format, generous quiet space around the scene. The {browser} logo on the desk is the only real brand logo; the forehead word is plain text; the exam, cheat box, book, practice exams and analysis sheet are simple abstract shapes."""

EXPERT_MIND = "a single closed book (the same book that is on the desk)"
EXPERT_DESK = "a closed book lying flat"
EXPER_MIND  = "a small stack of completed practice-exam sheets, each marked with a check (the same completed practice exams that are on the desk)"
EXPER_DESK  = "a small stack of completed practice-exam sheets, each marked with a check"

CONFIGS = {
    "a": dict(source_desk=EXPERT_DESK, source_mind=EXPERT_MIND, browser="Brave", harness_word="OCIC",
              face="The student looks fresh and alert, neat hair, calm face."),
    "b": dict(source_desk=EXPER_DESK, source_mind=EXPER_MIND, browser="Google Chrome", harness_word="CinC",
              face="The student looks tired and worn, tired eyes with faint shadows, slightly messy hair."),
}

STYLES = {
    "pencil": "Art style: a loose black-and-white PENCIL sketch on white paper. The person is a simple STICK FIGURE with a round head. Rough hand-drawn graphite lines, light sketchy shading, a hand-doodled notebook feel, deliberately simple and unpolished. Everything is pencil-grey EXCEPT the Claude and browser brand logos, which are drawn as their real full-colour recognisable logos.",
    "flat":   "Art style: a clean modern FLAT VECTOR illustration. Solid fills, bold even outlines, rounded friendly geometric shapes, a restrained muted palette. The person is a simple minimal flat character. The Claude and browser brand logos are rendered as their real recognisable full-colour brand marks.",
    "ink":    "Art style: a detailed black-and-white FINE-INK line drawing on warm off-white paper, precise thin linework with light crosshatch shading, an editorial illustration feel. The person is a simple line character. Monochrome ink EXCEPT the Claude and browser brand logos, which are drawn in their real recognisable full-colour form.",
}

# per-style scene tweaks (defaults keep chest crest + full-colour logos)
STYLE_OPTS = {
    "pencil": dict(crest_loc="forehead", mono_browser=True),
}

def build(style_key, cfg_key):
    c = CONFIGS[cfg_key]
    opts = STYLE_OPTS.get(style_key, {})
    return STYLES[style_key] + "\n\n" + scene(c["source_desk"], c["source_mind"],
                                              c["browser"], c["face"], c["harness_word"], **opts)

def main():
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None  # optional style filter
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    for style_key in STYLES:
        if only and style_key != only:
            continue
        for cfg_key in CONFIGS:
            prompt = build(style_key, cfg_key)
            out = os.path.join(HERE, f"img/style_{style_key}_{cfg_key}.png")
            print(f"[{style_key}/{cfg_key}] {len(prompt)} chars")
            generate(client, prompt, "gpt-image-2", "low", "1024x1024", out)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prop sheets: one grid-separated image per benchmark VARIABLE, each showing that
variable's permutations. Rendering all permutations of a variable in ONE pass keeps
them mutually consistent (same hand, same scale) -> continuity. Soft-pencil house style.

Writes img/prop_<key>.png. Run: python3 gen_props.py [KEY]
"""
import os, sys
from gen_image import load_key, generate
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = ("Art style: a soft graphite pencil drawing on warm off-white paper, smooth confident shading "
    "with rich tonal contrast and lively character, minimal hard outlines, soft edges. Monochrome graphite "
    "grey only. Crafted and consistent, like one page torn from a hand-drawn model / prop sheet.")

# the character matches the seated-student legs: soft pencil, LIGHT shading, minimal shadows
CHAR_STYLE = ("Art style: a soft graphite pencil drawing on warm off-white paper, the SAME look as the seated-student "
    "scenes in this project: clean, simple pencil linework with only LIGHT, gentle, airy shading that just suggests "
    "the roundness of the head and the body. Keep the shading minimal and soft; NO heavy or dark shading, NO strong 3D "
    "modelling, NO drop shadows. Monochrome graphite grey.")
CHAR_KEYS = {"v1-character"}

def grid(layout, panels, extra_text="No text or labels anywhere in the image."):
    return (f"This is a PROP SHEET. Lay it out as {layout}, the panels equal in size and evenly spaced on "
        f"one off-white sheet, divided by thin straight ruled pencil lines, each panel centred on its subject "
        f"with quiet space around it. Draw the SAME line quality and the SAME scale in every panel so the set "
        f"is perfectly consistent. {panels} {extra_text}")

# shared so the task paper looks identical everywhere it appears
TASK_PAPER = ("a sheet of test paper laid out in TWO clearly separate zones: at the TOP, the word \"TASK\" as a "
    "heading with a short block of a few lines of ILLEGIBLE scribbled text right beneath it (the task description); "
    "then a clear HORIZONTAL DIVIDER LINE and a gap; and BELOW the divider, plainly separate, a set of evenly spaced "
    "blank ruled answer lines (empty). The description block and the answer-line zone must read as two distinct parts "
    "with a hard cutoff between them, never blending or fading into each other")
GRADED = ("the TASK task paper (headed \"TASK\", a short illegible brief block, a divider line, then the ruled "
    "answer-line zone) but ALREADY FILLED IN and GRADED: the answer lines carry illegible handwriting and a grade "
    "mark (a check and a small circled score) sits near a top corner")

PROPS = [
 ("v1-character", grid(
    "a 2-row by 4-column grid of eight equal panels (a top row and a bottom row, each with four columns)",
    "Every panel shows the SAME simple character, upper body up, front view: a round head with two SMALL DOT EYES and "
    "a short straight mouth line, and below it a plain BLANK WHITE body, one simple smooth rounded torso with NO arms "
    "and no interior detail. The head size, the body shape and ALL proportions are IDENTICAL in every one of the eight "
    "panels; the ONLY things that change are (a) the tiredness on the FACE, increasing across the four columns, and "
    "(b) the word stamped on the forehead in small plain block capitals, changing between the two rows. "
    "The FOUR COLUMNS left to right: (1) fresh and alert, neat hair, no eye shadows; (2) slightly tired, faint light "
    "shadows under the eyes, a little messy hair; (3) clearly tired, dark baggy shadows, messier hair; (4) utterly "
    "exhausted, heavy dark shadows, very messy hair. "
    "The TOP ROW has the word OCIC on every forehead; the BOTTOM ROW has the word CinC on every forehead.",
    extra_text="The forehead words (OCIC and CinC) are the ONLY text anywhere in the image.")),

 ("v2-position", grid(
    "a 2 by 2 grid of four equal square panels",
    "Each panel shows a small desk from front-and-above. The four panels are the four FORMS in which supplied "
    "knowledge reaches the task, and they must look clearly different. "
    f"Top-left = NONE: just {TASK_PAPER}, and nothing else, a bare desk (no supplied knowledge). "
    f"Top-right = RAW: {TASK_PAPER} on the desk, and beside it {GRADED}, lying raw on the desk (there, but you must "
    "reach for it). "
    f"Bottom-left = ANALYSIS: {GRADED} lying on the desk, with a DISTINCT, SMALLER analysis sheet resting on top of "
    "only its upper portion and slightly offset, so the graded paper underneath extends beyond it and stays clearly "
    "visible around the sides and bottom. The analysis sheet is clean and neatly STRUCTURED and FORMATTED: it is "
    "HEADED with the word \"ANALYSIS\" (never \"TASK\") and has a few tidy, orderly sections of illegible text laid "
    "out as an outline with small sub-headings and short bullet-like blocks (typeset and organised, clearly unlike "
    "the loose handwriting on the graded paper), a written analysis of the content beneath it. "
    f"Bottom-right = RECIPE: {TASK_PAPER}, but with a bordered box of illegible scribbled text printed directly onto "
    "the paper near the top (supplied knowledge printed on the task itself, in hand).",
    extra_text="The only legible words anywhere are the heading \"TASK\" on the task papers and \"ANALYSIS\" on the "
    "analysis sheet; every other mark is illegible scribble.")),

 ("task-paper", grid(
    "a single row of three equal square panels",
    f"Every panel shows the SAME test paper at the same scale and position: {TASK_PAPER}. Only a printed reference "
    "box changes between panels. "
    "Left panel: the plain test paper, with no box. "
    "Middle panel: the same test paper with ONE bordered rectangular box of illegible scribbled text printed onto it "
    "just under the TASK heading (the recipe printed on the paper). "
    "Right panel: the same test paper with that box divided into TWO side-by-side sections, each filled with its own "
    "illegible scribbled text.",
    extra_text="The only legible word is the heading \"TASK\"; all other text is illegible scribble.")),

 ("v3-source", grid(
    "a 2 by 2 grid of four equal square panels (a top row and a bottom row)",
    f"Top-left (EXPERIENTIAL, one): a single instance of {GRADED}, hand-done and a little scrappy (the agent's own "
    "past work). "
    "Top-right (EXPERT, one): a single closed hardcover TEXTBOOK lying flat, clean and authoritative (authored "
    "knowledge). "
    "Bottom-left (EXPERIENTIAL, many): a neat STACK of several of those same filled-in, graded task sheets piled up. "
    "Bottom-right (EXPERT, many): a neat STACK of several closed textbooks piled up. "
    "Everything drawn at the same scale.",
    extra_text="The only legible word is the heading \"TASK\" on the experiential sheets; everything else is illegible "
    "scribble, and the textbook covers carry no title text.")),

 ("v4-prior",
    "One centred illustration on an off-white sheet: a soft cloud-shaped THOUGHT BUBBLE with two small trailing "
    f"circles beneath it, and inside the bubble sits {GRADED} as an example of its contents. The bubble is simply a "
    "container that can hold any of the source props; here it holds one graded task paper. The only legible word is "
    "the heading \"TASK\" on the sheet inside; everything else is illegible scribble; no other text or labels."),

 ("v6-browser", grid(
    "a single row of two equal square panels",
    "Each panel shows the same simple desk from front-and-above, its top bare, with the browser logo EMBEDDED on the "
    "vertical FRONT FACE of the desk, drawn in monochrome grey as if it is part of the desk. "
    "Left panel: the Brave browser lion-head logo on the desk front. "
    "Right panel: the Google Chrome circular pinwheel logo on the desk front. "
    "Show clearly how the logo sits embedded on the desk.")),
]

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    failed = []
    for key, panels in PROPS:
        if only and key != only:
            continue
        prompt = (CHAR_STYLE if key in CHAR_KEYS else STYLE) + "\n\n" + panels
        out = os.path.join(HERE, f"img/prop_{key}.png")
        print(f"[{key:13s}] {len(prompt)} chars")
        try:
            generate(client, prompt, "gpt-image-2", "low", "1024x1024", out)
        except Exception as e:
            print(f"  FAILED: {str(e)[:120]}")
            failed.append(key)
    if failed:
        print("failed:", ", ".join(failed))

if __name__ == "__main__":
    main()

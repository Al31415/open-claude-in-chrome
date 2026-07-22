#!/usr/bin/env python3
"""Leg -> key-art scaffolding.

A leg is a set of variable instantiations. Each channel maps to a NAMED prop on the
prop-design master sheet (by its label), and the template assembles a prompt that
references those props by name. The master sheet is passed to the edits endpoint as
a reference image so the model grounds style + props on it.

Prove on 5D first, then reuse for every leg.

Run: python3 gen_legs.py 5d [quality]
"""
import os, sys
from gen_image import load_key, generate_edit
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "img", "prop_master.png")

# --- the legs, as channel instantiations (the templated variable assignments) ---
# character=(tired,harness); browser; task=plain|recipe1|recipe2;
# desk=None|(source,"raw"|"analysis"); prior=None|(source,"single"|"stack")
LEGS = {
 "1a-brave": dict(character=("fresh", "OCIC"), browser="Brave", task="plain"),
 "1a-chrome": dict(character=("fresh", "OCIC"), browser="Chrome", task="plain"),
 "1b-cinc": dict(character=("fresh", "CinC"), browser="Chrome", task="plain"),
 "2a": dict(character=("fresh", "OCIC"), browser="Brave", task="plain", desk=("experiential", "raw")),
 "2b": dict(character=("fresh", "OCIC"), browser="Brave", task="plain", desk=("expert", "raw")),
 "3d": dict(character=("fresh", "OCIC"), browser="Brave", task="plain", desk=("experiential", "analysis")),
 "3c": dict(character=("fresh", "OCIC"), browser="Brave", task="plain", desk=("expert", "analysis")),
 "4a": dict(character=("wrecked", "OCIC"), browser="Brave", task="plain", prior=("experiential", "stack")),
 "4b": dict(character=("baggy", "OCIC"), browser="Brave", task="plain", prior=("expert", "stack")),
 "5a": dict(character=("fresh", "OCIC"), browser="Brave", task="recipe2"),
 "5b": dict(character=("fresh", "OCIC"), browser="Brave", task="recipe1"),
 "5c": dict(character=("lightly", "OCIC"), browser="Brave", task="plain", prior=("experiential", "single")),
 "5d": dict(character=("lightly", "OCIC"), browser="Brave", task="recipe1", prior=("experiential", "single")),
}

TL = {"fresh": ("FRESH", "fresh and rested: neat hair and a completely CLEAN face with absolutely NO bags and no marks under the eyes"),
      "lightly": ("LIGHTLY", "lightly tired: one small but CLEAR, distinct bag line under each eye, hair a little messy"),
      "baggy": ("BAGGY", "tired: clear, distinct bags under both eyes, messy hair"),
      "wrecked": ("WRECKED", "exhausted: heavy dark bags under both eyes, very messy hair")}
_CUT = ("a TASK heading and a short illegible description block, then a clear horizontal DIVIDER LINE and a gap, then "
    "the empty ruled answer lines below; the description block and the answer lines are two DISTINCT zones with a hard "
    "cutoff, never blending into each other")
TASK = {"plain": ("PLAIN TASK", f"the plain task paper exactly as on the master sheet: {_CUT}"),
        "recipe1": ("+ RECIPE", f"the task paper with, below the heading and above the divider, ONE recipe panel of "
                    f"dense illegible text; otherwise {_CUT}"),
        "recipe2": ("+ RECIPE ×2", f"the task paper with, below the heading and above the divider, TWO recipe panels "
                    f"side by side; otherwise {_CUT}")}
SRC1 = {"experiential": ('V3 · SOURCE "EXPERIENTIAL"', "a single filled-in, graded task sheet (the agent's own past work)"),
        "expert": ('V3 · SOURCE "EXPERT"', "a single closed textbook (authored knowledge)")}
SRCN = {"experiential": ('V3 · SOURCE "EXPERIENTIAL ×N"', "a stack of filled-in, graded task sheets"),
        "expert": ('V3 · SOURCE "EXPERT ×N"', "a stack of closed textbooks")}

BODY_NOTE = ("its body below the head is the SAME plain, blank, WHITE body used on the FRESH characters in the master "
    "sheet's V1 row: one simple smooth rounded torso shape, NO arms and NO interior detail; only the FACE changes with "
    "tiredness, the body is identical in every frame (never stick arms, never an oval-with-arms, never see-through)")
FACE_NOTE = ("its face is EXACTLY the V1 character: two small simple round DOT eyes and a short straight mouth line, "
    "nothing more; NEVER draw detailed, droopy, half-closed, almond, or shaded eyes. Under-eye BAGS are BINARY and "
    "DISCRETE, never faint, smudgy, or in-between: a FRESH face has ABSOLUTELY NO bags and no marks or shadows under "
    "the eyes at all (perfectly clean skin); a tired face has clear, distinct bag lines under the eyes. Tiredness is "
    "shown ONLY by these discrete bags and by messier hair, never by changing the eyes or the mouth")

def channels(leg):
    """Each instantiation -> a numbered prop reference grounded on the master sheet."""
    out = []
    tired, harness = leg["character"]
    tl_lbl, tl_desc = TL[tired]
    out.append(f'CHARACTER  [from V1 · THE CHARACTER, cell "{tl_lbl} · {harness}"]: a round head, {tl_desc}, with '
               f'"{harness}" stamped on its forehead, seated behind the desk facing us; {FACE_NOTE}; {BODY_NOTE}.')
    out.append(f'DESK + BROWSER  [from V6 · BROWSER, cell "{leg["browser"].upper()}"]: the desk seen front-and-above '
               f'with the {leg["browser"]} logo embedded on its vertical front face.')
    t_lbl, t_desc = TASK[leg["task"]]
    out.append(f'TASK PAPER  [from THE TASK PAPER, cell "{t_lbl}"]: {t_desc}, lying on the desk turned to face the '
               f'student (its text reading away from us).')
    if leg.get("desk"):
        src, form = leg["desk"]
        # a raw/analysis mount is the whole prior corpus = a STACK (distinct from a single warm-up sheet)
        s_ref, s_desc = SRCN[src]
        if form == "raw":
            out.append(f'DESK SOURCE  [from V2 · KNOWLEDGE FORM "RAW"; {s_ref}]: {s_desc}, lying raw on the desk '
                       f'beside the task (a whole corpus, there to be reached for).')
        else:
            out.append(f'DESK SOURCE + ANALYSIS  [from V2 · KNOWLEDGE FORM "ANALYSIS"; {s_ref}]: {s_desc}, with a '
                       f'distinct structured/formatted analysis sheet resting on top of the stack, offset so the '
                       f'stack stays visible underneath. The analysis sheet is HEADED with the word "ANALYSIS" (NOT '
                       f'"TASK"), a structured write-up with small section sub-headings and bullet-like blocks; it has '
                       f'NO grade mark and NO check (it is a write-up, not graded work); only the source underneath '
                       f'is graded.')
    if leg.get("prior"):
        src, count = leg["prior"]
        if count == "single":
            ref, desc = SRC1[src][0], "a single filled-in, graded task sheet (one warm-up already done)"
        else:
            ref, desc = SRCN[src]
        out.append(f'THOUGHT BUBBLE  [from V4 · INTERNALIZED PRIOR "BUBBLE = container"; holding {ref}]: a thought '
                   f'bubble above the head containing {desc}.')
    return out

def build_prompt(leg_id):
    leg = LEGS[leg_id]
    chans = channels(leg)
    body = "\n".join(f"{i+1}. {c}" for i, c in enumerate(chans))
    return (
"The attached image is a PROP DESIGN MASTER SHEET: a labelled reference of every prop for this project, all drawn in "
"one consistent soft graphite pencil style on warm off-white paper. Treat it as the single source of truth for BOTH "
"the drawing style and the exact look of each prop.\n\n"
"Draw ONE brand-new key-art scene (NOT a grid, NOT a copy of the sheet) in that exact same soft-pencil style, "
"assembling ONLY the props listed below, each copied faithfully from its labelled cell on the master sheet. "
"Composition: across the desk, seen front-and-above, so the desk fills the foreground and the character's face is "
"clearly visible above it; balanced, centred, square, generous quiet space.\n\n"
f"Props to assemble for this leg ({leg_id}):\n{body}\n\n"
"Rules: include ONLY the props listed; the rest of the desk is bare. Match the master sheet's linework and shading "
"exactly so this frame stays on-model. The character's BODY is always the same plain blank white FRESH body from V1 "
"(a simple rounded torso, no arms, no detail); only the face changes. The only legible text is the forehead word and "
"the word TASK; everything else is illegible scribble; add no labels, no titles, no extra objects.")

def build_baseline():
    return (
"The attached image is a PROP DESIGN MASTER SHEET: a labelled reference of every prop for this project, all drawn in "
"one consistent soft graphite pencil style on warm off-white paper. Treat it as the single source of truth for the "
"drawing style and the look of each prop.\n\n"
"Draw ONE brand-new BASELINE scene in that exact same soft-pencil style: the neutral starting scene, before any "
"variables are applied. Composition: across the desk, seen front-and-above, so the desk fills the foreground and the "
"character's face is clearly visible above it; balanced, centred, square, generous quiet space.\n\n"
"Scene:\n"
"1. CHARACTER [from V1 · THE CHARACTER, the FRESH cell]: a round head with two small simple DOT eyes and a short "
"straight mouth, fresh and rested, neat hair, and a completely CLEAN face with absolutely NO bags or marks under the "
"eyes; a completely BLANK forehead (NO word stamped on it); its body is the same plain blank WHITE FRESH body, one "
"simple smooth rounded torso with NO arms and NO interior detail, seated behind the desk facing us.\n"
"2. TASK PAPER [from THE TASK PAPER, cell \"PLAIN TASK\"]: the plain task paper exactly as on the master sheet, a TASK "
"heading and a short illegible description block, then a clear horizontal DIVIDER LINE and a gap, then the empty ruled "
"answer lines below; the description block and the answer lines are two DISTINCT zones with a HARD CUTOFF, never "
"blending into each other; lying on the desk turned to face the student.\n"
"3. DESK: a plain UNBRANDED desk; its vertical front face is completely blank with NO logo, emblem, or mark of any "
"kind.\n\n"
"Rules: nothing else on the desk, nothing in a thought bubble, no forehead word, no browser logo, no labels. The only "
"legible text is the word TASK; everything else is illegible scribble. Match the master sheet's linework and shading.")

def main():
    leg_id = sys.argv[1] if len(sys.argv) > 1 else "5d"
    quality = sys.argv[2] if len(sys.argv) > 2 else "low"
    prompt = build_baseline() if leg_id == "baseline" else build_prompt(leg_id)
    print(f"=== leg {leg_id} ({quality}) — {len(prompt)} chars ===\n{prompt}\n")
    client = OpenAI(api_key=load_key(os.path.join(HERE, "../../../.env")))
    out = os.path.join(HERE, f"img/leg_{leg_id}_{quality}.png")
    generate_edit(client, prompt, [MASTER], "gpt-image-2", quality, "1024x1024", out)

if __name__ == "__main__":
    main()

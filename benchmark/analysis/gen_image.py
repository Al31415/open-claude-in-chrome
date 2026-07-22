#!/usr/bin/env python3
"""Generate images from a text prompt via the OpenAI image API.

Style-experiment harness: pass a prompt, pick a model/quality/size, get PNGs.
Prompt stays constant across a run; sweep quality to compare cost vs fidelity.

Usage:
  # single image
  python3 gen_image.py --prompt-file aggregate_prompt.txt --quality high --out img/agg_high.png

  # quality sweep (low, medium, high) with ONE constant prompt
  python3 gen_image.py --prompt-file aggregate_prompt.txt --sweep-quality \
      --out-prefix img/aggregate --size 1024x1024

Key comes from OPENAI_API_KEY, or --env <path> to read it from a dotenv file.
"""
import argparse, base64, os, sys, time

def load_key(env_path):
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if env_path and os.path.isfile(env_path):
        for ln in open(env_path):
            ln = ln.strip()
            if ln.startswith("OPENAI_API_KEY="):
                return ln.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("No OPENAI_API_KEY in env or --env file")

def generate(client, prompt, model, quality, size, out_path, retries=4):
    from openai import BadRequestError
    t0 = time.time()
    last = None
    for attempt in range(retries):
        try:
            r = client.images.generate(model=model, prompt=prompt, quality=quality,
                                       size=size, n=1, moderation="low")
            break
        except BadRequestError as e:
            # output-stage moderation is stochastic; a re-roll usually passes
            if "moderation_blocked" in str(e) and attempt < retries - 1:
                print(f"  (moderation re-roll {attempt + 1}/{retries - 1})")
                last = e
                continue
            raise
    b64 = r.data[0].b64_json
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    dt = time.time() - t0
    kb = os.path.getsize(out_path) // 1024
    print(f"  {quality:6s} -> {out_path}  ({kb} KB, {dt:.1f}s)")
    return out_path

def generate_edit(client, prompt, image_paths, model, quality, size, out_path, retries=4):
    """Grounded generation: pass reference image(s) (e.g. the prop master sheet) to the
    edits endpoint so the model copies their style + props into a new composition."""
    from openai import BadRequestError
    t0 = time.time()
    r = None
    for attempt in range(retries):
        files = [open(p, "rb") for p in image_paths]
        try:
            img_arg = files if len(files) > 1 else files[0]
            r = client.images.edit(model=model, image=img_arg, prompt=prompt, size=size, quality=quality, n=1)
            break
        except BadRequestError as e:
            if "moderation_blocked" in str(e) and attempt < retries - 1:
                print(f"  (moderation re-roll {attempt + 1}/{retries - 1})")
                continue
            raise
        finally:
            for f in files:
                try: f.close()
                except Exception: pass
    b64 = r.data[0].b64_json
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    dt = time.time() - t0
    kb = os.path.getsize(out_path) // 1024
    print(f"  {quality:6s} -> {out_path}  ({kb} KB, {dt:.1f}s)")
    return out_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--out")
    ap.add_argument("--out-prefix")
    ap.add_argument("--sweep-quality", action="store_true")
    ap.add_argument("--env", default=os.path.join(os.path.dirname(__file__),
                                                   "../../../.env"))
    a = ap.parse_args()

    prompt = a.prompt
    if a.prompt_file:
        prompt = open(a.prompt_file).read().strip()
    if not prompt:
        sys.exit("Need --prompt or --prompt-file")

    from openai import OpenAI
    client = OpenAI(api_key=load_key(a.env))

    print(f"model={a.model} size={a.size}  prompt={len(prompt)} chars")
    if a.sweep_quality:
        if not a.out_prefix:
            sys.exit("--sweep-quality needs --out-prefix")
        for q in ("low", "medium", "high"):
            generate(client, prompt, a.model, q, a.size, f"{a.out_prefix}_{q}.png")
    else:
        if not a.out:
            sys.exit("Need --out (or use --sweep-quality with --out-prefix)")
        generate(client, prompt, a.model, a.quality, a.size, a.out)

if __name__ == "__main__":
    main()

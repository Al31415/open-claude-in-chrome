#!/usr/bin/env python3
"""Build the experiential Phase-2 environment from the raw phase-1 generation
traces.

These are traces extracted directly from a Claude Code session. The ONLY change
we make: inline image byte-data (base64 screenshots) is replaced with a
reference to an extracted frame in ./images/. Everything else in the trace is
kept exactly as Claude Code emitted it, because that structure is already
self-explanatory to the agent that consumes it.

Reproducible: source = environments/experiential/traces/<task>.trajectory.jsonl
(traces only; no finish/evaluation), output = environments/experiential/mounted/
<task>/{trace.jsonl, images/}. Rerun any time to rebuild.
"""
import json, os, base64, hashlib

SRC = "environments/experiential/traces"
OUT = "environments/experiential/mounted"
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

def replace_images(node, images_dir, order, byhash):
    """Recursively swap every base64 image block for a text reference block,
    writing the decoded bytes to images/. Identical frames share one file."""
    if isinstance(node, dict):
        src = node.get("source")
        if node.get("type") == "image" and isinstance(src, dict) and src.get("data"):
            data = src["data"]
            h = hashlib.sha1(data.encode()).hexdigest()
            if h not in byhash:
                ext = EXT.get(src.get("media_type"), "jpg")
                fn = "%04d.%s" % (len(order) + 1, ext)
                with open(os.path.join(images_dir, fn), "wb") as f:
                    f.write(base64.b64decode(data))
                byhash[h] = fn
                order.append(fn)
            fn = byhash[h]
            node.clear()
            node["type"] = "text"
            node["text"] = "[screenshot → images/%s]" % fn
            return
        for v in node.values():
            replace_images(v, images_dir, order, byhash)
    elif isinstance(node, list):
        for v in node:
            replace_images(v, images_dir, order, byhash)

def build_one(src_path, out_dir):
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    order, byhash, out_lines = [], {}, []
    for line in open(src_path):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        replace_images(o, images_dir, order, byhash)
        out_lines.append(json.dumps(o, ensure_ascii=False))
    open(os.path.join(out_dir, "trace.jsonl"), "w").write("\n".join(out_lines) + "\n")
    return len(out_lines), len(order)

def main():
    man = json.load(open("environments/experiential/manifest.json"))
    goals = {t["task_id"]: t["goal"] for t in man["tasks"]}
    if os.path.isdir(OUT):
        import shutil; shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    idx = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".trajectory.jsonl"):
            continue
        tid = f.split(".")[0]
        nrec, nimg = build_one(os.path.join(SRC, f), os.path.join(OUT, tid))
        idx.append((tid, nrec, nimg))
        print("%-12s %3d records, %2d frames -> mounted/%s/" % (tid, nrec, nimg, tid))

    readme = [
        "# Prior experience: your own past runs in this environment", "",
        "These are traces extracted directly from a Claude Code session — you",
        "(this same agent) completing similar tasks in this browser earlier.",
        "One folder per task: `trace.jsonl` is the session trace, `images/` holds",
        "the screenshots.", "",
        "The only modification from a raw session: inline image byte-data has been",
        "replaced with references. Where a screenshot used to sit in the trace you",
        "will now see `[screenshot → images/NNNN.jpg]`; open that file to view the",
        "frame. Nothing else about the trace format was changed.", "",
        "Read the run whose goal is closest to your current task and reuse the UI",
        "flow that already worked.", "",
        "## Tasks", "",
    ]
    for tid, nrec, nimg in idx:
        readme.append("- **%s/** — %s" % (tid, goals.get(tid, "?")))
    open(os.path.join(OUT, "README.md"), "w").write("\n".join(readme) + "\n")
    print("wrote mounted/README.md")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()

"""Process snapshots: the review pages the designer ruled on, kept as self-contained HTML.

    uv run python docs/process/build.py            # rebuild every snapshot from the manifest

Each page is one HTML file with its images inlined as base64 JPEG thumbnails, so it
opens from disk or from GitHub with nothing beside it. The manifest below is the
record: which frames were on the page, what the page said, what the designer said back.
Frames are named by their ledger id (or the spike's own filename) and looked up in the
source directories; a frame that is not on disk is written as a labelled empty tile so
the page still tells the truth about what was shown.

Snapshots are append-only. A new round gets a new entry, never an edit of an old one.
"""
from __future__ import annotations

import base64
import glob
import html
import io
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
THUMB_W = 720

# Where frames live on this machine. The pools are ignored and sit on the 4080 box, so
# the build looks in a scratch copy too; pass SNAP_FRAMES=<dir> to point somewhere else.
SOURCES = [
    os.path.join(ROOT, "surfaces", "_pool"),
    os.path.join(ROOT, "surfaces", "_pool-v4"),
    os.path.join(ROOT, "surfaces", "_pool-v5"),
    os.path.join(ROOT, "surfaces", "_pool-v6"),
    os.path.join(ROOT, "surfaces", "_pool-v7"),
    os.path.join(ROOT, "surfaces", "_calibration"),
    os.path.join(ROOT, "_local", "mesh"),
] + [p for p in os.environ.get("SNAP_FRAMES", "").split(os.pathsep) if p]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;800&family=IBM+Plex+Mono&display=swap');
*{box-sizing:border-box;min-width:0}
body{margin:0;padding:40px clamp(16px,4vw,56px) 80px;background:#FAFAF8;color:#111114;font:400 17px/1.5 Archivo,system-ui,sans-serif}
h1{font-weight:800;letter-spacing:-.045em;font-size:clamp(30px,4vw,48px);margin:0 0 6px;line-height:1}
h1 span{background:linear-gradient(90deg,#1E1A5C,#4B3BE8,#B44C9E,#D9628A);-webkit-background-clip:text;background-clip:text;color:transparent}
h2{font-weight:800;letter-spacing:-.03em;font-size:22px;margin:36px 0 4px}
p{max-width:72ch;color:#4A4A55;margin:0 0 10px}
.mono{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:12px;color:#4A4A55;word-break:break-all}
.meta{display:flex;gap:14px;flex-wrap:wrap;margin:0 0 18px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;border:1px solid rgba(17,17,20,.12);background:#fff}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin-top:14px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
figure{margin:0;background:#fff;border:1px solid rgba(17,17,20,.12);border-radius:14px;overflow:hidden}
figure img{display:block;width:100%;height:auto;background:#ECEAF6}
figure .missing{aspect-ratio:1664/944;display:grid;place-items:center;background:#ECEAF6;color:#4A4A55}
figcaption{padding:10px 14px;display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.verdict{border-left:3px solid #B44C9E;background:#fff;border-radius:0 12px 12px 0;padding:14px 18px;margin:28px 0 0;max-width:80ch}
.verdict b{font-weight:800}
nav{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 26px}
nav a{font-size:14px;color:#4B3BE8;text-decoration:none;border:1px solid rgba(17,17,20,.12);border-radius:999px;padding:2px 10px;background:#fff}
nav a.here{background:#111114;color:#FAFAF8;border-color:#111114}
"""


def find(frame: str) -> str | None:
    for d in SOURCES:
        exact = os.path.join(d, frame + ".png")
        if os.path.exists(exact):
            return exact
    for d in SOURCES:
        hits = glob.glob(os.path.join(d, frame + "*.png"))
        if hits:
            return sorted(hits)[0]
    return None


def thumb_b64(path: str) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.resize((THUMB_W, max(1, int(h * THUMB_W / w))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def figure(label: str, frame: str) -> str:
    path = find(frame)
    if path:
        img = f'<img src="{thumb_b64(path)}" alt="{html.escape(frame)}" loading="lazy">'
    else:
        img = f'<div class="missing">frame not on this machine</div>'
    return (f'<figure>{img}<figcaption><b>{html.escape(label)}</b>'
            f'<span class="mono">{html.escape(frame)}</span></figcaption></figure>')


def render(entry: dict, index: int, entries: list[dict]) -> str:
    nav = "".join(
        f'<a href="{e["slug"]}.html"{" class=here" if e is entry else ""}>{i + 1}. {html.escape(e["short"])}</a>'
        for i, e in enumerate(entries))
    sections = ""
    for sec in entry["sections"]:
        figs = "".join(figure(lbl, frame) for lbl, frame in sec["frames"])
        sections += (f'<h2>{html.escape(sec["title"])}</h2>'
                     + (f'<p>{html.escape(sec["text"])}</p>' if sec.get("text") else "")
                     + f'<div class="grid">{figs}</div>')
    verdict = (f'<div class="verdict"><b>The designer said:</b> {html.escape(entry["verdict"])}</div>'
               if entry.get("verdict") else "")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Handsel process: {html.escape(entry["short"])}</title><style>{CSS}</style></head>
<body><h1><span>Handsel</span> {html.escape(entry["title"])}</h1>
<div class="meta mono"><span class="pill">{entry["date"]}</span><span class="pill">BrandGate #22</span><span class="pill">round {index + 1} of {len(entries)}</span></div>
<nav>{nav}</nav>
<p>{html.escape(entry["lede"])}</p>
{sections}
{verdict}
</body></html>"""


def main() -> int:
    from manifest import ENTRIES  # noqa: PLC0415
    written = []
    for i, e in enumerate(ENTRIES):
        out = os.path.join(HERE, e["slug"] + ".html")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(e, i, ENTRIES))
        written.append((e["slug"], os.path.getsize(out) // 1024))
    for slug, kb in written:
        print(f"{slug}.html  {kb} KB")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    raise SystemExit(main())

"""Render the ident: ident.html seeked frame by frame, stitched to H.264.

    uv run python -m surfaces.motion.render --out surfaces/motion/out

The page takes ?t=<ms> and seeks its anime.js timeline there, so every frame is a
plain screenshot of a held state. That sidesteps the trap #11 names: Chrome's virtual
time advances timers without producing frames, so recording a playing page yields a
file of the right length holding the wrong pictures. Here the frame count is the loop
count, and ffprobe is asked to confirm it before anything is kept.

Outputs, in --out: frames/f_0000.png ..., masks/ for the sampled frames, ident.mp4
(1920x1080), ident-960.mp4 for the site, poster.jpg (the last frame), and score.json with
the gate's verdict on one frame a second, foreground declared.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lookdev import render as renderer  # noqa: E402

HTML = os.path.join(ROOT, "surfaces", "motion", "ident.html")
FPS = 30
SECONDS = 6
W, H = 1920, 1080


def frames(out: str, binary: str, wait_ms: int) -> list[str]:
    fdir = os.path.join(out, "frames")
    os.makedirs(fdir, exist_ok=True)
    paths = []
    n = FPS * SECONDS
    for i in range(n):
        t = round(i * 1000 / FPS)
        p = os.path.join(fdir, f"f_{i:04d}.png")
        if not os.path.exists(p):
            renderer.render(HTML, p, W, H, binary, wait_ms, query=f"?t={t}")
        paths.append(p)
        if i % 30 == 0:
            print(f"frame {i}/{n} at {t} ms", flush=True)
    return paths


def stitch(out: str, width: int, name: str) -> str:
    mp4 = os.path.join(out, name)
    vf = f"scale={width}:-2" if width != W else "null"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(out, "frames", "f_%04d.png"),
                    "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-movflags", "+faststart", mp4], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_frames,width,height,pix_fmt,codec_name",
                            "-of", "json", mp4], check=True, capture_output=True, text=True)
    st = json.loads(probe.stdout)["streams"][0]
    want = FPS * SECONDS
    if int(st["nb_read_frames"]) != want:
        os.remove(mp4)
        raise SystemExit(f"{name}: {st['nb_read_frames']} frames decoded, asked for {want}; not keeping it")
    print(f"wrote {os.path.relpath(mp4, ROOT)}: {st['codec_name']} {st['pix_fmt']} {st['width']}x{st['height']}, "
          f"{st['nb_read_frames']} frames, {os.path.getsize(mp4) // 1024} KB")
    return mp4


def score(out: str, binary: str, wait_ms: int) -> None:
    """One frame a second through the gate, each with its foreground declared, the way
    every composed surface is scored (surfaces/_lib.py): the same frame is rendered
    once more with ?mask=1, black foreground on white, and the gate judges the wash on
    the wash. The mark rules still run on the whole frame."""
    from surfaces import _lib
    from pipeline import gate, rules
    doc = rules.load()
    cfg = gate.load_config()
    mdir = os.path.join(out, "masks")
    os.makedirs(mdir, exist_ok=True)
    series = []
    for sec in range(SECONDS):
        i = sec * FPS
        f = os.path.join(out, "frames", f"f_{i:04d}.png")
        m = os.path.join(mdir, f"m_{i:04d}.png")
        if not os.path.exists(m):
            renderer.render(HTML, m, W, H, binary, wait_ms, query=f"?t={sec * 1000}&mask=1")
        mask = _lib.mask_from_png(m)
        v = gate.score_image(gate.load_image(f), cfg, doc, accepted_paths=[], foreground=mask)
        series.append({"t_ms": sec * 1000, "verdict": v["verdict"], "on_brand": v["on_brand"],
                       "failed_rules": v.get("failed_rules", []),
                       "reasons": [b["reason"] for b in v["breakdown"] if not b["passed"]],
                       "errored": [e["rule"] for e in v.get("errored", [])],
                       "foreground_frac": round(float(mask.mean()), 4)})
    with open(os.path.join(out, "score.json"), "w", encoding="utf-8") as fh:
        json.dump({"fps": FPS, "seconds": SECONDS, "sampled": series}, fh, indent=1)
    for s in series:
        print(f"  {s['t_ms']:>5} ms  {s['verdict']:>5}  on-brand {s['on_brand']}  fg {s['foreground_frac']}"
              f"  failed {s['failed_rules']}  {s['reasons']}  errored {s['errored']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m surfaces.motion.render")
    p.add_argument("--out", default=os.path.join(ROOT, "surfaces", "motion", "out"))
    p.add_argument("--chrome", default=None)
    p.add_argument("--wait-ms", type=int, default=3500, help="virtual time for fonts and the anime.js import")
    p.add_argument("--no-score", action="store_true")
    a = p.parse_args(argv)
    binary = a.chrome or renderer.chrome()
    paths = frames(a.out, binary, a.wait_ms)
    stitch(a.out, W, "ident.mp4")
    stitch(a.out, 960, "ident-960.mp4")
    from PIL import Image
    Image.open(paths[-1]).convert("RGB").save(os.path.join(a.out, "poster.jpg"), quality=86, optimize=True)
    if not a.no_score:
        score(a.out, binary, a.wait_ms)
    return 0


if __name__ == "__main__":
    sys.exit(main())

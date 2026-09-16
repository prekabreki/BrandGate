"""Render a lookdev HTML sheet to the PNG beside it, at CSS pixel size 1:1.

    python lookdev/render.py lookdev/takes/takes.html lookdev/takes/takes_03.png

The takes sheet lays six 720 px tiles on a 3x2 grid, 2352 by 1680 CSS pixels.
takes_03.png was once captured at half that window with a device scale factor
of 2, which yields a file of the right pixel size holding a quarter of the
sheet, one and a half takes, and nothing errors (#15). So this pins the
window to the sheet's own size and the scale factor to 1, serves the repo over
loopback (a file:// screenshot hangs on this box), and refuses to write a PNG
whose size is not the size it asked for.
"""
from __future__ import annotations

import argparse
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMES = (
    "/opt/google/chrome/chrome", "google-chrome", "chromium", "brave-browser",
    # Windows (#22: the surfaces were recomposed from the work box for the first time)
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Applicationrave.exe",
)


def chrome() -> str:
    """The browser that renders. BRANDGATE_CHROME wins when set; otherwise the first of
    CHROMES that exists on this machine."""
    override = os.environ.get("BRANDGATE_CHROME")
    if override:
        if os.path.exists(override):
            return override
        raise SystemExit(f"BRANDGATE_CHROME={override!r} does not exist")
    for c in CHROMES:
        p = c if os.path.isabs(c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    raise SystemExit("no Chrome found; install one, set BRANDGATE_CHROME, or pass --chrome")


def serve(root: str):
    handler = type("Quiet", (http.server.SimpleHTTPRequestHandler,),
                   {"log_message": lambda *a, **k: None})
    httpd = socketserver.TCPServer(("127.0.0.1", 0), lambda *a, **k: handler(*a, directory=root, **k))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def render(html: str, out: str, width: int, height: int, binary: str, wait_ms: int,
           scale: int = 1) -> None:
    """Screenshot `html` at width by height CSS pixels. `scale` is the device
    scale factor, so the PNG is scale times larger in each direction; the size
    check is against that, which is the whole point of this script."""
    from PIL import Image
    html = os.path.abspath(html)
    out = os.path.abspath(out)
    rel = os.path.relpath(html, ROOT).replace(os.sep, "/")
    httpd, port = serve(ROOT)
    try:
        cmd = [binary, "--headless=new", "--hide-scrollbars",
               f"--force-device-scale-factor={scale}",
               f"--window-size={width},{height}", f"--virtual-time-budget={wait_ms}",
               f"--screenshot={out}", f"http://127.0.0.1:{port}/{rel}"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=120)
    finally:
        httpd.shutdown()
    want = (width * scale, height * scale)
    with Image.open(out) as im:
        if im.size != want:
            os.remove(out)
            raise SystemExit(f"rendered {im.size}, asked for {want}; not keeping it")
    print(f"wrote {os.path.relpath(out, ROOT)} at {want[0]}x{want[1]}")


def print_pdf(html: str, out: str, binary: str, wait_ms: int) -> None:
    """Print `html` to a PDF. Page size and margins come from the page's own
    @page rule; Chrome's header and footer are off."""
    html = os.path.abspath(html)
    out = os.path.abspath(out)
    rel = os.path.relpath(html, ROOT).replace(os.sep, "/")
    httpd, port = serve(ROOT)
    try:
        cmd = [binary, "--headless=new", "--no-pdf-header-footer",
               f"--virtual-time-budget={wait_ms}", f"--print-to-pdf={out}",
               f"http://127.0.0.1:{port}/{rel}"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=120)
    finally:
        httpd.shutdown()
    if not os.path.exists(out) or os.path.getsize(out) < 1000:
        raise SystemExit(f"no PDF came out for {rel}")
    print(f"wrote {os.path.relpath(out, ROOT)}, {os.path.getsize(out) // 1024} KB")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python lookdev/render.py")
    p.add_argument("html")
    p.add_argument("out")
    p.add_argument("--size", default="2352x1680", help="CSS pixels, WxH; the takes sheet is 2352x1680")
    p.add_argument("--chrome", default=None)
    p.add_argument("--wait-ms", type=int, default=4000, help="virtual time for fonts to arrive")
    p.add_argument("--scale", type=int, default=1, help="device scale factor; the PNG is this many times the CSS size")
    a = p.parse_args(argv)
    if a.out.lower().endswith(".pdf"):
        print_pdf(a.html, a.out, a.chrome or chrome(), a.wait_ms)
        return 0
    w, h = (int(v) for v in a.size.lower().split("x"))
    render(a.html, a.out, w, h, a.chrome or chrome(), a.wait_ms, a.scale)
    return 0


if __name__ == "__main__":
    sys.exit(main())

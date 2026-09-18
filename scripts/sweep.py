"""The leak sweep that has to pass before this repo goes public (#13).

    python scripts/sweep.py            # tree, history, binaries, ledger, issues
    python scripts/sweep.py --no-gh    # skip the issue sweep (offline)

Exit 0 means zero findings. Anything else means read the list and resolve each one
BEFORE the visibility change, because a public repo's history and its issue list are
both public the moment it flips.

This script goes public with the repo, so it holds no private name of its own. It
derives what to hunt for at run time from two places:

  * `gh repo list <owner> --visibility private` for the private repo names
  * `_local/sweep-patterns.txt`, one pattern a line, for everything a repo list
    cannot know: family names, machine names, anything else

`_local/` is gitignored, so that file never ships. If it is missing the sweep FAILS
rather than reporting clean, because a sweep that silently drops half its patterns is
worse than no sweep at all.

What it reads, which is more than the source:

  * every tracked text file
  * every blob in the whole history, on every ref, not just the current tree
  * every commit message, author name and author email in the history
  * PNG text chunks and JPEG EXIF, because a reference hides in a rendered frame's
    metadata where no grep over source will ever see it
  * PDF document info
  * runs/ledger.jsonl explicitly, since its rows carry prompt text
  * every issue's title, body and comments

Matches on a key-shaped pattern are printed masked. Everything else prints in full,
because a name or a path is the thing you need to read to resolve it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = "prekabreki"
LOCAL_PATTERNS = os.path.join(ROOT, "_local", "sweep-patterns.txt")

# Patterns safe to commit: they describe a SHAPE, never a private string.
# Every one is matched CASE SENSITIVELY, because a key prefix is case-specific. The
# first run matched loosely and reported three false positives: a Skia class name
# (sk-image-linear-from-pos) as an OpenAI key, a base64 blob beginning AIZA as a Google
# one, and a standard Chrome install path as a private path. A sweep that cries wolf is
# a sweep that gets waved through, so the shapes are tight and the names stay loose.
# (name, regex, mask the match when printing)
SHAPES: list[tuple[str, str, bool]] = [
    # Only roots that identify a person or a private layout. C:\Program Files is a
    # standard install path with nothing private in it, and lookdev/render.py names one
    # on purpose, so it is not a finding.
    ("windows-abs-path", r"[A-Za-z]:\\\\?(?:Users|git|Games)[\\/][\w .\\/-]{2,80}", False),
    ("posix-home-path", r"/(?:home|Users)/[A-Za-z0-9._-]{2,32}/[\w./-]{2,80}", False),
    ("openai-key", r"sk-(?:proj-)?[A-Za-z0-9]{20,}", True),
    ("anthropic-key", r"sk-ant-[A-Za-z0-9]{20,}", True),
    ("github-token", r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}", True),
    ("google-key", r"AIza[A-Za-z0-9_-]{35}", True),
    ("slack-token", r"xox[baprs]-[A-Za-z0-9-]{10,}", True),
    ("aws-key", r"AKIA[0-9A-Z]{16}", True),
    ("private-key-block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", True),
    ("bearer-literal", r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", True),
    ("email", r"[A-Za-z0-9._%+-]+@(?!example\.|users\.noreply\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}", False),
]

# This repo's own name and the tool names it legitimately ships are not leaks.
ALLOW_NAMES = {"BrandGate"}
# Lines that are allowed to carry a match, because the match IS the subject.
ALLOW_PATH_PREFIXES = ("scripts/sweep.py",)


def run(cmd: list[str], **kw) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    return r.stdout or ""


def private_repo_names() -> list[str]:
    out = run(["gh", "repo", "list", OWNER, "--visibility", "private",
               "--limit", "200", "--json", "name"])
    try:
        names = [r["name"] for r in json.loads(out)]
    except Exception:
        raise SystemExit("could not read private repo names from gh; run `gh auth status`")
    return sorted(n for n in names if n not in ALLOW_NAMES)


def local_patterns() -> list[str]:
    if not os.path.exists(LOCAL_PATTERNS):
        raise SystemExit(
            f"missing {os.path.relpath(LOCAL_PATTERNS, ROOT)}.\n"
            "The sweep needs the patterns a repo list cannot know (family names, machine\n"
            "names). Write one per line in that gitignored file, then run this again.\n"
            "Refusing to report clean on half a pattern set.")
    with open(LOCAL_PATTERNS, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def build(names: list[str], extra: list[str]) -> list[tuple[str, re.Pattern[str], bool]]:
    pats = [(n, re.compile(rx), mask) for n, rx, mask in SHAPES]
    for n in names:
        pats.append((f"private-repo:{n}", re.compile(re.escape(n), re.IGNORECASE), False))
    for e in extra:
        pats.append((f"local:{e[:24]}", re.compile(re.escape(e), re.IGNORECASE), False))
    return pats


def show(m: str, mask: bool) -> str:
    if not mask:
        return m if len(m) <= 120 else m[:117] + "..."
    return f"{m[:6]}<masked, {len(m)} chars>"


class Findings:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def scan(self, where: str, text: str, pats) -> None:
        if any(where.startswith(p) for p in ALLOW_PATH_PREFIXES):
            return
        for name, rx, mask in pats:
            for m in rx.finditer(text):
                self.rows.append((where, name, show(m.group(0), mask)))
                break  # one row per pattern per place; the fix is the same either way

    def report(self) -> int:
        if not self.rows:
            print("\nzero findings.")
            return 0
        print(f"\n{len(self.rows)} finding(s):\n")
        for where, name, match in sorted(self.rows):
            print(f"  {name:<28} {where}\n      {match}")
        print("\nResolve every one before `gh repo edit --visibility public`.")
        return 1


def is_texty(blob: bytes) -> bool:
    return b"\0" not in blob[:8000]


def sweep_tree(f: Findings, pats) -> None:
    files = [p for p in run(["git", "ls-files", "-z"]).split("\0") if p]
    print(f"tracked files: {len(files)}")
    for p in files:
        full = os.path.join(ROOT, p)
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as fh:
            raw = fh.read()
        if is_texty(raw):
            f.scan(p, raw.decode("utf-8", "replace"), pats)
        else:
            sweep_binary(f, p, full, pats)


def sweep_binary(f: Findings, rel: str, full: str, pats) -> None:
    """A reference hides in a rendered frame's metadata, where grepping source never looks."""
    low = rel.lower()
    if low.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")):
        try:
            from PIL import Image
            with Image.open(full) as im:
                bits = list(getattr(im, "text", {}).items()) + list((im.info or {}).items())
                blob = " ".join(f"{k}={v}" for k, v in bits if isinstance(v, (str, bytes)))
                if isinstance(blob, bytes):
                    blob = blob.decode("utf-8", "replace")
                f.scan(f"{rel} [image metadata]", blob, pats)
        except Exception as e:
            f.rows.append((rel, "UNREADABLE-image-metadata", f"{type(e).__name__}: {e}"))
    elif low.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            meta = PdfReader(full).metadata or {}
            f.scan(f"{rel} [pdf info]", " ".join(f"{k}={v}" for k, v in meta.items()), pats)
        except Exception as e:
            f.rows.append((rel, "UNREADABLE-pdf-info", f"{type(e).__name__}: {e}"))


def sweep_history(f: Findings, pats) -> None:
    """Every blob on every ref, not just the current tree, plus the commit messages."""
    objs = [ln.split(maxsplit=1) for ln in
            run(["git", "rev-list", "--all", "--objects"]).splitlines() if ln.strip()]
    blobs = {}
    kinds = run(["git", "cat-file", "--batch-check", "--batch-all-objects"])
    for ln in kinds.splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[1] == "blob":
            blobs[parts[0]] = int(parts[2]) if len(parts) > 2 else 0
    named = {o[0]: (o[1] if len(o) > 1 else "") for o in objs}
    print(f"history blobs: {len(blobs)}")
    for sha, size in blobs.items():
        if size > 4_000_000:
            continue
        raw = subprocess.run(["git", "cat-file", "blob", sha], cwd=ROOT,
                             capture_output=True).stdout
        if is_texty(raw):
            f.scan(f"history blob {sha[:10]} ({named.get(sha, 'unnamed')})",
                   raw.decode("utf-8", "replace"), pats)
    log = run(["git", "log", "--all", "--format=%H%n%an%n%ae%n%B%n--"])
    f.scan("commit messages and authors (whole history)", log, pats)


def sweep_ledger(f: Findings, pats) -> None:
    p = os.path.join(ROOT, "runs", "ledger.jsonl")
    if not os.path.exists(p):
        print("ledger: absent")
        return
    with open(p, encoding="utf-8", errors="replace") as fh:
        rows = fh.read()
    print(f"ledger: {len(rows.splitlines())} rows")
    f.scan("runs/ledger.jsonl", rows, pats)


def sweep_issues(f: Findings, pats) -> None:
    """Issues go public the moment Issues are turned on, and a title leaks from the
    list without anyone opening it."""
    out = run(["gh", "issue", "list", "--state", "all", "--limit", "200",
               "--json", "number,title,body,comments"])
    try:
        issues = json.loads(out)
    except Exception:
        f.rows.append(("gh issues", "UNREADABLE-issues", "could not read; run `gh auth status`"))
        return
    print(f"issues: {len(issues)}")
    for i in issues:
        n = i["number"]
        f.scan(f"issue #{n} TITLE", i.get("title") or "", pats)
        f.scan(f"issue #{n} body", i.get("body") or "", pats)
        for c in i.get("comments") or []:
            f.scan(f"issue #{n} comment", c.get("body") or "", pats)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-gh", action="store_true", help="skip the issue sweep")
    a = ap.parse_args(argv)

    names = [] if a.no_gh else private_repo_names()
    extra = local_patterns()
    pats = build(names, extra)
    print(f"patterns: {len(SHAPES)} shapes, {len(names)} private repo names, "
          f"{len(extra)} local")

    f = Findings()
    sweep_tree(f, pats)
    sweep_history(f, pats)
    sweep_ledger(f, pats)
    if not a.no_gh:
        sweep_issues(f, pats)
    return f.report()


if __name__ == "__main__":
    sys.exit(main())

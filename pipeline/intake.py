"""Intake: a brand guide PDF becomes the rules file and tokens the gate reads.

    python -m pipeline.intake brand/guide_05.pdf --out brand/intake/
    python -m pipeline.intake brand/guide_05.pdf --out brand/intake/ --force
    python -m pipeline.intake diff brand/intake/rules.md brand/rules.md

Nobody hands a brand engineer rules.md; they hand over the guide (#26). So the first
stage is extraction: the guide's text goes to a language model with the parser's
section shape and trigger words in the prompt, and the model writes the rules and the
tokens. The hand-written set is never shown to it, which is what makes the diff a
measurement rather than a copy. Tuning happens afterwards, through the calibration
labels the gate already has.

The model runs through the local `claude` CLI, in a temp directory with no tools, on
the subscription. ANTHROPIC_API_KEY is stripped from its environment on purpose: that
key's account has no credit, and the CLI would prefer it over the login if it saw it.

Every run is a ledger row (model "claude-cli", tier "intake"), a failed one too, so
the intake has the same provenance as a generated ground. Text extraction is cached
beside the PDF, keyed on the PDF's hash, so a regenerated guide never reuses stale text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from pipeline import ledger, rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = os.path.join(ROOT, "brand", "prompts", "intake.md")
SECTIONS = ("Mark", "Colour", "Gradient", "Surface", "Type", "Motif", "Motion")
CLAUDE_TIMEOUT_S = 600


class IntakeError(RuntimeError):
    pass


# ---- the guide's text -----------------------------------------------------

def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def extract_text(source: str) -> str:
    """The guide as plain text. A .txt is read as is; a .pdf is extracted once and
    cached as <stem>.txt beside it with the PDF's hash in <stem>.txt.sha256."""
    if source.lower().endswith(".txt"):
        with open(source, encoding="utf-8") as fh:
            return fh.read()
    stem = os.path.splitext(source)[0]
    cache, stamp = stem + ".txt", stem + ".txt.sha256"
    digest = _sha(source)
    if os.path.exists(cache) and os.path.exists(stamp):
        with open(stamp, encoding="utf-8") as fh:
            if fh.read().strip() == digest:
                with open(cache, encoding="utf-8") as fh2:
                    return fh2.read()
    text = _pdf_to_text(source)
    with open(cache, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with open(stamp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(digest + "\n")
    return text


def _pdf_to_text(pdf: str) -> str:
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise IntakeError("no PDF text extractor: install poppler (pdftotext) or PyMuPDF")
    doc = fitz.open(pdf)
    return "\n".join(page.get_text() for page in doc)


# ---- the prompt -----------------------------------------------------------

def load_prompt(path: str | None = None) -> tuple[dict, str]:
    """Frontmatter (flat key: value) and body, same format as brand/prompts/*.md."""
    with open(path or PROMPT, encoding="utf-8") as fh:
        raw = fh.read().replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise IntakeError(f"{path or PROMPT}: no frontmatter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if "version" not in meta:
        raise IntakeError("intake prompt has no version")
    return meta, m.group(2).strip()


def build_prompt(guide_text: str, template: str) -> str:
    if "<<GUIDE>>" not in template:
        raise IntakeError("intake prompt has no <<GUIDE>> placeholder")
    return template.replace("<<GUIDE>>", guide_text.strip())


# ---- the model ------------------------------------------------------------

def call_claude(prompt: str, timeout_s: int = CLAUDE_TIMEOUT_S) -> str:
    """One `claude -p` call from an empty temp dir with no tools, so the model can
    read nothing but the prompt. Raises IntakeError on a non-zero exit."""
    exe = shutil.which("claude")
    if not exe:
        raise IntakeError("the claude CLI is not on PATH")
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([exe, "-p", "--tools", "", "--output-format", "text", prompt],
                           cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout_s)
    if r.returncode != 0:
        raise IntakeError(f"claude exited {r.returncode}: {r.stderr.strip()[:400]}")
    return r.stdout


FENCE = re.compile(r"```(\w+)?[ \t]*\n(.*?)\n```", re.S)


def parse_output(text: str) -> tuple[str, dict]:
    """The two fenced blocks, checked. A preamble or trailing chat is ignored; a
    missing section or unparseable JSON raises, so a half result never lands
    under the final name."""
    blocks = FENCE.findall(text)
    md = next((b for lang, b in blocks if (lang or "").lower() in ("markdown", "md")), None)
    js = next((b for lang, b in blocks if (lang or "").lower() == "json"), None)
    if md is None:
        raise IntakeError("no ```markdown block in the model's output")
    if js is None:
        raise IntakeError("no ```json block in the model's output")
    md = md.strip() + "\n"
    missing = [s for s in SECTIONS if not re.search(rf"^## {s}\s*$", md, re.M)]
    if missing:
        raise IntakeError(f"rules are missing sections: {', '.join(missing)}")
    if "—" in md:
        raise IntakeError("the rules contain an em dash")
    try:
        tokens = json.loads(js)
    except json.JSONDecodeError as e:
        raise IntakeError(f"tokens block is not JSON: {e}")
    return md, tokens


# ---- the run --------------------------------------------------------------

def run(source: str, out_dir: str, *, force: bool = False, prompt_path: str | None = None,
        ledger_path: str | None = None, call=call_claude) -> dict:
    """Extract, prompt, write. Returns the ledger row that was appended."""
    os.makedirs(out_dir, exist_ok=True)
    rules_out = os.path.join(out_dir, "rules.md")
    tokens_out = os.path.join(out_dir, "tokens.json")
    if os.path.exists(rules_out) and not force:
        print(f"{rules_out} exists; pass --force to run the model again", file=sys.stderr)
        return {}
    meta, template = load_prompt(prompt_path)
    text = extract_text(source)
    prompt = build_prompt(text, template)
    run_id = ledger.new_run_id()
    params = {"source": os.path.relpath(source, ROOT).replace(os.sep, "/"),
              "guide_chars": len(text), "out": os.path.relpath(out_dir, ROOT).replace(os.sep, "/")}
    t0 = time.monotonic()
    error, output_path = None, None
    try:
        raw = call(prompt)
        md, tokens = parse_output(raw)
        # write to temp names first, then move, so a crash leaves no half file
        for path, body in ((rules_out, md), (tokens_out, json.dumps(tokens, indent=2, ensure_ascii=False) + "\n")):
            tmp = path + ".partial"
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            os.replace(tmp, path)
        output_path = os.path.relpath(rules_out, ROOT).replace(os.sep, "/")
    except (IntakeError, subprocess.TimeoutExpired) as e:
        error = str(e)
    record = ledger.row(run_id=run_id, model=meta.get("model", "claude-cli"),
                        tier=meta.get("tier", "intake"), prompt_id=f"intake@{meta['version']}",
                        prompt_text=template, params=params, seed=None,
                        output_path=output_path, latency_s=time.monotonic() - t0, error=error)
    ledger.append(record, ledger_path)
    if error:
        raise IntakeError(error)
    return record


# ---- the diff -------------------------------------------------------------

STOP = {"the", "a", "an", "is", "are", "of", "on", "in", "and", "or", "to", "it", "its",
        "at", "as", "with", "for", "that", "this", "be", "by", "one", "every"}


def _bag(prose: str) -> set[str]:
    words = re.findall(r"[a-z0-9#]+", prose.lower().replace("`", ""))
    return {w for w in words if w not in STOP}


def _similar(a: str, b: str) -> float:
    A, B = _bag(a), _bag(b)
    return len(A & B) / len(A | B) if A | B else 0.0


def diff(guide_rules: str, hand_rules: str, threshold: float = 0.45) -> dict:
    """Per section: rules both sets state (best match over a word-overlap bar), rules
    only the guide produced, rules only the hand-written set has, and how many of
    each set the parser binds to a check. Greedy one-to-one matching, highest
    overlap first, so one hand-written rule cannot absorb every guide rule."""
    g = rules.parse(guide_rules)
    h = rules.parse(hand_rules)
    out = {"threshold": threshold, "sections": {}, "bound": {
        "guide": sum(1 for r in g if r.check != "manual"),
        "hand": sum(1 for r in h if r.check != "manual"),
        "guide_total": len(g), "hand_total": len(h)}}
    for sec in sorted({r.section for r in g} | {r.section for r in h}):
        gs = [r for r in g if r.section == sec]
        hs = [r for r in h if r.section == sec]
        pairs = sorted(((_similar(a.prose, b.prose), a, b) for a in gs for b in hs),
                       key=lambda t: -t[0])
        used_g, used_h, both = set(), set(), []
        for score, a, b in pairs:
            if score < threshold or a.id in used_g or b.id in used_h:
                continue
            used_g.add(a.id); used_h.add(b.id)
            both.append({"guide": a.id, "hand": b.id, "overlap": round(score, 2),
                         "guide_check": a.check, "hand_check": b.check})
        out["sections"][sec] = {
            "both": both,
            "guide_only": [{"id": r.id, "check": r.check, "prose": r.prose} for r in gs if r.id not in used_g],
            "hand_only": [{"id": r.id, "check": r.check, "prose": r.prose} for r in hs if r.id not in used_h],
        }
    return out


def format_diff(d: dict) -> str:
    lines = [f"bound to a check: guide {d['bound']['guide']} of {d['bound']['guide_total']}, "
             f"hand-written {d['bound']['hand']} of {d['bound']['hand_total']}  "
             f"(match bar: word overlap >= {d['threshold']})", ""]
    for sec, s in d["sections"].items():
        lines.append(f"## {sec}: {len(s['both'])} shared, {len(s['guide_only'])} guide only, {len(s['hand_only'])} hand only")
        for p in s["both"]:
            lines.append(f"  = {p['guide']} ~ {p['hand']}  overlap {p['overlap']}  checks {p['guide_check']}/{p['hand_check']}")
        for r in s["guide_only"]:
            lines.append(f"  + {r['id']:<12} {r['check']:<9} {r['prose'][:90]}")
        for r in s["hand_only"]:
            lines.append(f"  - {r['id']:<12} {r['check']:<9} {r['prose'][:90]}")
        lines.append("")
    return "\n".join(lines)


# ---- cli --------------------------------------------------------------------

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "diff":
        d = argparse.ArgumentParser(prog="python -m pipeline.intake diff",
                                    description="compare two rules files section by section")
        d.add_argument("guide_rules"); d.add_argument("hand_rules")
        d.add_argument("--json", action="store_true")
        a = d.parse_args(argv[1:])
        res = diff(a.guide_rules, a.hand_rules)
        print(json.dumps(res, indent=2) if a.json else format_diff(res))
        return 0
    ap = argparse.ArgumentParser(prog="python -m pipeline.intake", description=__doc__.split("\n\n")[0],
                                 epilog="or: python -m pipeline.intake diff <guide_rules.md> <hand_rules.md>")
    ap.add_argument("source", help="the brand guide, .pdf or .txt")
    ap.add_argument("--out", default=os.path.join(ROOT, "brand", "intake"), help="where rules.md and tokens.json land")
    ap.add_argument("--force", action="store_true", help="run the model even if --out holds a rules.md")
    a = ap.parse_args(argv)
    try:
        rec = run(a.source, a.out, force=a.force)
        if rec:
            print(f"wrote {rec['output_path']} and tokens.json in {rec['latency_s']} s; ledger row {rec['run_id']}")
        return 0
    except IntakeError as e:
        print(f"intake failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

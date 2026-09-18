"""Swap the model, hold everything else, and watch the on-brand distribution move.

    python -m runs.drift --models krea2 flux2 --n 48
    python -m runs.drift --models krea2 flux2 --n 48 --dry-run
    python -m runs.drift --score-only                  # re-gate and re-plot what is on disk

Everybody demos generation. This demos the thing a brand team actually pays
for: knowing, the week after a model is swapped, whether the house style
survived it. One prompt at one version, one tier, one size, the same seeds in
both arms, and the only thing that changes is which checkpoint drew the frame.
Whatever separates the two distributions is the model, because nothing else
was allowed to move.

Three artifacts, all under `runs/drift/`:

- `results.jsonl`, one row per frame: model, seed, verdict, on-brand, novelty,
  the rules it failed. The raw table, so the plot can be redrawn and disputed.
- `plot.png`, the distributions overlaid with the gate's own `on_brand_min`
  drawn across them. A histogram of one number per model is the whole claim.
- `scorecard.md`, the numbers a team would actually be handed: pass rate,
  spread, which rules fired and how often, and what each arm cost in time.
  Every figure is read from `results.jsonl` or `runs/ledger.jsonl`. None is
  typed by hand, which is the point of having a ledger at all.

**Novelty is measured against a fixed reference set**, the accepted grounds
this repo ships, and never against the arm's own frames. Measured within an
arm, novelty would say how varied that model is, which is a different and
easier question, and it would make the two arms incomparable because each
would be scored against a different reference.

The frames themselves land in `surfaces/_drift/<model>/` and are not tracked:
they are large and regenerable from the seeds in the ledger, exactly like the
sameness pool. The ledger rows are tracked, so the run is reproducible without
the pixels.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DRIFT_DIR = os.path.join(ROOT, "surfaces", "_drift")
OUT_DIR = os.path.join(ROOT, "runs", "drift")
LEDGER = os.path.join(ROOT, "runs", "ledger.jsonl")

# Fresh seeds, above the calibration block (1000s) and both pools (2000s,
# 3000s), so no drift frame shares a seed with a frame made for another
# question and the ledger stays readable by seed alone.
SEED_START = 4000

# The fixed reference for novelty: the grounds this repo has accepted, not the
# composed surfaces. A bare ground compared against a page with type laid over
# it measures the typography, not the generation.
REFERENCE_GLOB = os.path.join(ROOT, "surfaces", "*", "accepted", "ground*.png")

# Which brand colour each arm is drawn in. Two models, two token colours, from
# brand/tokens.json; a third model would need a third token, which is a brand
# decision and belongs in the tokens file rather than in a default palette.
ARM_COLOUR = {"krea2": "indigo", "flux2": "rose"}


def seeds(n: int, start: int = SEED_START) -> list[int]:
    return list(range(start, start + n))


def arm_dir(model: str, root: str = DRIFT_DIR) -> str:
    return os.path.join(root, model)


def reference_paths(pattern: str = REFERENCE_GLOB) -> list[str]:
    import glob
    return sorted(glob.glob(pattern))


# --------------------------------------------------------------------------
# generate


def fill_arms(models: list[str], n: int, prompt: str = "hero-ground",
              tier: str = "turbo", root: str = DRIFT_DIR,
              seed_start: int = SEED_START, prompt_version: int | None = None,
              dry_run: bool = False, backend=None,
              ledger_path: str | None = None) -> dict[str, list[dict]]:
    """One arm per model, the same seeds in each.

    `runs.pool.fill` already does this for one model and is resumable per
    seed, so an arm that dies at frame 30 of 48 resumes at 31 and the ledger
    still gets exactly one row per frame. Two arms is that, twice, with the
    prompt version pinned so a mid-run edit to the prompt cannot silently make
    the second arm answer a different question from the first.
    """
    from runs import pool

    out = {}
    for model in models:
        dest = arm_dir(model, root)
        print(f"\n== {model} / {tier}, {n} frames, seeds "
              f"{seed_start}..{seed_start + n - 1} -> {os.path.relpath(dest, ROOT)}",
              flush=True)
        out[model] = pool.fill(n, prompt, model, tier, dest,
                               seed_start=seed_start, dry_run=dry_run,
                               backend=backend, ledger_path=ledger_path,
                               prompt_version=prompt_version)
    return out


# --------------------------------------------------------------------------
# gate


def frames(model: str, root: str = DRIFT_DIR, prompt: str = "hero-ground",
           tier: str = "turbo") -> list[tuple[int, str]]:
    """(seed, path) for every frame in an arm, by seed. The filename is
    `<prompt>_<tier>_<seed>_<run>_00001_.png`, per `gen.generate`'s prefix."""
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(arm_dir(model, root), f"{prompt}_{tier}_*.png"))):
        parts = os.path.basename(p).split("_")
        try:
            out.append((int(parts[len(prompt.split("_")) + 1]), p))
        except (IndexError, ValueError):
            continue
    return sorted(out)


def gate_arm(model: str, root: str = DRIFT_DIR, prompt: str = "hero-ground",
             tier: str = "turbo", reference: list[str] | None = None,
             cfg: dict | None = None, doc: dict | None = None) -> list[dict]:
    from pipeline import gate, rules

    cfg = cfg or gate.load_config()
    doc = doc or rules.load()
    reference = reference_paths() if reference is None else reference
    rows = []
    for i, (seed, path) in enumerate(frames(model, root, prompt, tier)):
        r = gate.score_image(gate.load_image(path), cfg, doc, accepted_paths=reference)
        rows.append({
            "model": model, "tier": tier, "seed": seed,
            "image": os.path.relpath(path, ROOT).replace(os.sep, "/"),
            "verdict": r["verdict"], "on_brand": r["on_brand"],
            "novelty": r["novelty"], "failed_rules": r["failed_rules"],
            "counts": r["counts"],
            "reasons": {b["rule"]: b["reason"] for b in r["breakdown"]
                        if not b["passed"]},
            "errored": [e["rule"] for e in r["errored"]],
        })
        print(f"  [{i + 1:>3}] seed {seed}  {r['verdict']:<4} "
              f"on-brand {r['on_brand']}  novelty {r['novelty']:.2f}"
              + (f"  failed {r['failed_rules']}" if r["failed_rules"] else ""),
              flush=True)
    return rows


def write_results(rows: list[dict], path: str | None = None) -> str:
    path = path or os.path.join(OUT_DIR, "results.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def read_results(path: str | None = None) -> list[dict]:
    path = path or os.path.join(OUT_DIR, "results.jsonl")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --------------------------------------------------------------------------
# scorecard


def ledger_rows(models: list[str], seeds_: list[int], tier: str,
                path: str | None = None) -> dict[str, list[dict]]:
    """The generation rows behind this run, by model. Keyed on model, tier and
    seed rather than on time, so re-running an arm does not make the scorecard
    quote the first attempt's latency."""
    want = set(seeds_)
    out = collections.defaultdict(list)
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("model") in models and r.get("tier") == tier \
                        and r.get("seed") in want:
                    out[r["model"]].append(r)
    except OSError:
        pass
    return out


def summarise(rows: list[dict], led: list[dict] | None = None) -> dict:
    ob = [r["on_brand"] for r in rows if r["on_brand"] is not None]
    nov = [r["novelty"] for r in rows if r["novelty"] is not None]
    passed = [r for r in rows if r["verdict"] == "pass"]
    fails = collections.Counter(x for r in rows for x in r["failed_rules"])
    lat = [r["latency_s"] for r in (led or []) if r.get("latency_s") and not r.get("error")]
    cost = [r["cost_usd"] for r in (led or []) if r.get("cost_usd") is not None]
    return {
        "n": len(rows),
        "pass_rate": len(passed) / len(rows) if rows else None,
        "on_brand_mean": statistics.mean(ob) if ob else None,
        "on_brand_sd": statistics.stdev(ob) if len(ob) > 1 else None,
        "on_brand_min": min(ob) if ob else None,
        "on_brand_max": max(ob) if ob else None,
        "novelty_mean": statistics.mean(nov) if nov else None,
        "failed_rules": dict(fails.most_common()),
        "latency_median_s": statistics.median(lat) if lat else None,
        "latency_mean_s": statistics.mean(lat) if lat else None,
        "generated": len(led or []),
        "generation_errors": sum(1 for r in (led or []) if r.get("error")),
        "cost_usd_mean": statistics.mean(cost) if cost else None,
    }


def _n(v, fmt="{:.4f}", dash="n/a"):
    return dash if v is None else fmt.format(v)


def _pass_rate(rows: list[dict], model: str) -> float:
    mine = [r for r in rows if r["model"] == model]
    return sum(1 for r in mine if r["verdict"] == "pass") / len(mine) if mine else 0.0


def shared_seeds(rows: list[dict]) -> bool:
    """Did every arm draw the same seeds? The run's one real precondition."""
    by = collections.defaultdict(set)
    for r in rows:
        by[r["model"]].add(r["seed"])
    sets = list(by.values())
    return bool(sets) and all(s == sets[0] for s in sets)


def scorecard(rows: list[dict], cfg: dict, led: dict[str, list[dict]] | None = None,
              caveat: str | None = None) -> str:
    """The numbers a brand team would be handed, every one of them read from
    results.jsonl or the ledger."""
    models = list(dict.fromkeys(r["model"] for r in rows))
    by = {m: [r for r in rows if r["model"] == m] for m in models}
    stats = {m: summarise(by[m], (led or {}).get(m)) for m in models}
    bar = cfg["verdict"]["on_brand_min"]
    nov_bar = cfg["verdict"]["novelty_min"]

    out = ["# Drift: the same prompt and the same seeds, through two models", ""]
    if caveat:
        out += [caveat, ""]
    seeds_ = sorted({r["seed"] for r in rows})
    tiers = sorted({r["tier"] for r in rows})
    out += [
        f"{len(rows)} frames, {len(models)} models, {len(seeds_)} seeds "
        f"({min(seeds_)}..{max(seeds_)}), tier {'/'.join(tiers)}. "
        f"The gate passes a frame at on-brand {bar} and novelty {nov_bar}.",
        "",
    ]
    if not shared_seeds(rows):
        # The whole claim is that only the model changed. If the arms drew
        # different seeds, the gap between them is part model and part luck,
        # and no amount of formatting makes that comparison sound.
        out += ["> **The arms do not share a seed set**, so the difference below is not "
                "attributable to the model alone. This is a run of the machinery, not a "
                "drift result.", ""]
    out += [
        "| | " + " | ".join(models) + " |",
        "|---|" + "---|" * len(models),
    ]

    def row(label, fn):
        out.append(f"| {label} | " + " | ".join(fn(stats[m]) for m in models) + " |")

    row("frames scored", lambda s: str(s["n"]))
    row("pass rate", lambda s: _n(s["pass_rate"], "{:.0%}"))
    row("on-brand mean", lambda s: _n(s["on_brand_mean"]))
    row("on-brand spread (sd)", lambda s: _n(s["on_brand_sd"]))
    row("on-brand range", lambda s: f"{_n(s['on_brand_min'])} to {_n(s['on_brand_max'])}")
    row("novelty mean", lambda s: _n(s["novelty_mean"], "{:.3f}"))
    row("median latency", lambda s: _n(s["latency_median_s"], "{:.0f} s"))
    row("mean latency", lambda s: _n(s["latency_mean_s"], "{:.0f} s"))
    row("generation errors", lambda s: str(s["generation_errors"]))
    row("cost per frame",
        lambda s: _n(s["cost_usd_mean"], "${:.4f}", "local, unmetered"))

    out += ["", "## Which rules fired", ""]
    every = sorted({k for m in models for k in stats[m]["failed_rules"]})
    if not every:
        out += ["No frame failed a rule in either arm.", ""]
    else:
        out += ["| rule | " + " | ".join(models) + " | one frame's reason |",
                "|---|" + "---|" * (len(models) + 1)]
        # The first occurrence in seed order, not the last one seen, so the
        # column is the same on every re-run of the same results file. It is
        # an example of what the rule said, not the rule's own wording.
        reasons = {}
        for r in sorted(rows, key=lambda x: (x["model"], x["seed"])):
            for k, v in (r.get("reasons") or {}).items():
                reasons.setdefault(k, v)
        for rule in every:
            cells = " | ".join(f"{stats[m]['failed_rules'].get(rule, 0)}/{stats[m]['n']}"
                               for m in models)
            out.append(f"| `{rule}` | {cells} | {reasons.get(rule, '')} |")
        out.append("")

    errored = sorted({e for r in rows for e in r["errored"]})
    if errored:
        out += ["> Rules that could not run and are therefore in no number above: "
                + ", ".join(f"`{e}`" for e in errored) + ".", ""]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# figure


def figure(rows: list[dict], cfg: dict, out_path: str | None = None,
           caption: str = "") -> str:
    """Two panels: the on-brand distribution per model, and novelty.

    A violin plus every point, not a bar of the mean. The claim is about the
    shape of the distribution, and a mean hides the arm that passes on average
    while throwing one frame in six over the bar.
    """
    import logging

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from runs import plot as plot_helpers

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    c = plot_helpers.brand()
    plt.rcParams.update({
        "font.family": ["Archivo", "IBM Plex Sans", "DejaVu Sans", "sans-serif"],
        "font.size": 11,
        "axes.edgecolor": c["graphite"], "axes.labelcolor": c["ink"],
        "xtick.color": c["graphite"], "ytick.color": c["graphite"],
        "text.color": c["ink"],
        "figure.facecolor": c["paper"], "axes.facecolor": c["paper"],
        "savefig.facecolor": c["paper"],
    })

    models = list(dict.fromkeys(r["model"] for r in rows))
    colours = [c[ARM_COLOUR.get(m, "indigo")] for m in models]
    out_path = out_path or os.path.join(OUT_DIR, "plot.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4), dpi=150)
    panels = [
        (axes[0], "on_brand", "on-brand", cfg["verdict"]["on_brand_min"],
         "agreement with the brand rules"),
        (axes[1], "novelty", "novelty", cfg["verdict"]["novelty_min"],
         "distance from the accepted grounds"),
    ]
    rng = np.random.default_rng(0)  # jitter only, so the figure redraws identically
    for ax, key, title, bar, ylabel in panels:
        data = [[r[key] for r in rows if r["model"] == m and r[key] is not None]
                for m in models]
        if any(len(d) > 1 for d in data):
            parts = ax.violinplot([d for d in data if d], showextrema=False,
                                  positions=[i for i, d in enumerate(data) if d],
                                  widths=0.7)
            for body, col in zip(parts["bodies"],
                                 [col for col, d in zip(colours, data) if d]):
                body.set_facecolor(col)
                body.set_edgecolor(col)
                body.set_alpha(0.22)
        # Filled for a frame that passed, hollow for one that failed. Without
        # this the panel quietly disagrees with the scorecard: a frame fails
        # when ANY rule fails, so 21 of flux2's 48 failures sit at 0.94 to
        # 0.97, well above the bar. A reader seeing only the cloud and the
        # dashed line would conclude that arm passed nearly everything.
        for i, (m, col) in enumerate(zip(models, colours)):
            mine = [r for r in rows if r["model"] == m and r[key] is not None]
            ok = [r[key] for r in mine if r["verdict"] == "pass"]
            bad = [r[key] for r in mine if r["verdict"] != "pass"]
            ax.scatter(i + rng.uniform(-0.09, 0.09, len(ok)), ok, s=26, color=col,
                       alpha=0.85, linewidths=0, zorder=3)
            ax.scatter(i + rng.uniform(-0.09, 0.09, len(bad)), bad, s=30,
                       facecolors="none", edgecolors=col, linewidths=1.3,
                       alpha=0.95, zorder=3)
            if data[i]:
                ax.hlines(statistics.mean(data[i]), i - 0.28, i + 0.28, color=col,
                          lw=2.4, zorder=4)
        ax.axhline(bar, color=c["graphite"], lw=1, ls="--")
        # Anchored in axes fraction, not in data: at the right-hand end the
        # label lands past the last violin and matplotlib clips it away
        # without a word, which leaves a bare dashed line meaning nothing.
        ax.annotate(f"the gate's {title} bar, {bar}", xy=(0.012, bar),
                    xycoords=("axes fraction", "data"), xytext=(0, 4),
                    textcoords="offset points", ha="left", va="bottom",
                    fontsize=9, color=c["graphite"])
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([f"{m}\n{sum(1 for r in rows if r['model'] == m)} frames, "
                            f"{_pass_rate(rows, m):.0%} pass" for m in models])
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # The title is a claim about the experiment, so it is checked rather than
    # asserted: a figure that says "only the model changed" over two arms that
    # drew different seeds is the most persuasive way to be wrong here.
    fig.suptitle("Same prompt, same seeds, same tier. Only the model changed."
                 if shared_seeds(rows) else
                 "Same prompt and tier, DIFFERENT seeds per arm: not a controlled "
                 "comparison.",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    # Said once, under both panels, because "hollow" means nothing unless the
    # figure explains that a frame can clear the bar and still be refused.
    from matplotlib.lines import Line2D
    ink = c["graphite"]
    axes[0].legend(
        handles=[Line2D([], [], marker="o", ls="", markerfacecolor=ink,
                        markeredgecolor=ink, markersize=6, label="passed the gate"),
                 Line2D([], [], marker="o", ls="", markerfacecolor="none",
                        markeredgecolor=ink, markersize=6,
                        label="failed a rule, whatever its score")],
        loc="upper center", bbox_to_anchor=(1.09, -0.12), ncol=2, frameon=False,
        fontsize=9, labelcolor=c["ink"])
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    if caption:
        fig.text(0.01, -0.02, caption, ha="left", va="top", fontsize=9,
                 color=c["graphite"], wrap=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


# --------------------------------------------------------------------------
# cli


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m runs.drift")
    p.add_argument("--models", nargs="+", default=["krea2", "flux2"])
    p.add_argument("--n", type=int, default=48, help="frames per model")
    p.add_argument("--prompt", default="hero-ground")
    p.add_argument("--tier", default="turbo", choices=("turbo", "raw"))
    p.add_argument("--seed-start", type=int, default=SEED_START)
    p.add_argument("--prompt-version", type=int, default=None,
                   help="refuse to run unless brand/prompts/<prompt>.md is this version")
    p.add_argument("--root", default=DRIFT_DIR, help="where the arms' frames live")
    p.add_argument("--out", default=OUT_DIR)
    p.add_argument("--score-only", action="store_true",
                   help="skip generation, gate and plot whatever is on disk")
    p.add_argument("--caveat", help="a line printed at the top of the scorecard")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    from pipeline import gate

    if not a.score_only:
        fill_arms(a.models, a.n, a.prompt, a.tier, a.root, a.seed_start,
                  prompt_version=a.prompt_version, dry_run=a.dry_run)
        if a.dry_run:
            print("\ndry run: nothing generated, nothing scored")
            return 0

    cfg = gate.load_config()
    reference = reference_paths()
    if not reference:
        print(f"ERROR: no reference frames match {REFERENCE_GLOB}", file=sys.stderr)
        return 2
    print(f"\nnovelty reference: {len(reference)} accepted grounds", flush=True)

    rows = []
    for model in a.models:
        print(f"\n== gating {model}", flush=True)
        rows += gate_arm(model, a.root, a.prompt, a.tier, reference, cfg)
    if not rows:
        print(f"ERROR: no frames found under {os.path.relpath(a.root, ROOT)}; "
              "generate first, or point --root somewhere with frames", file=sys.stderr)
        return 2

    if not shared_seeds(rows):
        print("\nWARNING: the arms did not draw the same seeds, so the difference "
              "between them is not the model alone. Every artifact this run writes "
              "says so.", file=sys.stderr)
    results = write_results(rows, os.path.join(a.out, "results.jsonl"))
    led = ledger_rows(a.models, sorted({r["seed"] for r in rows}), a.tier)
    card = os.path.join(a.out, "scorecard.md")
    os.makedirs(a.out, exist_ok=True)
    with open(card, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(scorecard(rows, cfg, led, a.caveat))
    png = figure(rows, cfg, os.path.join(a.out, "plot.png"),
                 caption=a.caveat or "")

    for path in (results, card, png):
        print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

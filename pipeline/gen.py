"""Generate a brand ground from a versioned prompt template.

One prompt spec in, one PNG under surfaces/ and one ledger row out. The
backend is a local ComfyUI server; the models are Krea-2 in two tiers and
Flux.2, which is enough to hold a prompt and a seed still while the model
changes underneath them.

Run it:

    python -m pipeline.gen --prompt hero-ground --seed 1
    python -m pipeline.gen --prompt hero-ground --seed 1 --dry-run
    python -m pipeline.gen --prompt hero-ground --seed 1 --model flux2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from pipeline import ledger, prompts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "surfaces", "_scratch")
DEFAULT_SERVER = "http://127.0.0.1:8188"

# Weights are named, not vendored. The gate scores what comes out, so the
# ledger has to be able to say which checkpoint produced a frame even when
# that checkpoint lives on one machine's disk and nowhere else.
MODELS = {
    "krea2": {
        "turbo": {"unet": "krea2_turbo_fp8_scaled.safetensors", "steps": 8, "cfg": 1.0},
        "raw": {"unet": "krea2_raw_fp8_scaled.safetensors", "steps": 52, "cfg": 3.5},
        "clip": "qwen3vl_4b_fp8_scaled.safetensors",
        "clip_type": "krea2",
        "vae": "qwen_image_vae.safetensors",
    },
    "flux2": {
        "turbo": {"unet": "flux2_dev_fp8mixed.safetensors", "steps": 8, "cfg": 4,
                  "lora": "Flux2TurboComfyv2.safetensors"},
        "raw": {"unet": "flux2_dev_fp8mixed.safetensors", "steps": 20, "cfg": 4},
        "clip": "mistral_3_small_flux2_fp8.safetensors",
        "clip_type": "flux2",
        "vae": "flux2-vae.safetensors",
    },
}


class GenerationError(RuntimeError):
    """The backend refused or failed to produce a frame."""


# --------------------------------------------------------------------------
# graphs


def build_krea2(spec, *, seed, width, height, tier, prefix, negative=None):
    """Krea-2 fp8, two tiers: Turbo at 8 steps cfg 1.0 for hunting, Raw at 52
    steps cfg 3.5 for finals. Both euler/simple with no shift node, because
    Krea-2's 1.15 shift is baked into the model class rather than wired.

    The negative is chosen by the effective cfg, not by a flag. At cfg 1.0
    there is no classifier-free guidance, so ConditioningZeroOut is never
    evaluated and costs nothing. Above 1.0 it becomes live, and a zeroed
    tensor is far enough out of distribution that guidance blows up and the
    frame returns as chroma speckle. Any cfg over 1 therefore gets a real
    text encode, even of an empty string.
    """
    m = MODELS["krea2"]
    t = m[tier]
    cfg = t["cfg"]
    g = {
        "u": {"class_type": "UNETLoader",
              "inputs": {"unet_name": t["unet"], "weight_dtype": "default"}},
        "c": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": m["clip"], "type": m["clip_type"],
                         "device": "default"}},
        "v": {"class_type": "VAELoader", "inputs": {"vae_name": m["vae"]}},
        "pos": {"class_type": "CLIPTextEncode",
                "inputs": {"clip": ["c", 0], "text": spec.text}},
    }
    if cfg > 1.0 or negative is not None:
        g["neg"] = {"class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["c", 0], "text": negative or ""}}
    else:
        g["neg"] = {"class_type": "ConditioningZeroOut",
                    "inputs": {"conditioning": ["pos", 0]}}
    g["lat"] = {"class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}}
    g["ks"] = {"class_type": "KSampler",
               "inputs": {"model": ["u", 0], "seed": seed, "steps": t["steps"],
                          "cfg": cfg, "sampler_name": "euler",
                          "scheduler": "simple", "positive": ["pos", 0],
                          "negative": ["neg", 0], "latent_image": ["lat", 0],
                          "denoise": 1.0}}
    g["dec"] = {"class_type": "VAEDecode",
                "inputs": {"samples": ["ks", 0], "vae": ["v", 0]}}
    g["save"] = {"class_type": "SaveImage",
                 "inputs": {"images": ["dec", 0], "filename_prefix": prefix}}
    return g, {"steps": t["steps"], "cfg": cfg, "lora": []}


def build_flux2(spec, *, seed, width, height, tier, prefix, negative=None):
    """Flux.2 dev fp8. Turbo wears the 8-step LoRA; raw drops it for 20 steps
    of the base model. Flux takes its guidance through FluxGuidance rather
    than a sampler cfg, and has no negative conditioning at all, so the
    negative argument is accepted and ignored for parity with krea2."""
    m = MODELS["flux2"]
    t = m[tier]
    g = {
        "u": {"class_type": "UNETLoader",
              "inputs": {"unet_name": t["unet"], "weight_dtype": "default"}},
        "c": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": m["clip"], "type": m["clip_type"],
                         "device": "default"}},
        "v": {"class_type": "VAELoader", "inputs": {"vae_name": m["vae"]}},
        "pos": {"class_type": "CLIPTextEncode",
                "inputs": {"clip": ["c", 0], "text": spec.text}},
        "guide": {"class_type": "FluxGuidance",
                  "inputs": {"conditioning": ["pos", 0], "guidance": t["cfg"]}},
        "samp": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "lat": {"class_type": "EmptyFlux2LatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}},
        "sched": {"class_type": "Flux2Scheduler",
                  "inputs": {"steps": t["steps"], "width": width, "height": height}},
    }
    model_src = ["u", 0]
    loras = []
    if "lora" in t:
        g["lora"] = {"class_type": "LoraLoaderModelOnly",
                     "inputs": {"model": model_src, "lora_name": t["lora"],
                                "strength_model": 1.0}}
        model_src = ["lora", 0]
        loras.append(t["lora"])
    g["guider"] = {"class_type": "BasicGuider",
                   "inputs": {"model": model_src, "conditioning": ["guide", 0]}}
    g["sca"] = {"class_type": "SamplerCustomAdvanced",
                "inputs": {"noise": ["noise", 0], "guider": ["guider", 0],
                           "sampler": ["samp", 0], "sigmas": ["sched", 0],
                           "latent_image": ["lat", 0]}}
    g["dec"] = {"class_type": "VAEDecode",
                "inputs": {"samples": ["sca", 0], "vae": ["v", 0]}}
    g["save"] = {"class_type": "SaveImage",
                 "inputs": {"images": ["dec", 0], "filename_prefix": prefix}}
    return g, {"steps": t["steps"], "cfg": t["cfg"], "lora": loras}


BUILDERS = {"krea2": build_krea2, "flux2": build_flux2}


# --------------------------------------------------------------------------
# backend


class ComfyBackend:
    """A local ComfyUI server, spoken to over its HTTP API.

    Frames are pulled back over /view and written under this repo rather than
    left in the server's own output tree. That is the main thing that changed
    in making this a module: the generator no longer assumes it is running
    from inside the ComfyUI checkout, so the pipeline and the weights can
    live in different places, and the path in a ledger row is a path that
    exists in this repo.
    """

    def __init__(self, server: str | None = None, poll_s: float = 2.0):
        self.server = (server or os.environ.get("COMFY_SERVER")
                       or DEFAULT_SERVER).rstrip("/")
        self.poll_s = poll_s

    def _api(self, path, data=None, timeout=30):
        req = urllib.request.Request(self.server + path)
        if data is not None:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def _fetch(self, filename, subfolder, dest_dir):
        q = urllib.parse.urlencode(
            {"filename": filename, "subfolder": subfolder, "type": "output"})
        with urllib.request.urlopen(f"{self.server}/view?{q}", timeout=120) as r:
            blob = r.read()
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, filename)
        with open(dest, "wb") as fh:
            fh.write(blob)
        return dest

    def generate(self, graph, *, dest_dir, timeout=1800):
        """Queue a graph, wait for it, return the local paths written."""
        try:
            resp = self._api("/prompt", {"prompt": graph})
        except urllib.error.HTTPError as e:
            raise GenerationError(
                f"prompt rejected by server: {e.read().decode(errors='replace')}") from None
        except urllib.error.URLError as e:
            raise GenerationError(
                f"no ComfyUI server at {self.server} ({e.reason})") from None

        pid = resp["prompt_id"]
        t0 = time.time()
        while True:
            time.sleep(self.poll_s)
            entry = self._api(f"/history/{pid}").get(pid)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    msgs = [m for m in status.get("messages", [])
                            if m[0] == "execution_error"]
                    raise GenerationError(
                        json.dumps(msgs or status, default=str)[:2000])
                paths = []
                for node_out in entry.get("outputs", {}).values():
                    for img in node_out.get("images", []):
                        paths.append(self._fetch(
                            img["filename"], img.get("subfolder", ""), dest_dir))
                if not paths:
                    raise GenerationError("run completed but produced no images")
                return paths
            if time.time() - t0 > timeout:
                raise GenerationError(
                    f"timed out after {timeout}s; the job may still be running "
                    f"on {self.server}")


# --------------------------------------------------------------------------
# the run


def _repo_relative(path: str) -> str:
    """Repo-relative path for the ledger, or the bare filename if the output
    landed outside the repo.

    A plain relpath to somewhere outside ROOT produces `../../../../../tmp/...`
    carrying the machine's username, which is meaningless to any other reader
    and is a leak in a file that ships when the repo goes public. Outputs land
    inside the repo in real use; outside it only ever happens under test.
    """
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return os.path.basename(path) if rel.startswith("../") else rel


def generate(name, *, seed, model=None, tier=None, width=None, height=None,
             dest_dir=None, prompt_dir=None, ledger_path=None,
             backend=None, timeout=1800):
    """Generate one frame and write exactly one ledger row.

    Returns (paths, record). Both are returned even when the run fails: paths
    is empty and record carries `error`, so a caller batching a surface can
    keep going and still have the failure on disk.
    """
    spec = prompts.load(name, prompt_dir)
    model = model or spec.model
    tier = tier or spec.tier
    if model not in BUILDERS:
        raise ValueError(f"unknown model {model!r} (have: {', '.join(sorted(BUILDERS))})")
    if tier not in ("turbo", "raw"):
        raise ValueError(f"unknown tier {tier!r} (have: turbo, raw)")

    width = width or int(spec.params.get("width", 1664))
    height = height or int(spec.params.get("height", 944))
    dest_dir = dest_dir or SCRATCH
    run_id = ledger.new_run_id()
    prefix = f"{spec.name}_{tier}_{seed}_{run_id}"

    graph, meta = BUILDERS[model](
        spec, seed=seed, width=width, height=height, tier=tier,
        prefix=prefix, negative=spec.params.get("negative"))

    params = {"width": width, "height": height, "steps": meta["steps"],
              "cfg": meta["cfg"], "sampler": "euler", "scheduler": "simple"}

    backend = backend or ComfyBackend()
    t0 = time.time()
    paths, error = [], None
    try:
        paths = backend.generate(graph, dest_dir=dest_dir, timeout=timeout)
    except GenerationError as e:
        error = str(e)
    latency = time.time() - t0

    record = ledger.row(
        run_id=run_id, model=model, tier=tier, prompt_id=spec.prompt_id,
        prompt_text=spec.text, params=params, seed=seed, lora=meta["lora"],
        output_path=_repo_relative(paths[0]) if paths else None,
        latency_s=latency, error=error)
    ledger.append(record, ledger_path)
    return paths, record


def describe(name, *, seed, model=None, tier=None, width=None, height=None,
             prompt_dir=None):
    """What a run would send, without sending it and without a ledger row."""
    spec = prompts.load(name, prompt_dir)
    model = model or spec.model
    tier = tier or spec.tier
    width = width or int(spec.params.get("width", 1664))
    height = height or int(spec.params.get("height", 944))
    graph, meta = BUILDERS[model](
        spec, seed=seed, width=width, height=height, tier=tier,
        prefix=f"{spec.name}_{tier}_{seed}_dryrun",
        negative=spec.params.get("negative"))
    return {"prompt_id": spec.prompt_id, "model": model, "tier": tier,
            "seed": seed, "steps": meta["steps"], "cfg": meta["cfg"],
            "lora": meta["lora"], "width": width, "height": height,
            "prompt_text": spec.text, "graph": graph}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m pipeline.gen",
        description="Generate a brand ground from a versioned prompt template.")
    p.add_argument("--prompt", required=True,
                   help=f"template name under brand/prompts/ ({', '.join(prompts.available()) or 'none found'})")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--model", choices=sorted(BUILDERS),
                   help="override the template's model")
    p.add_argument("--tier", choices=("turbo", "raw"),
                   help="turbo hunts, raw finals")
    p.add_argument("-W", "--width", type=int)
    p.add_argument("-H", "--height", type=int)
    p.add_argument("--out", default=SCRATCH, help="where the PNG lands")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--dry-run", action="store_true",
                   help="print the request and exit, writing no ledger row")
    a = p.parse_args(argv)

    try:
        if a.dry_run:
            print(json.dumps(
                describe(a.prompt, seed=a.seed, model=a.model, tier=a.tier,
                         width=a.width, height=a.height),
                indent=2, ensure_ascii=False))
            return 0

        paths, record = generate(
            a.prompt, seed=a.seed, model=a.model, tier=a.tier, width=a.width,
            height=a.height, dest_dir=a.out, timeout=a.timeout)
    except (prompts.PromptError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if record["error"]:
        print(f"FAILED in {record['latency_s']}s: {record['error']}", file=sys.stderr)
        print(f"ledger row {record['run_id']} written with the error", file=sys.stderr)
        return 1
    print(f"{record['prompt_id']} {record['model']}/{record['tier']} "
          f"seed {record['seed']} in {record['latency_s']}s")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

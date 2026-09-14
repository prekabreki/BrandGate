"""Generation tests run with no ComfyUI server and no GPU: the backend is
stubbed, so what is under test is the graph, the row and the seams between
them, which is where the bugs actually live."""
import json
import os

import pytest

from pipeline import gen, ledger, prompts

BODY = """---
version: 2
model: krea2
tier: turbo
width: 64
height: 64
---
a soft indigo wash over paper
"""


class StubBackend:
    """Stands in for a local ComfyUI. Records the graph it was handed and
    writes a real file, so path handling is exercised rather than mocked."""

    def __init__(self, fail=None, filename="out_00001_.png"):
        self.graphs = []
        self.fail = fail
        self.filename = filename

    def generate(self, graph, *, dest_dir, timeout=1800):
        self.graphs.append(graph)
        if self.fail:
            raise gen.GenerationError(self.fail)
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, self.filename)
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        return [path]


@pytest.fixture
def env(tmp_path):
    (tmp_path / "hero-ground.md").write_text(BODY, encoding="utf-8")
    return {
        "prompt_dir": str(tmp_path),
        "dest_dir": str(tmp_path / "out"),
        "ledger_path": str(tmp_path / "runs" / "ledger.jsonl"),
    }


def _run(env, backend, **over):
    kw = dict(seed=1, backend=backend, **env)
    kw.update(over)
    return gen.generate("hero-ground", **kw)


# -- the row ---------------------------------------------------------------


def test_one_run_writes_exactly_one_row(env):
    _run(env, StubBackend())
    assert len(ledger.read(env["ledger_path"])) == 1


def test_row_has_the_full_field_set(env):
    _, record = _run(env, StubBackend())
    assert tuple(record) == ledger.FIELDS
    assert record["prompt_id"] == "hero-ground@2"
    assert record["prompt_text"] == "a soft indigo wash over paper"
    assert record["seed"] == 1
    assert record["model"] == "krea2"
    assert record["tier"] == "turbo"
    assert record["error"] is None
    assert record["latency_s"] is not None


def test_output_path_is_relative_to_the_repo(env):
    paths, record = _run(env, StubBackend())
    assert os.path.isabs(paths[0])
    # A ledger read on the other machine must not trip over an absolute path
    # from this one.
    assert not os.path.isabs(record["output_path"])
    assert "\\" not in record["output_path"]


def test_a_failed_run_still_writes_one_row(env):
    paths, record = _run(env, StubBackend(fail="server refused"))
    assert paths == []
    assert record["error"] == "server refused"
    assert record["output_path"] is None
    # The failure is on disk, not just in the caller's hands: what the model
    # refused is most of what a scorecard is made of.
    rows = ledger.read(env["ledger_path"])
    assert len(rows) == 1 and rows[0]["error"] == "server refused"


def test_run_ids_are_unique_across_runs(env):
    b = StubBackend()
    _run(env, b)
    _run(env, b)
    rows = ledger.read(env["ledger_path"])
    assert len({r["run_id"] for r in rows}) == 2


# -- the model swap, which is what #9's drift run rides on ------------------


def test_model_swap_changes_only_the_model_and_its_own_machinery(env):
    _, krea = _run(env, StubBackend(), model="krea2")
    _, flux = _run(env, StubBackend(), model="flux2")

    assert krea["model"] == "krea2" and flux["model"] == "flux2"
    # Everything that defines the ask holds still. If any of these moved, a
    # drift plot would be measuring the harness rather than the model.
    for field in ("tier", "prompt_id", "prompt_text", "seed"):
        assert krea[field] == flux[field], field
    for key in ("width", "height"):
        assert krea["params"][key] == flux["params"][key], key


def test_the_two_models_are_genuinely_different_graphs(env):
    # Guards the test above from passing because both builders return the same
    # thing: the swap has to actually swap something.
    kb, fb = StubBackend(), StubBackend()
    _run(env, kb, model="krea2")
    _run(env, fb, model="flux2")
    assert kb.graphs[0] != fb.graphs[0]
    assert kb.graphs[0]["u"]["inputs"]["unet_name"] != fb.graphs[0]["u"]["inputs"]["unet_name"]


def test_tier_selects_steps_and_cfg(env):
    _, turbo = _run(env, StubBackend(), tier="turbo")
    _, raw = _run(env, StubBackend(), tier="raw")
    assert turbo["params"]["steps"] == 8
    assert raw["params"]["steps"] == 52
    assert raw["params"]["cfg"] > turbo["params"]["cfg"]


def test_flux_turbo_records_its_lora_and_raw_does_not(env):
    _, turbo = _run(env, StubBackend(), model="flux2", tier="turbo")
    _, raw = _run(env, StubBackend(), model="flux2", tier="raw")
    assert turbo["lora"] == ["Flux2TurboComfyv2.safetensors"]
    assert raw["lora"] == []


def test_unknown_model_or_tier_is_refused(env):
    with pytest.raises(ValueError, match="unknown model"):
        _run(env, StubBackend(), model="midjourney")
    with pytest.raises(ValueError, match="unknown tier"):
        _run(env, StubBackend(), tier="deluxe")


# -- the graphs ------------------------------------------------------------


def test_krea_turbo_zeroes_the_negative_and_raw_encodes_one(env):
    b = StubBackend()
    _run(env, b, tier="turbo")
    _run(env, b, tier="raw")
    # At cfg 1.0 there is no CFG, so a zeroed conditioning is never evaluated.
    assert b.graphs[0]["neg"]["class_type"] == "ConditioningZeroOut"
    # Above cfg 1.0 it is live, and a zeroed tensor there returns chroma speckle.
    assert b.graphs[1]["neg"]["class_type"] == "CLIPTextEncode"


def test_the_seed_reaches_the_sampler(env):
    kb, fb = StubBackend(), StubBackend()
    _run(env, kb, model="krea2", seed=4242)
    _run(env, fb, model="flux2", seed=4242)
    assert kb.graphs[0]["ks"]["inputs"]["seed"] == 4242
    assert fb.graphs[0]["noise"]["inputs"]["noise_seed"] == 4242


def test_the_prompt_text_reaches_the_encoder(env):
    b = StubBackend()
    _run(env, b)
    assert b.graphs[0]["pos"]["inputs"]["text"] == "a soft indigo wash over paper"


def test_dimensions_come_from_the_template_and_are_overridable(env):
    b = StubBackend()
    _run(env, b)
    assert b.graphs[0]["lat"]["inputs"]["width"] == 64
    _run(env, b, width=128, height=256)
    assert b.graphs[1]["lat"]["inputs"]["width"] == 128
    assert b.graphs[1]["lat"]["inputs"]["height"] == 256


def test_every_graph_ends_in_a_save(env):
    for model in gen.BUILDERS:
        b = StubBackend()
        _run(env, b, model=model)
        assert b.graphs[0]["save"]["class_type"] == "SaveImage"


# -- dry run ---------------------------------------------------------------


def test_dry_run_writes_no_row_and_no_file(tmp_path, capsys, monkeypatch):
    # main() uses the repo's real prompt and ledger paths, so watch those: an
    # assertion against a tmp ledger main never touches would pass whatever
    # --dry-run did.
    monkeypatch.setattr(ledger, "LEDGER", str(tmp_path / "ledger.jsonl"))
    scratch = tmp_path / "out"
    rc = gen.main(["--prompt", "hero-ground", "--seed", "1", "--dry-run",
                   "--out", str(scratch)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["seed"] == 1
    assert "graph" in out
    assert ledger.read() == []
    assert not scratch.exists()


def test_the_dry_run_guard_can_fail(tmp_path, capsys, monkeypatch):
    # Proves the assertion above is live: the same watch catches a real run.
    monkeypatch.setattr(ledger, "LEDGER", str(tmp_path / "ledger.jsonl"))
    gen.generate("hero-ground", seed=1, backend=StubBackend(),
                 dest_dir=str(tmp_path / "out"))
    assert len(ledger.read()) == 1


def test_describe_reports_what_would_be_sent(env):
    d = gen.describe("hero-ground", seed=7, prompt_dir=env["prompt_dir"])
    assert d["prompt_id"] == "hero-ground@2"
    assert d["steps"] == 8
    assert d["graph"]["ks"]["inputs"]["seed"] == 7


# -- cli -------------------------------------------------------------------


def test_a_bad_prompt_name_exits_two_not_a_traceback(capsys):
    assert gen.main(["--prompt", "no-such-template", "--seed", "1", "--dry-run"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_backend_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("COMFY_SERVER", raising=False)
    assert gen.ComfyBackend().server == "http://127.0.0.1:8188"
    monkeypatch.setenv("COMFY_SERVER", "http://192.168.1.9:8188/")
    assert gen.ComfyBackend().server == "http://192.168.1.9:8188"

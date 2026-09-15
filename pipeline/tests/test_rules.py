"""rules.json is generated from prose, so the parse is the thing to pin: if it
drifts, every score moves and no check looks wrong."""
import json

import pytest

from pipeline import rules

MD = """# Handsel

## Colour

- Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.
- Indigo `#4B3BE8` is the one flat accent: links, the primary button, a chip border. Magenta is never a flat accent.
- Text is ink `#111114` on light grounds and white on night.

## Mark

- The mark is never rotated, mirrored, outlined, or shown with a drop shadow.
- Minimum width is 96 px on screen.

## Tone

- Plain sentences, sentence case, present tense.
"""


@pytest.fixture
def md(tmp_path):
    p = tmp_path / "rules.md"
    p.write_text(MD, encoding="utf-8")
    return str(p)


def _by_id(parsed):
    return {r.id: r for r in parsed}


def test_every_bullet_becomes_a_rule(md):
    assert len(rules.parse(md)) == 6


def test_ids_are_section_scoped_and_stable(md):
    ids = [r.id for r in rules.parse(md)]
    assert ids == ["colour.01", "colour.02", "colour.03",
                   "mark.01", "mark.02", "tone.01"]
    assert [r.id for r in rules.parse(md)] == ids


def test_each_rule_keeps_the_prose_it_came_from(md):
    r = _by_id(rules.parse(md))["mark.01"]
    assert r.prose.startswith("The mark is never rotated")


def test_an_uncheckable_rule_is_manual_not_dropped(md):
    # The gap between what a designer can say and what a machine can score has
    # to stay visible in the artifact.
    assert _by_id(rules.parse(md))["tone.01"].check == "manual"


def test_ground_rule_binds_to_palette_with_its_own_hexes(md):
    r = _by_id(rules.parse(md))["colour.01"]
    assert r.check == "palette"
    assert r.params["role"] == "ground"
    assert r.params["allow"] == ["#FAFAF8", "#ECEAF6", "#0D0B18"]
    assert r.params["forbid_hex"] == []


def test_polarity_is_resolved_per_sentence_not_per_bullet(md):
    # "Indigo is the one flat accent. Magenta is never a flat accent." reading
    # the bullet's polarity as a whole made the gate treat INDIGO, the brand's
    # only accent, as the forbidden colour and fail every correct surface.
    r = _by_id(rules.parse(md))["colour.02"]
    assert r.params["allow"] == ["#4B3BE8"]
    assert "#4B3BE8" not in r.params["forbid_hex"]


def test_a_colour_named_only_by_word_is_resolved_from_tokens(md):
    # "Magenta is never a flat accent" carries no hex; a hex-only parser drops
    # the prohibition in silence.
    r = _by_id(rules.parse(md))["colour.02"]
    assert r.params["forbid_hex"] == ["#B44C9E"]


def test_text_rules_bind_to_contrast_not_palette(md):
    # A rule about text also names colours, so palette would claim it on the
    # strength of its hexes and the contrast check would bind to nothing.
    assert _by_id(rules.parse(md))["colour.03"].check == "contrast"


def test_mark_transform_rule_lists_what_it_forbids(md):
    r = _by_id(rules.parse(md))["mark.01"]
    assert r.check == "band"
    assert set(r.params["forbid_transforms"]) == {"rotated", "mirrored",
                                                  "outlined", "drop shadow"}


def test_editing_the_prose_changes_the_parse(md, tmp_path):
    before = _by_id(rules.parse(md))["colour.01"].params["allow"]
    p = tmp_path / "rules.md"
    p.write_text(MD.replace("#FAFAF8", "#00FF00"), encoding="utf-8")
    after = _by_id(rules.parse(md))["colour.01"].params["allow"]
    assert before != after
    assert "#00FF00" in after


def test_build_writes_counts_and_a_parser_fingerprint(md, tmp_path):
    dest = str(tmp_path / "rules.json")
    doc = rules.build(md, dest)
    assert doc["counts"]["total"] == 6
    assert doc["counts"]["checked"] + doc["counts"]["manual"] == 6
    assert len(doc["parser"]) == 16
    assert json.load(open(dest, encoding="utf-8"))["parser"] == doc["parser"]


def test_a_stale_parse_is_rebuilt_when_the_parser_changes(tmp_path, monkeypatch):
    # rules.json derives from the prose AND the parser. Invalidating on the
    # prose alone let a corrected parser go on serving the previous parse, and
    # the gate scored against it.
    dest = str(tmp_path / "rules.json")
    rules.build(dest=dest)
    stale = json.load(open(dest, encoding="utf-8"))
    stale["parser"] = "0" * 16
    stale["rules"] = []
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(stale, fh)
    assert rules.load(dest)["rules"], "a stale parse was served instead of rebuilt"


def test_the_shipped_rules_parse_and_bind_all_five_checks():
    doc = rules.build()
    bound = {r["check"] for r in doc["rules"]} - {"manual"}
    assert bound == {"palette", "band", "contrast", "motif", "wash"}
    assert doc["counts"]["manual"] > 0, "every rule bound; the parse is too eager"


def test_the_softened_ground_rule_binds_to_wash_with_its_stops():
    doc = rules.build()
    r = next(r for r in doc["rules"] if r["id"] == "gradient.03")
    assert r["check"] == "wash"
    stops = {c.upper() for c in r["params"]["stops"]}
    assert {"#4B3BE8", "#B44C9E", "#D9628A"} <= stops, stops
    others = [x for x in doc["rules"] if x["section"] == "gradient" and x["id"] != "gradient.03"]
    assert all(x["check"] == "manual" for x in others), [x["id"] for x in others]

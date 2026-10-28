"""Tests for loading, validating and linting content packs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from anachronism.content.issues import ContentError
from anachronism.content.loader import PACKS_DIR, Content, load_content
from anachronism.content.schema import Stage
from anachronism.tools.lint_content import main as lint_main


@pytest.fixture
def packs(tmp_path: Path) -> Path:
    """A private copy of the real packs that a test may break."""
    root = tmp_path / "packs"
    shutil.copytree(PACKS_DIR, root)
    return root


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def problems(root: Path) -> list[str]:
    with pytest.raises(ContentError) as error:
        load_content(root=root)
    return [str(issue) for issue in error.value.issues]


def test_real_packs_load_cleanly() -> None:
    content = load_content()
    assert isinstance(content, Content)
    assert [pack.id for pack in content.packs] == ["core", "europe", "testworld"]
    assert content.scenarios["bronze_dawn"].player_civ == "veyra"
    assert content.techs["iron_working"].prerequisites == ("bronze_working", "charcoal_burning")
    assert content.scenarios["bronze_dawn"].civs["veyra"].techs["writing"] is Stage.ADOPTED


def test_loading_only_core_skips_the_test_world() -> None:
    content = load_content(["core"])
    assert [pack.id for pack in content.packs] == ["core"]
    assert not content.scenarios


def test_digest_is_stable_and_tracks_changes(packs: Path) -> None:
    first = load_content(root=packs).digest
    assert load_content(root=packs).digest == first
    edit(packs / "core" / "techs" / "craft.yaml", "Sealed jars", "Sealed pots")
    assert load_content(root=packs).digest != first


def test_typo_in_a_field_name_is_reported_with_the_node_id(packs: Path) -> None:
    edit(
        packs / "core" / "techs" / "craft.yaml", "prerequisites: [charcoal_burning]", "prereqs: []"
    )
    [problem] = problems(packs)
    assert "core/techs/craft.yaml" in problem
    assert "(piston_bellows)" in problem
    assert "prereqs" in problem


def test_unknown_prerequisite_and_material(packs: Path) -> None:
    edit(packs / "core" / "techs" / "craft.yaml", "[wheel, masonry]", "[wheel, masonary]")
    edit(packs / "core" / "techs" / "craft.yaml", "materials: [timber]}", "materials: [lumber]}")
    found = problems(packs)
    assert any("unknown prerequisite 'masonary'" in p for p in found)
    assert any("unknown material 'lumber'" in p for p in found)


def test_prerequisite_cycle(packs: Path) -> None:
    edit(
        packs / "core" / "techs" / "knowledge.yaml",
        "complexity: 2\n    effects: [{type: knowledge_gain, bp: 1000}",
        "complexity: 2\n    prerequisites: [paper]\n    effects: [{type: knowledge_gain, bp: 1000}",
    )
    cycles = [p for p in problems(packs) if "prerequisite cycle:" in p]
    assert len(cycles) == 1
    assert "paper -> writing" in cycles[0] or "writing -> paper" in cycles[0]


def test_asymmetric_neighbours(packs: Path) -> None:
    edit(
        packs / "testworld" / "provinces.yaml",
        "neighbours: [veyra_marshes, veyra_delta, veyra_coast]",
        "neighbours: [veyra_marshes, veyra_delta]",
    )
    assert any("'southern_isles' does not list it as a neighbour" in p for p in problems(packs))


def test_duplicate_yaml_key(packs: Path) -> None:
    edit(packs / "core" / "resources.yaml", "resources:\n", "resources:\nresources:\n")
    assert any("duplicate key 'resources'" in p for p in problems(packs))


def test_duplicate_id_across_files(packs: Path) -> None:
    edit(packs / "core" / "techs" / "health.yaml", "id: herbal_medicine", "id: writing")
    assert any("duplicate id, first in" in p and "(writing)" in p for p in problems(packs))


def test_wrong_schema_version(packs: Path) -> None:
    edit(packs / "core" / "terrain.yaml", "schema_version: 1", "schema_version: 2")
    assert any("expected schema_version 1, found 2" in p for p in problems(packs))


def test_invalid_effect_shape(packs: Path) -> None:
    edit(
        packs / "core" / "techs" / "metallurgy.yaml",
        "{type: unlocks_resource, target: iron}",
        "{type: unlocks_resource, bp: 100}",
    )
    assert any("needs a target" in p for p in problems(packs))


def test_missing_effect_caps(packs: Path) -> None:
    edit(packs / "core" / "effects.yaml", "  secrecy:", "  # secrecy:")
    assert any("missing caps for secrecy" in p for p in problems(packs))


def test_scenario_consistency(packs: Path) -> None:
    scenario = packs / "testworld" / "scenarios" / "bronze_dawn.yaml"
    edit(scenario, "capital: kessrin_highfort", "capital: veyra_heartland")
    edit(scenario, "kessrin_lake_basin: 52000", "veyra_delta: 52000")
    edit(
        scenario,
        "ore_prospecting: adopted",
        "ore_prospecting: adopted\n          iron_plough: adopted",
    )
    found = problems(packs)
    assert any("kessrin: capital 'veyra_heartland' is not one of its provinces" in p for p in found)
    assert any("province 'veyra_delta' is held by veyra and kessrin" in p for p in found)
    assert any("'iron_plough' is adopted but its prerequisite 'iron_working'" in p for p in found)


def test_unknown_dependency_pack(packs: Path) -> None:
    edit(packs / "testworld" / "pack.yaml", "depends_on: [core]", "depends_on: [core, atlantis]")
    assert any("unknown pack 'atlantis'" in p for p in problems(packs))


def test_all_problems_are_reported_together(packs: Path) -> None:
    edit(packs / "core" / "terrain.yaml", "capacity: 120000", "capacity: -5")
    edit(packs / "testworld" / "civs.yaml", 'colour: "#b5523b"', 'colour: "red"')
    found = problems(packs)
    assert any("core/terrain.yaml" in p for p in found)
    assert any("testworld/civs.yaml" in p for p in found)


def test_lint_cli_reports_success_and_failure(
    packs: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert lint_main([]) == 0
    assert "OK: core v1, europe v1, testworld v1" in capsys.readouterr().out
    edit(packs / "core" / "eras.yaml", "ends: 500}", "ends: -600}")
    assert lint_main(["--root", str(packs)]) == 1
    output = capsys.readouterr().out
    assert "1 problem(s) found" in output
    assert "era end years must strictly increase" in output


def test_lint_review_lists_what_needs_a_source(capsys: pytest.CaptureFixture[str]) -> None:
    assert lint_main(["--review"]) == 0
    output = capsys.readouterr().out
    assert "advancements:" in output
    assert "without a source" in output


def test_coastal_provinces_must_touch_a_sea(packs: Path) -> None:
    edit(
        packs / "testworld" / "seas.yaml",
        "neighbours: [southern_isles]\n",
        "neighbours: [southern_isles, veyra_heartland]\n",
    )
    assert any("(veyra_heartland): touches a sea but is not coastal" in p for p in problems(packs))


def test_scenario_provinces_need_map_positions(packs: Path) -> None:
    edit(packs / "testworld" / "provinces.yaml", "    position: [300, 340]\n", "")
    assert any("province 'veyra_heartland' has no map position" in p for p in problems(packs))


def test_real_map_provinces_need_a_latlon(packs: Path) -> None:
    edit(packs / "europe" / "provinces_ancient.yaml", "    latlon: [36.85, 10.2]\n", "")
    assert any(
        "province 'car_carthage' has no latlon for the europe map" in p for p in problems(packs)
    )


def test_latlon_must_be_on_earth(packs: Path) -> None:
    edit(
        packs / "europe" / "provinces_ancient.yaml",
        "latlon: [36.85, 10.2]",
        "latlon: [125.0, 36.85]",
    )
    assert any("is not a place on Earth" in p for p in problems(packs))


def test_sea_zone_needs_a_place(packs: Path) -> None:
    edit(packs / "europe" / "seas.yaml", " latlon: [40.0, 12.0],", "")
    assert any("a sea zone needs a position or a latlon" in p for p in problems(packs))


def test_emblem_font_has_every_emblem_character() -> None:
    font_characters = (PACKS_DIR.parents[3] / "client" / "fonts" / "emblems.txt").read_text(
        encoding="utf-8"
    )
    for civ in load_content().civs.values():
        missing = {ch for ch in civ.emblem if not ch.isascii() and ch not in font_characters}
        assert not missing, f"{civ.id}: run scripts/build_emblem_font.py (missing {missing})"

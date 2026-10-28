"""Tests for building a new game and for saving and loading it."""

from __future__ import annotations

import dataclasses
import json

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.content.schema import SocialGroup, Stage
from anachronism.engine.save import SaveError, dumps, loads
from anachronism.engine.setup import build_state
from anachronism.engine.state import GameState


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def state(content: Content) -> GameState:
    return build_state(content, "bronze_dawn", seed=42)


def test_new_game_matches_the_scenario(state: GameState) -> None:
    assert state.year == -1200
    assert state.turn == 0
    assert state.player_civ == "veyra"
    assert sorted(state.civs) == ["kessrin", "ushkai", "veyra"]
    assert state.population("veyra") == 370_000
    assert state.owned_provinces("ushkai") == [
        "ushkai_grasslands",
        "ushkai_high_pasture",
        "ushkai_north_steppe",
        "ushkai_salt_flats",
    ]
    assert state.provinces["desert_oasis"].owner is None
    veyra = state.civs["veyra"]
    assert veyra.capital == "veyra_heartland"
    assert veyra.starting_provinces == 6
    assert veyra.stats.literacy_bp == 300
    assert veyra.influence[SocialGroup.CLERGY] == 4_500


def test_starting_techs_get_stage_and_spread(state: GameState) -> None:
    veyra = state.civs["veyra"]
    assert veyra.tech["irrigation"].stage is Stage.WIDESPREAD
    assert veyra.tech["irrigation"].spread_bp == 10_000
    assert veyra.tech["writing"].stage is Stage.ADOPTED
    assert veyra.tech["writing"].spread_bp == 5_000
    kessrin = state.civs["kessrin"]
    assert kessrin.tech["writing"].stage is Stage.CONCEPT
    assert kessrin.tech["writing"].spread_bp == 0


def test_same_seed_same_game_and_different_seed_different_rng(content: Content) -> None:
    first = build_state(content, "bronze_dawn", seed=7)
    again = build_state(content, "bronze_dawn", seed=7)
    other = build_state(content, "bronze_dawn", seed=8)
    assert dumps(first) == dumps(again)
    assert first.rng != other.rng


def test_unknown_scenario_is_a_clear_error(content: Content) -> None:
    with pytest.raises(ValueError, match=r"unknown scenario 'atlantis'.*bronze_dawn"):
        build_state(content, "atlantis", seed=1)


def test_provinces_outside_the_scenario_are_dropped_from_borders(content: Content) -> None:
    scenario = content.scenarios["bronze_dawn"]
    unowned = {pid: pop for pid, pop in scenario.unowned.items() if pid != "desert_oasis"}
    smaller = scenario.model_copy(update={"unowned": unowned})
    trimmed = dataclasses.replace(content, scenarios={"bronze_dawn": smaller})
    state = build_state(trimmed, "bronze_dawn", seed=1)
    assert "desert_oasis" not in state.provinces
    assert "desert_oasis" not in state.world.geography["veyra_western_fields"].neighbours


def test_save_round_trip_is_byte_identical(state: GameState) -> None:
    text = dumps(state)
    loaded = loads(text)
    assert loaded == state
    assert dumps(loaded) == text


def test_save_is_canonical_json_with_sorted_keys(state: GameState) -> None:
    text = dumps(state)
    assert list(json.loads(text)) == sorted(json.loads(text))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("not json", "not a save file"),
        ('{"schema_version": 99}', "save format 99 is not supported"),
        ('{"schema_version": 1, "seed": 3}', "damaged"),
    ],
)
def test_bad_saves_are_rejected(text: str, message: str) -> None:
    with pytest.raises(SaveError, match=message):
        loads(text)


def test_copies_share_frozen_content_but_not_mutable_state(state: GameState) -> None:
    copy = state.model_copy(deep=True)
    assert copy.world is state.world
    assert copy.tech_nodes["writing"] is state.tech_nodes["writing"]
    assert copy.civs["veyra"] is not state.civs["veyra"]
    copy.civs["veyra"].stockpiles.food = 0
    assert state.civs["veyra"].stockpiles.food == 600


def test_common_techs_reach_only_states_with_the_prerequisites(content: Content) -> None:
    state = build_state(content, "rome_264", seed=1)
    assert state.civs["rome"].tech["written_law"].stage is Stage.WIDESPREAD
    assert "written_law" not in state.civs["e2_boii"].tech  # no writing yet
    for civ in state.civs.values():
        for node_id, known in civ.tech.items():
            if known.stage.is_adopted:
                for needed in content.techs[node_id].prerequisites:
                    assert civ.tech[needed].stage.is_adopted, (civ.id, node_id, needed)


def test_difficulty_levels_change_the_rival_rules_and_are_saved(content: Content) -> None:
    easy = build_state(content, "rome_264", seed=1, difficulty="easy")
    hard = build_state(content, "rome_264", seed=1, difficulty="hard")
    normal = build_state(content, "rome_264", seed=1)
    rules = normal.world.rules.rivals
    assert easy.world.rules.rivals.player_grace_turns > rules.player_grace_turns
    assert hard.world.rules.rivals.capture_per_excess_bp > rules.capture_per_excess_bp
    assert loads(dumps(hard)).world.difficulty == "hard"
    with pytest.raises(ValueError, match="unknown difficulty"):
        build_state(content, "rome_264", seed=1, difficulty="nightmare")

"""The turn's replay for the client (D-124)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.engine.actions import MarchArmy, RaiseArmy
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.tools.replay import build, snapshot


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


def test_a_march_and_a_raised_army_are_in_the_replay(content: Content) -> None:
    state = new_game(content, "rome_264", seed=3, player_civ="rome")
    state, _ = apply_action(state, RaiseArmy(civ="rome", province=state.civs["rome"].capital))
    army = next(a for a in state.armies.values() if a.owner == "rome")
    goal = state.world.geography[army.province].neighbours[0]
    state, _ = apply_action(state, MarchArmy(civ="rome", army=army.id, target=goal))
    before = snapshot(state)
    after, events = end_turn(state)
    replay = build(before, after, events)
    moved = [m for m in replay["marches"] if m["id"] == army.id]
    assert after.armies[army.id].province == goal  # one province away: there in a turn
    assert moved
    assert moved[0]["road"] == [goal]
    assert moved[0]["mine"]
    assert set(replay) >= {"marches", "sails", "sieges", "raised", "lost", "battles", "taken"}


def test_changes_of_ownership_are_flagged(content: Content) -> None:
    state = new_game(content, "rome_264", seed=3, player_civ="rome")
    before = snapshot(state)
    after = state.model_copy(deep=True)
    pid = after.owned_provinces("carthage")[0]
    after.provinces[pid].owner = "rome"
    replay = build(before, after, [])
    assert replay["taken"] == [
        {"at": pid, "from": "carthage", "to": "rome", "mine": True, "how": ""}
    ]


def test_a_sunk_fleet_is_among_the_losses(content: Content) -> None:
    state = new_game(content, "rome_264", seed=3, player_civ="rome")
    assert state.fleets
    fleet_id = sorted(state.fleets)[0]
    before = snapshot(state)
    after = state.model_copy(deep=True)
    del after.fleets[fleet_id]
    replay = build(before, after, [])
    assert [x["id"] for x in replay["lost"] if x.get("fleet")] == [fleet_id]


def test_your_cities_show_what_each_building_would_add(content: Content) -> None:
    # D-127: plain numbers for every building the player could raise, and the city's rank
    from anachronism.tools.view import build_view, city_tier

    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state.provinces["it_roma"].population = 900_000  # a city grown to a Town, as Latium once was
    latium = next(p for p in build_view(state)["provinces"] if p["id"] == "it_roma")
    assert latium["tier_name"] == "Town"
    assert latium["output"]["food"] > 0
    options = latium["can_build"]
    assert sum(1 for o in options if o["recommended"]) == 1
    granary = next(o for o in options if o["id"] == "granary")
    assert any("food a turn" in gain for gain in granary["gains"])
    assert city_tier(100_000, 0) == 0
    assert city_tier(3_000_000, 7) == 4

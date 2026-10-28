"""Holding conquered land (D-106)."""

from __future__ import annotations

from anachronism.content.loader import Content
from anachronism.engine.events import EventLog
from anachronism.engine.game import new_game
from anachronism.engine.occupation import garrisoned, occupation, restless
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, GameState
from anachronism.engine.war import capture


def conquered(content: Content) -> tuple[GameState, str]:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    target = next(
        p for p in state.owned_provinces("carthage") if p != state.civs["carthage"].capital
    )
    capture(state, "rome", target, EventLog(0, 0))
    state.armies = {}
    rules = state.world.rules.armies.model_copy(update={"uprising_bp": 10_000})
    state.world = state.world.model_copy(
        update={"rules": state.world.rules.model_copy(update={"armies": rules})}
    )
    return state, target


def test_a_conquered_people_remembers(content: Content) -> None:
    state, target = conquered(content)
    assert restless(state, target)
    assert state.provinces[target].people == "carthage"
    assert not restless(state, state.civs["rome"].capital)


def test_without_a_garrison_they_rise_for_their_old_lords(content: Content) -> None:
    state, target = conquered(content)
    state.civs["rome"].stats.unrest_bp = 10_000
    for _ in range(20):
        occupation(state, GameRng(state.rng), EventLog(state.turn, state.year))
        if state.provinces[target].owner != "rome":
            break
    assert state.provinces[target].owner == "carthage"


def test_a_garrison_holds_them_down(content: Content) -> None:
    state, target = conquered(content)
    need = state.provinces[target].population // state.world.rules.armies.garrison_people_per_man
    state.armies["g"] = Army(
        id="g", owner="rome", name="Garrison", province=target, troops={"levy": need + 1}
    )
    assert garrisoned(state, target)
    for _ in range(10):
        occupation(state, GameRng(state.rng), EventLog(state.turn, state.year))
    assert state.provinces[target].owner == "rome"


def test_in_time_they_become_our_own(content: Content) -> None:
    state, target = conquered(content)
    state.armies["g"] = Army(
        id="g", owner="rome", name="Garrison", province=target, troops={"levy": 10**6}
    )
    state.turn += state.world.rules.armies.assimilation_years // state.world.years_per_turn
    occupation(state, GameRng(state.rng), EventLog(state.turn, state.year))
    assert state.provinces[target].people == "rome"
    assert not restless(state, target)

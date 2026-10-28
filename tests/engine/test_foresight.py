"""The future is the player's alone; rivals get it only by spying (D-125)."""

from __future__ import annotations

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus, Stage
from anachronism.engine.events import EventLog
from anachronism.engine.game import new_game
from anachronism.engine.intelligence import rival_spies
from anachronism.engine.rivals import set_status, start_project
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState, Heard, TechState
from anachronism.engine.tech import beyond_age, feasibility


def _rome(content: Content) -> GameState:
    return new_game(content, "rome_264", seed=1, player_civ="rome")


def test_rivals_cannot_reach_ahead_of_their_age_but_the_player_can(content: Content) -> None:
    state = _rome(content)
    assert state.tech_nodes["printing_press"].year > state.year + 500
    assert beyond_age(state, "carthage", "printing_press")
    assert feasibility(state, "carthage", "printing_press").beyond_age
    assert not beyond_age(state, "rome", "printing_press")
    # something whose time has come is open to everyone
    near = next(n for n, node in sorted(state.tech_nodes.items()) if node.year <= state.year)
    assert not beyond_age(state, "carthage", near)


def test_a_stolen_secret_opens_the_future_to_a_rival(content: Content) -> None:
    state = _rome(content)
    node = "crop_rotation"
    assert not start_project(state, "pergamon", node)
    state.civs["pergamon"].tech[node] = TechState(stage=Stage.CONCEPT, stolen=True)
    assert not beyond_age(state, "pergamon", node)


def test_courts_that_heard_of_your_arts_send_spies_to_steal_them(content: Content) -> None:
    state = _rome(content)
    rules = state.world.rules.rivals
    object.__setattr__(rules, "rival_spy_bp", 10_000)
    object.__setattr__(rules, "rival_spy_caught_bp", 0)
    set_status(state, "rome", "carthage", RelationStatus.TRADING)
    # Rome has an idea far ahead of its time, and Carthage has heard of it
    node = next(
        n
        for n, t in sorted(state.tech_nodes.items())
        if t.year > state.year + 100
        and all(
            state.civs["carthage"].tech.get(p) and state.civs["carthage"].tech[p].stage.is_adopted
            for p in t.prerequisites
        )
    )
    state.civs["rome"].tech[node] = TechState(stage=Stage.ADOPTED)
    state.civs["carthage"].heard.append(Heard(about="rome", node_id=node, turn=0, garbled=False))
    events = EventLog(turn=state.turn, year=state.year)
    rival_spies(state, GameRng.from_seed(1), events)
    stolen = state.civs["carthage"].tech.get(node)
    assert stolen is not None
    assert stolen.stolen
    assert any(e.kind == "secrets_lost" for e in events.items)

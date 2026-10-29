"""Dilemmas put to the ruler (D-104)."""

from __future__ import annotations

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus, Stage
from anachronism.engine.actions import ChooseDilemma
from anachronism.engine.dilemmas import ask, fits
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.rivals import set_status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState


def only(state: GameState, dilemma_id: str, chance: int = 10_000) -> None:
    dilemma = state.world.dilemmas[dilemma_id].model_copy(update={"chance_bp": chance})
    state.world = state.world.model_copy(update={"dilemmas": {dilemma_id: dilemma}})


def test_historical_dilemmas_need_their_moment(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    corvus = state.world.dilemmas["corvus"]
    # rome_264 opens with Rome at war with Volsinii (DEC014); a dilemma cannot yet name its enemy,
    # so make peace there first to test the at-peace case.
    set_status(state, "rome", "e2_volsinii", RelationStatus.NEUTRAL)
    assert not fits(state, corvus)  # Rome is at peace: no Carthaginian wreck on the shore
    set_status(state, "rome", "carthage", RelationStatus.WAR)
    assert fits(state, corvus)
    carthage = new_game(content, "rome_264", seed=1, player_civ="carthage")
    set_status(carthage, "rome", "carthage", RelationStatus.WAR)
    carthage_dilemmas = carthage.world.dilemmas
    assert "corvus" not in {d for d in carthage_dilemmas if fits(carthage, carthage_dilemmas[d])}


def test_answering_applies_the_choice(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    only(state, "comet")
    ask(state, GameRng(state.rng), EventLog(state.turn, state.year))
    assert state.dilemma == "comet"
    before = dict(state.civs["rome"].influence)
    state, logged = apply_action(state, ChooseDilemma(civ="rome", dilemma="comet", choice=1))
    assert logged.ok
    assert "their temples fill" in logged.message
    assert state.dilemma is None
    assert state.civs["rome"].influence != before
    _, logged = apply_action(state, ChooseDilemma(civ="rome", dilemma="comet", choice=1))
    assert not logged.ok  # answered already


def test_unanswered_the_court_decides_and_once_is_once(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    only(state, "comet")
    ask(state, GameRng(state.rng), EventLog(state.turn, state.year))
    assert state.dilemma == "comet"
    state, events = end_turn(state)
    assert any(e.kind == "dilemma_settled" for e in events)
    assert state.dilemma is None  # a "once" dilemma does not return
    assert state.dilemmas_seen == ["comet"]


def test_an_idea_is_planted(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    set_status(state, "rome", "carthage", RelationStatus.WAR)
    only(state, "corvus")
    ask(state, GameRng(state.rng), EventLog(state.turn, state.year))
    assert state.dilemma == "corvus"
    me = state.player_civ
    state.civs[me].stockpiles.wealth = 10_000
    had = state.civs[me].tech.get("sternpost_rudder")
    state, logged = apply_action(state, ChooseDilemma(civ=me, dilemma="corvus", choice=0))
    assert logged.ok
    if had is None:
        assert state.civs[me].tech["sternpost_rudder"].stage is Stage.CONCEPT

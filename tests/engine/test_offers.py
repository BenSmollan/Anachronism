"""Envoys from rival courts and the player's answers (D-105)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import Disposition, RelationStatus
from anachronism.engine.actions import AnswerEnvoy, DeclareWar
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.offers import _candidates, envoys
from anachronism.engine.rivals import relation, status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState, Offer


@pytest.fixture
def rome(content: Content) -> GameState:
    state = new_game(content, "punic_wars", seed=1, player_civ="rome")
    state.turn = 5  # past the opening grace
    return state


def test_a_beaten_weary_enemy_sues_for_peace(rome: GameState) -> None:
    state, _ = apply_action(rome, DeclareWar(civ="rome", target="syracuse"))
    rel = relation(state, "rome", "syracuse")
    assert rel is not None
    rel.losses["syracuse"] = 2
    rel.weariness["syracuse"] = 9000
    assert any(o.kind == "peace" and o.from_civ == "syracuse" for o in _candidates(state))
    state.offer = Offer(kind="peace", from_civ="syracuse")
    state, logged = apply_action(state, AnswerEnvoy(civ="rome", accept=True))
    assert logged.ok
    assert status(state, "rome", "syracuse") is not RelationStatus.WAR


def test_defying_an_ultimatum_means_war(rome: GameState) -> None:
    rome.offer = Offer(kind="ultimatum", from_civ="syracuse")
    state, logged = apply_action(rome, AnswerEnvoy(civ="rome", accept=False))
    assert logged.ok
    assert status(state, "rome", "syracuse") is RelationStatus.WAR


def test_paying_tribute_keeps_the_peace_at_a_price(rome: GameState) -> None:
    rome.offer = Offer(kind="ultimatum", from_civ="syracuse")
    wealth = rome.civs["rome"].stockpiles.wealth
    state, logged = apply_action(rome, AnswerEnvoy(civ="rome", accept=True))
    assert logged.ok
    assert state.civs["rome"].stockpiles.wealth < wealth
    assert status(state, "rome", "syracuse") is RelationStatus.TRIBUTARY


def test_unanswered_envoys_are_refused(rome: GameState) -> None:
    rome.offer = Offer(kind="trade", from_civ="syracuse")
    state, events = end_turn(rome)
    assert any(e.kind == "envoy_declined" for e in events)
    assert status(state, "rome", "syracuse") is not RelationStatus.TRADING


def test_a_merchant_court_proposes_trade(rome: GameState) -> None:
    rome.civs["syracuse"].disposition = Disposition.MERCANTILE
    rel = relation(rome, "rome", "syracuse")
    assert rel is not None
    rel.status = RelationStatus.NEUTRAL
    rel.grievance = {}
    override = rome.world.rules.rivals.model_copy(update={"envoy_offer_bp": 10_000})
    rome.world = rome.world.model_copy(
        update={"rules": rome.world.rules.model_copy(update={"rivals": override})}
    )
    envoys(rome, GameRng(rome.rng), EventLog(rome.turn, rome.year))
    assert rome.offer is not None
    state, logged = apply_action(rome, AnswerEnvoy(civ="rome", accept=True))
    if rome.offer.kind == "trade" and rome.offer.from_civ == "syracuse":
        assert status(state, "rome", "syracuse") is RelationStatus.TRADING
    assert logged.ok

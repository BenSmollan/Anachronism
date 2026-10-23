"""Explaining the court's new arts quiets suspicion (DESIGN §7)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.engine.actions import Explain
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.state import Framing, GameState, NewsInTransit


@pytest.fixture
def suspected(content: Content) -> GameState:
    state = new_game(content, "punic_wars", seed=1, player_civ="rome")
    rome = state.civs["rome"]
    rome.stockpiles.wealth = 100_000
    rome.stockpiles.knowledge = 100_000
    rome.stats.suspicion_bp = 4000
    rome.framing = Framing.WITCHCRAFT
    return state


def test_a_trusted_ruler_turns_witchcraft_into_awe(suspected: GameState) -> None:
    suspected.civs["rome"].stats.legitimacy_bp = 7000
    state, logged = apply_action(suspected, Explain(civ="rome", story="divine"))
    assert logged.ok
    rome = state.civs["rome"]
    assert rome.stats.suspicion_bp == 2000
    assert rome.framing is Framing.INSPIRED
    assert rome.stockpiles.wealth < 100_000


def test_a_doubted_ruler_only_quiets_the_talk(suspected: GameState) -> None:
    suspected.civs["rome"].stats.legitimacy_bp = 2000
    state, logged = apply_action(suspected, Explain(civ="rome", story="divine"))
    assert logged.ok
    assert state.civs["rome"].framing is Framing.WITCHCRAFT
    assert state.civs["rome"].stats.suspicion_bp == 2000


def test_foreign_sages_quiet_more_but_rivals_hear_at_once(suspected: GameState) -> None:
    suspected.news.append(
        NewsInTransit(
            to_civ="carthage", about="rome", node_id="paper", arrives_turn=9, garbled=False
        )
    )
    state, logged = apply_action(suspected, Explain(civ="rome", story="sages"))
    assert logged.ok
    assert state.civs["rome"].stats.suspicion_bp == 500
    assert state.civs["rome"].stockpiles.knowledge < 100_000
    assert state.news[-1].arrives_turn == state.turn + 1


def test_a_story_told_too_often_is_refused(suspected: GameState) -> None:
    state, logged = apply_action(suspected, Explain(civ="rome", story="divine"))
    assert logged.ok
    state, logged = apply_action(state, Explain(civ="rome", story="sages"))
    assert not logged.ok
    for _ in range(3):
        state, _ = end_turn(state)
    state.civs["rome"].stats.suspicion_bp = 3000
    _, logged = apply_action(state, Explain(civ="rome", story="sages"))
    assert logged.ok


def test_nothing_to_explain_or_no_money(suspected: GameState) -> None:
    calm = suspected.model_copy(deep=True)
    calm.civs["rome"].stats.suspicion_bp = 0
    assert not apply_action(calm, Explain(civ="rome"))[1].ok
    poor = suspected.model_copy(deep=True)
    poor.civs["rome"].stockpiles.wealth = 0
    assert not apply_action(poor, Explain(civ="rome", story="divine"))[1].ok

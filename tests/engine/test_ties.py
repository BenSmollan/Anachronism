"""What a friendly tie is worth (D-278): tribute paid to an overlord, faith and trade."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.culture import tie_income, trade, tribute
from anachronism.engine.game import new_game
from anachronism.engine.rivals import make_tributary, overlord_of, set_status
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import GameState
from anachronism.tools.view import build_view

ME, OTHER = "rome", "carthage"


@pytest.fixture
def state(content: Content) -> GameState:
    return new_game(content, "punic_wars", seed=1, player_civ=ME)


def test_a_tributary_pays_its_overlord_every_turn(state: GameState) -> None:
    make_tributary(state, ME, OTHER)
    assert overlord_of(state, ME, OTHER) == ME
    state.civs[OTHER].stockpiles.wealth = 10_000
    owed = tribute(state, OTHER)
    assert 0 < owed <= 5_000
    mine = state.civs[ME].stockpiles.wealth
    trade(state)
    assert state.civs[ME].stockpiles.wealth >= mine + owed


def test_the_overlord_is_remembered_and_cleared(state: GameState) -> None:
    make_tributary(state, OTHER, ME)
    assert overlord_of(state, ME, OTHER) == OTHER
    assert loads(dumps(state)).relations["carthage|rome"].overlord == OTHER
    set_status(state, ME, OTHER, RelationStatus.TRADING)
    assert overlord_of(state, ME, OTHER) is None
    assert state.relations["carthage|rome"].overlord == ""


def test_old_tributary_bonds_fall_to_the_larger(state: GameState) -> None:
    set_status(state, ME, OTHER, RelationStatus.TRIBUTARY)  # no overlord recorded
    bigger = max((ME, OTHER), key=lambda c: state.population(c))
    assert overlord_of(state, ME, OTHER) == bigger


def test_shared_faith_trades_more(state: GameState) -> None:
    set_status(state, ME, OTHER, RelationStatus.TRADING)
    state.civs[OTHER].faith = "roman_gods" if state.civs[ME].faith != "roman_gods" else "x"
    state.civs[ME].faith = "roman_gods"
    apart = tie_income(state, ME, OTHER)
    state.civs[OTHER].faith = state.civs[ME].faith
    together = tie_income(state, ME, OTHER)
    assert apart > 0
    assert together > apart


def test_the_world_tab_shows_what_a_tie_is_worth(state: GameState) -> None:
    make_tributary(state, ME, OTHER)
    state.civs[OTHER].stockpiles.wealth = 10_000
    other = next(c for c in build_view(state)["civs"] if c["id"] == OTHER)
    assert other["tribute_in"] > 0
    assert other["tribute_out"] == 0
    assert other["trade_income"] > 0

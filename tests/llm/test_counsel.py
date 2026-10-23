"""Aware rival courts decide with the model (brief §7.2): bounded, guarded and recorded."""

from __future__ import annotations

from pathlib import Path

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import DeclareWar, SendEnvoy
from anachronism.engine.game import new_game
from anachronism.engine.rivals import relation
from anachronism.engine.state import Awareness, GameState
from anachronism.llm.config import LlmConfig
from anachronism.llm.counsel import available_moves, to_action, who_counsels
from anachronism.llm.fake import FakeProvider
from anachronism.llm.pipeline import IdeaPipeline
from anachronism.llm.provider import ProviderError
from anachronism.tools.server import Session

ONLINE = LlmConfig(api_key="test", model="fake-model")


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def game(content: Content) -> GameState:
    state = new_game(content, "punic_wars", seed=4, player_civ="rome")
    state.civs["carthage"].awareness = Awareness.AWARE
    state.civs["carthage"].stockpiles.wealth = 100_000
    state.civs["carthage"].martial_bp = 30_000  # a court strong enough to dare a war
    return state


def test_only_aware_courts_counsel_the_deepest_grudge_first(game: GameState) -> None:
    assert who_counsels(game) == "carthage"
    game.civs["syracuse"].awareness = Awareness.FREE_AGENT
    rel = relation(game, "syracuse", "rome")
    assert rel is not None
    rel.grievance["syracuse"] = 5000
    assert who_counsels(game) == "syracuse"
    for civ in game.civs.values():
        civ.awareness = Awareness.ON_SCRIPT
    assert who_counsels(game) is None


def test_the_guard_refuses_hopeless_wars(game: GameState) -> None:
    assert "war" in available_moves(game, "carthage")
    assert isinstance(to_action(game, "carthage", "war"), DeclareWar)
    assert isinstance(to_action(game, "carthage", "envoy"), SendEnvoy)
    assert to_action(game, "carthage", "wait") is None
    for province in game.provinces.values():  # make Carthage a speck
        if province.owner == "carthage":
            province.population = 1000
    assert "war" not in available_moves(game, "carthage")
    assert to_action(game, "carthage", "war") is None


def test_counsel_returns_a_guarded_move_and_a_line(game: GameState) -> None:
    fake = FakeProvider({"move": "envoy", "line": "Let us talk, Qin.", "reason": "curious"})
    action, line = IdeaPipeline(ONLINE, fake, use_files=False).counsel(game, "carthage")
    assert isinstance(action, SendEnvoy)
    assert line == "Let us talk, Qin."
    assert "available moves" in fake.calls[0][1]
    for reply in (ProviderError("down"), {"move": "conquer the world", "line": "x"}):
        pipeline = IdeaPipeline(ONLINE, FakeProvider(reply), use_files=False)
        assert pipeline.counsel(game, "carthage") == (None, "")
    assert IdeaPipeline(LlmConfig(offline=True), use_files=False).counsel(game, "carthage") == (None, "")


def test_a_court_that_marches_is_recorded_and_speaks(tmp_path: Path, game: GameState) -> None:
    fake = FakeProvider({"move": "war", "line": "Your sorcery ends here."})
    session = Session(load_content(), tmp_path, IdeaPipeline(ONLINE, fake, use_files=False))
    session.new_game({"scenario": "punic_wars", "civ": "rome", "seed": 4})
    session.state = game
    view = session.end_turn({})
    assert view["voices"][0]["text"] == "Your sorcery ends here."
    assert view["voices"][0]["civ"] == "carthage"
    rel = relation(session.game(), "carthage", "rome")
    assert rel is not None
    assert rel.status is RelationStatus.WAR
    assert any(isinstance(entry.action, DeclareWar) for entry in session.game().action_log)

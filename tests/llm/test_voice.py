"""Rival rulers voiced by the model: flavour only, always with a safe fallback."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.engine.game import new_game
from anachronism.engine.save import dumps
from anachronism.engine.state import GameState
from anachronism.llm.config import LlmConfig
from anachronism.llm.fake import FakeProvider
from anachronism.llm.pipeline import IdeaPipeline
from anachronism.llm.prompts import VOICE_TOOL
from anachronism.llm.provider import ProviderError
from anachronism.llm.voice import MAX_CHARS, clean_line, facts

ONLINE = LlmConfig(api_key="test", model="fake-model")
LINE = "We sent envoys; you sent excuses. Now Wei sends its armies."


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def game(content: Content) -> GameState:
    return new_game(content, "punic_wars", seed=4, player_civ="rome")


def test_offline_keeps_the_content_line(game: GameState) -> None:
    pipeline = IdeaPipeline(LlmConfig(offline=True), use_files=False)
    assert pipeline.voice_rival(game, "carthage", "rival_war", "Wei", LINE) == (LINE, "content")


def test_the_model_rewrites_the_line_and_it_is_cached(game: GameState) -> None:
    fake = FakeProvider({"line": '"Qin dares too much. Wei answers with iron."'})
    pipeline = IdeaPipeline(ONLINE, fake, use_files=False)
    before = dumps(game)
    text, source = pipeline.voice_rival(game, "carthage", "rival_war", "Wei", LINE)
    assert (text, source) == ("Qin dares too much. Wei answers with iron.", "model")
    assert pipeline.voice_rival(game, "carthage", "rival_war", "Wei", LINE)[1] == "cache"
    assert len(fake.calls) == 1
    assert dumps(game) == before  # speech never touches the game


def test_the_message_holds_facts_not_player_text(game: GameState) -> None:
    fake = FakeProvider({"line": "So be it."})
    IdeaPipeline(ONLINE, fake, use_files=False).voice_rival(game, "carthage", "rival_war", "Wei", LINE)
    system, user = fake.calls[0]
    assert VOICE_TOOL in system
    assert game.civs["carthage"].name in user
    assert "has just declared war" in user
    assert LINE in user


def test_failures_fall_back_to_the_content_line(game: GameState) -> None:
    for reply in (ProviderError("down"), {"wrong": "shape"}, {"line": "  "}):
        pipeline = IdeaPipeline(ONLINE, FakeProvider(reply), use_files=False)
        assert pipeline.voice_rival(game, "carthage", "rival_war", "Wei", LINE) == (LINE, "content")


def test_long_or_marked_up_lines_are_tidied() -> None:
    assert clean_line("  **We  <b>march</b>!**  ") == "We bmarch/b!"
    long = "We march at dawn. " * 40
    assert len(clean_line(long)) <= MAX_CHARS
    assert clean_line(long).endswith(".")


def test_facts_come_from_the_game(game: GameState) -> None:
    known = facts(game, "carthage", "rival_war", "Wei")
    assert known["temperament"] == game.civs["carthage"].disposition.value
    assert "BC" in known["year"]
    assert game.civs["rome"].name in known["addressing"]

"""The story so far: chapters of the game, told plainly or by the model."""

from __future__ import annotations

from pathlib import Path

from anachronism.content.loader import load_content
from anachronism.engine.bots import make_bot, play_turn
from anachronism.engine.game import new_game
from anachronism.engine.state import GameState
from anachronism.llm.config import LlmConfig
from anachronism.llm.fake import FakeProvider
from anachronism.llm.pipeline import IdeaPipeline
from anachronism.tools.chronicle import CHAPTER_TURNS, chapters
from anachronism.tools.server import Session


def played(turns: int) -> GameState:
    state = new_game(load_content(), "rome_264", seed=2)
    bots = {civ: make_bot("growth") for civ in state.civs}
    for _ in range(turns):
        state, _ = play_turn(state, bots)
    return state


def test_chapters_cover_the_game_in_order() -> None:
    state = played(CHAPTER_TURNS * 2 + 2)
    told = chapters(state)
    assert [c.finished for c in told] == [True, True, False]
    assert told[0].start_year == -264
    assert told[0].end_year == told[1].start_year
    assert told[-1].end_year == state.year
    assert all(c.text for c in told)
    assert "Rome" in told[0].facts["realm"]
    assert "million" in told[0].facts["people"]


def test_a_new_game_has_no_chapters() -> None:
    assert chapters(new_game(load_content(), "rome_264", seed=2)) == []


def test_finished_chapters_are_told_by_the_model_and_cached(tmp_path: Path) -> None:
    fake = FakeProvider({"line": "In those years Rome grew wise and quarrelsome."})
    online = IdeaPipeline(LlmConfig(api_key="k", model="m"), fake, use_files=False)
    session = Session(load_content(), tmp_path, online)
    session.new_game({"scenario": "rome_264", "seed": 2})
    session.state = played(CHAPTER_TURNS + 1)
    reply = session.chronicle({})
    told = reply["chapters"]
    assert [c["source"] for c in told] == ["content", "model"]  # newest first
    assert told[1]["text"].startswith("In those years")
    assert session.chronicle({})["chapters"][1]["source"] == "cache"
    assert len(fake.calls) == 1


def test_history_is_not_always_the_first_choice_shown() -> None:
    """Choices are listed in a shuffled order fixed per game and chapter (D-265)."""
    from anachronism.content.loader import load_content
    from anachronism.engine.game import new_game
    from anachronism.tools.story import choice_order

    content = load_content()
    state = new_game(content, "rome_264", seed=1, chronicle=True)
    firsts = []
    # few chapters, so the share is pooled over many games to be a fair sample
    for seed in range(1, 21):
        game = new_game(content, "rome_264", seed=seed, chronicle=True)
        for chapter in content.chapters.values():
            order = choice_order(game, chapter)
            assert sorted(order) == list(range(len(chapter.choices)))
            assert order == choice_order(game, chapter), "the order must not change between frames"
            ideas = [bool(chapter.choices[i].needs_adopted) for i in order]
            assert ideas == sorted(ideas), "choices needing an idea stay last"
            firsts.append(chapter.choices[order[0]].historical)
    share = sum(firsts) / len(firsts)
    assert 0.25 < share < 0.6, f"history's choice is shown first in {share:.0%} of chapters"
    other = new_game(content, "rome_264", seed=2, chronicle=True)
    assert any(
        choice_order(state, c) != choice_order(other, c) for c in content.chapters.values()
    ), "different games should list choices differently"

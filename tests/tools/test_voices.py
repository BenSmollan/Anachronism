"""Characters speak at the right moments, with the right names, deterministically."""

from __future__ import annotations

from pathlib import Path

import pytest

from anachronism.content.issues import ContentError
from anachronism.content.loader import Content, load_content
from anachronism.engine.game import new_game
from anachronism.engine.state import Event
from anachronism.tools.voices import opening_voices, speak, voices_for_turn
from tests.content.test_loader import edit, packs  # noqa: F401  (fixture)


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


def event(kind: str, civ: str, subject: str = "") -> Event:
    return Event(turn=1, year=-340, civ=civ, kind=kind, message="", subject=subject)


def test_the_ruler_opens_the_game(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    voice = speak(content, state, "game_start")
    assert voice is not None
    assert voice["name"] == "Duke Xiao"
    assert voice["portrait"] == "court"
    assert "{" not in voice["text"]


def test_the_steward_briefs_a_new_game_on_its_moment(content: Content) -> None:
    state = new_game(content, "sengoku", seed=1)
    voices = opening_voices(content, state)
    assert [v["moment"] for v in voices] == ["briefing", "game_start"]
    assert "Imagawa" in voices[0]["text"]
    assert voices[0]["speaker"] == "steward"


def test_worst_news_first_and_at_most_two(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    events = [
        event("widespread", "rome", "Coinage"),
        event("adopted", "rome", "Paper"),
        event("riot", "rome"),
        event("setback", "rome", "Roads"),
    ]
    voices = voices_for_turn(content, state, events)
    assert [v["moment"] for v in voices] == ["riot", "adopted"]
    assert voices[0]["name"] == "General"
    assert "Paper" in voices[1]["text"]


def test_a_rival_boasts_about_ideas_ahead_of_their_time(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    voices = voices_for_turn(content, state, [event("adopted", "chu", "Paper")])
    assert [v["moment"] for v in voices] == ["rival_adopted"]
    assert voices[0]["name"] == "King Xuan"
    assert voices[0]["civ"] == "chu"
    assert "Chu" in voices[0]["text"]
    # an old idea is not worth a boast; a quiet turn gets the steward instead
    quiet = voices_for_turn(content, state, [event("adopted", "chu", "Writing")])
    assert [v["moment"] for v in quiet] == ["quiet"]


def test_lines_are_chosen_deterministically(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=4)
    first = [speak(content, state, "adopted", "Paper") for _ in range(3)]
    assert first[0] == first[1] == first[2]


def load(root: Path) -> list[str]:
    with pytest.raises(ContentError) as error:
        load_content(root=root)
    return [str(issue) for issue in error.value.issues]


def test_bad_dialogue_is_reported(packs: Path) -> None:  # noqa: F811
    edit(packs / "core" / "dialogue.yaml", "speaker: diviner", "speaker: jester")
    edit(packs / "core" / "dialogue.yaml", "{subject}? Fascinating.", "{idea}? Fascinating.")
    found = load(packs)
    assert any("unknown speaker 'jester'" in p for p in found)
    assert any("unknown placeholder(s) ['idea']" in p for p in found)


def test_a_rival_who_declares_war_says_so(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    carthage = state.civs["carthage"].name
    war = Event(
        turn=1, year=-340, civ="rome", kind="war",
        message=f"The Wei court has declared war on {state.civs['rome'].name}.", subject=carthage,
    )  # fmt: skip
    voices = voices_for_turn(content, state, [war])
    rival = [v for v in voices if v["speaker"] == "rival"]
    assert len(rival) == 1
    assert rival[0]["civ"] == "carthage"
    assert rival[0]["moment"] == "rival_war"
    assert voices[0]["speaker"] != "rival"  # the court speaks first


def test_a_rival_makes_peace(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    voices = voices_for_turn(content, state, [event("peace", "rome", state.civs["zhao"].name)])
    assert any(v["moment"] == "rival_peace" and v["civ"] == "zhao" for v in voices)


def test_the_court_mourns_the_old_ruler_and_turns_to_the_new(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    state.civs["rome"].ruler = "King Huiwen"
    voices = voices_for_turn(content, state, [event("ruler_died", "rome", "Duke Xiao")])
    assert voices[0]["moment"] == "ruler_died"
    assert "Duke Xiao" in voices[0]["text"]
    assert "King Huiwen" in voices[0]["text"]


def test_no_eulogy_for_an_unnamed_ruler(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1, player_civ="carthage")
    assert state.civs["carthage"].ruler == ""
    death = event("ruler_died", "carthage", "the ruler of Carthage")
    voices = voices_for_turn(content, state, [death])
    assert all(v["moment"] != "ruler_died" for v in voices)

"""Rulers age, die and are succeeded by history's heirs, then by unnamed ones."""

from __future__ import annotations

from anachronism.content.loader import Content
from anachronism.engine.events import EventLog
from anachronism.engine.game import new_game
from anachronism.engine.rng import GameRng
from anachronism.engine.rulers import age_and_succeed, death_chance_bp
from tests.engine.conftest import override_rules


def test_rulers_start_from_the_scenario(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1)
    assert state.civs["macedon"].ruler == "Antigonus II Gonatas"
    assert state.civs["macedon"].ruler_age == 55
    assert state.world.successors["macedon"][0].name == "Demetrius II"


def test_older_rulers_are_likelier_to_die(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1)
    macedon = state.civs["macedon"]
    young = death_chance_bp(state, macedon)
    macedon.ruler_age = 70
    assert death_chance_bp(state, macedon) > young


def test_succession_follows_history_then_heirs(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1)
    override_rules(state, society={"death_chance_per_year_of_age_bp": 10_000})
    macedon = state.civs["macedon"]
    macedon.stats.legitimacy_bp = 3000
    events = EventLog(0, state.year)
    rng = GameRng(state.rng)
    names: list[str] = []
    for _ in range(16):
        macedon.ruler_age = 80
        age_and_succeed(state, macedon, rng, events)
        if not names or names[-1] != macedon.ruler or macedon.ruler == "":
            names.append(macedon.ruler)  # the chance is capped at 90%, so one may survive a turn
    line = ["Demetrius II", "Antigonus III Doson", "Philip V", "Perseus"]
    assert names[:4] == line
    assert names[4] == ""  # then unnamed heirs
    assert macedon.rulers >= 6
    kinds = [e.kind for e in events.items]
    assert "ruler_died" in kinds
    assert "succession_crisis" in kinds
    for e in events.items:
        assert " of Macedon of Macedon" not in e.message  # an unnamed ruler still reads naturally

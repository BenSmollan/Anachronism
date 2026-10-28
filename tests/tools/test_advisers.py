"""The court's counsel: one recommendation per adviser, suited to the moment."""

from __future__ import annotations

from anachronism.content.loader import load_content
from anachronism.engine.actions import DeclareWar
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.tech import feasibility
from anachronism.tools.advisers import REACH_YEARS, counsel


def test_each_adviser_recommends_a_distinct_idea_within_reach() -> None:
    content = load_content()
    state = new_game(content, "rome_264", seed=1)
    advice = counsel(content, state)
    assert {a["role"] for a in advice} == {"steward", "general", "scholar", "diviner"}
    assert len({a["node_id"] for a in advice}) == len(advice)
    for a in advice:
        assert not feasibility(state, state.player_civ, a["node_id"]).blocked
        assert a["years_ahead"] <= REACH_YEARS * 2
        assert a["text"]


def test_war_makes_the_general_urgent_and_first() -> None:
    content = load_content()
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state, _ = apply_action(state, DeclareWar(civ="rome", target="carthage"))
    advice = counsel(content, state)
    assert advice[0]["role"] == "general"
    assert advice[0]["urgent"]


def test_counsel_is_deterministic() -> None:
    content = load_content()
    a = counsel(content, new_game(content, "rome_264", seed=3))
    b = counsel(content, new_game(content, "rome_264", seed=3))
    assert a == b

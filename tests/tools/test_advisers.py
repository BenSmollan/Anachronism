"""The advisers' counsel: one recommendation per adviser, suited to the moment."""

from __future__ import annotations

import pytest

from anachronism.content.loader import load_content
from anachronism.content.schema import Stage
from anachronism.engine.actions import DeclareWar
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rivals import relation
from anachronism.engine.state import GameState, TechState
from anachronism.engine.tech import feasibility
from anachronism.tools.advisers import REACH_YEARS, _score, counsel, heard_from


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


def _ready_unknown(state: GameState, role: str) -> tuple[str, int]:
    """A ready idea of value to ``role`` that no civ in contact with Rome uses: (id, score)."""
    for node_id in sorted(state.tech_nodes):
        if state.tech_nodes[node_id].stub:
            continue
        if heard_from(state, "rome", node_id) is not None:
            continue
        if feasibility(state, "rome", node_id).blocked or node_id in state.civs["rome"].tech:
            continue
        score = _score(state, role, node_id, False, None)
        if score > 0:
            return node_id, score
    raise AssertionError("no unknown ready idea")


def _contact(state: GameState) -> str:
    """A living civ in contact with Rome."""
    return next(c for c in sorted(state.civs) if c != "rome" and relation(state, c, "rome"))


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_advisers_prefer_what_the_neighbours_use(seed: int) -> None:
    state = new_game(load_content(), "rome_264", seed=seed)
    node_id, before = _ready_unknown(state, "steward")
    other = _contact(state)
    state.civs[other].tech[node_id] = TechState(stage=Stage.ADOPTED)
    assert heard_from(state, "rome", node_id) == other
    assert _score(state, "steward", node_id, False, other) > before


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_an_old_idea_from_far_away_counts_for_less(seed: int) -> None:
    state = new_game(load_content(), "rome_264", seed=seed)
    old = [
        n for n in sorted(state.tech_nodes)
        if state.tech_nodes[n].year <= state.year and not state.tech_nodes[n].stub
    ]  # fmt: skip
    node_id = next(n for n in old if _score(state, "steward", n, False, "x") >= 30)
    far = _score(state, "steward", node_id, False, None)
    near = _score(state, "steward", node_id, False, "carthage")
    assert far < near
    assert abs(far * 3 - near) <= 3  # a half, against three halves


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_heard_from_ignores_civs_out_of_contact(seed: int) -> None:
    state = new_game(load_content(), "rome_264", seed=seed)
    node_id, _ = _ready_unknown(state, "steward")
    far = next(c for c in sorted(state.civs) if c != "rome" and relation(state, c, "rome") is None)
    state.civs[far].tech[node_id] = TechState(stage=Stage.ADOPTED)
    assert heard_from(state, "rome", node_id) is None


def test_counsel_names_the_neighbour_an_idea_comes_from() -> None:
    content = load_content()
    state = new_game(content, "rome_264", seed=1)
    for a in counsel(content, state):
        source = heard_from(state, "rome", a["node_id"])
        assert a["heard_from"] == (state.civs[source].name if source else "")


def test_counsel_is_deterministic() -> None:
    content = load_content()
    a = counsel(content, new_game(content, "rome_264", seed=3))
    b = counsel(content, new_game(content, "rome_264", seed=3))
    assert a == b

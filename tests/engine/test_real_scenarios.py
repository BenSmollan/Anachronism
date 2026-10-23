"""Every real-map scenario: historical populations stay sound over long games.

Scenario-specific facts are checked for the Punic Wars; the rest runs on every scenario
that sits on a real map, so new starting moments are tested as soon as they are written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.content.schema import RelationStatus
from anachronism.engine.bots import make_bot, play_turn
from anachronism.engine.economy import project_costs
from anachronism.engine.game import new_game, replay
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import GameState
from tests.engine.conftest import override_rules
from tests.engine.test_simulation import check_invariants

SCENARIO = "punic_wars"
REAL = sorted(s.id for s in load_content().scenarios.values() if s.map is not None)


def test_scenario_sits_on_the_real_map(content: Content) -> None:
    state = new_game(content, SCENARIO, seed=1)
    assert state.world.map == "europe"
    assert state.player_civ == "rome"
    assert state.year == content.scenarios[SCENARIO].start_year == -264
    assert all(g.latlon is not None for g in state.world.geography.values())
    assert state.world.seas, "seas touching the scenario's coasts are in play"
    assert 20_000_000 < sum(p.population for p in state.provinces.values()) < 40_000_000


def test_music_follows_the_scenario_and_the_civilisation(content: Content) -> None:
    assert new_game(content, "punic_wars", seed=1, player_civ="rome").world.music == "roman"
    carthage = new_game(content, "punic_wars", seed=1, player_civ="carthage")
    assert carthage.world.music == "near_east"


@pytest.mark.parametrize("scenario", REAL)
def test_every_music_track_exists(content: Content, scenario: str) -> None:
    music = Path(__file__).parents[2] / "client" / "music"
    start = content.scenarios[scenario]
    tracks = {start.music} | {civ.music for civ in start.civs.values()}
    assert start.music is not None, "real-map scenarios name their music"
    for track in sorted(t for t in tracks if t is not None):
        assert (music / f"{track}.mp3").is_file(), f"{scenario}: no client/music/{track}.mp3"


def test_cost_scale_multiplies_project_costs(content: Content) -> None:
    real = new_game(content, SCENARIO, seed=1)
    unscaled = real.model_copy(update={"world": real.world.model_copy(update={"cost_scale": 1})})
    scaled_cost = project_costs(real, "paper")
    base_cost = project_costs(unscaled, "paper")
    scale = real.world.cost_scale
    # The anachronism premium is rounded after scaling, so allow one unit per scale step.
    assert abs(scaled_cost.labour - base_cost.labour * scale) <= scale
    assert abs(scaled_cost.knowledge - base_cost.knowledge * scale) <= scale
    assert scaled_cost.labour > base_cost.labour


@pytest.mark.parametrize("scenario", REAL)
@pytest.mark.parametrize("bot", ["growth", "greedy"])
@pytest.mark.parametrize("seed", [1, 2])
def test_long_games_keep_every_invariant(
    content: Content, scenario: str, bot: str, seed: int
) -> None:
    state = new_game(content, scenario, seed)
    start_year = state.year
    bots = {civ_id: make_bot(bot) for civ_id in state.civs}
    for _ in range(30):
        state, _ = play_turn(state, bots)
        check_invariants(state, start_year)
    assert dumps(loads(dumps(state))) == dumps(state)


def test_careful_rome_is_stable_and_advances(content: Content) -> None:
    initial = new_game(content, SCENARIO, seed=3)
    bots = {civ_id: make_bot("idle") for civ_id in initial.civs}
    bots["rome"] = make_bot("growth")
    state = initial
    kinds: set[str] = set()
    for _ in range(30):
        state, events = play_turn(state, bots)
        kinds |= {e.kind for e in events if e.civ == "rome"}
    assert not {"riot", "revolt", "famine", "collapse"} & kinds
    adopted_now = sum(t.stage.is_adopted for t in state.civs["rome"].tech.values())
    adopted_then = sum(t.stage.is_adopted for t in initial.civs["rome"].tech.values())
    assert adopted_now >= adopted_then + 5
    assert state.population("rome") > initial.population("rome")


def peaceful(state: GameState) -> GameState:
    """The same world with no scripts, no wars and no chance events."""
    state.world = state.world.model_copy(update={"scripts": {}, "happenings": {}})
    # with no scripts every court acts on its temperament (D-116): no wars of ambition
    override_rules(state, rivals={"aggressive_war_chance_bp": 0})
    for rel in state.relations.values():
        if rel.status is RelationStatus.WAR:
            rel.status = RelationStatus.HOSTILE
    return state


@pytest.mark.parametrize("scenario", REAL)
def test_nobody_starves_when_left_alone(content: Content, scenario: str) -> None:
    """Content check: every state can feed its people (catches wrong terrain or capacity).

    Wars are switched off: this is about farmland, not about who conquers whom.
    """
    initial = peaceful(new_game(content, scenario, seed=5))
    bots = {civ_id: make_bot("idle") for civ_id in initial.civs}
    state = initial
    famines: set[str] = set()
    for _ in range(20):
        state, events = play_turn(state, bots)
        famines |= {e.civ for e in events if e.kind == "famine" and e.civ}
    assert not famines, f"famine in {sorted(famines)}"
    for civ_id in initial.civs:
        assert state.population(civ_id) >= initial.population(civ_id) * 0.9, civ_id


@pytest.mark.parametrize("scenario", REAL)
def test_games_replay_exactly(content: Content, scenario: str) -> None:
    initial = new_game(content, scenario, seed=9)
    bots = {civ_id: make_bot("growth") for civ_id in initial.civs}
    state = initial
    for _ in range(10):
        state, _ = play_turn(state, bots)
    assert dumps(replay(initial, state.action_log, until_turn=state.turn)) == dumps(state)

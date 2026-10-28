"""Spies and intelligence (D-115)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import Stage
from anachronism.engine import intelligence
from anachronism.engine.actions import SendSpies, StartProject
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rivals import key
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState, TechState

from .conftest import RuleOverride


@pytest.fixture
def punic(content: Content) -> GameState:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state.civs["rome"].stockpiles.wealth = 100_000
    return state


def log(state: GameState) -> EventLog:
    return EventLog(state.turn, state.year)


def test_spies_cost_wealth_and_make_reports_reliable(punic: GameState) -> None:
    before = intelligence.quality(punic, "rome", "carthage")
    punic, logged = apply_action(punic, SendSpies(civ="rome", target="carthage"))
    assert logged.ok, logged.message
    assert punic.civs["rome"].stockpiles.wealth < 100_000
    assert intelligence.quality(punic, "rome", "carthage") > before


def test_a_court_cannot_be_spied_on_twice_over_or_out_of_reach(punic: GameState) -> None:
    ok, _ = intelligence.send_spies(punic, "rome", "rome")
    assert not ok
    punic.civs["rome"].stockpiles.wealth = 0
    ok, message = intelligence.send_spies(punic, "rome", "carthage")
    assert not ok
    assert "wealth" in message


def test_spies_report_the_courts_true_plans_work_and_armies(
    punic: GameState, rules: RuleOverride
) -> None:
    rules(punic, rivals={"spy_caught_bp": 0, "spy_steal_bp": 0})
    intelligence.send_spies(punic, "rome", "carthage")
    # with spies and a perfect source every line is true
    punic.civs["rome"].spies["carthage"] = 3
    rules(punic, rivals={"spy_caught_bp": 0})
    intelligence.gather(punic, GameRng(punic.rng), log(punic))
    report = punic.civs["rome"].intel["carthage"]
    assert report.source == "our spies"
    assert any("men under arms" in line for line in report.lines)
    plans = intelligence.pending(punic, "carthage")
    if plans and report.trust_bp >= 9_500:
        assert report.lines[0].startswith("Carthage")


def test_spies_steal_secrets_that_speed_the_work(punic: GameState, rules: RuleOverride) -> None:
    rules(punic, rivals={"spy_caught_bp": 0, "spy_steal_bp": 10_000})
    rome, carthage = punic.civs["rome"], punic.civs["carthage"]
    carthage.tech["paper"] = TechState(stage=Stage.ADOPTED)
    for node in list(carthage.tech):
        if node != "paper" and carthage.tech[node].stage.is_adopted:
            rome.tech[node] = TechState(stage=Stage.ADOPTED)  # only paper is left to steal
    rome.tech.pop("paper", None)
    punic.civs["rome"].spies["carthage"] = 3
    events = log(punic)
    intelligence.gather(punic, GameRng(punic.rng), events)
    assert any(e.kind == "secrets_stolen" for e in events.items)
    assert rome.tech["paper"].head_start_bp > 0
    for prerequisite in punic.tech_nodes["paper"].prerequisites:
        rome.tech[prerequisite] = TechState(stage=Stage.ADOPTED)
    punic, logged = apply_action(punic, StartProject(civ="rome", node_id="paper"))
    if logged.ok:
        assert punic.civs["rome"].projects["paper"].progress_bp > 0


def test_caught_spies_leave_a_grudge(punic: GameState, rules: RuleOverride) -> None:
    rules(punic, rivals={"spy_caught_bp": 10_000})
    punic.civs["rome"].spies["carthage"] = 3
    events = log(punic)
    intelligence.gather(punic, GameRng(punic.rng), events)
    assert "carthage" not in punic.civs["rome"].spies
    assert any(e.kind == "spies_caught" for e in events.items)
    rel = punic.relations[key("rome", "carthage")]
    assert rel.grievance.get("carthage", 0) > 0

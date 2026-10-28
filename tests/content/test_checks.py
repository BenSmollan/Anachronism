"""Tests for the opt-in sourcing check."""

from __future__ import annotations

from anachronism.content.checks_sources import source_issues
from anachronism.content.loader import load_content
from anachronism.content.registry import Registry
from anachronism.content.schema import Scenario


def _sourcing(scenario: Scenario) -> list[str]:
    """Messages the sourcing check gives for this scenario alone."""
    registry = Registry()
    registry.scenarios[scenario.id] = scenario
    registry.origins[("scenarios", scenario.id)] = "europe/scenarios/x.yaml"
    return [i.message for i in source_issues(registry)]


def _scenario() -> Scenario:
    return next(iter(load_content().scenarios.values()))


def test_unflagged_scenario_needs_no_sources() -> None:
    scenario = _scenario()
    assert not scenario.sourced
    assert _sourcing(scenario) == []


def test_flagged_scenario_fails_on_unsourced_entry_and_passes_with_sources() -> None:
    scenario = _scenario()
    flagged = scenario.model_copy(update={"sourced": True})
    messages = _sourcing(flagged)
    assert messages, "an opted-in scenario with no sources must fail"
    assert any(civ_id in m for m in messages for civ_id in flagged.civs)

    cite = ("Polybius 1.7",)
    civs = {
        civ_id: civ.model_copy(
            update={
                "sources": cite,
                "generals": tuple(g.model_copy(update={"sources": cite}) for g in civ.generals),
                "successors": tuple(s.model_copy(update={"sources": cite}) for s in civ.successors),
                "scripts": tuple(s.model_copy(update={"sources": cite}) for s in civ.scripts),
            }
        )
        for civ_id, civ in flagged.civs.items()
    }
    relations = tuple(r.model_copy(update={"sources": cite}) for r in flagged.relations)
    sourced = flagged.model_copy(update={"civs": civs, "relations": relations})
    assert _sourcing(sourced) == []


def test_one_unsourced_entry_is_named() -> None:
    scenario = _scenario()
    cite = ("Livy 1.1",)
    civs = {
        civ_id: civ.model_copy(update={"sources": cite, "generals": (), "successors": ()})
        for civ_id, civ in scenario.civs.items()
    }
    civ_id = sorted(civs)[0]
    civs[civ_id] = civs[civ_id].model_copy(update={"sources": ()})
    flagged = scenario.model_copy(update={"sourced": True, "civs": civs, "relations": ()})
    # scripts are left as loaded: strip them so only the civ is unsourced
    civs = {k: v.model_copy(update={"scripts": ()}) for k, v in civs.items()}
    flagged = flagged.model_copy(update={"civs": civs})
    assert _sourcing(flagged) == [f"civ {civ_id!r} has no sources"]

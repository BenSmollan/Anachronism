"""Sourcing check: a scenario that sets ``sourced: true`` must cite a source for each entry.

Covers the entries the scenario file itself carries: each civ, its generals, successors and
scripts, and the starting relations. Provinces and chapters are not required to carry
sources here yet.
"""

from __future__ import annotations

from anachronism.content.issues import ContentIssue
from anachronism.content.registry import Registry
from anachronism.content.schema import Scenario


def unsourced_entries(scenario: Scenario) -> list[str]:
    """Describe each entry of the scenario that has no ``sources``, in a stable order."""
    missing: list[str] = []
    for civ_id, civ in sorted(scenario.civs.items()):
        if not civ.sources:
            missing.append(f"civ {civ_id!r} has no sources")
        for general in civ.generals:
            if not general.sources:
                missing.append(f"{civ_id}: general {general.name!r} has no sources")
        for successor in civ.successors:
            if not successor.sources:
                missing.append(f"{civ_id}: successor {successor.name!r} has no sources")
        for script in civ.scripts:
            if not script.sources:
                missing.append(f"{civ_id}: script {script.id!r} has no sources")
    for relation in scenario.relations:
        if not relation.sources:
            missing.append(f"relation {relation.a!r}/{relation.b!r} has no sources")
    return missing


def source_issues(registry: Registry) -> list[ContentIssue]:
    """Return an issue for every unsourced entry of every scenario that opted in."""
    issues: list[ContentIssue] = []
    for scenario in registry.scenarios.values():
        if not scenario.sourced:
            continue
        where = registry.origin("scenarios", scenario.id)
        label = f"scenarios ({scenario.id})"
        issues.extend(
            ContentIssue(where, label, message) for message in unsourced_entries(scenario)
        )
    return issues

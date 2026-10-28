"""Cross-reference checks across all loaded content (run after each file validated alone)."""

from __future__ import annotations

from collections.abc import Callable
from itertools import pairwise

from anachronism.content.checks_sources import source_issues
from anachronism.content.issues import ContentIssue
from anachronism.content.registry import Registry
from anachronism.content.schema import (
    MOMENTS,
    NUMERIC_EFFECTS,
    SPECIAL_SPEAKERS,
    EffectType,
    Scenario,
    ScriptGoal,
    Stage,
)


def cross_reference_issues(registry: Registry) -> list[ContentIssue]:
    """Return every broken reference or inconsistency between content files."""
    return [
        *_era_issues(registry),
        *_effect_cap_issues(registry),
        *_tech_issues(registry),
        *_province_issues(registry),
        *_sea_issues(registry),
        *_scenario_issues(registry),
        *_happening_issues(registry),
        *_unit_issues(registry),
        *_tale_issues(registry),
        *_dilemma_issues(registry),
        *_ship_issues(registry),
        *_building_issues(registry),
        *_tech_building_issues(registry),
        *_chapter_issues(registry),
        *_tactic_issues(registry),
        *_formation_issues(registry),
        *_symbol_issues(registry),
        *_dialogue_issues(registry),
        *source_issues(registry),
    ]


def _dialogue_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for moment in registry.dialogue.values():
        where = registry.origin("dialogue", moment.id)
        label = f"dialogue ({moment.id})"
        if moment.id not in MOMENTS:
            issues.append(ContentIssue(where, label, f"unknown moment (known: {sorted(MOMENTS)})"))
        if moment.speaker not in SPECIAL_SPEAKERS and registry.is_unknown(
            "speakers", moment.speaker
        ):
            issues.append(ContentIssue(where, label, f"unknown speaker {moment.speaker!r}"))
    return issues


def _era_issues(registry: Registry) -> list[ContentIssue]:
    if registry.eras is None:
        return []
    issues: list[ContentIssue] = []
    where = registry.origin("eras", "eras")
    ids = [era.id for era in registry.eras]
    if len(ids) != len(set(ids)):
        issues.append(ContentIssue(where, "eras", "era ids must be unique"))
    ends = [era.ends for era in registry.eras]
    if not ends or ends[-1] is not None:
        issues.append(ContentIssue(where, "eras", "the last era must have 'ends: null'"))
    bounded = [end for end in ends[:-1] if end is not None]
    if len(bounded) != len(ends[:-1]):
        issues.append(ContentIssue(where, "eras", "only the last era may have 'ends: null'"))
    elif any(later <= earlier for earlier, later in pairwise(bounded)):
        issues.append(ContentIssue(where, "eras", "era end years must strictly increase"))
    return issues


def _effect_cap_issues(registry: Registry) -> list[ContentIssue]:
    caps = registry.effect_caps
    if caps is None or registry.eras is None:
        return []
    issues: list[ContentIssue] = []
    where = registry.origin("effect_caps", "effect_caps")
    era_ids = {era.id for era in registry.eras}
    for effect in NUMERIC_EFFECTS:
        if effect not in caps:
            issues.append(ContentIssue(where, "effect_caps", f"missing caps for {effect}"))
    for effect, per_era in caps.items():
        if effect.is_unlock:
            issues.append(ContentIssue(where, f"effect_caps.{effect}", "unlocks have no caps"))
            continue
        if set(per_era) != era_ids:
            issues.append(
                ContentIssue(where, f"effect_caps.{effect}", f"needs exactly the eras {era_ids}")
            )
        if any(value <= 0 for value in per_era.values()):
            issues.append(ContentIssue(where, f"effect_caps.{effect}", "caps must be positive"))
    return issues


def _tech_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    techs = registry.techs
    for node in techs.values():
        where = registry.origin("techs", node.id)
        label = f"techs ({node.id})"
        for prerequisite in node.prerequisites:
            if registry.is_unknown("techs", prerequisite):
                issues.append(ContentIssue(where, label, f"unknown prerequisite {prerequisite!r}"))
        for infrastructure in node.requires.widespread:
            if registry.is_unknown("techs", infrastructure):
                issues.append(ContentIssue(where, label, f"unknown widespread {infrastructure!r}"))
        for material in node.requires.materials:
            if registry.is_unknown("resources", material):
                issues.append(ContentIssue(where, label, f"unknown material {material!r}"))
        for effect in node.effects:
            if effect.type is EffectType.UNLOCKS_RESOURCE and registry.is_unknown(
                "resources", effect.target
            ):
                issues.append(ContentIssue(where, label, f"unknown resource {effect.target!r}"))
    cycle = _find_prerequisite_cycle(registry)
    if cycle:
        where = registry.origin("techs", cycle[0])
        issues.append(ContentIssue(where, "techs", "prerequisite cycle: " + " -> ".join(cycle)))
    return issues


def _find_prerequisite_cycle(registry: Registry) -> list[str]:
    """Return one prerequisite cycle as a path (first id repeated at the end), or []."""
    done: set[str] = set()
    path: list[str] = []
    on_path: set[str] = set()

    def visit(node_id: str) -> list[str]:
        if node_id in on_path:
            return [*path[path.index(node_id) :], node_id]
        if node_id in done or node_id not in registry.techs:
            return []
        path.append(node_id)
        on_path.add(node_id)
        for prerequisite in sorted(registry.techs[node_id].prerequisites):
            cycle = visit(prerequisite)
            if cycle:
                return cycle
        path.pop()
        on_path.discard(node_id)
        done.add(node_id)
        return []

    for node_id in sorted(registry.techs):
        cycle = visit(node_id)
        if cycle:
            return cycle
    return []


def _province_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    provinces = registry.provinces
    for province in provinces.values():
        where = registry.origin("provinces", province.id)
        label = f"provinces ({province.id})"
        if registry.is_unknown("terrain", province.terrain):
            issues.append(ContentIssue(where, label, f"unknown terrain {province.terrain!r}"))
        for resource in province.resources:
            if registry.is_unknown("resources", resource):
                issues.append(ContentIssue(where, label, f"unknown resource {resource!r}"))
        for neighbour in province.neighbours:
            other = provinces.get(neighbour)
            if other is None:
                if registry.is_unknown("provinces", neighbour):
                    issues.append(ContentIssue(where, label, f"unknown neighbour {neighbour!r}"))
            elif province.id not in other.neighbours:
                issues.append(
                    ContentIssue(where, label, f"{neighbour!r} does not list it as a neighbour")
                )
    return issues


def _sea_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    shores: set[str] = set()
    for sea in registry.seas.values():
        where = registry.origin("seas", sea.id)
        for shore in sea.neighbours:
            shores.add(shore)
            if registry.is_unknown("provinces", shore):
                issues.append(
                    ContentIssue(where, f"seas ({sea.id})", f"unknown province {shore!r}")
                )
    if not registry.seas:
        return issues
    for province in registry.provinces.values():
        if province.coastal != (province.id in shores):
            where = registry.origin("provinces", province.id)
            state = (
                "is coastal but touches no sea"
                if province.coastal
                else "touches a sea but is not coastal"
            )
            issues.append(ContentIssue(where, f"provinces ({province.id})", state))
    return issues


def _scenario_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for scenario in registry.scenarios.values():
        where = registry.origin("scenarios", scenario.id)
        label = f"scenarios ({scenario.id})"

        def report(message: str, where: str = where, label: str = label) -> None:
            issues.append(ContentIssue(where, label, message))

        if scenario.player_civ not in scenario.civs:
            report(f"player civ {scenario.player_civ!r} is not in the scenario")
        for tech_id, stage in scenario.common_techs.items():
            common = registry.techs.get(tech_id)
            if common is None and registry.is_unknown("techs", tech_id):
                report(f"common_techs: unknown tech {tech_id!r}")
            elif common is not None and common.stub:
                report(f"common_techs: {tech_id!r} is a stub")
            if not stage.is_adopted:
                report(f"common_techs: {tech_id!r} must be adopted or widespread")
        claimed: dict[str, str] = {}
        for province in scenario.unowned:
            claimed[province] = "unowned"
        for civ_id, start in scenario.civs.items():
            if registry.is_unknown("civs", civ_id):
                report(f"unknown civ {civ_id!r}")
            if start.capital not in start.provinces:
                report(f"{civ_id}: capital {start.capital!r} is not one of its provinces")
            for province in start.provinces:
                if province in claimed:
                    report(f"province {province!r} is held by {claimed[province]} and {civ_id}")
                claimed[province] = civ_id
            needs = {n: set(t.prerequisites) for n, t in registry.techs.items()}
            starting = scenario.starting_techs(civ_id, needs)  # with the age's common ideas
            for tech_id, stage in start.techs.items():
                node = registry.techs.get(tech_id)
                if node is None:
                    if registry.is_unknown("techs", tech_id):
                        report(f"{civ_id}: unknown tech {tech_id!r}")
                    continue
                if node.stub:
                    report(f"{civ_id}: {tech_id!r} is a stub and cannot be a starting tech")
                if stage.is_adopted:
                    for prerequisite in node.prerequisites:
                        known = starting.get(prerequisite)
                        if known is None or not known.is_adopted:
                            report(
                                f"{civ_id}: {tech_id!r} is {stage} but its prerequisite "
                                f"{prerequisite!r} is not adopted"
                            )
                if stage is Stage.EXPERIMENTING:
                    report(f"{civ_id}: {tech_id!r} cannot start mid-experiment")
        _rival_issues(registry, scenario, report)
        for province in claimed:
            if registry.is_unknown("provinces", province):
                report(f"unknown province {province!r}")
            elif province in registry.provinces:
                geography = registry.provinces[province]
                if scenario.map is not None and geography.latlon is None:
                    report(f"province {province!r} has no latlon for the {scenario.map} map")
                elif scenario.map is None and geography.position is None:
                    report(f"province {province!r} has no map position")
    return issues


def _rival_issues(registry: Registry, scenario: Scenario, report: Callable[[str], None]) -> None:
    """Scripts and relations must name civilisations of the scenario and known ideas."""
    script_ids: set[str] = set()
    for start in scenario.civs.values():
        script_ids.update(script.id for script in start.scripts)
    seen: set[str] = set()
    for civ_id, start in scenario.civs.items():
        for script in start.scripts:
            if script.id in seen:
                report(f"{civ_id}: script {script.id!r} is defined twice")
            seen.add(script.id)
            if script.goal is ScriptGoal.ADOPT:
                if registry.is_unknown("techs", script.target):
                    report(f"{civ_id}: script {script.id!r} adopts unknown tech {script.target!r}")
            elif script.target not in scenario.civs or script.target == civ_id:
                report(f"{civ_id}: script {script.id!r} targets {script.target!r}: not a rival")
            for tech_id in script.preconditions.adopted:
                if registry.is_unknown("techs", tech_id):
                    report(f"{civ_id}: script {script.id!r} needs unknown tech {tech_id!r}")
            for dependency in script.depends_on:
                if dependency not in script_ids:
                    report(f"{civ_id}: script {script.id!r} depends on unknown {dependency!r}")
    held: dict[str, str] = {}
    for faith in scenario.faiths:
        for follower in faith.followers:
            if follower not in scenario.civs:
                report(f"faith {faith.id!r} names {follower!r}, not a civilisation of the scenario")
            elif follower in held:
                report(f"{follower!r} holds two faiths: {held[follower]!r} and {faith.id!r}")
            held[follower] = faith.id
    pairs: set[tuple[str, str]] = set()
    for relation in scenario.relations:
        for civ_id in (relation.a, relation.b):
            if civ_id not in scenario.civs:
                report(f"relation names {civ_id!r}, not a civilisation of the scenario")
        pair = (min(relation.a, relation.b), max(relation.a, relation.b))
        if pair in pairs:
            report(f"relation {pair[0]}-{pair[1]} is listed twice")
        pairs.add(pair)


def _happening_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for happening in registry.happenings.values():
        where = registry.origin("happenings", happening.id)
        label = f"happenings ({happening.id})"
        for terrain in happening.terrain:
            if registry.is_unknown("terrain", terrain):
                issues.append(ContentIssue(where, label, f"unknown terrain {terrain!r}"))
        for tech in happening.needs_adopted:
            if registry.is_unknown("techs", tech):
                issues.append(ContentIssue(where, label, f"unknown tech {tech!r}"))
        try:
            happening.message.format(civ="", province="")
        except (KeyError, IndexError, ValueError):
            issues.append(ContentIssue(where, label, "message may only use {civ} and {province}"))
    return issues


def _unit_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for unit in registry.units.values():
        where = registry.origin("units", unit.id)
        label = f"units ({unit.id})"
        for tech in unit.needs_techs:
            if registry.is_unknown("techs", tech):
                issues.append(ContentIssue(where, label, f"unknown tech {tech!r}"))
        for resource in unit.needs_resources:
            if registry.is_unknown("resources", resource):
                issues.append(ContentIssue(where, label, f"unknown resource {resource!r}"))
        for terrain in unit.terrain:
            if registry.is_unknown("terrain", terrain):
                issues.append(ContentIssue(where, label, f"unknown terrain {terrain!r}"))
    return issues


def _tale_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for tale in registry.tales.values():
        where = registry.origin("tales", tale.id)
        label = f"tales ({tale.id})"
        for terrain in tale.terrain:
            if registry.is_unknown("terrain", terrain):
                issues.append(ContentIssue(where, label, f"unknown terrain {terrain!r}"))
        for ship in tale.ships:
            if registry.is_unknown("ships", ship):
                issues.append(ContentIssue(where, label, f"unknown ship {ship!r}"))
        if tale.tactic and registry.is_unknown("tactics", tale.tactic):
            issues.append(ContentIssue(where, label, f"unknown battle plan {tale.tactic!r}"))
        if tale.sea and (tale.kind or tale.terrain):
            issues.append(ContentIssue(where, label, "a sea tale names ships, not soldiers"))
        for line in tale.lines:
            try:
                line.format(place="", winner="", loser="", unit="")
            except (KeyError, IndexError, ValueError):
                issues.append(
                    ContentIssue(where, label, "lines may use only {place} {winner} {loser} {unit}")
                )
    return issues


def _dilemma_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for dilemma in registry.dilemmas.values():
        where = registry.origin("dilemmas", dilemma.id)
        label = f"dilemmas ({dilemma.id})"

        def report(message: str) -> None:
            issues.append(ContentIssue(where, label, message))  # noqa: B023

        for scenario in dilemma.scenarios:
            if registry.is_unknown("scenarios", scenario):
                report(f"unknown scenario {scenario!r}")
        for civ in dilemma.civs:
            if registry.is_unknown("civs", civ):
                report(f"unknown civ {civ!r}")
        for tech in dilemma.needs_adopted:
            if registry.is_unknown("techs", tech):
                report(f"unknown tech {tech!r}")
        for choice in dilemma.choices:
            if choice.idea and registry.is_unknown("techs", choice.idea):
                report(f"unknown idea {choice.idea!r}")
        for text in (dilemma.text, *(c.outcome for c in dilemma.choices)):
            try:
                text.format(civ="", ruler="", adjective="")
            except (KeyError, IndexError, ValueError):
                report("texts may use only {civ} {ruler} {adjective}")
    return issues


def _symbol_issues(registry: Registry) -> list[ContentIssue]:
    return [
        ContentIssue(
            registry.origin("civs", civ.id), f"civs ({civ.id})", f"unknown symbol {civ.symbol!r}"
        )
        for civ in registry.civs.values()
        if civ.symbol and registry.is_unknown("symbols", civ.symbol)
    ]


def _tactic_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for tactic in registry.tactics.values():
        where = registry.origin("tactics", tactic.id)
        label = f"tactics ({tactic.id})"
        refs = [("tactics", b, "battle plan") for b in tactic.beats]
        refs += [("units", u, "unit") for u in tactic.needs_units]
        refs += [("terrain", t, "terrain") for t in (*tactic.needs_terrain, *tactic.terrain_bp)]
        for kind, ref, what in refs:
            if registry.is_unknown(kind, ref):
                issues.append(ContentIssue(where, label, f"unknown {what} {ref!r}"))
        for other in tactic.beats:
            beaten = registry.tactics.get(other)
            if beaten is not None and tactic.id in beaten.beats:
                issues.append(ContentIssue(where, label, f"{other!r} and it beat each other"))
    return issues


def _formation_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for form in registry.formations.values():
        where = registry.origin("formations", form.id)
        label = f"formations ({form.id})"
        for other in (*form.beats, *form.loses_to, *form.duel):
            if registry.is_unknown("formations", other):
                issues.append(ContentIssue(where, label, f"unknown formation {other!r}"))
        for other in form.beats:
            beaten = registry.formations.get(other)
            if beaten is not None and form.id in beaten.beats:
                issues.append(ContentIssue(where, label, f"{other!r} and it beat each other"))
        for other in form.loses_to:
            winner = registry.formations.get(other)
            if winner is not None and form.id not in winner.beats:
                issues.append(
                    ContentIssue(where, label, f"{other!r} is said to beat it but does not")
                )
    return issues


def _ship_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for ship in registry.ships.values():
        for tech in ship.needs_techs:
            if registry.is_unknown("techs", tech):
                where = registry.origin("ships", ship.id)
                issues.append(ContentIssue(where, f"ships ({ship.id})", f"unknown tech {tech!r}"))
    return issues


def _tech_building_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for node in registry.techs.values():
        for building in node.requires.buildings:
            if registry.is_unknown("buildings", building):
                where = registry.origin("techs", node.id)
                issues.append(
                    ContentIssue(where, f"techs ({node.id})", f"unknown building {building!r}")
                )
    return issues


def _building_issues(registry: Registry) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    for building in registry.buildings.values():
        where = registry.origin("buildings", building.id)
        label = f"buildings ({building.id})"
        for tech in building.needs_techs:
            if registry.is_unknown("techs", tech):
                issues.append(ContentIssue(where, label, f"unknown tech {tech!r}"))
        for resource in building.needs_resource:
            if registry.is_unknown("resources", resource):
                issues.append(ContentIssue(where, label, f"unknown resource {resource!r}"))
        if building.replaces is not None:
            if registry.is_unknown("buildings", building.replaces):
                issues.append(ContentIssue(where, label, f"unknown building {building.replaces!r}"))
            elif building.replaces == building.id:
                issues.append(ContentIssue(where, label, "a building cannot replace itself"))
    return issues


SPEAKER_KINDS = ("ruler",)


def _chapter_issues(registry: Registry) -> list[ContentIssue]:
    """Chronicle chapters (D-120) must name real scenarios, states, places and ideas."""
    issues: list[ContentIssue] = []
    for chapter in registry.chapters.values():
        where = registry.origin("chapters", chapter.id)
        label = f"chapters ({chapter.id})"

        def bad(message: str, where: str = where, label: str = label) -> None:
            issues.append(ContentIssue(where, label, message))

        scenario = registry.scenarios.get(chapter.scenario)
        if scenario is None:
            if registry.is_unknown("scenarios", chapter.scenario):
                bad(f"unknown scenario {chapter.scenario!r}")
            continue
        states = set(scenario.civs)
        places = {p for start in scenario.civs.values() for p in start.provinces}
        places |= set(scenario.unowned)
        if chapter.civ not in states:
            bad(f"{chapter.civ!r} is not a state in {chapter.scenario}")
        if not (
            chapter.speaker in SPEAKER_KINDS
            or chapter.speaker in registry.speakers
            or chapter.speaker in states
        ):
            bad(f"unknown speaker {chapter.speaker!r}")
        named_states = [
            *chapter.needs_alive,
            *chapter.needs_war_with,
            *chapter.needs_peace_with,
            *chapter.needs_stronger_than,
            *(o for o in (*chapter.needs_owner.values(), *chapter.needs_not_owner.values())),
        ]
        named_places = [*chapter.needs_owner, *chapter.needs_not_owner]
        for other in chapter.after + tuple(chapter.after_choice):
            if registry.is_unknown("chapters", other):
                bad(f"unknown chapter {other!r}")
        for choice in chapter.choices:
            deeds = choice.deeds
            named_states += [
                *deeds.war_with,
                *deeds.peace_with,
                *deeds.ally_with,
                *deeds.tributaries,
                *deeds.conquer,
                *deeds.grudges,
            ]
            if deeds.give_to:
                named_states.append(deeds.give_to)
            named_places += [*deeds.take, *deeds.give]
            for tech in (*choice.needs_adopted, *([choice.idea] if choice.idea else [])):
                if registry.is_unknown("techs", tech):
                    bad(f"unknown tech {tech!r}")
        for state in named_states:
            if state not in states and state != "nobody":
                bad(f"{state!r} is not a state in {chapter.scenario}")
        for place in named_places:
            if place not in places:
                bad(f"{place!r} is not a province in {chapter.scenario}")
    for entry in registry.almanac.values():
        scenario = registry.scenarios.get(entry.scenario)
        if scenario is None:
            continue
        for state in entry.needs_alive:
            if state not in scenario.civs:
                where = registry.origin("almanac", entry.id)
                issues.append(
                    ContentIssue(where, f"almanac ({entry.id})", f"{state!r} is not a state")
                )
    return issues

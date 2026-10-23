"""What the player's screen shows, as plain JSON-ready data built from the game state."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from anachronism.content.loader import Content
from anachronism.content.schema import Building, RelationStatus, Stage
from anachronism.engine.aid import gratitude, pledges_of
from anachronism.engine.armies import (
    STYLES,
    at_war_with,
    available_units,
    composition,
    mobilisation_cap,
    preview,
    raise_cost,
    route,
    under_arms,
    wall_cost,
    wall_tech,
)
from anachronism.engine.buildings import cost as building_cost
from anachronism.engine.buildings import options as building_options
from anachronism.engine.buildings import slots, worth
from anachronism.engine.commands import describe_blockers
from anachronism.engine.conquest import full_garrison, garrison_men, storm_outlook
from anachronism.engine.culture import tie_income, trade_income, tribute
from anachronism.engine.decrees import cost, explain_costs, explain_ready_in, news_on_the_road
from anachronism.engine.deployment import AUTO as DEPLOY_AUTO
from anachronism.engine.deployment import PLACE_NAMES, PLACE_NOTES, PLACES, SPLIT
from anachronism.engine.deployment import ordered as deploy_order
from anachronism.engine.deployment import resolved as deploy_resolved
from anachronism.engine.deployment import shares as deploy_shares
from anachronism.engine.dilemmas import effects_text, fill
from anachronism.engine.dynasty import remembered_in
from anachronism.engine.economy import project_costs, province_output
from anachronism.engine.effects import civ_effects
from anachronism.engine.fixed import BP
from anachronism.engine.formations import final as final_formation
from anachronism.engine.formations import lacks as formation_lacks
from anachronism.engine.formations import natural as formation_natural
from anachronism.engine.formations import ordered as formation_ordered
from anachronism.engine.navies import SIZES, best_ship, sea_links, sea_route, seas_of
from anachronism.engine.navies import power as sea_power
from anachronism.engine.occupation import garrisoned, restless
from anachronism.engine.offers import describe
from anachronism.engine.population import province_capacity
from anachronism.engine.projects import hasten_cost, project_turns
from anachronism.engine.reports import capacity
from anachronism.engine.rivals import at_war, overlord_of, relation, status, strength
from anachronism.engine.state import Army, Event, GameState
from anachronism.engine.suspicion import adoption_suspicion_bp
from anachronism.engine.tactics import AUTO, final, natural, needs_text, short_of_men
from anachronism.engine.tech import feasibility, is_adopted
from anachronism.engine.timeflow import per_turn, turns_for
from anachronism.engine.victory import progress
from anachronism.engine.war import defence_bp, fronts
from anachronism.tools.console import describe_effect

TRENDED = ("population", "food", "literacy_bp", "unrest_bp", "legitimacy_bp", "suspicion_bp")


def trend(state: GameState, civ_id: str, field: str) -> int:
    """1 if a value rose since last turn, -1 if it fell, 0 otherwise."""
    history = state.civs[civ_id].history
    if len(history) < 2:
        return 0
    now: int = getattr(history[-1], field)
    before: int = getattr(history[-2], field)
    return (now > before) - (now < before)


def build_view(state: GameState, events: list[Event] | None = None) -> dict[str, Any]:
    """Everything the client needs to draw the current turn for the player."""
    civ_id = state.player_civ
    civ = state.civs[civ_id]
    room = capacity(state, civ_id)
    strengths = {c: strength(state, c) for c in sorted(state.civs)}
    links = sea_links(state)
    return {
        "turn": state.turn + 1,
        "year": state.year,
        "years_per_turn": state.world.years_per_turn,
        "difficulty": state.world.difficulty,
        "scenario": state.world.scenario_name,
        "map": state.world.map,
        "music": state.world.music,
        "seed": state.seed,
        "player": civ_id,
        "status": {
            "name": civ.name,
            "ruler": civ.ruler,
            "ruler_age": civ.ruler_age,
            "faith": _faith_name(state, civ.faith),
            "faith_spreads": bool(civ.faith) and state.world.faiths[civ.faith].spreads,
            "mercenaries": civ.mercenaries,
            "festival_cost": cost(state, civ_id, state.world.rules.rivals.festival_wealth_per_1000),
            "mercenary_cost": cost(
                state, civ_id, state.world.rules.rivals.mercenary_wealth_per_1000
            ),
            "explain_costs": list(explain_costs(state, civ_id)),
            "explain_ready_in": explain_ready_in(state, civ_id),
            "sealed": civ.sealed,
            "seal_turns": state.world.rules.rivals.seal_turns,
            # D-278: what the decrees do, in numbers
            "festival_legitimacy_bp": state.world.rules.rivals.festival_legitimacy_bp,
            "festival_unrest_bp": state.world.rules.rivals.festival_unrest_bp,
            "mercenary_turns": state.world.rules.rivals.mercenary_turns,
            "mercenary_men": state.population(civ_id)
            * state.world.rules.armies.mercenary_men_bp
            // BP,
            "trade_total": trade_income(state, civ_id),
            "news_on_the_road": news_on_the_road(state, civ_id),
            "rumour_cost": cost(state, civ_id, state.world.rules.rivals.rumour_wealth_per_1000),
            "spy_cost": cost(state, civ_id, state.world.rules.rivals.spy_wealth_per_1000),
            "spy_turns": state.world.rules.rivals.spy_turns,
            "population": state.population(civ_id),
            "provinces": len(state.owned_provinces(civ_id)),
            # the time traveller's mark on history (D-126)
            "anachronisms": ahead_of_history(state, civ_id)[0],
            "years_ahead": ahead_of_history(state, civ_id)[1],
            **civ.stats.model_dump(),
            "framing": civ.framing.value,
            "collapsed": civ.collapsed,
            "dynasties": civ.dynasties,
            # fallen, but remembered: where the people may yet rise to restore the state
            "exile": [state.world.geography[p].name for p in remembered_in(state, civ_id)]
            if not state.owned_provinces(civ_id)
            else [],
            "stores": civ.stockpiles.model_dump(),
            "workforce": room.workforce,
            "free_labour": room.free_labour,
            "trends": {field: trend(state, civ_id, field) for field in TRENDED},
        },
        "civs": [
            {
                "id": other_id,
                "name": other.name,
                "colour": other.colour,
                "population": state.population(other_id),
                "provinces": len(state.owned_provinces(other_id)),
                "unrest_bp": other.stats.unrest_bp,
                "advances": sum(t.stage.is_adopted for t in other.tech.values()),
                "alive": bool(state.owned_provinces(other_id)),
                "adjective": other.adjective,
                "disposition": other.disposition.value,
                "ruler": other.ruler,
                "ruler_age": other.ruler_age,
                "faith": _faith_name(state, other.faith),
                "same_faith": bool(other.faith) and other.faith == civ.faith,
                "awareness": other.awareness.value,
                "strength": strengths[other_id],
                **_relation_to_player(state, other_id),
                **_intel(state, civ_id, other_id),
            }
            for other_id, other in sorted(state.civs.items())
        ],
        "wars": fronts(state),
        "armies": _armies(state),
        "tactics": _tactics(state),
        "formations": _formations(state),
        "deploy_places": _deploy_places(),
        "engage_rules": ENGAGE_RULES,
        "odds": _odds(state),
        "fleets": _fleets(state),
        "navy": _navy(state, civ_id),
        "dilemma": _dilemma(state),
        "offer": {
            "from": state.offer.from_civ,
            "kind": state.offer.kind,
            **describe(state, state.offer),
        }
        if state.offer
        else None,
        "levy": _levy(state, civ_id),
        "battles": _battle_sites(state, events or []),
        "sea_battles": _sea_battle_sites(state, events or []),
        "victory": {
            "paths": progress(state),
            "outcome": state.outcome.model_dump() if state.outcome else None,
        },
        "provinces": [
            {
                "id": pid,
                "name": geography.name,
                "terrain": geography.terrain,
                "river": geography.river,
                "coastal": geography.coastal,
                "position": list(geography.position) if geography.position else None,
                "latlon": list(geography.latlon) if geography.latlon else None,
                "neighbours": list(geography.neighbours),
                "owner": state.provinces[pid].owner,
                "population": state.provinces[pid].population,
                "resources": {
                    res: access.value for res, access in state.provinces[pid].resources.items()
                },
                "capital": any(c.capital == pid for c in state.civs.values()),
                "defence_bp": _defence(state, pid),
                "walls": state.provinces[pid].walls,
                "garrison": garrison_men(state, pid),
                "garrison_full": full_garrison(state, pid),
                **_people(state, pid),
                "ravaged": state.provinces[pid].ravaged,
                "port": next(iter(seas_of(state, pid)), None),
                "blockaded": state.provinces[pid].blockaded,
                **_walls_next(state, pid),
                **_buildings(state, pid),
            }
            for pid, geography in sorted(state.world.geography.items())
        ],
        "seas": [
            {
                "id": sid,
                "name": sea.name,
                "position": list(sea.position) if sea.position else None,
                "latlon": list(sea.latlon) if sea.latlon else None,
                "shores": sorted(p for p in sea.neighbours if p in state.provinces),
                "links": sorted(links[sid]),
                "command": _command_of(state, sid),
            }
            for sid, sea in sorted(state.world.seas.items())
        ],
        "projects": [
            {
                "id": node_id,
                "name": state.tech_nodes[node_id].name,
                "progress_bp": project.progress_bp,
                "funding_bp": project.last_funding_bp,
                "priority": project.priority.value,
                "paused": project.paused,
                "turns": project_turns(state, node_id),
                "hasten": asdict(hasten_cost(state, node_id)),
                "hastened": project.hastened_turn == state.turn,
            }
            for node_id, project in sorted(civ.projects.items())
        ],
        "ideas": _ideas(state, civ_id),
        "events": [
            {
                "civ": e.civ,
                "kind": e.kind,
                "message": e.message,
                **(
                    {
                        "phases": e.phases,
                        "sides": e.sides,
                        "ground": e.ground,
                        "target": e.subject,
                    }
                    if e.phases
                    else {}
                ),
                **({"spoils": e.spoils} if e.spoils else {}),
            }
            for e in (events or [])
            if e.civ == civ_id or e.kind in ("revolt", "collapse", "destroyed")
        ],
    }


def _intel(state: GameState, me: str, court: str) -> dict[str, Any]:
    """What the player knows of a court's plans, who says so, and the spies there (D-115)."""
    report = state.civs[me].intel.get(court)
    return {
        "intel": {
            "turn": report.turn,
            "source": report.source,
            "lines": list(report.lines),
            "trust_bp": report.trust_bp,
        }
        if report is not None and court != me
        else None,
        "spies": state.civs[me].spies.get(court, 0),
    }


def _defence(state: GameState, province_id: str) -> int:
    """How hard the province is to take from its holder (terrain, walls, last stand)."""
    owner = state.provinces[province_id].owner
    if owner is None:
        terrain = state.world.terrain[state.world.geography[province_id].terrain]
        return terrain.defence_bp
    return defence_bp(state, owner, province_id)


def next_steps(state: GameState, civ_id: str, node_id: str, limit: int = 3) -> list[dict[str, str]]:
    """The first ideas on the road to a blocked one that can be started now.

    Walks back through prerequisites not yet in use, nearest first, and keeps those whose
    own needs are met, so a ruling can offer "Begin" on the next step.
    """
    civ = state.civs[civ_id]
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    queue = list(state.tech_nodes[node_id].prerequisites) if node_id in state.tech_nodes else []
    while queue and len(found) < limit:
        current = queue.pop(0)
        if current in seen or current not in state.tech_nodes:
            continue
        seen.add(current)
        known = civ.tech.get(current)
        if known is not None and known.stage is not Stage.CONCEPT:
            continue  # in use, or already being tried
        if feasibility(state, civ_id, current).blocked:
            queue.extend(sorted(state.tech_nodes[current].prerequisites))
        else:
            found.append({"id": current, "name": state.tech_nodes[current].name})
    return found


def ahead_of_history(state: GameState, civ_id: str) -> tuple[int, int]:
    """Ideas brought in before their time, and by how many years in all (D-126)."""
    count = years = 0
    for node_id, tech in sorted(state.civs[civ_id].tech.items()):
        node = state.tech_nodes.get(node_id)
        if node is None or tech.adopted_year is None or not tech.stage.is_adopted:
            continue
        if node.year > tech.adopted_year:
            count += 1
            years += node.year - tech.adopted_year
    return count, years


def _ideas(state: GameState, civ_id: str) -> list[dict[str, Any]]:
    """Every idea the player could see, with what each needs.

    Known ones, those ready to start, and everything from the future the player remembers
    (the notebook, D-126).
    """
    civ = state.civs[civ_id]
    free = max(1, capacity(state, civ_id).free_labour)
    ideas = []
    for node_id, node in sorted(state.tech_nodes.items(), key=lambda item: item[1].name):
        known = civ.tech.get(node_id)
        result = feasibility(state, civ_id, node_id)
        future = node.year > state.year
        if known is None and result.blocked and not future:
            continue
        cost = project_costs(state, node_id)
        thieves = sorted(
            state.civs[other].name
            for other in state.civs
            if other != civ_id
            and node_id in state.civs[other].tech
            and state.civs[other].tech[node_id].stolen
        )
        ideas.append(
            {
                "id": node_id,
                "name": node.name,
                "category": node.category.value,
                "year": node.year,
                "ahead": node.year - state.year,
                "complexity": node.complexity,
                "flavour": node.flavour,
                "history": node.history,
                "stage": known.stage.value if known else None,
                "adopted_year": known.adopted_year if known else None,
                "goal": bool(known and known.goal),
                "stub": node.stub,
                "provenance": node.provenance.value,
                "spread_bp": known.spread_bp if known else 0,
                "ready": not result.blocked and not (known and known.stage is not Stage.CONCEPT),
                "blockers": describe_blockers(state, result) if result.blocked else "",
                "needs": [
                    {
                        "id": p,
                        "name": state.tech_nodes[p].name if p in state.tech_nodes else p,
                        "have": is_adopted(civ, p),
                    }
                    for p in node.prerequisites
                ],
                "cost": {
                    "labour": cost.labour,
                    "materials": cost.materials,
                    "knowledge": cost.knowledge,
                    "wealth": cost.wealth,
                },
                "labour_share": min(999, cost.labour * 100 // free),
                "suspicion": adoption_suspicion_bp(state, node) // 100,
                "stolen_by": thieves,
                "turns": project_turns(state, node_id),
                "effects": [
                    {
                        "type": e.type.value,
                        "bp": e.bp,
                        "target": e.target,
                        "text": describe_effect(e.type, e.bp, e.target),
                    }
                    for e in node.effects
                ],
            }
        )
    return ideas


def _people(state: GameState, province_id: str) -> dict[str, Any]:
    """Whose people live in a conquered province, and what holding it down takes."""
    if not restless(state, province_id):
        return {}
    province = state.provinces[province_id]
    people = state.civs.get(province.people or "")
    years = (state.turn - province.held_since) * state.world.years_per_turn
    rules = state.world.rules.armies
    return {
        "people": people.adjective if people else "",
        "conquered_years": years,
        "assimilate_in": max(0, rules.assimilation_years - years),
        "garrison_need": province.population // rules.garrison_people_per_man,
        "garrisoned": garrisoned(state, province_id),
    }


def _dilemma(state: GameState) -> dict[str, Any] | None:
    """The question waiting for the player's answer, if any."""
    dilemma = state.world.dilemmas.get(state.dilemma or "")
    if dilemma is None:
        return None
    return {
        "id": dilemma.id,
        "title": dilemma.title,
        "text": fill(state, dilemma.text),
        "choices": [{"label": c.label, "hint": effects_text(c)} for c in dilemma.choices],
    }


_BONUS_WORDS = (
    ("food_bp", "food"),
    ("materials_bp", "materials"),
    ("wealth_bp", "wealth"),
    ("knowledge_bp", "knowledge"),
    ("growth_bp", "growth"),
    ("capacity_bp", "room for people"),
)


def building_effects(kind: Building) -> str:
    """What a building does, in a few words (e.g. "+15% wealth, calms the realm")."""
    parts = [
        f"+{getattr(kind, name) // 100}% {word}"
        for name, word in _BONUS_WORDS
        if getattr(kind, name)
    ]
    if kind.calm_bp:
        parts.append("calms the realm")
    if kind.literacy_bp:
        parts.append("teaches reading")
    if kind.veterans_bp:
        parts.append("trains soldiers")
    return ", ".join(parts)


TIERS = ("Village", "Town", "City", "Great city", "Metropolis")
_TIER_POINTS = (0, 2, 4, 7, 10)


def city_tier(population: int, buildings: int) -> int:
    """How grown a province's chief city is (D-127): its people and its buildings."""
    points = buildings + population // 250_000
    return max(i for i, need in enumerate(_TIER_POINTS) if points >= need)


def _gains(state: GameState, province_id: str, kind: Building, now: Any, then: Any) -> list[str]:
    """What a building would add here, in plain numbers."""
    out = [
        f"+{then_value - now_value:,} {word} a turn"
        for word, now_value, then_value in (
            ("food", now.food, then.food),
            ("materials", now.materials, then.materials),
            ("wealth", now.wealth, then.wealth),
            ("knowledge", now.knowledge, then.knowledge),
        )
        if then_value > now_value
    ]
    if kind.growth_bp:
        out.append(f"its people grow {kind.growth_bp // 100}% faster")
    if kind.capacity_bp:
        room = province_capacity(state, province_id, None) * kind.capacity_bp // BP
        out.append(f"room for {room:,} more people")
    if kind.calm_bp:
        out.append("calms the realm")
    if kind.literacy_bp:
        out.append("teaches reading")
    if kind.veterans_bp:
        out.append(f"soldiers raised here start {kind.veterans_bp // 100}% seasoned")
    return out


def _buildings(state: GameState, province_id: str) -> dict[str, Any]:
    """What stands in a province, what is going up, and (for yours) what could be built.

    For the player's own provinces (D-127): how grown the city is, what it makes each turn,
    when its next building plot opens, and for each building it could raise what it would
    add here in plain numbers, what it costs to keep, and which is the best value.
    """
    province = state.provinces[province_id]
    kinds = state.world.buildings
    tier = city_tier(province.population, len(province.buildings))
    out: dict[str, Any] = {
        "buildings": [
            {
                "id": b,
                "name": kinds[b].name,
                "look": kinds[b].look,
                "does": building_effects(kinds[b]),
            }
            for b in province.buildings
            if b in kinds
        ],
        "works": {
            "id": province.works.building,
            "name": kinds[province.works.building].name,
            "look": kinds[province.works.building].look,
            "turns": province.works.turns_left,
        }
        if province.works is not None and province.works.building in kinds
        else None,
        "slots": slots(state, province_id),
        "queue": [{"id": b, "name": kinds[b].name} for b in province.queue if b in kinds],
        "tier": tier,
        "tier_name": TIERS[tier],
    }
    if province.owner == state.player_civ:
        me = state.player_civ
        effects = civ_effects(state, me)
        now = province_output(state, me, province_id, effects)
        out["output"] = asdict(now)
        rules = state.world.rules.buildings
        if out["slots"] < rules.max_slots:
            out["next_slot_at"] = (out["slots"] - rules.base_slots + 1) * rules.people_per_slot
        unrest = state.civs[me].stats.unrest_bp
        options: list[dict[str, Any]] = []
        busy = province.works is not None  # then the options are for the queue (D-128)
        skip = ("already built here", "a better one already stands here", "already planned here")
        for kind, reason in building_options(state, me, province_id, planning=busy):
            if reason in skip:
                continue
            materials, wealth = building_cost(state, province_id, kind.id)
            then = province_output(state, me, province_id, effects, kind.id)
            options.append(
                {
                    "id": kind.id,
                    "name": kind.name,
                    "look": kind.look,
                    "note": kind.note,
                    "does": building_effects(kind),
                    "gains": _gains(state, province_id, kind, now, then),
                    "upkeep": per_turn(state, kind.upkeep * state.world.cost_scale),
                    "replaces": kinds[kind.replaces].name if kind.replaces in kinds else "",
                    "materials": materials,
                    "wealth": wealth,
                    "turns": turns_for(state, kind.decades),
                    "why_not": reason,
                    "value": worth(kind, unrest) * 1000 // max(1, materials + wealth),
                }
            )
        # what can be built first, best value first; then what is nearly in reach
        options.sort(key=lambda o: (o["why_not"] is not None, -o["value"], o["name"]))
        ready = [o for o in options if o["why_not"] is None]
        for o in options:
            o["recommended"] = bool(ready) and o is ready[0]
        out["can_build"] = options
    return out


def _walls_next(state: GameState, province_id: str) -> dict[str, Any]:
    """What the next level of walls here would cost and need (for the player's provinces)."""
    if state.provinces[province_id].owner != state.player_civ:
        return {}
    needed = wall_tech(state, province_id)
    if needed is None:
        return {"wall_next": None}
    materials, wealth = wall_cost(state, province_id)
    node = state.tech_nodes.get(needed)
    ready = node is None or is_adopted(state.civs[state.player_civ], needed)
    return {
        "wall_next": {
            "materials": materials,
            "wealth": wealth,
            "needs": "" if ready else (node.name if node else needed),
        }
    }


ENGAGE_RULES = [
    {"id": "fight", "name": "Fight", "note": "Meet the enemy and fight it out."},
    {
        "id": "cautious",
        "name": "Cautious",
        "note": "Fall back from a battle it expects to lose (never from behind walls).",
    },
    {
        "id": "last_man",
        "name": "To the last man",
        "note": "Never gives way: hits harder, but loses far more if beaten.",
    },
]
"""The rules of engagement an army may be given."""


def _visible(state: GameState, army: Army) -> bool:
    """True when the player can see an army closely.

    It is the player's own (or an ally's), on or beside the player's land, or beside one of
    the player's armies.
    """
    me = state.player_civ
    if army.owner == me:
        return True
    if status(state, me, army.owner) is RelationStatus.ALLIED:
        return True
    here = {army.province, *state.world.geography[army.province].neighbours}
    if any(state.provinces[p].owner == me for p in here if p in state.provinces):
        return True
    return any(a.owner == me and a.province in here for a in state.armies.values())


def _fogged(state: GameState, men: int) -> int:
    """Men as a distant scout reports them: to the nearest few thousand."""
    unit = state.world.rules.armies.fog_round_men
    return max(unit, (men + unit // 2) // unit * unit)


def _armies(state: GameState) -> list[dict[str, Any]]:
    """Every army in the field: where, who, how many, and where it is going.

    Rival armies the player cannot see closely are reported rounded (``men_exact`` false).
    """
    out = []
    for army_id, army in sorted(state.armies.items()):
        owner = state.provinces[army.province].owner
        besieged = owner is not None and army.siege_bp > 0
        men = army.men
        seen = _visible(state, army)
        shown = men if seen else _fogged(state, men)
        out.append(
            {
                "id": army_id,
                "owner": army.owner,
                "name": army.name,
                "province": army.province,
                "men": shown,
                "men_exact": seen,
                "troops": [
                    {"unit": u, "name": state.world.units[u].name, "men": n * shown // max(1, men)}
                    for u, n in sorted(army.troops.items(), key=lambda item: -item[1])
                ],
                "morale_bp": army.morale_bp,
                "general": army.general,
                "skill": army.skill,
                "trait": army.trait,
                "mercenary": army.contract > 0,
                "target": army.target,
                "route": route(state, army.owner, army.province, army.target)
                if army.target
                else [],
                "stance": army.stance,
                **_plan(state, army),
                **_formation(state, army),
                **_deployment(state, army),
                "engage": army.engage,
                "dug_in": army.dug_in,
                "forced": army.forced,
                "veterancy_bp": army.veterancy_bp,
                "siege_bp": army.siege_bp,
                "siege_needed": defence_bp(state, owner, army.province)
                if besieged and owner
                else 0,
                "assault": army.assault,
                "storm": _storm(state, army),
            }
        )
    return out


def _storm(state: GameState, army: Army) -> dict[str, Any] | None:
    """For the player's army before an enemy city (D-273): its garrison and a storm's odds."""
    owner = state.provinces[army.province].owner
    if army.owner != state.player_civ or owner is None or owner == army.owner:
        return None
    if not at_war_with(state, army.owner, owner):
        return None
    return storm_outlook(state, army)


def _foe(state: GameState, army: Army) -> Army | None:
    """The enemy army this one would most likely meet (the player's, for a rival army)."""
    if army.owner != state.player_civ:
        return _nearest(state, army)
    near = {army.province, *state.world.geography[army.province].neighbours}
    foes = [a for a in state.armies.values() if at_war_with(state, army.owner, a.owner)]
    return min(
        foes,
        key=lambda a: (a.province != army.province, a.province not in near, -a.men, a.id),
        default=None,
    )


def _formation(state: GameState, army: Army) -> dict[str, Any]:
    """An army's formation: ordered, likely against its foe and (if yours) what is possible."""
    foe = _foe(state, army)
    out: dict[str, Any] = {
        "formation": army.formation,
        "formation_reads": army.formation == AUTO
        and army.skill >= state.world.rules.armies.reads_enemy_skill,
    }
    terrain = state.world.geography[army.province].terrain
    likely = final_formation(state, [army], [foe], terrain) if foe is not None else None
    out["formation_likely"] = {"id": likely.id, "name": likely.name} if likely else None
    if army.owner == state.player_civ:
        against = [foe] if foe is not None else []
        out["formation_options"] = [
            {
                "id": fid,
                "name": f.name,
                "description": f.description,
                "ok": not (why := formation_lacks(f, [army], against, terrain)),
                "lacking": why,
            }
            for fid, f in sorted(state.world.formations.items())
        ]
    return out


KIND_NAMES = {
    "infantry": "Infantry",
    "spear": "Spearmen",
    "missile": "Missile troops",
    "mounted": "Horse",
    "elephant": "Elephants",
    "siege": "Siege engines",
}


def _deploy_places() -> list[dict[str, str]]:
    """The places a kind of soldier can be ordered to (for the deployment picker)."""
    return [
        {"id": pid, "name": PLACE_NAMES[pid], "note": PLACE_NOTES[pid]}
        for pid in (DEPLOY_AUTO, *PLACES, SPLIT)
    ]


def _deployment(state: GameState, army: Army) -> dict[str, Any]:
    """How an army's kinds of soldier stand (D-270): yours show where, with auto resolved.

    ``deployment`` maps each kind present to ``place`` (left, centre, right, reserve, split,
    or camp for siege engines), ``auto`` (the formation decides) and ``shares`` (bp by place).
    """
    men: dict[str, int] = {}
    for unit_id, n in army.troops.items():
        found: str = state.world.units[unit_id].kind
        men[found] = men.get(found, 0) + n
    out: dict[str, Any] = {
        "kinds": [
            {"kind": k, "name": KIND_NAMES.get(k, k.title()), "men": n}
            for k, n in sorted(men.items(), key=lambda item: (-item[1], item[0]))
        ]
    }
    if army.owner != state.player_civ:
        return out
    foe = _foe(state, army)
    terrain = state.world.geography[army.province].terrain
    if foe is not None:
        form = final_formation(state, [army], [foe], terrain)
    else:  # nobody to read: the ruler's order, or what the general would naturally draw up
        form = formation_ordered(state, [army]) or formation_natural(state, [army], [], terrain)
    deployment: dict[str, Any] = {}
    for kind in sorted(men):
        order = deploy_order(army, kind)
        want = deploy_shares(form, kind, order)
        deployment[kind] = {
            "place": deploy_resolved(want),
            "auto": order == DEPLOY_AUTO,
            "shares": want,
        }
    out["deployment"] = deployment
    return out


def _formations(state: GameState) -> list[dict[str, Any]]:
    """The formations, what each beats and what beats it, for the formation picker."""
    forms = state.world.formations
    return [
        {
            "id": fid,
            "name": f.name,
            "description": f.description,
            "beats": [forms[b].name for b in f.beats if b in forms],
            "beaten_by": [o.name for _, o in sorted(forms.items()) if fid in o.beats],
            "equal_to": [forms[d].name for d in f.duel if d in forms],
            "edge_bp": f.edge_bp,
            "needs_ratio_bp": f.needs_ratio_bp,
        }
        for fid, f in sorted(forms.items())
    ]


def _odds(state: GameState) -> list[dict[str, Any]]:
    """The player's armies against enemy armies in or beside their province.

    ``win_bp`` is their share of the two sides' strength (5_000 even), counting plans,
    formations, camps and rules of engagement.
    """
    out = []
    for mine in sorted(state.armies.values(), key=lambda a: a.id):
        if mine.owner != state.player_civ:
            continue
        near = {mine.province, *state.world.geography[mine.province].neighbours}
        for foe in sorted(state.armies.values(), key=lambda a: a.id):
            if foe.province not in near or not at_war_with(state, mine.owner, foe.owner):
                continue
            holder = state.provinces[foe.province].owner
            attacking = holder != mine.owner
            if foe.province != mine.province:
                attacking = True
            outlook = preview(state, [mine], [foe], foe.province, attacking)
            share = int(outlook["win_bp"])
            if not _visible(state, foe):
                share = (share + 250) // 500 * 500
            out.append(
                {
                    "mine": mine.id,
                    "theirs": foe.id,
                    "province": foe.province,
                    "win_bp": share,
                    "wings": outlook["wings"],
                    "ground": outlook["ground"],
                }
            )
    return out


def _plan(state: GameState, army: Army) -> dict[str, Any]:
    """An army's battle plan: ordered, likely here, and (if yours) which its men cannot do.

    A rival army's likely plan is its answer to the nearest of the player's armies.
    """
    owner = state.provinces[army.province].owner
    attacking = owner is not None and owner != army.owner
    terrain = state.world.geography[army.province].terrain
    out: dict[str, Any] = {
        "plan": army.plan,
        "reads": army.plan == AUTO and army.skill >= state.world.rules.armies.reads_enemy_skill,
    }
    if army.owner == state.player_civ:
        likely = natural(state, [army], attacking, terrain)
        out["lacking"] = {
            tid: why
            for tid, tactic in sorted(state.world.tactics.items())
            if (why := short_of_men(state, tactic, [army]))
        }
    else:
        foe = _nearest(state, army)
        if foe is None:
            likely = natural(state, [army], attacking, terrain)
        else:
            likely = final(state, [army], [foe], attacking, terrain)
    out["likely"] = {"id": likely.id, "name": likely.name} if likely else None
    return out


def _nearest(state: GameState, army: Army) -> Army | None:
    """The player's army a rival army would most likely meet: here, next door, or the largest."""
    near = set(state.world.geography[army.province].neighbours)
    mine = [a for a in state.armies.values() if a.owner == state.player_civ]
    return min(
        mine,
        key=lambda a: (a.province != army.province, a.province not in near, -a.men, a.id),
        default=None,
    )


def _tactics(state: GameState) -> list[dict[str, Any]]:
    """The battle plans, what each beats and what beats it, for the plan picker."""
    tactics = state.world.tactics
    return [
        {
            "id": tid,
            "name": t.name,
            "note": t.note,
            "beats": [tactics[b].name for b in t.beats if b in tactics],
            "beaten_by": [o.name for _, o in sorted(tactics.items()) if tid in o.beats],
            "needs": needs_text(state, t),
        }
        for tid, t in sorted(tactics.items())
    ]


def _fleets(state: GameState) -> list[dict[str, Any]]:
    """Every fleet at sea: whose, where, how many ships, and where it is sailing."""
    out = []
    for fleet_id, fleet in sorted(state.fleets.items()):
        ship = state.world.ships[fleet.ship]
        out.append(
            {
                "id": fleet_id,
                "owner": fleet.owner,
                "name": fleet.name,
                "sea": fleet.sea,
                "ship": fleet.ship,
                "ship_name": ship.name,
                "ships": fleet.ships,
                "power": fleet.ships * ship.attack,
                "upkeep": fleet.ships * ship.upkeep_wealth // 10,
                "target": fleet.target,
                "route": sea_route(state, fleet.sea, fleet.target) if fleet.target else [],
            }
        )
    return out


def _navy(state: GameState, civ_id: str) -> dict[str, Any]:
    """What the player's shipyards can build: the best warship and what squadrons cost."""
    ship = best_ship(state, civ_id)
    if ship is None:
        sailing = state.tech_nodes.get("sailing")
        return {"ship": None, "needs": sailing.name if sailing else "Sailing"}
    return {
        "ship": ship.name,
        "ship_id": ship.id,
        "attack": ship.attack,
        "note": ship.note,
        "sizes": {
            size: {
                "ships": n,
                "materials": ship.materials * n,
                "wealth": ship.wealth * n,
                "upkeep": n * ship.upkeep_wealth // 10,
            }
            for size, n in SIZES.items()
        },
    }


def _command_of(state: GameState, sea: str) -> str | None:
    """Who commands a sea: the owner of the most naval power there, if anyone's ships are."""
    owners = sorted({f.owner for f in state.fleets.values() if f.sea == sea})
    if not owners:
        return None
    return max(owners, key=lambda o: (sea_power(state, o, sea), o))


def _levy(state: GameState, civ_id: str) -> dict[str, Any]:
    """What raising troops would give and cost: shares, styles and costs per 10,000 men."""
    rules = state.world.rules.armies
    styles = {}
    for style in STYLES:
        troops = composition(state, civ_id, 10_000, style)
        food, materials, wealth = raise_cost(state, troops)
        styles[style] = {
            "units": [state.world.units[u].name for u in troops],
            "food": food,
            "materials": materials,
            "wealth": wealth,
        }
    return {
        "martial_bp": state.civs[civ_id].martial_bp,
        "sizes": {
            "small": rules.raise_small_bp,
            "medium": rules.raise_medium_bp,
            "large": rules.raise_large_bp,
        },
        "styles": styles,
        "under_arms": under_arms(state, civ_id),
        "cap": mobilisation_cap(state, civ_id),
        "kinds": [u.name for u in available_units(state, civ_id)],
    }


def _battle_sites(state: GameState, events: list[Event]) -> list[str]:
    """Provinces where battles were fought in the last turn (for the crossed swords)."""
    by_name = {g.name.split(" (")[0]: pid for pid, g in state.world.geography.items()}
    return sorted(
        {by_name[e.subject] for e in events if e.kind == "battle_won" and e.subject in by_name}
    )


def _sea_battle_sites(state: GameState, events: list[Event]) -> list[str]:
    """Seas where fleets fought in the last turn."""
    by_name = {sea.name: sid for sid, sea in state.world.seas.items()}
    return sorted(
        {by_name[e.subject] for e in events if e.kind == "sea_battle_won" and e.subject in by_name}
    )


def _faith_name(state: GameState, faith_id: str) -> str:
    faith = state.world.faiths.get(faith_id)
    return faith.name if faith else ""


def _relation_to_player(state: GameState, other_id: str) -> dict[str, Any]:
    """How a civilisation stands with the player, for the World tab."""
    if other_id == state.player_civ:
        return {"relation": None, "grievance_bp": 0, "heard_of_you": []}
    rel = relation(state, state.player_civ, other_id)
    heard = [
        state.tech_nodes[h.node_id].name if not h.garbled else "strange rumours"
        for h in state.civs[other_id].heard
        if h.about == state.player_civ
    ]
    me = state.player_civ
    rules = state.world.rules.rivals
    return {
        "relation": rel.status.value if rel else None,
        "grievance_bp": rel.grievance.get(other_id, 0) if rel else 0,
        "heard_of_you": sorted(set(heard)),
        # D-277: who attacks it (the player may come to its aid), and the player's pledges
        "attacked_by": [
            {"id": foe, "name": state.civs[foe].name}
            for foe in at_war(state, other_id)
            if foe != me
        ],
        "aid": [
            {"against": p.against, "against_name": state.civs[p.against].name}
            for p in pledges_of(state, me, other_id)
        ],
        # D-278: what this tie is worth each turn: trade both ways, tribute one way
        "trade_income": tie_income(state, me, other_id),
        "tribute_in": tribute(state, other_id) if overlord_of(state, me, other_id) == me else 0,
        "tribute_if": tribute(state, other_id),
        "tribute_out": tribute(state, me) if overlord_of(state, me, other_id) == other_id else 0,
        "gratitude_bp": gratitude(state, me, other_id),
        "gratitude_warm_bp": rules.aid_warm_bp,
        "gratitude_alliance_bp": rules.aid_alliance_bp,
    }


def build_catalog(content: Content) -> list[dict[str, Any]]:
    """Every playable starting moment, for the civilisation picker (real-map scenarios)."""
    catalog: list[dict[str, Any]] = []
    for scenario_id, scenario in sorted(content.scenarios.items(), key=lambda s: s[1].start_year):
        civs: list[dict[str, Any]] = []
        for civ_id, start in scenario.civs.items():
            definition = content.civs[civ_id]
            civs.append(
                {
                    "id": civ_id,
                    "name": definition.name,
                    "adjective": definition.adjective,
                    "colour": definition.colour,
                    "description": definition.description,
                    "emblem": definition.emblem or definition.adjective[:1],
                    "symbol": definition.symbol or "",
                    "portrait": definition.portrait,
                    "leader": start.leader,
                    "pitch": start.pitch,
                    "population": sum(start.provinces.values()),
                    "provinces": len(start.provinces),
                    "capital": content.provinces[start.capital].name,
                    "advances": sum(stage.is_adopted for stage in start.techs.values()),
                    "literacy_bp": start.stats.literacy_bp,
                    # chronicle mode (D-120): how many chapters of history this state has
                    "chronicle": sum(
                        1
                        for c in content.chapters.values()
                        if c.scenario == scenario_id and c.civ == civ_id
                    ),
                }
            )
        civs.sort(key=lambda c: -sum(scenario.civs[c["id"]].provinces.values()))
        catalog.append(
            {
                "id": scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "start_year": scenario.start_year,
                "map": scenario.map,
                "default_civ": scenario.player_civ,
                "civs": civs,
            }
        )
    return catalog

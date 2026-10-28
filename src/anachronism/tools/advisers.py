"""The advisers' counsel: each recommends one idea a turn (DESIGN §14, brief §10).

The offline "Historical Advisors" way to play: instead of (or as well as) whispering ideas,
the player hears the steward, the general, the scholar and the diviner each recommend one
advancement within reach, chosen for what worries them now - thin granaries, an enemy at
the gates, restless streets. The choice is deterministic: it reads the game state only.
"""

from __future__ import annotations

from typing import Any

from anachronism.content.loader import Content
from anachronism.content.schema import EffectType, RelationStatus, Stage
from anachronism.engine.rivals import alive, at_war, relation, strength
from anachronism.engine.state import GameState
from anachronism.engine.tech import feasibility, is_adopted
from anachronism.tools.voices import speak

E = EffectType
CONCERNS: dict[str, dict[EffectType, int]] = {  # what each adviser values, per point of effect
    "steward": {E.FOOD_OUTPUT: 3, E.POPULATION_CAP: 2, E.STORAGE: 2, E.WEALTH_OUTPUT: 2,
                E.TRADE_INCOME: 2, E.MATERIALS_OUTPUT: 2, E.LABOUR_OUTPUT: 2},
    "general": {E.MILITARY_STRENGTH: 3, E.NAVAL_STRENGTH: 2, E.MOBILITY: 2},
    "scholar": {E.KNOWLEDGE_GAIN: 3, E.LITERACY_GROWTH: 3, E.INFORMATION_SPEED: 1,
                E.CULTURAL_INFLUENCE: 2},
    "diviner": {E.LEGITIMACY: 3, E.UNREST: -3, E.HEALTH: 2, E.SECRECY: 1},
}  # fmt: skip
REACH_YEARS = 200
"""How far ahead of their time advisers will look before an idea seems fantastical."""
HEARD_BONUS_NUM = 15
"""An idea a neighbour in contact already uses scores this many tenths (DEC018)."""
FAR_ONLY_DIV = 2
"""An old idea that no neighbour uses (known only far away) scores divided by this."""
UNLOCK_VALUE = {"general": (E.UNLOCKS_UNIT, 1500), "steward": (E.UNLOCKS_RESOURCE, 800)}


def _urgent(state: GameState, role: str) -> bool:
    """Is this adviser's worry pressing right now?"""
    me = state.player_civ
    civ = state.civs[me]
    if role == "steward":
        return civ.stockpiles.food * 10_000 < state.population(me) * 8
    if role == "general":
        if at_war(state, me):
            return True
        mine = strength(state, me)
        return any(
            (rel := relation(state, other, me)) is not None
            and rel.status is RelationStatus.HOSTILE
            and strength(state, other) > mine
            for other in sorted(state.civs)
            if other != me
        )
    if role == "diviner":
        return civ.stats.unrest_bp >= 3000 or civ.stats.suspicion_bp >= 2500
    return False


def heard_from(state: GameState, me: str, node_id: str) -> str | None:
    """The first civ (sorted ids) in contact with ``me`` that already uses ``node_id``."""
    for other in sorted(state.civs):
        if (
            other != me
            and alive(state, other)
            and relation(state, other, me) is not None
            and is_adopted(state.civs[other], node_id)
        ):
            return other
    return None


def _score(state: GameState, role: str, node_id: str, urgent: bool, heard: str | None) -> int:
    node = state.tech_nodes[node_id]
    score = 0
    for effect in node.effects:
        weight = CONCERNS[role].get(effect.type, 0)
        score += weight * effect.bp
        unlock = UNLOCK_VALUE.get(role)
        if unlock and effect.type is unlock[0]:
            score += unlock[1]
    if score <= 0:
        return 0
    ahead = node.year - state.year
    # Advisers think within their age: a step ahead pleases them, but what lies centuries
    # away is the ruler's own strange knowledge, not theirs to suggest.
    if 0 < ahead <= REACH_YEARS:
        score = score * 12 // 10
    elif ahead > REACH_YEARS:
        score = score * REACH_YEARS // ahead // 4
    # Romans borrow from the peoples they know (DEC018): what a neighbour already uses is
    # easy to argue for; an old idea known only at the far ends of the earth is not.
    if heard is not None:
        score = score * HEARD_BONUS_NUM // 10
    elif ahead <= 0:
        score = score // FAR_ONLY_DIV
    return score * (2 if urgent else 1)


def counsel(content: Content, state: GameState) -> list[dict[str, Any]]:
    """Up to four recommendations: who advises, what, and why (a speech line)."""
    me = state.player_civ
    civ = state.civs[me]
    ready = [
        node_id
        for node_id in sorted(state.tech_nodes)
        if not state.tech_nodes[node_id].stub
        and (civ.tech.get(node_id) is None or civ.tech[node_id].stage is Stage.CONCEPT)
        and node_id not in civ.projects
        and not feasibility(state, me, node_id).blocked
    ]
    heard = {node_id: heard_from(state, me, node_id) for node_id in ready}
    advice: list[dict[str, Any]] = []
    taken: set[str] = set()
    roles = sorted(CONCERNS, key=lambda r: (not _urgent(state, r), list(CONCERNS).index(r)))
    for role in roles:
        urgent = _urgent(state, role)
        scored = [(_score(state, role, n, urgent, heard[n]), n) for n in ready if n not in taken]
        scored = [(s, n) for s, n in scored if s > 0]
        if not scored:
            continue
        _, best = max(scored, key=lambda item: (item[0], -state.tech_nodes[item[1]].year))
        taken.add(best)
        moment = f"advise_{role}_urgent" if urgent else f"advise_{role}"
        if moment not in content.dialogue:
            moment = f"advise_{role}"
        voice = speak(content, state, moment, state.tech_nodes[best].name)
        if voice is None:
            continue
        ahead = state.tech_nodes[best].year - state.year
        source = heard[best]
        advice.append(
            {
                **voice,
                "role": role,
                "node_id": best,
                "urgent": urgent,
                "years_ahead": ahead,
                "heard_from": state.civs[source].name if source else "",
            }
        )
    return advice

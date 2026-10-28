"""Applying a ruling on the player's idea, after bounding everything in it (D-020).

Whatever produced the ruling (a model, the offline interpreter, a cached answer), this is
the last word: new advancements get complexity and year floors from their prerequisites,
effects are cut to the era's caps and the effect limit, unknown references are dropped, and
the advisers' nudges to unrest and suspicion are capped. Costs are never read from a
ruling: the engine derives them from complexity and year like any other advancement.
"""

from __future__ import annotations

from anachronism.content.schema import (
    EffectType,
    Provenance,
    Requirements,
    Stage,
    TechNode,
)
from anachronism.content.schema.tech import Effect
from anachronism.engine.fixed import BP, clamp
from anachronism.engine.rulings import Ruling, Verdict
from anachronism.engine.state import GameState, TechState
from anachronism.engine.tech import add_stub, propose
from anachronism.engine.timeflow import current_era


def bound_node(state: GameState, node: TechNode) -> TechNode:
    """A copy of a proposed new advancement with every number and reference bounded."""
    limits = state.world.rules.rulings
    era = current_era(state).id
    caps = state.world.effect_caps
    prerequisites = tuple(
        dict.fromkeys(p for p in node.prerequisites if p in state.tech_nodes and p != node.id)
    )[: limits.max_prerequisites]
    known = [state.tech_nodes[p] for p in prerequisites]
    complexity = node.complexity
    year = node.year
    if known:
        floor = max(k.complexity for k in known) - limits.min_complexity_per_prerequisite_tier
        complexity = max(complexity, floor)
        year = max(year, *(k.year for k in known))  # nothing arrives before what it needs
    effects: list[Effect] = []
    for effect in node.effects:
        if effect.type.is_unlock:
            continue  # buildings and units come from content, not from rulings
        cap = caps[effect.type][era] if effect.type in caps else 0
        if effect.type is EffectType.SUSPICION:
            bp = clamp(effect.bp, 0, limits.adviser_suspicion_bp)
        elif effect.type.may_be_negative:
            bp = clamp(effect.bp, -cap, cap)
        else:
            bp = clamp(effect.bp, 0, cap)
        if bp != 0 and all(e.type is not effect.type for e in effects):
            effects.append(Effect(type=effect.type, bp=bp))
    requires = Requirements(
        materials=tuple(m for m in node.requires.materials if m in state.world.resources),
        literacy_bp=node.requires.literacy_bp,
        widespread=tuple(w for w in node.requires.widespread if w in state.tech_nodes),
    )
    return node.model_copy(
        update={
            "complexity": clamp(complexity, 1, 5),
            "year": year,
            "prerequisites": prerequisites,
            "requires": requires,
            "effects": tuple(effects[: limits.max_effects]),
            "provenance": Provenance.PLAYER_IDEA,
            "stub": False,
            "sources": (),
        }
    )


def apply_ruling(state: GameState, civ_id: str, ruling: Ruling) -> tuple[bool, str]:
    """Carry out a ruling: add any new advancement and goal stubs, then consider the idea.

    Returns whether it was accepted and a message for the player.
    """
    civ = state.civs[civ_id]
    limits = state.world.rules.rulings
    civ.stats.unrest_bp = clamp(
        civ.stats.unrest_bp + min(ruling.unrest_bp, limits.adviser_unrest_bp), 0, BP
    )
    civ.stats.suspicion_bp = clamp(
        civ.stats.suspicion_bp + min(ruling.suspicion_bp, limits.adviser_suspicion_bp), 0, BP
    )
    if ruling.verdict is Verdict.IMPLAUSIBLE:
        return True, ruling.reason or "Your advisers cannot make sense of it yet."

    for spec in ruling.stubs[: limits.max_stubs]:
        stub = add_stub(state, spec.id, spec.name, spec.category)
        if spec.id not in civ.tech:
            civ.tech[stub.id] = TechState(stage=Stage.CONCEPT, goal=True)

    node_id = ruling.node_id
    if ruling.new_node is not None:
        existing = state.tech_nodes.get(ruling.new_node.id)
        if existing is None or existing.stub:
            node = bound_node(state, ruling.new_node)  # stubs above may be its prerequisites
            state.tech_nodes[node.id] = node
        node_id = ruling.new_node.id
    if node_id is None or node_id not in state.tech_nodes:
        return False, "the ruling names no advancement"
    node = state.tech_nodes[node_id]
    known = civ.tech.get(node_id)
    if known is not None and known.stage.is_adopted:
        return True, f"{node.name} is already in use."
    result = propose(state, civ_id, node_id)
    civ.tech[node_id].goal = False
    if result.blocked:
        missing = [
            state.tech_nodes[m].name
            for m in (*result.missing_prerequisites, *result.missing_widespread)
        ]
        materials = [state.world.resources[m].name for m in result.missing_materials]
        needs = ", ".join([*missing, *(f"access to {m}" for m in materials)])
        return True, f"{node.name} needs {needs} first." if needs else f"{node.name} is noted."
    return True, f"{node.name} could be attempted now."

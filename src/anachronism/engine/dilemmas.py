"""Dilemmas put to the ruler, and what each answer does (D-104).

At most one dilemma waits at a time. When the conditions of one hold, it may arise (on the
game's RNG, with its chance per decade); the player answers it with a ``ChooseDilemma``
action. A dilemma left unanswered when the turn ends is settled by the court: the first
choice is taken. Answers are recorded actions, so replays stay exact.
"""

from __future__ import annotations

from anachronism.content.schema import Choice, Dilemma, Stage
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP, apply_bp, clamp
from anachronism.engine.rivals import at_war
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState, TechState
from anachronism.engine.tech import is_adopted
from anachronism.engine.timeflow import per_turn


def fits(state: GameState, dilemma: Dilemma) -> bool:
    """True when a dilemma's conditions hold for the player now."""
    me = state.player_civ
    civ = state.civs[me]
    if dilemma.once and dilemma.id in state.dilemmas_seen:
        return False
    if dilemma.scenarios and state.world.scenario_id not in dilemma.scenarios:
        return False
    if dilemma.civs and me not in dilemma.civs:
        return False
    if dilemma.after_year is not None and state.year <= dilemma.after_year:
        return False
    if dilemma.before_year is not None and state.year >= dilemma.before_year:
        return False
    if any(not is_adopted(civ, t) for t in dilemma.needs_adopted):
        return False
    if dilemma.at_war is not None and bool(at_war(state, me)) != dilemma.at_war:
        return False
    stats = civ.stats
    return (
        stats.unrest_bp >= dilemma.min_unrest_bp
        and stats.suspicion_bp >= dilemma.min_suspicion_bp
        and stats.legitimacy_bp <= dilemma.max_legitimacy_bp
    )


def fill(state: GameState, text: str) -> str:
    """A dilemma's text with the player's names filled in."""
    civ = state.civs[state.player_civ]
    return text.format(
        civ=civ.name, ruler=civ.ruler or f"the ruler of {civ.name}", adjective=civ.adjective
    )


def effects_text(choice: Choice) -> str:
    """What a choice will do, in a few words (for the buttons' hints)."""
    parts = []
    for name, value in (
        ("food", choice.food_bp),
        ("materials", choice.materials_bp),
        ("wealth", choice.wealth_bp),
        ("knowledge", choice.knowledge_bp),
    ):
        if value:
            parts.append(f"{name} {value / 100:+.0f}%")
    for name, value in (
        ("unrest", choice.unrest_bp),
        ("legitimacy", choice.legitimacy_bp),
        ("suspicion", choice.suspicion_bp),
    ):
        if value:
            parts.append(f"{name} {value / 100:+.0f}")
    for group, value in sorted(choice.influence.items()):
        parts.append(f"{group.value} {value / 100:+.0f}")
    if choice.idea:
        parts.append("a new idea")
    if choice.volunteers_bp:
        parts.append("volunteers take up arms")
    return ", ".join(parts) or "no lasting effect"


def ask(state: GameState, rng: GameRng, events: EventLog) -> None:
    """Settle an unanswered dilemma, then perhaps raise a new one."""
    if state.dilemma is not None:
        dilemma = state.world.dilemmas.get(state.dilemma)
        state.dilemma = None
        if dilemma is not None:
            message = answer(state, dilemma, 0)
            events.add(
                state.player_civ,
                "dilemma_settled",
                f"Your advisers decided for you: {message}",
                dilemma.title,
            )
    for dilemma_id in sorted(state.world.dilemmas):
        dilemma = state.world.dilemmas[dilemma_id]
        if fits(state, dilemma) and rng.chance(per_turn(state, dilemma.chance_bp)):
            state.dilemma = dilemma_id
            state.dilemmas_seen.append(dilemma_id)
            events.add(state.player_civ, "dilemma", dilemma.title, dilemma.title)
            return


def answer(state: GameState, dilemma: Dilemma, index: int) -> str:
    """Apply one choice's consequences; returns what happened."""
    return apply_choice(state, dilemma.choices[index])


def apply_choice(state: GameState, choice: Choice) -> str:
    """A choice's consequences for the player's court (dilemmas and chapters alike)."""
    civ = state.civs[state.player_civ]
    stores = civ.stockpiles
    stores.food = max(0, stores.food + apply_bp(stores.food, choice.food_bp))
    stores.materials = max(0, stores.materials + apply_bp(stores.materials, choice.materials_bp))
    stores.wealth = max(0, stores.wealth + apply_bp(stores.wealth, choice.wealth_bp))
    stores.knowledge = max(0, stores.knowledge + apply_bp(stores.knowledge, choice.knowledge_bp))
    stats = civ.stats
    stats.unrest_bp = clamp(stats.unrest_bp + choice.unrest_bp, 0, BP)
    stats.legitimacy_bp = clamp(stats.legitimacy_bp + choice.legitimacy_bp, 0, BP)
    stats.suspicion_bp = clamp(stats.suspicion_bp + choice.suspicion_bp, 0, BP)
    for group, change in sorted(choice.influence.items()):
        civ.influence[group] = clamp(civ.influence.get(group, 0) + change, 0, BP)
    if choice.idea and choice.idea in state.tech_nodes and choice.idea not in civ.tech:
        civ.tech[choice.idea] = TechState(stage=Stage.CONCEPT)
    if choice.volunteers_bp and civ.capital in state.provinces:
        from anachronism.engine.armies import raise_army  # armies builds on much of the engine

        men = apply_bp(state.population(civ.id), choice.volunteers_bp)
        raise_army(state, civ.id, civ.capital, men, free=True)
    return fill(state, choice.outcome)

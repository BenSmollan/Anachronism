"""Royal decrees that spend the treasury: festivals, mercenaries and explanations.

Wealth builds up in a peaceful state; these give it uses with a price that grows with the
state's size, so a festival in a great empire costs more than in a small kingdom.
"""

from __future__ import annotations

from anachronism.engine.actions import (
    Decree,
    Explain,
    HireMercenaries,
    HoldFestival,
    SealBorders,
    SendSpies,
    SpreadRumours,
)
from anachronism.engine.fixed import BP, clamp, div_round
from anachronism.engine.state import Framing, GameState, NewsInTransit


def cost(state: GameState, civ_id: str, per_1000: int) -> int:
    """Wealth a decree costs: ``per_1000`` hundredths of a unit per 1,000 people."""
    return max(1, state.population(civ_id) // 1000 * per_1000 // 100)


def apply_decree(state: GameState, action: Decree) -> tuple[bool, str]:
    """Carry out a decree if the treasury allows."""
    civ = state.civs[action.civ]
    rules = state.world.rules.rivals
    if isinstance(action, HoldFestival):
        price = cost(state, civ.id, rules.festival_wealth_per_1000)
        if civ.stockpiles.wealth < price:
            return False, f"a festival needs {price} wealth"
        civ.stockpiles.wealth -= price
        civ.stats.legitimacy_bp = clamp(
            civ.stats.legitimacy_bp + rules.festival_legitimacy_bp, 0, BP
        )
        civ.stats.unrest_bp = clamp(civ.stats.unrest_bp - rules.festival_unrest_bp, 0, BP)
        return True, f"Feasts and games across {civ.name}: the people cheer their leaders."
    if isinstance(action, HireMercenaries):
        price = cost(state, civ.id, rules.mercenary_wealth_per_1000)
        if civ.stockpiles.wealth < price:
            return False, f"mercenaries want {price} wealth"
        if civ.mercenaries > 0:
            return False, "the mercenaries you hired are still serving"
        civ.stockpiles.wealth -= price
        civ.mercenaries = rules.mercenary_turns
        from anachronism.engine.armies import hire_company  # armies builds on the decrees

        company = hire_company(state, civ.id, rules.mercenary_turns)
        men = f"{company.men:,} " if company else ""
        return True, f"{men}hired swords muster at the capital for {rules.mercenary_turns} turns."
    if isinstance(action, Explain):
        return _explain(state, action)
    if isinstance(action, SealBorders):
        if civ.sealed:
            return False, "the borders are already sealed"
        civ.sealed = rules.seal_turns
        return True, (
            f"{civ.name} seals its borders for {rules.seal_turns} turns: the caravans stop, "
            "and word of our arts will crawl."
        )
    if isinstance(action, SpreadRumours):
        return _rumours(state, action)
    if isinstance(action, SendSpies):
        from anachronism.engine.intelligence import send_spies  # it builds on the decrees

        return send_spies(state, civ.id, action.target)
    raise AssertionError(f"unhandled decree {action!r}")


def explain_costs(state: GameState, civ_id: str) -> tuple[int, int]:
    """Wealth for a divine proclamation and knowledge for crediting foreign sages."""
    rules = state.world.rules.suspicion
    return (
        cost(state, civ_id, rules.explain_wealth_per_1000),
        cost(state, civ_id, rules.sages_knowledge_per_1000),
    )


def explain_ready_in(state: GameState, civ_id: str) -> int:
    """Turns until the court may explain itself again (0: now)."""
    since = state.turn - state.civs[civ_id].explained_turn
    return max(0, state.world.rules.suspicion.explain_cooldown_turns - since)


def _explain(state: GameState, action: Explain) -> tuple[bool, str]:
    civ = state.civs[action.civ]
    rules = state.world.rules.suspicion
    stats = civ.stats
    if stats.suspicion_bp <= 0:
        return False, "nobody is asking where your new arts come from"
    wait = explain_ready_in(state, civ.id)
    if wait:
        return False, f"the people heard your last story too recently ({wait} turn(s))"
    wealth, knowledge = explain_costs(state, civ.id)
    if action.story == "divine":
        if civ.stockpiles.wealth < wealth:
            return False, f"the temples want {wealth} wealth for the rites"
        civ.stockpiles.wealth -= wealth
        stats.suspicion_bp = max(0, stats.suspicion_bp - rules.explain_suspicion_bp)
        civ.explained_turn = state.turn
        believed = stats.legitimacy_bp >= rules.explain_belief_legitimacy_bp
        if believed and civ.framing in (Framing.WITCHCRAFT, Framing.FRAUD):
            civ.framing = Framing.INSPIRED
            return (
                True,
                f"Priests proclaim {civ.name}'s new arts a gift of the gods - "
                "and the people believe it.",
            )
        if believed:
            return (
                True,
                f"Priests proclaim {civ.name}'s new arts a gift of the gods. The talk quietens.",
            )
        return (
            True,
            "Priests proclaim the new arts divine. Some believe; the doubters only whisper lower.",
        )
    if civ.stockpiles.knowledge < knowledge:
        return False, f"crediting foreign sages takes {knowledge} knowledge"
    civ.stockpiles.knowledge -= knowledge
    stats.suspicion_bp = max(0, stats.suspicion_bp - rules.sages_suspicion_bp)
    civ.explained_turn = state.turn
    for news in state.news:  # the story travels: rivals learn of these arts at once
        if news.about == civ.id:
            news.arrives_turn = min(news.arrives_turn, state.turn + 1)
    return (
        True,
        f"Scholars of {civ.name} credit wise men from distant lands. Strangers' arts, not sorcery.",
    )


def news_on_the_road(state: GameState, civ_id: str) -> int:
    """How many courts have true word of ``civ_id``'s arts on its way to them."""
    return len({n.to_civ for n in state.news if n.about == civ_id and not n.garbled})


def _rumours(state: GameState, action: SpreadRumours) -> tuple[bool, str]:
    civ = state.civs[action.civ]
    rules = state.world.rules.rivals
    if not news_on_the_road(state, civ.id):
        return False, "no word of our arts is on the road to garble"
    price = cost(state, civ.id, rules.rumour_wealth_per_1000)
    if civ.stockpiles.wealth < price:
        return False, f"storytellers want {price} wealth"
    civ.stockpiles.wealth -= price
    clarify = max(1, div_round(rules.clarify_years, state.world.years_per_turn))
    truths: list[NewsInTransit] = []
    for news in state.news:
        if news.about == civ.id and not news.garbled:
            later = news.arrives_turn + clarify  # a muddle first, and the truth much later
            truths.append(news.model_copy(update={"arrives_turn": later}))
            news.garbled = True
    state.news.extend(truths)
    courts = len({n.to_civ for n in truths})
    return (
        True,
        f"Storytellers muddle the tales of {civ.name}'s arts on the road to {courts} court(s).",
    )

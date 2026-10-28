"""Trade and faith between states (brief §7.5: trade, religion and cultural flows).

- **Trade**: every friendly tie (trading, allied, tributary) earns both sides wealth each
  turn, in proportion to the smaller side's people.
- **Faith**: a spreading faith (Buddhism, the Christian churches, Islam) may cross to a
  neighbour of another faith each turn, more easily along friendly ties and from a state of
  great cultural influence. States of one faith forget old grudges faster. Missionaries
  (an action) try to convert a court directly.
"""

from __future__ import annotations

from anachronism.content.schema import EffectType
from anachronism.engine.effects import Effects
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP, apply_bp
from anachronism.engine.rivals import alive, overlord_of, status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import GameState
from anachronism.engine.timeflow import per_turn, rate_per_turn


def _tie_income(state: GameState, a: str, b: str) -> int:
    """What one friendly tie pays each side per turn, by the smaller side's people."""
    smaller = min(state.population(a), state.population(b))
    rules = state.world.rules.rivals
    income = per_turn(state, apply_bp(smaller // 1000, rules.trade_wealth_per_1000_bp))
    if shares_faith(state, a, b):  # pilgrims and merchants go together (D-278)
        income = apply_bp(income, BP + rules.faith_trade_bp)
    return income


def tie_income(state: GameState, a: str, b: str) -> int:
    """What the friendly tie between ``a`` and ``b`` pays each side this turn (0: none)."""
    return _tie_income(state, a, b) if (min(a, b), max(a, b)) in _live_ties(state) else 0


def tribute(state: GameState, vassal: str) -> int:
    """What a tributary pays its overlord this turn (D-278)."""
    rules = state.world.rules.rivals
    stores = state.civs[vassal].stockpiles.wealth
    floor = per_turn(state, state.population(vassal) // 1000 * rules.tribute_per_1000)
    return min(stores // 2, max(apply_bp(stores, rules.tribute_share_bp), floor))


def _live_ties(state: GameState) -> list[tuple[str, str]]:
    """Every friendly tie between two living civilisations, in id order."""
    ties = []
    for pair, rel in sorted(state.relations.items()):
        a, b = pair.split("|")
        if state.civs[a].sealed or state.civs[b].sealed:
            continue  # sealed borders: the caravans stop
        if rel.status.friendly and alive(state, a) and alive(state, b):
            ties.append((a, b))
    return ties


def trade_income(state: GameState, civ_id: str) -> int:
    """A civilisation's wealth per turn from all its friendly ties."""
    return sum(_tie_income(state, a, b) for a, b in _live_ties(state) if civ_id in (a, b))


def trade(state: GameState) -> None:
    """Pay each side of every friendly tie its share of the trade."""
    for a, b in _live_ties(state):
        income = _tie_income(state, a, b)
        state.civs[a].stockpiles.wealth += income
        state.civs[b].stockpiles.wealth += income
    for pair in sorted(state.relations):  # tribute (D-278)
        a, b = pair.split("|")
        lord = overlord_of(state, a, b)
        if lord is None or not alive(state, a) or not alive(state, b):
            continue
        vassal = b if lord == a else a
        paid = tribute(state, vassal)
        state.civs[vassal].stockpiles.wealth -= paid
        state.civs[lord].stockpiles.wealth += paid


def convert(state: GameState, civ_id: str, faith_id: str, events: EventLog, how: str) -> None:
    """A court takes up a faith."""
    civ = state.civs[civ_id]
    civ.faith = faith_id
    name = state.world.faiths[faith_id].name
    events.add(civ_id, "faith", f"{civ.name} takes up {name} ({how}).", name)
    if civ_id != state.player_civ and state.civs[state.player_civ].faith == faith_id:
        events.add(
            state.player_civ,
            "faith",
            f"The {civ.adjective} court now shares our faith, {name}.",
            name,
        )


def spread_faiths(
    state: GameState, effects_by_civ: dict[str, Effects], rng: GameRng, events: EventLog
) -> None:
    """Spreading faiths may cross to neighbours; shared faith softens old grudges."""
    rules = state.world.rules.rivals
    base = per_turn(state, rules.faith_spread_bp)
    converted: set[str] = set()
    for pair, rel in sorted(state.relations.items()):
        a, b = pair.split("|")
        if not alive(state, a) or not alive(state, b):
            continue
        fa, fb = state.civs[a].faith, state.civs[b].faith
        if fa and fa == fb:
            fade = rate_per_turn(state, rules.shared_faith_fade_bp)
            for holder in sorted(rel.grievance):
                rel.grievance[holder] -= apply_bp(rel.grievance[holder], fade)
            continue
        for source, target in ((a, b), (b, a)):
            faith = state.civs[source].faith
            if not faith or target in converted or not state.world.faiths[faith].spreads:
                continue
            if target == state.player_civ:
                continue  # your court changes its faith only by your choice
            chance = base * (2 if rel.status.friendly else 1)
            source_effects = effects_by_civ.get(source)
            influence = source_effects[EffectType.CULTURAL_INFLUENCE] if source_effects else 0
            chance = apply_bp(chance, BP + influence)
            held = state.civs[target].faith
            if held and state.world.faiths[held].spreads:
                # a court of another world faith holds to it: conversions are rare
                chance = apply_bp(chance, rules.faith_rooted_resistance_bp)
            if rng.chance(chance):
                convert(state, target, faith, events, f"carried from {state.civs[source].name}")
                converted.add(target)
                break


def shares_faith(state: GameState, a: str, b: str) -> bool:
    """True when two courts hold the same faith."""
    fa = state.civs[a].faith
    return bool(fa) and fa == state.civs[b].faith


def friendly(state: GameState, a: str, b: str) -> bool:
    """True for a trading, allied or tributary tie."""
    tie = status(state, a, b)
    return tie is not None and tie.friendly

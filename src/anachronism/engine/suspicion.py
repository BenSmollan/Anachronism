"""Suspicion: unexplained progress gets noticed (DESIGN §7, D-022).

Adopting something ahead of its historical time raises suspicion of the ruling house. Above a
threshold people settle on an explanation (the *framing*): inspired, witchcraft or fraud, each
with its own consequences. Suspicion fades over time, faster with legitimacy.
"""

from __future__ import annotations

from anachronism.content.schema import EffectType, SocialGroup, TechNode
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP, apply_bp, clamp
from anachronism.engine.rng import GameRng
from anachronism.engine.state import CivState, Framing, GameState
from anachronism.engine.timeflow import current_era, per_turn, rate_per_turn

_FRAMING_MESSAGES = {
    Framing.INSPIRED: "People say the rulers of {name} are divinely inspired.",
    Framing.WITCHCRAFT: "Priests in {name} denounce the new arts as witchcraft.",
    Framing.FRAUD: "Nobles of {name} whisper that the new wonders are frauds.",
    Framing.NONE: "Talk of strange knowledge in {name} dies down.",
}


def adoption_suspicion_bp(state: GameState, node: TechNode) -> int:
    """Suspicion gained by adopting ``node`` in the current year."""
    rules = state.world.rules.suspicion
    gain = 0
    years_ahead = node.year - state.year
    if years_ahead > 0:
        base = years_ahead * rules.gain_per_year_ahead_bp
        gain = apply_bp(base, rules.visibility_bp[node.visibility - 1])
    era = current_era(state).id
    cap = state.world.effect_caps[EffectType.SUSPICION][era]
    gain += sum(min(e.bp, cap) for e in node.effects if e.type is EffectType.SUSPICION)
    return min(gain, rules.max_gain_bp)


def on_adoption(state: GameState, civ: CivState, node: TechNode, events: EventLog) -> None:
    """Apply the suspicion caused by adopting ``node``."""
    gain = adoption_suspicion_bp(state, node)
    if gain <= 0:
        return
    civ.stats.suspicion_bp = clamp(civ.stats.suspicion_bp + gain, 0, BP)
    if gain >= 500:
        events.add(
            civ.id,
            "suspicion",
            f"Where did {civ.name} learn {node.name}? People wonder.",
            node.name,
        )


def update_suspicion(state: GameState, civ: CivState, rng: GameRng, events: EventLog) -> None:
    """Fade suspicion, settle or clear the framing, and apply the framing's consequences."""
    rules = state.world.rules.suspicion
    stats = civ.stats
    fading = apply_bp(stats.suspicion_bp, rate_per_turn(state, rules.decay_bp))
    fading += per_turn(state, apply_bp(rules.legitimacy_decay_bp, stats.legitimacy_bp))
    stats.suspicion_bp = max(0, stats.suspicion_bp - fading)

    if civ.framing is Framing.NONE and stats.suspicion_bp >= rules.framing_threshold_bp:
        weights = [
            stats.legitimacy_bp,
            civ.influence.get(SocialGroup.CLERGY, 0),
            civ.influence.get(SocialGroup.NOBILITY, 0),
        ]
        options = [Framing.INSPIRED, Framing.WITCHCRAFT, Framing.FRAUD]
        civ.framing = options[rng.weighted_index(weights)] if any(weights) else Framing.INSPIRED
        events.add(civ.id, "framing", _FRAMING_MESSAGES[civ.framing].format(name=civ.name))
    elif civ.framing is not Framing.NONE and stats.suspicion_bp < rules.framing_clear_bp:
        civ.framing = Framing.NONE
        events.add(civ.id, "framing", _FRAMING_MESSAGES[Framing.NONE].format(name=civ.name))

    if civ.framing is Framing.WITCHCRAFT:
        extra = per_turn(state, apply_bp(stats.suspicion_bp, rules.witchcraft_unrest_bp))
        stats.unrest_bp = clamp(stats.unrest_bp + extra, 0, BP)
    elif civ.framing is Framing.FRAUD:
        loss = per_turn(state, apply_bp(stats.suspicion_bp, rules.fraud_legitimacy_bp))
        stats.legitimacy_bp = clamp(stats.legitimacy_bp - loss, 0, BP)
    elif civ.framing is Framing.INSPIRED:
        boost = per_turn(state, apply_bp(stats.suspicion_bp, rules.inspired_legitimacy_bp))
        stats.legitimacy_bp = clamp(stats.legitimacy_bp + boost, 0, BP)

"""The offline interpreter: rules on the player's words using only the curated library.

Used when there is no API key, when the player chooses offline play, and as the fallback
when a model call fails. It splits the message into parts, matches each part to library
advancements by their names and keywords, and rules from the engine's own feasibility
check. Anything it cannot match is "implausible" with a hint toward ideas within reach, so
offline play still feels like a court that listens (brief §10).
"""

from __future__ import annotations

import re

from anachronism.engine.rulings import Verdict
from anachronism.engine.state import GameState
from anachronism.engine.summary import match_score, words
from anachronism.engine.tech import feasibility, is_adopted
from anachronism.llm.schemas import ModelIdea, ModelReply

MIN_SCORE = 4
"""A part must point at least this strongly at an advancement to count as a match."""
_SPLIT = re.compile(r"[;,\n]|\band also\b|\balso\b|\bthen\b|\bplus\b|\band\b", re.IGNORECASE)


def _best(state: GameState, text: str) -> tuple[int, str] | None:
    scored = [
        (match_score(node, text), node_id)
        for node_id, node in sorted(state.tech_nodes.items())
        if not node.stub
    ]
    best = max(scored, key=lambda pair: (pair[0], -len(pair[1])), default=None)
    return best if best is not None and best[0] >= MIN_SCORE else None


def _within_reach(state: GameState, civ_id: str, count: int = 2) -> list[str]:
    """Advancements the civilisation could start now, nearest ahead of their time first.

    Then the most recent known abroad: never the oldest basics first.
    """
    civ = state.civs[civ_id]
    options = []
    for node_id, node in sorted(state.tech_nodes.items()):
        if node.stub or is_adopted(civ, node_id) or node_id in civ.projects:
            continue
        if not feasibility(state, civ_id, node_id).blocked:
            ahead = node.year > state.year
            options.append((not ahead, abs(node.year - state.year), node.name))
    return [name for _, _, name in sorted(options)[:count]]


def interpret(state: GameState, civ_id: str, text: str) -> ModelReply:
    """Rule on a message with the library alone."""
    limit = state.world.rules.rulings.max_ideas_per_message
    parts = [p.strip() for p in _SPLIT.split(text) if p and p.strip()]
    found: dict[str, str] = {}
    strange: list[str] = []
    whole = _best(state, text)
    for part in parts:
        match = _best(state, part)
        if match is not None and match[1] not in found:
            found[match[1]] = part
        elif match is None and len(words(part)) >= 2:
            strange.append(part)  # a real idea the library has nothing for
    if not found and whole is not None:
        found[whole[1]] = text
    ideas: list[ModelIdea] = []
    for node_id, part in list(found.items())[:limit]:
        result = feasibility(state, civ_id, node_id)
        verdict = Verdict.BLOCKED if result.blocked else Verdict.FEASIBLE
        ideas.append(
            ModelIdea(
                text=part[:300],
                verdict=verdict,
                matches=node_id,
                name=state.tech_nodes[node_id].name,
            )
        )
    if not ideas and words(text):
        strange = [text]
    for part in strange[: max(0, limit - len(ideas))]:
        reach = _within_reach(state, civ_id)
        hint = f"Perhaps begin with {' or '.join(reach)}." if reach else ""
        ideas.append(
            ModelIdea(
                text=part[:300],
                verdict=Verdict.IMPLAUSIBLE,
                reason=(
                    "The scholars pored over your words but found nothing they could build"
                    " on. (Offline, your advisers know only their library of ideas; with the model"
                    " connected it can rule on anything.)"
                ),
                hint=hint,
            )
        )
    return ModelReply(ideas=ideas)

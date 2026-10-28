"""Characters who speak during play, and what they say (step 2.12, D-059).

Lines are written for *moments* (an idea adopted, a riot, the game starting...). The client
shows a character's portrait with a line chosen from the moment's list. Placeholders in
braces are filled in by the game: ``{civ}``, ``{ruler}``, ``{subject}`` (the idea, place or
resource the moment is about), ``{year}``, ``{adjective}`` (Mongol, Roman), and for rivals
``{rival}``, ``{rival_ruler}`` and ``{rival_adjective}``. Prefer "the {adjective} realm" to
"{civ}" before a verb: names like "Mongols" are plural.
In Phase 3 the same characters speak freely through the language model.
"""

from __future__ import annotations

import string

from pydantic import field_validator

from anachronism.content.schema.base import Frozen, Identifier

PLACEHOLDERS = frozenset(
    {"civ", "ruler", "subject", "year", "rival", "rival_ruler", "adjective", "rival_adjective"}
)
"""Names that may appear in braces in a line."""

SPECIAL_SPEAKERS = frozenset({"ruler", "rival"})
"""The player's own ruler and a rival civilisation's ruler (named in scenarios)."""

MOMENTS = frozenset(
    {
        "game_start", "project_started", "adopted", "widespread", "breakthrough", "setback",
        "stalled", "resistance", "suspicion", "framing", "discovery", "riot", "revolt",
        "famine", "collapse", "rival_adopted", "rival_war", "rival_peace", "rival_tribute", "quiet",
        "idea_feasible", "idea_blocked", "idea_implausible",
        "war", "conquest", "province_lost", "capital_lost", "ruler_died", "peace",
        "news", "imitation",
        "victory", "defeat", "ally_attacked", "disaster", "blessing", "faith", "coalition",
        "consequence", "battle_won", "battle_lost", "siege", "army_lost", "pillage", "pillaged",
        "uprising", "uprising_won", "sea_battle_won", "sea_battle_lost", "blockade",
        "crossing_barred", "dynasty", "restoration",
        "advise_steward", "advise_steward_urgent", "advise_general",
        "advise_general_urgent", "advise_scholar", "advise_diviner", "advise_diviner_urgent",
    }
)  # fmt: skip
"""When lines can be spoken. ``rival_adopted``: a rival adopts an idea ahead of its time,
and its ruler tells you so (``{rival}`` is that rival);
``quiet``: a turn with nothing else to say; ``idea_*``: the advisers' reaction to one of the
player's own ideas when no language model is speaking for them (offline mode)."""


class Speaker(Frozen):
    """An adviser who counsels the player: the Greek tutor, the censor..."""

    id: Identifier
    title: str
    subtitle: str = ""
    """The line under the name, e.g. ``Magistrate of Rome``; empty: ``<Adjective> court``."""
    portrait: str = ""
    """Placeholder portrait style (``scholar``, ``steward``, ``general``, ``diviner``);
    empty means the civilisation's own style."""


class Dialogue(Frozen):
    """What is said at one moment. ``id`` is the moment (see ``MOMENTS``)."""

    id: Identifier
    speaker: Identifier
    """A speaker id, or ``ruler`` / ``rival``."""
    lines: tuple[str, ...]

    @field_validator("lines")
    @classmethod
    def _check_lines(cls, lines: tuple[str, ...]) -> tuple[str, ...]:
        if not lines:
            raise ValueError("needs at least one line")
        for line in lines:
            names = {field for _, field, _, _ in string.Formatter().parse(line) if field}
            unknown = names - PLACEHOLDERS
            if unknown:
                raise ValueError(f"unknown placeholder(s) {sorted(unknown)} in {line!r}")
        return lines

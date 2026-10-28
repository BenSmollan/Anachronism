"""Rival civilisations' intentions, temperaments and relations (brief §7, DESIGN §10).

A script is a conditional intention, not a dated event: "Qin wants Shu" fires when Qin is
stable, strong enough and Shu is weak, whatever the calendar says. Scripts can depend on
other scripts, so when the player knocks one off course the ones built on it fall too.
They are written per civilisation inside a scenario (``ScenarioCiv.scripts``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from anachronism.content.schema.base import Frozen, Identifier, NonNegative, Rate


class Disposition(StrEnum):
    """A ruler's temperament, which steers a civilisation once it leaves its script."""

    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    SCHOLARLY = "scholarly"
    MERCANTILE = "mercantile"
    PIOUS = "pious"


class RelationStatus(StrEnum):
    """How two civilisations stand with each other."""

    WAR = "war"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    TRADING = "trading"
    ALLIED = "allied"
    TRIBUTARY = "tributary"
    """One pays tribute to the other (a friendly, unequal tie)."""

    @property
    def friendly(self) -> bool:
        """True for trading, allied and tributary ties (news and goods flow faster)."""
        return self in (RelationStatus.TRADING, RelationStatus.ALLIED, RelationStatus.TRIBUTARY)


class ScriptGoal(StrEnum):
    """What a script wants."""

    CONQUER = "conquer"
    """Make war on ``target`` (a civilisation)."""
    ALLY = "ally"
    """Seek an alliance with ``target``."""
    TRADE = "trade"
    """Open trade with ``target``."""
    ADOPT = "adopt"
    """Take up the advancement ``target`` (a tech node) when it can."""


class Preconditions(Frozen):
    """What must hold for a script to fire. Everything listed must be true."""

    after_year: int | None = None
    """Not before this year (negative = BC)."""
    before_year: int | None = None
    """The chance passes after this year: the script lapses, and scripts built on it too."""
    min_legitimacy_bp: Rate = 0
    max_unrest_bp: Rate = 10_000
    min_strength_ratio_bp: NonNegative = 0
    """Own military strength against the target's, e.g. 12_000 = 1.2 times stronger."""
    target_min_unrest_bp: Rate = 0
    """A trigger inside the target: turmoil there (a coup, a weak heir) opens the door."""
    adopted: tuple[Identifier, ...] = ()
    """Advancements the civilisation must already use."""
    at_peace: bool = False
    """Only when not already fighting another war."""


class Script(Frozen):
    """One intention of a civilisation in a scenario."""

    id: Identifier
    goal: ScriptGoal
    target: Identifier
    preconditions: Preconditions = Preconditions()
    depends_on: tuple[Identifier, ...] = ()
    """Scripts (of any civilisation) that must have fired first."""
    note: Annotated[str, Field(max_length=300)] = ""
    """What happened in real history, for the chronicle and for content review."""
    sources: tuple[str, ...] = ()
    """Where this is known from (ancient authors first, passage numbers)."""
    disputed: str = ""
    """What historians dispute about it and why; empty when nothing is."""


class StartingRelation(Frozen):
    """How two civilisations stand at the start.

    Pairs not listed begin neutral (if they can reach each other) and carry no memory.
    """

    a: Identifier
    b: Identifier
    status: RelationStatus
    grievance_bp: Rate = 0
    """Memory of old wrongs, which colours how they react (0-100%)."""
    note: Annotated[str, Field(max_length=300)] = ""
    sources: tuple[str, ...] = ()
    """Where this is known from (ancient authors first, passage numbers)."""
    disputed: str = ""
    """What historians dispute about it and why; empty when nothing is."""

    @model_validator(mode="after")
    def _check_pair(self) -> StartingRelation:
        if self.a == self.b:
            raise ValueError("a relation needs two different civilisations")
        return self


class Faith(Frozen):
    """A religion or school of belief in a scenario (brief §7.5).

    Who holds it at the start, and whether it spreads to neighbours by itself (Buddhism
    did; the old gods of a city did not).
    """

    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=60)]
    followers: tuple[Identifier, ...] = ()
    """Civilisations holding it at the start."""
    spreads: bool = False
    note: Annotated[str, Field(max_length=300)] = ""

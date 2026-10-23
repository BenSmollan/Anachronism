"""Scenarios: a named historical moment and everyone's situation in it."""

from __future__ import annotations

from collections.abc import Mapping, Set
from typing import Annotated, Literal

from pydantic import Field

from anachronism.content.schema.base import (
    Confidence,
    Frozen,
    Identifier,
    NonNegative,
    Positive,
    Rate,
)
from anachronism.content.schema.rivals import Disposition, Faith, Script, StartingRelation
from anachronism.content.schema.tech import SocialGroup, Stage


class StartingStockpiles(Frozen):
    """Stored resources at the start."""

    food: NonNegative
    materials: NonNegative
    wealth: NonNegative
    knowledge: NonNegative


class StartingStats(Frozen):
    """Civilisation-wide stats at the start, in basis points of 0-100."""

    literacy_bp: Rate
    unrest_bp: Rate
    legitimacy_bp: Rate
    suspicion_bp: Rate = 0


class Successor(Frozen):
    """Who comes next on the throne, if history is followed (brief §7.6)."""

    name: Annotated[str, Field(min_length=1, max_length=60)]
    age: Annotated[int, Field(ge=1, le=90)] = 25
    """Age on taking the throne."""
    disposition: Disposition | None = None
    """Their temperament; empty keeps the state's."""
    until: int | None = None
    """The year their reign really ended by violence or a chronicle's chapter: in a
    chronicle, the player's ruler is spared old age before then (D-130)."""
    died: int | None = None
    """The year they really died of age, illness or accident: in a chronicle, the player's
    ruler lives until then and dies then (D-132)."""
    ends: Annotated[str, Field(max_length=60)] = ""
    """How that reign ended, if not by death ("is forced to abdicate"): the chronicle's
    words for it (D-145)."""


GeneralTrait = Literal["horse", "siege", "shield", "bold", "quartermaster", "beloved"]
"""A general's gift: horse (cavalry fight harder), siege (walls fall faster), shield
(stubborn in defence), bold (fierce in attack, careless in defence), quartermaster (less
attrition), beloved (morale recovers faster and breaks slower)."""


class General(Frozen):
    """A commander a state can give its armies (D-101)."""

    name: Annotated[str, Field(min_length=1, max_length=60)]
    skill: Annotated[int, Field(ge=1, le=5)] = 2
    trait: GeneralTrait | None = None
    note: str = ""
    """A line of history."""


class ScenarioCiv(Frozen):
    """One civilisation's situation at the scenario's start."""

    capital: Identifier
    provinces: dict[Identifier, Positive]
    """Owned provinces and their starting populations."""
    stockpiles: StartingStockpiles
    stats: StartingStats
    influence: dict[SocialGroup, Rate]
    """How much weight each social group carries (0-100%)."""
    techs: dict[Identifier, Stage] = Field(default_factory=dict)
    """Advancements already known at the start (the era baseline)."""
    music: Identifier | None = None
    """Music track for a game as this civilisation, overriding the scenario's (D-208)."""
    leader: str = ""
    """Who rules at the start, e.g. ``Duke Xiao``; empty when the sources are unclear."""
    pitch: str = ""
    """One or two sentences for the civilisation picker: why play this state now."""
    leader_age: Annotated[int, Field(ge=1, le=90)] = 40
    """The ruler's age at the start."""
    leader_until: int | None = None
    """The year the first ruler's reign really ended. In a chronicle the player's ruler does
    not die of old age before then: how the reign ends is the chronicle's to tell."""
    leader_died: int | None = None
    """The year the first ruler really died of age, illness or accident: in a chronicle the
    player's ruler lives until then and dies then (D-132)."""
    successors: tuple[Successor, ...] = ()
    """Who follows, in order, when rulers die (after that, unnamed heirs)."""
    generals: tuple[General, ...] = ()
    """Commanders, best first: new armies take the next free one."""
    disposition: Disposition = Disposition.CAUTIOUS
    """The ruler's temperament, which steers the civilisation once it leaves its script."""
    martial_bp: Annotated[int, Field(ge=1000, le=200_000)] = 10_000
    navy_bp: Annotated[int, Field(ge=0, le=100_000)] = 10_000
    """Seafaring, against the usual: Carthage's fleet was many times Rome's in 264 BC."""
    """How much of its people a state can put under arms, against the usual 10_000: steppe
    peoples, where every adult man rode and shot, raise far more; a demilitarised court less."""
    scripts: tuple[Script, ...] = ()
    """What this civilisation means to do, if conditions allow (brief §7.1)."""


class Scenario(Frozen):
    """A playable starting moment."""

    id: Identifier
    name: str
    description: str = ""
    start_year: int
    years_per_turn: Annotated[int, Field(ge=1, le=50)]
    player_civ: Identifier
    civs: dict[Identifier, ScenarioCiv]
    unowned: dict[Identifier, NonNegative] = Field(default_factory=dict)
    """Provinces nobody controls, with their populations."""
    map: Identifier | None = None
    """Real-Earth map region the client draws (e.g. ``europe``); ``None`` means a map
    generated from province positions. On a real map every province needs a ``latlon``."""
    music: Identifier | None = None
    """Music track the client plays in this scenario (``roman``, ``asian``, ``medieval``,
    ``near_east``: files in ``client/music``); ``None`` keeps the title theme (D-208)."""
    faiths: tuple[Faith, ...] = ()
    """Religions and schools of belief, and who holds them at the start."""
    relations: tuple[StartingRelation, ...] = ()
    """Alliances, wars and grudges at the start; other reachable pairs begin neutral."""
    campaign_years_per_turn: Annotated[int, Field(ge=1, le=50)] | None = None
    """Turn length in chronicle mode (D-120), shorter so chapters fall in their years."""
    cost_scale: Annotated[int, Field(ge=1, le=1000)] = 1
    """Multiplies every project cost. Scenarios with real historical populations (millions,
    not tens of thousands) raise it so inventions cost the same share of a state's effort."""
    sources: tuple[str, ...] = ()
    """Internal research notes on the moment (populations, borders, rulers)."""
    confidence: Confidence = Confidence.LOW
    """How sure the snapshot is; internal only."""
    common_techs: dict[Identifier, Stage] = Field(default_factory=dict)
    """What every state of the age knows (written law, say), so each civ need not list it.
    A state gets one only if it already has its prerequisites (no law code without
    writing); a civ's own entry for the same idea wins."""

    def starting_techs(
        self, civ_id: str, prerequisites: Mapping[str, Set[str]]
    ) -> dict[str, Stage]:
        """A civ's starting ideas: its own list plus the age's common ones it can hold."""
        techs = dict(self.civs[civ_id].techs)
        added = True
        while added:  # a common idea may rest on another (a census on standard measures)
            added = False
            for node_id, stage in sorted(self.common_techs.items()):
                if node_id in techs:
                    continue
                needs = prerequisites.get(node_id, frozenset())
                if all(n in techs and techs[n].is_adopted for n in needs):
                    techs[node_id] = stage
                    added = True
        return techs

"""The physical world: eras, terrain, map resources and province geography."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, Field, model_validator

from anachronism.content.schema.base import Frozen, Identifier, NonNegative, Positive


def _check_latlon(value: tuple[float, float]) -> tuple[float, float]:
    lat, lon = value
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise ValueError(f"latlon {value} is not a place on Earth (lat, lon)")
    return value


LatLon = Annotated[tuple[float, float], AfterValidator(_check_latlon)]
"""A place on the real Earth: (degrees north, degrees east); south and west are negative."""


class Era(Frozen):
    """A span of history. Effect caps are set per era."""

    id: Identifier
    name: str
    ends: int | None
    """First year that is no longer in this era; ``None`` for the last era."""


class Terrain(Frozen):
    """A terrain type and what 1,000 people living on it produce per decade."""

    id: Identifier
    name: str
    food_bp: NonNegative
    """Food per 1,000 people per decade (10_000 = 1 unit)."""
    materials_bp: NonNegative
    capacity: Positive
    """Default number of people a province of this terrain can support."""
    defence_bp: Positive = 10_000
    """How hard a province here is to take in war (20_000 = half as likely to fall)."""


class MapResource(Frozen):
    """A resource that can exist on the map: iron, timber, horses..."""

    id: Identifier
    name: str


class Access(StrEnum):
    """How usable a map resource is in a province."""

    ACCESSIBLE = "accessible"
    LIMITED = "limited"
    UNEXPLORED = "unexplored"

    @property
    def usable(self) -> bool:
        """True if the resource can meet material requirements."""
        return self is not Access.UNEXPLORED


class ProvinceGeography(Frozen):
    """The fixed geography of a province. Ownership and population live in scenarios."""

    id: Identifier
    name: str
    terrain: Identifier
    river: bool = False
    coastal: bool = False
    capacity: Annotated[int, Field(ge=1)] | None = None
    """Overrides the terrain's default capacity when set."""
    resources: dict[Identifier, Access] = Field(default_factory=dict)
    neighbours: tuple[Identifier, ...] = ()
    position: tuple[int, int] | None = None
    """Where the province's centre sits on a generated map (x east, y south; about 1 unit
    per km). Provinces on the real Earth use ``latlon`` instead."""
    latlon: LatLon | None = None
    """The province's centre on the real Earth: (degrees north, degrees east)."""
    sources: tuple[str, ...] = ()
    """Where this is known from (ancient authors first, passage numbers)."""
    disputed: str = ""
    """What historians dispute about it and why; empty when nothing is."""

    @model_validator(mode="after")
    def _check_neighbours(self) -> ProvinceGeography:
        if self.id in self.neighbours:
            raise ValueError("a province cannot neighbour itself")
        if len(set(self.neighbours)) != len(self.neighbours):
            raise ValueError("neighbours contains duplicates")
        return self


class SeaZone(Frozen):
    """A named stretch of sea. Coastal provinces are exactly those next to a sea zone."""

    id: Identifier
    name: str
    position: tuple[int, int] | None = None
    """Centre of the sea zone on a generated map, in the same units as province positions."""
    latlon: LatLon | None = None
    """Centre of the sea zone on the real Earth: (degrees north, degrees east)."""
    neighbours: tuple[Identifier, ...]
    """Provinces on its shores."""

    @model_validator(mode="after")
    def _check_place(self) -> SeaZone:
        if self.position is None and self.latlon is None:
            raise ValueError("a sea zone needs a position or a latlon")
        return self

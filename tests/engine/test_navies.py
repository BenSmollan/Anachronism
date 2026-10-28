"""Fleets, sea battles, crossings and blockades (D-107)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import BuildFleet, MarchArmy, SailFleet, ScuttleFleet
from anachronism.engine.armies import march, raise_army
from anachronism.engine.economy import production
from anachronism.engine.effects import civ_effects
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.navies import (
    blockades,
    build_fleet,
    can_cross,
    fleet_upkeep,
    sail,
    sea_route,
    seas_of,
)
from anachronism.engine.rivals import set_status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Fleet, GameState


@pytest.fixture
def punic(content: Content) -> GameState:
    return new_game(content, "rome_264", seed=1, player_civ="rome")


def log(state: GameState) -> EventLog:
    return EventLog(state.turn, state.year)


def fleet(state: GameState, owner: str, sea: str, ships: int, kind: str = "warships") -> Fleet:
    made = Fleet(
        id=f"{owner}-test-{sea}", owner=owner, name="Test fleet", sea=sea, ship=kind, ships=ships
    )
    state.fleets[made.id] = made
    return made


def at_war(state: GameState) -> GameState:
    set_status(state, "rome", "carthage", RelationStatus.WAR)
    return state


def test_seafaring_states_start_with_fleets(punic: GameState) -> None:
    ships: dict[str, int] = {}
    for f in punic.fleets.values():
        ships[f.owner] = ships.get(f.owner, 0) + f.ships
        coast = [p for p in punic.owned_provinces(f.owner) if f.sea in seas_of(punic, p)]
        assert coast, f"{f.id} lies in a sea off its own coast"
    # Carthage ruled the sea in 264 BC; Rome had hardly a warship; Numidia none
    assert ships["carthage"] > 100
    assert ships.get("rome", 0) < 10
    assert "numidia" not in ships


def test_building_a_fleet_costs_materials_and_wealth(punic: GameState) -> None:
    stores = punic.civs["rome"].stockpiles
    materials, wealth = stores.materials, stores.wealth
    state, logged = apply_action(punic, BuildFleet(civ="rome", province="it_roma", size="small"))
    assert logged.ok
    built = [f for f in state.fleets.values() if f.owner == "rome"]
    assert len(built) == 1
    assert built[0].sea == "tyrrhenian"
    kind = state.world.ships[built[0].ship]
    assert state.civs["rome"].stockpiles.materials == materials - kind.materials * 10
    assert state.civs["rome"].stockpiles.wealth == wealth - kind.wealth * 10
    # more ships of the same kind in the same sea join the fleet already there
    state, logged = apply_action(state, BuildFleet(civ="rome", province="it_campania"))
    assert logged.ok
    assert [f.ships for f in state.fleets.values() if f.owner == "rome"] == [35]


def test_fleets_are_built_only_on_your_own_coasts(punic: GameState) -> None:
    _, logged = apply_action(punic, BuildFleet(civ="rome", province="car_carthage"))
    assert not logged.ok
    inland = next(p for p in sorted(punic.provinces) if not seas_of(punic, p))
    made, why = build_fleet(punic, punic.provinces[inland].owner or "rome", inland, 10)
    assert made is None
    assert why


def test_sail_and_lay_up_orders(punic: GameState) -> None:
    state, _ = apply_action(punic, BuildFleet(civ="rome", province="it_roma", size="small"))
    mine = next(f for f in state.fleets.values() if f.owner == "rome")
    _, logged = apply_action(state, SailFleet(civ="rome", fleet=mine.id, sea="tyrrhenian"))
    assert not logged.ok  # already there
    state, logged = apply_action(state, SailFleet(civ="rome", fleet=mine.id, sea="aegean"))
    assert logged.ok
    assert state.fleets[mine.id].target == "aegean"
    course = sea_route(state, "tyrrhenian", "aegean")
    sail(state, GameRng.from_seed(1), log(state))
    assert state.fleets[mine.id].sea == course[min(1, len(course) - 1)]  # two seas a turn
    state, logged = apply_action(state, ScuttleFleet(civ="rome", fleet=mine.id))
    assert logged.ok
    assert mine.id not in state.fleets


def test_enemy_fleets_meeting_at_sea_fight(punic: GameState) -> None:
    state = at_war(punic)
    for f in list(state.fleets.values()):
        if f.owner == "carthage":
            f.sea = "tyrrhenian"
    before = sum(f.ships for f in state.fleets.values() if f.owner == "carthage")
    roman = fleet(state, "rome", "tyrrhenian", 40)
    events = log(state)
    sail(state, GameRng.from_seed(3), events)
    kinds = [e.kind for e in events.items]
    assert "sea_battle_won" in kinds
    assert "sea_battle_lost" in kinds
    told = next(e.message for e in events.items if e.kind == "sea_battle_won")
    assert told.startswith("Sea battle in the Tyrrhenian Sea.")
    after = sum(f.ships for f in state.fleets.values() if f.owner == "carthage")
    assert after < before  # the winners lose ships too
    # the beaten Romans fall back, or are gone
    if roman.id in state.fleets:
        assert state.fleets[roman.id].target is not None or state.fleets[roman.id].ships < 40


def test_a_carthaginian_victory_is_told_as_carthaginian(punic: GameState) -> None:
    state = at_war(punic)
    fleet(state, "carthage", "ionian", 200)
    fleet(state, "rome", "ionian", 5)
    events = log(state)
    sail(state, GameRng.from_seed(1), events)
    told = next(e.message for e in events.items if e.kind == "sea_battle_won")
    assert "Carthage" in told  # the round war harbour of Carthage


def test_command_of_the_sea_decides_crossings(punic: GameState) -> None:
    state = at_war(punic)
    assert can_cross(state, "rome", "it_roma", "sa_sardinia")  # nobody holds the sea yet
    fleet(state, "carthage", "tyrrhenian", 100)
    for f in list(state.fleets.values()):
        if f.owner == "carthage" and f.sea != "tyrrhenian":
            state.fleets.pop(f.id)
    assert not can_cross(state, "rome", "it_roma", "sa_sardinia")
    army, _ = raise_army(state, "rome", "it_roma", 5000, free=True)
    assert army is not None
    state, logged = apply_action(state, MarchArmy(civ="rome", army=army.id, target="sa_sardinia"))
    assert logged.ok
    events = log(state)
    march(state, GameRng.from_seed(1), events)
    assert state.armies[army.id].province == "it_roma"
    assert "crossing_barred" in [e.kind for e in events.items]
    # a stronger Roman fleet opens the way
    fleet(state, "rome", "tyrrhenian", 200)
    assert can_cross(state, "rome", "it_roma", "sa_sardinia")


def test_blockades_close_harbours_and_cost_trade(punic: GameState) -> None:
    state = at_war(punic)
    effects = civ_effects(state, "rome")
    before = production(state, "rome", effects, BP).wealth
    fleet(state, "carthage", "tyrrhenian", 300)
    events = log(state)
    blockades(state, events)
    shut = [p for p in state.owned_provinces("rome") if state.provinces[p].blockaded]
    assert "it_roma" in shut
    assert "it_apulia" not in shut  # the Adriatic is open
    assert "blockade" in [e.kind for e in events.items]
    assert production(state, "rome", effects, BP).wealth < before
    rel = state.relations["carthage|rome"]
    assert rel.weariness.get("rome", 0) > 0
    # peace lifts the blockade
    set_status(state, "rome", "carthage", RelationStatus.NEUTRAL)
    blockades(state, log(state))
    assert not any(state.provinces[p].blockaded for p in state.owned_provinces("rome"))


def test_unpaid_crews_desert(punic: GameState) -> None:
    carthage = [f for f in punic.fleets.values() if f.owner == "carthage"]
    before = sum(f.ships for f in carthage)
    punic.civs["carthage"].stockpiles.wealth = 0
    fleet_upkeep(punic)
    after = sum(f.ships for f in punic.fleets.values() if f.owner == "carthage")
    assert after < before

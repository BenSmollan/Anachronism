"""Taking a province (D-273): garrisons, storms, starving out, and the spoils of a city taken."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.engine.actions import ArmyAssault, DeclareWar
from anachronism.engine.conquest import (
    full_garrison,
    garrison_army,
    garrison_men,
    sieges,
    storm_outlook,
)
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rng import GameRng
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import Army, GameState
from anachronism.tools.view import build_view

TOWN = "car_emporia"  # a small Carthaginian province (not the capital)
CITY = "car_byzacena"  # a large one
SEAT = "car_carthage"  # Carthage itself, the capital


@pytest.fixture
def warring(content: Content) -> GameState:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state, _ = apply_action(state, DeclareWar(civ="rome", target="carthage"))
    state.armies = {}  # the field is clear: only the armies a test places
    return state


def log(state: GameState) -> EventLog:
    return EventLog(state.turn, state.year)


def besiege(state: GameState, where: str, men: int, **orders: object) -> Army:
    army = Army(id="q", owner="rome", name="Eastern Army", province=where, troops={"levy": men})
    for key, value in orders.items():
        setattr(army, key, value)
    state.armies = {"q": army}
    return army


def test_garrisons_grow_with_people_walls_and_a_capital(warring: GameState) -> None:
    assert full_garrison(warring, CITY) > full_garrison(warring, TOWN) > 0
    before = full_garrison(warring, TOWN)
    warring.provinces[TOWN].walls = 2
    assert full_garrison(warring, TOWN) > before
    people = warring.provinces[SEAT].population
    rules = warring.world.rules.armies
    plain = people // rules.garrison_people_per_man * rules.garrison_share_bp // BP
    assert full_garrison(warring, SEAT) >= plain * 2 - 1  # a capital's is twice as large
    warring.provinces[TOWN].garrison_bp = 5000
    assert abs(garrison_men(warring, TOWN) - full_garrison(warring, TOWN) // 2) <= 1


def test_storming_before_the_breach_is_much_harder(warring: GameState) -> None:
    army = besiege(warring, CITY, 20_000)
    now = storm_outlook(warring, army)
    army.siege_bp = 10**6
    breached = storm_outlook(warring, army)
    assert now["walls_bp"] == BP
    assert breached["walls_bp"] == 0
    assert breached["win_bp"] > now["win_bp"] + 1000
    garrison = garrison_army(warring, army)
    assert garrison is not None
    assert garrison.garrison
    assert garrison.walls_bp > 0
    assert garrison.id not in warring.armies  # drawn up only for a storm, never kept


def test_a_small_army_is_thrown_back_from_the_walls(warring: GameState) -> None:
    besiege(warring, CITY, 3_000, assault="now")
    events = log(warring)
    sieges(warring, events, GameRng(warring.rng))
    assert warring.provinces[CITY].owner == "carthage"
    assert any(e.kind == "battle_lost" and "storming" in e.message for e in events.items)
    assert all(not a.garrison for a in warring.armies.values())
    army = warring.armies.get("q")
    assert army is None or army.province != CITY  # the beaten besiegers fell back
    assert warring.provinces[CITY].garrison_bp < BP  # but the garrison bled for it


def test_a_strong_army_storms_the_breach_and_takes_the_spoils(warring: GameState) -> None:
    army = besiege(warring, TOWN, 60_000)
    army.siege_bp = 10**6  # the walls are down
    warring.civs["carthage"].stockpiles.wealth = 100_000
    wealth = warring.civs["rome"].stockpiles.wealth
    prestige = warring.civs["rome"].stats.legitimacy_bp
    people = warring.provinces[TOWN].population
    events = log(warring)
    sieges(warring, events, GameRng(warring.rng))
    assert warring.provinces[TOWN].owner == "rome"
    spoils = next(e for e in events.items if e.kind == "spoils")
    assert spoils.civ == "rome"
    assert spoils.spoils["stormed"]
    assert spoils.spoils["wealth"] > 0
    assert warring.civs["rome"].stockpiles.wealth == wealth + spoils.spoils["wealth"]
    assert warring.civs["rome"].stats.legitimacy_bp > prestige
    assert warring.provinces[TOWN].population < people  # the city was sacked
    taker = warring.armies["q"]
    assert taker.veterancy_bp > 0
    assert taker.siege_bp == 0
    rules = warring.world.rules.armies
    assert warring.provinces[TOWN].garrison_bp == rules.conquered_garrison_bp


def test_a_starved_city_opens_its_gates_without_a_storm(warring: GameState) -> None:
    besiege(warring, CITY, 20_000, assault="starve")
    taken_on = None
    for turn in range(10):
        events = log(warring)
        sieges(warring, events, GameRng(warring.rng))
        assert not any(e.kind.startswith("battle") for e in events.items)
        if warring.provinces[CITY].owner == "rome":
            taken_on = turn
            assert any(e.kind == "surrender" for e in events.items)
            spoils = next(e for e in events.items if e.kind == "spoils")
            assert not spoils.spoils["stormed"]
            assert spoils.spoils["sacked"] == 0
            break
    assert taken_on is not None
    assert taken_on >= 2  # hunger takes a few turns
    assert warring.armies["q"].men < 20_000  # sickness in the siege lines


def test_a_lifted_siege_lets_the_garrison_recover(warring: GameState) -> None:
    warring.provinces[CITY].garrison_bp = 2000
    warring.armies = {}
    sieges(warring, log(warring), GameRng(warring.rng))
    assert warring.provinces[CITY].garrison_bp > 2000


def test_a_cautious_general_will_not_storm_a_hopeless_breach(warring: GameState) -> None:
    besiege(warring, SEAT, 2_000, assault="now", engage="cautious")
    events = log(warring)
    sieges(warring, events, GameRng(warring.rng))
    assert not any(e.kind.startswith("battle") for e in events.items)
    assert warring.armies["q"].province == SEAT  # still besieging


def test_the_assault_order(warring: GameState) -> None:
    besiege(warring, CITY, 20_000)
    state, logged = apply_action(warring, ArmyAssault(civ="rome", army="q", assault="starve"))
    assert logged.ok
    assert state.armies["q"].assault == "starve"
    _, logged = apply_action(warring, ArmyAssault(civ="carthage", army="q", assault="now"))
    assert not logged.ok


def test_the_view_shows_garrisons_and_the_storm(warring: GameState) -> None:
    besiege(warring, CITY, 20_000)
    view = build_view(warring)
    city = next(p for p in view["provinces"] if p["id"] == CITY)
    assert city["garrison"] == garrison_men(warring, CITY) > 0
    mine = next(a for a in view["armies"] if a["id"] == "q")
    assert mine["assault"] == "breach"
    assert mine["storm"]["garrison"] > 0
    assert 0 < mine["storm"]["win_bp"] < BP
    assert mine["storm"]["starve_turns"] >= 1


def test_old_saves_and_new_fields_round_trip(warring: GameState) -> None:
    besiege(warring, CITY, 20_000, assault="starve")
    warring.provinces[CITY].garrison_bp = 4000
    again = loads(dumps(warring))
    assert again.armies["q"].assault == "starve"
    assert again.provinces[CITY].garrison_bp == 4000

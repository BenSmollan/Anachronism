"""Armies, battles, sieges and supply (D-099)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import ArmyStance, DeclareWar, DisbandArmy, MarchArmy, RaiseArmy
from anachronism.engine.armies import (
    available_units,
    battle,
    raise_army,
    route,
    siege_progress,
    unit_power,
)
from anachronism.engine.conquest import sieges
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.rivals import status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, GameState


@pytest.fixture
def warring(content: Content) -> GameState:
    return new_game(content, "punic_wars", seed=1, player_civ="rome")


def log(state: GameState) -> EventLog:
    return EventLog(state.turn, state.year)


def test_every_state_starts_with_an_army_at_its_capital(warring: GameState) -> None:
    for civ_id, civ in warring.civs.items():
        mine = [a for a in warring.armies.values() if a.owner == civ_id]
        assert len(mine) == 1
        assert mine[0].province == civ.capital
        assert mine[0].men > 0


def test_soldiers_need_their_advancements_and_resources(warring: GameState) -> None:
    kinds = {u.id for u in available_units(warring, "rome")}
    assert "levy" in kinds
    assert "musketeers" not in kinds  # nobody has muskets in 350 BC
    for pid in warring.owned_provinces("rome"):
        warring.provinces[pid].resources.pop("horses", None)
    assert "cavalry" not in {u.id for u in available_units(warring, "rome")}


def test_raising_takes_men_and_stores(warring: GameState) -> None:
    capital = warring.civs["rome"].capital
    people = warring.provinces[capital].population
    wealth = warring.civs["rome"].stockpiles.wealth
    state, logged = apply_action(warring, RaiseArmy(civ="rome", province=capital, size="small"))
    assert logged.ok
    assert state.provinces[capital].population < people
    assert state.civs["rome"].stockpiles.wealth <= wealth
    # men raised where an army stands join it rather than form a new one
    assert len([a for a in state.armies.values() if a.owner == "rome"]) == 1


def test_armies_may_not_march_into_neutral_land(warring: GameState) -> None:
    from anachronism.engine.rivals import frontier

    army = next(a for a in warring.armies.values() if a.owner == "rome")
    target = frontier(warring, "rome", "carthage")[0]
    _, logged = apply_action(warring, MarchArmy(civ="rome", army=army.id, target=target))
    assert not logged.ok
    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    assert route(state, "rome", army.province, target)
    state, logged = apply_action(state, MarchArmy(civ="rome", army=army.id, target=target))
    assert logged.ok


def test_spears_stop_horse_and_chariots_founder_in_the_hills(content: Content) -> None:
    units = content.units
    horse = {"mounted": 10_000}
    spear_vs_horse = unit_power(units["spearmen"], 1000, False, horse, "plains")
    sword_vs_horse = unit_power(units["swordsmen"], 1000, False, horse, "plains")
    assert spear_vs_horse > sword_vs_horse
    on_plain = unit_power(units["chariots"], 1000, True, {}, "plains")
    in_hills = unit_power(units["chariots"], 1000, True, {}, "mountains")
    assert in_hills * 2 < on_plain


def test_the_stronger_side_wins_and_the_loser_falls_back(warring: GameState) -> None:
    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    field = state.civs["carthage"].capital
    behind = state.civs["rome"].capital
    big = Army(
        id="q", owner="rome", name="Big", province=field, came_from=behind, troops={"levy": 50_000}
    )
    small = Army(id="w", owner="carthage", name="Small", province=field, troops={"levy": 2_000})
    state.armies = {"q": big, "w": small}
    winner = battle(state, field, [big], [small], GameRng(state.rng), log(state))
    assert winner == "rome"
    assert big.men < 50_000  # nobody wins for free
    assert "w" not in state.armies or state.armies["w"].province != field


def test_a_beaten_attacker_falls_back_the_way_it_came(warring: GameState) -> None:
    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    field = state.civs["carthage"].capital
    behind = state.civs["rome"].capital
    weak = Army(
        id="q", owner="rome", name="Weak", province=field, came_from=behind, troops={"levy": 1_000}
    )
    strong = Army(id="w", owner="carthage", name="Strong", province=field, troops={"spearmen": 60_000})
    state.armies = {"q": weak, "w": strong}
    battle(state, field, [weak], [strong], GameRng(state.rng), log(state))
    if "q" in state.armies:
        assert state.armies["q"].province == behind


def test_a_siege_takes_the_province_in_time(warring: GameState) -> None:
    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    target = next(p for p in state.owned_provinces("carthage") if p != state.civs["carthage"].capital)
    state.armies = {
        "q": Army(
            id="q",
            owner="rome",
            name="Siege",
            province=target,
            troops={"levy": 80_000, "siege_engines": 5_000},
        )
    }
    assert siege_progress(state, state.armies["q"]) > 0
    for _ in range(10):
        sieges(state, log(state))
        if state.provinces[target].owner == "rome":
            break
    assert state.provinces[target].owner == "rome"


def test_disbanding_sends_the_men_home(warring: GameState) -> None:
    army = next(a for a in warring.armies.values() if a.owner == "rome")
    people = warring.provinces[army.province].population
    state, logged = apply_action(warring, DisbandArmy(civ="rome", army=army.id))
    assert logged.ok
    assert state.provinces[army.province].population == people + army.men
    assert army.id not in state.armies


def test_holding_and_defending(warring: GameState) -> None:
    army = next(a for a in warring.armies.values() if a.owner == "rome")
    state, logged = apply_action(warring, ArmyStance(civ="rome", army=army.id, stance="hold"))
    assert logged.ok
    assert state.armies[army.id].stance == "hold"


def test_wars_of_armies_replay_identically(warring: GameState) -> None:
    from anachronism.engine.save import dumps

    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    capital = state.civs["rome"].capital
    state, _ = apply_action(
        state, RaiseArmy(civ="rome", province=capital, size="large", style="mounted")
    )
    a, b = state, state.model_copy(deep=True)
    for _ in range(4):
        a, _ = end_turn(a)
        b, _ = end_turn(b)
    assert dumps(a) == dumps(b)
    assert status(a, "rome", "carthage") in (RelationStatus.WAR, RelationStatus.HOSTILE)
    for army in a.armies.values():
        assert army.men > 0
        assert army.province in a.provinces


def test_raise_army_respects_the_cap(warring: GameState) -> None:
    capital = warring.civs["rome"].capital
    army, _ = raise_army(warring, "rome", capital, 10**9, free=True)
    assert army is not None
    total = sum(a.men for a in warring.armies.values() if a.owner == "rome")
    from anachronism.engine.armies import mobilisation_cap

    assert total <= mobilisation_cap(warring, "rome") + 1


def test_new_armies_take_the_next_general(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1)
    carthage = state.civs["carthage"]
    royal = next(a for a in state.armies.values() if a.owner == "carthage")
    assert royal.general == "Hamilcar Barca"
    assert royal.trait == "bold"
    pool = [g.name for g in carthage.generals]
    army, _ = raise_army(
        state,
        "carthage",
        "num_massyli" if state.provinces["num_massyli"].owner == "carthage" else carthage.capital,
        5000,
        free=True,
    )
    if army is not None and army.id != royal.id:
        assert army.general == pool[0]
        state, _ = apply_action(state, DisbandArmy(civ="carthage", army=army.id))
        assert state.civs["carthage"].generals[0].name == pool[0]  # back at court


def test_a_horse_master_makes_cavalry_fight_harder(warring: GameState) -> None:
    from anachronism.engine.armies import side_power

    field = warring.civs["rome"].capital
    plain = Army(id="a", owner="rome", name="A", province=field, troops={"cavalry": 10_000})
    gifted = plain.model_copy(update={"id": "b", "trait": "horse"})
    foe = [Army(id="c", owner="carthage", name="C", province=field, troops={"levy": 10_000})]
    assert (
        side_power(warring, [gifted], foe, True, field)[0]
        > side_power(warring, [plain], foe, True, field)[0]
    )


def test_mercenaries_serve_their_contract_then_leave(warring: GameState) -> None:
    from anachronism.engine.actions import HireMercenaries

    warring.civs["rome"].stockpiles.wealth = 100_000
    people = warring.population("rome")
    state, logged = apply_action(warring, HireMercenaries(civ="rome"))
    assert logged.ok
    company = [a for a in state.armies.values() if a.owner == "rome" and a.contract]
    assert len(company) == 1
    assert state.population("rome") == people  # not our own men
    for _ in range(state.world.rules.rivals.mercenary_turns):
        state, _ = end_turn(state)
    assert not [a for a in state.armies.values() if a.owner == "rome" and a.contract]


def test_a_losing_enemy_cedes_the_land_we_hold(warring: GameState) -> None:
    from anachronism.engine.actions import MakePeace
    from anachronism.engine.rivals import frontier, relation

    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    held = frontier(state, "rome", "carthage")[0]
    state.armies["q"] = Army(id="q", owner="rome", name="Q", province=held, troops={"levy": 5000})
    rel = relation(state, "rome", "carthage")
    assert rel is not None
    _, logged = apply_action(state, MakePeace(civ="rome", target="carthage", terms="cede"))
    assert not logged.ok  # they have lost nothing yet
    rel.losses["carthage"] = 3
    rel.weariness["carthage"] = 9000
    state, logged = apply_action(state, MakePeace(civ="rome", target="carthage", terms="cede"))
    assert logged.ok
    assert state.provinces[held].owner == "rome"
    assert status(state, "rome", "carthage") is not RelationStatus.WAR


def test_walls_make_a_province_harder_to_take(warring: GameState) -> None:
    from anachronism.engine.actions import Fortify
    from anachronism.engine.war import defence_bp

    province = warring.civs["rome"].capital
    before = defence_bp(warring, "rome", province)
    warring.civs["rome"].stockpiles.materials = 100_000
    warring.civs["rome"].stockpiles.wealth = 100_000
    state, logged = apply_action(warring, Fortify(civ="rome", province=province))
    assert logged.ok, logged.message
    assert state.provinces[province].walls == 1
    assert defence_bp(state, "rome", province) > before
    enemy = state.civs["carthage"].capital
    _, logged = apply_action(state, Fortify(civ="rome", province=enemy))
    assert not logged.ok


def test_pillage_ravages_loots_and_feeds_the_army(warring: GameState) -> None:
    state, _ = apply_action(warring, DeclareWar(civ="rome", target="carthage"))
    target = next(p for p in state.owned_provinces("carthage") if p != state.civs["carthage"].capital)
    state.armies = {
        "q": Army(
            id="q",
            owner="rome",
            name="Raiders",
            province=target,
            troops={"cavalry": 20_000},
            stance="pillage",
        )
    }
    state.civs["carthage"].stockpiles.wealth = 50_000
    people = state.provinces[target].population
    qin_wealth = state.civs["rome"].stockpiles.wealth
    events = log(state)
    sieges(state, events)
    assert state.provinces[target].population < people
    assert state.provinces[target].owner == "carthage"  # ravaged, not taken
    assert state.provinces[target].ravaged > 0
    assert state.civs["rome"].stockpiles.wealth > qin_wealth
    assert any(e.kind == "pillaged" for e in events.items)


def test_levies_breed_unrest(warring: GameState) -> None:
    capital = warring.civs["rome"].capital
    unrest = warring.civs["rome"].stats.unrest_bp
    warring.civs["rome"].stockpiles.wealth = 100_000
    warring.civs["rome"].stockpiles.food = 100_000
    warring.civs["rome"].stockpiles.materials = 100_000
    state, logged = apply_action(warring, RaiseArmy(civ="rome", province=capital, size="large"))
    assert logged.ok
    assert state.civs["rome"].stats.unrest_bp > unrest


def test_battles_are_told_to_fit(warring: GameState) -> None:
    from anachronism.engine.tales import tell

    rng = GameRng(warring.rng)
    steppe_rout = tell(warring, "mounted", "steppe", True, rng)
    assert steppe_rout in warring.world.tales["horse_archers_steppe"].lines
    spears = tell(warring, "spear", "plains", False, rng)
    assert spears in warring.world.tales["spears_hold"].lines
    for kind in ("infantry", "spear", "missile", "mounted", "elephant", "siege"):
        line = tell(warring, kind, "hills", False, rng)
        assert line.format(place="X", winner="A", loser="B", unit="men")

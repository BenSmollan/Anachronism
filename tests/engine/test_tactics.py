"""Battle plans and veterans (D-108)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import ArmyPlan
from anachronism.engine.armies import battle, hire_company, raise_army
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rivals import set_status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, GameState
from anachronism.engine.tactics import edge, natural, ordered, plans
from anachronism.engine.tales import tell


@pytest.fixture
def warring(content: Content) -> GameState:
    return new_game(content, "rome_264", seed=1, player_civ="rome")


def army(owner: str, troops: dict[str, int], **extra: object) -> Army:
    return Army(id=f"{owner}-t", owner=owner, name="Test", province="x", troops=troops, **extra)


def test_generals_pick_plans_for_their_soldiers_and_ground(warring: GameState) -> None:
    def pick(troops: dict[str, int], attacking: bool, terrain: str) -> str:
        chosen = natural(warring, [army("rome", troops)], attacking, terrain)
        assert chosen is not None
        return chosen.id

    assert pick({"horse_archers": 8000, "levy": 2000}, True, "steppe") == "feint"
    assert pick({"cavalry": 3000, "levy": 7000}, True, "plains") == "flank"
    assert pick({"archers": 5000, "levy": 5000}, True, "plains") == "skirmish"
    assert pick({"levy": 10_000}, True, "plains") == "charge"
    assert pick({"levy": 10_000}, False, "hills") == "hold"
    assert pick({"levy": 10_000}, False, "forest") == "ambush"


def test_a_plan_that_beats_the_enemys_has_the_edge(warring: GameState) -> None:
    tactics = warring.world.tactics
    rules = warring.world.rules.armies
    plain = army("rome", {"levy": 1000})
    assert edge(warring, tactics["hold"], tactics["charge"], plain) == rules.tactic_edge_bp
    assert edge(warring, tactics["charge"], tactics["hold"], plain) == 0
    gifted = army("rome", {"levy": 1000}, general="Scipio", trait="shield")
    assert edge(warring, tactics["hold"], tactics["charge"], gifted) == 2 * rules.tactic_edge_bp
    # no plan beats another that beats it back
    for tactic in tactics.values():
        for other in tactic.beats:
            assert tactic.id not in tactics[other].beats


def test_generals_plan_against_what_they_expect(warring: GameState) -> None:
    attackers = [army("rome", {"levy": 10_000})]
    defenders = [army("carthage", {"levy": 10_000})]
    attack, defence = plans(warring, attackers, defenders, "plains")
    assert attack is not None
    assert defence is not None
    # the defenders would naturally form a shield wall, so nobody charges into it
    assert (attack.id, defence.id) == ("line", "hold")


def test_great_generals_read_the_enemys_real_plan(warring: GameState) -> None:
    defenders = [army("carthage", {"levy": 10_000}, plan="charge")]  # an unexpected order
    plodder = [army("rome", {"levy": 10_000}, skill=1)]
    genius = [army("rome", {"levy": 10_000}, skill=5)]
    slow = plans(warring, plodder, defenders, "plains")[0]
    quick = plans(warring, genius, defenders, "plains")[0]
    assert slow is not None
    assert quick is not None
    assert slow.id == "line"  # expecting a shield wall, and caught by the charge
    assert quick.id == "charge"  # he saw it coming


def test_an_order_that_cannot_be_carried_out_is_ignored(warring: GameState) -> None:
    no_archers = [army("rome", {"levy": 10_000}, plan="skirmish")]
    assert ordered(warring, no_archers, True, "plains") is None
    archers = [army("rome", {"archers": 6000, "levy": 4000}, plan="skirmish")]
    chosen = ordered(warring, archers, True, "forest")
    assert chosen is not None
    assert chosen.id == "skirmish"


def test_the_plan_order(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    state, logged = apply_action(warring, ArmyPlan(civ="rome", army=mine.id, plan="charge"))
    assert logged.ok
    assert state.armies[mine.id].plan == "charge"
    _, logged = apply_action(state, ArmyPlan(civ="rome", army=mine.id, plan="dance"))
    assert not logged.ok
    state, logged = apply_action(state, ArmyPlan(civ="rome", army=mine.id, plan="auto"))
    assert logged.ok
    assert state.armies[mine.id].plan == "auto"


def test_battles_teach_and_recruits_dilute(warring: GameState) -> None:
    set_status(warring, "rome", "carthage", RelationStatus.WAR)
    field = warring.civs["rome"].capital
    rome = next(a for a in warring.armies.values() if a.owner == "rome")
    foe = next(a for a in warring.armies.values() if a.owner == "carthage")
    foe.province = field
    foe.troops = {"levy": 200}
    before = rome.veterancy_bp
    battle(warring, field, [foe], [rome], GameRng.from_seed(1), EventLog(0, 0))
    assert rome.veterancy_bp > before
    learned = rome.veterancy_bp
    raise_army(warring, "rome", field, rome.men, free=True)
    assert 0 < rome.veterancy_bp < learned  # raw recruits joined
    company = hire_company(warring, "rome", 3)
    assert company is not None
    assert company.veterancy_bp == warring.world.rules.armies.mercenary_veterancy_bp


def test_the_report_names_the_plans(warring: GameState) -> None:
    set_status(warring, "rome", "carthage", RelationStatus.WAR)
    field = warring.civs["rome"].capital
    rome = next(a for a in warring.armies.values() if a.owner == "rome")
    foe = next(a for a in warring.armies.values() if a.owner == "carthage")
    foe.province = field
    foe.troops = {"levy": 500}
    foe.plan = "charge"
    rome.plan = "hold"
    events = EventLog(0, 0)
    battle(warring, field, [foe], [rome], GameRng.from_seed(2), events)
    told = next(e.message for e in events.items if e.kind == "battle_won")
    assert "shield wall beat the" in told
    assert "headlong charge" in told


def test_tales_follow_the_winning_plan(warring: GameState) -> None:
    rng = GameRng.from_seed(1)
    cannae = tell(warring, "mounted", "plains", True, rng, winner="carthage", plan="flank")
    assert "Carthaginian line bowed back" in cannae
    other = tell(warring, "mounted", "plains", True, rng, winner="rome", plan="flank")
    assert "{winner}" in other
    assert "Carthaginian" not in other

"""Coming to the aid of a state under attack (D-277)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import ComeToAid, DeclareWar, MakePeace, ProposeAlliance
from anachronism.engine.aid import aid_turn, aiding, gratitude, key, on_battle
from anachronism.engine.armies import _sides, battle, can_enter
from anachronism.engine.conquest import sieges
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rivals import declare_war, set_status, status
from anachronism.engine.rng import GameRng
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import Army, GameState
from anachronism.tools.view import build_view

ME, FRIEND, FOE = "rome", "e2_ligurians", "carthage"


def log(state: GameState) -> EventLog:
    return EventLog(state.turn, state.year)


@pytest.fixture
def attacked(content: Content) -> GameState:
    """Carthage has attacked the Gauls; Rome (the player) is neutral to both."""
    state = new_game(content, "rome_264", seed=1, player_civ=ME)
    set_status(state, ME, FRIEND, RelationStatus.NEUTRAL)
    set_status(state, ME, FOE, RelationStatus.NEUTRAL)
    declare_war(state, FOE, FRIEND, log(state))
    state.armies = {}
    return state


def test_coming_to_aid_joins_the_war_and_opens_the_road(attacked: GameState) -> None:
    friend_land = attacked.owned_provinces(FRIEND)[0]
    assert not can_enter(attacked, ME, friend_land)
    state, logged = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    assert logged.ok
    assert status(state, ME, FOE) is RelationStatus.WAR
    assert aiding(state, ME, FRIEND)
    assert can_enter(state, ME, friend_land)
    assert gratitude(state, ME, FRIEND) == state.world.rules.rivals.aid_join_bp


def test_aid_needs_a_friend_at_war(attacked: GameState) -> None:
    _, logged = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against="pergamon"))
    assert not logged.ok
    _, logged = apply_action(attacked, ComeToAid(civ=ME, target=FOE, against=FOE))
    assert not logged.ok


def test_helpers_defend_the_friends_land(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    where = state.owned_provinces(FRIEND)[0]
    mine = Army(id="m", owner=ME, name="Relief", province=where, troops={"levy": 5000})
    foe = Army(id="w", owner=FOE, name="Invaders", province=where, troops={"levy": 5000})
    state.armies = {"m": mine, "w": foe}
    sides = _sides(state, where)
    assert sides is not None
    attackers, defenders = sides
    assert [a.id for a in attackers] == ["w"]
    assert [a.id for a in defenders] == ["m"]


def test_victories_warm_the_friend_into_an_alliance(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    home = state.owned_provinces(FRIEND)[0]
    events = log(state)
    for _ in range(3):  # three victories on its own soil
        on_battle(state, home, ME, FOE, events)
    assert status(state, ME, FRIEND) is RelationStatus.TRADING
    state.offer = None
    aid_turn(state, events)
    assert state.offer is not None
    assert state.offer.kind == "alliance"
    assert state.offer.from_civ == FRIEND
    assert state.pledges[key(ME, FRIEND, FOE)].offered
    state.offer = None
    state, logged = apply_action(state, ProposeAlliance(civ=ME, target=FRIEND))
    assert logged.ok
    assert status(state, ME, FRIEND) is RelationStatus.ALLIED


def test_a_battle_on_the_friends_soil_counts_twice(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    start = gratitude(state, ME, FRIEND)
    on_battle(state, state.owned_provinces(ME)[0], ME, FOE, log(state))
    abroad = gratitude(state, ME, FRIEND) - start
    on_battle(state, state.owned_provinces(FRIEND)[0], ME, FOE, log(state))
    assert gratitude(state, ME, FRIEND) - start - abroad == 2 * abroad


def test_a_real_battle_earns_gratitude(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    where = state.owned_provinces(FRIEND)[0]
    mine = Army(id="m", owner=ME, name="Relief", province=where, troops={"spearmen": 60_000})
    foe = Army(id="w", owner=FOE, name="Invaders", province=where, troops={"levy": 2000})
    state.armies = {"m": mine, "w": foe}
    start = gratitude(state, ME, FRIEND)
    battle(state, where, [foe], [mine], GameRng(state.rng), log(state))
    assert gratitude(state, ME, FRIEND) > start


def test_a_friends_city_retaken_goes_back_to_it(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    city = next(p for p in state.owned_provinces(FRIEND) if p != state.civs[FRIEND].capital)
    state.provinces[city].owner = FOE  # Carthage took it from the Gauls
    assert state.provinces[city].people == FRIEND
    army = Army(id="m", owner=ME, name="Relief", province=city, troops={"spearmen": 80_000})
    army.siege_bp = 10**6
    state.armies = {"m": army}
    start = gratitude(state, ME, FRIEND)
    events = log(state)
    sieges(state, events, GameRng(state.rng))
    assert state.provinces[city].owner == FRIEND
    spoils = next(e for e in events.items if e.kind == "spoils")
    assert spoils.spoils["liberated"] == state.civs[FRIEND].name
    assert gratitude(state, ME, FRIEND) >= start + state.world.rules.rivals.aid_liberation_bp


def test_a_separate_peace_is_a_betrayal(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    rel = state.relations["e2_ligurians|rome"]
    before = rel.grievance.get(FRIEND, 0)
    rel_war = state.relations["carthage|rome"]
    rel_war.weariness[FOE] = 10**6  # Carthage is glad of any peace
    state, logged = apply_action(state, MakePeace(civ=ME, target=FOE))
    assert logged.ok
    events = log(state)
    aid_turn(state, events)
    assert key(ME, FRIEND, FOE) not in state.pledges
    assert any(e.kind == "aid_abandoned" for e in events.items)
    assert state.relations["e2_ligurians|rome"].grievance.get(FRIEND, 0) > before


def test_the_pledge_ends_with_the_friends_war(attacked: GameState) -> None:
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    set_status(state, FRIEND, FOE, RelationStatus.NEUTRAL)
    aid_turn(state, log(state))
    assert not state.pledges
    assert status(state, ME, FRIEND) is not RelationStatus.WAR


def test_view_and_saves(attacked: GameState) -> None:
    view = build_view(attacked)
    friend = next(c for c in view["civs"] if c["id"] == FRIEND)
    assert [f["id"] for f in friend["attacked_by"]] == [FOE]
    assert friend["aid"] == []
    state, _ = apply_action(attacked, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    friend = next(c for c in build_view(state)["civs"] if c["id"] == FRIEND)
    assert friend["aid"][0]["against"] == FOE
    assert friend["gratitude_bp"] > 0
    assert loads(dumps(state)).pledges == state.pledges


def test_the_player_hears_a_neighbour_is_attacked(content: Content) -> None:
    state = new_game(content, "rome_264", seed=1, player_civ=ME)
    set_status(state, ME, FRIEND, RelationStatus.NEUTRAL)
    events = log(state)
    declare_war(state, FOE, FRIEND, events)
    assert any(e.kind == "aid_call" and e.civ == ME for e in events.items)


def test_declaring_war_on_your_friend_is_not_aid(attacked: GameState) -> None:
    state, _ = apply_action(attacked, DeclareWar(civ=ME, target=FRIEND))
    _, logged = apply_action(state, ComeToAid(civ=ME, target=FRIEND, against=FOE))
    assert not logged.ok

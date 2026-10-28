"""Rivals: news and awareness, scripts and their dependencies, war, diplomacy, victory."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import Preconditions, RelationStatus, Script, ScriptGoal, Stage
from anachronism.engine.actions import DeclareWar, MakePeace, Priority, ProposeAlliance, SendEnvoy
from anachronism.engine.dynasty import renew
from anachronism.engine.economy import project_costs
from anachronism.engine.events import EventLog
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.occupation import occupation
from anachronism.engine.reports import capacity
from anachronism.engine.rivals import (
    contact_pairs,
    deliver_news,
    hops,
    key,
    relation,
    rival_decrees,
    run_scripts,
    set_status,
    spread_news,
    start_project,
    status,
    strength,
)
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Awareness, Event, GameState, TechState
from anachronism.engine.victory import check_outcome, progress
from anachronism.engine.war import capture, wear_wars


@pytest.fixture
def warring(content: Content) -> GameState:
    return new_game(content, "rome_264", seed=1, player_civ="rome")


def only_scripts(state: GameState, civ: str, *scripts: Script) -> None:
    state.world = state.world.model_copy(update={"scripts": {civ: tuple(scripts)}})


def test_relations_start_from_the_scenario_and_geography(warring: GameState) -> None:
    owners = {pid: p.owner for pid, p in warring.provinces.items()}
    for a, b in contact_pairs(warring.world, owners):
        assert key(a, b) in warring.relations
    assert status(warring, "seleucid", "ptolemaic") is RelationStatus.HOSTILE
    assert relation(warring, "seleucid", "ptolemaic").grievance["seleucid"] > 0  # type: ignore[union-attr]
    assert warring.civs["rome"].disposition == "aggressive"
    assert warring.world.scripts["rome"]


def test_news_travels_with_delay_and_makes_rivals_aware(warring: GameState) -> None:
    node = next(
        n for n in sorted(warring.tech_nodes) if warring.tech_nodes[n].year - warring.year > 1000
    )
    adopted = Event(
        turn=1,
        year=warring.year,
        civ="rome",
        kind="adopted",
        message="",
        subject=warring.tech_nodes[node].name,
    )
    spread_news(warring, [adopted], {}, GameRng(warring.rng))
    assert warring.news
    near = min(warring.news, key=lambda n: n.arrives_turn)
    far = max(warring.news, key=lambda n: n.arrives_turn)
    assert hops(warring, "rome", near.to_civ) <= hops(warring, "rome", far.to_civ)  # type: ignore[operator]
    events = EventLog(turn=0, year=warring.year)
    deliver_news(warring, events)
    assert all(c.awareness is Awareness.ON_SCRIPT for c in warring.civs.values())  # not yet
    warring.turn = far.arrives_turn
    deliver_news(warring, events)
    heard = [c for c in warring.civs.values() if c.heard]
    assert heard
    assert all(
        c.awareness is not Awareness.ON_SCRIPT
        for c in heard
        if any(not h.garbled for h in c.heard) or c.heard
    )
    assert any(e.kind == "news" for e in events.items)


def test_ordinary_adoptions_are_not_news(warring: GameState) -> None:
    old = next(n for n in sorted(warring.tech_nodes) if warring.tech_nodes[n].year < warring.year)
    adopted = Event(
        turn=1,
        year=warring.year,
        civ="rome",
        kind="adopted",
        message="",
        subject=warring.tech_nodes[old].name,
    )
    spread_news(warring, [adopted], {}, GameRng(warring.rng))
    assert not warring.news


def test_scripts_fire_on_their_preconditions(warring: GameState) -> None:
    only_scripts(
        warring,
        "seleucid",
        Script(id="sel_now", goal=ScriptGoal.CONQUER, target="ptolemaic"),
        Script(
            id="sel_later",
            goal=ScriptGoal.CONQUER,
            target="pergamon",
            preconditions=Preconditions(after_year=-100),
        ),
        Script(id="sel_after", goal=ScriptGoal.ALLY, target="bithynia", depends_on=("sel_later",)),
    )
    events = EventLog(turn=0, year=warring.year)
    strengths = {c: strength(warring, c) for c in warring.civs}
    run_scripts(warring, strengths, events)
    assert "sel_now" in warring.scripts_fired
    assert status(warring, "seleucid", "ptolemaic") is RelationStatus.WAR
    assert "sel_later" not in warring.scripts_fired
    assert "sel_after" not in warring.scripts_fired


def test_lapsed_scripts_pull_down_their_dependents(warring: GameState) -> None:
    only_scripts(
        warring,
        "seleucid",
        Script(
            id="gone",
            goal=ScriptGoal.CONQUER,
            target="ptolemaic",
            preconditions=Preconditions(before_year=-400),
        ),
        Script(id="built_on_it", goal=ScriptGoal.ALLY, target="bithynia", depends_on=("gone",)),
    )
    run_scripts(warring, {}, EventLog(turn=0, year=warring.year))
    assert set(warring.scripts_lapsed) == {"gone", "built_on_it"}


def test_free_agents_leave_their_scripts(warring: GameState) -> None:
    only_scripts(
        warring, "seleucid", Script(id="sel_now", goal=ScriptGoal.CONQUER, target="ptolemaic")
    )
    warring.civs["seleucid"].awareness = Awareness.FREE_AGENT
    run_scripts(warring, {}, EventLog(turn=0, year=warring.year))
    assert not warring.scripts_fired


def test_war_takes_provinces_and_ends_in_peace(warring: GameState) -> None:
    from anachronism.engine.armies import raise_army

    state = apply_action(warring, DeclareWar(civ="seleucid", target="ptolemaic"))[0]
    assert status(state, "seleucid", "ptolemaic") is RelationStatus.WAR
    state.civs["seleucid"].martial_bp = 60_000  # a great host
    raise_army(state, "seleucid", state.civs["seleucid"].capital, 400_000, free=True)
    start = len(state.owned_provinces("ptolemaic"))
    for _ in range(15):
        state, _ = end_turn(state)
        if status(state, "seleucid", "ptolemaic") is not RelationStatus.WAR:
            break
    assert len(state.owned_provinces("ptolemaic")) < start
    assert status(state, "seleucid", "ptolemaic") is not RelationStatus.WAR  # weariness made peace
    assert relation(state, "seleucid", "ptolemaic").grievance.get("ptolemaic", 0) > 0  # type: ignore[union-attr]


def test_losing_a_capital_moves_the_court(warring: GameState) -> None:
    events = EventLog(turn=0, year=warring.year)
    capital = warring.civs["seleucid"].capital
    capture(warring, "rome", capital, events)
    assert warring.civs["seleucid"].capital != capital
    assert warring.provinces[warring.civs["seleucid"].capital].owner == "seleucid"
    assert warring.civs["seleucid"].awareness is Awareness.FREE_AGENT


def test_allies_join_defensive_wars(warring: GameState) -> None:
    state, logged = apply_action(warring, DeclareWar(civ="seleucid", target="pergamon"))
    assert logged.ok
    # Pergamon and Bithynia are not allied, so Bithynia stays out
    assert status(state, "bithynia", "seleucid") is not RelationStatus.WAR
    state.relations[key("pergamon", "bithynia")].status = RelationStatus.ALLIED
    state, _ = apply_action(state, DeclareWar(civ="seleucid", target="bithynia"))
    assert status(state, "pergamon", "seleucid") is RelationStatus.WAR


def test_player_diplomacy(warring: GameState) -> None:
    state, logged = apply_action(warring, SendEnvoy(civ="rome", target="e2_veneti"))
    assert logged.ok
    assert state.civs["rome"].stockpiles.wealth < warring.civs["rome"].stockpiles.wealth
    assert status(state, "rome", "e2_veneti") is RelationStatus.TRADING
    _, logged = apply_action(state, SendEnvoy(civ="rome", target="carthage"))
    assert not logged.ok  # one embassy a turn
    state, logged = apply_action(state, ProposeAlliance(civ="rome", target="e2_veneti"))
    assert not logged.ok  # trade a while first
    state.turn += state.world.rules.rivals.alliance_trust_turns
    state, logged = apply_action(state, ProposeAlliance(civ="rome", target="e2_veneti"))
    assert logged.ok
    assert status(state, "rome", "e2_veneti") is RelationStatus.ALLIED
    state, logged = apply_action(state, DeclareWar(civ="rome", target="e2_boii"))
    assert logged.ok
    assert state.civs["e2_boii"].awareness is Awareness.FREE_AGENT
    state, logged = apply_action(state, MakePeace(civ="rome", target="e2_boii"))
    assert logged.ok or "scorns" in logged.message
    state, logged = apply_action(state, DeclareWar(civ="rome", target="rome"))
    assert not logged.ok


def test_victory_needs_ground_gained(warring: GameState) -> None:
    paths = progress(warring)
    for path, values in paths.items():
        assert (
            values["target_bp"]
            >= warring.victory_start[path] + warring.world.rules.rivals.victory_margin_bp
            or values["target_bp"] == 10_000
        ), path
    events = EventLog(turn=0, year=warring.year)
    check_outcome(warring, events)
    assert warring.outcome is None
    for pid in sorted(warring.provinces):
        if warring.provinces[pid].owner is not None:
            warring.provinces[pid].owner = "rome"
    check_outcome(warring, events)
    assert warring.outcome is not None
    assert warring.outcome.result == "victory"
    assert warring.outcome.path == "military"


def test_economic_victory_needs_allies_and_a_great_economy(warring: GameState) -> None:
    from anachronism.engine.rivals import set_status

    events = EventLog(turn=0, year=warring.year)
    others = [c for c in sorted(warring.civs) if c != "rome"]
    for other in others:
        set_status(warring, "rome", other, RelationStatus.TRADING)
    trading = progress(warring)["economic"]
    for other in others:
        set_status(warring, "rome", other, RelationStatus.ALLIED)
    allied = progress(warring)["economic"]
    assert allied["share_bp"] > trading["share_bp"]  # trading partners count only in part
    assert allied["partners"] == len(others)
    assert allied["income"] > 0
    check_outcome(warring, events)
    if allied["richest"]:
        assert warring.outcome is not None
        assert warring.outcome.path == "economic"
    else:
        assert warring.outcome is None


def test_losing_everything_is_defeat_only_once_no_one_remembers(warring: GameState) -> None:
    lost = warring.owned_provinces("rome")
    for pid in lost:
        warring.provinces[pid].owner = "carthage"
        warring.provinces[pid].people = "rome"
    check_outcome(warring, EventLog(turn=0, year=warring.year))
    assert warring.outcome is None  # the Roman people may yet rise again (D-113)
    for pid in lost:
        warring.provinces[pid].people = "carthage"  # assimilated: Rome is forgotten
    check_outcome(warring, EventLog(turn=0, year=warring.year))
    assert warring.outcome is not None
    assert warring.outcome.result == "defeat"


def test_a_fallen_state_is_restored_where_its_people_rise(warring: GameState) -> None:
    lost = warring.owned_provinces("rome")
    for pid in lost:
        warring.provinces[pid].owner = "carthage"
        warring.provinces[pid].people = "rome"
        warring.provinces[pid].held_since = warring.turn
    for army in [a for a in warring.armies.values() if a.owner in ("carthage", "rome")]:
        del warring.armies[army.id]  # no garrisons to hold them down
    override = warring.world.rules.armies.model_copy(update={"uprising_bp": 10_000})
    warring.world = warring.world.model_copy(
        update={"rules": warring.world.rules.model_copy(update={"armies": override})}
    )
    events = EventLog(turn=0, year=warring.year)
    occupation(warring, GameRng(warring.rng), events)
    assert warring.owned_provinces("rome")
    assert warring.civs["rome"].capital in warring.owned_provinces("rome")
    assert any(e.kind == "restoration" for e in events.items)


def test_a_collapsed_state_passes_to_a_new_dynasty(warring: GameState) -> None:
    rome = warring.civs["rome"]
    rome.collapsed = True
    rome.revolts = 3
    rome.stats.unrest_bp = 8_000
    events = EventLog(turn=0, year=warring.year)
    renew(warring, events)
    assert not rome.collapsed
    assert rome.dynasties == 2
    assert rome.revolts == 0
    assert rome.stats.unrest_bp < 8_000
    assert [e.kind for e in events.items] == ["dynasty"]
    check_outcome(warring, events)
    assert warring.outcome is None


def test_turns_with_rivals_stay_deterministic(content: Content) -> None:
    a = new_game(content, "rome_264", seed=3)
    b = new_game(content, "rome_264", seed=3)
    for _ in range(4):
        a, _ = end_turn(a)
        b, _ = end_turn(b)
    assert a == b
    assert a.scripts_fired


def test_the_player_is_asked_not_dragged_into_wars(warring: GameState) -> None:
    warring.relations[key("massalia", "rome")].status = RelationStatus.ALLIED
    state, _ = apply_action(warring, DeclareWar(civ="carthage", target="massalia"))
    assert status(state, "rome", "carthage") is not RelationStatus.WAR
    assert any(e.kind == "ally_attacked" and e.civ == "rome" for e in state.events)


def test_capitals_and_mountains_are_harder_to_take(warring: GameState) -> None:
    from anachronism.engine.war import defence_bp

    capital = warring.civs["seleucid"].capital
    other = next(p for p in warring.owned_provinces("seleucid") if p != capital)
    assert defence_bp(warring, "seleucid", capital) > defence_bp(warring, "seleucid", other) or (
        warring.world.geography[other].terrain == "mountains"
    )
    rules = warring.world.rules.rivals
    assert defence_bp(warring, "seleucid", capital) >= rules.capital_defence_bp


def test_a_last_province_holds_out_and_the_player_has_grace(warring: GameState) -> None:
    from anachronism.engine.war import defence_bp

    capital = warring.civs["seleucid"].capital
    walled = defence_bp(warring, "seleucid", capital)
    for pid in warring.owned_provinces("seleucid"):
        if pid != capital:
            warring.provinces[pid].owner = "rome"
    assert defence_bp(warring, "seleucid", capital) > walled  # the last stand
    # in the opening turns an enemy court does not march on the player
    from anachronism.engine.armies import command

    state, _ = apply_action(warring, DeclareWar(civ="seleucid", target="rome"))
    command(state, {})
    rome_land = set(state.owned_provinces("rome"))
    assert not any(a.target in rome_land for a in state.armies.values() if a.owner == "seleucid")


def test_faiths_start_from_the_scenario_and_spread(content: Content) -> None:
    from anachronism.engine.culture import spread_faiths

    state = new_game(content, "rome_264", seed=1)
    assert state.civs["rome"].faith == "roman_gods"
    assert state.civs["carthage"].faith == "punic_gods"
    override = state.world.rules.rivals.model_copy(update={"faith_spread_bp": 10_000})
    state.world = state.world.model_copy(
        update={"rules": state.world.rules.model_copy(update={"rivals": override})}
    )
    events = EventLog(turn=0, year=state.year)
    spread_faiths(state, {}, GameRng(state.rng), events)
    assert any(e.kind == "faith" for e in events.items)


def test_courts_of_world_faiths_hold_to_them(content: Content) -> None:
    from anachronism.engine.culture import spread_faiths

    state = new_game(content, "rome_264", seed=1)
    override = state.world.rules.rivals.model_copy(
        update={"faith_spread_bp": 10_000, "faith_rooted_resistance_bp": 0}
    )
    state.world = state.world.model_copy(
        update={"rules": state.world.rules.model_copy(update={"rivals": override})}
    )
    before = {c: civ.faith for c, civ in state.civs.items()}
    spread_faiths(state, {}, GameRng(state.rng), EventLog(turn=0, year=state.year))
    for civ_id, faith in before.items():
        if faith and state.world.faiths[faith].spreads:
            assert state.civs[civ_id].faith == faith, civ_id  # no world faith gives way
    assert any(state.civs[c].faith != f for c, f in before.items())  # the gods of one city only do


def test_the_players_faith_changes_only_by_choice(content: Content) -> None:
    from anachronism.engine.culture import spread_faiths

    state = new_game(content, "rome_264", seed=1)
    override = state.world.rules.rivals.model_copy(update={"faith_spread_bp": 10_000})
    state.world = state.world.model_copy(
        update={"rules": state.world.rules.model_copy(update={"rivals": override})}
    )
    faith = state.civs["rome"].faith
    for turn in range(5):
        spread_faiths(state, {}, GameRng(state.rng), EventLog(turn=turn, year=state.year))
    assert state.civs["rome"].faith == faith


def test_rivals_league_against_a_dominant_player(warring: GameState) -> None:
    from anachronism.engine.rivals import coalitions

    events = EventLog(turn=0, year=warring.year)
    coalitions(warring, GameRng(warring.rng), events)
    assert not events.items  # Rome is not yet feared
    # Rome's neighbours here are few: let the two that remain be at peace with each other
    set_status(warring, "carthage", "e2_mamertines", RelationStatus.NEUTRAL)
    for pid in sorted(warring.provinces)[: len(warring.provinces) * 2 // 3]:
        if warring.provinces[pid].owner is not None:
            warring.provinces[pid].owner = "rome"
    override = warring.world.rules.rivals.model_copy(update={"coalition_chance_bp": 10_000})
    warring.world = warring.world.model_copy(
        update={"rules": warring.world.rules.model_copy(update={"rivals": override})}
    )
    coalitions(warring, GameRng(warring.rng), events)
    assert [e.kind for e in events.items] == ["coalition"]


def test_a_far_weaker_court_pays_tribute(warring: GameState) -> None:
    from anachronism.engine.actions import DemandTribute

    _, logged = apply_action(warring, DemandTribute(civ="rome", target="carthage"))
    assert not logged.ok  # Carthage is no weakling
    small = next(c for c in sorted(warring.civs) if c != "rome" and status(warring, "rome", c))
    warring.civs["rome"].mercenaries = 0
    for pid in warring.owned_provinces(small)[1:]:
        warring.provinces[pid].owner = "rome"  # leave it one province
    if strength(warring, "rome") < strength(warring, small) * 3:
        warring.civs["rome"].martial_bp = 100_000
    state, logged = apply_action(warring, DemandTribute(civ="rome", target=small))
    assert logged.ok
    assert status(state, "rome", small) is RelationStatus.TRIBUTARY


def test_trade_pays_both_sides(warring: GameState) -> None:
    from anachronism.engine.culture import trade

    warring.relations[key("ptolemaic", "rhodes")].status = RelationStatus.TRADING
    before = warring.civs["ptolemaic"].stockpiles.wealth, warring.civs["rhodes"].stockpiles.wealth
    trade(warring)
    assert warring.civs["ptolemaic"].stockpiles.wealth > before[0]
    assert warring.civs["rhodes"].stockpiles.wealth > before[1]


def test_missionaries(content: Content) -> None:
    from anachronism.engine.actions import SendMissionaries

    state = new_game(content, "rome_264", seed=2)
    state.civs["syracuse"].stockpiles.wealth = 10_000
    state, logged = apply_action(state, SendMissionaries(civ="syracuse", target="carthage"))
    assert logged.ok
    assert state.civs["carthage"].faith == "olympians" or "home" in logged.message
    state, logged = apply_action(state, SendMissionaries(civ="syracuse", target="massalia"))
    assert not logged.ok  # Massalia already honours the Olympians
    _, logged = apply_action(state, SendMissionaries(civ="carthage", target="syracuse"))
    assert not logged.ok  # the gods of Carthage seek no converts


def test_decrees_spend_the_treasury(warring: GameState) -> None:
    from anachronism.engine.actions import HireMercenaries, HoldFestival

    rome = warring.civs["rome"]
    rome.stockpiles.wealth = 100_000
    rome.stats.unrest_bp = 3000
    state, logged = apply_action(warring, HoldFestival(civ="rome"))
    assert logged.ok
    assert state.civs["rome"].stats.unrest_bp < 3000
    assert state.civs["rome"].stockpiles.wealth < 100_000
    before = strength(state, "rome")
    state, logged = apply_action(state, HireMercenaries(civ="rome"))
    assert logged.ok
    assert strength(state, "rome") > before
    state, logged = apply_action(state, HireMercenaries(civ="rome"))
    assert not logged.ok  # still serving
    poor = warring.model_copy(deep=True)
    poor.civs["rome"].stockpiles.wealth = 0
    _, logged = apply_action(poor, HoldFestival(civ="rome"))
    assert not logged.ok


def test_rival_courts_issue_decrees(warring: GameState) -> None:
    state, _ = apply_action(warring, DeclareWar(civ="seleucid", target="ptolemaic"))
    state.civs["seleucid"].stockpiles.wealth = 100_000
    state.civs["pergamon"].stockpiles.wealth = 100_000
    state.civs["pergamon"].stats.unrest_bp = 5000
    state.civs["bithynia"].stockpiles.wealth = 0
    state.civs["bithynia"].stats.unrest_bp = 5000
    rival_decrees(state, EventLog(state.turn, state.year))
    assert state.civs["seleucid"].mercenaries > 0
    assert state.civs["seleucid"].stockpiles.wealth >= 50_000  # half kept in reserve
    assert state.civs["pergamon"].stats.unrest_bp < 5000
    assert state.civs["bithynia"].stats.unrest_bp == 5000  # cannot afford it
    assert state.civs["rome"].mercenaries == 0  # the player decides for themselves


def test_rival_courts_never_start_work_they_cannot_staff(content: Content) -> None:
    # D-112: work beyond the surplus is taken on only as steady (low-priority) work, so no
    # rival starves itself chasing an idea it heard of
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    node = "crop_rotation"
    for secret in (node, "quarantine"):  # stolen, so beyond-the-age is not what stops them
        state.civs["pergamon"].tech[secret] = TechState(stage=Stage.CONCEPT, stolen=True)
    assert project_costs(state, node).labour > capacity(state, "pergamon").free_labour
    assert start_project(state, "pergamon", node)
    assert state.civs["pergamon"].projects[node].priority is Priority.LOW
    assert not start_project(state, "pergamon", "quarantine")  # one steady task at a time


def test_the_side_that_tires_first_cedes_what_is_besieged(warring: GameState) -> None:
    # D-118: Carthage is worn out while Rome's army stands in one of its provinces
    set_status(warring, "rome", "carthage", RelationStatus.WAR)
    carthage_lands = warring.owned_provinces("carthage")
    assert len(carthage_lands) >= 2
    target = carthage_lands[0]
    army = next(a for a in warring.armies.values() if a.owner == "rome")
    army.province = target
    rel = relation(warring, "rome", "carthage")
    assert rel is not None
    rel.weariness["carthage"] = warring.world.rules.rivals.peace_weariness_bp
    events = EventLog(turn=0, year=warring.year)
    wear_wars(warring, events)
    assert warring.provinces[target].owner == "rome"
    assert status(warring, "rome", "carthage") is not RelationStatus.WAR
    assert any(e.kind == "ceded" for e in events.items)


def test_a_state_with_only_besieged_land_left_becomes_a_tributary(warring: GameState) -> None:
    set_status(warring, "rome", "e2_mamertines", RelationStatus.WAR)
    (home,) = warring.owned_provinces("e2_mamertines")
    army = next(a for a in warring.armies.values() if a.owner == "rome")
    army.province = home
    rel = relation(warring, "rome", "e2_mamertines")
    assert rel is not None
    rel.weariness["e2_mamertines"] = warring.world.rules.rivals.peace_weariness_bp
    wear_wars(warring, EventLog(turn=0, year=warring.year))
    assert warring.provinces[home].owner == "e2_mamertines"
    assert status(warring, "rome", "e2_mamertines") is RelationStatus.TRIBUTARY

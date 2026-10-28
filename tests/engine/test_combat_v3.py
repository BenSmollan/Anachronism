"""Combat v3 (D-270): wings, deployment, battle ground and a second army on the flank."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.engine.actions import ArmyDeploy, DeclareWar
from anachronism.engine.armies import _lines, battle
from anachronism.engine.deployment import (
    FACING,
    LINE,
    PLACES,
    layout,
    place_army,
    resolved,
    shares,
)
from anachronism.engine.events import EventLog
from anachronism.engine.formations import lacks
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.ground import adjust, ground_of
from anachronism.engine.power import wing_powers
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, Event, GameState
from anachronism.engine.wings import Line, contest
from anachronism.tools.view import build_view

MIXED = {"levy": 5000, "spearmen": 3000, "archers": 2000}
RIVER = "it_boii"  # river plains, with a river
PLAIN = "car_byzacena"  # plains, no river
HILLS = "it_latium"  # hills, no river


@pytest.fixture
def warring(content: Content) -> GameState:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state, _ = apply_action(state, DeclareWar(civ="rome", target="carthage"))
    return state


def pair(
    state: GameState,
    place: str,
    troops_a: dict[str, int] | None = None,
    troops_d: dict[str, int] | None = None,
) -> tuple[Army, Army]:
    """A Roman attacker and a Carthaginian defender standing in ``place``, and nothing else."""
    a = Army(
        id="q",
        owner="rome",
        name="Attackers",
        province=place,
        came_from=state.civs["rome"].capital,
        troops=dict(troops_a or MIXED),
        plan="line",
        formation="balanced",
    )
    d = Army(
        id="w",
        owner="carthage",
        name="Defenders",
        province=place,
        troops=dict(troops_d or MIXED),
        plan="line",
        formation="balanced",
    )
    state.armies = {"q": a, "w": d}
    return a, d


def fight(
    state: GameState, place: str, sides: tuple[list[Army], list[Army]], seed: int = 1
) -> list[Event]:
    log = EventLog(state.turn, state.year)
    battle(state, place, sides[0], sides[1], GameRng.from_seed(seed), log)
    return log.items


def line(first: dict[str, int], men: dict[str, int] | None = None, **extra: object) -> Line:
    """A side for the pure wing arithmetic: powers by place (reserve in ``later``)."""
    full = {p: first.get(p, 0) for p in PLACES}
    held = men or dict.fromkeys(PLACES, 1000)
    return Line(
        first=full,
        later=dict(full),
        men=held,
        horse=dict.fromkeys(PLACES, 0),
        **extra,  # type: ignore[arg-type]
    )


# --- the wing contests -------------------------------------------------------------------------


def test_a_wing_that_beats_its_opposite_breaks_it_and_wheels_on_the_centre(
    warring: GameState,
) -> None:
    rules = warring.world.rules.armies
    a = line({"left": 30_000, "centre": 10_000, "right": 10_000})
    d = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    out = contest(rules, a, d)
    left = out.wings[0]  # a's left meets d's right
    assert (left.wing, left.d_wing) == ("left", "right")
    assert left.broke == "d"
    assert out.broken_d == 1
    # the enemy centre suffers: it is worth less than the same centre of an unbroken line
    quiet = contest(rules, line({"left": 10_000, "centre": 10_000, "right": 10_000}), d)
    assert out.wings[1].d_power < quiet.wings[1].d_power
    assert out.wings[1].a_power > quiet.wings[1].a_power  # the wheeling wing joins in


def test_the_side_that_wins_two_of_three_contests_wins_the_clash(warring: GameState) -> None:
    rules = warring.world.rules.armies
    a = line({"left": 12_000, "centre": 12_000, "right": 8500})
    d = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    out = contest(rules, a, d)
    assert [w.winner for w in out.wings] == ["a", "a", "d"]
    assert out.winner == "a"


def test_reserves_go_in_where_the_line_is_weakest(warring: GameState) -> None:
    rules = warring.world.rules.armies
    d = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    a = line({"left": 14_000, "centre": 10_000, "right": 8000, "reserve": 6000})
    a.later = dict(a.first)
    out = contest(rules, a, d)
    assert out.reserve["a"] == "right"  # a's right is the one in danger
    assert out.reserve["d"] == ""
    # a great general, with no wing in danger, exploits the winning wing instead
    strong = line({"left": 14_000, "centre": 12_000, "right": 11_000, "reserve": 6000}, great=True)
    assert contest(rules, strong, d).reserve["a"] == "left"
    plain = line({"left": 14_000, "centre": 12_000, "right": 11_000, "reserve": 6000})
    assert contest(rules, plain, d).reserve["a"] == "right"


def test_a_deep_reserve_commits_in_a_battle(warring: GameState) -> None:
    a, d = pair(warring, PLAIN)
    a.formation = "deep_reserve"
    events = fight(warring, PLAIN, ([a], [d]))
    clash = next(p for p in events[0].phases if p["name"] == "Clash")
    assert clash["reserve"]["a"] in LINE
    assert clash["reserve"]["d"] == ""


def test_a_refused_wing_is_out_of_the_fight(warring: GameState) -> None:
    rules = warring.world.rules.armies
    a = line(
        {"left": 20_000, "centre": 10_000, "right": 3000},
        {"left": 6000, "centre": 3000, "right": 500, "reserve": 0},
    )
    d = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    out = contest(rules, a, d)
    assert out.wings[2].refused == "a"
    assert out.wings[2].winner == ""
    assert out.broken_a == 0  # refused, not broken


def test_horse_with_no_horse_facing_them_ride_round(warring: GameState) -> None:
    rules = warring.world.rules.armies
    a = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    a.horse["left"] = 6000
    d = line({"left": 10_000, "centre": 10_000, "right": 10_000})
    out = contest(rules, a, d)
    assert out.horse_round == {"a": True, "d": False}
    base = contest(rules, line(a.first), d)
    assert out.wings[1].d_power < base.wings[1].d_power
    d.horse["right"] = 6000  # horse opposite: nobody rides round
    assert contest(rules, a, d).horse_round["a"] is False


def test_a_second_army_falls_on_the_weaker_flank(warring: GameState) -> None:
    rules = warring.world.rules.armies
    a = line({"left": 10_000, "centre": 10_000, "right": 10_000}, flank=8000, flank_men=2000)
    d = line({"left": 12_000, "centre": 10_000, "right": 9000})
    out = contest(rules, a, d)
    assert out.flank == {"side": "a", "against": "right", "men": 2000}  # d's weaker wing
    alone = contest(rules, line(a.first), d)
    assert out.wings[0].a_power > alone.wings[0].a_power  # a's left faces d's right
    assert out.wings[0].d_power < alone.wings[0].d_power


def test_armies_arriving_from_two_directions_make_a_flank_attack(warring: GameState) -> None:
    a, d = pair(warring, PLAIN, {"levy": 8000}, {"levy": 8000})
    second = Army(
        id="q2",
        owner="rome",
        name="Second army",
        province=PLAIN,
        came_from="qin_shang",
        troops={"levy": 4000},
        plan="line",
        formation="balanced",
        arrived_turn=warring.turn,
    )
    a.came_from, a.arrived_turn = "qin_longxi", warring.turn
    warring.armies["q2"] = second
    lines = _lines(warring, PLAIN, [a, second], [d])
    assert lines.line_a.flank > 0
    assert lines.line_a.flank_men == 4000
    assert lines.line_d.flank == 0
    # the line itself holds only the first army
    assert sum(lines.line_a.men.values()) == 8000
    events = fight(warring, PLAIN, ([a, second], [d]))
    clash = next(p for p in events[0].phases if p["name"] == "Clash")
    assert clash["flank"]["side"] == "a"
    assert "second army fell on" in clash["text"]
    # from the same direction there is no flank
    second.came_from = "qin_longxi"
    assert _lines(warring, PLAIN, [a, second], [d]).line_a.flank == 0


# --- deployment --------------------------------------------------------------------------------


def test_the_deploy_order(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    state, logged = apply_action(
        warring, ArmyDeploy(civ="rome", army=mine.id, unit_kind="mounted", place="left")
    )
    assert logged.ok
    assert state.armies[mine.id].deployment == {"mounted": "left"}
    _, logged = apply_action(
        state, ArmyDeploy(civ="rome", army=mine.id, unit_kind="mounted", place="up")
    )
    assert not logged.ok
    _, logged = apply_action(
        state, ArmyDeploy(civ="rome", army=mine.id, unit_kind="ghosts", place="left")
    )
    assert not logged.ok
    _, logged = apply_action(
        state, ArmyDeploy(civ="rome", army=mine.id, unit_kind="siege", place="left")
    )
    assert not logged.ok
    assert "camp" in logged.message
    state, logged = apply_action(
        state, ArmyDeploy(civ="rome", army=mine.id, unit_kind="mounted", place="auto")
    )
    assert logged.ok
    assert state.armies[mine.id].deployment == {}
    _, logged = apply_action(
        state, ArmyDeploy(civ="rome", army="nobody", unit_kind="mounted", place="left")
    )
    assert not logged.ok


def test_ordered_kinds_stand_where_they_are_sent(warring: GameState) -> None:
    a, _ = pair(warring, PLAIN, {"levy": 4000, "archers": 2000, "cavalry": 2000})
    a.deployment = {"mounted": "right", "missile": "reserve", "infantry": "split"}
    placed = place_army(warring, a, warring.world.formations["balanced"])
    assert placed["right"].get("cavalry") == 2000
    assert placed["reserve"] == {"archers": 2000}
    assert (
        sum(placed["left"].values()) + sum(placed["centre"].values()) + placed["right"]["levy"]
        == 4000
    )
    assert sum(sum(t.values()) for t in placed.values()) == 8000


def test_siege_engines_stay_in_camp(warring: GameState) -> None:
    a, _ = pair(warring, PLAIN, {"levy": 4000, "siege_engines": 500})
    placed = place_army(warring, a, warring.world.formations["balanced"])
    assert all("siege_engines" not in troops for troops in placed.values())


def test_each_formation_is_a_preset_deployment(warring: GameState) -> None:
    forms = warring.world.formations
    cases = {  # formation: (kind, place its men mostly stand in)
        "strong_left": ("mounted", "left"),
        "strong_right": ("mounted", "right"),
        "strong_centre": ("infantry", "centre"),
        "balanced": ("infantry", "split"),
        "wide_line": ("infantry", "split"),
    }
    for fid, (kind, place) in cases.items():
        assert resolved(shares(forms[fid], kind, "auto")) == place or fid in ("wide_line",), fid
    # a deep reserve holds a fifth of everything back
    held = shares(forms["deep_reserve"], "infantry", "auto")["reserve"]
    assert 1500 <= held <= 2500
    assert "reserve" not in layout(forms["balanced"], "infantry")
    # strong wings are lopsided; a balanced line is even
    left = shares(forms["strong_left"], "infantry", "auto")
    assert left["left"] > left["centre"] > left["right"]
    even = shares(forms["balanced"], "infantry", "auto")
    assert max(even.values()) - min(even.values()) <= 1
    for fid in forms:
        assert sum(shares(forms[fid], "spear", "auto").values()) == 10_000


def test_a_great_general_turns_his_horse_on_the_enemys_weak_side(warring: GameState) -> None:
    a, d = pair(warring, PLAIN, {"cavalry": 1500, "levy": 8500}, {"spearmen": 4000, "levy": 6000})
    a.formation = "strong_left"  # his horse would stand on the left ...
    d.deployment = {"spear": "right", "infantry": "left"}  # ... where the spears wait
    plain = _lines(warring, PLAIN, [a], [d]).line_a.men
    assert plain["left"] > plain["right"]
    a.skill = 4
    wise = _lines(warring, PLAIN, [a], [d]).line_a.men
    assert wise["right"] > wise["left"]  # so he turns the line round
    a.deployment = {"mounted": "left", "infantry": "left"}  # an order is never second-guessed
    assert _lines(warring, PLAIN, [a], [d]).line_a.men["left"] == 10_000


# --- ground ------------------------------------------------------------------------------------


def test_a_river_costs_the_attackers_the_first_exchange(warring: GameState) -> None:
    ra, rd = pair(warring, RIVER)
    on_river = _lines(warring, RIVER, [ra], [rd])
    pa, pd = pair(warring, PLAIN)
    dry = _lines(warring, PLAIN, [pa], [pd])
    assert on_river.ground.river
    assert not dry.ground.river
    assert sum(on_river.line_a.first.values()) < sum(on_river.line_a.later.values())
    assert sum(on_river.line_a.later.values()) < sum(dry.line_a.later.values())
    assert sum(on_river.line_d.first.values()) == sum(on_river.line_d.later.values())
    assert "river" in on_river.ground.name or on_river.ground.river


def test_horse_suffer_most_crossing_a_river(warring: GameState) -> None:
    rules = warring.world.rules.armies
    ground = ground_of(warring, RIVER)
    units = warring.world.units
    foot = adjust(rules, ground, units["levy"], True, "centre", 10_000)
    horse = adjust(rules, ground, units["cavalry"], True, "centre", 10_000)
    assert foot < 0
    assert horse < foot
    assert adjust(rules, ground, units["cavalry"], False, "centre", 10_000) == 0  # the defenders


def test_defenders_holding_the_river_line_make_the_crossing_costlier(warring: GameState) -> None:
    a, d = pair(warring, RIVER)
    loose = _lines(warring, RIVER, [a], [d])
    d.dug_in = True
    held = _lines(warring, RIVER, [a], [d])
    assert held.held
    assert sum(held.line_a.first.values()) < sum(loose.line_a.first.values())
    assert "hold the river line" in view_ground(warring, held.ground, True)


def view_ground(state: GameState, ground: object, held: bool) -> str:
    from anachronism.engine.ground import text

    return text(state, ground, held)  # type: ignore[arg-type]


def test_hills_favour_the_defenders_archers_and_blunt_a_charge(warring: GameState) -> None:
    rules = warring.world.rules.armies
    ground = ground_of(warring, HILLS)
    units = warring.world.units
    assert ground.high
    assert adjust(rules, ground, units["archers"], False, "centre", 0) > 0
    assert adjust(rules, ground, units["archers"], True, "centre", 0) == 0
    assert adjust(rules, ground, units["cavalry"], True, "left", 0) < 0


def test_forest_and_marsh_weaken_horse_and_forbid_the_wide_line(warring: GameState) -> None:
    rules = warring.world.rules.armies
    forest = ground_of(warring, "germania")
    units = warring.world.units
    assert forest.rough
    assert adjust(rules, forest, units["cavalry"], False, "left", 0) < 0
    assert adjust(rules, forest, units["war_elephants"], False, "left", 0) < 0
    assert adjust(rules, forest, units["levy"], False, "left", 0) == 0
    a, d = pair(warring, PLAIN, {"levy": 20_000}, {"levy": 5000})
    wide = warring.world.formations["wide_line"]
    assert not lacks(wide, [a], [d])
    assert lacks(wide, [a], [d], "forest")
    assert lacks(wide, [a], [d], "marsh")


def test_open_plains_favour_horse_on_the_wings(warring: GameState) -> None:
    rules = warring.world.rules.armies
    plain = ground_of(warring, PLAIN)
    horse = warring.world.units["cavalry"]
    assert adjust(rules, plain, horse, False, "left", 0) > 0
    assert adjust(rules, plain, horse, False, "centre", 0) == 0
    a, d = pair(warring, PLAIN, {"cavalry": 4000}, {"levy": 4000})
    a.deployment = {"mounted": "left"}
    lines = _lines(warring, PLAIN, [a], [d])
    wide_open = lines.line_a.first["left"]
    rough = _lines(warring, "germania", [a], [d]).line_a.first["left"]
    assert wide_open > rough


def test_horse_against_spears_on_a_wing(warring: GameState) -> None:
    """Spears opposite horse beat them; the same spears opposite foot are only ordinary."""
    a, d = pair(warring, PLAIN, {"cavalry": 4000}, {"spearmen": 4000})
    a.deployment = {"mounted": "left"}
    d.deployment = {"spear": "right"}  # d's right faces a's left
    versus_horse = _lines(warring, PLAIN, [a], [d])
    assert versus_horse.line_d.first["right"] > versus_horse.line_a.first["left"] * 8 // 10
    d.deployment = {"spear": "left"}  # now they face nothing but empty wing
    elsewhere = _lines(warring, PLAIN, [a], [d])
    spears_here = wing_powers(
        warring,
        [d],
        {p: [] for p in PLACES} | {"right": [(d, {"spearmen": 4000})]},
        {p: [] for p in PLACES} | {"left": [(a, {"cavalry": 4000})]},
        False,
        PLAIN,
        ground_of(warring, PLAIN),
        0,
    )["right"]
    spears_vs_foot = wing_powers(
        warring,
        [d],
        {p: [] for p in PLACES} | {"right": [(d, {"spearmen": 4000})]},
        {p: [] for p in PLACES} | {"left": [(a, {"cavalry": 0, "levy": 4000})]},
        False,
        PLAIN,
        ground_of(warring, PLAIN),
        0,
    )["right"]
    assert spears_here > spears_vs_foot * 13 // 10  # the spear bonus against horse
    assert elsewhere.line_d.first["left"] > 0


# --- battles and the view ----------------------------------------------------------------------


def test_the_clash_reports_its_wings_and_the_battle_its_ground(warring: GameState) -> None:
    a, d = pair(warring, RIVER)
    events = fight(warring, RIVER, ([a], [d]))
    won = events[0]
    clash = next(p for p in won.phases if p["name"] == "Clash")
    assert [w["wing"] for w in clash["wings"]] == ["left", "centre", "right"]
    for w in clash["wings"]:
        assert {"wing", "a_men", "d_men", "winner", "text"} <= set(w)
        assert w["winner"] in ("a", "d", "")
        assert w["text"]
    assert set(clash["reserve"]) == {"a", "d"}
    assert "river" in won.ground.lower()
    assert events[1].ground == won.ground


def test_a_wing_wins_are_consistent_with_the_battle(warring: GameState) -> None:
    for seed in range(8):
        trial = warring.model_copy(deep=True)
        a, d = pair(trial, PLAIN, {"levy": 20_000}, {"levy": 5000})
        events = fight(trial, PLAIN, ([a], [d]), seed)
        clash = next(p for p in events[0].phases if p["name"] == "Clash")
        assert [w["winner"] for w in clash["wings"]].count("a") >= 2
        assert events[0].sides["winner"] == "a"


def test_the_view_carries_deployment_odds_wings_and_ground(warring: GameState) -> None:
    view = build_view(warring)
    assert [p["id"] for p in view["deploy_places"]] == [
        "auto",
        "left",
        "centre",
        "right",
        "reserve",
        "split",
    ]
    assert all({"id", "name", "note"} <= set(p) for p in view["deploy_places"])
    mine = next(a for a in view["armies"] if a["owner"] == "rome")
    assert mine["kinds"]
    assert {k["kind"] for k in mine["kinds"]} == set(mine["deployment"])
    for entry in mine["deployment"].values():
        assert entry["auto"] is True
        assert entry["place"] in (*PLACES, "split", "camp")
        assert sum(entry["shares"].values()) in (0, 10_000)
    rival = next(a for a in view["armies"] if a["owner"] != "rome")
    assert "deployment" not in rival
    assert rival["kinds"]
    # an order shows, with auto off
    state, _ = apply_action(
        warring, ArmyDeploy(civ="rome", army=mine["id"], unit_kind="infantry", place="reserve")
    )
    after = next(a for a in build_view(state)["armies"] if a["id"] == mine["id"])
    assert after["deployment"]["infantry"]["place"] == "reserve"
    assert after["deployment"]["infantry"]["auto"] is False


def test_the_odds_preview_names_each_wing_and_the_ground(warring: GameState) -> None:
    a, _ = pair(warring, RIVER)
    a.deployment = {"infantry": "left", "spear": "left", "missile": "left"}
    view = build_view(warring)
    odds = next(o for o in view["odds"] if o["mine"] == "q" and o["theirs"] == "w")
    assert [w["wing"] for w in odds["wings"]] == ["left", "centre", "right"]
    assert [w["vs"] for w in odds["wings"]] == ["right", "centre", "left"]
    assert all(w["outcome"] in ("strong", "even", "weak") for w in odds["wings"])
    assert odds["wings"][0]["outcome"] == "strong"  # everything massed on the left
    assert odds["wings"][2]["outcome"] != "strong"
    assert "river" in odds["ground"].lower()
    assert all(isinstance(w["ratio_bp"], int) for w in odds["wings"])


def test_old_armies_load_without_a_deployment() -> None:
    old = Army.model_validate(
        {"id": "x", "owner": "rome", "name": "Old", "province": "p", "troops": {"levy": 500}}
    )
    assert old.deployment == {}
    assert old.arrived_turn == -1


def test_facing_wings_are_opposite() -> None:
    assert [FACING[w] for w in LINE] == ["right", "centre", "left"]

"""Combat v2 (D-267): formations, battle phases, engagement rules, camps, forced marches."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import RelationStatus
from anachronism.engine.actions import ArmyEngage, ArmyFormation, DeclareWar, MarchArmy
from anachronism.engine.armies import battle, march, mobility, odds, side_power
from anachronism.engine.events import EventLog
from anachronism.engine.formations import edge, formations, lacks
from anachronism.engine.game import apply_action, new_game
from anachronism.engine.rivals import set_status
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, Event, GameState
from anachronism.tools.view import build_view

MIXED = {"levy": 5000, "spearmen": 3000, "archers": 2000}


@pytest.fixture
def warring(content: Content) -> GameState:
    state = new_game(content, "rome_264", seed=1, player_civ="rome")
    state, _ = apply_action(state, DeclareWar(civ="rome", target="carthage"))
    return state


def field(state: GameState) -> str:
    return state.civs["carthage"].capital


def pair(
    state: GameState,
    troops_a: dict[str, int] | None = None,
    troops_d: dict[str, int] | None = None,
    **extra: object,
) -> tuple[Army, Army]:
    """A Qin attacker and a Wei defender standing in Wei's capital, and nothing else."""
    place = field(state)
    a = Army(
        id="q",
        owner="rome",
        name="Attackers",
        province=place,
        came_from=state.civs["rome"].capital,
        troops=dict(troops_a or MIXED),
        plan="line",
    )
    d = Army(
        id="w",
        owner="carthage",
        name="Defenders",
        province=place,
        troops=dict(troops_d or MIXED),
        plan="line",
    )
    state.armies = {"q": a, "w": d}
    return a, d


def fight(state: GameState, a: Army, d: Army, seed: int = 1) -> tuple[str, list[Event]]:
    log = EventLog(state.turn, state.year)
    winner = battle(state, field(state), [a], [d], GameRng.from_seed(seed), log)
    return winner, log.items


# --- formations -------------------------------------------------------------------------------


def test_formation_matchups(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 13_000}, {"levy": 10_000})
    forms = warring.world.formations

    def beats(mine: str, theirs: str, side: list[Army], other: list[Army]) -> bool:
        return edge(forms[mine], forms[theirs], side, other) > 0

    for wing in ("strong_left", "strong_right"):
        assert beats(wing, "balanced", [d], [a])
        assert beats(wing, "strong_centre", [d], [a])
        assert not beats("balanced", wing, [d], [a])
        assert beats("deep_reserve", wing, [d], [a])
    assert beats("deep_reserve", "strong_centre", [d], [a])
    assert beats("strong_centre", "wide_line", [d], [a])
    assert not beats("wide_line", "strong_centre", [a], [d])
    # wide line: only with the numbers (a has 1.3 to 1)
    assert beats("wide_line", "balanced", [a], [d])
    assert beats("wide_line", "deep_reserve", [a], [d])
    assert lacks(forms["wide_line"], [d], [a])  # the smaller side cannot stretch
    assert not beats("wide_line", "balanced", [d], [a])  # thin: no edge


def test_opposite_wings_are_won_by_the_better_general(warring: GameState) -> None:
    a, d = pair(warring)
    a.skill, d.skill = 4, 1
    left, right = warring.world.formations["strong_left"], warring.world.formations["strong_right"]
    assert edge(left, right, [a], [d]) > 0
    assert edge(right, left, [d], [a]) == 0
    a.skill = 1  # equal generals: neither
    assert edge(left, right, [a], [d]) == 0


def test_a_general_answers_what_he_expects(warring: GameState) -> None:
    a, d = pair(warring)
    form_a, form_d = formations(warring, [a], [d])
    assert form_a is not None
    assert form_d is not None
    assert form_a.id in ("strong_left", "strong_right")  # the answer to an expected balanced line
    a.formation = "deep_reserve"  # an order is obeyed
    assert formations(warring, [a], [d])[0] == warring.world.formations["deep_reserve"]


def test_the_formation_order(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    state, logged = apply_action(
        warring, ArmyFormation(civ="rome", army=mine.id, formation="wide_line")
    )
    assert logged.ok
    assert state.armies[mine.id].formation == "wide_line"
    _, logged = apply_action(state, ArmyFormation(civ="rome", army=mine.id, formation="phalanx9"))
    assert not logged.ok
    state, logged = apply_action(state, ArmyFormation(civ="rome", army=mine.id, formation="auto"))
    assert logged.ok
    assert state.armies[mine.id].formation == "auto"


def wins(state: GameState, form_a: str, form_d: str, seeds: int = 12) -> int:
    won = 0
    for seed in range(seeds):
        trial = state.model_copy(deep=True)
        a, d = pair(trial)
        a.formation, d.formation = form_a, form_d
        winner, _ = fight(trial, a, d, seed)
        won += winner == "rome"
    return won


def test_the_better_formation_wins_the_battle(warring: GameState) -> None:
    assert wins(warring, "strong_left", "balanced") > wins(warring, "balanced", "balanced")
    assert wins(warring, "balanced", "strong_left") < wins(warring, "balanced", "balanced")
    assert wins(warring, "deep_reserve", "strong_centre") > wins(
        warring, "strong_centre", "strong_centre"
    )


def test_odds_count_formations_and_engagement(warring: GameState) -> None:
    a, d = pair(warring)
    a.formation = d.formation = "balanced"
    even = odds(warring, [a], [d], field(warring))
    a.formation = "strong_left"
    assert odds(warring, [a], [d], field(warring)) > even
    a.formation = "balanced"
    a.engage = "last_man"
    assert odds(warring, [a], [d], field(warring)) > even


# --- three phases ------------------------------------------------------------------------------


def test_a_battle_has_three_phases(warring: GameState) -> None:
    a, d = pair(warring)
    _, events = fight(warring, a, d)
    won = next(e for e in events if e.kind == "battle_won")
    assert [p["name"] for p in won.phases] == ["Skirmish", "Clash", "Pursuit"]
    for phase in won.phases:
        core = {"name", "text", "losses", "morale"}
        # the clash also carries the wing contests, the reserves and any flank blow (D-270)
        extra = {"wings", "reserve", "flank"} if phase["name"] == "Clash" else set()
        assert set(phase) == core | extra
        assert set(phase["losses"]) == set(phase["morale"]) == {"a", "d"}
        assert phase["text"]
    assert won.sides["winner"] in ("a", "d")
    assert next(e for e in events if e.kind == "battle_lost").phases == won.phases
    assert sum(p["losses"]["a"] for p in won.phases) == 10_000 - a.men


def test_missile_troops_hurt_morale_in_the_skirmish(warring: GameState) -> None:
    archers = {"archers": 10_000}
    a, d = pair(warring, archers, {"levy": 10_000})
    _, events = fight(warring, a, d)
    skirmish = events[0].phases[0]
    assert skirmish["losses"]["d"] > skirmish["losses"]["a"]  # archers shoot the levy


def test_a_shaken_side_breaks_in_the_skirmish(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 10_000}, {"archers": 10_000})
    a.morale_bp = 2000
    winner, events = fight(warring, a, d)
    assert winner == "carthage"
    names = [p["name"] for p in events[0].phases]
    assert names == ["Skirmish", "Pursuit"]  # a short battle: no clash
    assert "breaks" in events[0].phases[-1]["text"]
    assert sum(p["losses"]["a"] for p in events[0].phases) > 0


def test_a_line_that_gives_way_in_the_clash_breaks(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 30_000}, {"levy": 6000})
    d.morale_bp = 4000
    winner, events = fight(warring, a, d)
    assert winner == "rome"
    pursuit = events[0].phases[-1]
    assert pursuit["name"] == "Pursuit"
    assert "breaks" in pursuit["text"]
    assert pursuit["losses"]["d"] > 0


def test_horse_run_down_the_beaten(warring: GameState) -> None:
    foot = {"levy": 12_000}
    dead = {}
    for label, host in (("foot", foot), ("horse", {"cavalry": 12_000})):
        trial = warring.model_copy(deep=True)
        a, d = pair(trial, host, {"levy": 6000})
        d.morale_bp = 2500  # broken: the chase is on
        _, events = fight(trial, a, d)
        dead[label] = events[0].phases[-1]["losses"]["d"]
    assert dead["horse"] > dead["foot"]


def test_unbroken_losers_get_away_in_good_order(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 12_000}, {"levy": 10_000})
    _, events = fight(warring, a, d, seed=3)
    phases = events[0].phases
    if "good order" in phases[-1]["text"]:
        broken = pair(warring, {"levy": 12_000}, {"levy": 10_000})
        broken[1].morale_bp = 2000
        _, again = fight(warring, *broken, seed=3)
        assert again[0].phases[-1]["losses"]["d"] >= phases[-1]["losses"]["d"]


# --- rules of engagement -----------------------------------------------------------------------


def test_a_cautious_army_withdraws_from_a_hopeless_battle(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 2000}, {"levy": 30_000})
    a.engage = "cautious"
    morale = a.morale_bp
    winner, events = fight(warring, a, d)
    assert winner == "carthage"
    assert [e.kind for e in events] == ["withdrawal", "withdrawal"]
    assert not any(e.kind == "battle_lost" for e in events)
    assert a.province == warring.civs["rome"].capital  # fell back the way it came
    assert a.morale_bp == morale  # keeps its nerve
    assert 1900 <= a.men < 2000  # a small rear-guard loss
    assert d.men == 30_000


def test_a_cautious_army_fights_when_the_odds_are_fair(warring: GameState) -> None:
    a, d = pair(warring)
    a.engage = d.engage = "cautious"
    _, events = fight(warring, a, d)
    assert any(e.kind == "battle_won" for e in events)


def test_defenders_behind_walls_never_withdraw(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 30_000}, {"levy": 2000})
    d.engage = "cautious"
    warring.provinces[field(warring)].walls = 1
    _, events = fight(warring, a, d)
    assert any(e.kind == "battle_won" for e in events)
    assert not any(e.kind == "withdrawal" for e in events)


def test_the_last_man_neither_breaks_nor_yields(warring: GameState) -> None:
    a, d = pair(warring, {"levy": 10_000}, {"archers": 10_000})
    a.morale_bp = 2000
    a.engage = "last_man"
    _, events = fight(warring, a, d)
    assert "Clash" in [p["name"] for p in events[0].phases]  # no early break


def test_the_last_man_loses_far_more_if_beaten(warring: GameState) -> None:
    lost = {}
    for rule in ("fight", "last_man"):
        total = 0
        for seed in range(8):
            trial = warring.model_copy(deep=True)
            a, d = pair(trial, {"levy": 8000}, {"levy": 20_000})
            a.engage = rule
            fight(trial, a, d, seed)
            total += 8000 - a.men
        lost[rule] = total
    assert lost["last_man"] > lost["fight"] * 12 // 10


def test_the_engagement_order(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    state, logged = apply_action(warring, ArmyEngage(civ="rome", army=mine.id, engage="cautious"))
    assert logged.ok
    assert state.armies[mine.id].engage == "cautious"


# --- strategic touches -------------------------------------------------------------------------


def test_a_still_army_digs_in_and_loses_it_on_the_march(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    mine.stance = "hold"
    mine.raised_turn = -1
    assert not mine.dug_in
    march(warring, GameRng.from_seed(1), EventLog(0, 0))
    assert mine.dug_in
    here = mine.province
    mine.target = next(
        p for p in warring.world.geography[here].neighbours if p in warring.provinces
    )
    march(warring, GameRng.from_seed(1), EventLog(0, 0))
    assert mine.province != here
    assert not mine.dug_in


def test_a_fortified_camp_strengthens_the_defence(warring: GameState) -> None:
    a, d = pair(warring)
    plain, _ = side_power(warring, [d], [a], False, field(warring))
    d.dug_in = True
    camp, _ = side_power(warring, [d], [a], False, field(warring))
    assert camp > plain
    d.dug_in = False
    attack, _ = side_power(warring, [a], [d], True, field(warring))
    a.dug_in = True
    assert side_power(warring, [a], [d], True, field(warring))[0] == attack  # only in defence


def test_a_forced_march_goes_further_at_a_cost(warring: GameState) -> None:
    mine = next(a for a in warring.armies.values() if a.owner == "rome")
    base = mobility(warring, mine)
    mine.target, mine.forced = warring.civs["rome"].capital, True
    assert mobility(warring, mine) == base + 1
    mine.target = None
    far = next(
        p
        for p in sorted(warring.provinces)
        if p != mine.province and warring.provinces[p].owner == "rome"
    )
    state, logged = apply_action(
        warring, MarchArmy(civ="rome", army=mine.id, target=far, forced=True)
    )
    assert logged.ok
    assert "forced" in logged.message
    army = state.armies[mine.id]
    assert army.forced
    men, morale = army.men, army.morale_bp
    march(state, GameRng.from_seed(1), EventLog(0, 0))
    assert army.men < men
    assert army.morale_bp < morale
    assert not army.forced or army.target is not None  # the pace ends with the march


# --- the view ----------------------------------------------------------------------------------


def test_the_view_carries_the_new_army_data(warring: GameState) -> None:
    view = build_view(warring)
    mine = next(a for a in view["armies"] if a["owner"] == "rome")
    assert mine["formation"] == "auto"
    assert mine["engage"] == "fight"
    assert mine["dug_in"] is False
    assert mine["forced"] is False
    options = {o["id"]: o for o in mine["formation_options"]}
    assert set(options) == set(warring.world.formations)
    assert all({"name", "description", "ok", "lacking"} <= set(o) for o in options.values())
    assert {f["id"] for f in view["formations"]} == set(options)
    assert [r["id"] for r in view["engage_rules"]] == ["fight", "cautious", "last_man"]
    assert isinstance(view["odds"], list)


def test_distant_rival_armies_are_seen_roughly(warring: GameState) -> None:
    view = build_view(warring)
    for army in view["armies"]:
        if army["owner"] == "rome":
            assert army["men_exact"]
    far = [a for a in view["armies"] if not a["men_exact"]]
    assert far, "some rival army should be out of sight at the start"
    for army in far:
        assert army["men"] % 5000 == 0
        assert army["men"] >= 5000


def test_formation_and_odds_in_view_for_a_nearby_enemy(warring: GameState) -> None:
    set_status(warring, "rome", "carthage", RelationStatus.WAR)
    _, d = pair(warring)
    view = build_view(warring)
    mine = next(x for x in view["armies"] if x["id"] == "q")
    assert mine["formation_likely"] is not None
    assert any(o["mine"] == "q" and o["theirs"] == "w" for o in view["odds"])
    foe = next(x for x in view["armies"] if x["id"] == "w")
    assert foe["men_exact"]
    assert foe["men"] == d.men


def test_battle_phases_reach_the_view(warring: GameState) -> None:
    a, d = pair(warring)
    _, events = fight(warring, a, d)
    view = build_view(warring, events)
    ours = [e for e in view["events"] if e["kind"] in ("battle_won", "battle_lost")]
    assert ours
    assert ours[0]["phases"][0]["name"] == "Skirmish"


def test_old_armies_load_with_defaults() -> None:
    old = Army.model_validate(
        {"id": "x", "owner": "rome", "name": "Old", "province": "p", "troops": {"levy": 500}}
    )
    assert (old.formation, old.engage, old.dug_in, old.forced) == ("auto", "fight", False, False)

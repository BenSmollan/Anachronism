"""War between civilisations (DESIGN §10): captures, defences, weariness and peace.

The fighting is done by armies (``armies.py``, D-099): battles, sieges and supply. This
module holds what war means for states: a province changing hands (losing a capital moves
the court and shakes the ruler), how hard a province is to take, the weariness and unrest
of a long war, and peace, which the side that lost more carries away as a grievance.
"""

from __future__ import annotations

from anachronism.content.schema import RelationStatus
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP, clamp
from anachronism.engine.rivals import (
    add_grievance,
    alive,
    frontier,
    make_tributary,
    province_links,
    set_status,
)
from anachronism.engine.state import Awareness, GameState
from anachronism.engine.timeflow import per_turn


def fronts(state: GameState) -> list[dict[str, object]]:
    """Every active war and where it is fought (for the map's army markers)."""
    found: list[dict[str, object]] = []
    for pair, rel in sorted(state.relations.items()):
        if rel.status is not RelationStatus.WAR:
            continue
        a, b = pair.split("|")
        found.append(
            {
                "a": a,
                "b": b,
                "front": sorted({*frontier(state, a, b), *frontier(state, b, a)}),
                "clashes": clashes(state, a, b),
            }
        )
    return found


def clashes(state: GameState, a: str, b: str, limit: int = 4) -> list[list[str]]:
    """Pairs of bordering provinces [a's, b's] where the two armies face each other."""
    links = province_links(state.world)
    theirs = set(state.owned_provinces(b))
    pairs: list[list[str]] = []
    for mine in state.owned_provinces(a):
        land = [p for p in state.world.geography[mine].neighbours if p in theirs]
        across = sorted(p for p in links.get(mine, set()) if p in theirs)
        for other in sorted(land) or across[:1]:
            pairs.append([mine, other])
    pairs.sort(
        key=lambda pair: (
            -(state.provinces[pair[0]].population + state.provinces[pair[1]].population),
            pair,
        )
    )
    return pairs[:limit]


def capture(state: GameState, taker: str, province_id: str, events: EventLog) -> None:
    """``taker`` takes a province; a lost capital moves to the largest province left."""
    province = state.provinces[province_id]
    loser_id = province.owner
    province.owner = taker
    province.held_since = state.turn
    if province.people is None:
        province.people = taker  # unclaimed land: its people take the new lords as their own
    name = state.world.geography[province_id].name
    taker_civ = state.civs[taker]
    events.add(taker, "conquest", f"{taker_civ.adjective} armies take {name}.", name)
    if loser_id is None:
        return
    loser = state.civs[loser_id]
    events.add(loser_id, "province_lost", f"{name} falls to {taker_civ.adjective} armies.", name)
    if loser.capital == province_id:
        left = state.owned_provinces(loser_id)
        if left:
            loser.capital = max(left, key=lambda p: (state.provinces[p].population, p))
            loser.stats.legitimacy_bp = clamp(
                loser.stats.legitimacy_bp - state.world.rules.rivals.capital_loss_legitimacy_bp,
                0,
                BP,
            )
            new_seat = state.world.geography[loser.capital].name
            events.add(
                loser_id,
                "capital_lost",
                f"The {loser.adjective} government moves to {new_seat}.",
                name,
            )
    if not state.owned_provinces(loser_id):
        loser.collapsed = True
        events.add(
            loser_id,
            "destroyed",
            f"The {loser.adjective} state is no more:"
            f" {taker_civ.adjective} armies hold all its lands.",
            loser.name,
        )
    if taker == state.player_civ and loser_id != state.player_civ:
        loser.awareness = Awareness.FREE_AGENT  # a conquered people does not forget


def defence_bp(state: GameState, defender: str, province_id: str) -> int:
    """How hard a province is to take: terrain, capital walls, built walls, a last stand."""
    rules = state.world.rules.rivals
    terrain = state.world.terrain[state.world.geography[province_id].terrain]
    defence = terrain.defence_bp
    if state.civs[defender].capital == province_id:
        defence = defence * rules.capital_defence_bp // BP
    if len(state.owned_provinces(defender)) == 1:
        defence = defence * rules.last_stand_defence_bp // BP
    walls = state.provinces[province_id].walls if province_id in state.provinces else 0
    defence += walls * state.world.rules.armies.wall_level_bp
    return max(1, defence)


def side_strength(state: GameState, civ: str, enemy: str, strengths: dict[str, int]) -> int:
    """A civilisation's strength in its war with ``enemy``.

    Its own, plus half of each ally also at war with that enemy (allies send help, not
    their whole army).
    """
    total = strengths.get(civ, 0)
    for pair, rel in sorted(state.relations.items()):
        if rel.status is RelationStatus.ALLIED and civ in pair.split("|"):
            ally = next(c for c in pair.split("|") if c != civ)
            other = state.relations.get(f"{ally}|{enemy}" if ally < enemy else f"{enemy}|{ally}")
            if other is not None and other.status is RelationStatus.WAR:
                total += strengths.get(ally, 0) // 2
    return total


def wear_wars(state: GameState, events: EventLog) -> None:
    """Every war grinds on: both sides grow restless and weary; the first to tire sues for peace.

    The fighting itself is done by armies (``armies.py``); this is the cost of being at war.
    """
    rules = state.world.rules.rivals
    for pair, rel in sorted(state.relations.items()):
        if rel.status is not RelationStatus.WAR:
            continue
        a, b = pair.split("|")
        if not alive(state, a) or not alive(state, b):
            set_status(state, a, b, RelationStatus.HOSTILE)
            continue
        for side, other in ((a, b), (b, a)):
            civ = state.civs[side]
            civ.stats.unrest_bp = clamp(
                civ.stats.unrest_bp + per_turn(state, rules.war_unrest_bp), 0, BP
            )
            tiring = per_turn(state, rules.weariness_per_turn_bp)
            if rel.losses.get(side, 0) < rel.losses.get(other, 0):
                tiring //= 2  # a winning war is easier to bear
            rel.weariness[side] = rel.weariness.get(side, 0) + tiring
        tired = [c for c in (a, b) if rel.weariness.get(c, 0) >= rules.peace_weariness_bp]
        if len(tired) == 1:
            # the side that tires first must pay for peace with the cities under siege (D-118)
            settle(state, tired[0], b if tired[0] == a else a, events)
        elif tired:
            make_peace(state, a, b, events)


def settle(state: GameState, tired: str, other: str, events: EventLog) -> None:
    """The side worn out first sues for peace, giving up what the other's armies besiege.

    If that is all it has left, it bows as the other's tributary instead of vanishing. If
    nothing of its land is under siege, it is plain peace.
    """
    besieged = sorted(
        {
            army.province
            for army in state.armies.values()
            if army.owner == other and state.provinces[army.province].owner == tired
        }
    )
    if not besieged:
        make_peace(state, tired, other, events)
        return
    them, victor = state.civs[tired], state.civs[other]
    if len(besieged) >= len(state.owned_provinces(tired)):
        make_peace(state, tired, other, events)
        make_tributary(state, other, tired)
        add_grievance(state, tired, other, 1000)
        text = f"Worn out by war, {them.name} bows to {victor.name} and sends tribute."
        events.add(tired, "tribute", text, victor.name)
        events.add(other, "tribute", text, them.name)
        return
    for pid in besieged:
        capture(state, other, pid, events)
    make_peace(state, tired, other, events)
    add_grievance(state, tired, other, 1500)
    names = ", ".join(state.world.geography[p].name for p in besieged)
    text = f"Worn out by war, {them.name} cedes {names} to {victor.name} for peace."
    events.add(tired, "ceded", text, names)
    events.add(other, "ceded", text, names)


def make_peace(state: GameState, a: str, b: str, events: EventLog) -> None:
    """End a war. The side that lost more ground carries a grievance away."""
    rel = state.relations.get(f"{a}|{b}" if a < b else f"{b}|{a}")
    if rel is None or rel.status is not RelationStatus.WAR:
        return
    losses = dict(rel.losses)
    set_status(state, a, b, RelationStatus.HOSTILE)
    for army in state.armies.values():  # armies in the other's land march home
        other = b if army.owner == a else a if army.owner == b else None
        if other is not None and state.provinces[army.province].owner == other:
            army.province = state.civs[army.owner].capital
            army.target = None
            army.siege_bp = 0
            if army.stance == "pillage":
                army.stance = "defend"
    loser = (
        a
        if losses.get(a, 0) > losses.get(b, 0)
        else b
        if losses.get(b, 0) > losses.get(a, 0)
        else None
    )
    if loser is not None:
        winner = b if loser == a else a
        add_grievance(state, loser, winner, state.world.rules.rivals.war_grievance_bp)
    names = f"{state.civs[a].name} and {state.civs[b].name}"
    events.add(a, "peace", f"Peace between {names}.", state.civs[b].name)
    events.add(b, "peace", f"Peace between {names}.", state.civs[a].name)

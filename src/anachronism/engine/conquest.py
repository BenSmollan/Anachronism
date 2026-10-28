"""Taking a province (D-273): a garrison behind the walls, to be stormed or starved out.

Every province's owner keeps a garrison in its city: a share of its people under arms, more
behind built walls, twice as many in a capital. An army alone in an enemy province lays siege:
each turn its engines and numbers batter the walls, the garrison goes hungry, and the
besiegers sicken in their lines. Then it takes the city one of three ways (``Army.assault``):

- ``breach`` (the usual): storm the city once the walls are down;
- ``now``: storm at once, against walls still standing (far bloodier);
- ``starve``: never storm; wait until hunger and desertion leave no garrison, and the city
  opens its gates.

A storm is a battle (the same three phases, plans, formations and wings as in the field)
against the garrison, which fights from walls and streets with extra power. Beaten, the
besiegers fall back and the walls are rebuilt; victorious, they sack the city.

A city taken pays: spoils from the loser's treasury (twice as much, and some of its people,
when stormed and sacked), prestige at court (three times for a capital), veterancy and
morale for the army. Its new garrison starts small and is rebuilt over the turns of peace.
"""

from __future__ import annotations

from typing import Any

from anachronism.engine.aid import grateful, liberator
from anachronism.engine.armies import (
    _casualties,
    _enemies_here,
    at_war_with,
    battle,
    composition,
    pillage,
    preview,
    siege_progress,
)
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP, apply_bp, clamp
from anachronism.engine.power import trait_bp
from anachronism.engine.rivals import relation
from anachronism.engine.rng import GameRng
from anachronism.engine.state import Army, GameState, Pledge
from anachronism.engine.tactics import commander
from anachronism.engine.war import capture, defence_bp

GARRISON = "garrison_"
"""Id prefix of a garrison drawn up for a storm (never kept in the state between turns)."""


def full_garrison(state: GameState, province_id: str) -> int:
    """The men a province's owner keeps in its city at full strength (0 if it has no owner)."""
    rules = state.world.rules.armies
    province = state.provinces[province_id]
    if province.owner is None:
        return 0
    men = apply_bp(province.population // rules.garrison_people_per_man, rules.garrison_share_bp)
    men += province.walls * rules.garrison_wall_men
    if state.civs[province.owner].capital == province_id:
        men = men * rules.garrison_capital_bp // BP
    return men


def garrison_men(state: GameState, province_id: str) -> int:
    """The men in a province's garrison now (hunger and storms wear it down)."""
    return apply_bp(full_garrison(state, province_id), state.provinces[province_id].garrison_bp)


def walls_standing(state: GameState, army: Army) -> int:
    """Share (bp) of a besieged city's defences still standing against this army's siege."""
    owner = state.provinces[army.province].owner
    if owner is None:
        return 0
    defence = defence_bp(state, owner, army.province)
    return max(0, defence - army.siege_bp) * BP // max(1, defence)


def garrison_army(state: GameState, besieger: Army) -> Army | None:
    """The garrison of the city ``besieger`` stands before, drawn up to meet a storm.

    It is not put in the state: a storm adds it for the battle and takes it away after.
    """
    rules = state.world.rules.armies
    province = state.provinces[besieger.province]
    owner = province.owner
    men = garrison_men(state, besieger.province)
    if owner is None or men < 1:
        return None
    walls = (
        rules.storm_defence_bp
        + rules.storm_unbreached_bp * walls_standing(state, besieger) // BP
        + province.walls * rules.storm_wall_level_bp
    )
    place = state.world.geography[besieger.province].name.split(" (")[0]
    return Army(
        id=GARRISON + besieger.province,
        owner=owner,
        name=f"{place} garrison",
        province=besieger.province,
        troops=composition(state, owner, men, "infantry"),
        stance="hold",
        dug_in=True,
        garrison=True,
        walls_bp=walls,
    )


def storm_outlook(state: GameState, army: Army) -> dict[str, Any]:
    """What the city before ``army`` holds, and how a storm would go (for the view)."""
    rules = state.world.rules.armies
    owner = state.provinces[army.province].owner
    garrison = garrison_army(state, army)
    starve = max(1, rules.garrison_starve_bp)
    out: dict[str, Any] = {
        "garrison": garrison.men if garrison else 0,
        "full": full_garrison(state, army.province),
        "walls_bp": walls_standing(state, army),
        "starve_turns": -(-state.provinces[army.province].garrison_bp // starve),
        "breach_turns": -(
            -max(0, defence_bp(state, owner, army.province) - army.siege_bp)
            // max(1, siege_progress(state, army))
        )
        if owner is not None
        else 0,
        "win_bp": BP,
        "wings": [],
    }
    if garrison is not None:
        attackers = _attackers(state, army)
        seen = preview(state, attackers, [garrison], army.province, True)
        out["win_bp"] = seen["win_bp"]
        out["wings"] = seen["wings"]
    return out


def _attackers(state: GameState, army: Army) -> list[Army]:
    """Every army of the besieger's owner before the city, not off plundering (largest first)."""
    return sorted(
        (
            a
            for a in state.armies.values()
            if a.province == army.province and a.owner == army.owner and a.stance != "pillage"
        ),
        key=lambda a: (-a.men, a.id),
    )


def sieges(state: GameState, events: EventLog, rng: GameRng | None = None) -> None:
    """Armies alone in enemy provinces besiege them: batter, starve, and storm or wait."""
    rng = rng if rng is not None else GameRng(state.rng)
    rules = state.world.rules.armies
    besieged: set[str] = set()
    for army_id in sorted(state.armies):
        army = state.armies.get(army_id)
        if army is None:
            continue
        owner = state.provinces[army.province].owner
        if owner is None or owner == army.owner or not at_war_with(state, army.owner, owner):
            army.siege_bp = 0
            continue
        if _enemies_here(state, army):
            continue
        place = state.world.geography[army.province].name
        if army.stance == "pillage":
            pillage(state, army, owner, events)
            continue
        lead = _attackers(state, army)[0]
        if lead.id != army.id:
            continue  # the largest army before the city conducts the siege
        besieged.add(army.province)
        province = state.provinces[army.province]
        if army.siege_bp == 0:
            events.add(
                owner, "siege", f"{state.civs[army.owner].adjective} armies besiege {place}.", place
            )
        army.siege_bp += siege_progress(state, army)
        province.garrison_bp = max(0, province.garrison_bp - rules.garrison_starve_bp)
        sick = rules.siege_sickness_bp * BP // (BP + trait_bp(state, army, "quartermaster"))
        for camp in _attackers(state, army):
            _casualties(camp, sick)
        if garrison_men(state, army.province) == 0:
            _surrender(state, army, owner, events)
            continue
        breached = army.siege_bp >= defence_bp(state, owner, army.province)
        storm = army.assault == "now" or (army.assault == "breach" and breached)
        if storm and _will_storm(state, army):
            _storm(state, army, owner, rng, events)
    for province_id in sorted(state.provinces):
        if province_id not in besieged:
            province = state.provinces[province_id]
            province.garrison_bp = min(BP, province.garrison_bp + rules.garrison_recover_bp)


def _will_storm(state: GameState, army: Army) -> bool:
    """A cautious general does not throw his men at walls he expects to hold."""
    if commander(_attackers(state, army)).engage != "cautious":
        return True
    share = int(storm_outlook(state, army)["win_bp"])
    return share >= state.world.rules.armies.cautious_win_share_bp


def _storm(state: GameState, army: Army, owner: str, rng: GameRng, events: EventLog) -> None:
    """The besiegers go over the walls: a battle against the garrison."""
    garrison = garrison_army(state, army)
    if garrison is None:
        _surrender(state, army, owner, events)
        return
    province = state.provinces[army.province]
    full = max(1, full_garrison(state, army.province))
    standing = walls_standing(state, army)
    adjective = state.civs[owner].adjective
    walls = (
        "its walls breached"
        if standing == 0
        else f"its walls still {standing * 100 // BP}% standing"
    )
    told = (
        f"The {adjective} garrison, {garrison.men:,} men, holds the city, {walls}:"
        " they fight from walls, gates and streets."
    )
    attackers = _attackers(state, army)
    taker = army.owner
    state.armies[garrison.id] = garrison
    winner = battle(state, army.province, attackers, [garrison], rng, events, storm=told)
    left = state.armies.pop(garrison.id, None)
    province.garrison_bp = clamp((left.men if left else 0) * BP // full, 0, BP)
    if winner == taker:
        _take(state, army, owner, events, stormed=True)


def _surrender(state: GameState, army: Army, owner: str, events: EventLog) -> None:
    """Hunger has done its work: the city opens its gates."""
    place = state.world.geography[army.province].name
    text = (
        f"Starved and abandoned, {place} opens its gates to the {state.civs[army.owner].adjective}."
    )
    events.add(army.owner, "surrender", text, place)
    events.add(owner, "surrender", text, place)
    _take(state, army, owner, events, stormed=False)


def _take(state: GameState, army: Army, owner: str, events: EventLog, stormed: bool) -> None:
    """The city falls: it changes hands, and the conquerors take their spoils."""
    friend = liberator(state, army.owner, army.province)
    if friend is not None:
        _liberate(state, army, owner, friend, events, stormed)
        return
    rules = state.world.rules.armies
    province_id = army.province
    province = state.provinces[province_id]
    taker = state.civs[army.owner]
    loser = state.civs[owner]
    capital = loser.capital == province_id
    # the spoils: the city's share of the loser's treasury, doubled by a sack
    loot = province.population // 1000 * rules.spoils_per_1000
    sacked = 0
    if stormed:
        loot = loot * rules.sack_spoils_bp // BP
        sacked = apply_bp(province.population, rules.sack_people_bp)
        province.population -= sacked
    loot = clamp(loot, 0, loser.stockpiles.wealth)
    loser.stockpiles.wealth -= loot
    taker.stockpiles.wealth += loot
    capture(state, army.owner, province_id, events)
    for camp in _attackers(state, army):
        camp.siege_bp = 0
        camp.veterancy_bp = min(
            rules.max_veterancy_bp, camp.veterancy_bp + rules.conquest_veterancy_bp
        )
        camp.morale_bp = min(BP, camp.morale_bp + rules.conquest_morale_bp)
    glory = rules.conquest_legitimacy_bp * (3 if capital else 1)
    taker.stats.legitimacy_bp = clamp(taker.stats.legitimacy_bp + glory, 0, BP)
    province.garrison_bp = rules.conquered_garrison_bp
    rel = relation(state, army.owner, owner)
    if rel is not None:
        rival_rules = state.world.rules.rivals
        rel.losses[owner] = rel.losses.get(owner, 0) + 1
        rel.weariness[owner] = rel.weariness.get(owner, 0) + rival_rules.weariness_per_loss_bp
    place = state.world.geography[province_id].name
    how = "stormed and sacked" if stormed else "starved into surrender"
    parts = [f"{loot:,} wealth"]
    if sacked:
        parts.append(f"{sacked:,} of its people killed or carried off")
    text = (
        f"{place} is {how}. Spoils: {', '.join(parts)}; the {army.name} grows in renown,"
        f" and your prestige at home rises{' - an enemy capital!' if capital else '.'}"
    )
    events.add(
        army.owner,
        "spoils",
        text,
        place,
        spoils={
            "wealth": loot,
            "sacked": sacked,
            "stormed": stormed,
            "capital": capital,
            "prestige_bp": glory,
            "veterancy_bp": rules.conquest_veterancy_bp,
            "army": army.name,
            "province": province_id,
        },
    )


def _liberate(
    state: GameState, army: Army, owner: str, pledge: Pledge, events: EventLog, stormed: bool
) -> None:
    """A friend's city taken back from its attacker goes home to the friend (D-277)."""
    rules = state.world.rules.armies
    province_id = army.province
    province = state.provinces[province_id]
    friend = state.civs[pledge.friend]
    capture(state, pledge.friend, province_id, events)
    province.garrison_bp = rules.conquered_garrison_bp
    for camp in _attackers(state, army):
        camp.siege_bp = 0
        camp.veterancy_bp = min(
            rules.max_veterancy_bp, camp.veterancy_bp + rules.conquest_veterancy_bp
        )
        camp.morale_bp = min(BP, camp.morale_bp + rules.conquest_morale_bp)
    taker = state.civs[army.owner]
    glory = rules.conquest_legitimacy_bp
    taker.stats.legitimacy_bp = clamp(taker.stats.legitimacy_bp + glory, 0, BP)
    rel = relation(state, army.owner, owner)
    if rel is not None:
        rival_rules = state.world.rules.rivals
        rel.losses[owner] = rel.losses.get(owner, 0) + 1
        rel.weariness[owner] = rel.weariness.get(owner, 0) + rival_rules.weariness_per_loss_bp
    grateful(state, pledge, state.world.rules.rivals.aid_liberation_bp, events)
    place = state.world.geography[province_id].name
    how = "stormed" if stormed else "starved into surrender"
    text = (
        f"{place} is {how} and handed back to {friend.name}: a liberation, not a conquest."
        f" {friend.name} will remember it, and the {army.name} grows in renown."
    )
    events.add(
        army.owner,
        "spoils",
        text,
        place,
        spoils={
            "wealth": 0,
            "sacked": 0,
            "stormed": stormed,
            "capital": False,
            "prestige_bp": glory,
            "veterancy_bp": rules.conquest_veterancy_bp,
            "army": army.name,
            "province": province_id,
            "liberated": friend.name,
            "gratitude_bp": pledge.gratitude_bp,
        },
    )

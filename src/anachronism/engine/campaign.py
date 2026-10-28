"""Chronicle mode (D-120): playing along history, chapter by chapter.

At the start and after every turn the next chapter whose year has come is opened, if its
conditions hold; chapters whose moment has passed without them (``until_year``) are passed
over, and the chronicle says how history turned. One chapter waits at a time; the player
answers it with a ``ChooseChapter`` action (a recorded action, so replays stay exact). A
chapter still waiting when the turn ends is settled the way history went. The almanac tells
what happened elsewhere in the world each year.

Everything else in the game goes on between chapters: ideas ahead of their time, buildings,
armies, diplomacy. Ideas the player has brought in can unlock choices history never had.
"""

from __future__ import annotations

from anachronism.content.schema import Chapter, ChapterChoice, RelationStatus
from anachronism.engine.dilemmas import apply_choice, fill
from anachronism.engine.events import EventLog
from anachronism.engine.fixed import BP
from anachronism.engine.rivals import (
    add_grievance,
    alive,
    declare_war,
    make_tributary,
    set_status,
    status,
    strength,
)
from anachronism.engine.state import ChapterResult, Fleet, GameState
from anachronism.engine.tech import is_adopted

PASSED_OVER = -1


def year_text(year: int) -> str:
    """264 BC, AD 9."""
    return f"{-year} BC" if year < 0 else f"AD {year}"


def fits(state: GameState, chapter: Chapter) -> bool:
    """True when a chapter's conditions hold now."""
    me = state.player_civ
    if any(c not in state.civs or not alive(state, c) for c in (me, *chapter.needs_alive)):
        return False
    if any(status(state, me, c) is not RelationStatus.WAR for c in chapter.needs_war_with):
        return False
    if any(status(state, me, c) is RelationStatus.WAR for c in chapter.needs_peace_with):
        return False
    for other, ratio_bp in sorted(chapter.needs_stronger_than.items()):
        theirs = strength(state, other) if other in state.civs else 0
        if theirs and strength(state, me) * BP < ratio_bp * theirs:
            return False
    for pid, owner in chapter.needs_owner.items():
        held = state.provinces[pid].owner if pid in state.provinces else None
        if (held or "nobody") != owner:
            return False
    for pid, owner in chapter.needs_not_owner.items():
        held = state.provinces[pid].owner if pid in state.provinces else None
        if (held or "nobody") == owner:
            return False
    if any(state.chapters_done.get(c, PASSED_OVER) == PASSED_OVER for c in chapter.after):
        return False
    return all(state.chapters_done.get(c) == i for c, i in chapter.after_choice.items())


def available(state: GameState, choice: ChapterChoice) -> bool:
    """True if the player can take this choice (its ideas are in use)."""
    civ = state.civs[state.player_civ]
    return all(is_adopted(civ, t) for t in choice.needs_adopted)


def historical_index(chapter: Chapter) -> int:
    """The choice history made (the first one, if none is marked)."""
    return next((i for i, c in enumerate(chapter.choices) if c.historical), 0)


def advance(state: GameState, events: EventLog) -> None:
    """Settle a waiting chapter as history did; pass over lapsed ones; open the next."""
    if not state.chronicle_mode or not state.world.chapters:
        return
    if state.chapter is not None:
        chapter = state.world.chapters[state.chapter]
        _settle(state, chapter, historical_index(chapter), events, by_court=True)
    open_next(state, events)


def open_next(state: GameState, events: EventLog) -> None:
    """Open the next chapter whose year has come; pass over those whose moment has gone.

    Answering a chapter calls this too, so that two moments of the same year are both met
    in that year (D-134).
    """
    for chapter in state.world.chapters.values():  # in year order
        if chapter.id in state.chapters_done:
            continue
        if chapter.year > state.year:
            return
        if fits(state, chapter):
            state.chapter = chapter.id
            events.add(state.player_civ, "chapter", chapter.title, chapter.title)
            return
        if chapter.until_year is None or state.year >= chapter.until_year:
            state.chapters_done[chapter.id] = PASSED_OVER
            if chapter.diverged:
                events.add(state.player_civ, "history_turned", fill(state, chapter.diverged))


def choose(state: GameState, chapter_id: str, index: int) -> tuple[bool, str]:
    """The player answers the waiting chapter."""
    chapter = state.world.chapters.get(chapter_id)
    if chapter is None or state.chapter != chapter_id:
        return False, "that chapter is not before you"
    if not 0 <= index < len(chapter.choices):
        return False, "no such choice"
    if not available(state, chapter.choices[index]):
        names = ", ".join(
            state.tech_nodes[t].name
            for t in chapter.choices[index].needs_adopted
            if t in state.tech_nodes
        )
        return False, f"that path needs {names} in use"
    events = EventLog(turn=state.turn, year=state.year)
    message = _settle(state, chapter, index, events, by_court=False)
    open_next(state, events)
    state.events.extend(events.items)
    return True, message


def _settle(
    state: GameState, chapter: Chapter, index: int, events: EventLog, *, by_court: bool
) -> str:
    choice = chapter.choices[index]
    state.chapter = None
    state.chapters_done[chapter.id] = index
    outcome = apply_choice(state, choice)
    _deeds(state, chapter, choice, events)
    state.chapter_result = ChapterResult(
        chapter=chapter.id,
        choice=index,
        outcome=outcome,
        history=fill(state, chapter.history),
        historical=choice.historical,
        benchmark=benchmark(state, chapter),
    )
    kind = "chapter_settled" if by_court else "chapter_chosen"
    told = f"{chapter.title}: {outcome}" if not by_court else f"Your advisers chose: {outcome}"
    events.add(state.player_civ, kind, told, chapter.title)
    return outcome


def benchmark(state: GameState, chapter: Chapter) -> str:
    """How the player's state compares with the real one at this date."""
    if chapter.benchmark_provinces is None:
        return ""
    me = state.civs[state.player_civ]
    held = len(state.owned_provinces(me.id))
    real = chapter.benchmark_provinces
    when = year_text(chapter.year)
    verdict = "ahead of" if held > real else "behind" if held < real else "level with"
    return (
        f"In {when} the real {me.name} held {real} province{'s' if real != 1 else ''};"
        f" yours holds {held} -"
        f" {verdict} history."
    )


def _deeds(state: GameState, chapter: Chapter, choice: ChapterChoice, events: EventLog) -> None:
    """What the choice does in the world."""
    from anachronism.engine.armies import raise_army  # armies builds on much of the engine
    from anachronism.engine.navies import best_ship, seas_of
    from anachronism.engine.war import capture, make_peace

    me = state.player_civ
    civ = state.civs[me]
    deeds = choice.deeds
    for other in deeds.peace_with:
        if other in state.civs and status(state, me, other) is RelationStatus.WAR:
            make_peace(state, me, other, events)
    for other in deeds.war_with:
        if other in state.civs and alive(state, other):
            declare_war(state, me, other, events)
    for other in (*deeds.ally_with, *deeds.tributaries):
        if other not in state.civs or not alive(state, other):
            continue
        if status(state, me, other) is RelationStatus.WAR:
            make_peace(state, me, other, events)
        bond = RelationStatus.ALLIED if other in deeds.ally_with else RelationStatus.TRIBUTARY
        set_status(state, me, other, bond)
        if bond is RelationStatus.TRIBUTARY:
            make_tributary(state, me, other)
    for other in deeds.break_away:
        if other in state.civs and status(state, me, other) in (
            RelationStatus.ALLIED,
            RelationStatus.TRIBUTARY,
        ):
            set_status(state, me, other, RelationStatus.HOSTILE)
    taken: list[str] = []
    for pid in deeds.take:
        province = state.provinces.get(pid)
        if province is None or province.owner == me:
            continue
        if province.owner is None:
            province.owner = me
            province.held_since = state.turn
        else:
            capture(state, me, pid, events)
        taken.append(pid)
    for other in deeds.conquer:
        if other in state.civs and other != me:
            for pid in state.owned_provinces(other):
                capture(state, me, pid, events)
                taken.append(pid)
    for pid in taken:  # the army that took it stays to hold it down (D-122)
        _garrison(state, me, pid)
    for pid in deeds.give:
        province = state.provinces.get(pid)
        if province is None or province.owner != me or len(state.owned_provinces(me)) <= 1:
            continue
        if deeds.give_to and deeds.give_to in state.civs:
            capture(state, deeds.give_to, pid, events)
        else:
            province.owner = None
    if deeds.ships:
        ship = best_ship(state, me)
        ports = [p for p in [civ.capital, *state.owned_provinces(me)] if seas_of(state, p)]
        if ship is not None and ports:
            fleet_id = f"{me}-{chapter.id}"
            state.fleets[fleet_id] = Fleet(
                id=fleet_id,
                owner=me,
                name=f"Fleet of {chapter.title}"[:60],
                sea=seas_of(state, ports[0])[0],
                ship=ship.id,
                ships=deeds.ships,
            )
    if deeds.men and civ.capital in state.provinces and state.provinces[civ.capital].owner == me:
        raise_army(state, me, civ.capital, deeds.men, free=True)
    if deeds.martial_bp:
        civ.martial_bp = max(1_000, civ.martial_bp + deeds.martial_bp)
    new_seat = state.provinces.get(deeds.capital or "")
    if deeds.capital and new_seat is not None and new_seat.owner == me:
        civ.capital = deeds.capital
    if deeds.ruler_falls:
        from anachronism.engine.rulers import succeed

        succeed(state, civ, events, how=deeds.ruler_falls)
    for other, grudge in sorted(deeds.grudges.items()):
        if other in state.civs:
            add_grievance(state, other, me, grudge)


def _garrison(state: GameState, me: str, province_id: str) -> None:
    """Leave enough of the conquering army in a taken province to hold it down."""
    from anachronism.engine.armies import raise_army
    from anachronism.engine.occupation import garrisoned

    province = state.provinces[province_id]
    if province.owner != me or garrisoned(state, province_id):
        return
    need = province.population // state.world.rules.armies.garrison_people_per_man * 3 // 2 + 1
    before = province.population
    army, _ = raise_army(state, me, province_id, need, free=True)
    if army is not None:
        province.population = before  # the garrison are the conquerors, not the conquered
        army.stance = "hold"  # it stays put rather than marching on invaders


def almanac(state: GameState, after_year: int, events: EventLog) -> None:
    """Meanwhile in the world: entries for the years just passed (``after_year`` < y <= now)."""
    for entry in state.world.almanac.values():
        if not after_year < entry.year <= state.year:
            continue
        if any(c not in state.civs or not alive(state, c) for c in entry.needs_alive):
            continue
        events.add(state.player_civ, "almanac", f"{year_text(entry.year)}: {entry.text}")

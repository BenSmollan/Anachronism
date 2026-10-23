"""Chronicle mode for the client (D-120).

The waiting chapter, the last one's aftermath, and how the player's state stands against
history so far.
"""

from __future__ import annotations

import hashlib
from typing import Any

from anachronism.content.loader import Content
from anachronism.content.schema import Chapter
from anachronism.engine.campaign import PASSED_OVER, available, benchmark, year_text
from anachronism.engine.dilemmas import effects_text, fill
from anachronism.engine.state import GameState


def choice_order(state: GameState, chapter: Chapter) -> list[int]:
    """The order the client lists a chapter's choices in (D-265).

    History's choice is not always first: ordinary choices are shuffled by a hash of the
    game's seed and the chapter, so the order is the same every time this chapter is shown
    in this game but differs between chapters and games. Choices that need an idea ahead of
    its time stay last. Display only: actions still name a choice by its index in the file.
    """

    def key(i: int) -> tuple[bool, int]:
        mixed = int.from_bytes(hashlib.sha256(f"{state.seed}:{chapter.id}:{i}".encode()).digest()[:8])
        return bool(chapter.choices[i].needs_adopted), mixed

    return sorted(range(len(chapter.choices)), key=key)


def speaker_card(content: Content, state: GameState, speaker: str) -> dict[str, Any]:
    """Who brings a chapter: a name, a title and a portrait style for the client."""
    player = state.player_civ
    civ_id = speaker if speaker in state.civs else player
    civ_def = content.civs[civ_id]
    if speaker == "ruler" or speaker in state.civs:
        ruler = state.civs[civ_id].ruler or f"The ruler of {state.civs[civ_id].name}"
        name, title, portrait = ruler, f"{civ_def.name}", civ_def.portrait
    else:
        adviser = content.speakers.get(speaker)
        name = adviser.title if adviser else speaker.title()
        title = f"{content.civs[player].adjective} court"
        portrait = (adviser.portrait if adviser else "") or civ_def.portrait
    return {
        "name": name,
        "title": title,
        "portrait": portrait,
        "culture": civ_def.portrait,
        "colour": civ_def.colour,
        "symbol": civ_def.symbol or "",
        "civ": civ_id,
    }


def chronicle_block(content: Content, state: GameState) -> dict[str, Any] | None:
    """Everything the client shows of chronicle mode, or None in free play."""
    if not state.chronicle_mode:
        return None
    chapters = state.world.chapters
    out: dict[str, Any] = {
        "total": len(chapters),
        "done": sum(1 for v in state.chapters_done.values() if v != PASSED_OVER),
        "passed": sum(1 for v in state.chapters_done.values() if v == PASSED_OVER),
        "chapter": None,
        "result": None,
        "versus": _versus(state),
        "next": None,
    }
    if state.chapter is not None:
        chapter = chapters[state.chapter]
        out["chapter"] = {
            "id": chapter.id,
            "title": chapter.title,
            "year": year_text(chapter.year),
            "place": chapter.place,
            "speaker": {
                **speaker_card(content, state, chapter.speaker),
                **({"name": chapter.speaker_name} if chapter.speaker_name else {}),
                **({"title": chapter.speaker_title} if chapter.speaker_title else {}),
            },
            "story": fill(state, chapter.story).split("\n\n"),
            "choices": [
                {
                    "index": i,
                    "label": c.label,
                    "hint": effects_text(c) + _deeds_text(state, c.deeds),
                    "locked": ""
                    if available(state, c)
                    else "needs "
                    + ", ".join(
                        state.tech_nodes[t].name for t in c.needs_adopted if t in state.tech_nodes
                    ),
                    "anachronism": bool(c.needs_adopted),
                }
                for i, c in ((i, chapter.choices[i]) for i in choice_order(state, chapter))
            ],
        }
    result = state.chapter_result
    if result is not None and result.chapter in chapters:
        chapter = chapters[result.chapter]
        historical = next((c.label for c in chapter.choices if c.historical), "")
        out["result"] = {
            "title": chapter.title,
            "year": year_text(chapter.year),
            "chose": chapter.choices[result.choice].label,
            "outcome": result.outcome,
            "history": result.history,
            "historical": result.historical,
            "history_chose": historical,
            "benchmark": result.benchmark,
        }
    upcoming = [c for c in chapters.values() if c.id not in state.chapters_done]
    if upcoming and state.chapter is None:
        out["next"] = {"title": upcoming[0].title, "year": year_text(upcoming[0].year)}
    if not upcoming and state.chapter is None and chapters:
        out["verdict"] = _verdict(state)
    return out


def _verdict(state: GameState) -> str:
    """The end of the chronicle: did the player outdo history?"""
    marks = [c for c in state.world.chapters.values() if c.benchmark_provinces is not None]
    me = state.civs[state.player_civ]
    held = len(state.owned_provinces(me.id))
    real = max((c.benchmark_provinces or 0) for c in marks) if marks else held
    same = sum(
        1
        for cid, choice in state.chapters_done.items()
        if choice >= 0 and state.world.chapters[cid].choices[choice].historical
    )
    played = sum(1 for choice in state.chapters_done.values() if choice >= 0)
    if held > real:
        judged = "You have outdone history."
    elif held == real:
        judged = "You have matched history - no small thing."
    else:
        judged = "History did better than you."
    return (
        f"The chronicle is complete. At its height the real {me.name} held {real} provinces;"
        f" yours holds {held}. You chose as history did in {same} of {played} chapters."
        f" {judged}"
    )


def _versus(state: GameState) -> str:
    """The latest yardstick: the real state at the most recent date with one."""
    marks = [
        c
        for c in state.world.chapters.values()
        if c.benchmark_provinces is not None and c.year <= state.year
    ]
    return benchmark(state, marks[-1]) if marks else ""


def _deeds_text(state: GameState, deeds: Any) -> str:
    """A few words on what a choice does in the world."""

    def names(ids: tuple[str, ...]) -> str:
        return ", ".join(state.civs[i].name if i in state.civs else i for i in ids)

    parts = []
    if deeds.war_with:
        parts.append(f"war with {names(deeds.war_with)}")
    if deeds.peace_with:
        parts.append(f"peace with {names(deeds.peace_with)}")
    if deeds.ally_with:
        parts.append(f"alliance with {names(deeds.ally_with)}")
    if deeds.tributaries:
        parts.append(f"{names(deeds.tributaries)} pays tribute")
    if deeds.take:
        places = ", ".join(
            state.world.geography[p].name for p in deeds.take if p in state.world.geography
        )
        parts.append(f"gain {places}")
    if deeds.conquer:
        parts.append(f"{names(deeds.conquer)} falls to you")
    if deeds.give:
        places = ", ".join(
            state.world.geography[p].name for p in deeds.give if p in state.world.geography
        )
        parts.append(f"lose {places}")
    if deeds.break_away:
        parts.append(f"{names(deeds.break_away)} breaks away")
    if deeds.capital and deeds.capital in state.world.geography:
        parts.append(f"the court moves to {state.world.geography[deeds.capital].name}")
    if deeds.ships:
        parts.append(f"{deeds.ships} warships")
    if deeds.men:
        parts.append(f"{deeds.men:,} men")
    if deeds.martial_bp:
        more = "more" if deeds.martial_bp > 0 else "fewer"
        parts.append(f"for good, {abs(deeds.martial_bp) // 100}% {more} men can be called to arms")
    return ("; " if parts else "") + "; ".join(parts)

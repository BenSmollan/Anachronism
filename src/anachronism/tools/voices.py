"""Who speaks, and what they say, after something happens in the game (step 2.12).

Lines come from content (``dialogue``); this picks the moments worth a word, the speaker
(the player's ruler, an adviser or a rival ruler) and one line, filled in. The choice is
deterministic (a hash of seed, turn and moment), so the same game always says the same.
"""

from __future__ import annotations

import zlib
from typing import Any

from anachronism.content.loader import Content
from anachronism.engine.state import Event, GameState

PRIORITY = (
    "victory", "defeat", "restoration", "dynasty", "collapse", "ruler_died", "capital_lost", "war",
    "ally_attacked", "coalition",
    "province_lost", "uprising", "army_lost", "battle_lost", "sea_battle_lost", "siege",
    "pillaged", "blockade", "crossing_barred", "battle_won", "sea_battle_won", "uprising_won",
    "pillage",
    "conquest", "disaster", "revolt", "famine", "riot", "peace", "adopted", "imitation",
    "news", "breakthrough", "discovery", "suspicion", "framing", "resistance", "setback",
    "stalled", "widespread", "consequence", "blessing", "faith",
)  # fmt: skip
"""Moments in order of importance; at most ``MAX_VOICES`` are spoken per turn."""

MAX_VOICES = 2
AHEAD_YEARS = 100
"""A rival's adoption is remarked on when the idea is at least this far ahead of its time."""


def year_text(year: int) -> str:
    """``350 BC`` or ``AD 200``."""
    return f"{-year} BC" if year < 0 else f"AD {year}"


def speak(
    content: Content,
    state: GameState,
    moment: str,
    subject: str = "",
    rival: str | None = None,
) -> dict[str, Any] | None:
    """One character's line for a moment, or None if the content has nothing to say."""
    dialogue = content.dialogue.get(moment)
    if dialogue is None:
        return None
    player = state.player_civ

    def ruler_of(civ_id: str) -> str:
        ruler = state.civs[civ_id].ruler
        return ruler if ruler else f"the ruler of {state.civs[civ_id].name}"

    speaker_civ = rival if dialogue.speaker == "rival" and rival else player
    civ_def = content.civs[speaker_civ]
    if dialogue.speaker in ("ruler", "rival"):
        name = ruler_of(speaker_civ)
        title = civ_def.name if speaker_civ == player else f"Ruler of {civ_def.name}"
        portrait = civ_def.portrait
    else:
        adviser = content.speakers[dialogue.speaker]
        name = adviser.title
        title = adviser.subtitle or f"{content.civs[player].adjective} court"
        portrait = adviser.portrait or civ_def.portrait
    key = f"{state.seed}:{state.turn}:{moment}:{speaker_civ}:{subject}".encode()
    line = dialogue.lines[zlib.crc32(key) % len(dialogue.lines)]
    text = line.format(
        civ=state.civs[player].name,
        ruler=ruler_of(player),
        subject=subject,
        year=year_text(state.year),
        rival=state.civs[rival].name if rival else "",
        rival_ruler=ruler_of(rival) if rival else "",
        adjective=state.civs[player].adjective,
        rival_adjective=state.civs[rival].adjective if rival else "",
    )
    return {
        "moment": moment,
        "speaker": dialogue.speaker,
        "name": name[:1].upper() + name[1:],
        "title": title,
        "portrait": portrait,
        "culture": civ_def.portrait,
        "colour": civ_def.colour,
        "emblem": civ_def.emblem or civ_def.adjective[:1],
        "symbol": civ_def.symbol or "",
        "civ": speaker_civ,
        "subject": subject,
        "text": text,
    }


def adviser_voice(
    content: Content, state: GameState, role: str, text: str, mood: str
) -> dict[str, Any]:
    """A speech bubble for an adviser's reaction written by the model (not from dialogue)."""
    player = state.player_civ
    civ_def = content.civs[player]
    adviser = content.speakers.get(role)
    return {
        "moment": "idea",
        "speaker": role,
        "name": adviser.title if adviser else role.title(),
        "title": (adviser.subtitle if adviser else "") or f"{civ_def.adjective} court",
        "portrait": (adviser.portrait if adviser else "") or civ_def.portrait,
        "culture": civ_def.portrait,
        "colour": civ_def.colour,
        "emblem": civ_def.emblem or civ_def.adjective[:1],
        "symbol": civ_def.symbol or "",
        "civ": player,
        "text": text,
        "mood": mood,
    }


def rival_says(content: Content, state: GameState, rival: str, text: str) -> dict[str, Any]:
    """A speech bubble for a rival ruler's own words (decided with the model)."""
    civ_def = content.civs[rival]
    ruler = state.civs[rival].ruler or f"the ruler of {state.civs[rival].name}"
    return {
        "moment": "rival_counsel",
        "speaker": "rival",
        "name": ruler[:1].upper() + ruler[1:],
        "title": f"Ruler of {civ_def.name}",
        "portrait": civ_def.portrait,
        "culture": civ_def.portrait,
        "colour": civ_def.colour,
        "emblem": civ_def.emblem or civ_def.adjective[:1],
        "symbol": civ_def.symbol or "",
        "civ": rival,
        "subject": "",
        "text": text,
        "source": "model",
    }


def opening_voices(content: Content, state: GameState) -> list[dict[str, Any]]:
    """A new game opens with the steward's briefing on the moment, then the ruler's welcome."""
    voices: list[dict[str, Any]] = []
    scenario = content.scenarios.get(state.world.scenario_id)
    start = scenario.civs.get(state.player_civ) if scenario else None
    if start is not None and start.pitch:
        voices.append(adviser_voice(content, state, "steward", start.pitch, "neutral"))
        voices[-1]["moment"] = "briefing"
    welcome = speak(content, state, "game_start")
    if welcome:
        voices.append(welcome)
    return voices


def civ_named(state: GameState, name: str) -> str | None:
    """The id of the civilisation called ``name``, if any."""
    for civ_id in sorted(state.civs):
        if state.civs[civ_id].name == name:
            return civ_id
    return None


def _rival_speaks(content: Content, state: GameState, events: list[Event]) -> dict[str, Any] | None:
    """A rival ruler's word to the player when they declare war or make peace."""
    for event in events:
        if event.civ != state.player_civ:
            continue
        if event.kind == "war" and "declared war on" in event.message:
            moment = "rival_war"
        elif event.kind == "peace":
            moment = "rival_peace"
        else:
            continue
        rival = civ_named(state, event.subject)
        if rival is not None and rival != state.player_civ:
            return speak(content, state, moment, event.subject, rival=rival)
    return None


def _rival_boasts(content: Content, state: GameState, events: list[Event]) -> dict[str, Any] | None:
    """A rival ruler's boast when their court adopts something far ahead of its time."""
    by_name = {node.name: node for node in state.tech_nodes.values()}
    for event in events:
        node = by_name.get(event.subject)
        if (
            event.kind == "adopted"
            and event.civ not in (None, state.player_civ)
            and node is not None
            and node.year - state.year >= AHEAD_YEARS
        ):
            return speak(content, state, "rival_adopted", event.subject, rival=event.civ)
    return None


def voices_for_turn(
    content: Content, state: GameState, events: list[Event]
) -> list[dict[str, Any]]:
    """What the advisers (and one rival) have to say about the turn just played."""
    player = state.player_civ
    mine = {e.kind: e for e in events if e.civ == player}
    said: list[dict[str, Any]] = []
    if not state.civs[player].ruler:  # an unnamed ruler (a republic's magistrates): no eulogy
        mine.pop("ruler_died", None)
    for moment in PRIORITY:
        if moment in mine and len(said) < MAX_VOICES:
            voice = speak(content, state, moment, mine[moment].subject)
            if voice:
                said.append(voice)
    rival = _rival_speaks(content, state, events) or _rival_boasts(content, state, events)
    if rival:
        said.append(rival)
    if not said:
        voice = speak(content, state, "quiet")
        if voice:
            said.append(voice)
    return said

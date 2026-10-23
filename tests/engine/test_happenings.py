"""Chance events: they strike where they fit, are softened by advancements, and replay."""

from __future__ import annotations

from anachronism.content.loader import Content
from anachronism.content.schema import EffectType, Happening
from anachronism.engine.effects import Effects
from anachronism.engine.events import EventLog
from anachronism.engine.game import end_turn, new_game
from anachronism.engine.happenings import _apply, _places
from anachronism.engine.state import GameState

PLAGUE = Happening(
    id="test_plague", name="Plague", kind="disaster", message="Plague in {province}.",
    chance_bp=10_000, population_bp=-1000, softened_by=EffectType.HEALTH,
)  # fmt: skip


def effects(**values: int) -> Effects:
    found: Effects = dict.fromkeys(EffectType, 0)  # type: ignore[assignment]
    for name, value in values.items():
        found[EffectType(name)] = value
    return found


def test_happenings_strike_only_where_they_fit(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1, player_civ="rome")
    flood = state.world.happenings["flood"]
    for pid in _places(state, state.civs["rome"], flood):
        assert state.world.geography[pid].river


def test_health_softens_plague(content: Content) -> None:
    def deaths(health: int) -> int:
        state = new_game(content, "punic_wars", seed=1, player_civ="rome")
        capital = state.civs["rome"].capital
        before = state.provinces[capital].population
        _apply(state, state.civs["rome"], PLAGUE, capital, effects(health=health), EventLog(0, 0))
        return before - state.provinces[capital].population

    assert 0 < deaths(2000) < deaths(0)


def test_events_happen_in_long_games_and_replay(content: Content) -> None:
    a: GameState = new_game(content, "punic_wars", seed=6)
    b: GameState = new_game(content, "punic_wars", seed=6)
    kinds: set[str] = set()
    for _ in range(15):
        a, events = end_turn(a)
        b, _ = end_turn(b)
        kinds |= {e.kind for e in events}
    assert a == b
    assert kinds & {"disaster", "blessing"}


def test_consequences_follow_their_advancement(content: Content) -> None:
    from anachronism.content.schema import SocialGroup, Stage
    from anachronism.engine.happenings import strike
    from anachronism.engine.rng import GameRng
    from anachronism.engine.state import TechState

    pamphlets = content.happenings["pamphlet_wars"]
    state = new_game(content, "punic_wars", seed=1, player_civ="rome")
    rome = state.civs["rome"]
    only = {"pamphlet_wars": pamphlets.model_copy(update={"chance_bp": 10_000})}
    state.world = state.world.model_copy(update={"happenings": only})
    log = EventLog(0, 0)
    strike(state, rome, effects(), GameRng.from_seed(1), log)
    assert not log.items  # no printing press, no pamphlets
    rome.tech["printing_press"] = TechState(stage=Stage.ADOPTED)
    clergy = rome.influence[SocialGroup.CLERGY]
    strike(state, rome, effects(), GameRng.from_seed(1), log)
    assert [e.kind for e in log.items] == ["consequence"]
    assert rome.influence[SocialGroup.CLERGY] == max(0, clergy - 800)


def test_a_consequence_must_name_its_cause() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Happening(id="x", name="X", kind="consequence", message="m", chance_bp=1)

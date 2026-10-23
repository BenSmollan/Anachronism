"""Chronicle mode: playing along history in chapters (D-120)."""

from __future__ import annotations

import pytest

from anachronism.content.loader import Content
from anachronism.content.schema import Chapter, ChapterChoice, Deeds, RelationStatus, Stage
from anachronism.engine.actions import ChooseChapter
from anachronism.engine.campaign import PASSED_OVER, historical_index
from anachronism.engine.game import apply_action, end_turn, new_game
from anachronism.engine.rivals import status
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import GameState, TechState
from anachronism.tools.story import chronicle_block


@pytest.fixture
def chronicle(content: Content) -> GameState:
    return new_game(content, "punic_wars", seed=1, player_civ="rome", chronicle=True)


def test_free_play_has_no_chapters(content: Content) -> None:
    state = new_game(content, "punic_wars", seed=1, player_civ="rome")
    assert not state.world.chapters
    assert state.chapter is None
    assert state.world.years_per_turn == 10


def test_the_chronicle_opens_with_its_first_chapter_and_short_turns(
    chronicle: GameState,
) -> None:
    assert chronicle.world.years_per_turn == 2
    assert chronicle.chapter == "rome_messana"
    assert any(e.kind == "almanac" for e in chronicle.events)


def test_a_choice_acts_in_the_world_and_is_compared_with_history(
    chronicle: GameState,
) -> None:
    chapter = chronicle.world.chapters["rome_messana"]
    index = historical_index(chapter)
    state, logged = apply_action(
        chronicle, ChooseChapter(civ="rome", chapter="rome_messana", choice=index)
    )
    assert logged.ok, logged.message
    assert status(state, "rome", "carthage") is RelationStatus.WAR
    assert state.provinces["messana"].owner == "rome"
    assert state.chapter is None
    assert state.chapter_result is not None
    assert state.chapter_result.historical
    assert "real Rome held 8" in state.chapter_result.benchmark


def test_an_unanswered_chapter_goes_as_history_went(chronicle: GameState) -> None:
    state, events = end_turn(chronicle)
    assert state.chapters_done["rome_messana"] == historical_index(
        chronicle.world.chapters["rome_messana"]
    )
    assert any(e.kind == "chapter_settled" for e in events)


def test_a_chapter_whose_world_is_gone_is_passed_over(chronicle: GameState) -> None:
    # refuse Messana: there is no war, so Hiero never changes sides
    refuse = ChooseChapter(civ="rome", chapter="rome_messana", choice=1)
    state, _ = apply_action(chronicle, refuse)
    for _ in range(4):
        if state.chapter is not None:
            chapter = state.world.chapters[state.chapter]
            state, _ = apply_action(
                state,
                ChooseChapter(civ="rome", chapter=chapter.id, choice=historical_index(chapter)),
            )
        state, _ = end_turn(state)
    assert state.chapters_done.get("rome_hiero") == PASSED_OVER


def test_ideas_ahead_of_their_time_open_choices_history_never_had(
    chronicle: GameState,
) -> None:
    fleet = chronicle.world.chapters["rome_fleet"]
    locked = next(i for i, c in enumerate(fleet.choices) if c.needs_adopted)
    chronicle.chapter = "rome_fleet"
    _, logged = apply_action(
        chronicle, ChooseChapter(civ="rome", chapter="rome_fleet", choice=locked)
    )
    assert not logged.ok
    for tech in fleet.choices[locked].needs_adopted:
        chronicle.civs["rome"].tech[tech] = TechState(stage=Stage.ADOPTED)
    block = chronicle_block_for(chronicle)
    shown = next(c for c in block["chapter"]["choices"] if c["index"] == locked)
    assert shown["locked"] == ""
    _, logged = apply_action(
        chronicle, ChooseChapter(civ="rome", chapter="rome_fleet", choice=locked)
    )
    assert logged.ok


def chronicle_block_for(state: GameState) -> dict:  # type: ignore[type-arg]
    from anachronism.content.loader import load_content

    block = chronicle_block(load_content(), state)
    assert block is not None
    return block


def test_chronicle_games_save_and_replay(chronicle: GameState) -> None:
    state, _ = end_turn(chronicle)
    assert dumps(loads(dumps(state))) == dumps(state)


@pytest.fixture
def rome(chronicle: GameState) -> GameState:
    return chronicle


def put_chapter(state: GameState, chapter_id: str, civ: str, **deeds: object) -> None:
    """Add a made-up chapter whose only choice does ``deeds`` (for engine features that the
    scenario's own chapters need not use), and make it the one waiting."""
    chapter = Chapter(
        id=chapter_id,
        scenario="punic_wars",
        civ=civ,
        year=state.year,
        title="A test chapter",
        story="Something happens.",
        choices=(ChapterChoice(label="Do it", outcome="It is done.", deeds=Deeds(**deeds)),),
    )
    state.world = state.world.model_copy(
        update={"chapters": {**state.world.chapters, chapter_id: chapter}}
    )
    state.chapter = chapter_id


def test_reforms_last_and_conquered_land_comes_with_a_garrison(rome: GameState) -> None:
    from anachronism.engine.occupation import garrisoned

    before = rome.civs["rome"].martial_bp
    put_chapter(rome, "test_reform", "rome", martial_bp=5000)
    state, _ = apply_action(rome, ChooseChapter(civ="rome", chapter="test_reform", choice=0))
    assert state.civs["rome"].martial_bp > before
    # Syracuse falls whole: its only province is taken and held
    put_chapter(state, "test_conquest", "rome", conquer=("syracuse",))
    state, _ = apply_action(state, ChooseChapter(civ="rome", chapter="test_conquest", choice=0))
    assert state.civs["syracuse"].collapsed
    assert state.provinces["syr_syracuse"].owner == "rome"
    assert garrisoned(state, "syr_syracuse")
    # a garrison keeps apart from a host passing through
    state, _ = end_turn(state)
    assert garrisoned(state, "syr_syracuse")


def test_a_conquest_waits_until_the_state_is_strong_enough(rome: GameState) -> None:
    from anachronism.engine.campaign import fits

    chapter = Chapter(
        id="test_carthage_falls",
        scenario="punic_wars",
        civ="rome",
        year=rome.year,
        title="Carthage is ripe",
        story="The city lies open.",
        needs_stronger_than={"carthage": 30_000},
        choices=(ChapterChoice(label="Strike", outcome="Done."),),
    )
    assert not fits(rome, chapter)  # Rome is nowhere near three times as strong as Carthage
    rome.civs["carthage"].stockpiles.food = 0
    for pid in rome.owned_provinces("carthage"):
        rome.provinces[pid].population = 1_000
    assert fits(rome, chapter)


@pytest.fixture
def syracuse(content: Content) -> GameState:
    return new_game(content, "punic_wars", seed=1, player_civ="syracuse", chronicle=True)


def test_hiero_is_spared_old_age_until_history_ends_his_reign(
    syracuse: GameState, content: Content
) -> None:
    """The chronicle, not the dice, ends Hiero's reign (D-130): he really died in 215 BC."""
    from anachronism.engine.rulers import spared

    assert syracuse.world.years_per_turn == 2
    civ = syracuse.civs["syracuse"]
    civ.ruler_age = 80  # old enough to die any year
    assert spared(syracuse, civ)
    syracuse.year = -214
    assert not spared(syracuse, civ)
    free = new_game(content, "punic_wars", seed=1, player_civ="syracuse")
    assert not spared(free, free.civs["syracuse"])  # in free play the dice decide


def test_a_chapter_can_end_the_reign(syracuse: GameState) -> None:
    """A chapter's choice can end a reign the way history did, and the heir takes over."""
    put_chapter(syracuse, "test_leontini", "syracuse", ruler_falls="is assassinated at Leontini")
    state, _ = apply_action(
        syracuse, ChooseChapter(civ="syracuse", chapter="test_leontini", choice=0)
    )
    civ = state.civs["syracuse"]
    assert civ.ruler == "Hieronymus"
    assert civ.rulers == 2
    assert state.chapter_result is not None


def test_the_court_can_move_and_a_tributary_can_break_away(content: Content) -> None:
    """Carthage's court moves to another province, and Numidia slips out of its orbit."""
    state = new_game(content, "punic_wars", seed=1, player_civ="carthage", chronicle=True)
    assert status(state, "carthage", "numidia") is RelationStatus.TRIBUTARY
    put_chapter(state, "test_move", "carthage", capital="car_byzacena", break_away=("numidia",))
    state, _ = apply_action(state, ChooseChapter(civ="carthage", chapter="test_move", choice=0))
    assert state.civs["carthage"].capital == "car_byzacena"
    assert status(state, "carthage", "numidia") is RelationStatus.HOSTILE


def test_heirs_are_spared_until_their_reigns_really_ended(syracuse: GameState) -> None:
    """Hieronymus died in 214 BC; in the chronicle old age does not take him first."""
    from anachronism.engine.events import EventLog
    from anachronism.engine.rulers import spared, succeed

    civ = syracuse.civs["syracuse"]
    succeed(syracuse, civ, EventLog(syracuse.turn, syracuse.year), how="dies")
    assert civ.ruler == "Hieronymus"
    syracuse.year = -220
    assert spared(syracuse, civ)
    syracuse.year = -214
    assert not spared(syracuse, civ)


def test_a_reign_can_end_as_history_says_not_only_by_death(syracuse: GameState) -> None:
    """Hieronymus was assassinated at Leontini; the chronicle says so, and gives no eulogy."""
    from anachronism.engine.events import EventLog
    from anachronism.engine.rng import GameRng
    from anachronism.engine.rulers import age_and_succeed

    civ = syracuse.civs["syracuse"]
    civ.rulers = 2  # Hieronymus, first heir after Hiero
    civ.ruler = "Hieronymus"
    syracuse.year = -213
    events = EventLog(syracuse.turn, syracuse.year)
    age_and_succeed(syracuse, civ, GameRng(syracuse.rng), events)
    assert civ.ruler == "General Epicydes"
    assert [e.kind for e in events.items] == ["ruler_fell"]
    assert "assassinated" in events.items[0].message


def test_every_chronicle_starts_and_its_chapters_are_in_its_age(content: Content) -> None:
    """Each state with a chronicle can start one; its chapters fall within its moment."""
    chronicles = sorted({(c.scenario, c.civ) for c in content.chapters.values()})
    assert len(chronicles) >= 1
    for scenario_id, civ in chronicles:
        state = new_game(content, scenario_id, seed=1, player_civ=civ, chronicle=True)
        start = content.scenarios[scenario_id].start_year
        years = [c.year for c in state.world.chapters.values()]
        assert years, (scenario_id, civ)
        assert start <= min(years), (scenario_id, civ)
        assert max(years) <= start + 170, (scenario_id, civ)
        for chapter in state.world.chapters.values():
            for choice in chapter.choices:
                for node in choice.needs_adopted:
                    assert node in state.tech_nodes, (chapter.id, node)


def test_a_coup_does_not_happen_once_history_has_turned(syracuse: GameState) -> None:
    """If the player's last answer turned from history, a scheduled murder or deposition
    does not follow; natural deaths still keep their dates (D-153)."""
    from anachronism.engine.events import EventLog
    from anachronism.engine.rng import GameRng
    from anachronism.engine.rulers import age_and_succeed
    from anachronism.engine.state import ChapterResult

    civ = syracuse.civs["syracuse"]
    civ.rulers, civ.ruler, civ.ruler_age = 2, "Hieronymus", 30
    syracuse.year = -213
    syracuse.chapter_result = ChapterResult(
        chapter="rome_hiero", choice=1, outcome="", history="", historical=False, benchmark=""
    )
    age_and_succeed(syracuse, civ, GameRng(syracuse.rng), EventLog(syracuse.turn, syracuse.year))
    assert civ.ruler == "Hieronymus"

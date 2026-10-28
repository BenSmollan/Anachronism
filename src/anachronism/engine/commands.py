"""Applying player and AI actions to the state (validation first, then changes)."""

from __future__ import annotations

from anachronism.content.schema import Stage
from anachronism.engine.actions import (
    Action,
    AnswerEnvoy,
    ArmyAssault,
    ArmyDeploy,
    ArmyEngage,
    ArmyFormation,
    ArmyPlan,
    ArmyStance,
    Build,
    BuildFleet,
    CancelProject,
    ChooseChapter,
    ChooseDilemma,
    ComeToAid,
    DeclareWar,
    DemandTribute,
    DisbandArmy,
    Explain,
    Fortify,
    HastenProject,
    HireMercenaries,
    HoldFestival,
    LoggedAction,
    MakePeace,
    MarchArmy,
    PauseProject,
    ProposeAlliance,
    ProposeIdea,
    RaiseArmy,
    ResumeProject,
    RuleOnIdea,
    SailFleet,
    ScuttleFleet,
    SealBorders,
    SendEnvoy,
    SendMissionaries,
    SendSpies,
    SetPriority,
    SpreadRumours,
    StartProject,
    Unqueue,
)
from anachronism.engine.armies import apply_orders
from anachronism.engine.buildings import queue as queue_building
from anachronism.engine.buildings import unqueue as unqueue_building
from anachronism.engine.campaign import choose as choose_chapter
from anachronism.engine.decrees import apply_decree
from anachronism.engine.dilemmas import answer
from anachronism.engine.diplomacy import apply_diplomacy
from anachronism.engine.events import EventLog
from anachronism.engine.judge import apply_ruling
from anachronism.engine.offers import respond
from anachronism.engine.projects import hasten
from anachronism.engine.state import GameState, Project
from anachronism.engine.tech import Feasibility, feasibility, propose


def apply_action(state: GameState, action: Action) -> tuple[GameState, LoggedAction]:
    """Apply an action and log it.

    ``state`` itself is unchanged. A rejected action changes nothing except the log, where
    its reason is recorded.
    """
    new = state.model_copy(deep=True)
    ok, message = _apply(new, action)
    logged = LoggedAction(turn=new.turn, action=action, ok=ok, message=message)
    new.action_log.append(logged)
    return new, logged


def describe_blockers(state: GameState, result: Feasibility) -> str:
    """Explain in words what stops a project from starting."""

    def names(ids: tuple[str, ...]) -> str:
        return ", ".join(state.tech_nodes[i].name for i in ids)

    parts = []
    if result.stub:
        parts.append("the idea still needs a proper ruling")
    if result.missing_prerequisites:
        parts.append(f"needs {names(result.missing_prerequisites)} first")
    if result.missing_widespread:
        parts.append(f"needs {names(result.missing_widespread)} to be widespread")
    if result.missing_buildings:
        kinds = state.world.buildings
        built = ", ".join(
            kinds[b].name.lower() if b in kinds else b for b in result.missing_buildings
        )
        parts.append(f"needs {built} built somewhere in the realm")
    if result.beyond_age:
        parts.append("lies beyond this age")
    if result.missing_materials:
        materials = ", ".join(state.world.resources[m].name for m in result.missing_materials)
        parts.append(f"needs access to {materials}")
    return "; ".join(parts)


def _apply(state: GameState, action: Action) -> tuple[bool, str]:
    civ = state.civs.get(action.civ)
    if civ is None:
        return False, f"unknown civilisation {action.civ!r}"
    if isinstance(
        action, HoldFestival | HireMercenaries | Explain | SealBorders | SpreadRumours | SendSpies
    ):
        return apply_decree(state, action)
    if isinstance(
        action,
        RaiseArmy
        | MarchArmy
        | ArmyStance
        | ArmyPlan
        | ArmyFormation
        | ArmyDeploy
        | ArmyAssault
        | ArmyEngage
        | DisbandArmy
        | Fortify
        | BuildFleet
        | SailFleet
        | ScuttleFleet,
    ):
        return apply_orders(state, action)
    if isinstance(action, Build):
        return queue_building(state, action.civ, action.province, action.building)
    if isinstance(action, Unqueue):
        return unqueue_building(state, action.civ, action.province, action.building)
    if isinstance(action, AnswerEnvoy):
        if state.offer is None or civ.id != state.player_civ:
            return False, "no envoys are waiting"
        events = EventLog(turn=state.turn, year=state.year)
        message = respond(state, accept=action.accept, events=events)
        state.events.extend(events.items)
        return True, message
    if isinstance(action, ChooseChapter):
        if civ.id != state.player_civ:
            return False, "only the player plays the chronicle"
        return choose_chapter(state, action.chapter, action.choice)
    if isinstance(action, ChooseDilemma):
        dilemma = state.world.dilemmas.get(action.dilemma)
        if dilemma is None or state.dilemma != action.dilemma or civ.id != state.player_civ:
            return False, "that question is not before you"
        if not 0 <= action.choice < len(dilemma.choices):
            return False, "no such answer"
        state.dilemma = None
        return True, answer(state, dilemma, action.choice)
    if isinstance(action, RuleOnIdea):
        return apply_ruling(state, civ.id, action.ruling)
    if isinstance(
        action,
        DeclareWar
        | MakePeace
        | SendEnvoy
        | ProposeAlliance
        | ComeToAid
        | SendMissionaries
        | DemandTribute,
    ):
        return apply_diplomacy(state, action)
    node = state.tech_nodes.get(action.node_id)
    if node is None:
        return False, f"unknown idea {action.node_id!r}"
    known = civ.tech.get(node.id)
    project = civ.projects.get(node.id)

    if isinstance(action, ProposeIdea):
        if known is not None and known.stage.is_adopted:
            return False, f"{node.name} is already in use"
        result = propose(state, civ.id, node.id)
        if result.blocked:
            return True, f"{node.name}: {describe_blockers(state, result)}."
        return True, f"{node.name} could be attempted now."

    if isinstance(action, StartProject):
        if known is not None and known.stage.is_adopted:
            return False, f"{node.name} is already in use"
        if project is not None:
            return False, f"work on {node.name} is already under way"
        result = feasibility(state, civ.id, node.id)
        if result.blocked:
            return False, f"cannot start {node.name}: {describe_blockers(state, result)}"
        propose(state, civ.id, node.id)
        civ.tech[node.id].stage = Stage.EXPERIMENTING
        civ.tech[node.id].goal = False
        civ.projects[node.id] = Project(
            node_id=node.id,
            started_turn=state.turn,
            priority=action.priority,
            progress_bp=civ.tech[node.id].head_start_bp,  # stolen methods (D-115)
        )
        return True, f"Work begins on {node.name}."

    if project is None:
        return False, f"there is no project for {node.name}"
    if isinstance(action, HastenProject):
        return hasten(state, civ, node.id)
    if isinstance(action, PauseProject):
        if project.paused:
            return False, f"{node.name} is already paused"
        project.paused = True
        return True, f"Work on {node.name} is paused."
    if isinstance(action, ResumeProject):
        if not project.paused:
            return False, f"{node.name} is not paused"
        project.paused = False
        return True, f"Work on {node.name} resumes."
    if isinstance(action, CancelProject):
        del civ.projects[node.id]
        civ.tech[node.id].stage = Stage.CONCEPT
        return True, f"Work on {node.name} is abandoned."
    if isinstance(action, SetPriority):
        project.priority = action.priority
        return True, f"{node.name} now has {action.priority} priority."
    raise AssertionError(f"unhandled action {action!r}")

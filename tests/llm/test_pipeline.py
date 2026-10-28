"""The idea pipeline end to end, with the fake provider (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from anachronism.content.loader import Content, load_content
from anachronism.engine.actions import RuleOnIdea
from anachronism.engine.game import apply_action, end_turn, new_game, replay
from anachronism.engine.rulings import Verdict
from anachronism.engine.save import dumps, loads
from anachronism.engine.state import GameState
from anachronism.engine.summary import build
from anachronism.llm.config import LlmConfig, load_config
from anachronism.llm.fake import FakeProvider
from anachronism.llm.pipeline import IdeaPipeline
from anachronism.llm.provider import ProviderError

ONLINE = LlmConfig(api_key="test", model="fake-model")


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def game(content: Content) -> GameState:
    return new_game(content, "rome_264", seed=4, player_civ="rome")


def steam_engine(**overrides: Any) -> dict[str, Any]:
    idea: dict[str, Any] = {
        "text": "a machine that boils water to push a piston",
        "verdict": "blocked",
        "name": "Heat engine",
        "category": "craft",
        "complexity": 5,
        "year": 1712,
        "prerequisites": ["iron_working", "not_a_real_node"],
        "materials": ["Iron", "unobtainium"],
        "literacy_percent": 20,
        "effects": [
            {"type": "labour_output", "percent": 90},
            {"type": "materials_output", "percent": 30},
            {"type": "knowledge_gain", "percent": 5},
            {"type": "military_strength", "percent": 50},
        ],
        "missing": [{"name": "Precision boring", "category": "metallurgy"}],
        "advisers": [{"role": "scholar", "mood": "excited", "text": "A kettle that works!"}],
        "stirs_unrest": 3,
        "stirs_suspicion": 3,
    }
    idea.update(overrides)
    return {"ideas": [idea]}


def pipeline(*replies: Any) -> tuple[IdeaPipeline, FakeProvider]:
    fake = FakeProvider(*replies)
    return IdeaPipeline(ONLINE, fake, use_files=False), fake


def test_a_new_idea_is_bounded_and_recorded(game: GameState) -> None:
    ideas, fake = pipeline(steam_engine())
    outcome = ideas.consider(game, "rome", "a machine that boils water to push a piston")
    assert outcome.source == "model"
    assert len(outcome.rulings) == 1
    ruling = outcome.rulings[0]
    assert ruling.verdict is Verdict.BLOCKED
    assert ruling.new_node is not None
    assert [s.name for s in ruling.stubs] == ["Precision boring"]
    state, logged = apply_action(game, RuleOnIdea(civ="rome", ruling=ruling))
    assert logged.ok
    node = state.tech_nodes["heat_engine"]
    caps = state.world.effect_caps
    era = "classical"
    assert len(node.effects) <= state.world.rules.rulings.max_effects
    for effect in node.effects:
        assert 0 < effect.bp <= caps[effect.type][era]
    assert "not_a_real_node" not in node.prerequisites
    assert "precision_boring" in node.prerequisites  # the stub it named
    assert node.requires.materials == ("iron",)
    assert state.tech_nodes["precision_boring"].stub
    assert state.civs["rome"].tech["precision_boring"].goal
    limits = state.world.rules.rulings
    assert (
        state.civs["rome"].stats.unrest_bp - game.civs["rome"].stats.unrest_bp
        <= limits.adviser_unrest_bp
    )
    # the player's words reached the model inside the data tags, after the summary
    _, user = fake.calls[0]
    assert "<player_idea>a machine that boils water" in user
    assert user.index("STATE:") < user.index("<player_idea>")


def test_matching_an_existing_node_reuses_it(game: GameState) -> None:
    ideas, _ = pipeline(
        {"ideas": [{"text": "print books", "verdict": "blocked", "matches": "movable_type"}]}
    )
    ruling = ideas.consider(game, "rome", "print books").rulings[0]
    assert ruling.node_id == "movable_type"
    assert ruling.new_node is None
    state, logged = apply_action(game, RuleOnIdea(civ="rome", ruling=ruling))
    assert logged.ok
    assert "movable_type" in state.civs["rome"].tech
    assert len(state.tech_nodes) == len(game.tech_nodes)


def test_a_new_node_named_like_an_existing_one_reuses_it(game: GameState) -> None:
    ideas, _ = pipeline(steam_engine(name="Paper", verdict="feasible"))
    ruling = ideas.consider(game, "rome", "make paper").rulings[0]
    assert ruling.node_id == "paper"
    assert ruling.new_node is None


def test_several_ideas_are_split_and_capped(game: GameState) -> None:
    many = {
        "ideas": [
            {"text": f"idea {i}", "verdict": "feasible", "name": f"Gadget {i}"} for i in range(6)
        ]
    }
    ideas, _ = pipeline(many)
    rulings = ideas.consider(game, "rome", "six things").rulings
    assert len(rulings) == game.world.rules.rulings.max_ideas_per_message
    assert len({r.node_id for r in rulings}) == len(rulings)


def test_a_vague_message_gets_one_question_then_a_ruling(game: GameState) -> None:
    ideas, fake = pipeline(
        {"clarify": "Water for the fields, or water for the mills?"}, steam_engine()
    )
    first = ideas.consider(game, "rome", "make the river work for us")
    assert first.question
    assert not first.rulings
    second = ideas.consider(game, "rome", "make the river work for us", answer="the fields")
    assert second.rulings
    assert "<player_answer>the fields</player_answer>" in fake.calls[1][1]


def test_a_malformed_reply_is_retried_once(game: GameState) -> None:
    ideas, fake = pipeline({"ideas": [{"verdict": "maybe"}]}, steam_engine())
    outcome = ideas.consider(game, "rome", "steam")
    assert outcome.source == "model"
    assert outcome.rulings
    assert len(fake.calls) == 2
    assert "invalid" in fake.calls[1][1]


def test_failures_fall_back_to_offline(game: GameState) -> None:
    ideas, _ = pipeline(ProviderError("boom"))
    outcome = ideas.consider(game, "rome", "irrigation canals for the carthage valley")
    assert outcome.source == "offline"
    assert "could not agree" in outcome.note
    assert outcome.rulings[0].node_id in ("irrigation", "canals")
    ideas, _ = pipeline({"ideas": [{"verdict": "maybe"}]})
    assert ideas.consider(game, "rome", "paper").source == "offline"


def test_rulings_are_cached(game: GameState) -> None:
    ideas, fake = pipeline(steam_engine())
    ideas.consider(game, "rome", "Steam  engine")
    again = ideas.consider(game, "rome", "steam engine")
    assert again.source == "cache"
    assert len(fake.calls) == 1


def test_the_monthly_cap_stops_calls(game: GameState) -> None:
    fake = FakeProvider(steam_engine())
    ideas = IdeaPipeline(
        LlmConfig(api_key="k", model="m", monthly_tokens=100), fake, use_files=False
    )
    ideas.consider(game, "rome", "steam engine")
    assert not ideas.online
    assert ideas.consider(game, "rome", "paper").note == "monthly limit reached"


def test_replays_and_saves_keep_rulings_without_the_model(game: GameState) -> None:
    ideas, fake = pipeline(steam_engine(verdict="feasible", missing=[]))
    ruling = ideas.consider(game, "rome", "steam engine").rulings[0]
    state, _ = apply_action(game, RuleOnIdea(civ="rome", ruling=ruling))
    state, _ = end_turn(state)
    assert loads(dumps(state)) == state
    calls = len(fake.calls)
    again = replay(game, state.action_log, state.turn)
    assert dumps(again) == dumps(state)
    assert len(fake.calls) == calls


def test_summary_stays_small(game: GameState) -> None:
    text = build(game, "rome", "build a printing press so books spread everywhere")
    assert len(text) / 4 < 600  # roughly tokens
    assert "movable_type" in text


def test_files_and_debug_log(game: GameState, tmp_path: Path) -> None:
    config = LlmConfig(api_key="secret-key", model="m", data_dir=tmp_path)
    ideas = IdeaPipeline(config, FakeProvider(steam_engine()))
    ideas.consider(game, "rome", "steam engine")
    folder = tmp_path / "llm"
    assert json.loads((folder / "usage.json").read_text())
    assert (folder / "rulings.json").is_file()
    log = (folder / "calls.jsonl").read_text()
    assert "steam engine" in log
    assert "secret-key" not in log


def test_config_reads_env_file_and_has_no_default_model(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "ANTHROPIC_API_KEY=abc\n# comment\nANACHRONISM_MONTHLY_TOKENS=5\n"
    )
    config = load_config(tmp_path, env={})
    assert config.api_key == "abc"
    assert config.monthly_tokens == 5
    assert config.model == ""
    assert not config.online
    assert config.status == "offline (no model chosen)"
    assert "abc" not in config.status
    online = load_config(tmp_path, env={"ANACHRONISM_MODEL": "some-model"})
    assert online.online
    assert online.fast_model == "some-model"

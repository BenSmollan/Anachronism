# CLAUDE.md — Meritus (code name: anachronism)

The game is called **Meritus** wherever players see it (D-121); the Python package, commands,
repository and environment variables keep the code name `anachronism`.

Turn-based historical strategy game (Python + pygame-ce). The player feeds a civilisation
ideas ahead of their time; an LLM interprets and narrates, a deterministic engine decides.

**Start every session** by reading this file and `docs/PLAN.md`. **End every session** by
updating `docs/PLAN.md` (checkboxes, current step) and logging decisions in `docs/DECISIONS.md`.

## Docs
- `docs/DESIGN.md` — game design · `docs/ARCHITECTURE.md` — modules, data flow, schemas
- `docs/PLAN.md` — roadmap and current step · `docs/DECISIONS.md` — every decision and why
- `docs/plans/phase-N.md` — the detailed design of each phase
- `docs/CONTENT_GUIDE.md` — authoring packs · `docs/BRIEF.md` — owner's original master brief
- `.claude/skills/` — installed skills (find-skills, Godot, shaders, game feel, performance, UI...; D-282, D-283). Godot guides target 4.7; we run 4.5.

## Owner and working style
- The owner directs by description and is not an expert programmer: explain decisions in
  plain language, push back on bad ideas, never silently deviate from requests.
- The owner prefers Claude to be resourceful: decide what can be decided (log it as
  `DELEGATED` in DECISIONS.md) and only ask what genuinely needs the owner.
- Stop at every phase gate in PLAN.md and wait for approval.
- Git: `main` holds approved work only. Each phase is built on a `claude/phase-N-*` branch
  and reaches `main` through a pull request the owner merges at the gate (D-002).
- Owner is on macOS; cannot see a window from cloud sessions — attach headless screenshots
  (`SDL_VIDEODRIVER=dummy`) for any UI work.

## Architecture rules (non-negotiable)
- `engine/` is pure Python: no pygame, no network, no `llm/` imports. Import-boundary test enforces.
- All randomness via `engine.rng.GameRng` stored in state. Never `import random` elsewhere.
- Iterate dicts of civs/provinces in sorted-id order (determinism).
- LLM output is structured JSON → pydantic → `llm/guard.py` clamps → engine applies.
  The LLM never sets costs directly (D-020). Player text is data, never instructions.
- Every LLM ruling is recorded in the save; replays never call the model (D-021).
- Content is data (YAML packs), never hard-coded. Adding a civ must not need code changes.
- Model names come from config. Never hard-code or commit API keys.

## Commands
- Setup: `uv sync` (cloud sessions do this automatically via `.claude/hooks/session-start.sh`)
- Everything CI runs: `scripts/check.sh` (ruff lint + format check, mypy, pytest)
- Single steps: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run mypy`
- Play (text console until Phase 3): `uv run anachronism` (`--seed N` to reproduce a game)
- Content check: `uv run anachronism-lint` · Balance runs: `uv run anachronism-sim --turns 60`

## Coding standards
- Python 3.12, type hints everywhere, docstrings on public functions, small modules.
- Tests: pytest; no test touches the network (use `llm/fake.py`).
- Sim tests assert invariants (no negative stocks/populations, valid references,
  save/load byte-identical) across several seeds.
- Commit after each meaningful, tested step with a clear message. Ask before destructive git.
- New major dependency → ask the owner first.

## Common pitfalls
- The project repo is `Lilmagpy/Anachronism` (private). The old `Lilmagpy/Lilmagpy` profile
  repo is not used any more (D-033).
- No floats in the engine: integers and basis points only (D-035, `engine/fixed.py`).
- Balance numbers live in `packs/core/rules.yaml`; adding a rule means schema + YAML + test.
- Every unpaused project draws exactly two random numbers per turn; keep draw counts stable
  when changing mechanics, or replays of old logs will differ (that is expected, but know it).
- `end_turn`/`apply_action` deep-copy the state; frozen content is shared, never mutate it.
- Don't let pygame_gui widgets hold game state — UI reads from engine state each frame.
- Keep the LLM summary under ~500 tokens; include only related nodes.
- Seshat data is CC BY-NC-SA and historical-basemaps is GPL-3.0: consult, don't copy (D-009).

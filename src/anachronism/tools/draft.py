"""Drafting new library ideas with a language model, for human review (brief §9.2, §10).

    uv run anachronism-draft --region "East Asia" --era classical --count 8
    uv run anachronism-draft --promote drafts/europe_classical.yaml --pack europe

``--region`` drafts candidate advancements into ``drafts/`` (git-ignored until reviewed).
Nothing there reaches the game: the model's memory is never the only source for shipped
content. After the owner has read, corrected and sourced a draft, ``--promote`` checks each
entry against the content schema and appends it to the pack's ``techs/drafted.yaml``; the
content linter then checks the whole pack.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from anachronism.content.loader import load_content
from anachronism.content.schema import Category, EffectType, TechNode
from anachronism.llm.config import load_config
from anachronism.llm.guard import slug
from anachronism.llm.provider import Provider, ProviderError
from anachronism.llm.schemas import ModelEffect

DRAFT_NOTE = "DRAFT: proposed by a language model; check the date and add a real source"

SYSTEM = f"""You help write the library of advancements for Meritus, a historical strategy
game. Propose real advancements (techniques, institutions, tools) that appeared in the given
region and era, that are not in the list of existing ones. For each give: name, category
({", ".join(c.value for c in Category)}), complexity 1-5, the year it first appeared
(negative for BC, as best known), prerequisites (ids from the existing list only), 1-3
effects from this menu: {", ".join(e.value for e in EffectType if not e.is_unlock)} (percent
values, modest), a one-line flavour text in plain English, 4-8 keywords a player might type,
and a short note naming where the date comes from. Say so when a date is uncertain."""


class DraftNode(BaseModel):
    """One proposed advancement, as the model describes it."""

    model_config = ConfigDict(extra="ignore")

    name: Annotated[str, Field(min_length=1, max_length=80)]
    category: Category
    complexity: Annotated[int, Field(ge=1, le=5)]
    year: int
    prerequisites: list[str] = Field(default_factory=list)
    effects: list[ModelEffect] = Field(default_factory=list)
    flavour: Annotated[str, Field(max_length=200)] = ""
    keywords: list[str] = Field(default_factory=list)
    note: Annotated[str, Field(max_length=300)] = ""


class DraftReply(BaseModel):
    """The model's list of proposals."""

    model_config = ConfigDict(extra="ignore")

    nodes: list[DraftNode] = Field(default_factory=list)


def to_yaml_entries(reply: DraftReply, existing: Mapping[str, TechNode]) -> list[dict[str, Any]]:
    """Proposals as content entries, skipping names the library already has."""
    entries: list[dict[str, Any]] = []
    taken = {n.name.lower() for n in existing.values()} | set(existing)
    for node in reply.nodes:
        node_id = slug(node.name)
        if node_id in taken or node.name.lower() in taken:
            continue
        taken.add(node_id)
        effects = [
            {"type": e.type.value, "bp": round(e.percent * 100)}
            for e in node.effects
            if not e.type.is_unlock and round(e.percent * 100) > 0
        ][:3]
        entries.append(
            {
                "id": node_id,
                "name": node.name,
                "category": node.category.value,
                "year": node.year,
                "complexity": node.complexity,
                "prerequisites": [p for p in node.prerequisites if p in existing],
                "effects": effects,
                "flavour": node.flavour,
                "keywords": [k.lower()[:40] for k in node.keywords if len(k) >= 2][:8],
                "provenance": "llm",
                "sources": [DRAFT_NOTE, node.note] if node.note else [DRAFT_NOTE],
            }
        )
    return entries


def draft(
    provider: Provider, region: str, era: str, count: int, existing: Mapping[str, TechNode]
) -> list[dict[str, Any]]:
    """Ask the model for ``count`` proposals and return them as content entries."""
    listing = ", ".join(f"{n.id} ({n.name})" for n in sorted(existing.values(), key=lambda n: n.id))
    user = f"Region: {region}\nEra: {era}\nHow many: {count}\nExisting advancements: {listing}"
    completion = provider.complete(SYSTEM, user, DraftReply.model_json_schema())
    return to_yaml_entries(DraftReply.model_validate(completion.data), existing)


def promote(draft_file: Path, pack_dir: Path) -> list[str]:
    """Move reviewed entries into a pack. Entries still marked as unreviewed are refused."""
    entries = yaml.safe_load(draft_file.read_text(encoding="utf-8")).get("techs", [])
    problems: list[str] = []
    accepted: list[dict[str, Any]] = []
    for entry in entries:
        sources = entry.get("sources", [])
        if not sources or sources == [DRAFT_NOTE] or DRAFT_NOTE in sources:
            problems.append(
                f"{entry.get('id')}: still a draft - replace the DRAFT note with a real source"
            )
            continue
        try:
            TechNode.model_validate(entry)
        except ValidationError as error:
            problems.append(f"{entry.get('id')}: {error.errors()[0]['msg']}")
            continue
        accepted.append({**entry, "provenance": "library"})
    if accepted:
        target = pack_dir / "techs" / "drafted.yaml"
        current = yaml.safe_load(target.read_text(encoding="utf-8")) if target.exists() else None
        data = current or {"schema_version": 1, "techs": []}
        data["techs"].extend(accepted)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    """Command line: draft proposals, or promote reviewed ones."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--region", help="region to draft for, e.g. 'East Asia'")
    parser.add_argument("--era", default="classical")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("drafts"))
    parser.add_argument("--promote", type=Path, help="a reviewed draft file to move into a pack")
    parser.add_argument("--pack", help="pack id to promote into (e.g. core, europe)")
    args = parser.parse_args(argv)
    content = load_content()
    if args.promote:
        if not args.pack:
            parser.error("--promote needs --pack")
        pack_dir = Path(__file__).resolve().parents[1] / "content" / "packs" / args.pack
        problems = promote(args.promote, pack_dir)
        for problem in problems:
            print(problem, file=sys.stderr)
        print("Promoted. Now run: uv run anachronism-lint")
        return 1 if problems else 0
    if not args.region:
        parser.error("give --region to draft, or --promote to move a reviewed draft")
    config = load_config()
    if not config.online:
        print(f"Drafting needs the model: {config.status}. See .env.example.", file=sys.stderr)
        return 2
    from anachronism.llm.anthropic import AnthropicProvider

    try:
        entries = draft(AnthropicProvider(config), args.region, args.era, args.count, content.techs)
    except (ProviderError, ValidationError) as error:
        print(f"Drafting failed: {error}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{slug(args.region)}_{slug(args.era)}.yaml"
    header = "# Drafts for review. Check every date, write a real source, then promote.\n"
    path.write_text(
        header
        + yaml.safe_dump(
            {"schema_version": 1, "techs": entries}, sort_keys=False, allow_unicode=True
        ),
        encoding="utf-8",
    )
    print(f"{len(entries)} drafts written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

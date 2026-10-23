# Decision Log

Every significant decision, why it was made, and who made it.
**Status:** `LOCKED` = from the owner's brief; `OWNER` = the owner answered directly;
`DELEGATED` = the owner asked Claude to decide ("figure it out"); the owner may overturn any
`DELEGATED` decision at any time. Newest entries at the bottom.

---

## D-001 Working title and package name — DELEGATED (2026-09-30)
"Anachronism" is the working title from the brief. An *anachronism* is something out of its
proper time — exactly what the player introduces. The Python package is `anachronism`;
it lives at the root of the `Lilmagpy` repository (no nested project folder). Renaming later
is a one-line search-and-replace, so this is cheap to change.

## D-002 Git workflow — DELEGATED
All work goes on the session branch assigned by the environment (`claude/new-session-8vxe44`
for the first session). The repo has no `main` branch yet. At the Phase 0 gate Claude will
propose creating `main` from the approved state; after that each phase is a pull request into
`main` that the owner approves by merging. Rationale: gives a concrete "approve = merge" step
without the owner needing to know git.

## D-003 Platform, Python and tooling — DELEGATED
- Owner is on **macOS** (OWNER). Target Python **3.12**, installed and managed by **uv**
  (uv downloads the right Python itself, so the owner's system Python doesn't matter).
- One command setup on Mac: install uv, then `uv run anachronism` (see README).
- Tooling: `pyproject.toml`, ruff (lint + format), mypy (strict on `engine/` and `llm/`), pytest.

## D-004 How the owner sees the game without running it — DELEGATED
Verified 2026-09-30: pygame-ce renders headlessly in the cloud container
(`SDL_VIDEODRIVER=dummy`) and can save screenshots. Claude will attach screenshots at each UI
milestone, so the owner can review visuals from the Claude app; running locally is optional.

## D-005 Dependencies — DELEGATED
Runtime: `pydantic` (validation), `pyyaml` (content), `pygame-ce` (window/graphics),
`pygame_gui` (widgets: text entry, scroll panels; built on pygame-ce), `anthropic` (LLM, Phase 2).
Dev: `pytest`, `ruff`, `mypy`. All test-installed successfully 2026-09-30
(pygame-ce 2.5.8, pygame_gui 0.6.14, pydantic 2.13, anthropic 1.9).
Why pygame-ce over pygame: same API, actively maintained, better Unicode/IME text input
(needed for Chinese/Korean/Japanese names). Brief decision #1 ("Pygame") is honoured.

## D-006 Content formats — DELEGATED
Hand-authored content: **YAML** (comments allowed, readable). Saves, caches, generated data:
**JSON**. Every file carries `schema_version`. Validation by Pydantic models.

## D-007 Resource model — DELEGATED (see DESIGN §4)
Stockpiles: food, materials, wealth, knowledge. Flow: labour (per turn, cannot be stored).
Civ-wide stats: population, literacy, unrest, suspicion, legitimacy, military strength,
trade income. Added **wealth** (treasury) because trade income needs somewhere to go and
armies/bureaucracies are paid in it; merged "stability/legitimacy" into one stat
(**legitimacy**) with **unrest** as its counterweight, to avoid two near-identical numbers.

## D-008 Map representation — DELEGATED
**Province graph**: irregular provinces with adjacency lists; terrain, resources and
ownership stored per province. ~20 provinces for the Phase 1 test world, ~100–140 for East Asia.
Rejected hex (poor fit for historical borders) and tile grid (most work, least historical).

## D-009 Map and data sources / licences — DELEGATED
Checked 2026-09-30: Seshat public data is **CC BY-NC-SA (non-commercial only)**;
aourednik/historical-basemaps is **GPL-3.0**; CShapes covers only 1886 onward.
Decision: keep the game free to be released under any licence later, so **no GPL or NC data
is copied into shipped files**. These sources may be *consulted* as references (facts are not
copyrightable; datasets and drawings are). Province shapes are drawn by us. Wikidata (CC0) may
be imported directly. Every shipped fact records its reference in `sources`.

## D-010 Turn length — DELEGATED
Years per turn set per scenario by an era table, default: ancient 20, classical 15,
medieval 10, early modern 5. The engine allows the length to shrink mid-game when the
player's civ crosses a technology threshold (tunable; off by default until balanced).

## D-011 Dynasties and player continuity — DELEGATED (resolves brief #13 / open question #7)
Each dynasty/polity is a **separate data entry** (Tang, Song, Ming…) with `lineage` links
(predecessor/successor, cultural family). The player's guiding hand attaches to a **lineage**,
not a single polity. If the player's polity falls, the player chooses which successor polity
to continue with (default: the direct lineage successor). The game ends only if the lineage
has no surviving successor. Rationale: historical accuracy in data plus a continuous game.

## D-012 Imperfect knowledge (insight) — DELEGATED
No separate insight-points pool. Instead every advancement passes through **adoption stages**:
`concept → experimenting → adopted → widespread`. Experimentation costs resources, takes time
and can fail or partially succeed. This implements "the player remembers concepts, not details".

## D-013 Visibility of rival scripts — DELEGATED
**Intelligence reports that can be wrong.** Quality depends on relations, trade contact,
spies and distance. Ties directly into the information system.

## D-014 Combat — DELEGATED
Abstract strength comparison (troops × tech × terrain × supply × morale, plus seeded
randomness). No tactical battles unless the owner asks later.

## D-015 Victory measurement — DELEGATED (proposal, tuned in Phase 7)
Tiers: region → hemisphere → world. Per tier, any one path wins:
- Military: control or tributary overlordship of ≥ 60% of the tier's population.
- Economic: ≥ 50% of the tier's trade value flows through routes you own or tax.
- Cultural: ≥ 50% of the tier's population follows your religion, script or legal code
  (tracked per province as culture-layer shares).

## D-016 LLM models and cost — DELEGATED
Model names come from config, never code. Defaults (checked against current Anthropic docs
2026-09-30): `claude-opus-5-5` ($4 / $20 per million tokens in/out) for all tasks, with
effort `low` for interpretation/clarification and `medium` for rulings. Structured output
via the SDK's `messages.parse()` with Pydantic schemas; prompt caching on the stable prefix.
A cheaper model can be set per task in config (e.g. `claude-haiku-4-5` for interpretation) —
switching is the owner's choice. Estimated cost ~$0.02–0.05 per idea; a **monthly spend cap**
setting (default $10) automatically drops to offline mode when reached.

## D-017 Art direction and resolution — DELEGATED
Placeholder: "ink and parchment" palette (warm paper background, ink-dark lines, muted
province fills, one accent colour). Minimum window 1280×800, resizable, layouts use
proportional anchors. Retina (HiDPI) handled by scaling.

## D-018 Names and scripts — DELEGATED
English names primary; native-script names stored in data and shown as a subtitle
(e.g. "Goguryeo 高句麗"). Font: Noto Sans/Serif CJK subset bundled in Phase 5.

## D-019 Sharing tech trees — DELEGATED
Saves are self-contained JSON, so sharing a save shares a run. A dedicated "export tech tree"
feature is deferred to Phase 8+.

## D-020 Tech backbone and engine-computed costs — DELEGATED
A curated **core tech graph** (a few hundred generic advancements with structured
requirements) ships in `packs/core`. The LLM's first job is to **map** the player's idea onto
an existing node; it creates a new node only when nothing matches. The LLM never outputs
numbers directly for costs: it outputs a *complexity tier* and requirement tags, and the
engine computes cost/duration/effect magnitudes by formula. Rationale: consistency between
rulings, strong caching, and immunity to "make it free" manipulation.

## D-021 Replay safety — DELEGATED
Every LLM ruling is stored in the action log. Replaying a save re-applies recorded rulings
and never calls the model again. Seed + action log ⇒ identical game.

## D-022 Suspicion target — DELEGATED
Suspicion attaches to the **ruling house** (the guiding hand is invisible). It can shift
between "inspired", "witchcraft" and "fraud" framings based on events and religion.

## D-023 Phase 1 playability and balance bots — DELEGATED
Phase 1 includes an interactive **text console mode** (not just a printout) and scripted
**bot players** (growth, military rush, build-everything) used by headless balance tests.

## D-024 Rivals learn inventions — DELEGATED
When news of an advancement reaches a rival, that rival may begin its own `experimenting`
stage. Secrecy therefore protects a real advantage.

## D-025 Scenario authoring — DELEGATED
Layered timeline data (polity exists X–Y, border changes in year Z, relation changes in year W)
from which snapshots are assembled, plus per-scenario override files. East Asia will be built
one scenario at a time, starting with one flagship moment (chosen in Phase 5).

## D-026 Build, lock and Python pin — DELEGATED (Phase 0)
`uv_build` backend, `.python-version` = 3.12, `uv.lock` committed. The lock is written by the
cloud image's uv (0.8.17); verified 2026-09-30 that the newest uv (0.12.21, what the Mac and
CI install) accepts it with `--locked` and does not rewrite it, so the owner's checkout never
shows a modified lockfile.

## D-027 Dependencies arrive when first used — DELEGATED (refines D-005)
Now: `pydantic`, `pyyaml`; dev: `pytest`, `ruff`, `mypy`, `types-pyyaml`.
`anthropic` is added in Phase 2 and `pygame-ce` + `pygame_gui` in Phase 3.

## D-028 Guard rails are tests — DELEGATED
- `tests/test_architecture.py` reads the source and fails on forbidden imports per layer
  (engine: no network, pygame, clocks, threads, randomness, llm/ui/tools; content: no engine,
  llm, ui; llm: no pygame/ui).
- ruff bans `import random` project-wide (TID251).
- An autouse fixture blocks outbound network connections in every test.
- Hygiene tests: CLAUDE.md ≤ 100 lines, persistent docs exist, no API keys in tracked files,
  `.env` is git-ignored.
Each rule was verified by deliberately breaking it and watching the check fail.

## D-029 Continuous integration — DELEGATED
GitHub Actions runs `scripts/check.sh` plus the launcher on **Ubuntu and macOS** for every push
and pull request. The repo is public, so minutes are free. If it ever becomes private, macOS
minutes count 10×: then run macOS only on pull requests.

## D-030 GameRng is our own generator — DELEGATED (implemented in Phase 1)
Python only guarantees that `random.random()` keeps its sequence across versions; other
methods (`randrange`, `choice`, `shuffle`…) may change. Saves must replay identically on any
Python version, so `engine/rng.py` will implement a small documented PRNG (e.g. PCG32) whose
whole state is a few integers stored in `GameState`.

## D-031 Where the project lives — RESOLVED by D-033
`Lilmagpy/Lilmagpy` is the owner's GitHub **profile repository** (public): a `README.md` at its
root is displayed on the owner's public GitHub profile page. Until the owner decides, no root
README is added and setup instructions live in `docs/GETTING_STARTED.md`. Options: move to a
dedicated repo (recommended) or keep it here (the README would then appear on the profile).

## D-032 Licence — DEFERRED (owner decision, only needed before publishing a release)
No licence file yet, which legally means "all rights reserved": others may view the public repo
but not reuse it. Choose one before any public release.

## D-033 The project lives in Lilmagpy/Anachronism — OWNER (2026-09-30)
The owner chose a dedicated repository and created **`Lilmagpy/Anachronism`** (private) themselves:
the Claude GitHub App is not allowed to create repositories. History moved over intact; `main`
holds approved work. "Anachronism" stays a **placeholder name** (owner: "can we do a placeholder
for now"); renaming later is easy. The old profile repo `Lilmagpy/Lilmagpy` still holds a copy on
branch `claude/new-session-8vxe44` (its default branch). It has no README, so nothing shows on the
owner's profile; the owner can delete that repo or leave it.

## D-034 CI on a private repo — DELEGATED (amends D-029)
Mac minutes count 10x on private repos. Linux checks run on every push and pull request; the macOS
job runs only for pull requests, pushes to `main` and manual runs. Phase work is developed on a
`claude/phase-N-*` branch and reaches `main` through the phase's pull request (D-002).

## D-035 Integer maths everywhere — DELEGATED (Phase 1)
All engine state and maths use Python integers; rates and 0-100 stats are basis points
(10_000 bp = 100%). Floating-point maths can differ in the last digit between macOS and Linux
libraries, which would make saves replay differently across machines. `engine/fixed.py` holds
the rounding rules.

## D-036 Content file format — DELEGATED
Each YAML file holds `schema_version` plus exactly one kind (`techs`, `provinces`, `rules`…),
so authors can split files freely. List items are validated one at a time, so a broken item is
reported without hiding its valid siblings, and references to it are not reported twice.
Duplicate YAML keys are errors (PyYAML would silently keep the last). Numbers are in basis
points with `_bp` in the field name wherever that is not obvious.

## D-037 What lives where in content — DELEGATED
Province files hold fixed geography only; civ files hold lasting identity only; a scenario
holds the moment: ownership, populations, stockpiles, stats, social-group influence and known
techs. This keeps the Phase 5 layered timeline (D-025) possible without reshaping data.

## D-038 Effect caps follow the current era — DELEGATED
An advancement's effect is capped by the era the game is in, not the era it belongs to. An idea
adopted centuries early is held back until society catches up with it.

## D-039 Adoption spread is civilisation-wide in Phase 1 — DELEGATED
Spread is one percentage per civilisation and advancement, not tracked province by province.
Per-province adoption can come later if the map needs it.

## D-040 Core tech years are placeholders — DELEGATED
The `year` of each core tech node (first historical appearance) is an approximate value from
general knowledge, good enough for the fictional test world. Before real-history packs rely on
them (Phase 5), each gets a source note and a confidence level.

## D-041 Literacy fades without teaching — DELEGATED (Phase 1)
A share of literacy (5% per decade) is lost each turn, so literacy effects set a sustainable
level: writing alone sustains about 6%, printing and schools push toward 20-30%. Without this,
writing alone reached 20% literacy and a careful player 70% by 600 BC, far above history.

## D-042 Knowledge from everyone, not only the literate — DELEGATED
A small base amount of knowledge comes from the whole population (crafts, lore, observation);
literate people add much more. Otherwise a society without writing could never invent anything,
yet steppe peoples invented riding and the composite bow.

## D-043 Strain follows current conditions — DELEGATED
Strain moves toward a target set by this turn's project shortfall, labour diversion and unpaid
administration, instead of accumulating without limit. It measures how stressed society is now;
unrest carries the memory.

## D-044 Bots take actions only, with no randomness — DELEGATED
Automated players choose actions from the state and nothing else, so bot-played games replay
exactly from their action log. They run rival civilisations until Phase 4's scripts arrive.

## D-045 `uv run anachronism` starts the text console until Phase 3 — DELEGATED
One command to remember. When the window arrives, `anachronism` opens it and the text version
stays available as `anachronism-console`.

## D-046 First-pass balance, to tune with the owner — OPEN (Phase 7 per the brief)
Current numbers make overextension collapse reliably and careful growth thrive. Known issues:
a careful player is comfortable (the 55-node test tree is nearly exhausted by 600 BC) and
suspicion bites only when the "witchcraft" or "fraud" framing comes up. The brief asks for the
owner's help tuning suspicion; pacing is tuned when real content and conflict exist.

## D-047 Godot 4 replaces Pygame for the game's visuals — OWNER (2026-09-30)
The owner wants "incredible graphics" and chose a modern 3D world over a 2D map. This overrides
brief decision #1 (Pygame). Godot 4 is free, open source (MIT), has a full 3D renderer and
exports to macOS. Verified 2026-09-30 that Godot 4.5.1 renders 3D in the cloud container
(Xvfb + Mesa software rendering, Compatibility renderer), so screenshots can be sent to the
owner. The Python engine is unchanged; the text console remains a developer tool.

## D-048 Client-engine bridge — DELEGATED
The Godot client starts the Python engine as a child process and they exchange one JSON
message per line over its stdin/stdout. No network sockets (nothing to firewall, nothing
exposed). The engine stays the only authority on rules; the client only renders and sends
actions. The bridge lives in `tools/server.py`, outside the pure engine.

## D-049 Phase order: 3D world before the LLM — OWNER
Phase 2 is now the 3D world; the LLM ruling pipeline becomes Phase 3 and plugs into the 3D UI.

## D-050 Getting builds to the owner — DELEGATED
CI exports a macOS app for every pull request so the owner downloads and double-clicks; no
Terminal. Unsigned at first (right-click → Open the first time). Bundling Python inside the
app is solved in this phase; Apple signing waits for packaging (Phase 8).

## D-051 3D art sources — DELEGATED
Terrain, water and borders are generated from content data. Models come from openly licensed
packs (CC0 only, licences recorded in `client/assets/LICENSES.md`) until custom art is made.

## D-052 Visual style: a Rise of Kingdoms-like "living map" — OWNER (2026-09-30)
Fixed-angle tilted map (no free 3D orbit). Zoomed out: the strategic map with territories,
borders, names and banners. Zooming in reveals detail that fades in by distance: towns sized by
population, capitals with walls, farms, forests, and later units. Stylised, colourful low-poly
art rather than photorealism. Built on the Godot 3D client (D-047) using distance-based
level of detail.

## D-053 The map is the real Earth — OWNER (2026-09-30)
The owner's goal is maximum realism, so the fictional map is replaced by real geography
(the test world stays only for automated tests). This overrides the "stylised, not
photorealistic" part of D-052; the living-map camera and zoom-in detail stay.
- **Elevation:** Terrarium tiles (Mapzen / AWS Open Data; built from SRTM, GMTED2010, ETOPO1
  and others; attribution required), stitched by `client/tools/build_heightmap.gd`.
- **Colour:** NASA Blue Marble satellite mosaic (public domain, about 10 km per pixel),
  reprojected by `client/tools/build_colour.gd`. Chosen over colours guessed from climate,
  which looked wrong. Its snow cover is from one season. Higher-resolution imagery (Sentinel-2
  cloudless, NASA servers) is blocked from cloud sessions; revisit on the owner's Mac.
- **Rivers:** Natural Earth 10 m rivers (public domain), `scripts/build_rivers.py`.
- **Projection:** Web Mercator, one world unit ≈ 5 km at the equator; heights exaggerated
  about 14× so mountains read from a strategy camera. Regions are built one at a time,
  East Asia first (67.5–151.9°E, 5.6–55.8°N).
- Sources and licences are listed in `client/data/SOURCES.md`.

## D-054 First real scenario: the Warring States, 350 BC, playing Qin — DELEGATED (2026-09-30)
The owner asked Claude to pick. Chosen because it is the best-documented early East Asian
moment with many rival states (7 great states, 6 smaller ones, 5 frontier peoples), it sits
where the "ideas ahead of their time" play is richest (paper, cast iron, crossbows, canals,
civil service all within reach), and 350 BC is a clean anchor: Qin moves its capital to
Xianyang under Shang Yang's reforms. The player is Qin, the best-known state; other starts
can be added later as extra scenarios. Populations, borders and techs are Claude's estimates
from general historical knowledge; uncertainties are listed in `docs/history/warring_states.md`.

## D-055 Real-map content: latlon, map and cost scale — DELEGATED (2026-09-30)
Provinces and seas on the real Earth use `latlon` (degrees; content only, not used by the
simulation, so floats are safe for determinism). Scenarios name their `map`. Real
populations are about ten times the test world's, which made every invention trivially
cheap, so scenarios carry a `cost_scale` that multiplies project costs; shown populations stay
real. Old saves load unchanged (new fields default to "no map" and scale 1).

## D-056 Provinces are drawn by terrain-aware growth from their centres — DELEGATED (2026-09-30)
Hand-drawing historical borders would be slow, and the historical-basemaps polygons are GPL
(D-009). Instead each province grows from its centre over the real elevation, with steep
and high ground costly to cross, so frontiers settle on ridges and rivers stay inside
provinces. The client and the checking tool (`client/tools/province_report.gd`) use the same
code, so the rules' neighbours always match what the player sees. Borders are about 20 km
accurate. Hand-made border polygons can replace this later if the owner wants exact lines.

## D-057 How the Mac app carries the Python engine — DELEGATED (2026-09-30)
The exported Godot app contains the engine's Python source, its lock file and the `uv` tool
(both Mac chip types). On first launch it unpacks them into the game's user-data folder and
uv downloads its own Python 3.12 and the exact locked libraries (about a minute, once);
the Mac's own Python is never used. Nothing is installed system-wide and the owner needs no
Terminal. The app is ad-hoc signed only (no paid Apple developer account), so macOS asks
for "Open Anyway" once. CI proves the packaging on every push by exporting the same
package for Linux and starting it with an empty home folder. Elevation data moved from EXR
(readable only by the Godot editor) to a raw 16-bit file that exported games can read.
Later options: bundle Python itself for offline first launch; sign and notarise (Phase 8).

## D-058 Settlements are drawn larger than life — DELEGATED (2026-09-30)
At true scale a city on the continental map is a few pixels wide even fully zoomed in, so,
as in Rise of Kingdoms, settlements are drawn about 2.5 times larger than life and appear
when the camera comes within about 1,000 km. Each province has its chief city at its
centre (capitals walled in rammed earth, with gate towers and a palace hall on a terrace,
laid out on the cardinal directions as cities of the period were), plus towns and villages
by population, placed on the flattest, lowest land. Simple built shapes for now; the CC0
models of D-051 or custom art can replace them. Map lines (borders, rivers) now keep a
constant thickness on screen at every zoom.

## D-059 Art direction: bright cartoon, full of character — OWNER (2026-09-30)
After playing the first Mac build the owner said the quality fell well short: the game must
look good in the manner of Rise of Kingdoms (screenshots shared), may be cartoony, and needs
characterisation (figures from each empire popping up and speaking) and an intro where the
player picks a civilisation and a starting moment. The map keeps real geography (D-053) but
is painted in a bright cartoon style instead of satellite colours (owner's choice). Sources:
CC0 art packs for 3D models (D-051), code for the map, water, UI and effects. Scripted
character lines come now; free AI conversation belongs to Phase 3. Phase 2 continues
(steps 2.9–2.16) and its PR stays open until the owner is happy.

## D-060 Character portraits: placeholders made in code for now — OWNER (2026-09-30)
Offered AI-generated, artist-made or in-game-generated portraits; the owner chose
placeholders for now. They are drawn in code (heraldic emblems and silhouettes in each
civilisation's colours) and loaded from one folder per character, so real art can replace
them without code changes.

## D-061 First starting moments: all four regions — OWNER (2026-09-30)
The picker will offer East Asia (already built; add Korea and Japan starts), the
Mediterranean (Rome, Greece), Egypt / Near East and Medieval Europe (Britain, France,
Vikings). Each needs its own map region and researched scenario; they arrive one at a time.

## D-062 Night shift: work through the brief without stopping — OWNER (2026-09-30)
The owner is asleep and asked Claude to keep going without asking questions: improve
graphics and UI scaling, colour cities and territories by owner, vary the characters, and
implement the rest of the brief, then keep improving graphics. For this stretch the phase
gates are waived (work continues on the open Phase 2 PR, Lilmagpy/Anachronism#2); every
decision Claude makes alone is logged here as DELEGATED for review in the morning.

## D-063 How a ruling on the player's idea is bounded — DELEGATED (2026-10-01)
The model (or the offline interpreter) returns loose numbers: percentages, 0-3 levels.
`llm/guard.py` converts them into an engine `Ruling`, and `engine/judge.py` bounds the
ruling again when it is applied, so even a ruling that skipped the guard is safe: effects
are cut to the era's caps (at most 3 per idea, no unlocks from rulings), a new idea is at
least as complex as its hardest prerequisite minus one and cannot be "invented" before
its prerequisites (so the anachronism cost and suspicion cannot be dodged), unknown
references are dropped, and the advisers' reactions add at most 2 unrest and 3 suspicion.
Costs are never taken from the model (D-020). At most 3 ideas per message are ruled on
(no bundling). The limits live in `rules.yaml` under `rulings`. Each ruling is stored in
the save inside a `RuleOnIdea` action, so replays apply it again without any model (D-021).

## D-064 Offline "Historical Advisors" mode matches words to the library — DELEGATED (2026-10-01)
Every advancement now has `keywords` (words players might use: "printing press",
"zero", "river"). Offline, a message is split into parts, each part is matched to the
best advancement, and the ruling comes from the engine's own feasibility check; anything
unmatched is "beyond this age" with a hint toward ideas within reach. The court's reaction
comes from scripted dialogue (`idea_feasible`, `idea_blocked`, `idea_implausible`). The
same interpreter is the fallback whenever a model call fails.

## D-065 No model name in the code — DELEGATED (2026-10-01)
Model names change often and must come from configuration (CLAUDE.md), so there is no
default model: online play needs both `ANTHROPIC_API_KEY` and `ANACHRONISM_MODEL` in the
environment or a git-ignored `.env` file (see `.env.example`), with an optional cheaper
`ANACHRONISM_FAST_MODEL`. Without them the game plays offline and says so. The provider
uses only Python's standard library (no new dependency), forces structured output through
a single tool, marks the fixed system prompt for prompt caching, and retries rate limits.
A monthly token cap (default 2 million) stops calls once reached.

## D-066 Rival scripts live in the scenario files — DELEGATED (2026-10-01)
Each civilisation in a scenario lists its intentions (`scripts`) and temperament
(`disposition`); the scenario lists starting `relations` (alliances, wars, grudges).
Scripts are conditional: they fire when their preconditions hold (year window, stability,
strength against the target, turmoil in the target, advancements known, other scripts
fired) and lapse when their moment passes or their target is gone, taking dependent scripts
with them. The player's own civilisation never follows a script. The scripts for all four
moments were drafted from well-known history (the notes cite what really happened); they
are drafts for the owner's review, in the spirit of the brief's review workflow (§9.2).

## D-067 War is abstract — DELEGATED (2026-10-01)
No individual armies to move yet. Strength = workforce x military effects x legitimacy;
allies at war with the same enemy lend half their strength. Each turn the stronger side
may take one frontier province (chance grows with its advantage, capped at 50%); both sides
lose people on the front, gain unrest and weariness; the side that tires first makes peace
and keeps a grievance. A lost capital moves the court and costs legitimacy; losing every
province destroys a state. The map shows crossed swords on war fronts. Moving armies and
battles can come later (Phase 7) without changing saves' meaning.

## D-068 Victory paths and how they are measured — DELEGATED (2026-10-01)
The brief asked the owner how to measure each path; tonight's measures, all tunable in
`rules.yaml`: military = rule 50% of the scenario's people; economic = trade partners,
allies and tributaries hold 60% of everyone else's people, and you hold the richest
treasury; cultural = 40% of the region's culture (people weighted by literacy and cultural
influence), and the largest. Each target is at least the starting share plus 20 points,
so a dominant start (Egypt in 1275 BC) must still gain ground. Every victory is regional
until games span several regions. The game can continue after the banner.

## D-069 Korea's moment: the Three Kingdoms in AD 400 — DELEGATED (2026-10-01)
For the East Asian starts the owner asked for (D-061), the first Korean moment is AD 400:
Gwanggaeto's Goguryeo, Baekje, Silla, Gaya and the Wa of Japan, with the northern
dynasties (Wei, Yan, Qin), Eastern Jin and the Rouran. Korea and Japan get finer
provinces than in 350 BC. It suits the game: a young conqueror-king, a weak Silla that
history says will win, and Japan across the strait. Notes and uncertainties are in
docs/history/three_kingdoms.md. A Japan-centred moment is left for later.
Also tonight: an ally or tributary under attack pulls in its AI protectors, but the player
is never dragged into a war automatically; their general asks instead.

## D-070 Drafted content needs a real source before it ships — DELEGATED (2026-10-01)
`uv run anachronism-draft --region "East Asia" --era classical` asks the model for new
library ideas and writes them to `drafts/` (git-ignored), each marked as a draft. The
`--promote` step refuses any entry still carrying the draft note, so an idea reaches a
pack only after someone has checked its date and written a real source (brief §9.2:
the model's memory is never the only source for shipped facts).

## D-071 Chance events are content — DELEGATED (2026-10-01)
Plague, floods, droughts, locusts, earthquakes, fires, bandits, storms, bumper harvests,
silver strikes, wandering sages and good omens live in `core/happenings.yaml`: a chance per
decade, where each can strike (terrain, river, coast), what it does, and what softens it
(health against plague, storage against flood and drought). At most one per state per turn,
rolled on the game's RNG so replays match. `rules.society.happening_frequency_bp` scales
them all (0 turns them off, as the exact-number tests do). The steward and diviner react.
Also tonight: capitals are twice as hard to take and rough terrain is harder (D-067 tuning);
armies appear on war fronts; sound and music are synthesised by scripts/make_sounds.py.

## D-072 Rulers age, die and are succeeded — DELEGATED (2026-10-01)
Every state's ruler ages each turn; the chance of dying each decade is 0.7% per year of
age above 30 (so about 21% at 60, capped at 90% a turn). The next ruler is the scenario's
next historical successor (with their own temperament where history is clear: King Wuling
of Zhao, Cnut, Emperor Taiwu), then unnamed heirs. A death costs 8 points of legitimacy;
below 40 legitimacy it brings a succession crisis (+15 unrest). The player's own ruler
dies too; the state goes on. Successor lists are drafts from general history.

## D-073 Trade and faith as first-class flows — DELEGATED (2026-10-01)
Brief §7.5 asks for trade, religion and cultural flows as first-class things. Every
friendly tie (trading, allied, tributary) now earns both sides wealth each turn, by the
smaller side's people. Each scenario lists its faiths and who holds them (the Zhou rites,
the thousand gods of Hatti, the Olympians, Latin and Orthodox Christianity, Sunni and Shia
Islam, Buddhism, the kami...); faiths marked as spreading cross to neighbours by chance,
more easily along friendly ties and from states of great cultural influence. States of one
faith forget old grudges faster; courts sharing your faith add half their culture to your
cultural victory share. You can send missionaries (a wealth cost, a 35% chance, a small
grudge if refused). Faith lists are drafts from general history.

## D-074 Japan's moment: the Warring States in 1560 — DELEGATED (2026-10-01)
The Japan-centred start the owner asked for (D-061) is May 1560, on the eve of Okehazama:
play Oda Nobunaga with 3,000 men as Imagawa marches on Kyoto, among the Takeda, Uesugi,
Hojo, Mori, Shimazu and the rest, with Joseon Korea, Ryukyu and the Ming coast across the
sea. The Ming appear only as the provinces within reach, and far smaller than the real
empire, so a regional victory stays possible (noted in docs/history/sengoku.md). New
portrait styles: armoured samurai and a Joseon official's gat.

## D-075 A bigger library of ideas — DELEGATED (2026-10-01)
The library grows from 55 to 90 advancements, mostly medieval to early modern (lenses,
eyeglasses, telescope, microscope, germ theory, vaccination, the printing press,
newspapers, universities, the scientific method, banking, double-entry bookkeeping,
joint-stock companies, ocean-going ships, cannon, muskets, star forts, new crops, spinning
machines, coke smelting, the steam engine, railways...), so later moments have curated
ideas and the offline court recognises more of what players type. Dates are approximate
first appearances (placeholders pending the source review, as D-040). Several now appear
as landmarks around the capital.


## D-076 Royal decrees, and cultural victory must be earned — DELEGATED (2026-10-01)
Playtests showed wealth piling up with nothing to spend it on, and some starts winning a
cultural victory without the player doing anything (a big faith the player never held
counted towards their share). Two royal decrees now spend wealth, priced by the size of
your people: a festival (raises legitimacy, calms unrest) and hiring mercenaries (30% more
strength for two turns). A faith now counts towards your cultural share only if you held it
at the start, and cultural victory also needs at least 10% cultural influence of your own.
Rival courts use the same decrees: at war they hire swords, in unrest they hold feasts,
always keeping half their treasury in reserve.

## D-077 Cities in their region's style — DELEGATED (2026-10-01)
Every city was drawn in the East Asian style. Buildings now follow the region of the
province's first owner (from its portrait family): tiled roofs and rammed earth in East
Asia; flat-roofed mud brick, a columned temple and a pyramid on the Nile; mud brick and a
stepped temple tower in the Near East; white walls, terracotta and a columned temple around
the Mediterranean; steep roofs, a stone keep, round towers and a church spire in the north;
felt tents and a great yurt on the steppe. Trees no longer grow inside city walls.
Fixed on the way: on large maps (Europe 1000) cities vanished, because each kind of
building was one batch for the whole map and Godot hides a batch by its centre's distance
from the camera; buildings are now batched by map tile like the trees.

## D-078 Economic victory measured by network and income — DELEGATED (2026-10-01)
Playtests showed economic victory either came on turn 3 (Egypt at Kadesh: one envoy a turn
to each neighbour, instant alliances) or never (the "richest treasury" test failed against
any bigger empire, and spending on decrees counted against you). Now:
- your trade network must reach 60% of other peoples, with trading partners counting half
  and allies and tributaries in full, and include at least half the other living states;
- your income per turn (own lands plus trade ties) must be at least half the largest
  rival's: what you spend no longer counts against you;
- one embassy a turn, and a court allies only after two turns of trade (or against a
  common enemy).
Egypt at Kadesh, the region's superpower, can still win by trade in about 60 years of
patient diplomacy; elsewhere it takes most of a game. The World tab ticks off each
path's extra conditions.

## D-079 A fair chance for small starts — DELEGATED (2026-10-01)
Playing Oda in 1560 (one province against Imagawa and Saito) ended in collapse within six
turns in half of all games, often on turn 2, before a player could do anything. Now a
state's last province is defended to the end (three times harder to take); the player
loses no provinces in the first two turns, to answer an opening war; and Oda starts
with the wealth of Owari's port trade (enough to hire mercenaries at once). Sengoku stays
the hard start: about one game in six still ends early.

## D-080 What every state of an age knows — DELEGATED (2026-10-01)
The 35 newer advancements (D-075) were never added to the starting moments, so Rome was
offered "written law" despite its Twelve Tables, and Byzantium "hospitals" and "glass".
Scenarios now list `common_techs`, ideas every state of the age knows, given to each
state that already has their prerequisites (so peoples without writing get no law code).
Written law everywhere it fits; soap at Kadesh and in AD 1000; household registers in
East Asia; glass, hospitals and registers in AD 1000. Drafts from general history,
for the source review with the rest (D-040). CONTENT_GUIDE documents the field.

## D-081 Collapse comes from within; world faiths hold — DELEGATED (2026-10-01)
Two rules misfired in AD 1000 playtests. (1) "Collapse" counted any lost province, so a
two-province state that lost one battle "collapsed" - and for the player that meant game
over. As DESIGN §5 intends, collapse is now breaking apart from within: half the starting
provinces lost to revolt. Conquest is the war system's business (a state with nothing
left is destroyed). (2) Faiths converted courts of other world faiths as easily as pagan
ones: the Fatimid caliphate and the Zirids turned Latin Christian within decades. A court
holding another spreading faith now converts at a tenth of the chance, and missionaries
sent to one succeed at 30% of theirs.

## D-082 Democracy and the republic; a more careful offline court — DELEGATED (2026-10-01)
Players will type "democracy", and the offline court called it implausible - for Rome,
with Athens next door. The library gains Elected magistrates (the republic, Rome 509 BC)
and Citizens' assembly (democracy, Athens 508 BC); Rome and Carthage start with the
first, Athens and Rhodes with both. The offline court now takes a one-word idea that is
exactly a keyword as a match, ignores generic words alone ("flying machines" is not
"spinning machines"), suggests the nearest ideas ahead of their time, and says when it is
offline that it only knows its library. The content linter now checks each civ's
starting ideas together with the age's common ones.

## D-083 Confidence tiers and a source-review checklist — DELEGATED (2026-10-01)
Brief §2.14 asks for internal source notes and confidence levels. Advancements,
civilisations and scenarios now carry `sources` and `confidence` (high / medium / low,
low by default). `anachronism-lint --review` prints the checklist. Today everything is
honestly "low, no source": it was drafted from general history, so the Phase 5 source
review (D-040) starts from a complete list instead of a guess.

## D-084 A seventh moment: the Great Khan, 1206 — DELEGATED (2026-10-01)
On the East Asia map: play Genghis Khan at the kurultai of 1206, among the Tangut Xia, the
Jurchen Jin, the Southern Song, Goryeo, Kamakura Japan, the Qara Khitai, the Uyghurs of
Qocho, the Ongut and Dali (10 states, 54 provinces; history notes in
docs/history/great_khan.md). To make the steppe's real strength possible, scenarios can now
set a state's mobilisation (`martial_bp`: the Mongols put fifteen times the usual share of
their people under arms; the Jin and Song less). Tested: a passive Mongol player takes
nothing; one who goes to war takes Xia and much of the Jin over about two centuries.
Where the map's province growth leaves gaps across the Gobi, the steppe and the Tibetan
plateau, a few historical routes are linked by hand. Steppe capitals are camps of felt
tents around the khan's great yurt.

## D-085 Coalitions against a dominant player — DELEGATED (2026-10-01)
A player who grows to rule over 35% of a region's people (and ten points more than at the
start, so a state that began great is not punished for it) frightens its neighbours:
each turn, two of them at peace with each other may ally against the player (a 15%
chance, one new league a turn). Alliances already join defensive wars, so attacking one
member brings in the others. The steward warns you when a league forms.

## D-086 Demanding tribute — DELEGATED (2026-10-01)
Much of history ran on tribute, not conquest (Goryeo and Xia paid the Jin; Joseon and
Ryukyu the Ming). A court submits as your tributary if you are two and a half times
stronger, or, at war, once it has lost ground (submission is then the price of peace). It
resents it (a small grudge), and a refusal stings more. Tributaries already count fully
toward an economic victory and join your defensive wars. A "Demand tribute" button sits
with the other diplomacy buttons. Aggressive rival courts far stronger than a
neighbour take tribute instead of war half the time (never from the player).

## D-087 The library reaches the telephone — DELEGATED (2026-10-01)
Players love to rush far-future ideas ("electricity in Rome"), and the offline court
could not recognise them. Ten 19th-century advancements join the library (102 in all):
the electric battery, telegraph, telephone, photography, anaesthesia, steamships, canned
food, chemical fertiliser, cheap (Bessemer) steel and dynamite, each with prerequisites
reaching back through the tree, so asking for electricity in 264 BC shows the long road
there as goal stubs. Dates are approximate first appearances (D-040).

## D-088 Autosave and Continue — DELEGATED (2026-10-01)
The engine saves the game to an "autosave" slot after every turn; the title screen offers
CONTINUE whenever that slot exists, so a crash or an accidental quit costs at most one
turn. Named saves (Esc → Save) are unchanged. The title backdrop now centres on whichever
map is loaded (it pointed at East Asia even when the Europe map was shown).

## D-089 Difficulty levels — DELEGATED (2026-10-01)
Easy, Normal and Hard, chosen in the civilisation picker. Each level is a set of overrides
to the rival rules in rules.yaml (data, not code): Easy halves how often aggressive rulers
start wars, slows conquest and gives five quiet opening turns; Hard does the opposite with
one grace turn. Normal is the rules as written. The chosen rules are stored in the save,
so a game and its replay stay exactly the same.

## D-090 An eighth moment: Alexander's inheritance, 336 BC — DELEGATED (2026-10-01)
On the Europe map: play the twenty-year-old Alexander the moment his father Philip is
murdered, with Greece restless (Athens, Thebes, Sparta), Epirus allied, the Illyrians and
Thracians waiting to rebel, the Scythians on the Danube, and the Achaemenid empire of
Darius III from the Aegean to Bactria's edge; in the west, Carthage, Syracuse and Rome
(12 states, 54 provinces; history notes in docs/history/alexander.md). Scripted rivals
follow history loosely: the Theban and Illyrian revolts, Agis III's war, the Persian
counter-offensive in the Aegean, the Sicilian wars. Persia is much larger but raises a
smaller share of its people (`martial_bp`), and the Macedonian army a much larger one, so
the two start roughly level in strength. Tested over three seeds: a passive Macedon keeps
its lands; Persia slowly absorbs the Greek cities if nobody stops it.

## D-091 Rival rulers voiced by the model — DELEGATED (2026-10-01)
Rival rulers now speak to the player when they declare war on you, make peace, bow to a
tribute demand, or boast of something far ahead of its time. Each moment has stock lines in
the content (core/dialogue.yaml), so offline play is unchanged. When a model is
configured, the stock line and a few facts from the game (the ruler, their people, year,
temperament, faith, grudge and relative strength) go to the cheaper "fast" model, which
rewrites the line in that ruler's own voice. Why this is safe: the reply is only the text
of a speech bubble and changes nothing in the game, so replays need no record of it (rulings
still are recorded, D-021); the player's own words are never sent; the reply is cut to one
tidy line; any failure, odd shape or empty answer keeps the stock line; answers are cached
and count toward the monthly token cap. At most one rival speaks per turn.

## D-092 Explaining the court's new arts — DELEGATED (2026-10-01)
The design (§7) promised that suspicion could fall through "explanations", but nothing in
the game did that: the only cure was waiting. Measured: each idea far ahead of its time
adds up to 15% suspicion and talk settles into a framing at 25%, so two bold ideas in a row
are enough. A new royal decree gives the player a choice. **A divine gift**: priests
proclaim the arts sent by the gods (costs wealth like a festival; suspicion -20%; if the
people trust the throne - legitimacy 50% or more - talk of witchcraft or fraud turns to awe,
the "inspired" framing). **Foreign sages**: credit wise strangers from distant lands (costs
knowledge; suspicion -35%; but the story travels, and rivals learn of your inventions at
once). A story told too often is doubted: once every three turns. All numbers are in
rules.yaml. The buttons appear under Royal decrees only while people are asking.

## D-093 Keeping inventions secret — DELEGATED (2026-10-01)
The brief (§7.3) says information is a strategic resource: the player can keep inventions
secret, seal borders or feed disinformation. Advancements with a "secrecy" effect already
slowed news; two royal decrees now make it a choice. **Seal the borders** (free, three
turns): news of your inventions travels half as fast, but all trade with you stops - your
partners lose it too, and your economic path stalls while the gates are shut. **Spread
false rumours** (wealth): every true report of your arts already on the road arrives as a
muddle instead (rivals do not copy what they have only half heard), and the truth follows
much later. Only offered while there is news on the road; the panel says how many courts
it is heading to. Numbers in rules.yaml.

## D-094 Aware rival courts decide with the model — DELEGATED (2026-10-01)
Brief §7.2: courts that have heard of the player should have the model reason about how
their ruler responds; on-script courts cost nothing. Now, when a model is configured, once a
turn the aware (or free-agent) court with the deepest grudge against the player is asked
what its ruler does: **make war**, **send an envoy** or **wait**, and what they say. The
model sees only game facts (ruler, temperament, faith, relation, grudge, relative
strength, what they have heard of the player's arts, and which moves are allowed). A guard
offers war only when the court is at least two thirds the player's strength and not
already at war, and an envoy only when it can pay; anything else, or any failure, means
waiting. The move becomes an ordinary action, validated again by the engine and recorded in
the save, so replays never call the model (D-021). The ruler's line opens the turn's
speech bubbles. Alliances were left off the menu on purpose: a rival proposing one would
have to be accepted on the player's behalf. Offline play is unchanged.

## D-095 The story so far — DELEGATED (2026-10-01)
Brief §6.7 asks for a chronicle that reads like an alternate history. The Chronicle screen
now opens with "The story so far": the game in chapters of five turns, newest first, each
telling what the player's people learned, their wars and peaces, lands won and lost,
rulers who died, how the people saw the court, and which states fell, with the population
in round figures. Offline, chapters are told plainly from those facts. With a model
configured, each finished chapter is rewritten once by the chronicler (two to four
sentences, facts only) and cached; at most two new chapters are written per visit to keep
the screen quick and cheap. Like rival speech, this is presentation only and changes
nothing in the game.

## D-096 Consequences of new ideas — DELEGATED (2026-10-01)
Brief §6.7 asks for second-order effects: consequences the player did not plan for, like
printing's effect on religion. These are now content, in core/happenings.yaml, as a third
kind of happening ("consequence") that can only strike a state using the advancement it
follows. Fourteen to start: pamphlet wars and cheap scriptures (printing: the clergy lose
influence), the end of the knights (gunpowder: the nobles do), inflation (paper money), the
tyranny of the clock, the heavens are wrong (telescope: suspicion), public opinion
(newspapers), restless scholars (universities), machine breakers (spinning machines),
railway fever, ships held in quarantine, fear of the needle (vaccination), adventurers who
sail with the compass, and lawyers (written law). Happenings can now also move suspicion
and the influence of clergy, nobles and guilds. Fixed content rather than model-written:
deterministic, free, and reviewable; the model may later phrase them.

## D-097 A ninth moment: the Mauryan dawn, 321 BC — DELEGATED (2026-10-01)
India was missing. The East Asia map already reaches it (67.5°E to the Pacific, south to
Lanka), so no new map was needed; three Indian seas were added. Play Chandragupta, with
Chanakya's vow to destroy the Nandas, against the vast Nanda empire of the Ganges, the
Macedonian satraps left on the Indus (later Seleucus), Kalinga, the Chola, Pandya and Chera
kingdoms and Lanka (8 states, 35 provinces; history notes in docs/history/maurya.md).
Tested over three seeds: a passive Mauryan player keeps the Punjab; one who goes to war
survives every time and sometimes takes most of the Ganges. India gets its own look: new
portraits (a king in a jewelled turban, a brahmin, a minister) and buildings (whitewash
and brick under flat roofs, and a white stupa beside the palace hall).

## D-098 The court's counsel — DELEGATED (2026-10-01)
The brief's offline "Historical Advisors" mode (§10, DESIGN §14) had the matching of typed
ideas but not the advisers' own suggestions. Now, every turn, the Ideas tab opens with
"Your court's counsel": the steward, the general, the scholar and the diviner each
recommend one advancement you can begin now, with a reason in their own voice (lines in
core/dialogue.yaml). Each values different effects (food and wealth; strength; knowledge;
legitimacy and calm), and the one whose worry is pressing - thin granaries, a war or a
stronger hostile neighbour, restless streets or wild rumours - speaks first and urgently.
Advisers think within their age: an idea a little ahead of its time pleases them, but what
lies centuries away is the ruler's own strange knowledge, not theirs to suggest.

## D-099 A war of armies — owner request (2026-10-01)
The owner asked for far richer fighting and strategy. War was abstract: each turn the
stronger side had a chance to take one border province. Now wars are fought by armies
(DESIGN §10b): raised from a province's people with costs and upkeep, made of the kinds of
soldier the state's advancements and resources allow (13 kinds in core/units.yaml - data,
so a new kind needs no code), marching across the map, fighting battles weighed by unit
match-ups, terrain, walls, morale, generals and fortune, besieging provinces until the
walls fall, and wasting away to supply and attrition. Every rival court raises and directs
its armies by simple rules (mass at the capital, march on the nearest reachable enemy
province only with good odds, defend its land, go home at peace); the player's armies
defend their land unless told otherwise. Wars last longer than before (peace at 8,000
weariness, a winning side tires at half speed) because campaigns take several turns.
Battles, sieges and lost armies are spoken of by the general and recorded in the chronicle
and its chapters. Tested: twelve engine tests; sims across scenarios show campaigns,
battles, sieges and conquests, and deterministic replays. This replaces the "tactical
battles out of scope" line of DESIGN §16 at the owner's request.

## D-100 Armies on the map — DELEGATED (2026-10-01)
Every army stands beside its province's city in its owner's colours, larger for larger
hosts, with its strength above it (and siege progress while it besieges); a marching army's
road is drawn ahead of it; crossed swords mark last turn's battlefields. Clicking a province
lists the armies there (soldiers, morale, general, what they are doing) and, for your own,
the orders March… (then click the destination), Hold, Defend and Disband; your provinces
also offer "Raise a levy here" in three sizes and five mixes, with the cost shown. Orders
are ordinary recorded actions, so replays stay exact.

## D-101 Generals, mercenaries, land for peace and elephants — DELEGATED (2026-10-01)
- **Generals**: scenarios name each state's commanders (Parmenion and Craterus, Memnon of
  Rhodes, Hamilcar Barca and Xanthippus, Bai Qi and Sun Bin, Subutai and Jebe, Shibata
  Katsuie and the young Hideyoshi, Yamagata Masakage...), with a skill of 1-5 and a gift:
  master of horse, siege master, stubborn defender, bold attacker, careful quartermaster,
  or beloved by the men (strengths in rules.yaml). New armies take the next free general;
  one whose army disbands returns to court; one who falls in battle is gone. Generals
  whose careers came later are noted as such.
- **Mercenaries** are now a real company of professionals that musters at the capital
  for two turns, costs no men of your own, and then marches away.
- **Land for peace**: at war, "Demand land" asks for every province your armies stand
  in; only a side that is losing (more battles and provinces lost, and tired or clearly
  outmatched) agrees, and it never signs itself out of existence.
- **Elephants** are a map resource where war elephants came from (the Ganges and Kalinga,
  Assam, Lanka, Numidia and Carthage, Kush, and the Seleucid stud at Apamea).

## D-102 Walls, pillage and the price of levies — DELEGATED (2026-10-01)
More choices in war, each with a cost:
- **Walls**: build up to three levels in any of your provinces (stone walls, then towers
  and gates with Fortification, then star bastions with the Star fort). Each level adds
  to how long a siege takes. Costs materials and wealth.
- **Pillage**: an army in enemy land can ravage it instead of besieging: people killed or
  driven off, wealth carried off, half the crops and goods lost for two turns, the enemy
  wearier - and a lasting grudge. Pillaging armies live off the land (no campaign
  attrition). Steppe peoples (four times the usual mobilisation and more) raid what they
  cannot take quickly.
- **Levies breed unrest**: calling up men angers their families, in proportion to how many,
  less among warlike peoples.
- **Field battles weigh only the ground** (hills, mountains, marsh); walls, capitals and
  last stands count in sieges. Before, a lone capital's defenders counted triple in the open
  field and evenly matched rivals (Sengoku Japan) never dared attack. Rival courts now
  accept an even fight if warlike and want a modest edge if cautious, judged against the
  enemy armies near their objective.

## D-103 Battles told as stories — DELEGATED (2026-10-01)
Battle reports were formulaic. Now each battle is told by a fitting tale from content
(core/tales.yaml): horsemen sweeping round a flank on open ground, horse archers wearing
down an army on the steppe, a hedge of spears holding a pass, arrows darkening the sky, a
long grinding slaughter of infantry, elephants scattering horses, an army caught crossing
a river or strung out in a forest. The engine picks the tale that best fits the soldiers
who decided it, the ground, and whether it was a rout, then adds the losses and any fallen
general. A new way to tell a battle is a YAML entry.

## D-104 Dilemmas — DELEGATED (2026-10-01)
Brief §6.7 asks for events generated from the situation; the owner asked for storytelling
and strategy. Dilemmas are choices put to the ruler, as content: when one's conditions hold
it may arise (its chance per decade), a card in the middle of the screen tells the
situation and offers two or three answers, each showing what it will do (stores, unrest,
legitimacy, suspicion, the favour of clergy, nobles and guilds, a new idea, volunteers).
Unanswered at the end of the turn, the court takes the first answer. General ones (a comet,
a hungry city, a wandering preacher, whispers of sorcery, a merchants' charter, a library
for sale, deserters, veterans who want land, strangers from afar, a fever in the slums)
and historical ones: the Gordian knot and Diogenes for Alexander, the corvus for Rome,
the year 1000, Shang Yang's reforms for Qin, Chanakya's Arthashastra for the Mauryas, the
Yassa and the captured craftsmen for the Mongols, and the Portuguese guns of Tanegashima
in Sengoku Japan. Answers are recorded actions, so replays stay exact.

## D-105 Envoys come to you — DELEGATED (2026-10-01)
Diplomacy was all one way: the player sent envoys, rivals only acted. Now rival courts send
envoys with proposals the player must answer, shown on the same card as dilemmas: a beaten,
weary enemy **sues for peace**; a far stronger, aggrieved, warlike neighbour delivers an
**ultimatum** (pay a quarter of the treasury and become its tributary, or face war); a
friendly trading partner at war with the player's enemy **proposes an alliance** (accepting
means joining its war); a merchant court **proposes a trade pact**. A court with something
to propose sends envoys with a 25% chance per decade, one proposal at a time. Unanswered,
the court refuses for the player - which, for an ultimatum, means war. Answers are recorded
actions, so replays stay exact.

## D-106 Conquered peoples remember — DELEGATED (2026-10-01)
Conquest was permanent the moment the walls fell. Now every province has a people (its
owner at the start). A conquered province keeps its people, and while it has no garrison
(an army of its rulers with at least one man per hundred people) it may rise - 15% a decade,
more when the realm is restless - going back to its old state if that still stands, or
breaking free if not (a capital, with its court and guards, never rises). After 150 years
a conquered people thinks of itself as its rulers' own. The province card says whose people live there, how long ago they were conquered,
and what garrison holds them. Empires now cost soldiers to keep, not only to win.

## D-107 Navies: fleets, sea battles, command of the sea — DELEGATED (2026-10-01)
Armies crossed seas freely: Carthage's great fleet and Rome's lack of one meant nothing.
Now warships are content (`ships.yaml`: galleys, heavy warships, war junks, carracks, gun
ships, each needing its advancements), built as squadrons of 10, 25 or 60 in a coastal
province and launched into the sea on its shore. Fleets sail two seas a turn; enemy fleets
that meet fight once a turn (the stronger, with luck, wins; the beaten fall back to home
waters or a safe sea); sea battles are told like land battles, from content tales fitted to
the winners' ships and people (rams in the narrows, fire-bombs from Song junks, broadsides,
Greek fire for Byzantium, the corvus for Rome, turtle ships for Joseon). **Whoever commands
a sea decides who crosses it**: an army may cross only where no stronger enemy fleet holds
the water. **Blockades**: where enemy fleets command every sea on a province's shore, its
harbours close - it loses most of its trade, and its people tire of the war. Fleets cost
wealth every turn; unpaid crews desert. States start with fleets in proportion to their
coastal people and a historical seafaring factor per scenario (`navy_bp`: Carthage 4x,
Rome almost none in 264 BC; Venice, Denmark and Norway strong in 1000). Rival courts at
war build ships when out-matched at sea and send their fleets to meet the enemy's - or to
blockade its coasts.

## D-108 Battle plans and veterans — DELEGATED (2026-10-01)
Battles were decided by numbers, soldiers and ground alone. Now every army fights with a
battle plan (content, `core/tactics.yaml`): steady line, headlong charge, shield wall
(defence only), skirmishing (needs archers), envelopment (needs horse), feigned retreat
(needs much horse) and ambush (defence in forest, hills or marsh). Each beats some plans
and loses to others (a shield wall breaks a charge; arrows wear down a shield wall; a
feigned retreat draws an envelopment away), and the side whose plan wins gets +30% (+60%
with a general gifted for it). Plans also change the ground's worth, the blood spilt (a
charge is bloody, skirmishing is not) and how badly the beaten are destroyed (Cannae).
A general left to choose answers what he expects the enemy to do; a great general (3 stars
or more) reads the enemy's real plan. The player may order a plan for each army, and sees
the likely plan of rival armies. Battles are told by plan (Cannae, the Mongol feigned
retreat, the Teutoburg forest). Armies also learn: victories (and surviving defeats) make
veterans, up to +30%; raw recruits dilute them; mercenaries come as veterans.

## D-109 Graphics pass toward Rise of Kingdoms; heraldic symbols — DELEGATED (2026-10-01)
The owner asked for graphics "incredible", modelled on Rise of Kingdoms, rated 0-10 against
it and improved past 8; and for empires to bear symbols rather than letters. Done so far:
the coastline is drawn from the real heights as a smooth line with sand beaches and surf
(no more staircase cells); turquoise shallows deepen to rich blue, with painted swells
offshore; land is lush green; owned land carries a light wash and a glowing border in its
owner's colour; mountain ranges are fuller, with snowy peaks. Real 3D models from the
Kenney kits (CC0): forests of oaks, pines and palms; capitals as castles with towers,
gatehouses and banners whose roofs take the owner's colour; fleets as sailing warships;
siege trains with trebuchets. Armies are ranks of soldiers with shields in their colours
under a mounted commander and a standard. Every civilisation has a heraldic symbol (content
`symbols.yaml`, chosen from its history: the Roman eagle, the Athenian owl, the Seleucid
anchor, the Chola tiger, the Gojoseon bear, the Mongol wolf...), drawn on a shield in the
picker, the top bar and over its lands; art from game-icons.net (CC BY 3.0, credited on
the title screen). The Mac renderer's global illumination washed colours out, so it is off
and colours are graded instead. Labels of armies and fleets give way to more important
names. Clouds only appear over the whole-world view.
Second round: towns are now real little houses put together from Kenney fantasy-town pieces
(plaster or timber walls with doors and shuttered windows, gabled, steep or pointed roofs in
terracotta, slate or thatch, with a touch of the owner's colour). The landmarks your ideas
raise round your capital are kit buildings too: a stone windmill with turning sails, a water
mill, a clock tower, an observatory, a school hall, smoking forges, a market with stalls, a
harbour sailboat. A Roman-style temple has a stepped platform and columns all round. Seen
from far off, where the towns are hidden, each chief city stands as one larger-than-life
icon (a walled castle for a capital, a cluster of houses for a town) in its owner's
colours, as cities do on Rise of Kingdoms' map. Trade, alliance and tribute ties are
dashed lines flowing out from your capital, and fade out as you zoom into a city. The
owner wash is paler, so red over green land turns rosy rather than muddy. Province names
sit on dark name plates with a gold rim and their owner's colour at one end. Armies and
fleets are drawn large to read from afar and shrink toward life size as the camera comes
down to a city; soldiers carry tall rimmed shields and crested helmets. Mountain peaks are
faceted grey rock on a green foot with snow caps only on top (they were all-white blobs up
close), and settle into lower hills as the camera comes down so they never wall off a town.
East Asian towns have grey-tiled roofs and a palace of red pillars under a double roof; an
inland capital no longer shows a harbour boat on dry land.

## D-110 CI uses far fewer free minutes — DELEGATED (2026-10-01)
GitHub Actions stopped running because the repository's free monthly minutes ran out (the
owner confirmed). Every push had run the whole workflow twice (once as a push, once for the
open pull request), each time with the Mac app build, and the macOS checks whose minutes
count tenfold. Now the Linux checks run once per pull request update (and on pushes to
main); the macOS checks and the Mac app build run only when started by hand from the
Actions tab. The checks and the app are run and built in the cloud session anyway before
each commit. Roughly a tenth of the minutes per push.
Later the same day the owner made the repository public (free, unlimited minutes for
public repositories); the macOS checks and the Mac app build run on every pull request
update again, and each update still runs only once.

## D-111 Province buildings; cities that grow on the map — DELEGATED (2026-10-02)
The owner asked to stop polishing graphics and perfect the gameplay against the brief, and
for cities to visibly spread out and fill with buildings as a civilisation develops. The
brief's effect menu (§5.10) named `unlocks_building`, but there were no buildings: every
improvement was realm-wide. Now each province holds buildings (content
`core/buildings.yaml`; schema `content/schema/buildings.py`; engine
`engine/buildings.py`), gated by advancements, coast, river or ore, paid up front, built
over one or two decades and kept with upkeep. They raise the province's own output, growth
and room for people, or calm the realm, teach reading and train soldiers; upgrades take the
place of older buildings. A province holds two plus one per 250,000 people (up to eight),
and each standing building makes the next a quarter dearer, so growth and building feed
each other without one city taking everything. Pillage burns the newest building, which
gives raiding a lasting cost. Rival courts (and the simulation bots) build one a turn in
their biggest city when their stores hold three times the price, so rivals develop too.
On the map, each building appears in its city (a round temple, market stalls, a granary
barn, forges with smoke, a water mill, an aqueduct's arches...), the middle of the city is
kept for them, and cities are rebuilt larger whenever they have grown by a quarter or
raised something new. The numbers are a first pass, to be tuned with play.

## D-112 Rival courts no longer starve themselves; low priority is steady work — DELEGATED (2026-10-02)
Playing the Punic Wars with the simulation tool showed small rival states (Pergamon,
Rhodes, Sparta, Syracuse, Pontus) in famine and riots for most of the first 30 turns. The
cause: when a rival court heard of an idea, or a script told it to adopt one, it started the
project without checking whether it could staff it; one idea needed more labour than its
whole workforce, so farmers were pulled from the fields. Now (1) low-priority projects are
"steady work": funded only from spare hands (the surplus left after higher tiers), they
never divert farmers, never count as a shortfall, and do not decay while they keep moving;
(2) rival courts start a project at full pace only if their spare hands cover it, otherwise
as steady work, one at a time. In the same 30 turns there is no famine or riot anywhere and
small states still adopt a few ideas. The player gains the same choice: push an idea hard
(and risk hunger) or let it ripen slowly. Also, courts choosing buildings value calming
ones more as unrest rises, and the simulation bots start nothing new while unrest is above
half (the balance test "careful growth stays stable" caught a growth bot that built five
schools and no temple while unrest climbed).

## D-113 The fall is not the end: new dynasties and restored states — DELEGATED (2026-10-02)
D-011 said the player's guiding hand follows the lineage across dynastic change and the game
ends only when no successor survives; in practice every scenario gives each lineage a single
state, so a collapse or conquest simply ended the game. Now: a state that collapses from
within but still holds land passes to a new dynasty (revolts counted afresh, half the unrest
released, legitimacy reset to an untested 40%); a state destroyed by conquest is restored
where its remembering people rise against an unguarded conqueror (they rise twice as eagerly
as other peoples, and the state takes that province as its capital); the player is defeated
only when no province still remembers their state. This applies to rival states too, so
history keeps its restorations. New spoken moments: `dynasty`, `restoration`; the collapse
line no longer says "it is over". The side panel tells an exiled player where their people
still remember them.

## D-114 Infrastructure: some ideas need buildings standing in the realm — DELEGATED (2026-10-02)
Brief §5.4 lists infrastructure (roads, workshops, mills...) among what makes an idea
buildable. Until now that meant only other advancements. Tech requirements now include
`buildings`: printing press, movable type and spinning machines need workshops; blast
furnaces, crucible steel and cannon need forges; coke smelting needs forges and mines; the
steam engine and railways need mines (historically, engines first pumped mines);
universities need a school; banking a market; hospitals a temple; caravels, sternpost
rudders and steamships a harbour. An upgrade counts for what it replaced (a bank is still a
market). Blocked ideas say what is missing ("needs forges built somewhere in the realm").
Courts building for themselves favour what unlocks an idea they are waiting on, and the
language model's state summary lists the realm's buildings. This makes the bootstrapping
puzzle concrete: to print, first build the workshops.

## D-115 Spies and intelligence: rival plans you can learn (and misread) — DELEGATED (2026-10-02)
D-013 decided rival scripts are seen through intelligence reports that can be wrong, their
quality set by relations, trade, distance and spies; brief §7.3 lists spies among the ways
news travels. Nothing showed the player a rival's intentions. Now each turn the player
gets a report on every court in touch whose source is good enough: allied envoys (60%
reliable), tribute bearers (50%), merchants (40%), captured soldiers in wartime (30%),
less 10 points per border beyond the first. Each of up to two pending intentions is told
truly with that chance, otherwise with the wrong target (a planted or garbled story). A new
decree, **Send spies** (25 wealth hundredths per 1,000 people, five turns), adds 40 points,
the court's current projects and its men under arms; each decade spies have a 20% chance to
steal the methods of the court's oldest advancement you lack (30% of the work done when you
start it) and a 12% chance to be caught (they are lost and the court bears a grudge).
Rivals do not spy yet. Warnings that a court "means to make war on us" are shown in red.

## D-116 Rival courts make their own history once their scripts run out — DELEGATED (2026-10-02)
A 60-turn simulation of the Punic Wars showed every rival war came from the historical
scripts in the first 17 turns; after that the world went quiet for 400 years and borders
froze. Courts only acted on their temperament once they became "free agents" (by being
affected by the player). Now a court whose scripted intentions have all fired or lapsed
acts on its temperament too: aggressive rulers attack a neighbour they outmatch by half
again; cautious, scholarly and pious rulers also go to war, a fifth as often, and only
against a neighbour they bear a deep grudge (30%+) and outmatch twice over; mercantile
courts open trade. In the same simulation wars now continue throughout the game (53 wars,
15 conquests, one state swallowed), while uprisings and peace keep it from snowballing.

## D-117 Rival courts quiet suspicion and win back doubting peoples — DELEGATED (2026-10-02)
In a 60-turn simulation the strongest states (Rome, the Seleucids, Macedon) sat near 0%
legitimacy for centuries, branded frauds by suspicion they never answered: only the player
could explain the court's arts, and rival courts feasted only in unrest. Now rival courts
(and the simulation bots) have priests proclaim their new arts divine when suspicion passes
40% (if the treasury holds twice the price and the people have not heard the story too
recently), and hold festivals when legitimacy falls below 20% as well as in unrest. In the
same simulation Rome ends at 92% legitimacy and the Seleucids at 67%.

## D-118 Wars end on terms: the side that tires first pays — DELEGATED (2026-10-02)
Testing a conquering player showed armies winning battle after battle and besieging a
capital, only for the war to end in a plain peace the moment the losing side grew weary:
whoever tired first, the war simply stopped and every siege was lifted. Now, when one side
is worn out first, it sues for peace and cedes every province the other's armies stand in;
if that is all it has left, it becomes the other's tributary instead of vanishing. If none
of its land is held, or both sides tire together, it is a plain peace. The same for a player
demanding land when the enemy's only province is occupied (it used to "cede" nothing):
the enemy submits as a tributary. The simulation's military bot now really campaigns
(declares war on a neighbour it outmatches by 40%, marches on its weakest border province,
sues for peace only once nothing is under siege and the war is eight turns old), so the
balance tests exercise conquest: as Qin it grows from 3 to 5 provinces in 60 turns.

## D-119 Spend the stores: hastening work, and hoards that waste away — DELEGATED (2026-10-02)
Over 60 simulated turns Rome piled up 115,000 materials, 108,000 wealth and a million
knowledge while producing about 4,000 a turn: labour is what limits projects, so stores
became meaningless numbers. Two changes: (1) **Hasten**: once a turn a project can be
pushed on by a full turn's work, paid from the stores (wealth for hired craftsmen at three
times the turn's labour and wealth, and twice its materials and knowledge); rival courts and
bots hasten when their stores hold five times the price. (2) Stores of materials, knowledge
and wealth beyond ten turns' production waste away, a fifth of the excess each decade
(timber rots, scrolls are lost, treasure is embezzled), like the granary's spoilage. In the
same simulation Rome's wealth now ends near 26,000 and it adopts 74 ideas instead of 68.

## D-120 Chronicle mode: live through history and try to outdo it — owner's direction (2026-10-02)
The owner asked for a more scaffolded playthrough along history as it really happened, with
better storytelling, lightly romanticised but never at the cost of the history, keeping the
ideas ahead of their time and everything already built. Asked four questions, the owner
chose: **history bends, then catches up** (your choices change the world, but the great
turning points still come while their conditions hold; a turning point whose world no
longer exists is passed over, and the chronicle tells how history turned); **compare with
real history** (each chapter's aftermath tells what really happened and how your state
stands against the real one at that date; the goal is not to win but to outdo history);
**Rome against Carthage first** (19 chapters, Messana in 264 BC to the fall of Carthage in
146 BC, and 20 almanac entries of what happened elsewhere); **short turns** (two years a
turn in a chronicle; `campaign_years_per_turn` in the scenario).
How it works: chapters and almanac entries are content (`chapters`, `almanac` pack kinds).
One chapter waits at a time and the turn cannot end while it does (in the client); answering
is a recorded action, so replays stay exact; a chapter left unanswered is settled as history
did. Choices carry a dilemma's effects plus deeds in the world (war, peace, alliances,
tributaries, land taken or given, fleets, men). A choice may need an idea in use: these are
the anachronisms of the player's own making (a crossbow line at Cannae, a rudder-steered
fleet), shown locked with what they need until then, so the core idea game feeds the story.
Free play stays as it was; the picker offers "Follow history" where a scenario has chapters.

## D-121 The game is called Meritus; a new app icon — owner's direction (2026-10-02)
The owner renamed the game **Meritus** and asked for an icon about "the asymmetry of you
changing history with today's advancements". The icon is a tile split by a jagged seam of
light: on the left, the ancient world (parchment, a gold laurel wreath, a light bulb of
cracked stone with a bronze base); on the right, today (a night-blue blueprint grid, glowing
circuit traces finishing the wreath, the same bulb lit in glass and steel). Its source is
`client/icon.svg`. Renamed wherever players see the name: the title screen, the disclaimer,
the app (Meritus.app), the download (Meritus-mac), and how the AI's prompts name the game.
Kept, deliberately (DELEGATED): the code name `anachronism` for the Python package, the
commands, the repository and the environment variables (renaming them would break the
owner's settings file and every link for no visible gain); the bundle identifier; and the
folder that holds saves and settings (a custom user folder keeps it at "Anachronism", so
nothing is lost). The word "anachronism" still names the in-game idea of an advancement
ahead of its time.

## D-122 The second chronicle: Qin unifies China (350-221 BC) — DELEGATED (2026-10-02)
28 chapters from Shang Yang's second reform to the First Emperor, after Sima Qian's Shiji
and the Zhanguo ce, plus 18 almanac entries (Mencius, Alexander in India, Ashoka, Euclid,
Eratosthenes...). Three ideas carry over from the brief: the great figures speak in their
own names (a chapter may name its speaker: "Shang Yang", "Bai Qi", "Li Si"); dark history is
told plainly (Changping's prisoners) but a choice history did not take can spare them; and
ideas brought in early open new paths (stirrups at Changping, gunpowder at Handan, examined
officials in 237 BC, printing the one script in 221 BC).
Playtesting with the simulation bot showed what the chapters needed to be playable:
- **Decisive battles end, they don't linger.** A historical victory (Danyang, Yique, Ying)
  now takes its land and leaves a grudge instead of an open war; open wars had left Shu
  bare for Chu to take.
- **Reforms last.** A chapter's choice may change how many of the people the state can arm
  (`martial_bp`): carrying Shang Yang's reform through makes Qin the war machine it was;
  repealing it does the opposite.
- **Land taken in a chapter comes with a garrison.** The conquering army stays (half again
  as many men as the province needs, at no cost, holding its ground), and a garrison told to
  hold no longer merges into a passing army and marches off with it - a fix for every
  player and court, not only chronicles.
- **Great conquests need the strength to make them.** A chapter can require the player to
  outmatch a state (`needs_stronger_than`): Han falls only to a Qin half as strong again;
  otherwise history turns, and the chronicle says so. A choice may `conquer` a whole state.
In the same simulation Qin now stays level with history to 300 BC and unifies China in
220-218 BC, a few years after the real one.

## D-123 Seamless zoom: nothing pops, the camera glides — owner's direction (2026-10-02)
The owner asked for smoother transitions when zooming and moving around. What popped:
towns, trees, peaks, landmarks, armies and roads each appeared or vanished at a hard camera
distance (some in square map tiles at once), names blinked on and off as they made room
for each other, the camera zoomed toward the middle of the screen in uneven steps, and
"visit the capital" jumped. Now:
- **Fades, not pops.** Every distance cutoff fades over the last fifth of its range
  (`scripts/lod.gd`); near towns crossfade with their far-away icons. Godot's own fade
  hides our custom-shaded models (Kenney kit buildings, mountain peaks) outright, so those
  dissolve themselves with a fine dither, each building by its own distance
  (`shaders/lod.gdshaderinc`) - which also works on the simpler renderer. Per-object shader
  values ran out of room (thousands of buildings), so the fade distances sit in a few
  copies of each material instead.
- **Names fade.** Map names ease in and out, both at the ends of their distance range and
  when one gives way to another, instead of blinking.
- **The camera.** Zoom glides in equal steps of scale and keeps the point under the mouse
  still, as maps do; a dragged map carries on and slows when let go; keyboard panning
  eases in; flying to a place arcs up and back down over long journeys.

## D-124 Each turn plays out on the map — owner's direction (2026-10-02)
The owner asked for animations of what happens between turns, the marches and attacks, to
make it feel epic. After End Turn the map now shows the turn before its results ("350 BC →
340 BC, the years pass"; the panels slide aside): armies march along their roads with dust
and drums and fleets sail their courses trailing spray (the camera follows the player's);
the player's battles on land and sea are visited one by one (the hosts lunge at each other, dust, sparks and
flashes, the battle's name, VICTORY or DEFEAT and a horn), other battles flare where they
were fought; destroyed armies and fleets sink away; besieged cities burn while stones arc
into them from the siege lines ("Siege of Hexi · 45%"); the map recolours and every province that changed
hands raises its new owner's banner and arms, with a ring sweeping over the land and a
line ("Etruria is ours!"); new armies rise from the ground; the camera returns. Any click
or key skips to the end, and Settings can turn it off. The engine is untouched: the server
compares the map before and after the turn (`tools/replay.py`). New synthesised sounds:
marching drums, a battle clash, a victory horn and a defeat horn. Painted "moment" cards
for disasters and the like will follow when the art from docs/ART_PROMPTS.md comes in.

## D-125 The future is yours alone; rivals get it only by spying on you — owner's direction (2026-10-02)
The owner: "you as the person playing should be the only person who has these technologies
unless other places come and spy on you to steal the technologies". Until now rival courts
(run by the same planner as the test bots) started any advancement whose prerequisites
they had, however far ahead of its time, and copied the player's ideas from mere hearsay.
Now a rival court can only work on advancements whose time has come (at most 25 years
before history had them, `foresight_years`) or whose secret it stole: history keeps its
own pace for everyone but the player. A court that has heard of the player's arts sends
spies to steal one (1.8 chances in 10 a decade per court, the earliest it could use);
the player's people catch 4 in 10 of them (twice as many while the borders are sealed,
which also halves the attempts), and the player hears of every theft and every foiled
attempt. A stolen secret starts the thief's work with a head start. In a 15-turn test as
Rome the player held 8 ideas from the future and the rivals one between them, while five
thefts and three foiled attempts were reported.

Also fixed: the Mac build never carried the game's font files, so every screen used
Godot's plain default font, and panels such as the dilemma box measured their text with
an empty font and shrank to slivers under their own words. The export now carries the
fonts, and the font loader falls back to the imported copy if the raw file is missing.

## D-126 The time traveller's notebook — owner's direction (2026-10-02)
The owner: the premise ("what if you went back in time with today's knowledge") did not
feel significant enough, and choosing advancements was awkward. Now:
- **The notebook from the future** (N, or the gold NOTEBOOK button beside End Turn, or the
  banner atop the Ideas tab) is a two-page journal of everything the player remembers of
  the world to come - every idea from the future, not only those within reach, sorted into
  Ready now, Needs groundwork, Being made, In use (brought from the future) and Of this
  age. Each page gives how many years before its time it is, the player's note, **In our
  history** (who first made it, where and when - written for all 102 advancements), what
  it will do, what it takes (per turn, and as a share of free hands), the risks (suspicion,
  spies) and what it builds on (click to turn to that page), with one big button: Bring it
  into the world.
- **Breakthroughs are an event.** When an idea from the future works, the turn's replay
  flies to the capital, where a pillar of golden light rises with its name and "N years
  before its time", and a card tells what really happened in our history and what changes.
- **The mark on history**: the game remembers the year each idea came into use, and counts
  how many were brought early and by how many years in all.

## D-127 Developing your cities: real numbers, ranks you can see, one screen for it all — owner's direction (2026-10-02)
The owner: building was awkward, it was unclear what a building actually gives, and cities
should visibly expand and develop so that one can stop and develop one's base. Now:
- **The Cities screen** (🏛 CITIES beside the notebook, C, or "Develop the city" on a
  province card) lists every city with its rank and whether it has room to build; the open
  city shows what it makes each turn, what it could build - each with what it would add
  **there**, in plain numbers ("+119 food a turn, its people grow 10% faster, room for
  61,000 more people"), what it costs, how long it takes and what it costs to keep, with the
  best value marked - and its building plots: built, going up, empty, and when the next one
  opens. One building goes up at a time in each city, so building more means building in
  more cities, all from one screen. The engine computes one province's output with or
  without a building (`economy.province_output`); production itself is unchanged.
- **Ranks**: a city is a Village, Town, City, Great city or Metropolis by its buildings and
  people (a point a building, a point per 250,000 people). On the map a city spreads wider
  and fills with houses as it rises; a City gets walls of its own, a Great city spills out
  into suburbs beyond them. Building work stands on the map as the new building half-risen
  in timber scaffolding, with a crane.
- Place names now float above their cities, so a city's buildings show beneath its name.

## D-128 A building queue in every city — DELEGATED (2026-10-02)
Follow-on to D-127 ("ergonomically smoother to build more"): while builders are at work
in a city, BUILD becomes QUEUE, and up to three buildings wait their turn there. Each is
paid for only when it starts; if the stores cannot pay yet it waits; if it can no longer
go up (no plot, the city lost) it is dropped. A queue belongs to whoever made it and lapses
when the city changes hands. Queued buildings can be taken off the plans (✕).

## D-129 The future stands out on the map — DELEGATED (2026-10-02)
Follow-on to D-126: landmarks around the capital that were built from an idea brought in
before its time now carry a slowly turning golden halo, a soft glow and rising sparkles,
and up close their name and how early they came ("✦ Paper · 144 yrs early"), so the
player's mark on history can be seen at a glance.

## D-130 The third chronicle: Oda Nobunaga, 1560-1582 — DELEGATED (2026-10-02)
Follows the owner's "keep building" and the plan's "more chronicles". Sixteen chapters
from Okehazama to Honno-ji and Yamazaki, with a Sengoku almanac (Lepanto, Manila, Tycho's
new star, Yasuke, the Gregorian calendar). Decisions:
- **One year a turn.** Nobunaga's career is 22 years of crowded events; at two years a
  turn the chapters queued up and lapsed.
- **Muskets at the start.** Matchlocks were everywhere in Japan by 1560 (Tanegashima,
  1543), so every daimyo and the Ming now start with them; Joseon (none until the 1590s)
  and Ryukyu do not. This also affects free play of the scenario, which is more accurate.
- **A chapter can end a reign** (`ruler_falls` in a choice's deeds): the ruler dies as the
  chapter tells it and the next in line takes over, with the usual cost to legitimacy.
  Honno-ji's historical choice kills Nobunaga and loses Kyoto to Mitsuhide.
- **The chronicle's leader is spared old age** until the year their reign really ended
  (`leader_until` on a scenario state; only in chronicle mode, only the first ruler of the
  player's state). In tests Nobunaga kept dying of old age in the 1570s.
- **No Tokugawa state on this map**, so Ieyasu's Mikawa counts as Oda land once the
  Kiyosu alliance is made; the chapters say so plainly.
- Choices only the player's future ideas open: coke-smelted gun barrels, a joint-stock
  company at Sakai, printed broadsheets against Mount Hiei, spyglasses at Nagashino and
  Honno-ji, an academy at Azuchi, steamships in Osaka bay, tinned rations over the winter
  passes into Kai.
- With a passive test player (no wars of its own) all 16 chapters are played on every
  seed tried, ending with 5 to 7 provinces against history's 12. A player who fights does
  better.

## D-131 The fourth chronicle: Goguryeo, AD 400-475 — DELEGATED (2026-10-02)
Fourteen chapters from Gwanggaeto's rescue of Silla to Jangsu's capture of Hanseong (the
monk Dorim and his game of baduk), with an almanac (Faxian, the sack of Rome, Zu
Chongzhi's pi, the Yungang Buddhas). Decisions:
- **Two years a turn**, and Gwanggaeto is spared old age until 416 (D-130's rule), so his
  death is the chapter 'The Great King Dies' (412): every choice in it ends his reign,
  because the choice is what he tells his son, not whether he dies.
- **Two new deeds for chapters:** `capital` (the court moves; Jangsu to Pyongyang in 427)
  and `break_away` (an ally or tributary turns wary; Silla leaving Goguryeo's orbit in
  433). Both show in the choice's summary.
- Where the map has no state for something (Eastern Buyeo, the Ye of the east coast) the
  chapter takes an unclaimed province (the Mohe forests, the eastern mountains).
- The Feng Hong chapter opens while Yan still stands and Wei is at its gates, since Wei
  does not reliably take Longcheng on its own in play; one choice lets you take it first.
- A passive test player plays all 14 chapters on the seeds tried.

## D-132 Chronicle rulers keep history's calendar — DELEGATED (2026-10-03)
Follow-on to D-130. Sparing a ruler until their reign's real end was not enough: after
that, old age was left to the dice, and in testing Duke Xiao of Qin lived until 294 BC
(he died in 338). A scenario now says, for its first ruler and each named heir, either
`died` (a natural death: in a chronicle the player's ruler lives until that year and dies
in the turn that contains it) or `until` (a violent end a chapter tells, like Nobunaga at
Honno-ji: spared until then, and if the player changes history the ruler lives on with
the usual odds). Free play is unchanged. Qin now has its real line through Xiaowen and
Zhuangxiang to King Zheng (the future First Emperor), who takes the throne just as his
chapter opens in 246 BC; Jangsu of Goguryeo reigns to 491.

## D-133 The fifth chronicle: Ramesses II's Egypt, 1275-1208 BC — DELEGATED (2026-10-03)
The owner asked (going to sleep) for storylines for every civilisation and age, to be built
until they wake. Egypt comes first because the Kadesh moment had none. Twelve chapters:
the march north, Kadesh (the planted Shasu spies), the Sherden bodyguard, carving the Kadesh
poem, Amurru lost, the fugitive Hittite king, the silver-tablet treaty, Abu Simbel and
Nefertari, the Hittite bride, Prince Khaemwaset, the Libyan forts, and Merneptah at Perire
(the stela that first names Israel). Three years a turn; Ramesses dies in 1213 BC as he
did (D-132), followed by Merneptah and Seti II. The ideas that open choices history never
had: iron weapons, relay riders at Kadesh, the alphabet, concrete, schools. All twelve
chapters play with a passive test player.

## D-134 The sixth chronicle: Alexander, 336-323 BC; crowded years — DELEGATED (2026-10-03)
Sixteen chapters at one year a turn: Philip's murder, Diogenes, Thebes, the Granicus,
the Gordian knot, Issus, Darius's offer ("if I were Parmenion"), Tyre, Alexandria and Siwa,
Gaugamela, Persepolis, Darius's death, Cleitus, the Hyphasis mutiny, the Susa weddings,
and Babylon, where every historical choice ends the reign and one anachronism (germ theory)
lets Alexander live. Two engine changes, because Alexander's years are crowded:
- **Several chapters a year.** Answering a chapter now opens the next one whose year has
  come, instead of waiting a turn; the client shows "what really happened" first and the
  next chapter after it. Before, chapters fell behind their years and some lapsed.
- **Same-year chapters keep the order they are written in** (they were sorted by id,
  which put Darius's death before Persepolis and made Persepolis lapse).
Conquering Persia brings a regional victory mid-chronicle; "keep playing" carries on.
All five earlier chronicles still play through.

## D-135 The seventh chronicle: the Mauryas, 321-232 BC — DELEGATED (2026-10-03)
Seventeen chapters across three reigns, at three years a turn: Chanakya and the porridge,
the fall of the Nandas, Rakshasa's ring, the Greeks leaving the Indus, Seleucus's 500
elephants, Megasthenes, the Arthashastra, the Girnar lake, Chandragupta becoming a Jain
monk (a chapter ends his reign; staying king is allowed), Bindusara's Deccan, the letter
asking Antiochus for figs and a philosopher, Ashoka's disputed throne, Kalinga, the
conquest by dhamma, the edicts, Mahinda in Lanka and the half-fruit. Bindusara and Ashoka
die in their real years (D-132). Many of these stories come from legends written down
centuries later; each history note says which. All 17 chapters play with a passive test
player.

## D-136 The eighth chronicle: the Mongols, 1206-1279 — DELEGATED (2026-10-03)
Twenty-one chapters across five Great Khans, at three years a turn: the assembly on the
Onon, the shaman Teb Tengri, the forest peoples, the dyke at Zhongxing, the Uyghurs' letter,
the Badger's Mouth, Zhongdu, Yelu Chucai, Jebe and Kuchlug, Otrar, the last campaign,
'pasture or taxes', Goryeo's island court, the fall of the Jin, Karakorum and the yam,
news from Hungary, Dali, Diaoyu, Xiangyang, the kamikaze and Yamen. Genghis, Ogedei,
Guyuk, Mongke and Kublai die in their real years (D-132). Khwarazm, Russia and Hungary are
off this map, so those campaigns are told from the khan's camp. With a passive test player
20 of 21 chapters play; Xiangyang steps aside when the player has taken it already.

## D-137 The ninth chronicle: England, 1002-1066 — DELEGATED (2026-10-03)
Every moment on the timeline now has a chronicle for its leading state. England's has
fifteen chapters at two years a turn: Emma of Normandy, St Brice's Day, Danegeld, the
lost fleet, Archbishop Ælfheah, Sweyn Forkbeard, the king over the water, Assandun,
Cnut's North Sea empire, the waves, Alfred the Ætheling, Edward the Confessor, Harold's
oath, Stamford Bridge and Hastings. The chronicle follows the crown, not a family: the
English successors are now the real line (Edmund Ironside, Cnut, Harold Harefoot,
Harthacnut, Edward, Harold Godwinson, then Edgar the Ætheling), which also makes free play
more accurate. Where two reigns ended in the same two-year turn, the earlier death is
dated a year early so each king appears at his chapter. Hastings's historical choice
kills Harold and gives Wessex and East Anglia to Normandy; England lives on in the north.

## D-138 A second chronicle for 264 BC: Carthage — DELEGATED (2026-10-03)
Following the owner's "storylines for each civilisation and empire", moments now get
chronicles for their other great states, starting with Carthage: fifteen chapters from
the garrison at Messana through Xanthippus, Drepana, Hamilcar 'the lightning', the
Aegates, the Truceless War, Sardinia, the oath at the altar, Saguntum, the Alps, Cannae,
the Metaurus, Zama and Hannibal as suffete, to "Carthage must be destroyed". Carthage
was a republic, so it has no named ruler and the chapters speak to its council. Two
tuning notes: Messana's historical choice hires 30,000 mercenaries and Xanthippus brings
20,000, because without them Rome's AI took the city of Carthage itself by 250 BC; and the
court no longer gives a eulogy when an unnamed ruler 'dies' (it read "the seal passes to
the ruler of Carthage"). With a passive test player 12-14 of 15 chapters play.

## D-139 A second chronicle for 336 BC: Darius III of Persia — DELEGATED (2026-10-03)
Alexander's war from the other side, in nine chapters: Bagoas's poisoned cup, Memnon's
scorched-earth plan at Zeleia, Memnon's death, leaving the open plain for Issus, the offer
of half the empire, Batis at Gaza, the night before Gaugamela, the Persian Gates, and
Patron's warning before Bessus's betrayal. Persia left no account of these years, so the
historical choices are the Greek writers' version, and the other choices are mostly the
advice Darius's own commanders gave him (Memnon, Amyntas, Patron) - this is the chronicle
in which the player can make Persia listen. Darius is spared old age until the end a chapter
tells (D-130); Bessus until his execution. All nine chapters play with a passive test player.

## D-140 A second chronicle for 1275 BC: the Hittites — DELEGATED (2026-10-03)
Eleven chapters at three years a turn: the planted Shasu spies at Kadesh, Amurru, the
scornful letter to Assyria ("were you and I born of the same mother?"), Hattusili's coup
against his nephew (a chapter ends that reign), the silver treaty, Puduhepa's dowry letter,
the first trade embargo after Nihriya, Yazilikaya, the grain letters ("a matter of life or
death"), the first recorded sea battle off Cyprus, and the abandonment of Hattusa. Hatti's
line is now Muwatalli II, Mursili III, Hattusili III, Tudhaliya IV, Arnuwanda III and
Suppiluliuma II, each dying (or deposed) in his real years. All eleven chapters play with a
passive test player.

## D-141 A second chronicle for AD 1000: the dukes of Normandy — DELEGATED (2026-10-03)
Twelve chapters from Emma's marriage to William the Conqueror's death: the English exiles,
Herleva the tanner's daughter, Robert's pilgrimage, Val-ès-Dunes, Matilda of Flanders,
Mortemer, the fleet at Dives, Hastings from the Norman side, the Harrying of the North,
Domesday and the fall at Mantes. Normandy's dukes now follow the real line (Richard II,
Richard III, Robert, William, Robert Curthose). One tuning note: Mortemer's historical
choice no longer declares war on France - the French were beaten and went home - because
an open-ended war let France's AI swallow the one-province duchy before 1066. All twelve
chapters play with a passive test player.

## D-142 A second chronicle for 1206: the Southern Song — DELEGATED (2026-10-03)
The Mongol century from Hangzhou, in eleven chapters: Han Tuozhou's head, stopping the
tribute to the Jin, Zhao Gong's report on the Mongols, Shi Miyuan's chosen emperor, the
march on the three capitals, Song Ci's forensic handbook, Diaoyu and the gift of fish,
Jia Sidao's secret truce, Xiangyang, the surrender of Lin'an and Yamen. The Song now have
their real line of emperors, from Ningzong to the boy Zhao Bing; Emperor Gong is taken
north and Zhao Bing drowns in chapters, so the player can change both. All eleven chapters
play with a passive test player.

## D-143 A second chronicle for 1560: the Takeda of Kai — DELEGATED (2026-10-03)
Nine chapters: the woodpecker plan at the fourth Kawanakajima, Shingen's rebel heir,
Suruga and the sea, Kenshin's salt, the shogun's call and Mikatagahara (Shingen dies on
the way home in his real year), Katsuyori at Takatenjin, the fence at Nagashino (the old
generals' advice to retreat is the choice history did not take), the new castle at Shinpu,
and Tenmokuzan. Katsuyori is spared old age until the chapter that ends the house. All nine
play with a passive test player.

## D-144 A second chronicle for 350 BC: Zhao — DELEGATED (2026-10-03)
Qin's great rival, in eleven chapters: King Wuling's trousers and horse archers, Zhongshan,
Wuling's abdication (a chapter ends his reign), the jade returned intact, Lian Po's thorns,
'two rats in a hole' at Yuyu, the gift of Shangdang, Zhao Kuo at Changping, Mao Sui's awl in
the bag, Li Mu on the frontier and Li Mu betrayed. Many of these are still Chinese proverbs.
Zhao now has its real line of rulers, from Marquis Cheng to King Youmiu and Jia of Dai. The
first chapter is in 307 BC, so the chronicle opens with some forty years of free play.

## D-145 A second chronicle for AD 1000: Byzantium; how reigns end — DELEGATED (2026-10-03)
Ten chapters: Basil II's annual campaigns, Kleidion and the blinded army, the keys of
Ohrid, Basil's lack of an heir, Romanos III's bath, Maniakes in Sicily (with Harald
Hardrada), the people rising for Zoe, the bull on the altar in 1054, Manzikert and the
Venetian golden bull. 'You' are whoever holds the throne: the chronicle follows thirteen
emperors and empresses in their real years. Two engine details:
- A scenario's heir can say how the reign really ended (`ends`: "abdicates, ill, and
  becomes a monk"), used when the chronicle ends it on time instead of "has died".
- Such ends, and reigns ended by chapters, are recorded as `ruler_fell`, not `ruler_died`,
  so the court's eulogy (added earlier this night) is kept for real deaths.
All ten chapters play with a passive test player.

## D-146 A second chronicle for AD 400: Baekje — DELEGATED (2026-10-03)
Goguryeo's chronicle seen from the south, in eight chapters: the hostage prince in Yamato
and the Wa alliance, Jeonji waiting on the island, ships to the Jin court (and Baekje's
learning passed on to Japan), white falcons for Silla, the prince born on Kakara island
(King Muryeong), the letter to Wei, Dorim's game of baduk, and the court's flight to
Ungjin. Baekje's line now runs from Asin to Muryeong, with Munju and Dongseong murdered as
history says (D-145's `ends`). All eight chapters play with a passive test player.

## D-147 A third chronicle for 1206: Kamakura Japan — DELEGATED (2026-10-03)
Ten chapters: the Wada rising, Sanetomo murdered on the shrine steps (a chapter ends his
reign), Masako's speech and the Jokyu war, the Goseibai Shikimoku, Nichiren's prophecy,
Kublai's letter, the Bun'ei invasion, the beheaded envoys and the stone wall at Hakata,
the Koan invasion and the 'divine wind', and the warriors' unpaid rewards that doomed the
shogunate. After Sanetomo the chronicle follows the real rulers, the Hojo regents, each in
his real years. No chapter declares war on the Mongols: the invasions are told from the
beach, and the player's ideas (a printed law code, steamships) change how they go. All ten
chapters play with a passive test player.

## D-148 A third chronicle for AD 1000: the Western Empire — DELEGATED (2026-10-03)
Eight chapters from Otto III to Henry IV: the Congress of Gniezno and Charlemagne's tomb,
"are you not my Romans?", Henry II's war with Bolesław beside the pagan Liutizi, Conrad
II's coronation between Cnut and Rudolf of Burgundy, the three popes deposed at Sutri,
the boy king's leap from Anno's boat, the letter to "Hildebrand, now not pope but false
monk", and Canossa. The crown passes through Ottonians and Salians in their real years.
All eight chapters play with a passive test player.

## D-149 A fourth chronicle for AD 1000: Kievan Rus — DELEGATED (2026-10-03)
Nine chapters: Vladimir's feasts for the poor, Novgorod refusing tribute, the murder of
Boris and Gleb (played as Sviatopolk), Bolesław at the Golden Gate and the Alta (a chapter
ends Sviatopolk's reign), the Russkaya Pravda, the Pechenegs and St Sophia, the last sea
raid on Constantinople, Anna Yaroslavna's marriage to the King of France, and Yaroslav's
testament. The 1043 raid no longer declares a lasting war (peace came in 1046; an
open-ended war let Byzantium's AI take Kiev). All nine chapters play.

## D-150 A third chronicle for 350 BC: Chu — DELEGATED (2026-10-03)
Eight chapters: the conquest of Yue, Zhang Yi's 'six hundred li', King Huai seized at the
Wu pass (a chapter ends his reign), Qu Yuan's exile and the Li Sao, the fall of Ying and
Qu Yuan's death in the Miluo (the Dragon Boat festival), Lord Chunshen smuggling the prince
out of Qin, Lu and Xunzi, and Xiang Yan against Wang Jian. Chu's line runs from King Xuan to
Fuchu. The 'six li' war is a lost campaign that ends, not an open war, because a permanent
war let Qin's AI swallow a passive Chu decades early. All eight chapters play.

## D-151 A third chronicle for 1275 BC: Middle Assyria — DELEGATED (2026-10-03)
Six chapters across three kings: the claim to be a 'brother' of the great kings, the end of
Mitanni, Nihriya, Marduk carried off from Babylon, the new city of Kar-Tukulti-Ninurta,
and Tukulti-Ninurta murdered by his son (a chapter ends that reign). Assyria now has its
real line: Adad-nirari I, Shalmaneser I, Tukulti-Ninurta I. Nihriya is a battle won, not an
open war, because a lasting war with Hatti brought in Hatti's ally Egypt (which never fought
Assyria). All six chapters play.

## D-152 A third chronicle for 1560: Uesugi Kenshin — DELEGATED (2026-10-03)
Six chapters: the siege of Odawara and the Uesugi name, Kawanakajima from Kenshin's side,
the salt sent to an enemy, the road west against Nobunaga, the Tedori river, and Kenshin's
sudden death and the war between his adopted sons. Kenshin dies at the turn of 1577-78 so
that the last chapter is played as Kagekatsu. All six chapters play.

## D-153 A fifth chronicle for AD 1000: the fall of Córdoba — DELEGATED (2026-10-03)
A short, tragic chronicle in five chapters: al-Mansur's last campaign, Sanchuelo's
fatal winter march, the sack of Madinat al-Zahra, Ibn Hazm's Ring of the Dove, and the
abolition of the caliphate in 1031. The 'ruler' is whoever really held power: al-Mansur's
sons, then six caliphs of the civil war, each removed in his real year in the way history
records (killed in the fighting, executed, murdered in his bath, poisoned, deposed). All
five chapters play.

Follow-up rule (applies to every chronicle): a reign that history ended by murder, coup
or deposition (`ends`) is only ended on schedule while the player's most recent chapter
answer was history's. Once the player has turned history aside, those violent ends no
longer happen by themselves and the ruler lives on with the usual odds; natural deaths
keep their dates either way.

## D-154 A third chronicle for AD 400: Silla — DELEGATED (2026-10-03)
The weakest kingdom of AD 400, which would unite Korea in 668, across 160 years in nine
chapters: Goguryeo's rescue, Bak Je-sang, the alliance with Baekje, the name 'Silla' and the
title of king, the wooden lions of Usan, Ichadon's white blood and the coming of Buddhism,
the surrender of Geumgwan Gaya (ancestors of Kim Yu-sin), the seizure of the Han river,
and the hwarang Sadaham at Daegaya. Eight kings in their real years, Silseong killed in
Nulji's plot as history says. The 'chapters within their moment' test now allows 170 years.
All nine chapters play.

## D-155 A sixth chronicle for AD 1000: the Fatimids of Cairo — DELEGATED (2026-10-03)
Seven chapters: al-Hakim and the regent in the garden, the House of Knowledge and Ibn
al-Haytham's feigned madness, the destruction of the Holy Sepulchre, al-Hakim's
disappearance in the Muqattam hills (a chapter ends his reign; the Druze still await him),
Nasir-i Khusraw's Cairo, the Great Calamity, and Badr al-Jamali. Al-Hakim, al-Zahir and
al-Mustansir in their real years. All seven chapters play.

## D-156 A third chronicle for 264 BC: the Seleucids — DELEGATED (2026-10-03)
Nine chapters from Antiochus II to Antiochus III: Berenice's dowry, the Laodicean war, the
young king against Molon, Raphia's elephants, the eastern anabasis, Panium, Hannibal at
court, Magnesia, and the death at the temple of Bel (a chapter ends that reign). Six kings
in their real years, with Seleucus II's fall from his horse and Seleucus III's murder as
history records. All nine chapters play.

## D-157 A fourth chronicle for 264 BC: the Ptolemies — DELEGATED (2026-10-03)
Five chapters of Alexandria's golden age: the Library's seized books, Ptolemy III's march
to avenge his sister (and the Lock of Berenice), Eratosthenes measuring the Earth, the
Egyptian phalanx at Raphia (and the revolts it led to), and the Memphis decree that became
the Rosetta Stone. Four Ptolemies in their real years. The Syrian expedition takes the coast
without an open-ended war (peace came in 241); the Seleucid AI still fights its scripted
Syrian Wars, so a passive Egypt loses ground, as an active one need not. All five chapters
play.

## D-158 Chronicles are easy to find in the picker — DELEGATED (2026-10-03)
With 29 chronicles, a player could only discover one by clicking each state. Now every
state with a chronicle wears a small gold seal on its shield showing its number of
chapters (and its tooltip says so), and those states come first in the row of shields.

## D-159 A fourth chronicle for 1560: Joseon and the Imjin War — DELEGATED (2026-10-03)
Ten chapters from King Seonjo's accession (1567) to Noryang (1598): the sarim scholars and
Yi Hwang, the split into Easterners and Westerners, Yi I's plea for a hundred thousand
soldiers, the envoys who came back from Japan disagreeing, Yi Sun-sin's turtle ships, the
fall of Busan and the flight from Hanyang, Hansan Island, the Ming relief army, the twelve
ships at Myeongnyang and Yi's death at Noryang. Myeongjong dies in 1566 and Seonjo rules to
1608, as in history. The invasion strips Joseon to two provinces and the Ming return them,
so the benchmark follows the real war; all ten chapters play on two seeds.

## D-160 A fourth chronicle for 1206: Goryeo — DELEGATED (2026-10-03)
Ten chapters from 1211 to 1274, told to the kings while the Choe dictators rule: Huijong's
failed palace plot against Choe Chung-heon (Choe hid behind a paper screen; the king was deposed),
the brotherhood with the Mongols at Gangdong, Pak Seo's defence of Guju, the flight to
Ganghwa Island, the first book printed with cast metal type, the carving of the Tripitaka
Koreana, the fall of the last Choe, the crown prince's meeting with Kublai, the
Sambyeolcho revolt (and the northwest lost to the Mongols, as in history), and the fleet
built for the invasion of Japan. Five kings in their real years (Huijong's reign ends in
the chapter; the others die when they did). All ten chapters play on two seeds.

## D-161 A fifth chronicle for 1206: the fall of the Jurchen Jin — DELEGATED (2026-10-03)
Ten chapters, 1206-1234, from the other side of the Mongol conquest: Han Tuozhou's head
and the peace of 1208, Genghis Khan spitting at the news of Yongji's accession and the
Badger's Mouth, Hushahu the kingmaker, the princess paid to the Khan and the flight to
Kaifeng (Zhongdu and Liaoxi go to the Mongols in the historical choice), Puxian Wannu's
breakaway kingdom (Liaodong and the Jurchen homeland pass to nobody), the war on the Song
for lost revenue, Aizong's peace on two fronts, the Loyal and Filial Army, the gunpowder
bombs of Kaifeng, and Caizhou. Six emperors in their real years; Xuanzong's death (January
1224) is set a year early so that Aizong is on the throne at the 1224 chapter on the
three-year turn grid. All ten chapters play on three seeds; a passive Jin outlasts history,
because the Mongol AI does not press as hard as the real Mongols did.

## D-162 A sixth chronicle for 1206: Western Xia — DELEGATED (2026-10-03)
Seven chapters, 1206-1227, of the kingdom the Mongols erased: Huanzong deposed by his
cousin and his own mother, the Yellow River dyke that flooded Genghis Khan's camp, the
examination champion who became emperor and turned on the Jin, Asha Gambu's "if he has
not enough soldiers", the peace of brothers with the Jin, the frozen river at Lingzhou and
the month's grace at Zhongxing, while the Khan lay dead. Five rulers in their real years:
the reigns end by coup, coup, abdication, death and execution, each in the year it did.
The Hexi corridor and the Ordos pass to the Mongols in the historical choice at Lingzhou.
All seven chapters play on two seeds.

## D-163 A fourth chronicle for 1275 BC: Kassite Babylon — DELEGATED (2026-10-03)
Nine chapters over 110 years, 1266-1155 BC: Kadashman-Turgu's offer to Hattusili, the
vizier who froze the Hittites out, Sin-leqi-unninni's standard Gilgamesh, the foundation
inscription Nabonidus would dig up seven centuries later, Tukulti-Ninurta's sack of
Babylon (the capital goes to Assyria in the historical choice), the nobles' revolt that
put Adad-shuma-usur on the throne (Babylon taken back), Meli-Shipak's daughter sent to
Susa, Shutruk-Nakhunte carrying Hammurabi's stele to Susa, and Marduk taken to Elam.
Thirteen kings in their real years (Brinkman's dates), including the three Assyrian-era
puppets who each fall in turn; where a death fell between turns, the turn grid already
put the right king on the throne, so no date needed shifting. Gilgamesh's editor is
dated only "Kassite period"; the history note says so. All nine chapters play on two seeds.

## D-164 A fifth chronicle for 1275 BC: Mycenae — DELEGATED (2026-10-03)
Six chapters, 1251-1180 BC, built only on what documents and digs show, not on Homer:
the Tawagalawa letter about Piyamaradu (the one time a Greek king was a Hittite 'brother'),
the Lion Gate, Linear B accounts (preserved only because the palaces burned), Millawanda
lost to Tudhaliya IV (and 'Ahhiyawa' rubbed out of the Sausgamuwa treaty), the hidden
cistern and the Isthmus wall as Thebes burns, and the Pylos tablets' 'watchers guarding
the coast' before the palace fell. No Mycenaean king's name survives from his own time,
so the ruler stays unnamed ('the wanax'). Where a historical answer is unknown (how the
king answered Hattusili), the choice taken is the one the later letters imply, and the
history note says that the answer is unknown. All six chapters play on two seeds.

## D-165 A third chronicle for 336 BC: Athens — DELEGATED (2026-10-03)
Nine chapters, 336-322 BC, of the last free years of the democracy: Demosthenes's garland
for Philip's murder, Thebes left to its fate, Alexander's demand for the orators (and
Demades's fee), Lycurgus's stone theatre and the official texts of the tragedians (the
ones Ptolemy III later kept: the two chronicles point at each other), Agis's war, On the
Crown, Harpalus's gold, the Lamian War and Antipater's terms. Athens had no king, so the
"ruler" is the leading statesman: Demosthenes until his conviction in 324, Hyperides until
his execution in 322, Phocion until his hemlock in 318, then Demetrius of Phalerum. The
Lamian War is told with grudges and men, not an open-ended war, so a one-province Athens is
not swallowed by the Macedon AI (the lesson of D-149/D-150). All nine chapters play on two
seeds.

## D-166 A fourth chronicle for 336 BC: Epirus and Pyrrhus — DELEGATED (2026-10-03)
Twelve chapters across 64 years, 336-272 BC: Philip murdered at Alexander of Epirus's
wedding, the call from Tarentum and the oracle of Acheron and Pandosia, the first Greek
treaty with Rome, the death at the river, the infant Pyrrhus at the Illyrian king's knees,
Ipsus, Cineas's "why not rest now?", Heraclea and the Senate "of kings", Asculum (the
Pyrrhic victory), Sicily, Beneventum and the roof tile at Argos. Magna Graecia and western
Sicily are taken and lost in the historical choices, so the benchmark tracks both Italian
adventures. Five kings: Alexander I and Aeacides end in chapters, Alcetas II is murdered
in 307, and Pyrrhus rules from 306 to his death. Pyrrhus's five years of exile (302-297)
are folded into the Ipsus chapter's outcome rather than modelled as a second reign. All
twelve chapters play on two seeds.

## D-167 A fourth chronicle for AD 400: Northern Wei — DELEGATED (2026-10-03)
Thirteen chapters over 92 years, 402-494, of the Xianbei emperors who reunited the north
and then made themselves Chinese: Chaibi, the custom of killing the heir's mother (and
Daowu's murder), Liu Yu's crescent formation, the siege of Hulao, the boy emperor at
Shengle, the White City, the Gobi campaign, Northern Yan's fall, the persecution of
Buddhism, Cui Hao's history in stone, the Yungang Buddhas, the equal-field law and the move
to Luoyang. Luoyang, the Ordos, Chang'an, Longcheng and Youzhou are taken in historical
choices, so the benchmark rises from three provinces to eight as the real Wei's did (the
conquest of Shandong in 469 is not modelled). Seven emperors in their real years; the
short-lived Prince of Nan'an (452) is skipped. All thirteen chapters play on two seeds;
a passive Wei loses a province to a late uprising, as passive players do elsewhere.

## D-168 An eighth chronicle for AD 1000: Denmark — DELEGATED (2026-10-03)
Ten chapters, 1000-1035, from the Danish side of the England chronicle: Svolder, revenge
for St Brice's Day, Sweyn's forty days as King of England, Harald II's fleet for his
brother, Olaf the Saint taking Norway, Cnut's letter to the English, the Holy River and
Ulf's murder, Cnut walking beside the emperor in Rome, Norway bought with English silver,
and "Aelfgifu's time". Norway is a tributary from Svolder to Nesjar and again from 1028 to
1035. Cnut's England is modelled as an ally, not a tributary: in testing, a tributary
England with an old grudge declared war on Denmark in 1030, which is the opposite of
Cnut's reign; as one king's two realms, an alliance holds. Sweyn's death (3 February 1014)
is set to 1013 so that Harald is king at the 1014 chapter; Harald II's death is uncertain
(c. 1018) and set to 1017 so that Cnut is king at the 1019 chapter. All ten chapters play
on three seeds.

## D-169 A ninth chronicle for AD 1000: Piast Poland — DELEGATED (2026-10-03)
Nine chapters, 1000-1054: the Congress of Gniezno, the blinded duke of Bohemia, the Peace
of Bautzen, the Golden Gate of Kiev (the Cherven towns, Volhynia on this map, are taken),
Bolesław's coronation, the double invasion of 1031 that broke Mieszko II (Volhynia goes
back to Rus), Bretislav carrying off St Adalbert's body (Silesia goes to Bohemia; Kraków
becomes the capital), Masław of Masovia, and Silesia regained at Quedlinburg for a
tribute. Mieszko II appears twice in the line of rulers, either side of Bezprym's year,
as he really reigned. Masław's Masovia stays on the Polish map, because one choice can
pass provinces to only one state; the story says it was his. All nine chapters play on
two seeds. This is the Polish side of the Rus chronicle's 1018 (D-149).

## D-170 A tenth chronicle for AD 1000: Hungary — DELEGATED (2026-10-03)
Ten chapters, 1000-1055: the crown from Rome rather than Constantinople, Gyula's
Transylvania, the pilgrims' road to Jerusalem, Ajtony's salt tolls and Bishop Gerard,
Conrad II starved out, Prince Imre's death and the blinding of Vazul, Peter "the
Venetian" driven out, Ménfő, the Vata rising and Gerard's martyrdom, and the Tihany
charter with the oldest written Hungarian sentence. Six reigns in eleven years after
Stephen: Peter Orseolo appears twice in the line (1038-41, 1044-46), either side of Samuel
Aba, and each reign ends in its chapter. Legends (Kund the diver, Vazul's plot) are told
as "it is said". All ten chapters play on two seeds.

## D-171 An eleventh chronicle for AD 1000: the Ghaznavids — DELEGATED (2026-10-03)
Nine chapters, 1000-1040: Jayapala's pyre, Firdawsi paid in silver (told as the later
tradition it is), al-Biruni carried off from Khwarazm, Mathura and Kannauj, Somnath, the
Turkmen let into Khorasan, the library of Rayy (Jibal is taken), al-Biruni refusing an
elephant-load of silver for the Masudic Canon, and Dandanaqan. The map has no India, so
the raids are told in outcomes as wealth and legitimacy; Khorasan stands for the
Ghaznavid heartland. The raids on Hindu temples are told plainly, as the sources and
their modern critics (Thapar) tell them, with the rebuilding and the long memory, neither
celebrated nor softened. Mahmud dies in 1030 and Masud's reign ends at Dandanaqan; his
brother Muhammad's months on the throne in 1030 are left out. All nine chapters play on
two seeds.

## D-172 A twelfth chronicle for AD 1000: Ireland — DELEGATED (2026-10-03)
Eight chapters, 1000-1064: Christmas in Dublin after Glenmama, Máel Sechnaill's
submission, "Imperator Scottorum" in the Book of Armagh, the hostages of the north, the
chess game at Kincora and the failed siege of Dublin, Clontarf (Brian dies in his tent;
the north, Ulster on this map, slips away), Donnchad's law of 1040, and Donnchad's last
road to Rome. The Cogad and Njal's saga are a century later and partisan, so their
stories (the chess game, Brodir) are told as the saga's, beside what the annals say.
Brian is spared old age until Clontarf; Donnchad until his fall in 1063-64. All eight
chapters play on three seeds.

## D-173 A thirteenth chronicle for AD 1000: Venice — DELEGATED (2026-10-03)
Seven chapters, 1000-1084: Pietro II Orseolo's Ascension Day voyage down the Dalmatian
coast, the Byzantine princess with the golden fork, the fall of the Orseolo, the law
against co-doges, the new St Mark's on the model of the Holy Apostles, Alexios I's Golden
Bull, and the defeat off Corfu. Seven doges in their real years; the elected doges are
the "rulers" (an "Otto Orseolo ... takes the throne" message is a small stretch for an
elected office). Alliances with Byzantium were left out of the deeds: a two-province
Venice allied to Byzantium would be dragged into Basil II's Bulgarian war (the lesson of
D-149/D-150). All seven chapters play on two seeds.

## D-174 A fifth chronicle for 1560: the late Ming — DELEGATED (2026-10-03)
Ten chapters, 1561-1619: Qi Jiguang's Yiwu army against the wokou, Hai Rui's memorial
and his coffin, Moon Harbour and the silver trade, the Altan Khan peace, Zhang Juzheng's
land survey and his posthumous disgrace, Wanli's thirty-year "strike", the Korean war,
Matteo Ricci's clocks, and Sarhu (Liaodong is lost in the historical choice). Three
emperors in their real years: Jiajing (died January 1567, set to 1566, the Chinese year),
Longqing and Wanli; Taichang's month on the throne follows. Ray Huang's "1587" is the
guiding modern source for Wanli's reign. All ten chapters play on two seeds.

## D-175 A fifth chronicle for 264 BC: Syracuse — DELEGATED (2026-10-03)
Nine chapters, 263-212 BC: Hiero changing sides to Rome, his tithe law (which Rome kept),
Archimedes and the crown (told as Vitruvius's story), grain for Carthage in the Mercenary
War (Polybius's balance-of-power remark), the Syracusia sent to Ptolemy, the golden
Victory sent to Rome after Cannae, Hieronymus going over to Carthage, Archimedes' claws,
and the fall of the city. Hiero dies at ninety-one in 215, Hieronymus is killed at
Leontini in 214, and the general Epicydes leads until the fall; the "burning mirrors" are
left out as a later story. Its chapters point at the Carthage, Rome and Ptolemy
chronicles. All nine chapters play on two seeds.

## D-176 A sixth chronicle for 264 BC: the Antigonids — DELEGATED (2026-10-03)
Eight chapters over a century, 262-168 BC: Athens garrisoned after the Chremonidean War,
the flagship dedicated at Delos after Cos, Aratus's night climb up Acrocorinth (Corinth
goes to the Achaeans), Doson's price for saving Aratus and Sellasia (Corinth comes back),
Philip V's treaty with Hannibal caught by the Roman fleet, Cynoscephalae (Thessaly and
Corinth are lost; Greece "freed"), the forged letter and Demetrius's death, and Pydna.
Five kings in their real years. The chronicle complements the Alexander chronicle (D-134)
for the same kingdom a century later. All eight chapters play on two seeds.

## D-177 A fourth chronicle for 350 BC: Qi — DELEGATED (2026-10-03)
Eight chapters, 342-221 BC: Sun Bin's cooking fires and "Pang Juan dies under this tree",
the Jixia Academy, Mencius and the occupation of Yan, the annexation of Song, Yue Yi's
seventy cities (Linzi, Pingyuan and Song go to Yan; King Min is killed at Ju), Tian Dan's
fire oxen (Linzi and Pingyuan come back), the Queen Dowager's jade rings and the refusal
of grain to Zhao before Changping, and the surrender to Qin. The benchmark follows Qi's
real fortunes: 4, 5, 2, 4, then 1. Five kings in their real years; King Jian is spared
until -220, the turn on which the 221 BC chapter opens on the two-year grid. All eight
chapters play on two seeds.

## D-178 A fifth chronicle for 350 BC: Yan — DELEGATED (2026-10-03)
Ten chapters, 316-222 BC: King Kuai giving his throne to Zizhi, the Qi invasion, Guo
Wei's "start with me" and the Golden Terrace, Qin Kai's thousand li beyond the wall
(the Xilamulun steppe and Liaodong are taken), Yue Yi's seventy cities (Linzi and
Pingyuan taken), the recall of Yue Yi and Tian Dan's revenge (given back, with peace),
the attack on Zhao at Hao, Jing Ke's dagger in the map, Prince Dan's head, and the end in
Liaodong. Ten rulers in their real years, Zizhi included. Three lessons from testing: Qi's
AI invasion of 314 kept Yan's provinces, so the Golden Terrace chapter restores them with
peace, as the Yan rising did; Qi's "occupy Yan in turmoil" script re-fires while Yan's
unrest stays above 2000, so the restoration also calms the country; and `grudges` names
who resents the player, not whom the player resents (a misdirected grudge made Qi hate
Yan; removed). All ten chapters play on three seeds, two of them level with history
throughout.

## D-179 A sixth chronicle for 1275 BC: Ugarit — DELEGATED (2026-10-03)
Six chapters, c. 1275-1185 BC, built from Ugarit's own archives: chariots for Kadesh,
the thirty-sign alphabet (in the a-b-g-d order still used), Ammistamru II's divorce case
judged by the Hittite court, fifty minas of gold to be excused from the war on Assyria,
the Great King's famine letter ("a matter of life or death"), and Ammurapi's last letter
to Cyprus as the enemy's ships came. Ugarit had no rulers in the scenario; it now has
five kings, Niqmepa to Ammurapi, in Singer's approximate dates. The popular story of
letters "still in the kiln" is left out, as excavators now doubt it. All six chapters
play on two seeds.

Also fixed: the Western Xia flood chapter (D-162) gave the Jin a grudge against Xia,
where the story meant the reverse; `grudges` names who resents the player (see D-178),
so it was removed.

## D-180 A seventh chronicle for 1275 BC: Middle Elam — DELEGATED (2026-10-03)
Seven chapters across 165 years, c. 1272-1110 BC, the Elamite side of the Babylon
chronicle (D-163): the ziggurat city of Chogha Zanbil, the two-ton bronze statue of Queen
Napir-Asu, Kidin-Hutran's raids on Nippur, Shutruk-Nakhunte's trophies (Babylon is taken),
Marduk carried to Susa, Shilhak-Inshushinak's bricks naming earlier kings, and
Nebuchadnezzar's summer march to the Ulai (Babylon is given back). Eight kings in
approximate reign dates; the last vanishes after the Ulai, as he does from history. The
chronicle runs to the edge of the 170-year limit for a chronicle's span. All seven
chapters play on two seeds.

## D-181 A sixth chronicle for 350 BC: Wei — DELEGATED (2026-10-03)
Eight chapters, 344-225 BC, of the strongest state of the age in decline: King Hui's crown
at Fengze, Maling from the losing side, Shang Yang's feast and the loss of Hexi and Shang,
Mencius's "why speak of profit?", Anyi given up, Lord Xinling's stolen tiger tally, the
prince too popular to keep, and Daliang flooded. Wei's line of kings follows the Bamboo
Annals (Hui, Xiang, Zhao, Anxi, Jingmin, Jia), replacing the scenario's "King Ai", which
came from the Shiji's known error. The benchmark falls 5, 3, 2, 1 as Wei's lands passed to
Qin. All eight chapters play on two seeds.

## D-182 A seventh chronicle for 350 BC: Han — DELEGATED (2026-10-03)
Eight chapters, 350-230 BC, of the smallest of the seven: Shen Buhai's "technique", Wei's
invasion and Qi's late rescue at Maling (peace with Wei), Su Qin's "head of a chicken",
Yiyang lost to Qin (and King Wu's cauldron), Shangdang handed to Zhao (the spark of
Changping), Zheng Guo's canal plot that fed Qin instead, Han Fei sent to his death, and
the first fall. Testing showed the Wei AI's attack of 342 taking Xinzheng outright, so the
Maling chapter ends that war as history did. The chronicles of Qin, Zhao, Chu, Qi, Yan,
Wei and Han now cover all seven warring states. All eight chapters play on three seeds,
level with history throughout.

## D-183 A sixth chronicle for 1560: the Mori — DELEGATED (2026-10-03)
Eight chapters, 1560-1600: Motonari's letter to his three sons (the "three arrows" told
as the later embellishment it is), the Iwami silver mine, the starving of Gassan-Toda
(the Amago are conquered), Motonari's deathbed "do not seek the realm", the fire pots at
Kizugawaguchi, Takamatsu castle in its lake as Nobunaga dies, thirty thousand men for
Korea, and Terumoto staying in Osaka while Sekigahara was lost (Aki and Izumo are given
up). Motonari dies in 1571 and Terumoto reigns on. The Mori chronicle meets the Oda and
Joseon chronicles at Takamatsu and in Korea. All eight chapters play on two seeds.

## D-184 A seventh chronicle for 1560: the Shimazu — DELEGATED (2026-10-03)
Ten chapters, 1560-1609: the matchlocks of Tanegashima, Takahisa's retirement in favour of
his four sons, Kizaki's three hundred against three thousand, Mimigawa against the
Christian lord Otomo (Hyuga taken), Okitanawate (Hizen), Hetsugigawa and Funai (Bungo),
the submission to Hideyoshi (all three given up), Sacheon, the retreat through the
Tokugawa army at Sekigahara, and the invasion of Ryukyu (taken). The benchmark follows
the Shimazu's rise and fall exactly: 1, 2, 3, 4, 1, 2. Four lords in their real years:
Takahisa retires in 1566, Yoshihisa submits in 1587, Yoshihiro hands over in 1602. All ten
chapters play on two seeds, level with history throughout.

## D-185 An eighth chronicle for 1560: the Hojo — DELEGATED (2026-10-03)
Five chapters, 1561-1590, of the masters of the Kanto: Kenshin's hundred thousand at the
gates of Odawara, Hojo Saburo sent to Kenshin as his adopted son, Ujiyasu's dying advice
to make peace with the Takeda, the Otate disturbance in which Saburo died, and the
"Odawara council" that debated until Hideyoshi's siege ended the house (Musashi is given
up). Ujiyasu dies in 1571; Ujimasa's rule ends at Odawara. Its chapters meet the Uesugi
and Takeda chronicles at the same events from the other side. All five chapters play on
two seeds.

## D-186 A ninth chronicle for 1560: the Date — DELEGATED (2026-10-03)
Seven chapters, 1564-1613: Harumune stepping aside, Terumune handing the house to his
one-eyed son, the shooting on the Abukuma that killed Terumune with his kidnappers, the
white robe at Odawara, the pierced eye of the wagtail seal, the founding of Sendai, and
Hasekura's embassy across the Pacific to Spain and the Pope. The white robe, the golden
cross and the wagtail are later chronicle stories and are told as such. Three Date lords,
each reign ending in its chapter. All seven chapters play on two seeds.

## D-187 Chronicles are now written by six helper agents in parallel — DELEGATED (2026-10-03)
At the owner's request, six helper agents (Sonnet) now draft chronicles at once, each for
its own states, following a written guide (format, turn-grid timing, grudge direction, no
open-ended wars, accuracy rules) and testing in a private copy of the code. They never touch
the repository; the manager reviews each chronicle, spot-checks facts, merges the chapter
file and the ruler-line patch, runs the full checks and ships. The first batch, for 1560:
the Ashikaga shoguns (5 chapters, 1560-1573; based on the manager's draft, corrected by the
agent: Kenshin became Kanto deputy in 1561, not 1559; no alliance with Nobunaga in the
deeds, only peace with the Miyoshi).

## D-188 A chronicle for 1560: Otomo Sorin — DELEGATED (2026-10-03)
Eight chapters, 1560-1593: the Funai hospital and Portuguese trade, risings behind the
Mori, Ichijo Kanesada, Sorin's baptism and Mimigawa (matching the Shimazu chronicle), the
Tensho embassy to Rome, the appeal to Hideyoshi, Sorin's death, and Yoshimune's disgrace
at Hosan in Korea. Sorin rules until 1587 (his formal retirement in 1562 is ignored, since
he remained the house's will); Yoshimune's fall in 1593 ends the line, as Bungo, the last
province, cannot be given away. Yoshimune's age corrected to 29 (born 1558). Both seeds
clean.

## D-189 A chronicle for 1560: the Chosokabe of Tosa — DELEGATED (2026-10-03)
Ten chapters, 1560-1614: Motochika's first battle (the "Princess boy", told as a later
story), the Shimanto, Nobunaga's order and Honno-ji, the conquest of Shikoku (Iyo-and-
Sanuki is taken in 1584 and goes to the Mori's Kobayakawa in 1585), Hetsugigawa and the
choice of Morichika as heir, the San Felipe at Urado, the hundred-article code, Sekigahara
and Osaka. Kunichika dies in 1560, Motochika in 1599, Morichika falls at Osaka. The loss of
Tosa in 1600 is told but not enacted (last province). Both seeds clean.

## D-190 to D-207 Eighteen chronicles from the helper agents — DELEGATED (2026-10-03)
Written in parallel by the six helper agents (D-187), each tested on two seeds in a private
copy, then reviewed, spot-checked and merged by the manager. Every one plays all its
chapters with the right ruler on the throne; dates the agents could not pin down are marked
"approximate" in the file headers, and legends are labelled as such.
- D-190 France (8 chapters, 1000-1096): Bertha and the excommunication, the Orléans
  burnings, Burgundy, Anne of Kiev, Varaville, Baldwin's regency, Bertrade, Clermont. The
  benchmark reads "ahead of history" throughout, honestly: the map gives France six
  provinces, the real Capetians governed one or two.
- D-191 Norway (9, 1000-1066): Svolder to Stamford Bridge, consistent with the Denmark
  chronicle; Viken is lost and retaken as in history, with peace deeds where AI rivals
  would otherwise keep it.
- D-192 Scotland (9, 1004-1092): Monzievaird to Alnwick; three chapters say plainly that
  Shakespeare's Macbeth is fiction.
- D-193 The Papacy (10, 1000-1084): Gniezno to Gregory VII's exile; eighteen popes as the
  ruler line; Benedict IX and Gregory VI end in their chapters.
- D-194 Bulgaria (7, 1000-1018): Samuel's war with Basil II to Kleidion and the surrender.
  (An agent queried the Byzantium chronicle's "dies two days later": Skylitzes counts from
  the blinded army's arrival, so the existing text stands.)
- D-195 León (10, 1017-1086): the Fuero to Sagrajas. The Córdoba AI otherwise conquered
  León, which never happened, so the historical choices carry peace with Córdoba and take
  back the provinces the real kings held.
- D-196 Georgia (9, 1000-1122): Bagrat III to Didgori and Tbilisi.
- D-197 Armenia (6, 1000-1044): the Ani cathedral to the Byzantine annexation; the Seljuk
  sack and Manzikert are the epilogue. Gagik I's death set to 1019 (1017-1020 in sources).
- D-198 The Buyids (9, 1000-1055): the House of Learning to Tughril in Baghdad; Ibn Sina at
  Hamadan; Jibal goes to the Ghaznavids in 1029 with peace, matching D-171.
- D-199 Rhodes (8, 226-164 BC): the Colossus to Delos the free port; the ruler is the
  republic's magistracy.
- D-200 Pergamon (10, 264-134 BC): Philetaerus to the bequest to Rome. The Seleucid AI
  conquered Pergamon early in testing; peace deeds at the Galatian chapters prevent it.
- D-201 Sparta (9, 264-188 BC): Areus to Philopoemen's demolition of the walls; the line
  follows whichever king each chapter is about; four end years moved by a year or two to
  fit the turn grid (noted in the YAML).
- D-202 Early Rome (10, 336-272 BC, file chapters_rome_early.yaml): the Latin settlement to
  Tarentum's surrender; the "ruler" is the leading magistrate of each crisis.
- D-203 Eastern Jin (9, 400-420): Sun En to Liu Yu's Song; the court in Emperor An's name,
  then Liu Yu as ruler.
- D-204 Lanka (8, 321-153 BC): Pandukabhaya to Dutugemunu, all labelled Mahavamsa
  tradition with disputed chronology.
- D-205 Imagawa (6, 1560-1575): Okehazama to Ujizane at kemari; Kenshin's "salt to the
  enemy" marked as a later legend.
- D-206 Asakura (6, 1560-1573): Yoshiaki's host to Ichijodani; the lacquered skulls in the
  epilogue.
- D-207 Miyoshi (8, 1560-1573): Nagayoshi to Wakae; the Eiroku incident conquers the
  Ashikaga (matching D-187), and the cause of the Todai-ji fire is left open.

## D-208 Era music from the owner (2026-10-03)
The owner supplied four music tracks (Roman, Asian, medieval, Egyptian/Arabic), about
twenty-five minutes each, committed to `main` as MP3s. They now live in `client/music/` as
`roman.mp3`, `asian.mp3`, `medieval.mp3` and `near_east.mp3`, and loop during play; the
title screen keeps the old synthesised theme. Which track plays is content, not code: a
scenario names its `music`, and a civilisation can override it (Carthage, the Ptolemies and
Seleucids, Persia, Kush, Numidia and the Islamic states of AD 1000 play `near_east`;
Mycenae and Troy at Kadesh play `roman`). Each game stores its track in the state, so a
loaded game plays the right one. A test checks every named track has a file. DELEGATED:
the mapping above. Rights: the owner's tracks, source not yet confirmed; recorded in
`client/assets/LICENSES.md` and must be cleared before any public release. Also removed a
stray `year_1000.yaml.orig` patch leftover that an earlier commit had picked up.

## D-209 to D-226 Eighteen more chronicles from the helper agents — DELEGATED (2026-10-03)
Second round of the six helpers (D-187), for states that had no chronicle. Each was tested
on seeds 1 and 2 in a private copy; after merging, the manager replayed every one with all
changes combined (seed 1, and seed 3 for seven of them) and all chapters played. Doubtful
dates are marked "approximate" in file headers or scenario comments; hostile or late
sources and legends are labelled in the text. A source check before release is advisable,
as the helpers wrote from memory without the network.
- D-209 Sweden (9, 1000-1160): Svolder to Eric IX; saga scenes labelled; two death years
  moved a little onto the two-year turn grid, with comments.
- D-210 Bohemia (8, 1002-1158): Boleslaus III's blinding to Vladislaus II's crown; Silesia
  taken at Gniezno 1038 and given back at Quedlinburg 1054.
- D-211 Navarre (8, 1010-1134): Sancho the Great to García Ramírez's restoration; Navarre
  gets its kings (it had no leader); Zaragoza goes to Barcelona in 1134 as a stand-in for
  Aragon, which is not a state on this map.
- D-212 Barcelona (8, 1010-1148): Córdoba to Tortosa. The 1010 historical choice makes peace
  and alliance with Córdoba (the paid expedition), because otherwise Córdoba's AI took
  Barcelona by 1020 in every test.
- D-213 Zirids (7, 1016-1148): al-Mu'izz to Mahdia's fall to Roger II; the 1016 riots told
  soberly; no benchmark after 1148, when the real Zirids held nothing on this map.
- D-214 Emirate of Sicily (7, 1019-1090): the Kalbids to Noto; later rulers named by office
  where the sources do not name them. The weakest-sourced of the round: check against
  Metcalfe and Amari.
- D-215 Numidia (9, 206-105 BC): Masinissa to Bocchus's betrayal of Jugurtha; the two
  Numidian provinces change hands with Syphax and Bocchus.
- D-216 Pontus (8, 220-108 BC): Sinope to the Bosporus; regnal dates approximate.
- D-217 Epirus (8, 240-167 BC, file chapters_epirus_punic.yaml): the last Aeacids, then the
  league as "the Epirote Assembly", to the Roman sack of seventy towns in 167.
- D-218 Athens (8, 264-146 BC, file chapters_athens_hellenistic.yaml): the Chremonidean
  surrender to staying out of the Achaean War; "the Assembly" rules where no leading man
  can be named with confidence.
- D-219 Achaea (9, 251-146 BC): Aratus to Corinth's destruction. The Acrocorinth chapter
  grants a large army (40,000 men) because Macedon's AI otherwise retook Corinth on about one
  seed in six; generous, but only on the historical path. Peace with Aetolia is given where
  history ended that war.
- D-220 Aetolia (9, 238-189 BC): to the treaty of 189; the leading general of each year
  rules, the first unnamed.
- D-221 Zhongshan (6, 322-298 BC): the kingship to Zhao's conquest; peace with Zhao in 306
  and 304 matches the real truce.
- D-222 Song (6, 330-286 BC, file chapters_songstate.yaml): King Yan, from the hostile
  Shiji portrait, labelled as such.
- D-223 Lu (5, 334-260 BC): the last chapter opens in 260 rather than 256 because Chu's
  existing script takes Qufu in 258; the text gives the true date. Left so rather than
  change how Chu plays in every game.
- D-224 Saito (6, 1560-1573): Yoshitatsu to Tatsuoki's death at Ichijodani; consistent with
  the Oda chronicle.
- D-225 Amago (7, 1560-1578): Gassan-Toda to Kozuki; Yamanaka Yukimori's vow marked as a
  later story; consistent with the Mori chronicle.
- D-226 Ryukyu (7, 1560-1728): Sho Gen to Sai On, with the full line of kings; the 1609
  invasion consistent with the Shimazu chronicle.

## D-227 to D-245 Nineteen more chronicles from the helper agents — DELEGATED (2026-10-03)
Third round of the six helpers (D-187), again for states with no chronicle. Four helpers
were cut off by the usage limit and resumed after it reset. Each chronicle was tested on
seeds 1 and 2 in a private copy; after merging, the manager replayed all nineteen together
on seed 3, and every chapter played. The helpers had no network, so facts are from memory,
hedged in the text and marked approximate where unsure: a source check before release is
advisable. Thin Bronze Age and early sources mean some chronicles are short rather than
invented.
- D-227 Kara Khitai (5, 1206-1218): Kuchlug's arrival to his death at Jebe's hands.
- D-228 Uyghurs of Qocho (5, 1206-1219, file chapters_uyghurs_qocho.yaml): Barchuq kills the
  Khitan resident and becomes Genghis's "fifth son". Barchuq is given leader_until 1225 (he
  lived into the 1230s): on seed 3 he otherwise died of age in 1212.
- D-229 Dali (4, 1206-1256): the Gao chancellors to Duan Xingzhi as maharaja under the
  Mongols; Dali gets its Duan kings. Peace with the Mongols after the conquest.
- D-230 Wa (8, 400-552): the Gwanggaeto stele, the five kings of the Song shu, Iwai, the
  Baekje Buddha; the scenario leader "Nintoku (legendary)" becomes "the king of Wa (name
  unknown)", and identifications with Nihon shoki emperors are called disputed.
- D-231 Gaya (8, 400-562): from Goguryeo's 400 attack to Daegaya's fall; reigns from the late
  Samguk yusa, marked traditional.
- D-232 Later Yan and Northern Yan (8, 400-436): Murong Xi and Lady Fu to the burning of
  Longcheng; Xi's death put at 409 (really 407) so his last chapter sees him, with a comment.
- D-233 Later Qin (7, 400-416): Kumarajiva to Liu Yu; Gao seng zhuan stories marked as such.
  Also corrects the Eastern Jin chronicle's "Wang Zhenwu" to Wang Zhen'e.
- D-234 Southern Yan (5, 400-410): Murong De to the fall of Guanggu.
- D-235 Rouran (7, 402-552): Shelun's title to the Türk revolt; peace with Northern Wei where
  history made it, so Wei's scripts do not swallow the khaganate.
- D-236 Amurru (5, 1275-1179 BC): Benteshina deposed and restored, Shaushgamuwa's embargo
  clause (consistent with the Hittite chronicle).
- D-237 Alashiya (5, 1275-1170 BC): copper, the Hittite claims, the letters about enemy ships;
  kings whose names are lost are called so.
- D-238 Wilusa (6, 1275-1182 BC): the Alaksandu treaty, Walmu, Troy VIIa; the Homeric link
  is tradition only. Peace with Mycenae at the settlement stops its script swallowing Wilusa.
- D-239 Hanigalbat (2, 1275-1263 BC): only Assyrian sources survive, so only two chapters;
  the 14,400 blinded is Shalmaneser's own boast.
- D-240 Zhou (6, 343-249 BC): the last kings to Lu Buwei; follows the Shiji's Duke of West Zhou
  for 256, where the Qin chronicle names the king (noted in the header).
- D-241 Wey (6, 346-209 BC, the small state, not Wei): outlasts every other state until the
  Second Emperor. The historical choice of one chapter allies it with Zhao and Song and adds
  soldiers, because the one-province state was otherwise swallowed; generous, but six of six
  seeds then played cleanly.
- D-242 Yue (6, 336-202 BC): Wujiang's defeat to Wuzhu, King of Minyue.
- D-243 Massalia (5, 218-118 BC): Rome's ally from Hannibal's march to the Ligurian wars.
- D-244 Kush (6, 264-204 BC): Arkamani and the priests (Diodorus, a Greek-told story) and the
  Ptolemaic frontier; king order after Arkamani I is a scholarly reconstruction.
- D-245 Cisalpine Gauls (7, 232-190 BC): Telamon to the Boii's defeat. Rome's own script takes
  the Boii land early, so the benchmark reads "behind history" from 224 to 200; left so rather
  than change Rome's play. The Telamon chapter's change of leaders is a game device.

## D-246 to D-263 Eighteen more chronicles from the helper agents — DELEGATED (2026-10-03)
Fourth round of the six helpers (D-187). With it, every state in every real-map scenario has a
chronicle except the Seleucid-era "satraps" of the Maurya scenario. Each was tested on seeds
1 and 2 by its helper and replayed on seed 3 by the manager after merging; every chapter
played. The helpers had no network: facts are from memory, hedged in the text and marked
approximate where unsure, so a source check before release is advisable. Thin sources mean
several are deliberately short (Chera, Nanda, Ba: three chapters each).
- D-246 Kalinga (4, 318-261 BC): to Ashoka's war, with Rock Edict XIII's own figures.
- D-247 Chola (5, 291-159 BC) and D-248 Pandya (5, 300-168 BC): Ashoka's edicts naming them
  as neighbours, Megasthenes' Pandyan queen (a Greek story), Elara (consistent with the Lanka
  chronicle), and Kharavela's inscription on its disputed early date. Sangam poetry is used
  only as later, undated tradition. The edict chapters need the Mauryas alive, so a game where
  the AI destroys them skips one chapter, with a note.
- D-249 Nanda (3, 321-315 BC): the fall to Chandragupta from late, contradictory sources;
  Dhana Nanda kept alive to the last chapter with leader_until.
- D-250 Chera (3, 321-255 BC): pepper, the "Mauryan chariots" poems, Ashoka's Keralaputras.
- D-251 Scythians (3, 336-325 BC): the Danube campaign, the Jaxartes Saka (named as a
  different people) and Zopyrion at Olbia; the Thatis battle left out (a Bosporan war).
- D-252 Thebes (6, 336-316 BC): the revolt and destruction of 335, four chained chapters in
  one year, then Cassander's refounding.
- D-253 Odrysians (6, 336-313 BC): Seuthes III, Zopyrion, Lysimachus and Seuthopolis.
- D-254 Illyrians (5, 335-307 BC): Pelium, Glaucias and the infant Pyrrhus (consistent with
  the Epirus chronicle); Cleitus's unrecorded end handled by ruler_falls.
- D-255 Syracuse under Agathocles (9, 336-289 BC, file chapters_syracuse_agathocles.yaml):
  the first historical choice makes peace with Carthage, because Carthage's script otherwise
  took Syracuse by 325. The poisoning is told as Diodorus's story.
- D-256 Carthage in Agathocles' war (7, 317-277 BC, chapters_carthage_agathocles.yaml): the 310
  sacrifice reported by Diodorus alone, told soberly with that caveat.
- D-257 Sparta from Agis III to Pyrrhus (8, 336-272 BC, chapters_sparta_agis.yaml): the player
  follows the Eurypontid kings, then Areus I (an Agiad) from 275, a simplification of Sparta's
  double kingship.
- D-258 Shu (4, 337-316 BC) and D-259 Ba (3, 320-316 BC): to Qin's conquest; Huayang guo zhi
  stories labelled as late tradition.
- D-260 Yiqu (5, 326-272 BC): to the killing at Ganquan; a 306 chapter adds soldiers so Qin's
  script does not take Yiqu before history did.
- D-261 Donghu (5, 306-208 BC): Qin Kai to Modu's famous demands (Shiji 110, labelled). The
  Li Mu chapter's pact with Zhao and army boost is the game's invention, as the text says.
- D-262 Gojoseon (6, 322-194 BC): to Wiman's coup; Dangun called a 13th-century tradition.
  The historical choice against Yan adds an alliance with Qi and soldiers to stop Yan's
  script swallowing Joseon; the manager added a line to the outcome saying no source records
  the Qi pact.
- D-263 Onggut (6, 1206-1296): Alaqush to Prince George; Alaqai Beki's regency and Rabban
  Sauma; rulers between Alaqai and George are unnamed placeholders.

## D-264 The Macedonian Satraps — the last chronicle — DELEGATED (2026-10-03)
Eight chapters, 321-301 BC (file chapters_satraps.yaml): Triparadisus, Eudemus's murder of
Porus and his march west with 120 elephants, his execution after Gabiene, then Seleucus
(the story says plainly that it now speaks for him in Babylon): crossing the Indus, the
treaty and 500 elephants (terms debated, marked so), Megasthenes, Ipsus. Eudemus gets
leader_until -314. Tested on seeds 1-4; the Maurya chronicle still plays all 17 chapters
alongside it. This chronicle loses Gandhara when Eudemus marches west (Taxila lies east of
the Indus), where the Maurya chronicle has it pass at the treaty; the province straddles
the river, so both readings are defensible, and they are left as they are. With this,
every state in the nine real-map scenarios has a chronicle.

## D-265 History's choice is no longer easy to spot (2026-10-04)
The owner play-tested the chronicles: history's choice was always listed first (1,097 of 1,100
chapters), and usually obvious anyway. A count found why: 892 chapters offered only two
choices; in 302 only history's choice showed any effect on the world in its hint; in 241 it
showed far more effects than the alternatives; in 180 its label was much the longest.
Two fixes:
- Code (this entry): the client lists a chapter's ordinary choices in a shuffled order, fixed
  for a given game and chapter (a hash of the game's seed and the chapter id), so it does not
  jump about between frames but differs between chapters and games; choices needing an idea
  ahead of its time stay last. It is display only: actions still name the choice by its index
  in the file, so saves and replays are untouched. A test checks history is shown first in
  only about a third to a half of chapters.
- Content (D-266): every chapter gets at least three real, tempting options with comparable
  visible costs and benefits, rewritten by the helper agents under a checker script
  (balance.py) and a guard that history's choice keeps its tested mechanics.

## D-266 Every chapter's choices rewritten so history is not obvious — DELEGATED (2026-10-04)
Following D-265, the six helper agents rewrote the choices of all 1,100 chapters in twelve
batches, under a checker (balance.py) and a guard that history's choice keeps its tested
mechanics and every chapter keeps its facts (both run by the manager on every merged file,
against the last commit). Rules: at least three real options, each a course argued at the
time or open to a ruler then (never silly or doomed); labels of similar length and voice,
with famous phrases and hindsight words removed; comparable visible costs and benefits;
stories and titles that foreshadowed the answer reworded; new choices only appended, so
saved games and `after_choice` references keep their meaning. Rules were added as the work
revealed new tells (alternatives must cost something when history was a disaster; history
must not show far fewer effects; history must not usually have the best numbers).
Result, before -> after: chapters with only two choices 892 -> 0; chapters where only history
showed a deed 302 -> 0; history's label much the longest 180 -> about 155 (now rarely by
much); history with the best net numbers 59% -> 32% (a third is fair). The last step was a
seeded nudge: in about a third of the chapters where history's numbers were still strictly
best, the closest alternative's legitimacy was raised just past it. Three tests now hold
these lines (three choices, never only history with deeds, best numbers under 40%).
Caveats: many new options are plausible courses rather than recorded proposals (their outcome
text does not claim they happened); a few chapter titles were changed; where history's own
numbers are extreme (a reign ending in disaster), a careful player may still guess. A
spot-play of sample chronicles on seed 2 matched the pre-rewrite results exactly.

## D-267 Combat v2: formations, three-phase battles, rules of engagement — DELEGATED (2026-10-04)
The owner asked for combat that is "more strategic and tactical". A battle was one roll
(numbers x soldiers x ground x general x veterancy x the D-108 plan x luck). Everything that
existed stays (plans, veterans, morale, sieges, supply, navies, generals, tales); this adds
real decisions before and during a battle.
- **Formations** (content, `core/formations.yaml`): balanced line, strong centre, strong left,
  strong right, deep reserve, wide line. Each beats some and loses to others, in words the
  player can read: a strong wing turns the flank of a balanced line or a strong centre; the
  opposite strong wings meet as equals and the better general wins (Leuctra); a deep reserve
  beats a strong centre or a wing (it plugs the breach) but is wasted against a steady line;
  a wide line overlaps a balanced line or a reserve but needs 1.2 times the enemy's men (or it
  is thin: -20% and no edge) and a strong centre punches through it. The winning matchup is
  worth +20% power in the clash. A ruler may order one; left alone a general draws up against
  what he expects, and a great general (3 stars) reads the enemy's real formation, exactly as
  with plans. New order `ArmyFormation`.
- **Three phases**: (1) the skirmish, where missile troops trade shots - few die, morale is
  shaken, and the plan matters (skirmishing and ambush help, a headlong charge hurts); (2) the
  clash, the old power contest with plan and formation edges, where a deep reserve commits;
  morale falls with each side's share of the dead; (3) the pursuit, where the winner's horse
  run down the beaten (this replaces part of the old "crush"; an envelopment still adds). A
  side whose morale falls below the break threshold (3,000) runs, in the skirmish or the clash
  (a short battle), and a side that holds together but loses gets away in good order (half
  the pursuit). Each battle report carries the three phases (text, losses, morale).
  Casualties are tuned to the old ballpark (winner about 8% lost, loser about 19%).
- **Rules of engagement** (`ArmyEngage`): fight (as before); cautious (withdraws, with a 3%
  rear-guard loss and its morale intact, from a battle where it would hold under 35% of the two
  sides' strength; defenders behind walls and armies with nowhere to go never withdraw); last
  man (never breaks, hits 10% harder, loses 50% more if beaten). Rival courts set cautious
  (or fight, if aggressive) themselves and will not march a cautious army on a stronger host.
- **Strategic touches**: an army that stood a whole turn without marching is dug in (+15%
  defence, lost when it moves or is beaten); a forced march (`MarchArmy.forced`) goes one
  province further at 8% morale and 3% of the men a turn; rival armies the player cannot see
  closely (not on or beside his land, nor beside his armies) are shown in the view rounded to
  5,000 men (the engine keeps exact numbers).
- Everything is integers from the saved random stream; every tuning number is in the core
  rules (`ArmyRules`); new fields have defaults, so old saves load. Tests: matchups, phases,
  early breaks, cautious, last man, camps, forced march, view fields.
## D-268 Screens that do not overflow, and a calmer, richer map (2026-10-04)
The owner reported that after a long game "the tabs get so much text they start covering the
screen". Screenshots of a 60-turn game at laptop size found three causes, now fixed:
- The top bar grew with the numbers (6,974 (1,395); 37,079) until the menu button was pushed
  off the screen. Figures now use a compact form (37.1k, 6.2M; the exact number is in the
  tooltip), sit in a strip that clips instead of pushing, and shrink on screens narrower than
  1,800 pixels; the menu button always stays on screen.
- The province card grew with every army and open box until it ran under the top bar and off
  the bottom. It now stops below the top bar and scrolls; its buttons wrap.
- The news box ran under the Cities/Notebook/End Turn buttons and its long lines spilled. It
  now ends before those buttons and shows four one-line items, the rest on hover.
Graphics: the map read neon green everywhere. The terrain palette is warmer and more natural,
drier lands (Spain, Anatolia, the steppe) show their tan, hill country turns olive, steep
ground is shaded so relief reads, and the global saturation boost is lower (1.32 -> 1.12 on
the Mac's renderer). Army and fleet figures on the map now sit on rounded banners in their
owner's colour (gold-brown for the player) instead of floating as bare text.

## D-269 Combat v2 on screen, and a gentler formation edge (2026-10-04)
The client now shows D-267: each of your armies has a Formation picker (with what each beats
and needs, and why a wide line would be thin), an "If attacked" picker (fight, cautious,
last man), a Forced march button beside March, a live odds line against nearby enemy
armies (your share of the fighting strength, green, even or red), and notes for camps
("dug in"), forced marches and enemy strength guessed out of sight. Rival armies show their
likely formation. After a turn with battles, the news box offers "Battle reports": each
battle phase by phase (skirmish, clash, pursuit), with both sides' losses and morale bars,
so the player can see why it was won or lost. The formation edge is lowered from +20% to
+15% (the helper found +20% close to decisive at even numbers; numbers, ground and
generals should still count). The test options now give war and march orders before the
played turns, so screenshots can show real battles.
## D-270 Combat v3: wings, deployment and battle ground — DELEGATED (2026-10-05)
The owner asked to "make the battles even more tactical". Everything from Combat v2 (D-267)
stays; the clash is now a real fight between wings of troops the player places, on ground that
matters. Engine only: the client screens for it come in a later step.
- **Deployment.** Each army places its troops by kind (infantry, spear, missile, mounted,
  elephant) on the left wing, centre, right wing or in reserve, or "split" across the line.
  A kind left alone is "auto": the army's formation puts it where it belongs. The six
  formations are now presets of a deployment (a `layout` in `core/formations.yaml`: strong left
  masses the horse and best foot on the left, strong centre masses heavy foot in the middle with
  horse on the wings, deep reserve holds back a fifth, wide line spreads). Siege engines never
  stand in the line. New order `ArmyDeploy`; new army fields `deployment` and `arrived_turn`.
- **The clash, wing by wing.** Left meets the enemy's right, centre meets centre. Each wing's
  power uses the same unit maths as before but against only the kinds standing opposite it, so
  spears opposite horse count their bonus and spears opposite foot do not. A first exchange
  (no luck of the day, only each wing's own fortune) shows how it goes: a wing at 1.5 times its
  opposite BREAKS it, which then fights on at 60%, and the winner wheels on the enemy centre
  (that centre loses 20% and takes 30% of the winning wing's power on top). Reserves then go in
  where the line is weakest (a great general, with nothing in danger, presses the best wing
  instead), so a deep reserve plugs a breach before it becomes one. A wing held far back (under
  half its fair third) is "refused": it is neither broken nor won, and the enemy wing facing it
  is free to wheel on the centre. Horse on a wing that faces no horse ride round (enemy centre
  -10%). The side that wins two of the three contests wins the clash (power breaks a tie); each
  broken wing also costs its side morale, which feeds the existing break rules. The formation
  edge (+15%) stays, so the old matchups still hold; the wing maths adds to it rather than
  replacing it. A deep reserve no longer pays a -12% power cost (its men really are held back).
- **Ground.** All numbers are in the rules. River (the province's geography flag): attackers
  lose 12% (horse 37%) in the first exchange and 40% of that afterwards; defenders dug in on the
  bank ("holding the river line") make it 50% worse. Hills and mountains: the defenders'
  missile troops shoot 20% better (skirmish too) and horse charging uphill lose 20%. Forest and
  marsh: horse and elephants lose 25%, and a wide line cannot form (it is thin). Open ground
  (plains, river plains, steppe): horse on the wings gain 15%. Battle reports and the odds
  preview carry a `ground` sentence. Rivers are on most provinces of the real maps, so the
  river penalty was kept small.
- **Two armies, two directions.** Armies of one side that march into the battle province in
  the same turn from different neighbours: the largest army (and any that came the same way)
  forms the line; the others are an extra force that falls on the enemy's weaker wing
  (+25% power; that wing -15%). The report says "the Roman second army fell on the
  Carthaginian left".
- **Rivals.** Rival courts deploy "auto". A general of 3+ stars also tries the line turned
  round (left and right swapped) against what the enemy will show and takes it if better.
- **Balance.** Measured before and after on eight standard matchups at 60 seeds each: winner's
  losses stay 7-12%, loser's 20-35% (as v2); win rates stay in the same bands (for example, an
  even mixed host: attacker wins 23% in v2, 26% now; the formation matrix keeps its shape:
  strong wings beat a balanced line or strong centre, a deep reserve beats a strong wing or
  centre, a balanced line beats a deep reserve). Each wing has its own luck on top of the day's
  (15%), so a 10% lead wins less surely than before (91% to 73%).
- The view now has `deploy_places`, each army's `kinds` and `deployment`, and the odds preview
  has `wings` and `ground`. Old saves load (new fields default). Tests: wing contests,
  reserves, refused wings, horse riding round, flank blows, river/hills/forest/plains, deploy
  order, formation presets, great-general adaptation, view fields.

## D-271 Cities with streets, and the invisible houses fixed — DELEGATED (2026-10-05)
- **What.** Settled cities (all styles but the steppe camps) are now laid out on a street grid:
  a central square (larger for a capital or a city with buildings), main streets crossing it,
  side streets every few blocks, houses filling the lots and facing the nearer street, a few
  lots left as gardens. The ground is paved in a stone colour by region (sandy for Egypt and
  the Near East, reddish for India, grey-brown in the north), kept a shade darker than the
  sunlit land so it reads as stone, not snow.
- **Why.** The owner asked for better-looking cities; the old cities were a scatter of houses.
- **Bug fixed on the way.** Egyptian, Near Eastern and Indian houses, and all farm fields, were
  invisible on the Mac renderer (only their shadows drew): Godot's built-in distance fade hides
  custom-shader meshes. The house, field and new paving shaders now fade themselves out with
  distance (the same trick the army and mountain shaders already used).

## D-272 Readable tooltips and the battle sketch — DELEGATED (2026-10-05)
- **Tooltips.** Hover help is now a dark card with a gold border, cream text at 18 px, wrapped
  to about 60 characters a line, and appears after a quarter second (it was small pale text in
  one very long line). Every control's tooltip is wrapped automatically when it is created.
- **Battle sketch.** Each of your army cards shows a small top-down sketch: your three wings
  and reserve at the bottom (wider blocks for more men, from the deployment), the enemy's at
  the top (their right faces your left), and **red dashed arrows** for what you mean to do: a
  strong left curves round the enemy's right flank, a strong centre punches through the middle,
  a wide line wraps both ends, a deep reserve moves up. The battle plan adds its own marks
  (a charge's solid arrows, a skirmish's arrows loosed, a hold line, flanking curves, a feigned
  flight, a hidden ambush) and its name in red. Against a nearby enemy each wing gets a green
  tick, grey bars or a red cross for "likely to win / even / likely to give way".
- **Deployment pickers.** Under the formation, one picker per kind of soldier (infantry,
  spearmen, missile troops, horse, elephants): leave it to the formation or put them on the
  left, centre, right, in reserve or split along the line (the engine side is D-270). The
  battle ground sentence (river, hills...) shows under the odds.
- **Battle reports.** The Clash phase of each report draws the same sketch from your side, with
  each wing's fate (beaten wings hatched red), a blue arrow where a second army fell on the
  enemy's flank, and one line per wing saying what happened.
- The sketch script is loaded with `preload` rather than a global class name, because the
  class-name cache is not committed and a fresh checkout would fail to parse.

## D-273 Taking a province is a real undertaking: garrisons, storms, starving out, spoils — DELEGATED (2026-10-05)
- **What the owner asked.** Battles should feel a big deal; taking a territory should need
  planning and good execution, not be easy, and feel rewarding when it works.
- **Before.** An army alone in an enemy province simply wore the walls down (two turns for an
  ordinary province) and the province changed hands. Nothing defended the city itself.
- **Garrisons.** Every owned province keeps a garrison: 0.75% of its people under arms (rules
  `garrison_share_bp`), 400 more men for each level of built walls, twice as many in a capital.
  A garrison bled by a failed storm or by hunger rebuilds 20% a turn once the siege lifts; a
  newly taken city's garrison starts at a quarter (hold it against a counter-attack).
- **Taking the city: three ways (the new "assault" order).** *Storm at the breach* (the
  default): batter the walls, then storm once they are down. *Storm now*: go over the walls at
  once, against walls still standing (up to +250% for the defenders). *Starve them out*: never
  storm; the garrison loses 35% a turn to hunger and desertion and the city opens its gates
  after about three turns. Meanwhile besiegers lose 2% of their men a turn to sickness (halved
  by a quartermaster general), and enemy field armies can still come to relieve the city.
- **A storm is a real battle.** The garrison is drawn up as an army of the owner's soldiers
  and fought with the same three phases, plans, formations, wings and reports as a field
  battle (titled "The storming of ..."), fighting from walls and streets with +80% power, more
  for built walls and for walls not yet breached. Lose, and the attackers fall back and the
  siege starts again; a cautious general will not throw his men at walls he expects to hold.
- **The reward.** A city taken pays spoils from the loser's treasury (6 wealth per 1,000
  people; doubled by a sack, which also kills or carries off 5% of its people), prestige at
  court (+3% legitimacy, +9% for a capital), +4% veterancy and +15% morale for the army. Any
  field victory now also brings +1% legitimacy (and the loser loses as much).
- **Measured on real maps** (main starting army against a fresh city, storm now / at breach):
  Rome 31k vs Carthaginian provinces 70-91% / 86-96%, vs Carthage itself 27% / 49%; Qin 18k vs
  Wei provinces 11-60% / 31-86%, vs the Wei capital 8% / 24%; Egypt 30k vs Hattusa 29% / 60%.
  Ordinary provinces fall to a proper siege; capitals need a larger army, siege engines, a
  second army or starvation. The full test suite (503 tests, including the multi-seed
  simulations) passes unchanged.
- **On screen.** The province card shows the garrison; an army before an enemy city shows a
  siege panel (garrison, walls standing, turns to the breach or to starvation, today's storm
  odds) with the three orders; its battle sketch draws the city wall with its breaches. Before
  the turn ends, a **Council of War** lists every storm and battle coming this turn with its
  sketch, odds, ground and the plan, formation, rules of engagement and assault pickers ("Not
  yet" / "To battle!"; once a turn). A city taken opens a **triumph card** (rays of light in
  your colours, falling gold) listing the spoils.
- Old saves load: new fields default (full garrisons, "breach").

## D-274 Battles and conquests played out on the map; livelier buttons — DELEGATED (2026-10-05)
- **Your battles in full.** When the turn plays out, each battle your armies fight is staged
  where it happens: two blocks of soldiers in their states' colours rise up with standards at
  their head; arrows arc between them ("The skirmish"); the lines charge and crash together
  with dust, sparks and a camera shake ("The clash"); they heave back and forth; then the
  beaten side breaks, some falling, the rest running, its standard toppling, while the
  victors' standard rises and the line advances ("The rout"). At a storm the defenders stand
  on a wall and stones fly in from the siege lines.
- **A city taken.** Fireworks in gold and your colours burst over it under a shaft of light;
  the caption says how it fell ("Hexi is stormed!", "... opens its gates!").
- **Buttons** swell slightly under the mouse and give when pressed (every button, by one hook).

## D-275 Houses in each civilisation's own style — DELEGATED (2026-10-05)
- **What the owner asked.** Buildings more intricate and customised to the civilisations.
- **What changed.** Instead of the same fantasy-kit cottages everywhere, houses are now built
  in code from simple solids with their details modelled, three kinds per region: East Asia:
  white plaster between dark timber posts, lattice windows, hipped tile roofs with curling
  eaves and ridge ends, two-storey houses with a skirt roof, long townhouses with slatted shop
  fronts; and a five-tier pagoda in capitals and great cities. The Nile: mud brick with
  parapets, rooftop palm-thatch shelters, outside stairs, walled yards with palms; obelisks at
  the temple gate. The Near East: whitewashed cubes with blue doors, domed houses, wind towers.
  India: whitewash and brick with crenellated parapets and ochre bands, red door frames,
  rooftop pavilions (chhatris) and domed balconies. The Mediterranean: atrium houses with
  columned porches under terracotta, three-storey tenements with shops and a wooden balcony,
  small houses with vine pergolas. Northern towns keep their timber houses, the steppe its
  tents.
- Roofs (and flat roof terraces) still take a little of the owner's colour, so a conquered
  city's roofs change with it. One new shader, which fades itself out with distance like the
  others (the built-in fade hides custom shaders, D-123).

## D-276 Menus checked on different screens — DELEGATED (2026-10-05)
- **Checked.** The game screen, province card, council of war, Cities, Settings, Chronicle and
  tech tree at 1024x768 (4:3), 1280x720, 1440x900 (16:10), 1600x900 and 2560x1080 (ultrawide).
- **Fixed.** The Cities screen ran off the right edge below 1380 px wide: it now fits the
  window, with a narrower city list and one column of building choices on narrow screens.
  Menus (Settings and the rest) ran off the bottom of short screens: they now scroll inside
  the window. The question card (dilemmas, envoys) narrows to fit between the side panels.
- **Interface size.** On small windows the whole interface shrank with the window and text
  got tiny; "Auto" now keeps it at least 90% of its designed size. Settings has a new
  **Interface size** choice (Auto, Larger, Largest) for a big or high-resolution screen; it
  never enlarges so far that panels would collide.

## D-277 Coming to the aid of a state under attack — DELEGATED (2026-10-06)
- **What the owner asked.** "March to help other people getting attacked, to build alliances."
- **The order.** In the World tab, any state at war shows "Under attack by ..." and a button
  "Come to their aid against X". You go to war with the attacker (an ally of the attacker
  is betrayed, as with any declaration of war). When a neighbour of yours is attacked, the
  news says so and points to the button.
- **Your armies may go there.** While you fight for a friend, your armies may march through
  its land (normally only allies' land is open) and they defend its provinces as its allies
  would: an enemy army that comes there fights you as the defender.
- **Gratitude** (shown as a bar on the friend's card) is earned by joining (15%), each victory
  over the attacker (15%, double on the friend's soil), each of its cities you take back
  (40%), and each turn an army of yours stands on its soil (3%). It eases the friend's grudges
  against you; at 25% it warms to neutral, at 50% it opens trade, and at 100% its envoys come
  offering an alliance (or "Propose alliance" succeeds at once from 50%).
- **Liberation, not conquest.** A city of the friend's people that the attacker had taken,
  stormed or starved by you, goes back to the friend instead of to you: no spoils, but
  prestige, veterancy and a large debt of gratitude. The triumph card says "... IS FREE!".
- **Betrayal.** Making a separate peace with the attacker while the friend still fights
  gives the friend a lasting grudge (30%). The pledge ends with the friend's war; the warmer
  relation and eased grudges remain.
- Rival courts do not (yet) come to others' aid this way; allies still join automatically.
  Old saves load (no pledges).

## D-278 Every action earns its place — DELEGATED (2026-10-06)
- **What the owner asked.** Many actions looked like they were "there for the sake of it":
  make sure each has a clear, worthwhile use, or improve or remove it.
- **Audit.** Every player action was checked against what the rules actually do with it.
- **Fixed: tribute paid nothing.** Making a state your tributary only changed a label. Now a
  tributary pays its overlord each turn (10% of its treasury, at least 2 wealth per 1,000 of
  its people, never more than half its treasury) - and so does the player, if they bow to an
  ultimatum. Who is overlord is now recorded (older saves: the larger state). "Demand
  tribute" only appears when it could work (a court a third as strong as you, or one you are
  at war with), and its tooltip says what they would pay.
- **Improved: missionaries.** Converting a court to your faith now makes trade with it pay
  half as much again (on top of grudges fading faster and the faith spreading on).
- **Shown: what each tie is worth.** Each state's card in the World tab shows "Each turn:
  trade +N, tribute +N wealth" (or the tribute you pay, in red).
- **Removed: "Spread false rumours"** (it did almost the same as sealing the borders) and the
  project **"Pause"** button (pausing only let progress decay; low priority slows work
  without losing it). Both still load in old saves and replays.
- **Clearer:** "Send envoy" only shows when it would do something (a cool relation or a
  grudge to ease), and says what it will do; "Seal the borders" says what it protects and
  costs (the trade lost each turn) and is only offered while word of your inventions is on
  the road; festival, mercenaries, alliance, war, missionaries and abandoning a project all
  say in numbers what they do and when to use them.

## D-279 Cities planned on their ground — DELEGATED (2026-10-06)
- **What the owner asked.** Buildings were placed unnaturally, often overlapping, sometimes
  in the sea. Cities should each be unique, thoughtfully laid out for the terrain around
  them. Later: "I liked the buildings just on the grass; combine that depending on how
  developed each city is."
- **Nothing overlaps.** Every building claims its ground, and nothing is built where another
  stands; houses shrink to fit their lot. Every footprint must be dry all round, so nothing
  stands in the water.
- **Each city its own shape.** The outline follows the land: a coastal city is laid out to
  face the sea, keeps to the shore and sends a road down to its piers; lots across a bay or
  up a mountainside (220 m above the centre) are left out, and only lots that can be reached
  from the centre are built on. Planned cities (Rome, China) are near-square grids with
  regular streets; elsewhere the roads fan out from the centre in their own directions and
  the houses sit a little askew; northern towns have a ring road.
- **A square at the heart** sized to the palace; public buildings take the lots next to the
  square and the main streets, facing it; the pagoda of an eastern city stands among them.
- **Walls follow the outline**, are built before the houses (so nothing breaks them), stop
  where the water guards the city, and open in a gatehouse wherever a road leaves.
- **Paving grows with the city:** a town's houses stand on the grass round a small paved
  square; a city paves its streets too; only a great city or a metropolis paves everything.
  Suburbs of a great city grow along the roads out of the gates.
- **Towns and villages** are a lane of houses facing each other with their fields beyond,
  placed on good farmland after every chief city is planned, so they never land inside one.
- The Nile capital's pyramid stands on dry desert ground beyond the city. Plain painted parts
  (palaces, columns, terraces, tents) now fade with distance like the rest (they were left
  half see-through).

## D-280 Detailed buildings from a model kit — DELEGATED (2026-10-07)
- **What the owner asked.** "It's still so basic ... make the components less simple blocky
  things, take your time and do the job properly", using several Sonnet agents in parallel.
- **A modelling kit** (`client/scripts/models/kit.gd`): real roofs with slab thickness,
  overhanging and upturned eaves, columns, domes and onion domes, framed, shuttered, latticed
  and arched windows, doors, chimneys, banners. Each face carries a material, and one shader
  (`models.gdshader`) draws its surface: roof tiles in rows, stone courses, brick bond,
  plaster, timber planks, thatch, felt, rammed earth. Roofs and banners take the owner's
  colour, so who holds a city still shows at a glance. Only gilding is shiny.
- **Seven modules, built in parallel by agents, one per region**, each with its own
  houses (four to six genuinely different shapes, so a street looks lived-in), palace and
  landmarks: East Asia (incl. the Japanese castle keep and pagoda), Classical (temple, forum,
  arch, insulae and villas), Northern Europe (timber, thatch, longhouse, izba, castle,
  church), Steppe (yurts, great tent, wagon tent), Nile / Near East / South Asia (pyramid,
  sphinx, ziggurat, stupa, shikhara), walls (six families of wall, tower and gatehouse) and
  civic buildings (market, bank, temple, granary, workshop, factory, school, academy,
  observatory, windmill, water wheel, clock tower, aqueduct, hospital, station, harbour).
- **Culture picks the house:** samurai, Joseon, Punic, Viking, Rus and Assyrian peoples
  each get their own mix and palace. Content packs need no change: a culture without its
  own mapping uses its region's set, and a region without a module keeps the older houses.
- **Inventions** now raise the matching civic building beside the capital (a windmill, an
  observatory, an aqueduct) instead of a coloured block.
- **Paving** is patterned: flagstones, cobbles or beaten earth, by how developed a city is.

## D-281 Living cities: grown from the ground, planned by culture, never repeating — DELEGATED (2026-10-08)
- **What the owner asked.** "The buildings themselves look good but they look like they have
  just been thrown onto terrain. There needs to be a seamless blend between the ground and the
  buildings, with smaller things like barrels, shrubbery, paths... Many of the layouts still
  need work. The same two buildings are often just shoved together for every city... find
  another way." Done with ten parallel agents, each owning separate files (see below).
- **Split of the work.** Settlements keeps drawing; planning moved out:
  `scripts/city/plan_city.gd` (chief cities), `plan_rural.gd` (towns, villages, farms, camps),
  `ground.gd` (the ground under them), `dressing.gd` (props). Every building placed is recorded
  in `Settlements.placed`, so the ground and the dressing work from the plan, whoever made it.
- **Ground grown, not laid.** No more raised paving slabs. Streets, squares, yards and fields
  are skins draped on the exact terrain with feathered, noisy edges in the map's own palette:
  dirt lanes with ruts and grass breaking through, fine cobbles, flagged squares. Every
  building gets a worn apron (wider at its door), a dark contact band at the wall foot, a path
  from its door to the street and a plinth reaching into sloping ground, so no corner floats.
  Paving still grows with a city's rank (D-279).
- **Plans by culture.** Streets first, then blocks: main roads from the gates bend to level
  ground; lanes fill the blocks; houses front the streets shoulder to shoulder in the core,
  with yards and gardens behind, thinning to cottages and orchards at the edge and suburbs
  along the roads outside. Rome a grid round a forum; China walled wards on a ceremonial axis;
  Japan a castle town on the high ground; the north a market place and churchyard; the Nile,
  Near East and India winding lanes and courtyard clusters. Villages likewise: greens and
  ponds, stream and paddy villages, Nile-bank clusters, tank villages, villa farms, herder
  camps, with lanes, tracks and a patchwork of draped fields, orchards and pastures.
- **Variety by generation.** Instead of a handful of hand-made houses, each region's module
  builds houses from parameter tables (storeys, roof form, annexes, porches, materials...):
  about 37-49 kinds per region plus two-lot terraces, courtyard compounds and farmsteads, chosen
  per culture and per rank (`house_set`, `big_house_set`). Neighbours never repeat the last few
  kinds, and each building weathers to its own tint in the shader.
- **Life between the buildings.** ~35 generic props, ~35 plants and animals and ~40 regional
  ones (stone lanterns, amphorae, market crosses, shadufs, tree platforms, horse lines...),
  placed by rule: goods by doors, gardens and animals behind, fenced yards in local materials,
  stalls on squares, boats on shores, and a ring of shrubs and trees thinning into the land.
- **Fixes on the way.** Each people's temple in its towns (pagoda, church, shikhara, pylon
  temple, ziggurat) instead of the Greco-Roman one; idea landmarks at the city's own scale;
  standards, not cypresses, at the khan's tent; the bare flagpole gone.
- **Cost.** Building every settlement grew to ~32 s on the (slow) cloud machine; the
  planners and the ground were then optimised (see PLAN). The log prints the time per phase.

## D-282 The find-skills skill, kept in the repo — owner's request (2026-10-11)
- **What the owner asked.** Add the "find skills" Claude skill: it searches the open agent
  skills directory (skills.sh) for a skill suited to a task and installs it.
- Vercel's `find-skills` (MIT, `vercel-labs/skills`) is copied unchanged, with its licence,
  into `.claude/skills/find-skills/`, so every cloud session on this repo loads it (cloud
  containers start fresh; a skill installed only in the user folder would vanish).
- It works through `npx skills find <query>` / `npx skills add <owner/repo@skill>`; it checks
  install counts and the source's reputation before recommending, and installs only on the
  owner's say-so.

## D-283 Game-development skills from the open directory — owner's request (2026-10-11)
- Found with find-skills (D-282) and vetted: install count, source, licence, and every file read
  (all are markdown guides; none runs commands or fetches anything). Copied unchanged with their
  licences into `.claude/skills/`:
  - gamedev-skills/awesome-gamedev-agent-skills (Apache-2.0, LICENSE + NOTICE kept):
    `godot-shaders`, `procedural-gen`, `game-feel`, `performance-optimization`, `game-ui-ux`,
    `camera-systems`, `game-ai`.
  - wshobson/agents (MIT): `godot-gdscript-patterns`.
  - minimax-ai/skills (MIT): `shader-dev` (GLSL techniques, to adapt to Godot's language).
- The gamedev-skills Godot guides target Godot 4.7; this project runs 4.5, so anything they mark
  as new in 4.7 is checked before use. The project's own rules (CLAUDE.md, the model kit, D-xxx)
  win over any general advice in them.
- Left out: `godot-master` (very broad, LGPL), `create-game-assets` (2D/AI-image oriented, wants
  Python packages), and the Three.js/Unity/Unreal/Roblox skills (other engines).

## D-284 Using the skills: measured performance work and game feel — DELEGATED (2026-10-11)
- **What the owner asked.** "Use the skills to improve the game." Led by the
  performance-optimization skill (measure first, fix the biggest cost, measure again) and the
  game-feel skill (layered, short feedback scaled to how much a moment matters).
- **Measured, not guessed.** A `--perf` option prints draw calls, triangles and memory for a
  view, and `--perf-parts` how much each part of the world costs (hide it, re-measure).
  Qin's capital, close (distance 14) and the province view (120), before → after:
  triangles 30.8M → 14.2M close, 46.8M → 20.1M wide; draw calls 2,505 → 2,306 and
  4,888 → 2,267; scene objects 4,097 → 3,193 and 9,424 → 3,167.
- **The two biggest costs found:**
  - **Trees** were 21M of the 31M close-up triangles: every map tree was the full Kenney model
    (up to 400 triangles) out to 260 units, with shadows. Now the detailed trees show only
    within 60 units, in small batches; beyond, a simple tree of a few dozen triangles without
    a shadow stands in, fading across. Clearing trees out of cities covers both.
  - **Armies** were 212,000 triangles and 180 nodes each (5.4M in the province view): every
    head and helmet was Godot's default sphere (some 4,000 triangles), each part its own node.
    Now spheres are low-poly and each army is one mesh per colour: 5,900 triangles, 8 nodes,
    and looks the same at map scale.
  - Small settlement props (barrels, animals, garden beds) now show only within 100 units.
- **Game feel.** The camera shake was random jumps along a tween; now it is the skill's
  "trauma" model: great moments add trauma (0..1), the camera sways by trauma squared along
  smooth waves, and it settles in under a second. Battles shake hardest, a city of yours won
  or lost strongly, a breakthrough moderately, siege stones landing lightly. A Settings
  checkbox turns screen shake off (accessibility, as the skill advises).
- **Tried and dropped.** A tilt-shift (depth of field) "diorama" look close up: it showed no
  visible effect in the headless renderer at any strength, so it was removed rather than
  shipped unverified.

## D-285 Caveman skill: shorter replies — owner's request (2026-10-12)
- Found with find-skills (568K installs, Apache-2.0, juliusbrussee/caveman); copied unchanged
  with its licence into `.claude/skills/caveman/`. It trims Claude's chat replies (no
  greetings, recaps or filler; every fact, command and number kept) to save usage. It never
  touches code, commits, docs or memory files, and switches back to full sentences for
  warnings, irreversible actions, questions to the owner, or when the owner seems confused,
  which keeps faith with "explain in plain language". Off with "stop caveman" / "normal mode".

## D-286 Rome only, 509-27 BC, a thousand times deeper — owner's direction (2026-10-20)
- **What the owner asked.** Scrap every other timeline; you can only play the Roman state; the
  scale shrinks but historical accuracy and detail multiply; build the city of Rome (the owner
  named "Rome Remodelled", taken to mean Rome Reborn); same concept, narrower and deeper.
- **Owner's choices (asked 2026-10-20):** build our own Rome (Rome Reborn is commercial,
  Flyover Zone holds an exclusive licence; it is used only as visual reference); the
  Republic to Augustus, 509-27 BC; keep the time-traveller core; archive then remove the rest.
- **Archive.** The whole multi-civilisation game is kept on the branch
  `claude/archive-multi-civ` (commit 93815d7). A git tag was refused by the repository, so a
  branch holds it instead.
- The plan, its sources and its phases (R0-R6, each a gate): `docs/plans/rome.md`. Every
  historical fact will carry its source, and the linter will enforce that.

## D-287 Rome's Italian allies are separate civs bound by treaty — DELEGATED (2026-10-23)
- The *socii* kept their own laws and armies and served under treaty; Polybius 2.24 lists their
  levies apart from the Romans. So in the 264 BC start (`rome_264`) the allies (Samnites,
  Etruscans, Umbrians, Italiote Greeks and others) are their own civs, allied to Rome, and can
  defect as Capua and Tarentum did after Cannae (Polybius 3.118). Rome itself holds the ager
  Romanus and the lands of the Latins, Volsci, Hernici, Aequi, Sabines, Caere, Aurunci,
  Campania, Picenum and the Senones.
- Latin colonies inside allied land cannot be drawn at this map grain; R3 adds a real alliance
  and citizenship system.
- Facts the agents could not read in a source are marked `# unverified` and wait for the R6
  checking pass.
- The test port (all old-scenario tests now use `punic_wars`) found that the Aegean no longer
  links to the Levantine sea since the other packs were removed; to be restored.

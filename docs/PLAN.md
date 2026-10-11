# Anachronism — Plan

**Current phase:** Phase 2 — 3D world (Godot) on the Phase 1 engine (branch `claude/phase-2-3d`).
**Next action:** the owner plays the build (gate 2.16). Meanwhile, gameplay depth from the
brief is being added (owner, 2026-10-02: "stop working on the graphics, and perfect the
gameplay"): province buildings first (D-111), then a review of the brief for gaps.

Each phase ends at a **gate**: Claude stops, summarises, shows how to run it, lists known
problems, and waits for approval (D-002: approval = merging the phase PR).

## Phase 0 — Foundations
- [x] 0.1 Read brief, ask questions, record decisions (DECISIONS.md), draft docs
- [x] 0.2 Owner approves DESIGN.md, ARCHITECTURE.md, PLAN.md (approved 2026-09-30)
- [x] 0.3 `pyproject.toml` (uv, Python 3.12), ruff, mypy, pytest config; package skeleton;
      `uv run anachronism` launcher
- [x] 0.4 Mac setup guide (`docs/GETTING_STARTED.md`, see D-031); `.env.example`
- [x] 0.5 Guard-rail tests (layers, network, secrets, docs); `scripts/check.sh`;
      GitHub Actions CI on Ubuntu + macOS
- [x] 0.6 SessionStart hook so cloud sessions can run tests and linters
- [x] 0.7 Repo moved to `Lilmagpy/Anachronism` with `main` (D-033); gate passed 2026-09-30

## Phase 1 — Headless engine on a test world (design: plans/phase-1.md)
- [x] 1.1 `GameRng` (PCG32, seeded, serialisable) + integer maths helpers
- [x] 1.2 Content schemas + loader + linter for `core` and `testworld` packs
- [x] 1.3 Test world: 3 fictional civs, 20 provinces, 55 core tech nodes
- [x] 1.4 GameState models; new game; save/load round-trip
- [x] 1.5 Economy: workforce, surplus, production, upkeep, granary, history snapshots
- [x] 1.6 Projects: priority funding, scarcest input, progress, luck, stalling, decay
- [x] 1.7 Strain → unrest → riots → revolts → collapse spiral
- [x] 1.8 Tech graph: stages, feasibility, goals, stubs, effects with caps and stacking
- [x] 1.9 Suspicion and framings
- [x] 1.10 Turn pipeline; action log; replay
- [x] 1.11 Interactive console (`uv run anachronism`)
- [x] 1.12 Bots, simulation tool, long-game invariant and balance tests
- [x] 1.13 Gate: approved and merged by the owner (2026-09-30)

## Phase 2 — 3D world (design: plans/phase-2.md; replaces the Pygame front end, D-047)
- [x] 2.1 Engine bridge: JSON messages over stdin/stdout (`anachronism-server`), tested
- [x] 2.2 Map layout in content: province positions and sea zones; linted
- [x] 2.2b Real Earth map (D-053): measured elevation, NASA satellite colour, Natural Earth
      rivers; East Asia first. The fictional test world stays only for tests (`--map=testworld`)
- [x] 2.2c Real historical scenario: the Warring States, 350 BC, playing Qin (D-054..D-056):
      18 states and peoples, 53 provinces, 10 seas, borders grown over real terrain
- [x] 2.3 Godot client: 3D terrain, water, sky, Rise of Kingdoms-style camera (pan, zoom)
- [x] 2.4 Borders coloured by owner, province labels, selection and hover
- [x] 2.5 Game UI: top bar with trends, ideas and details, projects, end turn, events
- [x] 2.6 Settlements scaled by population: walled capitals with palace halls, towns,
      villages and fields on the flattest land (D-058); hand-made models can come later
- [x] 2.7 Screenshot pipeline in the cloud; CI builds a downloadable Mac app (D-057)
- [x] 2.8a Owner played the Mac app (2026-09-30): it works, but the look and feel fall short
      of what the owner wants (D-059). Phase 2 continues with 2.9–2.16 before its gate.

### Phase 2, part two — look, characters and choice (D-059..D-061)
- [x] 2.9 Title screen and civilisation picker: choose a civilisation and a starting
      moment (portrait, description, bonus, Confirm), like Rise of Kingdoms
- [x] 2.10 Engine: list scenarios and playable civs; start as any civ in a scenario
- [x] 2.11 Bright cartoon map over the real geography: painted biomes (classified from the
      satellite image), toon light bands, sea painted by depth with coastal foam, cartoon
      forests; cream-and-gold game screens. Still to come: animated water, clouds
- [x] 2.11b Animated cartoon water (waves, crests, glints), drifting clouds, low-poly
      snow-capped peaks over the real ranges
- [x] 2.12 Characters: rulers, advisers and rivals pop up and speak (scripted lines as
      content data in core/dialogue.yaml and speakers.yaml; placeholder portraits, D-060)
- [x] 2.13a Your ideas made visible: landmarks around your capital for adopted ideas
      (aqueduct, windmill, water wheel, observatory, school, workshops, forges, harbour…);
      click your emblem to fly down to the capital
- [ ] 2.13b Cartoon cities from CC0 art packs (needs network access to the packs)
- [x] 2.13c Cities in their region's style (East Asian, Nile, Near Eastern, Mediterranean,
      northern, steppe), no trees inside walls; batches tiled so cities show on large maps
      (D-077); map names give way instead of overlapping
- [x] 2.14 New regions and moments (D-061): the "europe" map (Ireland to Persia, Sahara to
      Scandinavia) is built; [x] Rome and Carthage, 264 BC (19 states, 70 provinces);
      [x] Egypt and the Hittites, 1275 BC (11 states, 50 provinces); [x] Europe in the Year 1000
      (29 states, 96 provinces); [x] The Three Kingdoms of Korea, AD 400 (11 states, 38
      provinces, Korea and Japan in detail; D-069); [x] Japan's Warring States, 1560 (18 states,
      41 provinces; D-074); [x] The Great Khan, 1206 (10 states, 54 provinces; D-084);
      [x] Alexander's inheritance, 336 BC (12 states, 54 provinces; D-090);
      [x] The Mauryan dawn, 321 BC (8 states, 35 provinces, India on the East Asia map; D-097)
- [x] 2.15a Screens (brief §11): pre-play disclaimer; a timeline of starting moments in the
      picker; in-game menu (Esc) with save, load, chronicle, tech tree (goal stubs, your
      own ideas marked) and settings (model status, offline switch); developer overlay (F3)
- [x] 2.15b Charts over time (menu → Charts): people, stores, society, the largest states
- [x] 2.15c Sound and music, synthesised by scripts/make_sounds.py (plucked-string theme,
      gong, drums, chimes, clicks); switches in Settings
- [x] 2.15d Comfort: autosave every turn and Continue (D-088); difficulty levels (D-089);
      Enter ends the turn, 1/2/3 switch tabs; trade routes drawn on the map; blocked
      rulings offer the first steps; click an idea in the tech tree to ask the court; an
      end screen that sums up the reign; tooltips on every figure
- [ ] 2.16 Gate: owner plays the new build on their Mac and merges the phase PR

## Phase 3 — LLM ruling pipeline (moved after the 3D world, D-049)
- [x] 3.1 Output schemas (`llm/schemas.py`); guard (`llm/guard.py`) plus engine bounds
      (`engine/judge.py`): effect caps, complexity/year floors, capped adviser nudges (D-063)
- [x] 3.2 Compact summary builder (`engine/summary.py`, tested under 600 tokens)
- [x] 3.3 Fake provider; pipeline interpret/clarify/split/rule/flavour (`llm/pipeline.py`)
- [x] 3.4 Ruling cache; rulings stored in the action log (`RuleOnIdea`); replay without calls
- [x] 3.5 Offline interpreter over the library, with keywords on every node (D-064)
- [x] 3.6 Anthropic provider: model from config (no default, D-065), prompt caching,
      forced tool output, retries — standard library only, no new dependency
- [x] 3.7 Monthly token cap and usage ledger; debug log of every call (toggle)
- [x] 3.8 Prompt-injection and failure-fallback tests; the idea box in the 3D UI with a
      "the court deliberates" state; "Ask the court" on goal stubs
- [ ] 3.9 Gate (owner needs an Anthropic API key and a model name for live testing)

## Phase 4 — Scripts, awareness, information (headless)
- [x] 4.1 Scripts with preconditions (conquer / ally / trade / adopt), per civ per scenario,
      lapsing when their moment passes; dependency graph (lapses ripple) (D-066)
- [x] 4.2 Awareness: on-script → aware (heard news) → free agent (grudge, war, conquest);
      rulers' dispositions steer free agents
- [x] 4.3 News of anachronistic adoptions travels border by border, faster along friendly
      ties and with suspicion, slower with secrecy; far news garbled, truth later;
      intelligence reports ("Chu has learned of your Paper"); rivals copy what they hear
- [x] 4.4 Relations with memory (grievances fade slowly); alliances join defensive wars
- [x] 4.5 Abstract war: strength from workforce, military effects and legitimacy; frontier
      captures, losses, weariness, peace; capitals move; states can be destroyed (D-067)
- [x] 4.6 Player diplomacy: envoy, alliance, war, peace; World tab; war fronts on the map
- [x] 4.7 Tiered victory (regional for now): military, economic, cultural; defeat (D-068)
- [x] 4.8 Historical scripts and relations for all four starting moments
- [ ] 4.9 Gate: owner review (scripts are drafts from general history; see D-066)

## Phase 5 — East Asia pilot
- [x] Review workflow: `anachronism-draft` drafts ideas into git-ignored `drafts/`;
      `--promote` moves only sourced, reviewed entries into a pack (D-070)
- [ ] Finalise schemas; choose flagship scenario;
      author 8–10 civs; timeline UI; CJK fonts; balance pass; gate

## Phase 6 — Europe (schema stress test) + steppe connector; gate
## Phase 7 — Depth: events, rival rulers via LLM, chronicle, advisors, victory, suspicion tuning; gate
### Phase 7, early (done during the night shift, before its gate)
- [x] Rulers age, die and are succeeded (named heirs per scenario); succession crises
- [x] Happenings: plague, flood, harvest, comet… at most one a turn (core/happenings.yaml)
- [x] Trade and faith as flows: friendly ties pay wealth; faiths spread; missionaries (D-073)
- [x] Capitals and terrain defend; a last stand; two turns' grace for the player (D-079)
- [x] Royal decrees (festival, mercenaries), used by rival courts too (D-076)
- [x] Victory tuning: cultural needs your own influence; economic needs a network of
      allies and a large economy, one embassy a turn (D-076, D-078)
- [x] A library of 102 advancements to the telephone, with the republic and democracy
      (D-075, D-082, D-087)
- [x] Coalitions against a dominant player; demanding tribute (D-085, D-086)
- [x] A seventh moment, the Great Khan 1206, with steppe mobilisation (D-084)
- [x] An eighth moment, Alexander's inheritance 336 BC (D-090)
- [x] A ninth moment, the Mauryan dawn 321 BC, with Indian portraits and buildings (D-097)
- [x] Confidence tiers and a source-review checklist (D-083)
- [x] Rival rulers voiced by the model: war, peace, tribute and boasts (D-091)
- [x] Suspicion: the court can explain its new arts - a divine gift or foreign sages (D-092)
- [x] Aware rival courts decide with the model: war, envoy or wait, guarded and recorded (D-094)
- [x] The story so far: the chronicle told in chapters, by the model when online (D-095)
- [x] Consequences: second-order effects of advancements, as content (D-096)
- [x] The court's counsel: each adviser recommends an idea a turn (D-098)
- [x] Secrets (brief §7.3): seal the borders; spread false rumours (D-093)
- [x] War of armies: unit types, raising, marching, battles, sieges, supply, rival generalship (D-099)
- [x] Armies on the map in the client: markers, routes, sieges, orders, raising, battle sites (D-100)
- [x] Historical generals with gifts, mercenary companies, land-for-peace, elephants where they lived (D-101)
- [x] Walls in three levels, pillage, levies that breed unrest; field battles weigh the ground only (D-102)
- [x] Battles told as stories (D-103); dilemmas: historical choices put to the ruler (D-104)
- [x] Envoys: rival courts sue for peace, deliver ultimatums, propose alliances and trade (D-105)
- [x] Holding conquered land: peoples remember, rise without garrisons, assimilate in time (D-106)
- [x] Navies: fleets, sea battles told as stories, command of the sea, blockades (D-107)
- [x] Battle plans that beat each other, great generals who read the enemy, veterans (D-108)
- [x] Graphics toward Rise of Kingdoms: coasts, water, models, heraldic symbols, kit-built
      towns and landmarks, city icons, name plates (D-109; paused at the owner's request)
- [x] Province buildings, and cities that grow and fill with them on the map (D-111)
- [x] Rival courts no longer starve themselves; low priority is steady work (D-112)
- [x] The fall is not the end: new dynasties after collapse, restored states (D-113)
- [x] Infrastructure: some ideas need buildings standing in the realm (D-114)
- [x] Spies and intelligence: rival plans, stolen secrets, caught spies (D-115)
- [x] Rival courts make their own history once their scripts run out (D-116)
- [x] Rival courts quiet suspicion and win back doubting peoples (D-117)
- [x] Wars end on terms: the side that tires first cedes what is besieged (D-118)
- [x] Spend the stores: hastening work; hoards waste away (D-119)
- [x] Chronicle mode: chapters along real history, Rome against Carthage first (D-120)
- [x] The second chronicle: Qin unifies China, 350-221 BC (D-122)
- [x] Seamless zoom: fades instead of pops, names that fade, a gliding camera (D-123)
- [x] Each turn plays out on the map: marches, battles, conquests (D-124)
- [x] Chapters wait while you look at the map; only you know the future (D-125)
- [x] The notebook from the future, with our history for every idea (D-126)
- [x] Developing your cities: real numbers, ranks you can see, scaffolding (D-127)
- [ ] Fit in the painted art from docs/ART_PROMPTS.md as it arrives
- [x] The third chronicle: Oda Nobunaga, Okehazama to Honno-ji, 1560-1582 (D-130)
- [x] The fourth chronicle: Goguryeo under Gwanggaeto and Jangsu, AD 400-475 (D-131)
- [x] The fifth chronicle: Egypt under Ramesses II, Kadesh to the Sea Peoples, 1275-1208 BC (D-133)
- [x] The sixth chronicle: Alexander, from Aegae to Babylon, 336-323 BC (D-134)
- [x] The seventh chronicle: the Mauryas, Chandragupta to Ashoka, 321-232 BC (D-135)
- [x] The eighth chronicle: the Mongols, Genghis Khan to the fall of the Song, 1206-1279 (D-136)
- [x] The ninth chronicle: England from Æthelred to Hastings, 1002-1066 (D-137)
- [x] A second chronicle for 264 BC: Carthage, from Messana to its destruction (D-138)
- [x] A second chronicle for 336 BC: Persia under Darius III (D-139)
- [x] A second chronicle for 1275 BC: the Hittites, Kadesh to the fall of Hattusa (D-140)
- [x] A second chronicle for AD 1000: the dukes of Normandy to William the Conqueror (D-141)
- [x] A second chronicle for 1206: the Southern Song, from the Kaixi war to Yamen (D-142)
- [x] A second chronicle for 1560: the Takeda, Shingen and Katsuyori (D-143)
- [x] A second chronicle for 350 BC: Zhao, from Hu clothing to the fall of Handan (D-144)
- [x] A second chronicle for AD 1000: Byzantium, Basil II to Alexios Komnenos (D-145)
- [x] A second chronicle for AD 400: Baekje, the hostage prince to the bear ford (D-146)
- [x] A third chronicle for 1206: Kamakura Japan and the Mongol invasions (D-147)
- [x] A third chronicle for AD 1000: the Western Empire, Otto III to Canossa (D-148)
- [x] A fourth chronicle for AD 1000: Kievan Rus, Vladimir to Yaroslav the Wise (D-149)
- [x] A third chronicle for 350 BC: Chu, from Yue to Xiang Yan, with Qu Yuan (D-150)
- [x] A third chronicle for 1275 BC: Middle Assyria, Adad-nirari to Tukulti-Ninurta (D-151)
- [x] A third chronicle for 1560: Uesugi Kenshin, the Dragon of Echigo (D-152)
- [x] A fifth chronicle for AD 1000: the fall of the Caliphate of Córdoba (D-153)
- [x] A third chronicle for AD 400: Silla, from little brother to conqueror of Gaya (D-154)
- [x] A sixth chronicle for AD 1000: the Fatimid caliphs of Cairo (D-155)
- [x] A third chronicle for 264 BC: the Seleucids and Antiochus the Great (D-156)
- [x] A fourth chronicle for 264 BC: the Ptolemies of Alexandria (D-157)
- [x] A fourth chronicle for 1560: Joseon and the Imjin War (D-159)
- [x] A fourth chronicle for 1206: Goryeo under the Choe and the Mongols (D-160)
- [x] A fifth chronicle for 1206: the fall of the Jurchen Jin (D-161)
- [x] A sixth chronicle for 1206: Western Xia, the Tangut kingdom (D-162)
- [x] A fourth chronicle for 1275 BC: Kassite Babylon, from Kadesh to Elam (D-163)
- [x] A fifth chronicle for 1275 BC: Mycenae, the Ahhiyawa of the Hittite letters (D-164)
- [x] A third chronicle for 336 BC: Athens under Alexander, Demosthenes to Phocion (D-165)
- [x] A fourth chronicle for 336 BC: Epirus, Alexander the Molossian and Pyrrhus (D-166)
- [x] A fourth chronicle for AD 400: Northern Wei, from Chaibi to Luoyang (D-167)
- [x] An eighth chronicle for AD 1000: Denmark, Sweyn Forkbeard and Cnut (D-168)
- [x] A ninth chronicle for AD 1000: Piast Poland, Bolesław the Brave to Casimir (D-169)
- [x] A tenth chronicle for AD 1000: Hungary, from Stephen's crown to Tihany (D-170)
- [x] An eleventh chronicle for AD 1000: the Ghaznavids, Mahmud and Masud (D-171)
- [x] A twelfth chronicle for AD 1000: Ireland, Brian Boru and his heirs (D-172)
- [x] A thirteenth chronicle for AD 1000: Venice, the doges from Orseolo to the Golden Bull (D-173)
- [x] A fifth chronicle for 1560: the late Ming, from the wokou to Sarhu (D-174)
- [x] A fifth chronicle for 264 BC: Syracuse, Hiero II and Archimedes (D-175)
- [x] A sixth chronicle for 264 BC: the Antigonid kings of Macedon, to Pydna (D-176)
- [x] A fourth chronicle for 350 BC: Qi, from Maling to the last surrender (D-177)
- [x] A fifth chronicle for 350 BC: Yan, from Zizhi to Jing Ke (D-178)
- [x] A sixth chronicle for 1275 BC: Ugarit, the alphabet city, to its burning (D-179)
- [x] A seventh chronicle for 1275 BC: Middle Elam, from Chogha Zanbil to the Ulai (D-180)
- [x] A sixth chronicle for 350 BC: Wei, from King Hui to the flooding of Daliang (D-181)
- [x] A seventh chronicle for 350 BC: Han, from Shen Buhai to the first fall (D-182)
- [x] A sixth chronicle for 1560: the Mori of Aki, from the three arrows to Sekigahara (D-183)
- [x] A seventh chronicle for 1560: the Shimazu of Satsuma, to the invasion of Ryukyu (D-184)
- [x] An eighth chronicle for 1560: the Hojo of Odawara, from Kenshin's siege to Hideyoshi's (D-185)
- [x] A ninth chronicle for 1560: the Date and Masamune, the One-Eyed Dragon (D-186)
- [x] Three more chronicles for 1560 by helper agent: Ashikaga, Otomo, Chosokabe (D-187, D-188, D-189)
- [x] Eighteen more chronicles by the helper agents: France, Norway, Scotland, the Papacy, Bulgaria, León, Georgia, Armenia, the Buyids (AD 1000); Rhodes, Pergamon, Sparta (264 BC); early Rome (336 BC); Eastern Jin (AD 400); Lanka (321 BC); Imagawa, Asakura, Miyoshi (1560) (D-190 to D-207)
- [x] Era music: the owner's Roman, Asian, medieval and Egyptian/Arabic tracks play by scenario and civilisation (D-208)
- [x] Eighteen more by the helper agents: Sweden, Bohemia, Navarre, Barcelona, the Zirids, Sicily (AD 1000); Numidia, Pontus, Epirus, Athens, Achaea, Aetolia (264 BC); Zhongshan, Song, Lu (350 BC); Saito, Amago, Ryukyu (1560) (D-209 to D-226)
- [x] Nineteen more by the helper agents: Kara Khitai, Uyghurs, Dali (1206); Wa, Gaya, Later Yan, Later Qin, Southern Yan, Rouran (AD 400); Amurru, Alashiya, Wilusa, Hanigalbat (1275 BC); Zhou, Wey, Yue (350 BC); Massalia, Kush, Cisalpine Gauls (264 BC) (D-227 to D-245)
- [x] Eighteen more by the helper agents: Kalinga, Chola, Pandya, Nanda, Chera (321 BC); Scythians, Thebes, Odrysians, Illyrians, Syracuse, Carthage, Sparta (336 BC); Shu, Ba, Yiqu, Donghu, Gojoseon (350 BC); Onggut (1206) (D-246 to D-263)
- [x] The Macedonian Satraps (D-264): every state in the nine real-map scenarios now has a chronicle
- [x] History's choice listed in a shuffled order (D-265); every chapter's choices rewritten so it is not obvious (D-266)
- [x] Combat v2 engine (D-267): formations, three-phase battles, rules of engagement, camps, forced marches, scouting fog in the view (on screen: D-269)
- [x] Screens that do not overflow after long games; calmer map colours; army banners (D-268)
- [x] Combat v3 engine (D-270): deployment by kind (left, centre, right, reserve), the clash fought wing by wing, battle ground (river, hills, forest, plains), a second army on the flank; on screen: D-272
- [x] City streets and paving, invisible houses and fields fixed on the Mac renderer (D-271)
- [x] Readable tooltips; battle sketch with red dashed plan arrows, deployment pickers, wing-by-wing battle reports (D-272)
- [x] Conquest is hard-won (D-273): garrisons, storm at the breach / storm now / starve out, storms fought as battles, spoils, prestige and veterancy; council of war before battles; triumph card
- [x] Battles and conquests played out on the map; livelier buttons (D-274)
- [x] Houses in each civilisation's own style, pagodas and obelisks (D-275)
- [x] Menus checked and fixed on different screen sizes; interface size setting (D-276)
- [x] Come to the aid of a state under attack: march through its land, gratitude, liberated cities, alliance offer (D-277)
- [x] Action audit: tributaries pay tribute, shared faith boosts trade, tie worth shown, redundant buttons removed, clear tooltips (D-278)
- [x] Cities planned on their ground: no overlaps, nothing in the sea, own shapes, walls on the outline, paving by development (D-279)
- [x] Detailed buildings from a model kit: seven regional modules, culture-specific houses and palaces, civic landmarks, walls (D-280)
- [x] Living cities: ground blended under buildings, culture-specific town and village plans, generated house variety, props, plants and animals (D-281)
- [x] Performance pass (trees, armies, props; measured) and smooth screen shake with a Settings switch (D-284)
- [ ] Source-check pass over the helper-written chronicles (written without network access) before any public release
- [ ] Phase 7 gate
## Phase 8+ — More regions, first contact, tiered victory, art/sound, packaging

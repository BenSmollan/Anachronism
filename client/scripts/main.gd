## Starts the engine, builds the world and runs the game.
##
## Command-line options (after `--`): `--screenshot=PATH` saves a picture and quits,
## `--seed=N` picks the game, `--turns=N` plays N turns (the player does nothing) first,
## `--focus=province_id,distance` points the camera at a province (practice map),
## `--look=lat,lon,distance` points it at a real place, `--scenario=ID` picks the scenario
## (default `warring_states`; `bronze_dawn` is the fictional test world). On the real map:
## `--start=idea_id` begins an experiment, `--select=province_id` selects a province and
## `--play=N` then ends N turns, `--click=x,y` clicks the map, `--tab=ideas|projects|world` opens a panel (all for
## screenshots and tests). `--smoke` goes through the title screen and picker, builds the
## game, prints SMOKE OK and quits. `--screen=title|picker` (`--pick=civ_id`) shows the menus;
## `--civ=ID` starts straight away as that civilisation.
extends Node3D

const UiScale := preload("res://scripts/ui_scale.gd")

var bridge := EngineBridge.new()
var rig := CameraRig.new()
var world: WorldBuilder
var earth: EarthBuilder
var provinces: ProvinceMap
var settlements: Settlements
var scenery: Scenery
var _last_pose := Transform3D()
var game_menu: GameMenu
var landmarks: Landmarks
var _earth_holder: Node3D   ## where the map's cities are built
var _replay: TurnReplay   ## the turn playing out on the map, if one is (D-124)
var _quick_turns := false   ## turns from the command line skip the replay
var _growth := ""   ## the cities' sizes and buildings when they were last built
var audio: GameAudio
var hud: GameHud
var menus: Menus
var holder: Node3D
var _press_at := Vector2.ZERO
var view: Dictionary = {}
var options := {}
var environment := Environment.new()
var sun := DirectionalLight3D.new()


func _ready() -> void:
	# every hover text in the game is wrapped into a readable card (see UiStyle.wrap_tip)
	get_tree().node_added.connect(func(node: Node):
		if node is Control:
			_wrap_tip.call_deferred(node)
		if node is Button and not node is OptionButton:
			_lively(node as Button))
	ProjectSettings.set_setting("gui/timers/tooltip_delay_sec", 0.25)
	UiScale.apply(get_tree().root)   # readable on small windows (D-276)
	get_tree().root.size_changed.connect(func() -> void: UiScale.apply(get_tree().root))
	for arg in OS.get_cmdline_user_args():
		var parts := arg.trim_prefix("--").split("=", true, 1)
		options[parts[0]] = parts[1] if parts.size() > 1 else "true"
	_setup_environment()
	add_child(rig)
	audio = GameAudio.new()
	add_child(audio)
	var notice := _notice("Starting the game engine…\nThe very first launch downloads Python and takes about a minute.")
	for i in 3:
		await get_tree().process_frame
	var repo_root := ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir()
	var catalog: Variant = null
	if bridge.start(repo_root):
		catalog = bridge.request("scenarios")
	if catalog == null:
		_fail(notice)
		return
	notice.queue_free()
	holder = Node3D.new()
	holder.name = "World"
	add_child(holder)
	var real: Array = catalog["scenarios"].filter(func(s): return s["map"] != null)
	var direct := options.has("scenario") or options.has("civ") or (options.has("screenshot") and not options.has("screen"))
	if direct or real.is_empty():
		_start_game(str(options.get("scenario", "warring_states")), str(options.get("civ", "")))
		return
	# Title screen over a slowly drifting view of the real map, then the civilisation picker.
	_ensure_earth(str(real[0]["map"]))
	rig.look_at_point(earth.ground_at_pixel(earth.size() / 2.0), 1100.0)  # whichever map it is
	menus = Menus.new()
	menus.catalog = real
	add_child(menus)
	menus.start_requested.connect(_start_game)
	menus.quit_requested.connect(func(): get_tree().quit())
	menus.continue_requested.connect(_continue_game)
	var saves: Variant = bridge.request("saves")
	if saves != null:
		menus.can_continue = saves["saves"].any(func(s): return s["name"] == "autosave")
	menus.show_title()
	if options.get("screen", "") == "picker" or options.has("smoke"):
		menus.show_picker("", str(options.get("pick", "")))
	if options.has("continue"):  # --continue: resume the autosave, as the title button does
		_continue_game()
		return
	if options.has("smoke"):  # CI self-test: title, picker, then the game itself
		await get_tree().process_frame
		_start_game(str(real[0]["id"]), "")
	elif options.has("screenshot"):
		_take_screenshot(str(options["screenshot"]))


func _fail(notice: CanvasLayer) -> void:
	push_error(bridge.last_error)
	if options.has("smoke") or options.has("screenshot"):
		get_tree().quit(1)
	else:  # tell the player instead of vanishing
		var label: Label = notice.get_child(1)
		label.text = "The game engine could not start:\n%s\n\nCheck your internet connection for the first launch, then open the game again." % bridge.last_error


func _start_game(scenario_id: String, civ_id: String, difficulty := "normal", chronicle := false) -> void:
	var args := {"scenario": scenario_id, "seed": int(options.get("seed", "1")),
		"difficulty": str(options.get("difficulty", difficulty)),
		"chronicle": chronicle or options.has("chronicle")}
	if civ_id != "":
		args["civ"] = civ_id
	_enter_game(bridge.request("new_game", args))


## Resume the game saved automatically after the last turn played.
func _continue_game() -> void:
	_enter_game(bridge.request("load", {"name": "autosave"}))


func _enter_game(result: Variant) -> void:
	if result == null:
		_fail(_notice(""))
		return
	if menus != null:
		menus.queue_free()
		menus = null
	view = result
	audio.set_era(str(view.get("music", "")))
	for i in int(options.get("turns", "0")):
		view = bridge.request("end_turn")
	if view.get("map") != null:
		_build_earth(holder, str(view["map"]))
		_build_hud()
		if options.has("smoke"):  # CI self-test: the engine answered and the world was built
			print("SMOKE OK: %s as %s, %d provinces, %d ideas" % [view["scenario"], view["status"]["name"], view["provinces"].size(), view["ideas"].size()])
			bridge.stop()
			get_tree().quit()
			return
		if options.has("screenshot"):
			_take_screenshot(str(options["screenshot"]))
		return
	world = WorldBuilder.new(view)
	world.build(holder)
	PropsBuilder.new(world, view).build(holder, view)
	rig.bounds = Rect2(-350, -330, 700, 640)
	if options.has("focus"):
		# --focus=province_id,distance: look at one province (screenshots, tests)
		var f: PackedStringArray = str(options["focus"]).split(",")
		for p in view["provinces"]:
			if p["id"] == f[0]:
				var pos := Vector2(p["position"][0], p["position"][1])
				rig.look_at_point(world.to_world(pos), float(f[1]) if f.size() > 1 else 150.0)
	if options.has("screenshot"):
		_take_screenshot(str(options["screenshot"]))


## The bare real map (D-053), built once per region: also the title screen's backdrop.
func _ensure_earth(region: String) -> void:
	if earth != null and earth.region == region:
		return
	if earth != null:
		for child in holder.get_children():
			child.queue_free()
	earth = EarthBuilder.new(region)
	earth.build(holder)
	scenery = Scenery.new(earth)
	scenery.build(holder)
	Peaks.new(earth).build(holder)
	var half := earth.size() / 2.0
	var clouds := Clouds.new()
	clouds.build(Rect2(-half, earth.size()))
	holder.add_child(clouds)
	rig.bounds = Rect2(-half, earth.size())
	rig.far = earth.size().x * 0.9
	rig.near = 18.0


## The real map with the game on it: provinces, borders, settlements.
func _build_earth(holder: Node3D, region: String) -> void:
	_ensure_earth(region)
	provinces = ProvinceMap.new(earth, view)
	provinces.build(holder)
	settlements = Settlements.new(provinces)
	var started := Time.get_ticks_msec()
	settlements.build(holder)
	print("SETTLEMENTS built in %d ms: %d buildings placed" % [Time.get_ticks_msec() - started, settlements.placed.size()])
	scenery.clear(settlements.clearings)
	_earth_holder = holder
	_growth = provinces.growth_signature()
	provinces.show_roads(view, holder)
	_draw_armies()
	provinces.show_ties(view)
	landmarks = Landmarks.new()
	landmarks.setup(provinces)
	holder.add_child(landmarks)
	landmarks.update(view)
	environment.fog_density = 0.00003  # a continent-sized map needs thinner haze
	var sky_material: ProceduralSkyMaterial = environment.sky.sky_material
	sky_material.ground_bottom_color = Color(0.03, 0.10, 0.20)  # open ocean beyond the map edge
	sky_material.ground_horizon_color = Color(0.10, 0.20, 0.32)
	# Open over the player's capital, far enough out to see the neighbouring states.
	var start := Vector3.ZERO
	var owned := 0
	for p in view["provinces"]:
		if p["owner"] == view["player"]:
			owned += 1
			if p["capital"] and p["latlon"] != null:
				start = earth.ground_at(p["latlon"][0], p["latlon"][1])
	# a small state opens closer; the capital sits left of centre, as the panel covers the right
	var distance := clampf(420.0 + owned * 80.0, 450.0, 900.0)
	rig.look_at_point(start + Vector3(distance * 0.18, 0, 0), distance)
	if options.has("look"):
		var f: PackedStringArray = str(options["look"]).split(",")
		var d := float(f[2]) if f.size() > 2 else 200.0
		rig.look_at_point(earth.ground_at(float(f[0]), float(f[1])), d)


## A centred message on a dark screen (while the engine starts).
func _notice(text: String) -> CanvasLayer:
	var layer := CanvasLayer.new()
	var back := ColorRect.new()
	back.color = Color(0.06, 0.05, 0.04)
	back.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(back)
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.set_anchors_preset(Control.PRESET_FULL_RECT)
	label.add_theme_font_size_override("font_size", 22)
	label.add_theme_color_override("font_color", Color(0.86, 0.72, 0.42))
	layer.add_child(label)
	add_child(layer)
	return layer


# --- playing on the real map ---------------------------------------------------------

func _build_hud() -> void:
	hud = GameHud.new()
	add_child(hud)
	game_menu = GameMenu.new()
	game_menu.bridge = bridge
	game_menu.audio = audio
	add_child(game_menu)
	hud.menu_requested.connect(game_menu.open_menu)
	hud.capital_requested.connect(_visit_capital)
	hud.city_requested.connect(func(id: String):  # fly down to a city to see it (D-127)
		for p in view["provinces"]:
			if p["id"] == id and p.get("latlon") != null:
				rig.fly_to(earth.ground_at(p["latlon"][0], p["latlon"][1]), 80.0)
				_select(id))
	hud.spoke.connect(func(): audio.play("speak"))
	game_menu.message.connect(func(text: String):
		hud.message = text
		hud.show_view(view))
	game_menu.loaded.connect(_on_loaded)
	game_menu.asked.connect(func(name: String):
		hud.set_tab("ideas")
		_on_idea(name, ""))
	game_menu.quit_to_title.connect(func():
		bridge.stop()
		get_tree().reload_current_scene())
	hud.action_requested.connect(_on_action)
	hud.armies_changed.connect(_draw_armies)
	hud.end_turn_requested.connect(_on_end_turn)
	hud.idea_submitted.connect(_on_idea)
	_refresh_dev()
	var court: Variant = bridge.request("settings")
	if court != null:
		hud.court_mode = "a language model rules" if court["online"] else "offline: the library of ideas rules"
	if options.has("tab"):
		hud.tab = str(options["tab"])
	if options.has("dilemma-demo"):  # --dilemma-demo: show a made-up dilemma (screenshots)
		view["dilemma"] = {"id": "demo", "title": "The sickness in the poor quarter",
			"text": "A fever spreads through the poorest streets of the capital. The physicians disagree about everything.",
			"choices": [{"label": "Close the quarter", "hint": "food -3%, unrest +6"},
				{"label": "Pray at the temples", "hint": "unrest +3, clergy +6"},
				{"label": "Let the physicians try", "hint": "wealth -4%, knowledge +8%"}]}
	hud.show_view(view)
	hud.speak(view.get("voices", []), true)
	if options.has("start"):
		_on_action({"kind": "start", "node_id": str(options["start"])})
	if options.has("breakthrough-demo"):  # --breakthrough-demo=idea: its card (screenshots)
		for idea in view.get("ideas", []):
			if str(idea["id"]) == str(options["breakthrough-demo"]):
				hud.show_breakthroughs([{"id": idea["id"], "name": idea["name"], "ahead": idea["ahead"], "history": idea["history"]}])
	if options.has("cities"):  # --cities[=province]: open the Cities screen (screenshots)
		hud.open_cities("" if str(options["cities"]) == "true" else str(options["cities"]))
	if options.has("notebook"):  # --notebook[=idea]: open the notebook (screenshots)
		hud.open_notebook("" if str(options["notebook"]) == "true" else str(options["notebook"]))
	if options.has("fold"):  # --fold: fold the waiting chapter away (screenshots)
		hud.fold_chapter()
	if options.has("choose"):  # --choose=N: answer the waiting chapter (screenshots)
		var block: Variant = view.get("chronicle")
		if block != null and block.get("chapter") != null:
			_on_action({"kind": "chapter", "chapter": str(block["chapter"]["id"]), "choice": int(options["choose"])})
	if options.has("war"):  # --war=civ: declare war (testing the turn replay)
		_on_action({"kind": "declare_war", "target": str(options["war"])})
	if options.has("raise"):  # --raise=province: raise an army there
		_on_action({"kind": "raise", "province": str(options["raise"]), "size": "large"})
	if options.has("march"):  # --march=province: the player's largest army marches there
		var best: Dictionary = {}
		for army in view.get("armies", []):
			if army["owner"] == view["player"] and (best.is_empty() or int(army["men"]) > int(best["men"])):
				best = army
		if not best.is_empty():
			_on_action({"kind": "march", "army": str(best["id"]), "target": str(options["march"])})
	for order in ["formation", "plan", "assault"]:  # --formation=id / --plan=id for the largest army (screenshots)
		if options.has(order):
			var biggest: Dictionary = {}
			for army in view.get("armies", []):
				if army["owner"] == view["player"] and (biggest.is_empty() or int(army["men"]) > int(biggest["men"])):
					biggest = army
			if not biggest.is_empty():
				_on_action({"kind": order, "army": str(biggest["id"]), order: str(options[order])})
	_quick_turns = true   # turns run from the command line are not played out on the map
	if options.has("build"):  # --build=province:building,... one a turn (screenshots)
		for order in str(options["build"]).split(","):
			var bits := order.split(":")
			_on_action({"kind": "build", "province": bits[0], "building": bits[1]})
			_on_end_turn()
	for i in int(options.get("play", "0")):
		_on_end_turn()
	_quick_turns = false
	if options.has("queue"):  # --queue=province:building,...: build or queue, no turn ends
		for order in str(options["queue"]).split(","):
			var bits := order.split(":")
			_on_action({"kind": "build", "province": bits[0], "building": bits[1]})
	if options.has("aid"):  # --aid=friend:attacker: come to a friend's aid (screenshots)
		var bits := str(options["aid"]).split(":")
		_on_action({"kind": "aid", "target": bits[0], "against": bits[1]})
	if options.has("tab"):
		hud.set_tab(str(options["tab"]))
	if options.has("side-scroll"):  # --side-scroll=px: scroll the side panel (screenshots)
		var body: Control = hud.get("_side_body")
		var scroller := body.get_parent().get_parent() as ScrollContainer
		if scroller != null:
			scroller.set_deferred("scroll_vertical", int(options["side-scroll"]))
	if options.has("open"):  # --open=build|levy|fleet: unfold part of the province card
		hud.open_box = str(options["open"])
	if options.has("select"):
		_select(str(options["select"]))
	if options.has("menu"):  # --menu=menu|save|load|chronicle|tree|settings (screenshots)
		var screen := str(options["menu"])
		game_menu.call("open_menu" if screen == "menu" else "open_" + screen)
	if options.has("dev"):
		hud.toggle_dev()
	if options.has("battles"):  # --battles: open the last turn's battle reports (screenshots)
		var fought: Array = []
		for e in view.get("events", []):
			if str(e["kind"]) in ["battle_won", "battle_lost"] and e.has("phases"):
				fought.append(e)
		print("battles: ", fought.size())
		if not fought.is_empty():
			hud.call("_show_battles", fought)
	if options.has("council"):  # --council: the council of war before the coming battles (screenshots)
		hud.show_council()
	if options.has("conquest"):  # --conquest: the triumph card for the last city taken (screenshots)
		var taken: Array = view.get("events", []).filter(func(e): return str(e["kind"]) == "spoils" and e.get("civ") == view["player"])
		if taken.is_empty():
			taken = [{"kind": "spoils", "spoils": {"wealth": 1840, "sacked": 12000, "stormed": true, "capital": false,
				"prestige_bp": 300, "veterancy_bp": 400, "army": "Eastern Army", "province": str(options["conquest"])}}]
		hud.show_conquests(taken)
	if options.has("outcome"):  # --outcome=victory|defeat: preview the end screen (screenshots)
		var won := str(options["outcome"]) != "defeat"
		hud.call("_show_outcome", {"result": "victory" if won else "defeat",
			"path": "economic" if won else "collapse", "year": view["year"]})
	if options.has("visit"):
		_visit_capital()
	if options.has("tour") or (not Tutorial.seen() and not options.has("smoke") and not options.has("screenshot")):
		var tour := Tutorial.new()
		tour.start_at = int(options.get("tour", "1")) - 1 if str(options.get("tour", "")).is_valid_int() else 0
		add_child(tour)
	if options.has("idea"):  # --idea=TEXT: propose an idea, as if typed (screenshots, tests)
		_on_idea(str(options["idea"]).replace("_", " "), "")
		while bridge.busy:
			await get_tree().process_frame
	if options.has("click"):  # --click=x,y: pick whatever is at that screen point
		await get_tree().process_frame
		var xy: PackedStringArray = str(options["click"]).split(",")
		var index := _pick(Vector2(float(xy[0]), float(xy[1])))
		print("clicked: ", "nothing" if index < 0 else provinces.sites[index]["id"])
		_select("" if index < 0 else str(provinces.sites[index]["id"]))


## The player's own words go to the court (the idea pipeline). The engine may consult a
## language model, which takes a few seconds, so this runs in the background.
func _on_idea(text: String, answer: String) -> void:
	if bridge.busy:
		return
	hud.set_deliberating(true)
	audio.play("click")
	bridge.request_async("idea", {"text": text, "answer": answer}, func(reply: Variant):
		hud.set_deliberating(false)
		if reply == null:
			hud.message = bridge.last_error
			hud.show_view(view)
			return
		hud.message = ""
		hud.dev_info["last ruling"] = "%s %s" % [reply.get("source", ""), reply.get("note", "")]
		hud.dev_info["last usage"] = str(reply.get("usage", {}))
		if reply.has("view"):
			view = reply["view"]
			hud.show_view(view)
		hud.show_rulings(reply)
		audio.play("idea")
		hud.speak(reply.get("voices", [])))


## Fly down to the player's capital, close enough to see what their ideas have built.
func _visit_capital() -> void:
	for p in view["provinces"]:
		if p["owner"] == view["player"] and p["capital"] and p["latlon"] != null:
			rig.fly_to(earth.ground_at(p["latlon"][0], p["latlon"][1]), 70.0)


## A saved game was loaded: redraw the map for it (a different region if need be).
func _on_loaded(new_view: Dictionary) -> void:
	view = new_view
	for child in holder.get_children():
		child.queue_free()
	earth = null
	provinces = null
	settlements = null
	await get_tree().process_frame
	_build_earth(holder, str(view["map"]))
	hud.rulings = []
	hud.show_view(view)
	hud.speak(view.get("voices", []), true)
	_refresh_dev()


func _refresh_dev() -> void:
	var court: Variant = bridge.request("settings")
	if court != null:
		hud.dev_info["court"] = court["status"]
		hud.dev_info["tokens this month"] = "%s (%d calls)" % [GameHud.number(int(court["tokens_this_month"])), int(court["calls_this_month"])]


func _on_action(action: Dictionary) -> void:
	if bridge.busy:
		return
	audio.play("click")
	var reply: Variant = bridge.request("act", {"action": action})
	if reply == null:
		hud.message = bridge.last_error
	else:
		hud.message = "" if reply["accepted"] else str(reply["message"])
		view = reply["view"]
		if reply["accepted"] and action["kind"] == "start":
			hud.tab = "projects"
		if reply["accepted"] and action["kind"] == "chapter":   # history may move borders (D-120)
			if provinces.update(view) and settlements != null:
				settlements.recolour()
			provinces.show_ties(view)
		if action["kind"] in ["raise", "march", "stance", "disband", "fortify", "dilemma", "envoy_answer",
				"build_fleet", "sail", "scuttle", "plan", "build", "spies", "hasten"]:
			hud.message = str(reply["message"])
			if reply["accepted"] and action["kind"] == "disband":
				hud.selected_army = ""
			if reply["accepted"] and action["kind"] == "scuttle":
				hud.selected_fleet = ""
		_draw_armies()
	hud.show_view(view)
	if reply != null:
		hud.speak(reply.get("voices", []))


func _on_end_turn() -> void:
	if bridge.busy or _replay != null:
		return
	audio.play("end_turn")
	hud.rulings = []
	var reply: Variant = bridge.request("end_turn")
	if reply == null:
		hud.message = bridge.last_error
	else:
		hud.message = ""
		view = reply
		var replay: Dictionary = view.get("replay", {})
		if TurnReplay.enabled() and TurnReplay.worth_showing(replay) and rig != null and not _quick_turns and not options.has("smoke"):
			# the turn plays out on the map before its results are shown (D-124)
			hud.set_replaying(true, int(view["year"]) - int(view.get("years_per_turn", 10)), int(view["year"]))
			provinces.hushed = true
			_last_pose = Transform3D()  # names look again
			rig.set_process_unhandled_input(false)
			_replay = TurnReplay.new()
			_earth_holder.add_child(_replay)
			await _replay.play(replay, provinces, rig, audio, _apply_turn_map)
			_replay = null
			rig.set_process_unhandled_input(true)
			provinces.hushed = false
			_last_pose = Transform3D()  # names look again
			hud.set_replaying(false)
		else:
			_apply_turn_map()
		var kinds: Array = view.get("events", []).map(func(e): return e["kind"])
		if "victory" in kinds:
			audio.play("victory")
		elif "war" in kinds:
			audio.play("war")
	hud.show_view(view)
	hud.speak(view.get("voices", []), true)
	if reply != null and not _quick_turns:
		hud.show_breakthroughs(view.get("replay", {}).get("breakthroughs", []))
		hud.show_conquests(view.get("events", []).filter(func(e): return str(e["kind"]) == "spoils" and e.get("civ") == view["player"]))


## The map as the turn left it: colours, cities, armies, ties and landmarks.
func _apply_turn_map() -> void:
	if provinces.update(view) and settlements != null:
		settlements.recolour()
	_grow_cities()
	_draw_armies()
	provinces.show_ties(view)
	landmarks.update(view)


## Cities that have grown, or raised new buildings, are built again, larger (D-111).
func _grow_cities() -> void:
	if settlements == null or _earth_holder == null:
		return
	var signature := provinces.growth_signature()
	if signature == _growth:
		return
	_growth = signature
	settlements.remove()
	settlements = Settlements.new(provinces)
	settlements.build(_earth_holder)
	scenery.clear(settlements.clearings)


func _draw_armies() -> void:
	if provinces != null:
		var chosen := hud.selected_army if hud != null else ""
		var ships := hud.selected_fleet if hud != null else ""
		provinces.show_armies(view.get("armies", []), view.get("battles", []), chosen,
			view.get("fleets", []), view.get("sea_battles", []), ships)
		if rig != null and rig.camera != null:
			provinces.declutter(rig.camera)


func _select(place_id: String) -> void:
	var mine: Array = view.get("armies", []).filter(func(a): return a["province"] == place_id and a["owner"] == view["player"])
	hud.selected_army = str(mine[0]["id"]) if not mine.is_empty() else ""
	var ships: Array = view.get("fleets", []).filter(func(f): return f["sea"] == place_id and f["owner"] == view["player"])
	hud.selected_fleet = str(ships[0]["id"]) if not ships.is_empty() else ""
	_draw_armies()
	hud.select(place_id)
	for index in provinces.sites.size():
		if provinces.sites[index]["id"] == place_id:
			provinces.outline(holder, index)
			return
	provinces.outline(holder, -1)


## The province or sea under a point on the screen, or -1.
func _pick(screen: Vector2) -> int:
	var camera := rig.camera
	var origin := camera.project_ray_origin(screen)
	var direction := camera.project_ray_normal(screen)
	if direction.y >= 0.0:
		return -1
	# March along the ray until it passes under the ground, then narrow it down.
	var step := maxf(rig.distance / 200.0, 0.5)
	var t := 0.0
	var previous := 0.0
	var hit := false
	for i in 3000:
		var p := origin + direction * t
		if p.y <= _ground_height(p):
			hit = true
			break
		previous = t
		t += step
	if not hit:
		return -1
	for i in 12:
		var middle := (previous + t) / 2.0
		var p := origin + direction * middle
		if p.y <= _ground_height(p):
			t = middle
		else:
			previous = middle
	var point := origin + direction * t
	return provinces.site_at(Vector2(point.x, point.z) + earth.size() / 2.0)


func _ground_height(point: Vector3) -> float:
	return maxf(earth.ground_at_pixel(Vector2(point.x, point.z) + earth.size() / 2.0).y, 0.0)


func _process(delta: float) -> void:
	if menus != null and earth != null:  # the title backdrop drifts slowly east
		rig.position.x += delta * 6.0
	if provinces != null:
		provinces.animate(Time.get_ticks_msec() / 1000.0, rig.distance)
		provinces.fade_labels(delta)
	if earth != null and rig != null:  # shadows sharp near the camera, wherever it is
		sun.directional_shadow_max_distance = clampf(rig.distance * 2.5, 60.0, 900.0)
	if earth != null:  # territory colours fade as you zoom in, so the land itself shows
		earth.terrain_material.set_shader_parameter("tint", lerpf(0.32, 0.05, rig.zoom_level()))
		earth.terrain_material.set_shader_parameter("edge_tint", lerpf(0.8, 0.12, smoothstep(0.35, 0.95, rig.zoom_level())))
	if provinces != null:
		var pose := rig.camera.global_transform
		if pose != _last_pose:  # names that would overlap give way as the camera moves
			_last_pose = pose
			provinces.declutter(rig.camera)


func _unhandled_input(event: InputEvent) -> void:
	if provinces == null:
		return
	if _replay != null:  # a click or key skips the turn's replay
		if (event is InputEventMouseButton or event is InputEventKey) and event.pressed:
			_replay.skip()
			get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			if game_menu.is_open():
				game_menu.close()
			else:
				game_menu.open_menu()
			return
		if event.keycode == KEY_F3:
			hud.toggle_dev()
			return
		if game_menu.is_open():
			return
		# shortcuts (typing in the idea box never reaches here: the box takes its keys)
		if event.keycode in [KEY_ENTER, KEY_KP_ENTER] and not hud.deliberating and hud.can_end_turn():
			hud.request_end_turn()   # a council of war first, if battles are coming (D-273)
			return
		if event.keycode == KEY_N:  # the notebook from the future (D-126)
			hud.open_notebook()
			return
		if event.keycode == KEY_C:  # your cities (D-127)
			hud.open_cities()
			return
		var tabs := {KEY_1: "ideas", KEY_2: "projects", KEY_3: "world"}
		if tabs.has(event.keycode):
			hud.set_tab(tabs[event.keycode])
			return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_press_at = event.position
		elif event.position.distance_to(_press_at) < 6.0:  # a click, not a drag
			var index := _pick(event.position)
			var place := "" if index < 0 else str(provinces.sites[index]["id"])
			if hud.marching_army != "" and place != "":
				var army := hud.marching_army
				hud.marching_army = ""
				_on_action({"kind": "march", "army": army, "target": place, "forced": hud.forced_march})
				hud.forced_march = false
				return
			if hud.sailing_fleet != "" and place != "":
				var fleet := hud.sailing_fleet
				hud.sailing_fleet = ""
				# a click on a coastal province means the sea on its shore
				var sea := place if provinces.sites[index]["sea"] else hud.port_of(place)
				_on_action({"kind": "sail", "fleet": fleet, "sea": sea if sea != "" else place})
				return
			_select(place)
	elif event is InputEventMouseMotion and not event.button_mask:
		var index := _pick(event.position)
		var text := ""
		if index >= 0:
			var site: Dictionary = provinces.sites[index]
			text = str(site["name"])
			if site["owner"] != null:
				text += " · " + str(provinces.civ_names[site["owner"]])
		hud.show_hover(text, event.position)


func _setup_environment() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.22, 0.40, 0.66)
	sky_material.sky_horizon_color = Color(0.78, 0.74, 0.66)
	sky_material.ground_horizon_color = Color(0.55, 0.52, 0.48)
	var sky := Sky.new()
	sky.sky_material = sky_material
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.35
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	environment.tonemap_exposure = 0.9
	environment.fog_enabled = true
	environment.fog_light_color = Color(0.78, 0.76, 0.72)
	environment.fog_density = 0.00025
	# colour grading for a bright storybook map (G1); global illumination (SDFGI) washed the
	# colours out on the Mac, so the light stays simple
	environment.adjustment_enabled = true
	environment.adjustment_saturation = 1.06
	environment.adjustment_contrast = 1.06
	if RenderingServer.get_current_rendering_method() == "forward_plus":
		environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		environment.tonemap_exposure = 0.92
		environment.adjustment_saturation = 1.12
		environment.ssao_enabled = true
		environment.ssao_intensity = 1.2
		environment.ssao_radius = 2.0
		environment.glow_enabled = true
		environment.glow_intensity = 0.35
		environment.glow_bloom = 0.04
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	add_child(world_environment)
	sun.rotation_degrees = Vector3(-32, 55, 0)
	sun.light_color = Color(1.0, 0.92, 0.80)
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 1500.0
	sun.shadow_bias = 0.08
	sun.shadow_normal_bias = 1.5
	add_child(sun)


## A made-up turn for screenshots: the player's largest army marches into `target`, wins a
## battle against its owner there and takes it.
func _demo_replay(target: String) -> void:
	var best: Dictionary = {}
	for army in view.get("armies", []):
		if army["owner"] == view["player"] and (best.is_empty() or int(army["men"]) > int(best["men"])):
			best = army
	var owner := ""
	for p in view["provinces"]:
		if p["id"] == target:
			owner = str(p["owner"])
	var name := provinces.province_name(target)
	var replay := {
		"marches": [{"id": best["id"], "owner": view["player"], "from": best["province"], "road": [target], "mine": true}],
		"battles": [{"at": target, "name": "Battle of " + name, "winner": view["player"], "loser": owner, "mine": true, "won": true,
			"storm": options.has("replay-storm")}],
		"skirmishes": [], "lost": [], "raised": [],
		"sieges": [{"at": target, "by": view["player"], "held_by": owner, "progress": 45, "mine": true}],
		"taken": [{"at": target, "from": owner, "to": view["player"], "mine": true, "how": "stormed" if options.has("replay-storm") else ""}],
	}
	hud.set_replaying(true, int(view["year"]), int(view["year"]) + 10)
	provinces.hushed = true
	_last_pose = Transform3D()  # names look again
	_replay = TurnReplay.new()
	_earth_holder.add_child(_replay)
	await _replay.play(replay, provinces, rig, audio, func() -> void: pass)
	_replay = null
	provinces.hushed = false
	_last_pose = Transform3D()  # names look again
	hud.set_replaying(false)


func _take_screenshot(path: String) -> void:
	for i in 4:
		await get_tree().process_frame
	if options.has("hover"):  # --hover=x,y: rest the mouse there so its tooltip shows (screenshots)
		var xy: PackedStringArray = str(options["hover"]).split(",")
		var at := Vector2(float(xy[0]), float(xy[1]))
		for step in 6:
			Input.warp_mouse(at + Vector2(step, 0))
			await get_tree().process_frame
		var waited := 0.0
		while waited < 1.2:
			await get_tree().process_frame
			waited += get_process_delta_time()
	if options.has("replay-shots"):  # --replay-shots=t1,t2,...: pictures as the next turn plays
		if options.has("replay-demo"):  # --replay-demo=province: a made-up turn there (screenshots)
			_demo_replay(str(options["replay-demo"]))
		else:
			_on_end_turn()   # (game time, so run with --fixed-fps where frames are slow)
		var elapsed := 0.0
		for t in str(options["replay-shots"]).split(","):
			while elapsed < float(t):
				await get_tree().process_frame
				elapsed += get_process_delta_time()
			get_viewport().get_texture().get_image().save_png(path.replace(".png", "_t%s.png" % t))
		bridge.stop()
		get_tree().quit()
		return
	if options.has("filmstrip"):  # --filmstrip=d1,d2,...: one picture per camera distance
		var centre := rig.position
		for d in str(options["filmstrip"]).split(","):
			rig.look_at_point(centre, float(d))
			provinces.declutter(rig.camera)
			for i in 30:  # long enough for names to finish fading
				await get_tree().process_frame
			get_viewport().get_texture().get_image().save_png(path.replace(".png", "_%s.png" % d))
		bridge.stop()
		get_tree().quit()
		return
	if options.has("perf"):  # --perf: what this view costs to draw, measured over 30 frames
		var worst := 0.0
		for i in 30:
			await get_tree().process_frame
			worst = maxf(worst, Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0)
		print("PERF draw_calls=%d primitives=%d objects=%d process_ms=%.1f worst_process_ms=%.1f nodes=%d mem_mb=%.0f" % [
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
			Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, worst,
			Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
			Performance.get_monitor(Performance.MEMORY_STATIC) / 1048576.0])
		if options.has("perf-parts"):  # --perf-parts: what each part of the world costs
			var total: float = Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
			var parts: Array = []
			for child in holder.get_children():
				for sub in ([child] + (child.get_children() if child.get_child_count() <= 12 else [])):
					if sub is Node3D and (sub as Node3D).visible:
						parts.append(sub)
			for part in parts:
				(part as Node3D).visible = false
				for i in 3:
					await get_tree().process_frame
				var without: float = Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
				(part as Node3D).visible = true
				if total - without > 200000.0:
					print("PERF part %s: %.1fM primitives" % [part.get_path(), (total - without) / 1e6])
			for i in 3:
				await get_tree().process_frame
	if options.has("no-ui"):  # --no-ui: the map alone, every panel and card hidden (screenshots)
		for layer in get_tree().root.find_children("*", "CanvasLayer", true, false):
			(layer as CanvasLayer).hide()
		for control in get_tree().root.find_children("*", "Control", true, false):
			(control as Control).hide()
		for i in 3:
			await get_tree().process_frame
	get_viewport().get_texture().get_image().save_png(path)
	bridge.stop()
	get_tree().quit()


func _exit_tree() -> void:
	bridge.stop()
	UiStyle.release()
	Lod.release()


## Buttons swell a little under the mouse and give when pressed (D-274), from their middle.
func _lively(button: Button) -> void:
	if button.has_meta("lively"):
		return
	button.set_meta("lively", true)
	var centre := func() -> void: button.pivot_offset = button.size / 2.0
	button.resized.connect(centre)
	var to := func(scale: float, seconds: float) -> void:
		if not is_instance_valid(button) or not button.is_inside_tree():
			return
		centre.call()
		var tween := button.create_tween()
		tween.tween_property(button, "scale", Vector2.ONE * scale, seconds).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	button.mouse_entered.connect(func() -> void:
		if not button.disabled:
			to.call(1.04, 0.15))
	button.mouse_exited.connect(func() -> void: to.call(1.0, 0.15))
	button.button_down.connect(func() -> void: to.call(0.95, 0.08))
	button.button_up.connect(func() -> void: to.call(1.04 if button.is_hovered() else 1.0, 0.18))


func _wrap_tip(node: Node) -> void:
	if is_instance_valid(node):
		var control := node as Control
		if control.tooltip_text.length() > 60:
			control.tooltip_text = UiStyle.wrap_tip(control.tooltip_text)

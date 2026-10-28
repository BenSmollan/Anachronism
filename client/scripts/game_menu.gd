## The in-game menu and its screens (brief §11): save and load, settings (the language
## model's status and the offline switch), the chronicle of everything that has happened,
## the tech tree with goal stubs, and a way back to the title screen.
##
## Screens ask the engine for what they show each time they open, so they never hold state.
class_name GameMenu
extends CanvasLayer

signal loaded(view: Dictionary)      ## a saved game was loaded
signal quit_to_title
signal message(text: String)
signal asked(idea_name: String)   ## the player clicked an idea in the tech tree

var bridge: EngineBridge
var audio: GameAudio
var _root := Control.new()
var _modal: Control


func _ready() -> void:
	layer = 5
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UiStyle.theme()
	add_child(_root)


func is_open() -> bool:
	return _modal != null


func close() -> void:
	if _modal != null:
		_modal.queue_free()
		_modal = null


## The main menu: a column of big buttons.
func open_menu() -> void:
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	for entry in [["Save game", open_save], ["Load game", open_load], ["Chronicle", open_chronicle],
			["Charts", open_charts], ["Tech tree", open_tree], ["Settings", open_settings], ["Quit to title", func():
				close()
				quit_to_title.emit()]]:
		var button := UiStyle.big_button(entry[0], 22, UiStyle.GOLD if entry[0] != "Quit to title" else Color(0.85, 0.8, 0.7))
		button.custom_minimum_size = Vector2(320, 56)
		button.pressed.connect(entry[1])
		body.add_child(button)
	_open("Menu", body, Vector2(380, 0))


func open_save() -> void:
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	body.add_child(UiStyle.label("Name your save (letters, digits, - and _):", 16, UiStyle.INK_SOFT))
	var name := LineEdit.new()
	name.text = "save_%s" % Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_")
	name.custom_minimum_size = Vector2(420, 44)
	name.add_theme_font_size_override("font_size", 18)
	body.add_child(name)
	var result := UiStyle.label("", 15, UiStyle.RED)
	var go := UiStyle.big_button("SAVE", 22)
	go.pressed.connect(func():
		var reply: Variant = bridge.request("save", {"name": name.text.strip_edges()})
		if reply == null:
			result.text = bridge.last_error
		else:
			close()
			message.emit("Saved as %s." % name.text.strip_edges()))
	body.add_child(go)
	body.add_child(result)
	_open("Save game", body, Vector2(480, 0))


func open_load() -> void:
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 6)
	var reply: Variant = bridge.request("saves")
	var saves: Array = reply["saves"] if reply != null else []
	if saves.is_empty():
		body.add_child(UiStyle.label("No saved games yet.", 17, UiStyle.INK_SOFT))
	for save in saves:
		var row := HBoxContainer.new()
		var label := UiStyle.label(str(save["name"]), 18, UiStyle.INK, "body", 700)
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(label)
		row.add_child(UiStyle.label(Time.get_datetime_string_from_unix_time(int(save["modified"])).replace("T", " "), 13, UiStyle.INK_SOFT))
		var load_button := UiStyle.big_button("LOAD", 16)
		load_button.pressed.connect(func():
			var view: Variant = bridge.request("load", {"name": save["name"]})
			if view == null:
				message.emit(bridge.last_error)
				return
			close()
			loaded.emit(view))
		row.add_child(load_button)
		body.add_child(row)
	_open("Load game", body, Vector2(560, 0), true)


func open_settings() -> void:
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	var reply: Variant = bridge.request("settings")
	if reply == null:
		body.add_child(UiStyle.label(bridge.last_error, 16, UiStyle.RED))
		_open("Settings", body, Vector2(620, 0))
		return
	if str(reply.get("difficulty", "")) != "":
		body.add_child(UiStyle.label("This game", 20, UiStyle.RED, "title", 800))
		body.add_child(UiStyle.wrapped("Difficulty: %s (chosen when the game began)" % str(reply["difficulty"]).capitalize(), 15, UiStyle.INK_SOFT, 580))
	var court := "Free Thought: a language model rules on your ideas" if reply["online"] else "Historical Advisors: your ideas are matched against the library"
	body.add_child(UiStyle.label("How your ideas are judged", 20, UiStyle.RED, "title", 800))
	body.add_child(UiStyle.wrapped(court, 17, UiStyle.INK, 580))
	body.add_child(UiStyle.wrapped("Status: %s" % reply["status"], 15, UiStyle.INK_SOFT, 580))
	body.add_child(UiStyle.wrapped("API key: %s   ·   Model: %s" % ["found" if reply["has_key"] else "not set", reply["model"] if reply["model"] != "" else "not chosen"], 15, UiStyle.INK_SOFT, 580))
	body.add_child(UiStyle.wrapped("Tokens used this month: %s of %s (%d calls)" % [GameHud.number(int(reply["tokens_this_month"])), GameHud.number(int(reply["monthly_tokens"])) if int(reply["monthly_tokens"]) > 0 else "no cap", int(reply["calls_this_month"])], 15, UiStyle.INK_SOFT, 580))
	var offline := CheckBox.new()
	offline.text = "Play offline even when a key is set"
	offline.button_pressed = bool(reply["offline"])
	offline.add_theme_font_size_override("font_size", 16)
	offline.toggled.connect(func(on: bool):
		bridge.request("settings", {"offline": on})
		close()
		open_settings())
	body.add_child(offline)
	var tour := UiStyle.big_button("Show the guided tour again", 15, Color(0.85, 0.8, 0.7))
	tour.pressed.connect(func():
		close()
		get_parent().add_child(Tutorial.new()))
	body.add_child(tour)
	body.add_child(UiStyle.label("The screen", 20, UiStyle.RED, "title", 800))
	var sizes := HBoxContainer.new()
	sizes.add_theme_constant_override("separation", 8)
	var caption := UiStyle.label("Interface size", 16, UiStyle.INK)
	sizes.add_child(caption)
	var scale_script := preload("res://scripts/ui_scale.gd")
	for picked in scale_script.CHOICES:
		var b := UiStyle.big_button(str(scale_script.NAMES[picked]), 15, UiStyle.GOLD if scale_script.choice() == picked else Color(0.85, 0.8, 0.7))
		b.tooltip_text = "Auto keeps text readable on small windows; Larger and Largest make the whole interface bigger."
		b.pressed.connect(func():
			scale_script.set_choice(picked, get_tree().root)
			close()
			open_settings())
		sizes.add_child(b)
	body.add_child(sizes)
	body.add_child(UiStyle.label("The map", 20, UiStyle.RED, "title", 800))
	var replay := CheckBox.new()
	replay.text = "Play each turn out on the map (marches, battles, conquests)"
	replay.button_pressed = TurnReplay.enabled()
	replay.add_theme_font_size_override("font_size", 16)
	replay.toggled.connect(TurnReplay.set_enabled)
	body.add_child(replay)
	var shake := CheckBox.new()
	shake.text = "Shake the camera at great moments (battles, conquests, breakthroughs)"
	shake.button_pressed = CameraRig.shake_enabled()
	shake.add_theme_font_size_override("font_size", 16)
	shake.toggled.connect(CameraRig.set_shake_enabled)
	body.add_child(shake)
	if audio != null:
		body.add_child(UiStyle.label("Sound", 20, UiStyle.RED, "title", 800))
		var music := CheckBox.new()
		music.text = "Music"
		music.button_pressed = audio.music_on
		music.add_theme_font_size_override("font_size", 16)
		music.toggled.connect(audio.set_music)
		body.add_child(music)
		var effects := CheckBox.new()
		effects.text = "Sound effects"
		effects.button_pressed = audio.effects_on
		effects.add_theme_font_size_override("font_size", 16)
		effects.toggled.connect(audio.set_effects)
		body.add_child(effects)
	body.add_child(UiStyle.label("To switch the model on", 20, UiStyle.RED, "title", 800))
	body.add_child(UiStyle.wrapped("Put your Anthropic API key and a model name in this file, then restart the game:\n%s\n\nANTHROPIC_API_KEY=your-key\nANACHRONISM_MODEL=a model name from docs.claude.com" % reply["env_file"], 14, UiStyle.INK_SOFT, 580))
	body.add_child(UiStyle.wrapped("Press F3 during play for the developer overlay.", 13, UiStyle.INK_SOFT, 580))
	_open("Settings", body, Vector2(640, 0))


func open_chronicle() -> void:
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 4)
	var reply: Variant = bridge.request("chronicle")
	var entries: Array = reply["entries"] if reply != null else []
	var told: Array = reply.get("chapters", []) if reply != null else []
	if entries.is_empty():
		body.add_child(UiStyle.label("Nothing has happened yet. History is waiting.", 17, UiStyle.INK_SOFT))
	if not told.is_empty():
		body.add_child(UiStyle.label("The story so far", 22, UiStyle.RED, "title", 800))
		for chapter in told:
			body.add_child(UiStyle.label(str(chapter["title"]), 16, UiStyle.INK, "title", 700))
			body.add_child(UiStyle.wrapped(str(chapter["text"]), 15, UiStyle.INK, 660))
		body.add_child(UiStyle.label("Year by year", 22, UiStyle.RED, "title", 800))
	var year: Variant = null
	entries.reverse()  # newest first
	for entry in entries:
		if entry["year"] != year:
			year = entry["year"]
			body.add_child(UiStyle.label(GameHud.year_text(int(year)), 19, UiStyle.RED, "title", 800))
		var colour := UiStyle.INK if entry["mine"] else UiStyle.INK_SOFT
		body.add_child(UiStyle.wrapped("• " + str(entry["message"]), 15, colour, 660))
	_open("Chronicle", body, Vector2(720, 0), true)


func open_charts() -> void:
	var reply: Variant = bridge.request("history")
	if reply == null:
		message.emit(bridge.last_error)
		return
	var turns: Array = reply["player"]
	var years: Array = turns.map(func(t): return t["year"])
	var pick := func(field: String) -> Array: return turns.map(func(t): return t[field])
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 20)
	grid.add_theme_constant_override("v_separation", 14)
	var charts := [
		["Your people", [["People", Color(0.2, 0.45, 0.8), pick.call("population")]], false],
		["Your stores", [["Food", Color(0.85, 0.38, 0.18), pick.call("food")], ["Materials", Color(0.5, 0.45, 0.4), pick.call("materials")],
			["Wealth", Color(0.9, 0.75, 0.2), pick.call("wealth")], ["Knowledge", Color(0.3, 0.55, 0.3), pick.call("knowledge")]], false],
		["Your society", [["Literacy", Color(0.2, 0.5, 0.7), pick.call("literacy_bp")], ["Unrest", Color(0.8, 0.3, 0.15), pick.call("unrest_bp")],
			["Legitimacy", Color(0.85, 0.65, 0.1), pick.call("legitimacy_bp")], ["Suspicion", Color(0.45, 0.3, 0.6), pick.call("suspicion_bp")]], true],
	]
	var biggest: Array = reply["populations"].keys()
	biggest.sort_custom(func(a, b): return reply["populations"][a][-1] > reply["populations"][b][-1])
	var states: Array = []
	for civ_id in biggest.slice(0, 5):
		states.append([str(civ_id).capitalize().replace("_", " "), Color.from_hsv(float(states.size()) / 5.0, 0.6, 0.75), reply["populations"][civ_id]])
	charts.append(["The largest states", states, false])
	for entry in charts:
		var chart := Charts.new()
		chart.setup(entry[0], years, entry[1], entry[2])
		grid.add_child(chart)
	_open("Charts", grid, Vector2(1320, 0))


func open_tree() -> void:
	var reply: Variant = bridge.request("tree")
	if reply == null:
		message.emit(bridge.last_error)
		return
	var tree := TechTree.new()
	tree.setup(reply["nodes"], int(reply["year"]))
	tree.asked.connect(func(name: String):
		close()
		asked.emit(name))
	var legend := HBoxContainer.new()
	legend.add_theme_constant_override("separation", 18)
	for entry in [["In use", TechTree.ADOPTED], ["Being tried", TechTree.TRYING], ["Known idea", TechTree.KNOWN],
			["Goal", TechTree.GOAL], ["Needs a ruling", TechTree.STUB], ["Unknown", TechTree.UNKNOWN]]:
		var chip := ColorRect.new()
		chip.color = entry[1]
		chip.custom_minimum_size = Vector2(18, 18)
		legend.add_child(chip)
		legend.add_child(UiStyle.label(entry[0], 14, UiStyle.INK_SOFT))
	var body := VBoxContainer.new()
	body.add_child(legend)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(1360, 640)
	scroll.add_child(tree)
	body.add_child(scroll)
	_open("Tech tree", body, Vector2(1420, 0))


## A cream panel in the middle of the screen with a title and a close button.
func _open(title: String, content: Control, width: Vector2, scrolls := false) -> void:
	close()
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0, 0, 0, 0.45)
	shade.gui_input.connect(func(event: InputEvent):
		if event is InputEventMouseButton and event.pressed:
			close())
	_modal = shade
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	panel.custom_minimum_size = width
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	var head := HBoxContainer.new()
	var heading := UiStyle.label(title, 30, UiStyle.RED, "title", 900)
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(heading)
	var shut := UiStyle.big_button("✕", 18, Color(0.85, 0.8, 0.7))
	shut.pressed.connect(close)
	head.add_child(shut)
	column.add_child(head)
	var room := get_viewport().get_visible_rect().size
	panel.custom_minimum_size.x = minf(width.x, room.x - 40.0)
	var scroll := ScrollContainer.new()   # anything taller than the screen scrolls (D-276)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.add_child(content)
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_child(scroll)
	var tallest := room.y - 170.0
	if scrolls:
		scroll.custom_minimum_size = Vector2(panel.custom_minimum_size.x - 40, minf(560.0, tallest))
	else:
		var fit := func() -> void:
			if is_instance_valid(scroll) and is_instance_valid(content):
				scroll.custom_minimum_size = Vector2(0, minf(content.get_combined_minimum_size().y, tallest))
		fit.call_deferred()
	panel.add_child(column)
	shade.add_child(panel)
	_root.add_child(shade)

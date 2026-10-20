## The screens before a game: the title screen and the year picker.
##
## The player always plays Rome (D-286). The picker shows one Roman-styled card per Rome
## scenario the engine lists (year, title, pitch); pick a year, then BEGIN.
class_name Menus
extends CanvasLayer

signal start_requested(scenario_id: String, civ_id: String, difficulty: String, chronicle: bool)
signal quit_requested
signal continue_requested   ## resume the autosaved game

var catalog: Array = []        ## real-map scenarios from the engine's "scenarios" command
var scenario: Dictionary = {}
var civ: Dictionary = {}

var _root := Control.new()


func _ready() -> void:
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = UiStyle.theme()
	add_child(_root)


var can_continue := false   ## an autosaved game exists
var difficulty := "normal"  ## chosen in the picker; kept while browsing moments
var chronicle := true   ## follow history in chapters (D-120), where the state has them


func show_title() -> void:
	_clear()
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.05, 0.03, 0.02, 0.35)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(shade)
	var column := VBoxContainer.new()
	column.set_anchors_preset(Control.PRESET_CENTER)
	column.grow_horizontal = Control.GROW_DIRECTION_BOTH
	column.grow_vertical = Control.GROW_DIRECTION_BOTH
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	column.add_theme_constant_override("separation", 14)
	var title := UiStyle.headline("MERITUS", 96, UiStyle.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(title)
	var tagline := UiStyle.headline("Guide Rome, 509 to 27 BC, with ideas ahead of their time", 26, UiStyle.CREAM)
	tagline.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(tagline)
	# which build this is, so old downloads can be told from new ones (written by package.sh)
	var stamp := FileAccess.get_file_as_string("res://engine_src/VERSION").strip_edges()
	var version := UiStyle.headline(stamp if stamp != "" else "Development build", 20, Color(0.85, 0.80, 0.70))
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(version)
	var gap := Control.new()
	gap.custom_minimum_size.y = 40
	column.add_child(gap)
	var entries := [["NEW GAME", show_disclaimer, UiStyle.GOLD], ["QUIT", func(): quit_requested.emit(), Color(0.85, 0.80, 0.70)]]
	if can_continue:
		entries.push_front(["CONTINUE", func(): continue_requested.emit(), UiStyle.GOLD])
	for entry in entries:
		var button := UiStyle.big_button(entry[0], 30, entry[2])
		button.custom_minimum_size = Vector2(340, 70)
		button.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		button.pressed.connect(entry[1])
		column.add_child(button)
	_root.add_child(column)
	var credit := UiStyle.label("Map: Mapzen Terrain Tiles · NASA Blue Marble · Natural Earth   ·   Models: Kenney (CC0)   ·   Heraldry: game-icons.net by Lorc, Delapouite and others (CC BY 3.0)", 13, Color(1, 1, 1, 0.7))
	credit.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	credit.position = Vector2(16, -30)
	credit.offset_top = -30
	credit.offset_left = 16
	_root.add_child(credit)


## Before play (brief §8): this is a good-faith simulation, not a re-enactment.
func show_disclaimer() -> void:
	_clear()
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.05, 0.03, 0.02, 0.6)
	_root.add_child(shade)
	var card := PanelContainer.new()
	card.set_anchors_preset(Control.PRESET_CENTER)
	card.grow_horizontal = Control.GROW_DIRECTION_BOTH
	card.grow_vertical = Control.GROW_DIRECTION_BOTH
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	column.add_child(UiStyle.label("A word before you begin", 36, UiStyle.RED, "title", 900))
	for text in [
		"Meritus is a good-faith simulation of history, not an exact re-enactment. Its peoples, places and rulers are real, but borders, populations, dates and temperaments are simplified from general sources, and some are informed guesses.",
		"From the moment you start, history is yours to change. The rival states follow what they really intended - until your ideas reach them. What happens after that is invention.",
		"When a language model helps judge your ideas, its words are fiction written for the game; the game's own rules decide what is possible.",
	]:
		column.add_child(UiStyle.wrapped(text, 20, UiStyle.INK, 760))
	var row := HBoxContainer.new()
	var back := UiStyle.big_button("BACK", 20, Color(0.85, 0.80, 0.70))
	back.pressed.connect(show_title)
	row.add_child(back)
	var push := Control.new()
	push.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(push)
	var go := UiStyle.big_button("I UNDERSTAND", 26)
	go.custom_minimum_size = Vector2(300, 64)
	go.pressed.connect(func(): show_picker())
	row.add_child(go)
	column.add_child(row)
	card.add_child(column)
	_root.add_child(card)


const ROME := "rome"
const SENATE_RED := Color(0.36, 0.05, 0.06)
const SENATE_RED_DARK := Color(0.16, 0.02, 0.03)


## Pick a starting year for Rome. The catalogue is whatever the engine lists for Rome, so a
## new Rome scenario simply appears as one more card. `scenario_id` preselects a card.
func show_picker(scenario_id := "", _civ_id := "") -> void:
	if catalog.is_empty():
		return
	scenario = catalog[0]
	for s in catalog:
		if s["id"] == scenario_id:
			scenario = s
	civ = _rome_of(scenario)
	_draw_picker()


## Rome's entry in a scenario (the player's civilisation is always Rome).
func _rome_of(s: Dictionary) -> Dictionary:
	for c in s["civs"]:
		if c["id"] == ROME:
			return c
	return s["civs"][0]


func _draw_picker() -> void:
	_clear()
	var back := ColorRect.new()
	back.set_anchors_preset(Control.PRESET_FULL_RECT)
	back.color = SENATE_RED_DARK
	_root.add_child(back)
	var glow := ColorRect.new()  # a deep red wash fading to dark at the foot
	glow.set_anchors_preset(Control.PRESET_FULL_RECT)
	var gradient := Gradient.new()
	gradient.set_color(0, Color(SENATE_RED, 1.0))
	gradient.set_color(1, Color(SENATE_RED_DARK, 1.0))
	var wash := GradientTexture2D.new()
	wash.gradient = gradient
	wash.fill_from = Vector2(0.5, 0.0)
	wash.fill_to = Vector2(0.5, 1.0)
	var wash_rect := TextureRect.new()
	wash_rect.texture = wash
	wash_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	wash_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	wash_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(wash_rect)
	var frame := MarginContainer.new()
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right"]:
		frame.add_theme_constant_override("margin_" + side, 40)
	frame.add_theme_constant_override("margin_top", 22)
	frame.add_theme_constant_override("margin_bottom", 24)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	frame.add_child(column)
	_root.add_child(frame)
	# SPQR header
	var spqr := UiStyle.headline("S · P · Q · R", 64, UiStyle.GOLD)
	spqr.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(spqr)
	column.add_child(_gold_rule())
	var ask := UiStyle.headline("CHOOSE THE YEAR OF ROME", 30, UiStyle.CREAM)
	ask.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(ask)
	# one card per Rome scenario, side by side; scrolls sideways when there are many
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var cards := HBoxContainer.new()
	cards.add_theme_constant_override("separation", 18)
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cards.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	for s in catalog:
		cards.add_child(_year_card(s))
	scroll.add_child(cards)
	column.add_child(scroll)
	# keep the chosen card in view
	var index := maxi(0, catalog.find(scenario))
	get_tree().process_frame.connect(func() -> void:
		if is_instance_valid(scroll) and is_instance_valid(cards) and index < cards.get_child_count():
			scroll.ensure_control_visible(cards.get_child(index)), CONNECT_ONE_SHOT)
	column.add_child(_gold_rule())
	column.add_child(_picker_footer())


## The scenario's name without a trailing year ("Rome and Carthage, 264 BC" -> "Rome and Carthage"),
## since the year is the card's heading.
func _title_of(s: Dictionary) -> String:
	var name := str(s["name"])
	var year := GameHud.year_text(int(s["start_year"]))
	if name.ends_with(", " + year):
		name = name.trim_suffix(", " + year)
	return name


## A thin gold line.
func _gold_rule() -> Control:
	var rule := ColorRect.new()
	rule.color = UiStyle.GOLD_DARK
	rule.custom_minimum_size.y = 3
	return rule


## One starting year as a card: the year large, then the title and Rome's pitch.
func _year_card(s: Dictionary) -> Control:
	var rome := _rome_of(s)
	var chosen: bool = s["id"] == scenario["id"]
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(380, 470)
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	card.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	var fill := Color(0.50, 0.08, 0.09) if chosen else Color(0.30, 0.05, 0.06)
	var box := UiStyle.panel(fill, UiStyle.GOLD if chosen else UiStyle.GOLD_DARK, 8)
	var border := 5 if chosen else 2
	box.set_border_width_all(border)
	box.set_content_margin_all(18)
	card.add_theme_stylebox_override("panel", box)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 8)
	body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(body)
	var year := UiStyle.headline(GameHud.year_text(int(s["start_year"])), 54, UiStyle.GOLD)
	year.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.add_child(year)
	body.add_child(_gold_rule())
	var title := UiStyle.label(_title_of(s).to_upper(), 20, UiStyle.CREAM, "title", 800)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.custom_minimum_size.x = 340
	body.add_child(title)
	var pitch_text := str(rome.get("pitch", ""))
	if pitch_text != "":
		var pitch := UiStyle.wrapped(pitch_text, 16, Color(0.98, 0.90, 0.62), 340)
		pitch.add_theme_font_override("font", UiStyle.font("body", 800))
		pitch.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		body.add_child(pitch)
	if str(s["description"]).strip_edges() != "":
		var story := UiStyle.wrapped(str(s["description"]), 14, Color(0.93, 0.86, 0.78), 340)
		story.max_lines_visible = 8
		story.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		body.add_child(story)
	var fill_space := Control.new()
	fill_space.size_flags_vertical = Control.SIZE_EXPAND_FILL
	fill_space.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.add_child(fill_space)
	var facts := UiStyle.label("%s   ·   %d provinces" % [GameHud.people(int(rome["population"])), int(rome["provinces"])],
		15, UiStyle.GOLD, "body", 800)
	facts.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	facts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.add_child(facts)
	for child in body.get_children():
		child.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			if chosen and event.double_click:
				_begin()
			else:
				show_picker(str(s["id"])))
	return card


## Back, difficulty, history mode and the gold BEGIN button.
func _picker_footer() -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var back_button := UiStyle.big_button("BACK", 20, Color(0.85, 0.80, 0.70))
	back_button.pressed.connect(show_title)
	row.add_child(back_button)
	var push := Control.new()
	push.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(push)
	var chapters := int(civ.get("chronicle", 0))
	if chapters > 0:
		# chronicle mode: live through the real history, chapter by chapter, and try to outdo it
		for follow in [true, false]:
			var label := ("FOLLOW HISTORY · %d chapters" % chapters) if follow else "FREE PLAY"
			var way := UiStyle.big_button(label, 16, UiStyle.GOLD if chronicle == follow else Color(0.85, 0.80, 0.70))
			way.custom_minimum_size = Vector2(260, 44)
			way.tooltip_text = ("Live through what really happened, chapter by chapter. Your goal is not to win but to outdo history." if follow
				else "The same moment with no chapters: history is only what you and the rivals make it.")
			way.pressed.connect(func():
				chronicle = follow
				_draw_picker())
			row.add_child(way)
		var gap := Control.new()
		gap.custom_minimum_size.x = 16
		row.add_child(gap)
	# difficulty: how bold the rivals are and how forgiving the opening turns
	var tips := {"easy": "Gentler rivals, slower conquests, five quiet turns to start",
		"normal": "The game as designed", "hard": "Bolder rivals, faster conquests, no grace"}
	for level in ["easy", "normal", "hard"]:
		var pick := UiStyle.big_button(level.to_upper(), 16, UiStyle.GOLD if level == difficulty else Color(0.85, 0.80, 0.70))
		pick.custom_minimum_size = Vector2(96, 44)
		pick.tooltip_text = tips[level]
		pick.pressed.connect(func():
			difficulty = level
			_draw_picker())
		row.add_child(pick)
	var gap2 := Control.new()
	gap2.custom_minimum_size.x = 16
	row.add_child(gap2)
	var begin := UiStyle.big_button("BEGIN", 32)
	begin.custom_minimum_size = Vector2(300, 72)
	begin.pressed.connect(_begin)
	row.add_child(begin)
	return row


func _begin() -> void:
	start_requested.emit(str(scenario["id"]), ROME, difficulty, chronicle and int(civ.get("chronicle", 0)) > 0)


func _clear() -> void:
	for child in _root.get_children():
		_root.remove_child(child)
		child.queue_free()

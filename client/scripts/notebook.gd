## The notebook from the future (D-126): everything the player remembers of the world to
## come, as a two-page journal. Left, the entries - each with how far ahead of its time it
## is and whether it can be brought in now; right, the open entry: the player's note, what
## really happened in our history, what it will do, what it takes, the risks, and what it
## needs first (click to turn to that page). One button brings it into the world.
class_name Notebook
extends Control

signal start_requested(node_id: String)

const INK := UiStyle.INK
const DIM := UiStyle.INK_SOFT
const GOOD := Color(0.16, 0.45, 0.18)
const BAD := Color(0.62, 0.12, 0.08)
const FILTERS := [["ready", "Ready now"], ["groundwork", "Needs groundwork"],
	["working", "Being made"], ["in_use", "In use"], ["of_this_age", "Of this age"]]

var view: Dictionary = {}
var _filter := "ready"
var _selected := ""
var _list: VBoxContainer
var _page: VBoxContainer
var _tally: Label
var _filter_row: HBoxContainer


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.05, 0.03, 0.02, 0.66)
	shade.gui_input.connect(func(event: InputEvent):
		if event is InputEventMouseButton and event.pressed:
			close())
	add_child(shade)
	var centre := CenterContainer.new()
	centre.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	centre.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(centre)
	var book := PanelContainer.new()
	book.add_theme_stylebox_override("panel", UiStyle.ornate_panel())
	book.custom_minimum_size = Vector2(1320, 780)
	centre.add_child(book)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 16)
	book.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	margin.add_child(column)
	# heading
	var head := HBoxContainer.new()
	var titles := VBoxContainer.new()
	titles.add_theme_constant_override("separation", 0)
	titles.add_child(UiStyle.label("YOUR NOTEBOOK FROM THE FUTURE", 32, UiStyle.RED, "title", 900))
	titles.add_child(UiStyle.label("Everything you remember of the world to come. Bring it into this one - centuries before its time.", 15, DIM))
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(titles)
	_tally = UiStyle.label("", 17, UiStyle.GOLD_DARK, "body", 800)
	_tally.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_tally.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(_tally)
	var shut := UiStyle.big_button("✕", 20, Color(0.85, 0.80, 0.70))
	shut.custom_minimum_size = Vector2(48, 44)
	shut.tooltip_text = "Close the notebook (Esc)"
	shut.pressed.connect(close)
	head.add_child(shut)
	column.add_child(head)
	_filter_row = HBoxContainer.new()
	_filter_row.add_theme_constant_override("separation", 8)
	column.add_child(_filter_row)
	# the two pages
	var pages := HBoxContainer.new()
	pages.add_theme_constant_override("separation", 18)
	pages.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(pages)
	var left := ScrollContainer.new()
	left.custom_minimum_size = Vector2(470, 0)
	left.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	pages.add_child(left)
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 4)
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_child(_list)
	var spine := ColorRect.new()
	spine.color = Color(0.55, 0.40, 0.20, 0.5)
	spine.custom_minimum_size = Vector2(3, 0)
	pages.add_child(spine)
	var right := ScrollContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	pages.add_child(right)
	_page = VBoxContainer.new()
	_page.add_theme_constant_override("separation", 10)
	_page.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_child(_page)


func open(new_view: Dictionary, idea_id := "") -> void:
	view = new_view
	if idea_id != "":
		_selected = idea_id
		var idea := _find(idea_id)
		if not idea.is_empty():
			_filter = _status(idea)
	visible = true
	move_to_front()
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 0.2)
	refresh(view)


func close() -> void:
	visible = false


func is_open() -> bool:
	return visible


## Redraw from a new view (keeps the open page).
func refresh(new_view: Dictionary) -> void:
	view = new_view
	if not visible:
		return
	var status: Dictionary = view.get("status", {})
	var count := int(status.get("anachronisms", 0))
	var years := int(status.get("years_ahead", 0))
	_tally.text = "✦ Nothing from your notebook is in use yet." if count == 0 else \
		"✦ %d idea%s brought in · history pushed %s years ahead" % [count, "" if count == 1 else "s", GameHud.number(years)]
	_fill_filters()
	_fill_list()
	_fill_page()


func _unhandled_key_input(event: InputEvent) -> void:
	if visible and event.is_pressed() and (event as InputEventKey).keycode == KEY_ESCAPE:
		close()
		get_viewport().set_input_as_handled()


# --- entries -------------------------------------------------------------------------------


## Which list an idea belongs on.
func _status(idea: Dictionary) -> String:
	var stage = idea.get("stage")
	if stage in ["adopted", "widespread"]:
		# only what the player brought from the future is in their notebook
		var since = idea.get("adopted_year")
		return "in_use" if since != null and int(idea["year"]) > int(since) else "known"
	if stage == "experimenting":
		return "working"
	if int(idea.get("ahead", 0)) <= 0:
		return "of_this_age"
	return "ready" if bool(idea.get("ready", false)) else "groundwork"


func _find(id: String) -> Dictionary:
	for idea in view.get("ideas", []):
		if str(idea["id"]) == id:
			return idea
	return {}


func _entries(filter: String) -> Array:
	var out: Array = view.get("ideas", []).filter(func(i: Dictionary) -> bool:
		if filter == "of_this_age":
			return _status(i) == "of_this_age" and bool(i.get("ready", false))
		return _status(i) == filter)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a["ahead"]) < int(b["ahead"]) if filter != "of_this_age" else int(a["year"]) > int(b["year"]))
	return out


func _fill_filters() -> void:
	for child in _filter_row.get_children():
		child.queue_free()
	for entry in FILTERS:
		var key: String = entry[0]
		var n := _entries(key).size()
		var chip := UiStyle.big_button("%s  %d" % [entry[1], n], 15, UiStyle.GOLD if key == _filter else Color(0.86, 0.81, 0.71))
		chip.custom_minimum_size = Vector2(0, 38)
		chip.pressed.connect(func():
			_filter = key
			_selected = ""
			refresh(view))
		_filter_row.add_child(chip)


func _fill_list() -> void:
	for child in _list.get_children():
		child.queue_free()
	var entries := _entries(_filter)
	if entries.is_empty():
		var empty := {
			"ready": "Nothing can be brought in this very moment. Look under \"Needs groundwork\": each entry says what must come first.",
			"groundwork": "Every idea from your notebook is within reach.",
			"working": "Your people are not working on anything from the notebook yet.",
			"in_use": "Nothing from the future is in use yet. Bring something in!",
			"of_this_age": "You know everything this age already knows.",
		}
		_list.add_child(UiStyle.wrapped(empty[_filter], 15, DIM, 440))
		return
	if _selected == "" or _find(_selected).is_empty() or _status(_find(_selected)) != _filter and not (_filter == "of_this_age"):
		_selected = str(entries[0]["id"])
	for idea in entries:
		_list.add_child(_row(idea))


func _row(idea: Dictionary) -> Control:
	var id := str(idea["id"])
	var row := Button.new()
	row.toggle_mode = true
	row.button_pressed = id == _selected
	row.flat = id != _selected
	row.custom_minimum_size = Vector2(440, 46)
	row.focus_mode = Control.FOCUS_NONE
	row.pressed.connect(func():
		_selected = id
		refresh(view))
	var line := HBoxContainer.new()
	line.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	line.offset_left = 10
	line.offset_right = -10
	line.add_theme_constant_override("separation", 8)
	line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var glyph: String = {"ready": "●", "groundwork": "◌", "working": "⚙", "in_use": "✓", "of_this_age": "·"}[_status(idea)]
	var mark := UiStyle.label(glyph, 18, GOOD if glyph in ["●", "✓"] else DIM, "body", 800)
	mark.mouse_filter = Control.MOUSE_FILTER_IGNORE
	line.add_child(mark)
	var name := UiStyle.label(str(idea["name"]), 17, INK, "body", 700)
	name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name.clip_text = true
	name.mouse_filter = Control.MOUSE_FILTER_IGNORE
	line.add_child(name)
	if not (idea.get("stolen_by", []) as Array).is_empty():
		var thief := UiStyle.label("⚠", 16, BAD, "body", 800)
		thief.tooltip_text = "Stolen by spies"
		line.add_child(thief)
	var ahead := int(idea["ahead"])
	if ahead > 0:
		var badge := UiStyle.label("+%s yrs" % GameHud.number(ahead), 14, _ahead_colour(ahead), "body", 800)
		badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
		line.add_child(badge)
	row.add_child(line)
	return row


func _ahead_colour(years: int) -> Color:
	if years >= 1000:
		return Color(0.55, 0.12, 0.45)
	if years >= 300:
		return BAD
	return UiStyle.GOLD_DARK


# --- the open page ---------------------------------------------------------------------------


func _fill_page() -> void:
	for child in _page.get_children():
		child.queue_free()
	var idea := _find(_selected)
	if idea.is_empty():
		return
	var ahead := int(idea["ahead"])
	var status := _status(idea)
	var category := str(GameHud.CATEGORY_NAMES.get(idea["category"], idea["category"]))
	_page.add_child(UiStyle.label(category.to_upper(), 14, UiStyle.GOLD_DARK, "body", 800))
	_page.add_child(UiStyle.label(str(idea["name"]), 40, UiStyle.RED, "title", 900))
	if ahead > 0:
		_page.add_child(UiStyle.label("%s years before its time" % GameHud.number(ahead), 22, _ahead_colour(ahead), "title", 800))
	else:
		_page.add_child(UiStyle.label("Known in the world since %s" % GameHud.year_text(int(idea["year"])), 18, DIM, "title", 700))
	match status:
		"ready", "of_this_age":
			var go := UiStyle.big_button("BRING IT INTO THE WORLD  ▸" if ahead > 0 else "LEARN IT  ▸", 22)
			go.custom_minimum_size = Vector2(380, 56)
			var id := str(idea["id"])
			go.pressed.connect(func(): start_requested.emit(id))
			_page.add_child(go)
		"groundwork":
			_page.add_child(UiStyle.wrapped("◌ Not yet: it builds on ideas this world does not have. See what it builds on, below.", 16, BAD, 760))
		"working":
			_page.add_child(UiStyle.wrapped("⚙ Your people are working on it now (see Projects).", 17, UiStyle.GOLD_DARK, 760))
		"in_use":
			var since = idea.get("adopted_year")
			var when := (" since %s" % GameHud.year_text(int(since))) if since != null else ""
			var early := (", %s years before history" % GameHud.number(int(idea["year"]) - int(since))) if since != null and int(idea["year"]) > int(since) else ""
			_page.add_child(UiStyle.wrapped("✓ In use in your lands%s%s." % [when, early], 17, GOOD, 760))
	if str(idea.get("flavour", "")) != "":
		_section("YOUR NOTE")
		_page.add_child(UiStyle.wrapped("“%s”" % str(idea["flavour"]), 19, INK, 760))
	if str(idea.get("history", "")) != "":
		_section("IN OUR HISTORY")
		_page.add_child(UiStyle.wrapped(str(idea["history"]), 16, INK, 760))
	var effects: Array = idea.get("effects", [])
	if not effects.is_empty():
		_section("WHAT IT WILL DO")
		for e in effects:
			_page.add_child(UiStyle.wrapped("▸ " + str(e["text"]), 16, GOOD, 760))
	if status in ["ready", "groundwork", "of_this_age"]:
		var c: Dictionary = idea["cost"]
		_section("WHAT IT TAKES")
		_page.add_child(UiStyle.wrapped("Every turn until it works: %s labour, %s materials, %s knowledge, %s wealth - about %d turn%s." % [
			GameHud.number(int(c["labour"])), GameHud.number(int(c["materials"])), GameHud.number(int(c["knowledge"])),
			GameHud.number(int(c["wealth"])), int(idea["turns"]), "" if int(idea["turns"]) == 1 else "s"], 16, INK, 760))
		var share := int(idea.get("labour_share", 0))
		var hands := "It would take %d%% of your free hands." % share if share <= 100 else "It needs more hands than you have free: work would stall, or pull farmers from the fields."
		_page.add_child(UiStyle.wrapped(hands, 15, BAD if share > 60 else DIM, 760))
	if ahead > 0 and status != "in_use":
		_section("THE RISKS")
		var risks := []
		var suspicion := int(idea.get("suspicion", 0))
		if suspicion > 0:
			risks.append("People will wonder where it came from: suspicion of Rome's new arts +%d%%." % suspicion)
		risks.append("Courts that hear of it may send spies to steal it.")
		_page.add_child(UiStyle.wrapped(" ".join(risks), 15, DIM, 760))
	var thieves: Array = idea.get("stolen_by", [])
	if not thieves.is_empty():
		_page.add_child(UiStyle.wrapped("⚠ Stolen by the spies of %s." % ", ".join(thieves), 15, BAD, 760))
	var needs: Array = idea.get("needs", [])
	if not needs.is_empty():
		_section("BUILDS ON")
		var chips := HFlowContainer.new()
		chips.add_theme_constant_override("h_separation", 8)
		chips.add_theme_constant_override("v_separation", 6)
		for need in needs:
			var have := bool(need["have"])
			var chip := UiStyle.big_button(("✓ " if have else "◌ ") + str(need["name"]), 14, Color(0.80, 0.90, 0.75) if have else Color(0.95, 0.85, 0.6))
			var target := str(need["id"])
			chip.tooltip_text = "Already in use" if have else "Turn to this page"
			chip.pressed.connect(func():
				var other := _find(target)
				if not other.is_empty():
					_selected = target
					_filter = _status(other)
					refresh(view))
			chips.add_child(chip)
		_page.add_child(chips)
	if str(idea.get("blockers", "")) != "" and status == "groundwork":
		_page.add_child(UiStyle.wrapped("First: " + str(idea["blockers"]) + ".", 15, BAD, 760))


func _section(title: String) -> void:
	var label := UiStyle.label(title, 14, UiStyle.GOLD_DARK, "body", 900)
	_page.add_child(label)

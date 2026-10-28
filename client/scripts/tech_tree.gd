## The tech tree (brief §11): every advancement as a card, one row per field, ordered by
## when it first appeared in history, with lines to its prerequisites. Goal stubs (ideas the
## court named but has not ruled on) are shown, so the player sees what they are working
## toward. Hover a card for its description.
class_name TechTree
extends Control

signal asked(idea_name: String)   ## a card was clicked: ask the court about it

const ADOPTED := Color(0.45, 0.70, 0.35)
const TRYING := Color(0.95, 0.72, 0.25)
const KNOWN := Color(0.62, 0.78, 0.92)
const GOAL := Color(0.95, 0.55, 0.35)
const STUB := Color(0.80, 0.62, 0.90)
const UNKNOWN := Color(0.86, 0.83, 0.77)
const CARD := Vector2(160, 44)
const GAP := Vector2(24, 18)
const LANE_LABEL := 130.0
const CATEGORY_NAMES := GameHud.CATEGORY_NAMES

var nodes: Array = []
var year := 0
var _where := {}   ## node id -> Rect2


func setup(tree_nodes: Array, now: int) -> void:
	nodes = tree_nodes
	year = now
	var lanes := {}
	for node in nodes:
		lanes[node["category"]] = true
	var categories: Array = lanes.keys()
	categories.sort()
	var columns := {}
	var max_column := 0
	var by_lane := {}
	for node in nodes:
		by_lane.get_or_add(node["category"], []).append(node)
	var lane_rows := {}
	var y := 10.0
	for category in categories:
		var list: Array = by_lane[category]
		list.sort_custom(func(a, b): return a["year"] < b["year"] if a["year"] != b["year"] else a["name"] < b["name"])
		# pack cards into as few rows as fit: a column index by order, two rows per lane
		for i in list.size():
			var node: Dictionary = list[i]
			var column := i / 2
			var row := i % 2
			max_column = maxi(max_column, column)
			_where[node["id"]] = Rect2(Vector2(LANE_LABEL + column * (CARD.x + GAP.x), y + row * (CARD.y + 6)), CARD)
		lane_rows[category] = y
		y += 2 * (CARD.y + 6) + GAP.y
	custom_minimum_size = Vector2(LANE_LABEL + (max_column + 1) * (CARD.x + GAP.x) + 20, y)
	set_meta("lanes", lane_rows)
	tooltip_text = " "
	queue_redraw()


func _colour(node: Dictionary) -> Color:
	if node["stub"]:
		return STUB
	match node["stage"]:
		"adopted", "widespread":
			return ADOPTED
		"experimenting":
			return TRYING
		"concept":
			return GOAL if node["goal"] else KNOWN
	return UNKNOWN


func _draw() -> void:
	var font := UiStyle.font("body", 700)
	var lanes: Dictionary = get_meta("lanes", {})
	for category in lanes:
		draw_string(UiStyle.font("title", 800), Vector2(6, lanes[category] + 30), str(CATEGORY_NAMES.get(category, category)),
			HORIZONTAL_ALIGNMENT_LEFT, LANE_LABEL - 12, 16, UiStyle.RED)
		draw_line(Vector2(0, lanes[category] - 6), Vector2(size.x, lanes[category] - 6), Color(0.5, 0.4, 0.3, 0.25), 1.0)
	for node in nodes:
		var rect: Rect2 = _where[node["id"]]
		for prerequisite in node["prerequisites"]:
			if _where.has(prerequisite):
				var from: Rect2 = _where[prerequisite]
				var a := Vector2(from.end.x, from.get_center().y)
				var b := Vector2(rect.position.x, rect.get_center().y)
				if a.x > b.x:
					a = from.get_center()
					b = rect.get_center()
				draw_line(a, b, Color(0.35, 0.25, 0.15, 0.35), 1.5, true)
	for node in nodes:
		var rect: Rect2 = _where[node["id"]]
		var fill := _colour(node)
		draw_rect(rect, fill)
		draw_rect(rect, fill.darkened(0.4), false, 2.0)
		if node["provenance"] == "player_idea":
			draw_circle(rect.position + Vector2(rect.size.x - 8, 8), 5, UiStyle.GOLD)  # your own idea
		# long names shrink to fit the card rather than being cut off
		var title := str(node["name"])
		var size := 13
		while size > 10 and font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > CARD.x - 12:
			size -= 1
		draw_string(font, rect.position + Vector2(6, 18), title, HORIZONTAL_ALIGNMENT_LEFT, CARD.x - 12, size, UiStyle.INK)
		var when := GameHud.year_text(int(node["year"]))
		var ahead := int(node["year"]) - year
		draw_string(font, rect.position + Vector2(6, 36), when + ("  ▲ ahead" if ahead > 100 else ""), HORIZONTAL_ALIGNMENT_LEFT, CARD.x - 12, 11,
			Color(0.6, 0.15, 0.1) if ahead > 100 else UiStyle.INK_SOFT)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		for node in nodes:
			if (_where[node["id"]] as Rect2).has_point(event.position):
				if not node["stage"] in ["adopted", "widespread", "experimenting"]:
					asked.emit(str(node["name"]))
				return


func _get_tooltip(at: Vector2) -> String:
	for node in nodes:
		if (_where[node["id"]] as Rect2).has_point(at):
			var text := "%s (%s)" % [node["name"], GameHud.year_text(int(node["year"]))]
			if node["flavour"] != "":
				text += "\n" + str(node["flavour"])
			if not node["stage"] in ["adopted", "widespread", "experimenting"]:
				text += "\nClick to ask the Senate about it."
			return text
	return ""

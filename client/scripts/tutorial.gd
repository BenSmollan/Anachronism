## A short guided tour for a first game: a tip card beside each part of the screen, with
## an arrow pointing at it. Shown once (remembered in the player's settings), skippable,
## and available again from Settings.
class_name Tutorial
extends CanvasLayer

signal finished

const SETTINGS := "user://settings.cfg"
## title, text, where the arrow points (in 1600x900 layout units), where the card sits
const STEPS := [
	["Welcome, Senator", "You guide a real state at a real moment in history. You have one advantage: you know what comes next. Every idea you give the Senate can change the world.", Vector2(-1, -1), Vector2(560, 300)],
	["Your state", "The top bar shows your people, stores of food, materials, wealth and knowledge, and your society: literacy, unrest, legitimacy, and suspicion - how uncanny your progress looks. Arrows show which way things are moving.", Vector2(620, 40), Vector2(420, 120)],
	["Whisper an idea", "Type any idea here - \"make the river work for us\", \"a printing press\", \"germs cause disease\". The Senate judges it: within reach, needs groundwork first (with the first steps to begin), or beyond this age.", Vector2(1320, 174), Vector2(700, 150)],
	["Begin the work", "Ideas within reach can be tried. Press Begin: it costs labour, materials, knowledge and wealth every turn until it works. Take on too much and the people suffer - set a project to Low to use only spare hands, or Hasten it with your stores.", Vector2(1520, 395), Vector2(830, 330)],
	["Your provinces", "Click one of your provinces to see what it holds. Open Build to raise markets, granaries, temples, schools and more - some ideas need them, like workshops for printing. Cities spread and fill with buildings as they grow.", Vector2(700, 480), Vector2(760, 520)],
	["The world", "The World tab shows the paths to victory and what each still needs, decrees of the Senate, and every state you can reach: envoys, alliances, tribute, missionaries, spies - or war - and what is said of each court's plans. Gold lines on the map are your trade.", Vector2(1510, 120), Vector2(830, 170)],
	["Time moves on", "Each press of End Turn (or Enter) is a decade, and the game saves itself. Rivals follow their own history - until news of your ideas reaches them.", Vector2(1478, 855), Vector2(900, 600)],
	["Your capital", "Click your emblem to fly down to your capital; your adopted ideas appear there as buildings. Esc opens the menu: save, load, the chronicle, charts and the tech tree.", Vector2(50, 40), Vector2(90, 150)],
]

var _step := 0
var start_at := 0   ## for screenshots: open the tour at a later step
var _root := Control.new()


static func seen() -> bool:
	var config := ConfigFile.new()
	return config.load(SETTINGS) == OK and bool(config.get_value("tutorial", "seen", false))


static func mark_seen(value: bool) -> void:
	var config := ConfigFile.new()
	config.load(SETTINGS)
	config.set_value("tutorial", "seen", value)
	config.save(SETTINGS)


func _ready() -> void:
	layer = 8
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UiStyle.theme()
	add_child(_root)
	_step = start_at
	_show()


func _show() -> void:
	for child in _root.get_children():
		child.queue_free()
	if _step >= STEPS.size():
		mark_seen(true)
		finished.emit()
		queue_free()
		return
	var step: Array = STEPS[_step]
	var target: Vector2 = step[2]
	var card_at: Vector2 = step[3]
	var arrow := _Arrow.new()
	arrow.set_anchors_preset(Control.PRESET_FULL_RECT)
	arrow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	arrow.to = target
	arrow.from = card_at + Vector2(200, 0)
	_root.add_child(arrow)
	var card := PanelContainer.new()
	card.position = card_at
	card.custom_minimum_size = Vector2(420, 0)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	body.add_child(UiStyle.label(str(step[0]), 26, UiStyle.RED, "title", 900))
	body.add_child(UiStyle.wrapped(str(step[1]), 17, UiStyle.INK, 400))
	var row := HBoxContainer.new()
	var skip := UiStyle.big_button("Skip tour", 15, Color(0.85, 0.8, 0.7))
	skip.pressed.connect(func():
		_step = STEPS.size()
		_show())
	row.add_child(skip)
	var push := Control.new()
	push.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(push)
	row.add_child(UiStyle.label("%d / %d" % [_step + 1, STEPS.size()], 14, UiStyle.INK_SOFT))
	var next := UiStyle.big_button("Next" if _step < STEPS.size() - 1 else "Play!", 18)
	next.pressed.connect(func():
		_step += 1
		_show())
	row.add_child(next)
	body.add_child(row)
	card.add_child(body)
	_root.add_child(card)


class _Arrow extends Control:
	var from := Vector2.ZERO
	var to := Vector2(-1, -1)

	func _draw() -> void:
		if to.x < 0:
			return
		var dir := (to - from).normalized()
		var tip := to - dir * 12.0
		draw_line(from, tip, Color(0.96, 0.76, 0.26), 6.0, true)
		draw_line(from, tip, Color(0.4, 0.2, 0.05), 2.0, true)
		var side := Vector2(-dir.y, dir.x)
		draw_colored_polygon(PackedVector2Array([to, tip - dir * 14.0 + side * 12.0, tip - dir * 14.0 - side * 12.0]), Color(0.96, 0.76, 0.26))
		draw_arc(to, 26.0, 0, TAU, 32, Color(0.96, 0.76, 0.26), 4.0)

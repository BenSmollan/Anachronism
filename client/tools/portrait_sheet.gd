## Draws a contact sheet of portraits for checking them by eye:
##   godot --path client -s res://tools/portrait_sheet.gd -- OUT.png
extends SceneTree

const CASTS := [
	["rome", "roman", ""], ["carthage", "punic", ""], ["egypt", "pharaoh", ""], ["hatti", "hittite", ""],
	["england", "medieval_king", ""], ["norway", "viking", ""], ["kyiv", "rus", ""], ["venice", "doge", ""],
	["rome_scholar", "scholar", "roman"], ["rome_steward", "steward", "roman"], ["rome_general", "general", "roman"],
	["rome_diviner", "diviner", "roman"], ["egypt_scholar", "scholar", "pharaoh"], ["egypt_steward", "steward", "pharaoh"],
	["egypt_general", "general", "pharaoh"], ["egypt_diviner", "diviner", "pharaoh"],
	["england_scholar", "scholar", "medieval_king"], ["england_steward", "steward", "medieval_king"],
	["england_general", "general", "medieval_king"], ["england_diviner", "diviner", "medieval_king"],
]
const COLOURS := ["#3a4a6b", "#b04a2e", "#6b8e3a", "#8a5a9e", "#c49a2a", "#2e7d8c", "#9e3a3a"]


func _initialize() -> void:
	var out := "portraits.png"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	var root_control := Control.new()
	root_control.size = Vector2(1600, 900)
	get_root().add_child(root_control)
	for i in CASTS.size():
		var p := Portrait.new()
		p.position = Vector2((i % 7) * 226 + 8, (i / 7) * 222 + 8)
		p.size = Vector2(210, 210)
		root_control.add_child(p)
		p.setup({"id": CASTS[i][0], "portrait": CASTS[i][1], "culture": CASTS[i][2], "colour": COLOURS[i % COLOURS.size()]})
	for k in 6:
		await process_frame
	get_root().get_texture().get_image().save_png(out)
	quit()

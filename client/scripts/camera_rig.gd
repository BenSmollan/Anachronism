## Map camera in the style of Rise of Kingdoms: a fixed heading, drag or WASD to pan, wheel or
## pinch to zoom. Zoomed out it looks almost straight down at the strategic map; zooming in
## tilts it towards the horizon so towns and forests stand up (D-052).
##
## Movement is eased so the map never jumps (D-123): zoom glides in equal steps of scale
## (log space) and keeps the point under the mouse where it is; a drag carries on and slows
## when let go; `fly_to` arcs out and back down over long distances, like a globe.
class_name CameraRig
extends Node3D

var near := 60.0       ## closest zoom; the map sets this
var far := 1100.0      ## farthest zoom; the map sets this to fit
const PITCH_NEAR := 0.72  ## radians above the horizon when fully zoomed in (about 41°)
const PITCH_FAR := 1.30   ## when fully zoomed out (about 75°)
const ZOOM_STEP := 0.82   ## one wheel notch
const ZOOM_EASE := 9.0    ## how quickly zoom catches up with the wheel (per second)
const GLIDE_DECAY := 5.0  ## how quickly a flung map slows down (per second)

var distance := 760.0
var target_distance := 760.0
var bounds := Rect2(-400, -400, 800, 800)  ## where the camera may look, on the ground plane
var camera := Camera3D.new()
var _dragging := false
var _anchor := Vector2(-1, -1)   ## the screen point zoom keeps still (-1: the centre)
var _glide := Vector2.ZERO       ## pan velocity after a drag, ground units per second
var _drag_velocity := Vector2.ZERO
var _flight: Tween
## Shake (game-feel): a "trauma" of 0..1 that great moments add to and that drains away; the
## camera sways by trauma squared, so small knocks barely stir it and great ones punch, along
## smooth waves rather than a random buzz. It moves only the view, never the map.
const SHAKE_DECAY := 1.1       ## trauma lost per second
const SHAKE_REACH := 0.018     ## at full trauma, the sway as a share of the camera's distance
const SETTINGS := "user://settings.cfg"
var trauma := 0.0
var _shake_t := 0.0
static var _shake_on := -1     ## the player's choice, read once (-1: not read yet)


func _ready() -> void:
	camera.fov = 40.0
	camera.near = 1.0
	camera.far = 6000.0
	add_child(camera)
	_apply()


## How far zoomed in, from 0 (fully out) to 1 (fully in).
func zoom_level() -> float:
	return 1.0 - inverse_lerp(log(near), log(far), log(distance))


## Jump straight to a point (no animation).
func look_at_point(point: Vector3, new_distance: float) -> void:
	_stop_flight()
	position = Vector3(point.x, 0, point.z)
	distance = new_distance
	target_distance = new_distance
	_glide = Vector2.ZERO
	_apply()


## Glide to a point and distance over `seconds` (by default, longer for longer journeys).
## A long way off, the camera rises on the way, so the map slides by at a readable pace,
## and comes back down at the far end.
func fly_to(point: Vector3, new_distance: float, seconds := -1.0) -> Tween:
	_stop_flight()
	_glide = Vector2.ZERO
	var from := Vector2(position.x, position.z)
	var to := Vector2(point.x, point.z)
	var span := from.distance_to(to)
	var start_d := distance
	var end_d := clampf(new_distance, near, far)
	var peak := clampf(maxf(maxf(start_d, end_d), span * 1.1), near, far)
	if seconds < 0.0:
		seconds = clampf(0.6 + log(1.0 + span / 60.0) * 0.45, 0.6, 2.2)
	_flight = create_tween()
	_flight.tween_method(func(t: float) -> void:
		var e := t * t * (3.0 - 2.0 * t)   # smoothstep: eased at both ends
		var at := from.lerp(to, e)
		position = Vector3(at.x, 0, at.y)
		# distance in log space, with a hump in the middle when the journey is long
		var base := lerpf(log(start_d), log(end_d), e)
		var hump := maxf(0.0, log(peak) - maxf(log(start_d), log(end_d))) * sin(PI * e)
		distance = exp(base + hump)
		target_distance = distance
		_apply(), 0.0, 1.0, seconds)
	_flight.finished.connect(func() -> void: target_distance = end_d)
	return _flight


func _stop_flight() -> void:
	if _flight != null and _flight.is_valid():
		_flight.kill()
	_flight = null


func is_flying() -> bool:
	return _flight != null and _flight.is_valid() and _flight.is_running()


func _apply() -> void:
	distance = clampf(distance, near, far)
	camera.near = maxf(1.0, distance * 0.05)  # keeps depth precise so land and water don't flicker
	position.x = clampf(position.x, bounds.position.x, bounds.end.x)
	position.z = clampf(position.z, bounds.position.y, bounds.end.y)
	var pitch := lerpf(PITCH_FAR, PITCH_NEAR, zoom_level())
	camera.position = Vector3(0, sin(pitch), cos(pitch)) * distance
	camera.look_at(global_position, Vector3.UP)


## Where a screen point meets the ground plane (or the rig's own point, looking at the sky).
func _ground_under(screen: Vector2) -> Vector3:
	var origin := camera.project_ray_origin(screen)
	var direction := camera.project_ray_normal(screen)
	if direction.y > -0.01:
		return global_position
	return origin + direction * (-origin.y / direction.y)


func _zoom(factor: float, at: Vector2) -> void:
	_stop_flight()
	target_distance = clampf(target_distance * factor, near, far)
	_anchor = at


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_zoom(ZOOM_STEP, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_zoom(1.0 / ZOOM_STEP, event.position)
		elif event.button_index == MOUSE_BUTTON_LEFT:
			_dragging = event.pressed
			if event.pressed:
				_stop_flight()
				_glide = Vector2.ZERO
				_drag_velocity = Vector2.ZERO
			else:
				_glide = _drag_velocity  # let go: the map carries on and slows
	elif event is InputEventMagnifyGesture:
		_zoom(1.0 / event.factor, event.position)
	elif event is InputEventPanGesture:
		_stop_flight()
		_pan(event.delta * distance * 0.01)
	elif event is InputEventMouseMotion and _dragging:
		var amount: Vector2 = -event.relative * distance * 0.0015
		_pan(amount)
		var step := maxf(get_process_delta_time(), 1.0 / 240.0)
		_drag_velocity = _drag_velocity.lerp(amount / step, 0.5)


## Add to the shake: about 0.2 for a knock, 0.5 for a blow, 0.9 for a cataclysm.
func add_trauma(amount: float) -> void:
	if shake_enabled():
		trauma = clampf(trauma + amount, 0.0, 1.0)


## Whether the player wants the camera to shake (Settings; on unless switched off).
static func shake_enabled() -> bool:
	if _shake_on < 0:
		var config := ConfigFile.new()
		_shake_on = 1 if config.load(SETTINGS) != OK or bool(config.get_value("display", "shake", true)) else 0
	return _shake_on == 1


static func set_shake_enabled(on: bool) -> void:
	var config := ConfigFile.new()
	config.load(SETTINGS)
	config.set_value("display", "shake", on)
	config.save(SETTINGS)
	_shake_on = 1 if on else 0


func _shake_step(delta: float) -> void:
	if trauma <= 0.0:
		return
	trauma = maxf(trauma - SHAKE_DECAY * delta, 0.0)
	var power := trauma * trauma
	_shake_t += delta * 22.0
	var reach := distance * SHAKE_REACH * power
	camera.h_offset = reach * (sin(_shake_t * 1.7) + 0.5 * sin(_shake_t * 3.1))
	camera.v_offset = reach * 0.7 * (sin(_shake_t * 2.3 + 1.0) + 0.5 * sin(_shake_t * 4.3))
	if trauma <= 0.0:
		camera.h_offset = 0.0
		camera.v_offset = 0.0


func _process(delta: float) -> void:
	_shake_step(delta)
	if is_flying():
		return
	var move := Vector2(Input.get_axis("ui_left", "ui_right"), Input.get_axis("ui_up", "ui_down"))
	if move != Vector2.ZERO:
		_glide = _glide.lerp(move * distance * 1.1, minf(1.0, delta * 6.0))  # ease into it
	elif _dragging:
		_glide = Vector2.ZERO
		_drag_velocity *= exp(-12.0 * delta)  # holding still while dragging: no fling
	if _glide.length() > distance * 0.01:
		_pan(_glide * delta)
		if move == Vector2.ZERO:
			_glide *= exp(-GLIDE_DECAY * delta)
	else:
		_glide = Vector2.ZERO
	if absf(log(distance) - log(target_distance)) > 0.0005:
		var screen := _anchor if _anchor.x >= 0.0 else get_viewport().get_visible_rect().size / 2.0
		var before := _ground_under(screen)
		var k := 1.0 - exp(-ZOOM_EASE * delta)
		distance = exp(lerpf(log(distance), log(target_distance), k))
		_apply()
		# keep the point under the mouse where it was, as maps do
		var after := _ground_under(screen)
		position += Vector3(before.x - after.x, 0, before.z - after.z)
		_apply()
	elif distance != target_distance:
		distance = target_distance
		_anchor = Vector2(-1, -1)
		_apply()


func _pan(amount: Vector2) -> void:
	position += Vector3(amount.x, 0, amount.y)
	_apply()

## Cartoon trees over the real map, wherever the satellite image shows forest (step 2.11).
##
## Round leafy trees in the warm south, pointed conifers in the north and on mountains.
## The map is cut into tiles, each shown only when the camera is near it, so a whole
## continent of forest costs little.
class_name Scenery
extends RefCounted

const TILE := 120.0            ## tile size in map units (about 500 km)
const SHOW_WITHIN := 260.0     ## camera distance at which a tile's trees appear
## Level of detail (performance skill, D-284): the detailed trees only near the camera, in
## small batches; beyond, simple ones (a few dozen triangles, no shadow) in large batches.
## Measured: trees were 21 of the 31 million triangles in a close city view.
const NEAR_TILE := 40.0        ## batch size of the detailed trees
const DETAIL_WITHIN := 60.0    ## camera distance within which trees are drawn in detail
const STEP := 4                ## sample the land every STEP height-map pixels
const S := 2.4                 ## trees are drawn larger than life, like the towns (D-058)

var earth: EarthBuilder
var rng := RandomNumberGenerator.new()
var _batches := {}   ## near tile -> [[multimesh, transforms], ...], for clearing city ground
var _far_batches := {}   ## (large) tile -> [[multimesh, transforms], ...], the simple trees
var _simple := {}   ## kind -> its simple mesh
var _cleared: Array = []   ## [multimesh, index, transform] of trees taken away


func _init(earth_builder: EarthBuilder) -> void:
	earth = earth_builder
	rng.seed = hash(earth.region)


func build(parent: Node3D) -> void:
	var holder := Node3D.new()
	holder.name = "Trees"
	parent.add_child(holder)
	var tiles := {}   # near tile -> {variant: [transforms, colours]}
	var far := {}     # large tile -> {kind: [transforms, colours]}
	var image := earth.colour_image
	var w := int(earth.size().x)
	var h := int(earth.size().y)
	for y in range(0, h, STEP):
		for x in range(0, w, STEP):
			var pixel := Vector2(x, y)
			if earth.is_ocean_at(pixel):
				continue
			var metres := earth.metres_at(pixel)
			var c := image.get_pixel(x * image.get_width() / w, y * image.get_height() / h)
			var lum := c.r * 0.3 + c.g * 0.59 + c.b * 0.11
			var veg := clampf((c.g - c.r) * 7.0 + 0.55, 0.0, 1.0)
			var forest := veg * (1.0 - smoothstep(0.16, 0.32, lum))
			if metres > 3800.0 or rng.randf() > forest * 0.9:
				continue
			var lat := earth.latitude(y)
			var conifer := lat > 42.0 or metres > 1600.0 or (lat > 33.0 and rng.randf() < 0.3)
			var kind := "conifer" if conifer else "leafy"
			if lat < 32.0 and metres < 400.0 and lum > 0.22 and rng.randf() < 0.6:
				kind = "palm"   # warm lowlands: date and coconut palms
			var far_key := Vector2i(int(x / TILE), int(y / TILE))
			if not far.has(far_key):
				far[far_key] = {}
			if not far[far_key].has(kind):
				far[far_key][kind] = [[], []]
			var grove := pixel + Vector2(rng.randf_range(0, STEP), rng.randf_range(0, STEP))
			for i in rng.randi_range(3, 7):
				var variant: String = KINDS[kind][rng.randi() % KINDS[kind].size()]
				var p := grove + Vector2(rng.randf_range(-1.6, 1.6), rng.randf_range(-1.6, 1.6))
				var key := Vector2i(floori(p.x / NEAR_TILE), floori(p.y / NEAR_TILE))
				if not tiles.has(key):
					tiles[key] = {}
				if not tiles[key].has(variant):
					tiles[key][variant] = [[], []]
				var size := rng.randf_range(0.75, 1.3) * S
				var ground := earth.ground_at_pixel(p)
				var placed := Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * size), ground)
				var green := Color(0.36, 0.66, 0.26) if kind != "conifer" else Color(0.22, 0.52, 0.30)
				green = green.lightened(rng.randf() * 0.2).darkened(rng.randf() * 0.1)
				tiles[key][variant][0].append(placed)
				tiles[key][variant][1].append(green)
				far[far_key][kind][0].append(placed)
				far[far_key][kind][1].append(green)
	for key in tiles:
		for variant in tiles[key]:
			var entry: Array = tiles[key][variant]
			var instance := _multimesh(KenneyKit.mesh(variant, 0.8, "foliage"), entry[0], entry[1])
			Lod.near(instance, DETAIL_WITHIN)
			holder.add_child(instance)
			if not _batches.has(key):
				_batches[key] = []
			_batches[key].append([instance.multimesh, entry[0]])
	var paint := ShaderMaterial.new()
	paint.shader = load("res://shaders/props.gdshader")
	for key in far:
		for kind in far[key]:
			var entry: Array = far[key][kind]
			var simple := _multimesh(_simple_mesh(str(kind)), entry[0], entry[1], true)
			simple.material_override = paint
			simple.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF   # too far to matter
			Lod.between(simple, DETAIL_WITHIN, SHOW_WITHIN)
			holder.add_child(simple)
			if not _far_batches.has(key):
				_far_batches[key] = []
			_far_batches[key].append([simple.multimesh, entry[0]])


## A tree of a few dozen triangles for the distance, about the Kenney trees' size and shape.
func _simple_mesh(kind: String) -> Mesh:
	if not _simple.has(kind):
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var trunk := CylinderMesh.new()
		trunk.top_radius = 0.04
		trunk.bottom_radius = 0.05
		trunk.height = 0.3
		trunk.radial_segments = 4
		trunk.cap_top = false
		trunk.cap_bottom = false
		st.append_from(trunk, 0, Transform3D(Basis(), Vector3(0, 0.15, 0)))
		if kind == "conifer":
			var cone := CylinderMesh.new()
			cone.top_radius = 0.0
			cone.bottom_radius = 0.22
			cone.height = 0.62
			cone.radial_segments = 6
			cone.cap_top = false
			st.append_from(cone, 0, Transform3D(Basis(), Vector3(0, 0.5, 0)))
		else:
			var crown := SphereMesh.new()
			crown.radius = 0.26 if kind == "leafy" else 0.22
			crown.height = 0.4 if kind == "leafy" else 0.16
			crown.radial_segments = 6
			crown.rings = 3
			st.append_from(crown, 0, Transform3D(Basis(), Vector3(0, 0.52 if kind == "leafy" else 0.62, 0)))
		_simple[kind] = _coloured(st.commit(), 0.28)
	return _simple[kind]


## The Kenney nature kit's trees (CC0), by kind.
const KINDS := {
	"leafy": ["nature/tree_default", "nature/tree_oak", "nature/tree_detailed", "nature/tree_fat"],
	"conifer": ["nature/tree_pineRoundA", "nature/tree_pineTallA", "nature/tree_pineDefaultA", "nature/tree_cone"],
	"palm": ["nature/tree_palm", "nature/tree_palmTall"],
}


## No trees inside cities: clear each circle [pixel, radius] (and restore earlier clearings,
## since one map serves several scenarios).
func clear(circles: Array) -> void:
	for item in _cleared:
		(item[0] as MultiMesh).set_instance_transform(item[1], item[2])
	_cleared.clear()
	var hidden := Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO)
	for circle in circles:
		var centre: Vector3 = earth.ground_at_pixel(circle[0])
		var reach: float = circle[1]
		var near_tile := Vector2i(floori(circle[0].x / NEAR_TILE), floori(circle[0].y / NEAR_TILE))
		var tile := Vector2i(int(circle[0].x / TILE), int(circle[0].y / TILE))
		var span := ceili(reach / NEAR_TILE)
		var batches: Array = []
		for dx in range(-span, span + 1):
			for dy in range(-span, span + 1):
				batches.append_array(_batches.get(near_tile + Vector2i(dx, dy), []))
		for dx in [-1, 0, 1]:
			for dy in [-1, 0, 1]:
				batches.append_array(_far_batches.get(tile + Vector2i(dx, dy), []))
		for batch in batches:
			var transforms: Array = batch[1]
			for i in transforms.size():
				var at: Vector3 = transforms[i].origin
				if Vector2(at.x - centre.x, at.z - centre.z).length() < reach:
					_cleared.append([batch[0], i, transforms[i]])
					(batch[0] as MultiMesh).set_instance_transform(i, hidden)


## A lollipop tree: a brown trunk under a round canopy (canopy takes the instance colour).
func _leafy_tree() -> Mesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.05
	trunk.bottom_radius = 0.07
	trunk.height = 0.35
	trunk.radial_segments = 6
	st.append_from(trunk, 0, Transform3D(Basis(), Vector3(0, 0.17, 0)))
	var canopy := SphereMesh.new()
	canopy.radius = 0.28
	canopy.height = 0.5
	canopy.radial_segments = 8
	canopy.rings = 5
	st.append_from(canopy, 0, Transform3D(Basis(), Vector3(0, 0.55, 0)))
	return _coloured(st.commit(), 0.3)


## A conifer: trunk and two stacked cones.
func _conifer() -> Mesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.04
	trunk.bottom_radius = 0.06
	trunk.height = 0.25
	trunk.radial_segments = 6
	st.append_from(trunk, 0, Transform3D(Basis(), Vector3(0, 0.12, 0)))
	for tier in 2:
		var cone := CylinderMesh.new()
		cone.top_radius = 0.0
		cone.bottom_radius = 0.26 - tier * 0.07
		cone.height = 0.42
		cone.radial_segments = 7
		st.append_from(cone, 0, Transform3D(Basis(), Vector3(0, 0.42 + tier * 0.24, 0)))
	return _coloured(st.commit(), 0.22)


## Marks the trunk brown with a vertex colour; the shader keeps it brown and paints the rest
## with the instance colour. `trunk_top` is the trunk's height.
func _coloured(mesh: Mesh, trunk_top: float) -> Mesh:
	var arrays := mesh.surface_get_arrays(0)
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var colours := PackedColorArray()
	colours.resize(verts.size())
	for i in verts.size():
		colours[i] = Color(1, 0, 0) if verts[i].y < trunk_top else Color(0, 0, 0)
	arrays[Mesh.ARRAY_COLOR] = colours
	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return out


func _multimesh(mesh: Mesh, transforms: Array, colours: Array, custom := false) -> MultiMeshInstance3D:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = not custom  # the leaves' green (trunks keep their own colour)
	mm.use_custom_data = custom   # props.gdshader reads it from there
	mm.mesh = mesh
	mm.instance_count = transforms.size()
	for i in transforms.size():
		mm.set_instance_transform(i, transforms[i])
		if custom:
			mm.set_instance_custom_data(i, colours[i])
		else:
			mm.set_instance_color(i, colours[i])
	var instance := MultiMeshInstance3D.new()
	instance.multimesh = mm
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return instance

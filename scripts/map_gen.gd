class_name MapGen
extends RefCounted
## "Shatterfield": a 144 x 144 m two-player map with 180-degree symmetry.
## Screen up is -z. Player 1 starts bottom-left, player 2 top-right.
## Each base site has 8 golden crystal nodes in an arc and 2 Void Slime piles.

## [center, direction to the resources]; pairs mirror each other.
const SITES := [
	[Vector2(22.5, 121.5), Vector2(-1, 1)],     # 0  P1 main
	[Vector2(121.5, 22.5), Vector2(1, -1)],     # 1  P2 main
	[Vector2(22.5, 80.5), Vector2(-1, 0)],      # 2  P1 natural
	[Vector2(121.5, 63.5), Vector2(1, 0)],      # 3  P2 natural
	[Vector2(63.5, 122.5), Vector2(0, 1)],      # 4  P1 third
	[Vector2(80.5, 21.5), Vector2(0, -1)],      # 5  P2 third
	[Vector2(24.5, 26.5), Vector2(-1, -1)],     # 6  top-left corner
	[Vector2(119.5, 117.5), Vector2(1, 1)],     # 7  bottom-right corner
	[Vector2(56.5, 68.5), Vector2(-1, 0)],      # 8  centre west
	[Vector2(87.5, 75.5), Vector2(1, 0)],       # 9  centre east
]

## Rock blobs on P1's half: [centre, radius]. Mirrored for P2.
const BLOBS := [
	[Vector2(72, 72), 4.5],
	[Vector2(45, 100), 3.5],
	[Vector2(52, 48), 3.0],
	[Vector2(38, 58), 2.5],
	[Vector2(84, 104), 3.0],
	[Vector2(104, 98), 3.5],
	[Vector2(64, 96), 2.0],
	[Vector2(70, 50), 2.5],
]

## Rock models' half-extents (x, z) at scale 1, measured from rock_a/b/c.glb.
const ROCK_EXT := [Vector2(1.42, 1.42), Vector2(1.92, 0.95), Vector2(2.42, 1.42)]
const KEEP_CLEAR := 10.5


static func mirror(v: Vector2, size: int) -> Vector2:
	return Vector2(size, size) - v


static func build_standard(w) -> void:
	var size: int = w.grid.size
	var rock_cells: Dictionary = {}
	# walls round each main, with one wide choke facing its natural
	_ring(rock_cells, SITES[0][0], 20.0, 25.5, -110.0, -70.0, size)
	for b in BLOBS:
		_blob(rock_cells, b[0], b[1], size)
	# P2's half is P1's turned 180 degrees, cell for cell
	for c in rock_cells.keys():
		rock_cells[Vector2i(size - 1 - c.x, size - 1 - c.y)] = true
	# keep base sites and their resources clear
	var keep: Array = []
	for s in SITES:
		keep.append(s[0])
	for c in rock_cells.keys():
		var cp := Vector2(c.x + 0.5, c.y + 0.5)
		var ok := true
		for k in keep:
			if cp.distance_to(k) < KEEP_CLEAR:
				ok = false
				break
		if ok:
			w.grid.set_cell(c, 1, null)
	# base sites and resources
	for i in SITES.size():
		_make_site(w, i, SITES[i][0], (SITES[i][1] as Vector2).normalized())
	# rock models, and the cells under them made solid so nothing walks through
	w.set_meta("rock_spots", _place_rocks(w, keep))
	if w.visuals:
		_terrain(w)
		_rocks_visual(w)


static func _ring(cells: Dictionary, c: Vector2, r0: float, r1: float, gap_a: float, gap_b: float, size: int) -> void:
	for y in range(int(c.y - r1 - 1), int(c.y + r1 + 2)):
		for x in range(int(c.x - r1 - 1), int(c.x + r1 + 2)):
			if x < 0 or y < 0 or x >= size or y >= size:
				continue
			var d := Vector2(x + 0.5, y + 0.5) - c
			var L := d.length()
			if L < r0 or L > r1:
				continue
			var ang := rad_to_deg(atan2(d.y, d.x))
			if ang >= gap_a and ang <= gap_b:
				continue
			cells[Vector2i(x, y)] = true


static func _blob(cells: Dictionary, c: Vector2, r: float, size: int) -> void:
	for y in range(int(c.y - r - 1), int(c.y + r + 2)):
		for x in range(int(c.x - r - 1), int(c.x + r + 2)):
			if x < 1 or y < 1 or x >= size - 1 or y >= size - 1:
				continue
			# slightly lumpy edge
			var d := Vector2(x + 0.5, y + 0.5) - c
			var wob := 1.0 + 0.18 * sin(atan2(d.y, d.x) * 3.0 + c.x)
			if d.length() <= r * wob:
				cells[Vector2i(x, y)] = true


static func _make_site(w, index: int, center: Vector2, dir: Vector2) -> void:
	var cell := Vector2i(int(floor(center.x - 2.5)), int(floor(center.y - 2.5)))
	var site := {"index": index, "center": center, "cell": cell, "dir": dir, "minerals": [], "slimes": [], "taken_by": -1}
	w.sites.append(site)
	var base_ang := atan2(dir.y, dir.x)
	# 8 crystals on an arc
	for k in 8:
		var a := base_ang + deg_to_rad(lerpf(-62.0, 62.0, float(k) / 7.0))
		var rad := 7.2 if k % 2 == 0 else 8.0
		var pos := center + Vector2(cos(a), sin(a)) * rad
		var tangent := Vector2(-sin(a), cos(a))
		var sz := Vector2i(2, 1) if absf(tangent.x) >= absf(tangent.y) else Vector2i(1, 2)
		var c := Vector2i(int(round(pos.x - sz.x * 0.5)), int(round(pos.y - sz.y * 0.5)))
		if not w.grid.rect_free(c, sz):
			continue
		var r = w.spawn_resource("mineral", c, sz, Defs.MINERAL_AMOUNT, (k + index) % 4, index)
		site["minerals"].append(r)
	# two slime piles beyond the ends of the arc
	for side in [-1.0, 1.0]:
		var a := base_ang + deg_to_rad(98.0 * side)
		var pos := center + Vector2(cos(a), sin(a)) * 8.3
		var c := Vector2i(int(round(pos.x - 1.5)), int(round(pos.y - 1.5)))
		if not w.grid.rect_free(c, Vector2i(3, 3)):
			c = w.grid.cell_of(w.grid.nearest_walkable(pos)) - Vector2i(1, 1)
		var r = w.spawn_resource("slime", c, Vector2i(3, 3), Defs.SLIME_AMOUNT, 0, index)
		site["slimes"].append(r)


# ---------------------------------------------------------------- visuals

static func _terrain(w) -> void:
	var size: int = w.grid.size
	# a mask texture: R = rock nearby, G = base plateau
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var k: int = w.grid.kind_at(Vector2i(x, y))
			var r := 1.0 if k == 1 else 0.0
			var g := 0.0
			var cp := Vector2(x + 0.5, y + 0.5)
			for s in w.sites:
				var d: float = cp.distance_to(s["center"])
				g = maxf(g, clampf(1.0 - (d - 8.0) / 6.0, 0.0, 1.0))
			img.set_pixel(x, y, Color(r, g, 0, 1))
	var mask := ImageTexture.create_from_image(img)
	var mesh := PlaneMesh.new()
	var ext := float(size) + 120.0
	mesh.size = Vector2(ext, ext)
	# about one vertex per metre, so the shader can raise mounds and swells
	mesh.subdivide_width = int(ext)
	mesh.subdivide_depth = int(ext)
	var mi := MeshInstance3D.new()
	mi.name = "Ground"
	mi.mesh = mesh
	mi.position = Vector3(size * 0.5, 0, size * 0.5)
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/ground.gdshader")
	sm.set_shader_parameter("mask", mask)
	sm.set_shader_parameter("map_size", float(size))
	mi.material_override = sm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	w.add_child(mi)
	w.set_meta("ground_mask", img)


## Pick every rock model's spot, size and turn (seeded, the same with or
## without visuals), then mark the cells under each one solid. A rock must sit
## mostly on wall cells, and never on a base site or a resource.
static func _place_rocks(w, keep: Array) -> Array:
	var size: int = w.grid.size
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var out: Array = []
	for y in range(0, size, 3):
		for x in range(0, size, 3):
			var c := Vector2i(x + 1, y + 1)
			# P1's half only; every rock gets an exact twin on P2's half
			if c.x + c.y > size - 1 or (c.x + c.y == size - 1 and c.x > c.y):
				continue
			if w.grid.kind_at(c) != 1 or x == 0 or y == 0 or x >= size - 3 or y >= size - 3:
				continue
			var v := rng.randi() % 3
			var yaw := rng.randf() * TAU
			var sc := rng.randf_range(0.85, 1.3)
			var hy := rng.randf_range(0.8, 1.3)
			var q := Vector2(c.x + 0.5 + rng.randf_range(-0.6, 0.6), c.y + 0.5 + rng.randf_range(-0.6, 0.6))
			for attempt in 3:
				var cells := _footprint(q, ROCK_EXT[v] * sc, yaw, size)
				if _fits(w, cells, keep, 0.6):
					_add_pair(w, out, cells, q, v, yaw, sc, hy, size)
					break
				sc *= 0.75
	# a ring of rocks just outside the map edge: top and left, mirrored to
	# bottom and right
	for i in range(-2, size + 3, 4):
		for e in [Vector2(i, -1.5), Vector2(-1.5, i)]:
			var q: Vector2 = e + Vector2(rng.randf_range(-1, 1), rng.randf_range(-1, 1))
			var v := rng.randi() % 3
			var yaw := rng.randf() * TAU
			var sc := rng.randf_range(0.85, 1.3)
			var hy := rng.randf_range(0.8, 1.3)
			var cells := _footprint(q, ROCK_EXT[v] * sc, yaw, size)
			if not _fits(w, cells, keep, 0.0):
				sc *= 0.6
				cells = _footprint(q, ROCK_EXT[v] * sc, yaw, size)
				if not _fits(w, cells, keep, 0.0):
					continue
			_add_pair(w, out, cells, q, v, yaw, sc, hy, size)
	return out


## Places a rock and its twin turned 180 degrees about the map centre. The
## twin's cells are the mirrored cells, so both halves block exactly alike.
static func _add_pair(w, out: Array, cells: Array, q: Vector2, v: int, yaw: float, sc: float, hy: float, size: int) -> void:
	var twin: Array = []
	for c in cells:
		twin.append(Vector2i(size - 1 - c.x, size - 1 - c.y))
	_mark(w, cells)
	_mark(w, twin)
	out.append([q, v, yaw, sc, hy])
	out.append([mirror(q, size), v, yaw + PI, sc, hy])


## Map cells a rock covers: an ellipse turned by yaw, a little generous so the
## visible edge never overhangs a walkable cell.
static func _footprint(q: Vector2, ext: Vector2, yaw: float, size: int) -> Array:
	var ex := ext.x * 0.85 + 0.35
	var ez := ext.y * 0.85 + 0.35
	var r := maxf(ex, ez)
	var cs := cos(yaw)
	var sn := sin(yaw)
	var out: Array = []
	for y in range(int(floor(q.y - r)), int(ceil(q.y + r)) + 1):
		for x in range(int(floor(q.x - r)), int(ceil(q.x + r)) + 1):
			if x < 0 or y < 0 or x >= size or y >= size:
				continue
			var d := Vector2(x + 0.5, y + 0.5) - q
			# Basis(UP, yaw) maps local (lx, lz) to world; this is its inverse
			var lx := cs * d.x - sn * d.y
			var lz := sn * d.x + cs * d.y
			if (lx * lx) / (ex * ex) + (lz * lz) / (ez * ez) <= 1.0:
				out.append(Vector2i(x, y))
	return out


static func _fits(w, cells: Array, keep: Array, min_rock: float) -> bool:
	if cells.is_empty():
		return true
	var rock := 0
	for c in cells:
		var k: int = w.grid.kind_at(c)
		if k == 1:
			rock += 1
			continue
		if k != 0:
			return false
		var cp := Vector2(c.x + 0.5, c.y + 0.5)
		for s in keep:
			if cp.distance_to(s) < KEEP_CLEAR:
				return false
	return float(rock) / float(cells.size()) >= min_rock


static func _mark(w, cells: Array) -> void:
	for c in cells:
		if w.grid.kind_at(c) == 0:
			w.grid.set_cell(c, 1, null)


static func _rocks_visual(w) -> void:
	var spots: Array = w.get_meta("rock_spots", [])
	var meshes: Array = [Models.rock_mesh(0), Models.rock_mesh(1), Models.rock_mesh(2)]
	var per: Array = [[], [], []]
	for s in spots:
		per[int(s[1])].append(s)
	for v in 3:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = meshes[v]
		mm.instance_count = per[v].size()
		for i in per[v].size():
			var s: Array = per[v][i]
			var q: Vector2 = s[0]
			var sc: float = s[3]
			var t := Transform3D(Basis(Vector3.UP, float(s[2])).scaled(Vector3(sc, sc * float(s[4]), sc)), Vector3(q.x, -0.1, q.y))
			mm.set_instance_transform(i, t)
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Rocks%d" % v
		mmi.multimesh = mm
		w.add_child(mmi)

class_name MapGen
extends RefCounted
## Builds a map from its data in Maps: elevation (plateaus, ramps, cliffs), lava and ice,
## rock walls and their models, base sites with their resources, and the ground mesh.
## Only player 1's half is authored; every shape is also placed turned 180 degrees about
## the map centre, cell for cell, so both players get exactly the same ground.
## Each base site has 8 golden crystal nodes in an arc and 2 Void Slime piles.

## Rock models' half-extents (x, z) at scale 1, measured from rock_a/b/c.glb.
const ROCK_EXT := [Vector2(1.42, 1.42), Vector2(1.92, 0.95), Vector2(2.42, 1.42)]
const KEEP_CLEAR := 10.5
const HAZ_LAVA := 1
const HAZ_ICE := 2


static func mirror(v: Vector2, size: int) -> Vector2:
	return Vector2(size, size) - v


## Kept for old callers and tests: the original map.
static func build_standard(w) -> void:
	build(w, "shatterfield")


static func build(w, id: String) -> void:
	var d: Dictionary = Maps.get_def(id)
	var size: int = w.grid.size
	var t: Terrain = w.terrain
	w.map_id = Maps.resolve(id)
	w.theme = Maps.theme_of(id)
	var keep: Array = []
	for s in d["sites"]:
		keep.append(s[0])
		keep.append(mirror(s[0], size))
	# elevation
	for pl in d["plateaus"]:
		if pl[0] == "disc":
			t.plateau_disc(pl[1], float(pl[2]), int(pl[3]))
		else:
			t.plateau_poly(PackedVector2Array(pl[1]), int(pl[2]))
	t.symmetrize()
	for r in d["ramps"]:
		t.add_ramp(r[0], r[1], float(r[2]))
		t.add_ramp(mirror(r[0], size), mirror(r[1], size), float(r[2]))
	# lava blocks like rock; ice is only a look
	var haz := PackedByteArray()
	haz.resize(size * size)
	haz.fill(0)
	for h in d["hazards"]:
		var kind := HAZ_LAVA if h[0] == "lava" else HAZ_ICE
		if h[1] == "disc":
			_haz_disc(haz, h[2], float(h[3]), kind, size)
		else:
			_haz_river(haz, h, false, kind, size)
	for y in size:
		for x in size:
			var i := y * size + x
			var j := (size - 1 - y) * size + (size - 1 - x)
			var top := maxi(haz[i], haz[j])
			haz[i] = top
			haz[j] = top
	w.hazard = haz
	# rock walls, on player 1's half, then mirrored
	var rock_cells: Dictionary = {}
	for b in d["rocks"]:
		_blob(rock_cells, b[0], b[1], size)
	for c in rock_cells.keys():
		rock_cells[Vector2i(size - 1 - c.x, size - 1 - c.y)] = true
	for c in rock_cells.keys():
		if t.is_ramp(c):
			continue
		var cp := Vector2(c.x + 0.5, c.y + 0.5)
		var ok := true
		for k in keep:
			if cp.distance_to(k) < KEEP_CLEAR:
				ok = false
				break
		if ok:
			w.grid.set_cell(c, 1, null)
	for y in size:
		for x in size:
			if haz[y * size + x] == HAZ_LAVA:
				w.grid.set_cell(Vector2i(x, y), 1, null)
	# cliffs become rock in the grid
	t.finish(w.grid)
	# base sites and resources, in mirrored pairs: 0 and 1 are the two mains
	var idx := 0
	for s in d["sites"]:
		var dir: Vector2 = (s[1] as Vector2).normalized()
		_make_site(w, idx, s[0], dir)
		_make_site(w, idx + 1, mirror(s[0], size), -dir)
		idx += 2
	# rock models, and the cells under them made solid so nothing walks through
	w.set_meta("rock_spots", _place_rocks(w, keep, int(d.get("seed", 7))))
	if w.visuals:
		_terrain(w)
		_rocks_visual(w)


static func _m(q: Vector2, m: bool, size: int) -> Vector2:
	return mirror(q, size) if m else q


static func _haz_disc(haz: PackedByteArray, c: Vector2, r: float, kind: int, size: int) -> void:
	for y in range(int(c.y - r - 2), int(c.y + r + 3)):
		for x in range(int(c.x - r - 2), int(c.x + r + 3)):
			if x < 1 or y < 1 or x >= size - 1 or y >= size - 1:
				continue
			var d := Vector2(x + 0.5, y + 0.5) - c
			var wob := 1.0 + 0.12 * sin(atan2(d.y, d.x) * 4.0 + c.y * 0.3)
			if d.length() <= r * wob:
				haz[y * size + x] = kind


## A river along a polyline, with gaps (fords and bridges) left dry.
static func _haz_river(haz: PackedByteArray, h: Array, m: bool, kind: int, size: int) -> void:
	var pts: Array = []
	for q in h[2]:
		pts.append(_m(q, m, size))
	var hw: float = h[3]
	var gaps: Array = []
	for g in h[4]:
		gaps.append([_m(g[0], m, size), float(g[1])])
	for y in range(1, size - 1):
		for x in range(1, size - 1):
			var cp := Vector2(x + 0.5, y + 0.5)
			var best := INF
			for i in pts.size() - 1:
				var q := Geometry2D.get_closest_point_to_segment(cp, pts[i], pts[i + 1])
				best = minf(best, cp.distance_to(q))
			# a little meander in the width
			var wob := 1.0 + 0.22 * sin(cp.x * 0.21 + cp.y * 0.13)
			if best > hw * wob:
				continue
			var dry := false
			for g in gaps:
				if cp.distance_to(g[0]) < g[1]:
					dry = true
					break
			if not dry:
				haz[y * size + x] = kind


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
	var t: Terrain = w.terrain
	var th: Dictionary = w.theme
	# a mask texture: R = rock wall, G = base plateau, B = lava (1) or ice (0.5)
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var c := Vector2i(x, y)
			var hz: int = w.hazard[y * size + x]
			var k: int = w.grid.kind_at(c)
			var r := 1.0 if (k == 1 and hz != HAZ_LAVA and not t.is_cliff(c)) else 0.0
			var g := 0.0
			var cp := Vector2(x + 0.5, y + 0.5)
			for s in w.sites:
				var dd: float = cp.distance_to(s["center"])
				g = maxf(g, clampf(1.0 - (dd - 8.0) / 6.0, 0.0, 1.0))
			var b := 1.0 if hz == HAZ_LAVA else (0.5 if hz == HAZ_ICE else 0.0)
			img.set_pixel(x, y, Color(r, g, b, 1))
	w.set_meta("ground_mask", img.duplicate())
	# soften the cell steps so lava banks and lake shores curve instead of stair-stepping
	var soft := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var acc := Color(0, 0, 0, 0)
			var wsum := 0.0
			for dy in [-1, 0, 1]:
				for dx in [-1, 0, 1]:
					var xx := clampi(x + dx, 0, size - 1)
					var yy := clampi(y + dy, 0, size - 1)
					var wt := 4.0 if (dx == 0 and dy == 0) else (2.0 if (dx == 0 or dy == 0) else 1.0)
					acc += img.get_pixel(xx, yy) * wt
					wsum += wt
			var c0 := img.get_pixel(x, y)
			var bl := acc / wsum
			soft.set_pixel(x, y, Color(bl.r, c0.g, bl.b, 1))
	img = soft
	var mask := ImageTexture.create_from_image(img)
	var hmap := ImageTexture.create_from_image(t.height_image())
	var mesh := PlaneMesh.new()
	var ext := float(size) + 120.0
	mesh.size = Vector2(ext, ext)
	# one vertex per metre, on whole-metre corners, so the mesh matches Terrain exactly
	mesh.subdivide_width = int(ext) - 1
	mesh.subdivide_depth = int(ext) - 1
	var mi := MeshInstance3D.new()
	mi.name = "Ground"
	mi.mesh = mesh
	mi.position = Vector3(size * 0.5, 0, size * 0.5)
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/ground.gdshader")
	sm.set_shader_parameter("mask", mask)
	sm.set_shader_parameter("hmap", hmap)
	sm.set_shader_parameter("map_size", float(size))
	for key in ["dust", "rust", "basalt", "vein", "plate", "cliff_a", "cliff_b", "hazard"]:
		sm.set_shader_parameter(key, th[key])
	for key in ["snow", "hazard_glow", "vein_glow"]:
		sm.set_shader_parameter(key, float(th[key]))
	sm.set_shader_parameter("vein_w", float(th.get("vein_w", 0.014)))
	sm.set_shader_parameter("vein_mix", float(th.get("vein_mix", 0.35)))
	mi.material_override = sm
	# cliffs throw shadows onto the ground below them
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if t.max_level > 0 else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.extra_cull_margin = 8.0
	w.add_child(mi)
	w.set_meta("height_tex", hmap)


## Pick every rock model's spot, size and turn (seeded, the same with or
## without visuals), then mark the cells under each one solid. A rock must sit
## mostly on wall cells, and never on a base site, a resource, a ramp or a cliff.
static func _place_rocks(w, keep: Array, seed_v: int) -> Array:
	var size: int = w.grid.size
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_v
	var out: Array = []
	for y in range(0, size, 3):
		for x in range(0, size, 3):
			var c := Vector2i(x + 1, y + 1)
			# P1's half only; every rock gets an exact twin on P2's half
			if c.x + c.y > size - 1 or (c.x + c.y == size - 1 and c.x > c.y):
				continue
			if not _wall(w, c) or x == 0 or y == 0 or x >= size - 3 or y >= size - 3:
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


## A rock-wall cell: rock in the grid that isn't a cliff or lava.
static func _wall(w, c: Vector2i) -> bool:
	if w.grid.kind_at(c) != 1 or w.terrain.is_cliff(c):
		return false
	if c.x >= 0 and c.y >= 0 and c.x < w.grid.size and c.y < w.grid.size and w.hazard[c.y * w.grid.size + c.x] == HAZ_LAVA:
		return false
	return true


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
	var t: Terrain = w.terrain
	for c in cells:
		if t.is_cliff(c) or t.is_ramp(c):
			return false
		if w.hazard[c.y * w.grid.size + c.x] != 0:
			return false
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
	# a rock stands on one level, never across a cliff
	var h0 := t.height_at(Vector2(cells[0].x + 0.5, cells[0].y + 0.5))
	for c in cells:
		if absf(t.height_at(Vector2(c.x + 0.5, c.y + 0.5)) - h0) > 0.3:
			return false
	return float(rock) / float(cells.size()) >= min_rock


static func _mark(w, cells: Array) -> void:
	for c in cells:
		if w.grid.kind_at(c) == 0:
			w.grid.set_cell(c, 1, null)


static func _rocks_visual(w) -> void:
	var spots: Array = w.get_meta("rock_spots", [])
	var meshes: Array = [Models.rock_mesh(0), Models.rock_mesh(1), Models.rock_mesh(2)]
	var tint: Color = w.theme.get("rock_tint", Color(1, 1, 1))
	var per: Array = [[], [], []]
	for s in spots:
		per[int(s[1])].append(s)
	for v in 3:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = meshes[v] if tint == Color(1, 1, 1) else Models.tinted_mesh(meshes[v], tint)
		mm.instance_count = per[v].size()
		for i in per[v].size():
			var s: Array = per[v][i]
			var q: Vector2 = s[0]
			var sc: float = s[3]
			var y: float = w.terrain.height_at(q) - 0.1
			var t := Transform3D(Basis(Vector3.UP, float(s[2])).scaled(Vector3(sc, sc * float(s[4]), sc)), Vector3(q.x, y, q.y))
			mm.set_instance_transform(i, t)
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Rocks%d" % v
		mmi.multimesh = mm
		w.add_child(mmi)

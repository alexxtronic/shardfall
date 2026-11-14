class_name Terrain
extends RefCounted
## Elevation. Every map cell sits on level 0, 1 or 2, LEVEL_H metres apart. Plateaus are edged
## by a two-cell cliff band (one cell each side of the step) that nothing walks on (marked rock in the PathGrid); ramps are
## walkable slopes cut through the band, with walls along their sides.
##
## Heights are stored at cell corners and read back bilinearly. The ground mesh has one vertex
## per corner and samples the same numbers, so units stand exactly on the ground you see.
##
## Gameplay: a ground unit can't see up a cliff (fog of war), and a ground shot fired up at a
## higher target misses UPHILL_MISS of the time. Both maps sides are mirror images, so this
## changes tactics, not balance.

const LEVEL_H := 2.6
const UPHILL_MISS := 0.3
const STEP := 0.5        # a height change bigger than this between neighbours is a wall

var size: int
var level := PackedByteArray()       # per cell: 0, 1 or 2
var ramp_of := PackedInt32Array()    # per cell: ramp index + 1, or 0
var cliff := PackedByteArray()       # per cell: 1 on the cliff band and ramp walls
var corner := PackedFloat32Array()   # (size + 1)^2 heights at cell corners
var ramps: Array = []                # {a, b, width, ha, hb}
var max_level: int = 0


func _init(n: int) -> void:
	size = n
	level.resize(n * n)
	level.fill(0)
	ramp_of.resize(n * n)
	ramp_of.fill(0)
	cliff.resize(n * n)
	cliff.fill(0)
	corner.resize((n + 1) * (n + 1))
	corner.fill(0.0)


func idx(x: int, y: int) -> int:
	return y * size + x


func inside(x: int, y: int) -> bool:
	return x >= 0 and y >= 0 and x < size and y < size


# ---------------------------------------------------------------- authoring

## Raise every cell whose centre is inside a disc (with a lumpy edge) to at least `lvl`.
func plateau_disc(c: Vector2, r: float, lvl: int, wobble: float = 0.08) -> void:
	for y in range(int(c.y - r - 2), int(c.y + r + 3)):
		for x in range(int(c.x - r - 2), int(c.x + r + 3)):
			if not inside(x, y):
				continue
			var d := Vector2(x + 0.5, y + 0.5) - c
			var wob := 1.0 + wobble * sin(atan2(d.y, d.x) * 5.0 + c.x * 0.37)
			if d.length() <= r * wob:
				_raise(x, y, lvl)


## Raise every cell inside a polygon (map coordinates) to at least `lvl`. The edge is
## roughened by up to `wobble` metres so long sides don't read as ruled lines.
func plateau_poly(pts: PackedVector2Array, lvl: int, wobble: float = 1.4) -> void:
	var lo := pts[0]
	var hi := pts[0]
	for q in pts:
		lo = lo.min(q)
		hi = hi.max(q)
	var w := ceili(wobble) + 1
	for y in range(int(lo.y) - w, int(hi.y) + w + 1):
		for x in range(int(lo.x) - w, int(hi.x) + w + 1):
			if not inside(x, y):
				continue
			var c := Vector2(x + 0.5, y + 0.5)
			var j := Vector2(sin(c.y * 0.41 + 1.3) + 0.5 * sin(c.y * 0.97 + 0.4),
				sin(c.x * 0.37 + 2.1) + 0.5 * sin(c.x * 1.07 + 0.9)) * (wobble / 1.5)
			if Geometry2D.is_point_in_polygon(c + j, pts):
				_raise(x, y, lvl)


func _raise(x: int, y: int, lvl: int) -> void:
	var i := idx(x, y)
	if level[i] < lvl:
		level[i] = lvl
	max_level = maxi(max_level, lvl)


## Copy the levels onto the other half turned 180 degrees, cell for cell (maps author
## player 1's half only, so both sides end up identical).
func symmetrize() -> void:
	for y in size:
		for x in size:
			var i := idx(x, y)
			var j := idx(size - 1 - x, size - 1 - y)
			var top := maxi(level[i], level[j])
			level[i] = top
			level[j] = top


## A ramp from its low end `a` to its high end `b` (centres of the two ends), `width` metres
## across. Its end heights are the levels found under a and b when the terrain is finished.
func add_ramp(a: Vector2, b: Vector2, width: float) -> void:
	ramps.append({"a": a, "b": b, "width": width, "ha": 0.0, "hb": 0.0})


# ---------------------------------------------------------------- finishing

## Resolve ramps, cliff bands and corner heights, and block the cliff cells in the grid.
func finish(grid) -> void:
	# ramp end heights come from the plateau levels under each end
	for k in ramps.size():
		var r: Dictionary = ramps[k]
		r["ha"] = float(_level_xy(r["a"])) * LEVEL_H
		r["hb"] = float(_level_xy(r["b"])) * LEVEL_H
	# ramp cells
	for k in ramps.size():
		var r: Dictionary = ramps[k]
		var a: Vector2 = r["a"]
		var b: Vector2 = r["b"]
		var L := a.distance_to(b)
		var dir := (b - a) / L
		var side := Vector2(-dir.y, dir.x)
		var half := float(r["width"]) * 0.5
		var lo := a.min(b) - Vector2(half + 1, half + 1)
		var hi := a.max(b) + Vector2(half + 1, half + 1)
		for y in range(int(lo.y), int(hi.y) + 1):
			for x in range(int(lo.x), int(hi.x) + 1):
				if not inside(x, y):
					continue
				var d := Vector2(x + 0.5, y + 0.5) - a
				var along := d.dot(dir)
				if along >= 0.0 and along <= L and absf(d.dot(side)) <= half:
					ramp_of[idx(x, y)] = k + 1
	# cliff band: both cells of any big step between neighbours, and every cell beside a
	# ramp whose height doesn't match the ramp next to it
	for y in size:
		for x in size:
			var i := idx(x, y)
			if ramp_of[i] != 0:
				continue
			var h := float(level[i]) * LEVEL_H
			var wall := false
			for dy in [-1, 0, 1]:
				for dx in [-1, 0, 1]:
					if (dx == 0 and dy == 0) or not inside(x + dx, y + dy):
						continue
					var j := idx(x + dx, y + dy)
					if ramp_of[j] != 0:
						if absf(cell_h(x + dx, y + dy) - h) > STEP:
							wall = true
					elif absf(float(level[j]) * LEVEL_H - h) > STEP:
						wall = true
			if wall:
				cliff[i] = 1
	# corner heights
	var n1 := size + 1
	for y in n1:
		for x in n1:
			corner[y * n1 + x] = _corner_h(x, y)
	if grid:
		for y in size:
			for x in size:
				if cliff[idx(x, y)] == 1:
					grid.set_cell(Vector2i(x, y), 1, null)


func _level_xy(q: Vector2) -> int:
	var x := clampi(int(floor(q.x)), 0, size - 1)
	var y := clampi(int(floor(q.y)), 0, size - 1)
	return level[idx(x, y)]


## The height a cell's centre stands at: a ramp's slope, or its level.
func cell_h(x: int, y: int) -> float:
	var i := idx(x, y)
	if ramp_of[i] != 0:
		return ramp_h(ramp_of[i] - 1, Vector2(x + 0.5, y + 0.5))
	return float(level[i]) * LEVEL_H


func ramp_h(k: int, q: Vector2) -> float:
	var r: Dictionary = ramps[k]
	var a: Vector2 = r["a"]
	var b: Vector2 = r["b"]
	var t := clampf((q - a).dot(b - a) / a.distance_squared_to(b), 0.0, 1.0)
	# eased at both ends so the slope meets the flat ground smoothly
	t = t * t * (3.0 - 2.0 * t)
	return lerpf(float(r["ha"]), float(r["hb"]), t)


## A corner touching a ramp takes the ramp's height there. A corner touching ground off the
## cliff band takes the lowest such ground round it, so plateau tops and low ground stay
## flat. A corner inside the band takes the average round it, so the cliff face slopes down
## across both band cells.
func _corner_h(x: int, y: int) -> float:
	var low := INF
	var band := 0.0
	var nb := 0
	for c in [Vector2i(x - 1, y - 1), Vector2i(x, y - 1), Vector2i(x - 1, y), Vector2i(x, y)]:
		if not inside(c.x, c.y):
			continue
		var i := idx(c.x, c.y)
		if ramp_of[i] != 0:
			return ramp_h(ramp_of[i] - 1, Vector2(x, y))
		var h := float(level[i]) * LEVEL_H
		if cliff[i] == 1:
			band += h
			nb += 1
		else:
			low = minf(low, h)
	if low < INF:
		return low
	return band / float(nb) if nb > 0 else 0.0


# ---------------------------------------------------------------- queries

## Ground height at a map point (bilinear between corners, like the mesh).
func height_at(q: Vector2) -> float:
	var fx := clampf(q.x, 0.0, float(size) - 0.001)
	var fy := clampf(q.y, 0.0, float(size) - 0.001)
	var x := int(fx)
	var y := int(fy)
	var tx := fx - x
	var ty := fy - y
	var n1 := size + 1
	var h00 := corner[y * n1 + x]
	var h10 := corner[y * n1 + x + 1]
	var h01 := corner[(y + 1) * n1 + x]
	var h11 := corner[(y + 1) * n1 + x + 1]
	return lerpf(lerpf(h00, h10, tx), lerpf(h01, h11, tx), ty)


## The level a point counts as for vision: a ramp's lower half is the low level.
func level_at(q: Vector2) -> int:
	return int(floor(height_at(q) / LEVEL_H + 0.45))


func is_ramp(c: Vector2i) -> bool:
	return inside(c.x, c.y) and ramp_of[idx(c.x, c.y)] != 0


func is_cliff(c: Vector2i) -> bool:
	return inside(c.x, c.y) and cliff[idx(c.x, c.y)] == 1


## True when a ground shot from `from` at `to` goes up a cliff.
func uphill(from: Vector2, to: Vector2) -> bool:
	return level_at(to) > level_at(from)


## The corner heights as a half-float texture for the ground and fog shaders (half floats
## filter linearly on every GPU; 32-bit float textures often do not on mobile).
func height_image() -> Image:
	var n1 := size + 1
	var img := Image.create(n1, n1, false, Image.FORMAT_RH)
	for y in n1:
		for x in n1:
			img.set_pixel(x, y, Color(corner[y * n1 + x], 0, 0))
	return img

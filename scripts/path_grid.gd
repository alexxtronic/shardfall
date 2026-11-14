class_name PathGrid
extends RefCounted
## The walkable grid: 1 m cells over the whole map. Rocks, buildings and
## resource nodes make cells solid. Ground units path with A* and then pull the
## path tight with line-of-sight checks.

var size: int
var astar := AStarGrid2D.new()
var solid := PackedByteArray()   # 0 free, 1 rock, 2 building, 3 resource
var occupant: Array = []          # building or resource node per cell (or null)


func _init(map_size: int) -> void:
	size = map_size
	solid.resize(size * size)
	solid.fill(0)
	occupant.resize(size * size)
	astar.region = Rect2i(0, 0, size, size)
	astar.cell_size = Vector2(1, 1)
	astar.offset = Vector2(0.5, 0.5)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.default_compute_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.default_estimate_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.update()
	# map border is rock
	for i in size:
		for c in [Vector2i(i, 0), Vector2i(i, size - 1), Vector2i(0, i), Vector2i(size - 1, i)]:
			set_cell(c, 1, null)


func inside(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < size and c.y < size


func idx(c: Vector2i) -> int:
	return c.y * size + c.x


func cell_of(p: Vector2) -> Vector2i:
	return Vector2i(int(floor(p.x)), int(floor(p.y)))


func center_of(c: Vector2i) -> Vector2:
	return Vector2(c.x + 0.5, c.y + 0.5)


func set_cell(c: Vector2i, kind: int, who) -> void:
	if not inside(c):
		return
	solid[idx(c)] = kind
	occupant[idx(c)] = who
	astar.set_point_solid(c, kind != 0)


func set_rect(origin: Vector2i, sz: Vector2i, kind: int, who) -> void:
	for y in sz.y:
		for x in sz.x:
			set_cell(origin + Vector2i(x, y), kind, who)


func walkable(c: Vector2i) -> bool:
	return inside(c) and solid[idx(c)] == 0


func walkable_p(p: Vector2) -> bool:
	return walkable(cell_of(p))


func kind_at(c: Vector2i) -> int:
	if not inside(c):
		return 1
	return solid[idx(c)]


func who_at(c: Vector2i):
	if not inside(c):
		return null
	return occupant[idx(c)]


func rect_free(origin: Vector2i, sz: Vector2i) -> bool:
	for y in sz.y:
		for x in sz.x:
			if not walkable(origin + Vector2i(x, y)):
				return false
	return true


## The nearest walkable cell to p (spiral search).
func nearest_walkable(p: Vector2, max_r: int = 24) -> Vector2:
	var c := cell_of(p)
	if walkable(c):
		return p
	var best := p
	var best_d := INF
	for r in range(1, max_r):
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if absi(dx) != r and absi(dy) != r:
					continue
				var cc := c + Vector2i(dx, dy)
				if walkable(cc):
					var cp := center_of(cc)
					var d := cp.distance_squared_to(p)
					if d < best_d:
						best_d = d
						best = cp
		if best_d < INF:
			return best
	return p


## A path from a to b as world points, pulled tight. The first point is a.
func find_path(a: Vector2, b: Vector2, radius: float = 0.4) -> PackedVector2Array:
	var start := nearest_walkable(a, 6)
	var goal := nearest_walkable(b)
	var sc := cell_of(start)
	var gc := cell_of(goal)
	var out := PackedVector2Array()
	out.append(a)
	if line_clear(a, goal, radius):
		out.append(goal)
		return out
	var raw: PackedVector2Array = astar.get_point_path(sc, gc, true)
	if raw.size() == 0:
		out.append(goal)
		return out
	# replace the last cell centre with the exact goal when it's reachable
	if cell_of(raw[raw.size() - 1]) == gc:
		raw[raw.size() - 1] = goal
	# string pulling
	var anchor := a
	var i := 0
	while i < raw.size():
		var j := raw.size() - 1
		var advanced := false
		while j > i:
			if line_clear(anchor, raw[j], radius):
				out.append(raw[j])
				anchor = raw[j]
				i = j + 1
				advanced = true
				break
			j -= 1
		if not advanced:
			out.append(raw[i])
			anchor = raw[i]
			i += 1
	return out


## True when a disc of `radius` can slide from a to b without touching solid cells.
func line_clear(a: Vector2, b: Vector2, radius: float = 0.4) -> bool:
	var d := b - a
	var L := d.length()
	if L < 0.001:
		return walkable_p(a)
	var dir := d / L
	var perp := Vector2(-dir.y, dir.x) * (radius * 0.85)
	var steps := int(ceil(L / 0.4))
	for s in steps + 1:
		var p := a + dir * (L * float(s) / float(steps))
		if not walkable_p(p) or not walkable_p(p + perp) or not walkable_p(p - perp):
			return false
	return true

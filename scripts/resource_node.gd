class_name ResourceNode
extends Entity
## A golden spike crystal (minerals) or a black Void Slime pile. Slime needs an
## extractor (Void Machine / Void Maw) built on top before workers can draw it.

var kind: String = "mineral"   # "mineral" or "slime"
var amount: int = 0
var start_amount: int = 0
var cell: Vector2i
var cells: Vector2i = Vector2i(2, 1)
var miner = null               # the worker mining it now
var extractor = null           # Building on a slime pile
var site_index: int = -1       # which base site it belongs to


func setup(w, k: String, c: Vector2i, sz: Vector2i, amt: int) -> void:
	world = w
	kind = k
	cell = c
	cells = sz
	amount = amt
	start_amount = amt
	is_resource = true
	owner_id = -1
	def_id = "crystal" if k == "mineral" else "slime_pile"
	p = Vector2(c.x + sz.x * 0.5, c.y + sz.y * 0.5)
	radius = max(sz.x, sz.y) * 0.5
	height = 1.6 if k == "mineral" else 0.7
	max_hp = 1.0
	hp = 1.0
	position = Vector3(p.x, ground_h(), p.y)


## Closest point on the node's rectangle to q (where a worker stands to mine).
func edge_point(q: Vector2) -> Vector2:
	var mn := Vector2(cell.x, cell.y)
	var mx := mn + Vector2(cells.x, cells.y)
	return Vector2(clampf(q.x, mn.x, mx.x), clampf(q.y, mn.y, mx.y))


func dist_to(q: Vector2) -> float:
	return q.distance_to(edge_point(q))


func take(n: int) -> int:
	var got: int = mini(n, amount)
	amount -= got
	if amount <= 0 and kind == "mineral" and world:
		world.deplete(self)
	return got


func status_text() -> String:
	if kind == "mineral":
		return "Golden crystals: %d" % amount
	return "Void Slime: %d" % amount

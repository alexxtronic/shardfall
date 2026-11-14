class_name Building
extends Entity
## A structure: constructs itself once a worker places it, then trains units
## from a queue of up to five. Main bases also take in resources.

const QUEUE_MAX := 5

var cell: Vector2i
var size: int = 3
var slot: String = ""
var built: bool = false
var progress: float = 0.0      # construction, 0..1
var build_time: float = 30.0
var queue: Array = []          # unit ids
var prod_t: float = 0.0
var rally_set: bool = false
var rally: Vector2 = Vector2.ZERO
var rally_node = null          # a resource node or entity to rally onto
var slime_node = null          # ResourceNode under an extractor
var occupant = null            # worker inside an extractor
var seen: bool = false         # the human has seen it (fog memory)
var anim_t: float = 0.0


func setup(w, id: String, owner: int, c: Vector2i) -> void:
	setup_common(w, id, owner)
	is_building = true
	cell = c
	size = int(def["size"])
	slot = String(def["slot"])
	build_time = float(def["time"])
	radius = size * 0.5
	height = float(def.get("model_h", 3.0))
	p = Vector2(c.x + size * 0.5, c.y + size * 0.5)
	position = Vector3(p.x, 0, p.y)


func is_main() -> bool:
	return slot == "main"


func produces() -> Array:
	return def.get("produces", [])


func start_construction() -> void:
	built = false
	progress = 0.0
	hp = max_hp * 0.1


func finish_instantly() -> void:
	built = true
	progress = 1.0
	hp = max_hp


func step(dt: float) -> void:
	if dead:
		return
	if not built:
		progress += dt / build_time
		hp = minf(max_hp, hp + max_hp * 0.9 * dt / build_time)
		if progress >= 1.0:
			progress = 1.0
			built = true
			world.on_building_done(self)
		return
	if queue.size() > 0:
		prod_t += dt
		var ud: Dictionary = Defs.units[queue[0]]
		if prod_t >= float(ud["time"]):
			var uid: String = queue.pop_front()
			prod_t = 0.0
			world.spawn_from(self, uid)


func queue_progress() -> float:
	if queue.is_empty():
		return 0.0
	var ud: Dictionary = Defs.units[queue[0]]
	return clampf(prod_t / float(ud["time"]), 0.0, 1.0)


## Where new units appear: just outside the front (+z) edge.
func exit_point() -> Vector2:
	var front := Vector2(p.x, cell.y + size + 0.7)
	if rally_set:
		var d := (rally - p)
		if d.length() > 0.1:
			d = d.normalized()
			front = p + d * (size * 0.5 + 0.9)
	return world.grid.nearest_walkable(front)


## Closest point on the footprint to q.
func edge_point(q: Vector2) -> Vector2:
	var mn := Vector2(cell.x, cell.y)
	var mx := mn + Vector2(size, size)
	return Vector2(clampf(q.x, mn.x, mx.x), clampf(q.y, mn.y, mx.y))


func dist_to(q: Vector2) -> float:
	return q.distance_to(edge_point(q))


func status_text() -> String:
	if not built:
		return "Building %d%%" % int(progress * 100.0)
	if queue.size() > 0:
		return "Training %s %d%%" % [Defs.units[queue[0]]["name"], int(queue_progress() * 100.0)]
	if slot == "extractor" and slime_node:
		return "Void Slime left: %d" % slime_node.amount
	return ""

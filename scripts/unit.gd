class_name Unit
extends Entity
## A unit: moves along grid paths (or flies straight), fights, and if it's a
## worker, gathers resources and places buildings.

enum O { IDLE, MOVE, AMOVE, ATTACK, HOLD, GATHER, BUILD }

const ACQUIRE_EVERY := 0.3
const LEASH := 9.0

var slot: String = ""
var speed: float = 3.0
var weapon: Dictionary = {}
var fly: float = 0.0
var supply: int = 1

var order: int = O.IDLE
var goal: Vector2 = Vector2.ZERO
var anchor: Vector2 = Vector2.ZERO      # where an idle unit stands guard
var target = null                       # Entity being attacked
var path := PackedVector2Array()
var path_i: int = 0
var arrive_tol: float = 0.4
var moving: bool = false
var vel: Vector2 = Vector2.ZERO
var facing: float = 0.0
var cd: float = 0.0
var acq_t: float = 0.0
var repath_t: float = 0.0
var stuck_t: float = 0.0
var stuck_count: int = 0
var last_prog_p: Vector2 = Vector2.ZERO
var attack_anim: float = 0.0
var walk_phase: float = 0.0

# worker
var is_worker: bool = false
var gstate: String = ""                 # to_node, mining, to_base, wait, inside
var gnode = null                        # ResourceNode (mineral) or extractor Building (slime)
var gtimer: float = 0.0
var carry_kind: String = ""
var carry: int = 0
var build_id: String = ""
var build_cell: Vector2i
var resume_node = null                  # job to go back to after building
var hidden_inside: bool = false


func setup(w, id: String, owner: int, at: Vector2) -> void:
	setup_common(w, id, owner)
	is_unit = true
	slot = String(def["slot"])
	speed = float(def["speed"])
	radius = float(def["radius"])
	weapon = def["weapon"]
	is_air = bool(def["air"])
	fly = float(def.get("fly", 0.0))
	supply = int(def["supply"])
	is_worker = slot == "worker"
	height = float(def.get("model_h", 1.0)) + fly
	p = at
	anchor = at
	goal = at
	acq_t = randf() * ACQUIRE_EVERY
	position = Vector3(p.x, fly, p.y)


# ---------------------------------------------------------------- orders

func clear_job() -> void:
	if gnode and gnode is ResourceNode and gnode.miner == self:
		gnode.miner = null
	if gnode and gnode is Building and gnode.occupant == self:
		gnode.occupant = null
	if hidden_inside:
		_exit_extractor()
	gstate = ""


func cmd_move(to: Vector2, attack_move: bool = false, shared_path: PackedVector2Array = PackedVector2Array()) -> void:
	clear_job()
	if is_worker and build_id != "":
		world.refund_build(self)
	order = O.AMOVE if attack_move else O.MOVE
	target = null
	set_goal(to, shared_path)


func cmd_attack(t: Entity) -> void:
	clear_job()
	if is_worker and build_id != "":
		world.refund_build(self)
	order = O.ATTACK
	target = t
	repath_t = 0.0
	path = PackedVector2Array()


func cmd_stop() -> void:
	clear_job()
	if is_worker and build_id != "":
		world.refund_build(self)
	order = O.IDLE
	target = null
	moving = false
	anchor = p
	path = PackedVector2Array()


func cmd_hold() -> void:
	cmd_stop()
	order = O.HOLD


func cmd_gather(node) -> void:
	if not is_worker:
		return
	clear_job()
	if build_id != "":
		world.refund_build(self)
	order = O.GATHER
	target = null
	gnode = node
	if carry > 0:
		gstate = "to_base"
		_go_to_base()
	else:
		gstate = "to_node"
		set_goal(_node_spot(node))


func cmd_build(bid: String, c: Vector2i) -> void:
	var prev = gnode if order == O.GATHER else null
	clear_job()
	order = O.BUILD
	target = null
	build_id = bid
	build_cell = c
	resume_node = prev
	var bd: Dictionary = Defs.buildings[bid]
	var sz: int = int(bd["size"])
	var center := Vector2(c.x + sz * 0.5, c.y + sz * 0.5)
	set_goal(center)


func set_goal(to: Vector2, shared_path: PackedVector2Array = PackedVector2Array()) -> void:
	goal = to
	moving = true
	stuck_t = 0.0
	stuck_count = 0
	last_prog_p = p
	path_i = 1
	if is_air:
		path = PackedVector2Array([p, to])
	elif shared_path.size() >= 2:
		path = shared_path.duplicate()
		path[0] = p
		path[path.size() - 1] = to
	else:
		path = world.grid.find_path(p, to, radius)


# ---------------------------------------------------------------- step

func step(dt: float) -> void:
	if dead:
		return
	cd -= dt
	attack_anim = maxf(0.0, attack_anim - dt)
	match order:
		O.IDLE:
			_step_idle(dt)
		O.HOLD:
			_step_hold(dt)
		O.MOVE:
			if _follow(dt):
				_arrive()
		O.AMOVE:
			_step_amove(dt)
		O.ATTACK:
			_step_attack(dt)
		O.GATHER:
			_step_gather(dt)
		O.BUILD:
			_step_build(dt)


func _arrive() -> void:
	order = O.IDLE
	moving = false
	anchor = p
	target = null


func _step_idle(dt: float) -> void:
	moving = false
	if is_worker:
		return
	if target != null and _valid_target(target):
		# chase within a leash of where we stood
		if p.distance_to(anchor) > LEASH and not _in_range(target):
			target = null
			set_goal(anchor)
			order = O.MOVE
			return
		_engage(dt, true)
		return
	target = null
	acq_t -= dt
	if acq_t <= 0.0:
		acq_t = ACQUIRE_EVERY
		target = world.find_target(self, sight)
	if target == null and p.distance_to(anchor) > 1.5:
		set_goal(anchor)
		order = O.MOVE


func _step_hold(dt: float) -> void:
	moving = false
	if target != null and _valid_target(target) and _in_range(target):
		_fire_at(target, dt)
		return
	target = null
	acq_t -= dt
	if acq_t <= 0.0:
		acq_t = ACQUIRE_EVERY
		var t = world.find_target(self, _wrange() + radius + 1.5)
		if t and _in_range(t):
			target = t


func _step_amove(dt: float) -> void:
	if target != null and _valid_target(target):
		_engage(dt, true)
		return
	target = null
	acq_t -= dt
	if acq_t <= 0.0:
		acq_t = ACQUIRE_EVERY
		target = world.find_target(self, sight)
		if target:
			return
	if _follow(dt):
		_arrive()


func _step_attack(dt: float) -> void:
	if target == null or not _valid_target(target):
		target = null
		_arrive()
		return
	_engage(dt, false)


## Move into range of target, then shoot it.
func _engage(dt: float, auto: bool) -> void:
	if weapon.is_empty() or (target.is_air and not bool(weapon["air"])) or (not target.is_air and not bool(weapon["ground"])):
		target = null
		return
	if _in_range(target):
		moving = false
		path = PackedVector2Array()
		_fire_at(target, dt)
		return
	# chase
	repath_t -= dt
	var tp: Vector2 = target.p
	if target is Building:
		tp = target.edge_point(p)
	if path.size() == 0 or repath_t <= 0.0 or goal.distance_to(tp) > 2.0:
		repath_t = 0.6
		goal = tp
		path_i = 1
		if is_air or p.distance_to(tp) < 6.0 and world.grid.line_clear(p, tp, radius):
			path = PackedVector2Array([p, tp])
		else:
			path = world.grid.find_path(p, tp, radius)
	moving = true
	_follow(dt)


func _wrange() -> float:
	return float(weapon.get("range", 0.0))


func _in_range(t: Entity) -> bool:
	var d: float
	if t is Building:
		d = t.dist_to(p) - radius
	else:
		d = p.distance_to(t.p) - radius - t.radius
	return d <= _wrange() + 0.15


func _valid_target(t) -> bool:
	if t == null or not is_instance_valid(t) or t.dead:
		return false
	if t is Unit and t.hidden_inside:
		return false
	return true


func _fire_at(t: Entity, dt: float) -> void:
	var to: Vector2 = t.p - p
	if to.length() > 0.01:
		_face(atan2(to.x, to.y), dt * 3.0)
	if cd <= 0.0:
		cd = float(weapon["cd"])
		attack_anim = 0.35
		world.fire(self, t)


func _face(yaw: float, k: float) -> void:
	facing = lerp_angle(facing, yaw, clampf(k * 4.0, 0.0, 1.0))


## Walk the path. Returns true on arrival.
func _follow(dt: float) -> bool:
	if path.size() == 0 or path_i >= path.size():
		moving = false
		return p.distance_to(goal) <= arrive_tol + 0.6
	var wp: Vector2 = path[path_i]
	var to := wp - p
	var d := to.length()
	var last := path_i == path.size() - 1
	var tol := arrive_tol if last else 0.35
	if d <= tol:
		path_i += 1
		if path_i >= path.size():
			moving = false
			return true
		return false
	var step_len := minf(d, speed * dt)
	var dir := _avoid(to / d)
	vel = dir * speed
	_face(atan2(dir.x, dir.y), dt * 3.0)
	_slide(dir * step_len)
	moving = true
	walk_phase += dt * speed * 2.4
	# stuck detection
	stuck_t += dt
	if stuck_t > 0.8:
		if p.distance_to(last_prog_p) < 0.25:
			stuck_count += 1
			if p.distance_to(goal) < 2.5 + radius * 2.0 or stuck_count >= 4:
				path_i = path.size()
				moving = false
				return true
			if not is_air:
				path = world.grid.find_path(p, goal, radius)
				path_i = 1
		stuck_t = 0.0
		last_prog_p = p
	return false


## Sidestep round a unit standing in the way (one that isn't walking our way),
## so the back rows of an army flow round the front instead of piling up.
func _avoid(dir: Vector2) -> Vector2:
	if is_air or (is_worker and order == O.GATHER):
		return dir
	var block = null
	var best := INF
	for v in world.units_near(p, radius + 1.8):
		if v == self or v.dead or v.is_air or v.hidden_inside:
			continue
		if v.is_worker and v.order == O.GATHER:
			continue
		var to: Vector2 = v.p - p
		var dist := to.length()
		if dist < 0.001 or dist > radius + v.radius + 0.45:
			continue
		if to.dot(dir) < 0.3 * dist:
			continue
		if v.moving and v.vel.dot(dir) > speed * 0.6:
			continue
		if dist < best:
			best = dist
			block = v
	if block == null:
		return dir
	var tb: Vector2 = block.p - p
	var c := dir.cross(tb)
	if absf(c) < 0.0001:
		c = 1.0 if eid % 2 == 0 else -1.0
	var left := Vector2(-dir.y, dir.x)
	var steer := left * (-signf(c))
	return (dir * 0.4 + steer).normalized()


## Move by delta, sliding along solid cells.
func _slide(delta: Vector2) -> void:
	if is_air:
		p += delta
		p = p.clamp(Vector2(1, 1), Vector2(world.grid.size - 1, world.grid.size - 1))
		return
	var np := p + delta
	if world.grid.walkable_p(np):
		p = np
		return
	var nx := Vector2(p.x + delta.x, p.y)
	if world.grid.walkable_p(nx):
		p = nx
		return
	var nz := Vector2(p.x, p.y + delta.y)
	if world.grid.walkable_p(nz):
		p = nz


# ---------------------------------------------------------------- workers

func _node_spot(node) -> Vector2:
	var base = world.nearest_dropoff(owner_id, node.p)
	var from: Vector2 = base.p if base else p
	var e: Vector2 = node.edge_point(from)
	var out := (from - e)
	if out.length() < 0.01:
		out = Vector2(0, 1)
	return e + out.normalized() * (radius + 0.15)


func _go_to_base() -> void:
	var base = world.nearest_dropoff(owner_id, p)
	if base == null:
		order = O.IDLE
		gstate = ""
		return
	gstate = "to_base"
	var e: Vector2 = base.edge_point(p)
	var out := (p - e)
	if out.length() < 0.01:
		out = Vector2(0, 1)
	set_goal(e + out.normalized() * (radius + 0.15))


func _step_gather(dt: float) -> void:
	if gnode == null or not is_instance_valid(gnode) or gnode.dead:
		_find_new_node()
		return
	match gstate:
		"to_node":
			if _follow(dt) or gnode.dist_to(p) <= radius + 0.35:
				_try_mine()
		"wait":
			gtimer -= dt
			if gtimer <= 0.0:
				_try_mine()
		"mining":
			gtimer -= dt
			_face(atan2(gnode.p.x - p.x, gnode.p.y - p.y), dt * 3.0)
			attack_anim = 0.2
			if gtimer <= 0.0:
				var n: ResourceNode = gnode
				carry = n.take(Defs.MINERAL_PER_TRIP)
				carry_kind = "mineral"
				if n.miner == self:
					n.miner = null
				_go_to_base()
		"inside":
			gtimer -= dt
			if gtimer <= 0.0:
				var b: Building = gnode
				var sn: ResourceNode = b.slime_node
				carry = sn.take(Defs.SLIME_PER_TRIP) if sn else 0
				carry_kind = "slime"
				_exit_extractor()
				if b.occupant == self:
					b.occupant = null
				_go_to_base()
		"to_base":
			var base = world.nearest_dropoff(owner_id, p)
			if base == null:
				order = O.IDLE
				return
			if _follow(dt) or base.dist_to(p) <= radius + 0.45:
				if base.dist_to(p) <= radius + 0.9:
					world.deposit(owner_id, carry_kind, carry)
					carry = 0
					carry_kind = ""
					if gnode and is_instance_valid(gnode) and not gnode.dead:
						gstate = "to_node"
						set_goal(_node_spot(gnode))
					else:
						_find_new_node()
				else:
					_go_to_base()
		_:
			gstate = "to_node"
			set_goal(_node_spot(gnode))


func _try_mine() -> void:
	if gnode is ResourceNode:
		var n: ResourceNode = gnode
		if n.amount <= 0:
			_find_new_node()
			return
		if n.miner == null or n.miner == self or not is_instance_valid(n.miner) or n.miner.dead or n.miner.gnode != n:
			n.miner = self
			gstate = "mining"
			gtimer = Defs.MINE_TIME
			moving = false
			return
		# busy: try a free crystal nearby, else wait
		var alt = world.free_mineral_near(n, owner_id, 5.0)
		if alt and alt != n:
			gnode = alt
			gstate = "to_node"
			set_goal(_node_spot(alt))
			return
		gstate = "wait"
		gtimer = 0.25
		moving = false
	elif gnode is Building:
		var b: Building = gnode
		if not b.built or b.slime_node == null or b.slime_node.amount <= 0:
			_find_new_node()
			return
		if b.occupant == null or b.occupant == self or not is_instance_valid(b.occupant) or b.occupant.dead:
			b.occupant = self
			gstate = "inside"
			gtimer = Defs.SLIME_TIME
			hidden_inside = true
			visible = false
			moving = false
			return
		gstate = "wait"
		gtimer = 0.2
		moving = false


func _exit_extractor() -> void:
	hidden_inside = false
	if world and world.visuals:
		visible = shown


func _find_new_node() -> void:
	var kind := "mineral"
	if gnode is Building or carry_kind == "slime":
		kind = "slime"
	var n = world.nearest_resource(owner_id, p, kind)
	if n == null and kind == "slime":
		n = world.nearest_resource(owner_id, p, "mineral")
	if n == null:
		gnode = null
		order = O.IDLE
		gstate = ""
		anchor = p
		return
	gnode = n
	gstate = "to_node"
	set_goal(_node_spot(n))


func _step_build(dt: float) -> void:
	var bd: Dictionary = Defs.buildings[build_id]
	var sz: int = int(bd["size"])
	var center := Vector2(build_cell.x + sz * 0.5, build_cell.y + sz * 0.5)
	var near := p.distance_to(center) <= sz * 0.5 + radius + 1.2
	if not near:
		if _follow(dt):
			near = p.distance_to(center) <= sz * 0.5 + radius + 2.5
		if not near:
			return
	var placed: bool = world.place_building(self, build_id, build_cell)
	build_id = ""
	if not placed:
		order = O.IDLE
		anchor = p
		return
	if resume_node and is_instance_valid(resume_node) and not resume_node.dead:
		cmd_gather(resume_node)
	else:
		var n = world.nearest_resource(owner_id, p, "mineral")
		if n and n.p.distance_to(p) < 20.0:
			cmd_gather(n)
		else:
			order = O.IDLE
			anchor = p
	resume_node = null


func status_text() -> String:
	if is_worker:
		match order:
			O.GATHER:
				if gnode is Building:
					return "Harvesting Void Slime"
				return "Harvesting crystals"
			O.BUILD:
				return "On the way to build"
	match order:
		O.IDLE:
			return "Idle"
		O.HOLD:
			return "Holding position"
		O.MOVE:
			return "Moving"
		O.AMOVE:
			return "Attack-moving"
		O.ATTACK:
			return "Attacking"
	return ""

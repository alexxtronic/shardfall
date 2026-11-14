class_name World
extends Node3D
## The match simulation: players, the grid, every entity, combat and economy.
## Rendering is optional (visuals = false for the headless balance battles).

signal message(text: String, kind: String)
signal game_over(winner: int)
signal alert(at: Vector2)
signal unit_ready(u: Unit)

const HASH := 4.0

var visuals: bool = true
var running: bool = true
var time: float = 0.0
var players: Array = []          # PlayerState
var human: int = 0               # -1 when nobody plays (balance runs)
var grid: PathGrid
var units: Array = []
var buildings: Array = []
var resources: Array = []
var sites: Array = []            # base sites (see MapGen)
var next_eid: int = 1
var buckets: Dictionary = {}
var fx: Fx
var fog = null                   # Fog
var ais: Array = []
var over: bool = false
var winner: int = -1
var victory_t: float = 0.0
var alert_t: float = -100.0
var entity_root: Node3D
var cam = null                   # CameraRig (for alerts)
var speed_mult: float = 1.0
var cfg: Dictionary = {}
var check_victory: bool = true
var power_rev: int = 0           # bumps whenever a Power Relay finishes or dies


func setup(c: Dictionary) -> void:
	cfg = c
	visuals = bool(c.get("visuals", true))
	human = int(c.get("human", 0))
	var size: int = int(c.get("map_size", Defs.MAP_SIZE))
	grid = PathGrid.new(size)
	entity_root = Node3D.new()
	entity_root.name = "Entities"
	add_child(entity_root)
	fx = Fx.new()
	fx.world = self
	fx.name = "Fx"
	add_child(fx)
	var races: Array = c.get("races", ["ambron", "void"])
	var ai_flags: Array = c.get("ai", [false, true])
	var cols := [Color(0.22, 0.62, 1.0), Color(1.0, 0.27, 0.22)]
	for i in races.size():
		var pl := PlayerState.new()
		pl.id = i
		pl.race = races[i]
		pl.is_ai = ai_flags[i]
		pl.color = cols[i % 2]
		pl.name = ("You" if i == human else "Bot") if human >= 0 else "P%d" % (i + 1)
		pl.minerals = int(c.get("start_minerals", Defs.START_MINERALS))
		players.append(pl)
	if String(c.get("map", "standard")) == "standard":
		MapGen.build_standard(self)
		for i in players.size():
			start_player(i, i)
	if visuals and human >= 0:
		fog = Fog.new()
		fog.world = self
		fog.name = "Fog"
		add_child(fog)
		fog.setup()
	for i in players.size():
		if players[i].is_ai and bool(c.get("ai_enabled", true)):
			var ai := BotAI.new()
			ai.world = self
			ai.pid = i
			ai.difficulty = String(c.get("difficulty", "normal"))
			ai.name = "AI%d" % i
			add_child(ai)
			ais.append(ai)


## Give a player their main base and workers at a base site.
func start_player(pid: int, site_index: int) -> void:
	var s: Dictionary = sites[site_index]
	var pl: PlayerState = players[pid]
	pl.start_site = site_index
	var mid: String = Defs.building_id(pl.race, "main")
	var b := spawn_building(mid, pid, s["cell"], true)
	s["taken_by"] = pid
	var wid: String = Defs.unit_id(pl.race, "worker")
	var minerals: Array = s["minerals"]
	for i in Defs.START_WORKERS:
		var ang := TAU * float(i) / float(Defs.START_WORKERS)
		var at: Vector2 = b.p + Vector2(cos(ang), sin(ang)) * 3.4
		at = grid.nearest_walkable(at)
		var u := spawn_unit(wid, pid, at)
		if minerals.size() > 0:
			u.cmd_gather(minerals[i % minerals.size()])


# ---------------------------------------------------------------- spawning

func spawn_unit(uid: String, pid: int, at: Vector2) -> Unit:
	var u := Unit.new()
	u.eid = next_eid
	next_eid += 1
	u.setup(self, uid, pid, at)
	u.name = "%s_%d" % [uid, u.eid]
	units.append(u)
	entity_root.add_child(u)
	if visuals:
		Models.attach_unit(self, u)
	return u


func spawn_building(bid: String, pid: int, c: Vector2i, finished: bool) -> Building:
	var b := Building.new()
	b.eid = next_eid
	next_eid += 1
	b.setup(self, bid, pid, c)
	b.name = "%s_%d" % [bid, b.eid]
	buildings.append(b)
	entity_root.add_child(b)
	grid.set_rect(c, Vector2i(b.size, b.size), 2, b)
	if b.slot == "extractor":
		for r in resources:
			if r.kind == "slime" and r.cell == c and not r.dead:
				b.slime_node = r
				r.extractor = b
	if pid == human:
		b.seen = true
	if visuals:
		Models.attach_building(self, b)
	if finished:
		b.finish_instantly()
		if b.slot == "supply":
			power_rev += 1
	else:
		b.start_construction()
	return b


func spawn_resource(kind: String, c: Vector2i, sz: Vector2i, amount: int, variant: int, site_index: int) -> ResourceNode:
	var r := ResourceNode.new()
	r.eid = next_eid
	next_eid += 1
	r.setup(self, kind, c, sz, amount)
	r.site_index = site_index
	r.name = "%s_%d" % [kind, r.eid]
	resources.append(r)
	entity_root.add_child(r)
	grid.set_rect(c, sz, 3, r)
	if visuals:
		Models.attach_resource(self, r, variant)
	return r


# ---------------------------------------------------------------- the loop

func _process(delta: float) -> void:
	if not running or over:
		return
	var dt := minf(delta, 0.05) * speed_mult
	# fast speeds take several small steps so nothing tunnels
	var n := int(ceil(dt / 0.05))
	for i in n:
		step(dt / float(n))
	if visuals:
		_sync_visuals(delta)


func step(dt: float) -> void:
	time += dt
	_rebuild_hash()
	for u in units:
		u.step(dt)
	_separate()
	for b in buildings:
		b.step(dt)
	fx.step(dt)
	_cleanup()
	for ai in ais:
		ai.step(dt)
	if fog:
		fog.step(dt)
	victory_t += dt
	if victory_t >= 1.0 and check_victory:
		victory_t = 0.0
		_check_victory()


func _sync_visuals(delta: float) -> void:
	for u in units:
		Models.animate_unit(u, delta)
	for b in buildings:
		Models.animate_building(b, delta)


func _rebuild_hash() -> void:
	buckets.clear()
	for u in units:
		if u.dead or u.hidden_inside:
			continue
		var k := Vector2i(int(u.p.x / HASH), int(u.p.y / HASH))
		if buckets.has(k):
			buckets[k].append(u)
		else:
			buckets[k] = [u]


func units_near(at: Vector2, r: float) -> Array:
	var out: Array = []
	var x0 := int((at.x - r) / HASH)
	var x1 := int((at.x + r) / HASH)
	var y0 := int((at.y - r) / HASH)
	var y1 := int((at.y + r) / HASH)
	for y in range(y0, y1 + 1):
		for x in range(x0, x1 + 1):
			var k := Vector2i(x, y)
			if buckets.has(k):
				out.append_array(buckets[k])
	return out


func _separate() -> void:
	for u in units:
		if u.dead or u.hidden_inside:
			continue
		if u.is_worker and u.order == Unit.O.GATHER:
			continue
		var near := units_near(u.p, u.radius + 2.0)
		for v in near:
			if v == u or v.dead or v.is_air != u.is_air:
				continue
			if v.is_worker and v.order == Unit.O.GATHER:
				continue
			var d: Vector2 = u.p - v.p
			var dist := d.length()
			var mn: float = u.radius + v.radius
			if dist >= mn:
				continue
			if dist < 0.001:
				d = Vector2(randf() - 0.5, randf() - 0.5)
				dist = d.length()
			var share := 0.5
			if not u.moving and v.moving:
				share = 0.8
			elif u.moving and not v.moving:
				share = 0.2
			if u.order == Unit.O.HOLD:
				share = 0.05
			var push: Vector2 = d / dist * (mn - dist) * share * 0.6
			var np: Vector2 = u.p + push
			if u.is_air or u.ground_ok(np):
				u.p = np


func _cleanup() -> void:
	var i := units.size() - 1
	while i >= 0:
		if units[i].dead:
			var u: Unit = units[i]
			units.remove_at(i)
			u.queue_free()
		i -= 1
	i = buildings.size() - 1
	while i >= 0:
		if buildings[i].dead:
			var b: Building = buildings[i]
			buildings.remove_at(i)
			b.queue_free()
		i -= 1
	i = resources.size() - 1
	while i >= 0:
		if resources[i].dead:
			var r: ResourceNode = resources[i]
			resources.remove_at(i)
			r.queue_free()
		i -= 1


# ---------------------------------------------------------------- combat

func find_target(u: Unit, r: float):
	var w: Dictionary = u.weapon
	if w.is_empty():
		return null
	var can_air: bool = w["air"]
	var can_ground: bool = w["ground"]
	var best = null
	var best_s := INF
	for v in units_near(u.p, r + 2.0):
		if v.dead or v.owner_id == u.owner_id or v.owner_id < 0:
			continue
		if v.is_air and not can_air:
			continue
		if not v.is_air and not can_ground:
			continue
		var d: float = u.p.distance_to(v.p) - v.radius
		if d > r:
			continue
		var s := d
		if v.is_worker or v.weapon.is_empty():
			s += 5.0
		if s < best_s:
			best_s = s
			best = v
	# towers shoot back, so they count as armed targets
	if can_ground:
		for b in buildings:
			if b.dead or b.weapon.is_empty() or b.owner_id == u.owner_id or b.owner_id < 0:
				continue
			var d: float = b.dist_to(u.p)
			if d <= r and d < best_s:
				best_s = d
				best = b
	if best != null or not can_ground:
		return best
	for b in buildings:
		if b.dead or b.owner_id == u.owner_id or b.owner_id < 0:
			continue
		var d: float = b.dist_to(u.p)
		if d <= r and d < best_s:
			best_s = d
			best = b
	return best


## The nearest enemy unit a tower can hit, armed ones first.
func tower_target(b: Building, r: float):
	var w: Dictionary = b.weapon
	var best = null
	var best_s := INF
	for v in units_near(b.p, r + b.size):
		if v.dead or v.owner_id == b.owner_id or v.owner_id < 0 or v.hidden_inside:
			continue
		if (v.is_air and not bool(w["air"])) or (not v.is_air and not bool(w["ground"])):
			continue
		var d: float = b.dist_to(v.p) - v.radius
		if d > r:
			continue
		var s := d + (5.0 if (v.is_worker or v.weapon.is_empty()) else 0.0)
		if s < best_s:
			best_s = s
			best = v
	return best


func tower_fire(b: Building, t: Entity) -> void:
	if visuals:
		fx.tower_shot(b, t)
	hit(b.owner_id, b, t, t.p, b.weapon, String(b.def.get("fx", "")))


func damage_vs(w: Dictionary, t: Entity) -> float:
	var dmg: float = float(w["dmg"])
	var bonus: Dictionary = w.get("bonus", {})
	for tag in bonus:
		if t.tags.has(tag):
			dmg += float(bonus[tag])
	return maxf(0.5, dmg - t.armor)


func fire(u: Unit, t: Entity) -> void:
	var w: Dictionary = u.weapon
	var sp: float = float(w.get("proj", 0.0))
	if sp <= 0.0:
		fx.instant(u, t)
		hit(u.owner_id, u, t, t.p, w, String(u.def.get("fx", "")))
	else:
		fx.projectile(u, t, sp)


## Resolve a hit at `at`. Splash hurts other enemies in the same layer.
func hit(owner: int, src: Entity, t: Entity, at: Vector2, w: Dictionary, kind: String) -> void:
	var splash: float = float(w.get("splash", 0.0))
	# a small random spread on every hit, so hits-to-kill breakpoints average out
	var roll := randf_range(0.8, 1.2)
	if t and is_instance_valid(t) and not t.dead:
		t.apply_damage(damage_vs(w, t) * roll, src if src and is_instance_valid(src) else null)
		_credit(owner, t)
	if splash > 0.0:
		var air: bool = t.is_air if (t and is_instance_valid(t)) else false
		for v in units_near(at, splash + 1.5):
			if v == t or v.dead or v.owner_id == owner or v.owner_id < 0 or v.is_air != air:
				continue
			if v.p.distance_to(at) - v.radius <= splash:
				v.apply_damage(damage_vs(w, v) * 0.6 * roll, src if src and is_instance_valid(src) else null)
				_credit(owner, v)
	if visuals:
		fx.impact(at, t, kind, splash)


func _credit(owner: int, t: Entity) -> void:
	if t.dead and owner >= 0 and not t.get_meta("credited", false):
		t.set_meta("credited", true)
		players[owner].kills += 1
		players[owner].value_killed += Defs.value_of(t.def_id)


func on_damaged(e: Entity, src: Entity) -> void:
	if src and e is Unit and not e.dead:
		var u: Unit = e
		if (u.order == Unit.O.IDLE) and u.target == null and not u.weapon.is_empty() and not u.is_worker:
			var w: Dictionary = u.weapon
			if (src.is_air and bool(w["air"])) or (not src.is_air and bool(w["ground"])):
				u.target = src
	if e.owner_id == human and human >= 0 and time - alert_t > 15.0:
		var on_screen := false
		if cam and cam.has_method("sees"):
			on_screen = cam.sees(e.p)
		if not on_screen:
			alert_t = time
			var what := "base" if e is Building else "forces"
			message.emit("Your %s are under attack!" % what if what == "forces" else "Your base is under attack!", "alert")
			alert.emit(e.p)


func kill(e: Entity, src: Entity) -> void:
	if e.dead:
		return
	e.dead = true
	if e.selected:
		e.set_selected(false)
	if e is Unit:
		var u: Unit = e
		if u.build_id != "":
			refund_build(u)
		u.clear_job()
		var pl: PlayerState = players[u.owner_id]
		pl.units_lost += 1
		pl.value_lost += Defs.value_of(u.def_id)
	elif e is Building:
		var b: Building = e
		players[b.owner_id].value_lost += Defs.value_of(b.def_id)
		if b.slot == "supply":
			power_rev += 1
		if b.slot == "extractor" and b.slime_node and is_instance_valid(b.slime_node):
			var r: ResourceNode = b.slime_node
			r.extractor = null
			grid.set_rect(r.cell, r.cells, 3, r)
			if b.occupant and is_instance_valid(b.occupant):
				b.occupant._exit_extractor()
				b.occupant.gstate = ""
		else:
			grid.set_rect(b.cell, Vector2i(b.size, b.size), 0, null)
		for s in sites:
			if s["taken_by"] == b.owner_id and b.slot == "main" and Vector2i(s["cell"]) == b.cell:
				s["taken_by"] = -1
	if visuals:
		fx.death(e)


func deplete(r: ResourceNode) -> void:
	r.dead = true
	grid.set_rect(r.cell, r.cells, 0, null)
	if visuals:
		fx.puff(r.p, Color(1.0, 0.8, 0.3))


# ---------------------------------------------------------------- economy

func deposit(pid: int, kind: String, n: int) -> void:
	var pl: PlayerState = players[pid]
	if kind == "mineral":
		pl.minerals += n
		pl.gathered_m += n
	elif kind == "slime":
		pl.slime += n
		pl.gathered_s += n


func nearest_dropoff(pid: int, from: Vector2):
	var best = null
	var bd := INF
	for b in buildings:
		if b.dead or b.owner_id != pid or not b.built or b.slot != "main":
			continue
		var d: float = b.dist_to(from)
		if d < bd:
			bd = d
			best = b
	return best


## Nearest mineral crystal (or own working extractor for "slime").
func nearest_resource(pid: int, from: Vector2, kind: String):
	var best = null
	var bd := INF
	if kind == "slime":
		for b in buildings:
			if b.dead or b.owner_id != pid or b.slot != "extractor" or not b.built:
				continue
			if b.slime_node == null or b.slime_node.amount <= 0:
				continue
			var d: float = b.p.distance_to(from)
			if d < bd:
				bd = d
				best = b
		return best
	for r in resources:
		if r.dead or r.kind != "mineral" or r.amount <= 0:
			continue
		var d: float = r.p.distance_to(from)
		if r.miner != null:
			d += 2.0
		if d < bd:
			bd = d
			best = r
	return best


func free_mineral_near(n: ResourceNode, pid: int, r: float):
	var best = null
	var bd := INF
	for m in resources:
		if m == n or m.dead or m.kind != "mineral" or m.amount <= 0 or m.miner != null:
			continue
		var d: float = m.p.distance_to(n.p)
		if d <= r and d < bd:
			bd = d
			best = m
	return best


func supply_used(pid: int) -> int:
	var s := 0
	for u in units:
		if u.owner_id == pid and not u.dead:
			s += u.supply
	for b in buildings:
		if b.owner_id == pid and not b.dead:
			for q in b.queue:
				s += int(Defs.units[q]["supply"])
	return s


func supply_cap(pid: int) -> int:
	var s := 0
	for b in buildings:
		if b.owner_id == pid and not b.dead and b.built:
			s += int(b.def.get("supply", 0))
	return mini(s, Defs.SUPPLY_MAX)


func has_built(pid: int, bid: String) -> bool:
	for b in buildings:
		if b.owner_id == pid and not b.dead and b.built and b.def_id == bid:
			return true
	return false


func count_buildings(pid: int, bid: String, include_unfinished: bool = true) -> int:
	var n := 0
	for b in buildings:
		if b.owner_id == pid and not b.dead and b.def_id == bid and (include_unfinished or b.built):
			n += 1
	return n


func missing_requirement(pid: int, bid: String) -> String:
	var bd: Dictionary = Defs.buildings[bid]
	for req in bd["requires"]:
		if not has_built(pid, req):
			return String(Defs.buildings[req]["name"])
	return ""


## Queue a unit. Returns "" or a reason it couldn't.
func queue_unit(b: Building, uid: String) -> String:
	if b.dead or not b.built:
		return "Still under construction"
	if not b.produces().has(uid):
		return "Can't train that here"
	if b.queue.size() >= Building.QUEUE_MAX:
		return "Queue is full"
	var ud: Dictionary = Defs.units[uid]
	var pl: PlayerState = players[b.owner_id]
	if pl.minerals < int(ud["cost"][0]):
		return "Not enough crystals"
	if pl.slime < int(ud["cost"][1]):
		return "Not enough Void Slime"
	if supply_used(b.owner_id) + int(ud["supply"]) > supply_cap(b.owner_id):
		return "supply"
	pl.pay(ud["cost"])
	b.queue.append(uid)
	return ""


func cancel_queue(b: Building, index: int) -> void:
	if index < 0 or index >= b.queue.size():
		return
	var uid: String = b.queue[index]
	players[b.owner_id].refund(Defs.units[uid]["cost"])
	b.queue.remove_at(index)
	if index == 0:
		b.prod_t = 0.0


func cancel_construction(b: Building) -> void:
	if b.built or b.dead:
		return
	players[b.owner_id].refund(b.def["cost"], 0.75)
	b.hp = 0
	kill(b, null)


func spawn_from(b: Building, uid: String) -> void:
	var u := spawn_unit(uid, b.owner_id, b.exit_point())
	players[b.owner_id].units_made += 1
	if u.is_worker:
		if b.rally_node and is_instance_valid(b.rally_node) and not b.rally_node.dead:
			u.cmd_gather(b.rally_node)
		elif b.rally_set:
			u.cmd_move(b.rally)
		else:
			var n = nearest_resource(b.owner_id, b.p, "mineral")
			if n and n.p.distance_to(b.p) < 14.0:
				u.cmd_gather(n)
	elif b.rally_set:
		u.cmd_move(b.rally, false)
	else:
		u.cmd_move(u.p + Vector2(0, 2.0))
	if b.owner_id == human:
		unit_ready.emit(u)


func on_building_done(b: Building) -> void:
	if b.slot == "supply":
		power_rev += 1
	if b.owner_id == human:
		message.emit("%s complete" % b.def["name"], "done")
	if b.slot == "extractor":
		# send three nearby crystal workers onto the new extractor
		var n := 0
		var cands: Array = []
		for u in units:
			if u.owner_id == b.owner_id and u.is_worker and u.order == Unit.O.GATHER and u.gnode is ResourceNode and u.carry == 0:
				cands.append(u)
		cands.sort_custom(func(a, c): return a.p.distance_to(b.p) < c.p.distance_to(b.p))
		for u in cands:
			if n >= 3 or u.p.distance_to(b.p) > 18.0:
				break
			u.cmd_gather(b)
			n += 1


# ---------------------------------------------------------------- building placement

func can_place(pid: int, bid: String, c: Vector2i) -> bool:
	return place_error(pid, bid, c) == ""


## Why a building can't go at c, or "" when it can.
func place_error(pid: int, bid: String, c: Vector2i) -> String:
	var bd: Dictionary = Defs.buildings[bid]
	var sz: int = int(bd["size"])
	if String(bd["slot"]) == "extractor":
		var r = grid.who_at(c)
		if r is ResourceNode and r.kind == "slime" and r.cell == c and r.extractor == null and not r.dead:
			return ""
		return "Build it on a slime pile"
	if not grid.rect_free(c, Vector2i(sz, sz)):
		return "Can't build there"
	if String(bd["slot"]) == "main":
		# base sites are laid out by hand, so they are always fine
		for st in sites:
			if Vector2i(st["cell"]) == c:
				return "" if st["taken_by"] < 0 else "Can't build there"
		var rect := Rect2(Vector2(c), Vector2(sz, sz)).grow(3.0)
		for r in resources:
			if not r.dead and rect.intersects(Rect2(Vector2(r.cell), Vector2(r.cells))):
				return "Too close to resources"
	if Defs.needs_power(bid) and not powered_at(pid, Vector2(c.x + sz * 0.5, c.y + sz * 0.5)):
		return "Must be inside a Power Relay's field"
	return ""


## Ambron power: inside the field of a finished Power Relay.
func powered_at(pid: int, at: Vector2) -> bool:
	for b in buildings:
		if b.owner_id == pid and not b.dead and b.built and b.slot == "supply" and b.p.distance_to(at) <= Defs.POWER_RADIUS:
			return true
	return false


## Whether a building has the power it needs (cached until a relay changes).
func is_powered(b: Building) -> bool:
	if not b.needs_power:
		return true
	if b.power_rev != power_rev:
		b.power_rev = power_rev
		b.powered = powered_at(b.owner_id, b.p)
	return b.powered


## Finished Power Relays of a player (their fields are drawn while placing).
func relays(pid: int) -> Array:
	var out: Array = []
	for b in buildings:
		if b.owner_id == pid and not b.dead and b.built and b.slot == "supply" and players[pid].race == "ambron":
			out.append(b)
	return out


## The nearest good spot for a building near q: the footprint is free, a
## one-cell lane round it stays open, and it keeps off the crystal lines.
func suggest_spot(pid: int, bid: String, q: Vector2) -> Variant:
	var bd: Dictionary = Defs.buildings[bid]
	var sz: int = int(bd["size"])
	var c0 := Vector2i(int(floor(q.x - sz * 0.5 + 0.5)), int(floor(q.y - sz * 0.5 + 0.5)))
	var best = null
	var best_d := INF
	for dy in range(-14, 15):
		for dx in range(-14, 15):
			var d := float(dx * dx + dy * dy)
			if d >= best_d or d > 196.0:
				continue
			var c := c0 + Vector2i(dx, dy)
			if not can_place(pid, bid, c):
				continue
			if not grid.rect_free(c - Vector2i(1, 1), Vector2i(sz + 2, sz + 2)):
				continue
			if _near_resources(c, sz, 2.0):
				continue
			best_d = d
			best = c
	return best


func _near_resources(c: Vector2i, sz: int, gap: float) -> bool:
	var rect := Rect2(Vector2(c), Vector2(sz, sz)).grow(gap)
	for r in resources:
		if not r.dead and rect.intersects(Rect2(Vector2(r.cell), Vector2(r.cells))):
			return true
	return false


## The best main-base spot near q, if q is close to an open base site.
func snap_main(q: Vector2) -> Variant:
	for s in sites:
		if s["taken_by"] >= 0:
			continue
		var center: Vector2 = s["center"]
		if center.distance_to(q) < 7.0:
			return s["cell"]
	return null


## Snap q to a slime pile's cell when it's on one.
func snap_extractor(q: Vector2) -> Variant:
	for r in resources:
		if r.kind == "slime" and not r.dead and r.extractor == null:
			if Rect2(Vector2(r.cell), Vector2(r.cells)).grow(0.6).has_point(q):
				return r.cell
	return null


## Order a worker to build. Pays now; refunded if the order is dropped.
func command_build(w: Unit, bid: String, c: Vector2i) -> String:
	if w == null or w.dead or not w.is_worker:
		return "Select a worker first"
	var miss := missing_requirement(w.owner_id, bid)
	if miss != "":
		return "Requires %s" % miss
	var perr := place_error(w.owner_id, bid, c)
	if perr != "":
		return perr
	var bd: Dictionary = Defs.buildings[bid]
	var pl: PlayerState = players[w.owner_id]
	if pl.minerals < int(bd["cost"][0]):
		return "Not enough crystals"
	if pl.slime < int(bd["cost"][1]):
		return "Not enough Void Slime"
	if w.build_id != "":
		refund_build(w)
	pl.pay(bd["cost"])
	w.cmd_build(bid, c)
	return ""


func refund_build(w: Unit) -> void:
	if w.build_id == "":
		return
	players[w.owner_id].refund(Defs.buildings[w.build_id]["cost"])
	w.build_id = ""


func place_building(w: Unit, bid: String, c: Vector2i) -> bool:
	if not can_place(w.owner_id, bid, c):
		players[w.owner_id].refund(Defs.buildings[bid]["cost"])
		if w.owner_id == human:
			message.emit("Can't build there", "error")
		return false
	var b := spawn_building(bid, w.owner_id, c, false)
	# nudge units out of the footprint
	var rect := Rect2(Vector2(c), Vector2(b.size, b.size)).grow(0.3)
	for u in units:
		if not u.is_air and rect.has_point(u.p):
			u.p = grid.nearest_walkable(u.p)
	if b.slot == "main":
		for s in sites:
			if Vector2i(s["cell"]) == c:
				s["taken_by"] = w.owner_id
	return true


# ---------------------------------------------------------------- group commands

func command_move(list: Array, to: Vector2, attack_move: bool) -> void:
	var ground: Array = []
	var air: Array = []
	for u in list:
		if u.dead:
			continue
		if u.is_air:
			air.append(u)
		else:
			ground.append(u)
	if ground.size() > 0:
		var slots := formation(ground, to)
		var c := Vector2.ZERO
		for u in ground:
			c += u.p
		c /= ground.size()
		var shared := grid.find_path(c, to, 0.5)
		for i in ground.size():
			var u: Unit = ground[i]
			var dst: Vector2 = slots[i]
			if u.p.distance_to(c) < 8.0 and shared.size() > 2:
				u.cmd_move(dst, attack_move, shared)
			else:
				u.cmd_move(dst, attack_move)
			u.arrive_tol = 0.4
	if air.size() > 0:
		var slots := formation(air, to)
		for i in air.size():
			air[i].cmd_move(slots[i], attack_move)


## Spread destinations in a block facing the travel direction.
func formation(list: Array, to: Vector2) -> Array:
	var n := list.size()
	var out: Array = []
	if n == 1:
		out.append(to if list[0].is_air else grid.nearest_walkable(to))
		return out
	var c := Vector2.ZERO
	var maxr := 0.4
	for u in list:
		c += u.p
		maxr = maxf(maxr, u.radius)
	c /= n
	var fwd := (to - c)
	fwd = fwd.normalized() if fwd.length() > 0.01 else Vector2(0, 1)
	var side := Vector2(-fwd.y, fwd.x)
	var cols := int(ceil(sqrt(float(n) * 1.6)))
	var rows := int(ceil(float(n) / cols))
	var sp := maxr * 2.3
	var spots: Array = []
	for i in n:
		var col := i % cols
		var row := i / cols
		var off := side * (float(col) - (cols - 1) * 0.5) * sp - fwd * (float(row) - (rows - 1) * 0.5) * sp
		var q := to + off
		if not list[0].is_air:
			q = grid.nearest_walkable(q)
		spots.append(q)
	# match units to spots by their order across the side axis
	var order: Array = range(n)
	order.sort_custom(func(a, b2):
		var ua: Unit = list[a]
		var ub: Unit = list[b2]
		var ra := int(floor((ua.p - c).dot(-fwd)))
		var rb := int(floor((ub.p - c).dot(-fwd)))
		if ra != rb:
			return ra < rb
		return (ua.p - c).dot(side) < (ub.p - c).dot(side))
	out.resize(n)
	for k in n:
		out[order[k]] = spots[k]
	return out


func command_attack(list: Array, t: Entity) -> void:
	for u in list:
		if u.dead or u.weapon.is_empty():
			continue
		var w: Dictionary = u.weapon
		if (t.is_air and bool(w["air"])) or (not t.is_air and bool(w["ground"])):
			u.cmd_attack(t)
		else:
			u.cmd_move(t.p, true)


func command_gather(list: Array, node) -> void:
	for u in list:
		if u.is_worker and not u.dead:
			u.cmd_gather(node)


# ---------------------------------------------------------------- end of the game

func _check_victory() -> void:
	if over:
		return
	var alive: Array = []
	for pl in players:
		if not pl.alive:
			continue
		var has := false
		for b in buildings:
			if b.owner_id == pl.id and not b.dead:
				has = true
				break
		if not has:
			pl.alive = false
			if visuals:
				message.emit("%s eliminated" % pl.name, "alert")
		else:
			alive.append(pl.id)
	if alive.size() <= 1:
		finish(alive[0] if alive.size() == 1 else -1)


func finish(w: int) -> void:
	if over:
		return
	over = true
	winner = w
	game_over.emit(w)


func surrender(pid: int) -> void:
	players[pid].alive = false
	for pl in players:
		if pl.id != pid and pl.alive:
			finish(pl.id)
			return
	finish(-1)

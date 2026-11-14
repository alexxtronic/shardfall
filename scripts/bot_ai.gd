class_name BotAI
extends Node
## The computer opponent. It plays by the same rules and costs as the human:
## no extra income, no map hacks beyond knowing where bases are. Each think it
## keeps workers busy, keeps supply ahead, follows a build order up the tech
## tree, expands, trains a mix that answers what it sees, defends, and attacks
## in waves that grow over time.

const LEVELS := {
	"easy": {"think": 1.4, "worker_cap": 26, "first_wave": 16, "wave_step": 6, "max_barracks": 1, "max_factory": 1, "max_air": 1, "expand_at": 420.0, "max_mains": 2, "queue": 1, "tech_delay": 1.6},
	"normal": {"think": 0.7, "worker_cap": 44, "first_wave": 22, "wave_step": 10, "max_barracks": 3, "max_factory": 2, "max_air": 1, "expand_at": 210.0, "max_mains": 3, "queue": 1, "tech_delay": 1.0},
	"hard": {"think": 0.35, "worker_cap": 64, "first_wave": 26, "wave_step": 14, "max_barracks": 4, "max_factory": 2, "max_air": 2, "expand_at": 150.0, "max_mains": 4, "queue": 2, "tech_delay": 0.8},
}

var world
var pid: int = 1
var difficulty: String = "normal"
var cfg: Dictionary
var race: String
var think_t: float = 1.0
var state: String = "build"      # build, attack, defend
var wave_supply: int = 22
var sent_supply: int = 0
var attack_target = null
var last_wave_t: float = -999.0
var home: Vector2
var rally: Vector2
var base_dir: Vector2
var mix_flip: int = 0
var stats := {}
var reserve: Array = [0, 0]


func _ready() -> void:
	cfg = LEVELS.get(difficulty, LEVELS["normal"])
	race = world.players[pid].race
	wave_supply = int(cfg["first_wave"])
	var s: Dictionary = world.sites[world.players[pid].start_site]
	home = s["center"]
	base_dir = -(s["dir"] as Vector2).normalized()
	# gather at the main's choke, toward the natural
	var nat = _nearest_site(home, true)
	if nat != null:
		rally = home + ((nat["center"] as Vector2) - home).normalized() * 14.0
	else:
		rally = home + base_dir * 10.0
	rally = world.grid.nearest_walkable(rally)


func step(dt: float) -> void:
	if not world.players[pid].alive or world.over:
		return
	think_t -= dt
	if think_t > 0.0:
		return
	think_t = float(cfg["think"])
	_think()


func uid(slot: String) -> String:
	return Defs.unit_id(race, slot)


func bid(slot: String) -> String:
	return Defs.building_id(race, slot)


# ---------------------------------------------------------------- the brain

func _think() -> void:
	var pl: PlayerState = world.players[pid]
	var workers: Array = []
	var army: Array = []
	for u in world.units:
		if u.owner_id != pid or u.dead:
			continue
		if u.is_worker:
			workers.append(u)
		else:
			army.append(u)
	var mains := _mine("main", true)
	var built_mains := _mine("main", false)
	var active := _active_mains(built_mains)
	stats = {"workers": workers.size(), "army": army.size()}
	reserve = [0, 0]
	_economy(workers, built_mains)
	_supply(pl)
	_train_workers(pl, workers, active)
	_tech(pl, workers, mains, active)
	_train_army(pl)
	_army(army)


## Mains that still have a fair amount of crystals around them.
func _active_mains(built_mains: Array) -> Array:
	var out: Array = []
	for b in built_mains:
		var left := 0
		for r in world.resources:
			if r.kind == "mineral" and not r.dead and r.p.distance_to(b.p) < 12.0:
				left += r.amount
		if left > 1500:
			out.append(b)
	return out


func _mine(slot: String, include_unfinished: bool) -> Array:
	var out: Array = []
	var id := bid(slot)
	for b in world.buildings:
		if b.owner_id == pid and not b.dead and b.def_id == id and (include_unfinished or b.built):
			out.append(b)
	return out


func _pending(slot: String) -> int:
	var id := bid(slot)
	var n := 0
	for u in world.units:
		if u.owner_id == pid and not u.dead and u.is_worker and u.build_id == id:
			n += 1
	return n


func _count(slot: String) -> int:
	return _mine(slot, true).size() + _pending(slot)


# ---------------------------------------------------------------- economy

func _economy(workers: Array, built_mains: Array) -> void:
	# extractors want three each
	var exts := _mine("extractor", false)
	for e in exts:
		if e.slime_node == null or e.slime_node.amount <= 0:
			continue
		var on := 0
		for u in workers:
			if u.order == Unit.O.GATHER and u.gnode == e:
				on += 1
		if on < 3:
			for u in workers:
				if on >= 3:
					break
				if u.order == Unit.O.GATHER and u.gnode is ResourceNode and u.carry == 0 and u.p.distance_to(e.p) < 22.0:
					u.cmd_gather(e)
					on += 1
	# idle workers go to the least crowded base's crystals
	for u in workers:
		if u.order == Unit.O.IDLE:
			var n = _best_mineral(u.p, built_mains)
			if n:
				u.cmd_gather(n)


func _best_mineral(from: Vector2, built_mains: Array):
	var best = null
	var best_s := INF
	for b in built_mains:
		var miners := 0
		var nodes: Array = []
		for r in world.resources:
			if r.kind == "mineral" and not r.dead and r.amount > 0 and r.p.distance_to(b.p) < 12.0:
				nodes.append(r)
		if nodes.is_empty():
			continue
		for u in world.units:
			if u.owner_id == pid and u.is_worker and u.order == Unit.O.GATHER and u.gnode is ResourceNode and u.gnode.p.distance_to(b.p) < 12.0:
				miners += 1
		var sat := float(miners) / float(nodes.size() * 2)
		var s := sat * 40.0 + from.distance_to(b.p) * 0.2
		if s < best_s:
			best_s = s
			best = nodes[randi() % nodes.size()]
	if best == null:
		best = world.nearest_resource(pid, from, "mineral")
	return best


func _supply(pl: PlayerState) -> void:
	var cap: int = world.supply_cap(pid)
	if cap >= Defs.SUPPLY_MAX:
		return
	var used: int = world.supply_used(pid)
	var producers := 0
	for b in world.buildings:
		if b.owner_id == pid and not b.dead and b.built and b.produces().size() > 0:
			producers += 1
	var unfinished := 0
	for b in _mine("supply", true):
		if not b.built:
			unfinished += 1
	for b in _mine("main", true):
		if not b.built:
			unfinished += 2
	unfinished += _pending("supply")
	var need: int = 3 + producers * 2
	if cap + unfinished * 8 - used < need and pl.minerals >= 100:
		_build("supply")


func _tech(pl: PlayerState, workers: Array, mains: Array, active: Array) -> void:
	var t: float = world.time
	var td: float = float(cfg["tech_delay"])
	var used: int = world.supply_used(pid)
	var n_barracks := _count("barracks")
	var n_ext := _count("extractor")
	var n_factory := _count("factory")
	var n_air := _count("airfield")
	var n_special := _count("special")
	var unfinished_mains := mains.size() - _mine("main", false).size() + _pending("main")
	var want_mains: int = mini(int(cfg["max_mains"]), 1 + int(t / float(cfg["expand_at"])))
	var want := ""
	if n_barracks == 0 and used >= 13:
		want = "barracks"
	elif n_ext == 0 and n_barracks > 0 and used >= 15:
		want = "extractor"
	elif active.size() + unfinished_mains < want_mains:
		want = "main"
	elif n_factory == 0 and world.has_built(pid, bid("barracks")) and t > 150.0 * td:
		want = "factory"
	elif n_ext < 2 and n_factory > 0:
		want = "extractor"
	elif n_air == 0 and world.has_built(pid, bid("factory")) and t > 300.0 * td:
		want = "airfield"
	elif n_special == 0 and world.has_built(pid, bid("airfield")) and t > 480.0 * td:
		want = "special"
	elif _free_slime_near_mains() > 0 and _live_extractors() < active.size() * 2 and t > 240.0 * td:
		want = "extractor"
	else:
		# more production as the economy grows
		var nb := active.size()
		if n_barracks < mini(int(cfg["max_barracks"]), 1 + nb):
			want = "barracks"
		elif n_factory > 0 and n_factory < mini(int(cfg["max_factory"]), nb):
			want = "factory"
		elif n_air > 0 and n_air < mini(int(cfg["max_air"]), nb):
			want = "airfield"
		if want != "" and pl.minerals < 300:
			want = ""
	if want == "":
		return
	var cost: Array = Defs.buildings[bid(want)]["cost"]
	if pl.can_afford(cost):
		_build(want)
	else:
		# save up for it: the army waits
		reserve = [int(cost[0]), int(cost[1])]


func _live_extractors() -> int:
	var n := _pending("extractor")
	for e in _mine("extractor", true):
		if e.slime_node != null and e.slime_node.amount > 0:
			n += 1
	return n


func _free_slime_near_mains() -> int:
	var n := 0
	for b in _mine("main", false):
		for r in world.resources:
			if r.kind == "slime" and not r.dead and r.extractor == null and r.amount > 0 and r.p.distance_to(b.p) < 14.0:
				n += 1
	return n


func _train_workers(pl: PlayerState, workers: Array, active: Array) -> void:
	var exts := _live_extractors()
	var want_workers: int = mini(int(cfg["worker_cap"]), maxi(1, active.size()) * 16 + exts * 3 + 2)
	var queued := _queued(uid("worker"))
	for m in _mine("main", false):
		if m.queue.size() < 1 and workers.size() + queued < want_workers and pl.minerals >= 50:
			if world.queue_unit(m, uid("worker")) == "":
				queued += 1


func _train_army(pl: PlayerState) -> void:
	var qmax: int = int(cfg["queue"])
	var enemy := _enemy_mix()
	# expensive producers choose first
	for slot in ["special", "airfield", "factory", "barracks"]:
		for b in world.buildings:
			if b.owner_id != pid or b.dead or not b.built or b.slot != slot:
				continue
			if b.queue.size() >= qmax:
				continue
			var choice := _pick_unit(b, enemy, pl)
			if choice != "":
				world.queue_unit(b, choice)
			elif slot == "special" and pl.slime >= 300:
				# save crystals for the big unit
				reserve[0] = maxi(int(reserve[0]), 400)


func _queued(id: String) -> int:
	var n := 0
	for b in world.buildings:
		if b.owner_id == pid and not b.dead:
			for q in b.queue:
				if q == id:
					n += 1
	return n


func _enemy_mix() -> Dictionary:
	var m := {"light": 0.0, "armored": 0.0, "air": 0.0, "total": 0.0}
	for u in world.units:
		if u.dead or u.owner_id == pid or u.owner_id < 0 or u.is_worker:
			continue
		var v := Defs.value_of(u.def_id)
		m["total"] += v
		for tag in ["light", "armored", "air"]:
			if u.tags.has(tag):
				m[tag] += v
	return m


func _pick_unit(b: Building, enemy: Dictionary, pl: PlayerState) -> String:
	var opts: Array = b.produces()
	var tot: float = maxf(1.0, enemy["total"])
	var light: float = enemy["light"] / tot
	var armored: float = enemy["armored"] / tot
	var air: float = enemy["air"] / tot
	mix_flip += 1
	var pref: Array = []
	var slime_rich: bool = pl.slime > 250
	match b.slot:
		"barracks":
			if air > 0.3 or (mix_flip % 3 != 0 and not slime_rich):
				pref = [uid("infantry"), uid("heavy")]
			else:
				pref = [uid("heavy"), uid("infantry")]
		"factory":
			if armored > light or slime_rich:
				pref = [uid("vehicle_missile"), uid("vehicle_flame")]
			else:
				pref = [uid("vehicle_flame"), uid("vehicle_missile")]
			if mix_flip % 4 == 0:
				pref.reverse()
		"airfield":
			if air > 0.2 or (mix_flip % 3 == 0 and not slime_rich):
				pref = [uid("air_light"), uid("air_heavy")]
			else:
				pref = [uid("air_heavy"), uid("air_light")]
		"special":
			pref = [uid("special")]
	for id in pref:
		if not opts.has(id):
			continue
		var ud: Dictionary = Defs.units[id]
		if pl.can_afford(ud["cost"]) and world.supply_used(pid) + int(ud["supply"]) <= world.supply_cap(pid):
			# leave what we are saving for
			if pl.minerals - int(ud["cost"][0]) >= int(reserve[0]) and pl.slime - int(ud["cost"][1]) >= int(reserve[1]):
				return id
	return ""


# ---------------------------------------------------------------- placing buildings

func _build(slot: String) -> bool:
	var id := bid(slot)
	var bd: Dictionary = Defs.buildings[id]
	var pl: PlayerState = world.players[pid]
	if not pl.can_afford(bd["cost"]):
		return false
	if world.missing_requirement(pid, id) != "":
		return false
	var c = _spot(slot)
	if c == null:
		return false
	var cell: Vector2i = c
	var center := Vector2(cell.x + bd["size"] * 0.5, cell.y + bd["size"] * 0.5)
	var w = _builder(center)
	if w == null:
		return false
	return world.command_build(w, id, cell) == ""


func _builder(at: Vector2):
	var best = null
	var bd := INF
	for u in world.units:
		if u.owner_id != pid or u.dead or not u.is_worker or u.hidden_inside or u.build_id != "":
			continue
		if u.order == Unit.O.GATHER and u.gnode is Building:
			continue
		var d: float = u.p.distance_to(at) + (5.0 if u.carry > 0 else 0.0)
		if d < bd:
			bd = d
			best = u
	return best


func _spot(slot: String) -> Variant:
	match slot:
		"extractor":
			var best = null
			var bdist := INF
			for b in _mine("main", false):
				for r in world.resources:
					if r.kind != "slime" or r.dead or r.extractor != null or r.amount <= 0:
						continue
					if _reserved(r.cell):
						continue
					var d: float = r.p.distance_to(b.p)
					if d < 14.0 and d < bdist:
						bdist = d
						best = r.cell
			return best
		"main":
			var s = _nearest_site(home, true)
			if s == null:
				return null
			if _reserved(s["cell"]):
				return null
			return s["cell"]
	var bd: Dictionary = Defs.buildings[bid(slot)]
	var sz: int = int(bd["size"])
	var mains := _mine("main", false)
	if mains.is_empty():
		return null
	var anchor: Vector2 = mains[0].p
	var away := base_dir
	var rng := RandomNumberGenerator.new()
	rng.seed = int(world.time * 10.0) + pid
	for attempt in 60:
		var r := 6.5 + float(attempt) * 0.18
		var a := atan2(away.y, away.x) + rng.randf_range(-1.6, 1.6)
		var q := anchor + Vector2(cos(a), sin(a)) * r
		var c := Vector2i(int(floor(q.x - sz * 0.5 + 0.5)), int(floor(q.y - sz * 0.5 + 0.5)))
		# keep a one-cell lane round every building
		if world.grid.rect_free(c - Vector2i(1, 1), Vector2i(sz + 2, sz + 2)) and world.can_place(pid, bid(slot), c) and not _reserved(c) and not _near_minerals(c, sz):
			return c
	return null


func _near_minerals(c: Vector2i, sz: int) -> bool:
	var rect := Rect2(Vector2(c), Vector2(sz, sz)).grow(2.5)
	for r in world.resources:
		if not r.dead and rect.intersects(Rect2(Vector2(r.cell), Vector2(r.cells))):
			return true
	return false


func _reserved(c: Vector2i) -> bool:
	for u in world.units:
		if u.owner_id == pid and u.build_id != "" and u.build_cell.distance_to(c) < 4.0:
			return true
	return false


func _nearest_site(from: Vector2, free_only: bool):
	var best = null
	var bd := INF
	for s in world.sites:
		if free_only and s["taken_by"] >= 0:
			continue
		var d: float = (s["center"] as Vector2).distance_to(from)
		if d < 1.0:
			continue
		# don't walk into the enemy's home
		var enemy_home := false
		for pl in world.players:
			if pl.id != pid and (world.sites[pl.start_site]["center"] as Vector2).distance_to(s["center"]) < 1.0:
				enemy_home = true
		if enemy_home:
			continue
		if d < bd:
			bd = d
			best = s
	return best


# ---------------------------------------------------------------- the army

func _army(army: Array) -> void:
	if army.is_empty():
		return
	var supply := 0
	var center := Vector2.ZERO
	for u in army:
		supply += u.supply
		center += u.p
	center /= army.size()
	# defend first: any enemy near our buildings?
	var threat = _threat()
	if threat != null:
		state = "defend"
		for u in army:
			if u.order != Unit.O.ATTACK and (u.order == Unit.O.IDLE or u.order == Unit.O.MOVE or u.goal.distance_to(threat) > 8.0):
				if u.target == null:
					u.cmd_move(threat, true)
		return
	if state == "defend":
		state = "build"
		for u in army:
			u.cmd_move(rally + Vector2(randf_range(-3, 3), randf_range(-3, 3)), false)
	if state == "attack":
		# retreat when the wave is spent
		if supply < sent_supply * 0.3 and supply < wave_supply * 0.5:
			state = "build"
			world.command_move(army, rally, false)
			return
		if attack_target == null or not is_instance_valid(attack_target) or attack_target.dead:
			attack_target = _enemy_target(center)
		if attack_target == null:
			return
		# reinforcements wait at the rally and join in groups
		var waiting: Array = []
		var wait_sup := 0
		var front := Vector2.ZERO
		var n_front := 0
		for u in army:
			if u.p.distance_to(rally) < 10.0 and (u.order == Unit.O.IDLE or u.order == Unit.O.MOVE):
				waiting.append(u)
				wait_sup += u.supply
			elif u.order == Unit.O.IDLE:
				# arrived with nothing to shoot: push on
				u.cmd_move(attack_target.p, true)
			else:
				front += u.p
				n_front += 1
		if waiting.size() > 0 and (wait_sup >= 8 or n_front == 0):
			world.command_move(waiting, attack_target.p if n_front == 0 else front / n_front, true)
		return
	# building up: gather at the rally, attack at the threshold
	var loose: Array = []
	for u in army:
		if u.order == Unit.O.IDLE and u.p.distance_to(rally) > 8.0:
			loose.append(u)
	if loose.size() > 0:
		world.command_move(loose, rally, false)
	if supply >= wave_supply or world.supply_used(pid) >= 190:
		state = "attack"
		sent_supply = supply
		last_wave_t = world.time
		wave_supply += int(cfg["wave_step"])
		attack_target = _enemy_target(center)
		if attack_target:
			world.command_move(army, attack_target.p, true)


func _threat():
	var mine: Array = []
	for b in world.buildings:
		if b.owner_id == pid and not b.dead:
			mine.append(b)
	for u in world.units:
		if u.dead or u.owner_id == pid or u.owner_id < 0:
			continue
		for b in mine:
			if b.p.distance_to(u.p) < 16.0:
				return u.p
	return null


func _enemy_target(from: Vector2):
	var best = null
	var bd := INF
	for b in world.buildings:
		if b.dead or b.owner_id == pid or b.owner_id < 0:
			continue
		var d: float = b.p.distance_to(from)
		if d < bd:
			bd = d
			best = b
	return best

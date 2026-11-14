class_name Commander
extends Node
## Turns touches into selections and orders.
##
## Tap your unit/building: select it. Double-tap (or long-press) a unit: select
## every one of that type on screen. Long-press then drag: box select.
## With units selected: tap ground to attack-move there (workers just move),
## tap an enemy to attack it, tap crystals or your Void Machine to harvest.
## With a production building selected: tap ground to set its rally point.
## One finger drags the map, two fingers pinch to zoom.

signal selection_changed
signal mode_changed

enum M { NONE, PLACE, ATTACK, MOVE, RALLY }

const TAP_MOVE := 14.0
const LONG_PRESS := 0.42
const DOUBLE_TAP := 0.38

var world: World
var rig: CameraRig
var hud = null
var pid: int = 0
var selection: Array = []
var mode: int = M.NONE
var place_id: String = ""
var place_cell: Vector2i = Vector2i.ZERO
var place_ok: bool = false
var ghost: Node3D = null
var ghost_base: MeshInstance3D = null
var touches: Dictionary = {}
var multi: bool = false
var pinch_d: float = 0.0
var box_active: bool = false
var box_start: Vector2 = Vector2.ZERO
var box_end: Vector2 = Vector2.ZERO
var last_tap_t: float = -10.0
var last_tap_e = null
var groups: Dictionary = {}


func now() -> float:
	return Time.get_ticks_msec() / 1000.0


func _process(_delta: float) -> void:
	# drop the dead from the selection
	var changed := false
	var i := selection.size() - 1
	while i >= 0:
		var e = selection[i]
		if not is_instance_valid(e) or e.dead or (e.owner_id != pid and not e.shown):
			if is_instance_valid(e):
				e.set_selected(false)
			selection.remove_at(i)
			changed = true
		i -= 1
	if changed:
		selection_changed.emit()
	# long press: start a box
	if touches.size() == 1 and not multi:
		var idx: int = touches.keys()[0]
		var t: Dictionary = touches[idx]
		if not t["moved"] and not t["long"] and now() - float(t["t"]) >= LONG_PRESS and mode == M.NONE:
			t["long"] = true
			box_active = true
			box_start = t["start"]
			box_end = t["start"]
			if hud:
				hud.haptic_hint("Drag to select")
	if mode == M.PLACE:
		_update_ghost()


func _unhandled_input(ev: InputEvent) -> void:
	if world == null or world.over:
		return
	if ev is InputEventScreenTouch:
		_touch(ev)
	elif ev is InputEventScreenDrag:
		_drag(ev)
	elif ev is InputEventMouseButton and ev.pressed:
		if hud and hud.blocks(ev.position):
			return
		match ev.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				rig.zoom_by(0.9)
			MOUSE_BUTTON_WHEEL_DOWN:
				rig.zoom_by(1.1)
			MOUSE_BUTTON_RIGHT:
				if mode == M.PLACE:
					cancel_mode()
				else:
					smart(ev.position, true)
	elif ev is InputEventMagnifyGesture:
		rig.zoom_by(1.0 / ev.factor)
	elif ev is InputEventPanGesture:
		rig.pan_pixels(-ev.delta * 8.0)
	elif ev is InputEventKey and ev.pressed and not ev.echo:
		_key(ev)


func _touch(ev: InputEventScreenTouch) -> void:
	if ev.pressed:
		if hud and hud.blocks(ev.position):
			return
		touches[ev.index] = {"start": ev.position, "pos": ev.position, "t": now(), "moved": false, "long": false}
		if touches.size() >= 2:
			multi = true
			box_active = false
			var ps: Array = touches.values()
			pinch_d = (ps[0]["pos"] as Vector2).distance_to(ps[1]["pos"])
		return
	if not touches.has(ev.index):
		return
	var t: Dictionary = touches[ev.index]
	touches.erase(ev.index)
	if touches.is_empty():
		var was_multi := multi
		multi = false
		if was_multi:
			return
		if box_active:
			box_active = false
			if t["moved"]:
				_finish_box()
			else:
				long_press(ev.position)
			return
		if not t["moved"]:
			tap(ev.position)
		else:
			var dt := now() - float(t["t"])
			if dt < 0.25 and mode != M.PLACE:
				var v: Vector2 = (ev.position - (t["start"] as Vector2)) / maxf(dt, 0.05)
				rig.fling(v * 0.6)


func _drag(ev: InputEventScreenDrag) -> void:
	if not touches.has(ev.index):
		return
	var t: Dictionary = touches[ev.index]
	t["pos"] = ev.position
	if not t["moved"] and (ev.position - (t["start"] as Vector2)).length() > TAP_MOVE:
		t["moved"] = true
	if touches.size() >= 2:
		var ps: Array = touches.values()
		var d := (ps[0]["pos"] as Vector2).distance_to(ps[1]["pos"])
		if pinch_d > 1.0 and d > 1.0:
			rig.zoom_by(pinch_d / d)
		pinch_d = d
		rig.pan_pixels(ev.relative * 0.5)
		return
	if box_active:
		box_end = ev.position
		return
	if t["moved"]:
		rig.pan_pixels(ev.relative)


func _key(ev: InputEventKey) -> void:
	match ev.keycode:
		KEY_ESCAPE:
			if mode != M.NONE:
				cancel_mode()
			elif hud:
				hud.toggle_menu()
		KEY_Q:
			action("attack")
		KEY_X:
			action("stop")
		KEY_H:
			action("hold")
		KEY_F2:
			action("army")
		KEY_PERIOD:
			action("idle")
		KEY_TAB:
			action("base")
		KEY_1, KEY_2, KEY_3, KEY_4, KEY_5:
			var n: int = ev.keycode - KEY_0
			if ev.ctrl_pressed or ev.meta_pressed:
				groups[n] = selection.duplicate()
			elif groups.has(n):
				var g: Array = []
				for e in groups[n]:
					if is_instance_valid(e) and not e.dead:
						g.append(e)
				set_selection(g)


# ---------------------------------------------------------------- taps

func tap(sp: Vector2) -> void:
	match mode:
		M.PLACE:
			var g := rig.screen_to_ground(sp)
			var c := _cell_for(place_id, g)
			if c == place_cell:
				confirm_place()
			else:
				place_cell = c
		M.ATTACK:
			var e = pick(sp)
			var army := own_units(false)
			if e and e.owner_id >= 0 and e.owner_id != pid:
				world.command_attack(army, e)
				world.fx.marker(e.p, Color(1, 0.3, 0.2))
			else:
				var g := rig.screen_to_ground(sp)
				world.command_move(army, g, true)
				world.fx.marker(g, Color(1, 0.3, 0.2))
			Sfx.play("click")
			cancel_mode()
		M.MOVE:
			var g := rig.screen_to_ground(sp)
			world.command_move(own_units(true), g, false)
			world.fx.marker(g, Color(0.3, 1, 0.45))
			Sfx.play("click")
			cancel_mode()
		M.RALLY:
			_set_rally(sp)
			cancel_mode()
		_:
			smart(sp, false)


func long_press(sp: Vector2) -> void:
	var e = pick(sp)
	if e and e is Unit and e.owner_id == pid:
		select_type_on_screen(e.def_id)
	else:
		tap(sp)


## The context action for a tap (or right click) at sp.
func smart(sp: Vector2, right_click: bool) -> void:
	var e = pick(sp)
	var g := rig.screen_to_ground(sp)
	var army := own_units(false)
	var workers := own_workers()
	var all_units := army + workers
	var producers := own_producers()
	if e != null:
		if e.owner_id == pid:
			if e is Building and e.slot == "extractor" and e.built and workers.size() > 0:
				world.command_gather(workers, e)
				_ack(e.p, Color(0.6, 0.4, 1.0))
				return
			if right_click and all_units.size() > 0:
				world.command_move(all_units, e.p, false)
				_ack(e.p, Color(0.3, 1, 0.45))
				return
			_select_tap(e)
			return
		if e.owner_id >= 0:
			if all_units.size() > 0:
				world.command_attack(army, e)
				if workers.size() > 0 and army.is_empty():
					world.command_attack(workers, e)
				_ack(e.p, Color(1, 0.3, 0.2))
			else:
				_select_tap(e)
			return
		if e is ResourceNode:
			if workers.size() > 0:
				if e.kind == "mineral":
					world.command_gather(workers, e)
					_ack(e.p, Color(1, 0.85, 0.3))
				elif e.extractor and e.extractor.owner_id == pid and e.extractor.built:
					world.command_gather(workers, e.extractor)
					_ack(e.p, Color(0.6, 0.4, 1.0))
				else:
					_say("Build a %s on the slime first" % Defs.buildings[Defs.building_id(world.players[pid].race, "extractor")]["name"], "error")
				if army.size() > 0:
					world.command_move(army, g, true)
				return
			if producers.size() > 0:
				_set_rally(sp)
				return
			if army.size() > 0:
				world.command_move(army, g, true)
				_ack(g, Color(1, 0.3, 0.2))
				return
			_select_tap(e)
			return
	# plain ground
	if all_units.size() > 0:
		if army.size() > 0:
			world.command_move(army, g, true)
		if workers.size() > 0:
			world.command_move(workers, g, false)
		_ack(g, Color(1, 0.45, 0.3) if army.size() > 0 else Color(0.3, 1, 0.45))
		return
	if producers.size() > 0:
		_set_rally(sp)
		return
	if selection.size() > 0 and not right_click:
		set_selection([])


func _ack(at: Vector2, col: Color) -> void:
	world.fx.marker(at, col)
	Sfx.play("click")


func _say(t: String, kind: String) -> void:
	if hud:
		hud.show_message(t, kind)
	if kind == "error":
		Sfx.play("error")


func _set_rally(sp: Vector2) -> void:
	var e = pick(sp)
	var g := rig.screen_to_ground(sp)
	for b in own_producers():
		b.rally_set = true
		b.rally = g
		b.rally_node = e if (e is ResourceNode and e.kind == "mineral") else null
		if e is Building and e.slot == "extractor" and e.owner_id == pid:
			b.rally_node = e
	_ack(g, Color(0.4, 0.8, 1.0))


func _select_tap(e) -> void:
	var t := now()
	if e is Unit and e.owner_id == pid and last_tap_e == e and t - last_tap_t < DOUBLE_TAP:
		select_type_on_screen(e.def_id)
		last_tap_e = null
		return
	last_tap_e = e
	last_tap_t = t
	set_selection([e])
	Sfx.play("click")


## The entity under a screen point (finger-sized slack).
func pick(sp: Vector2):
	var best = null
	var best_s := INF
	var g := rig.screen_to_ground(sp)
	for list in [world.units, world.buildings, world.resources]:
		for e in list:
			if e.dead or not e.shown:
				continue
			if e is Unit and e.hidden_inside:
				continue
			var fly: float = e.fly if e is Unit else 0.0
			var c3 := Vector3(e.p.x, fly + e.height * 0.45, e.p.y)
			if not rig.in_front(c3):
				continue
			var sc := rig.to_screen(c3)
			var edge := rig.to_screen(c3 + Vector3(e.radius, 0, 0))
			var pr := sc.distance_to(edge)
			var slack := 24.0
			var d := sp.distance_to(sc)
			var s := INF
			if d <= pr + slack:
				s = d / (pr + slack)
			if (e is Building or e is ResourceNode) and e.edge_point(g).distance_to(g) < 0.05:
				s = minf(s, 0.6)
			if e is Unit:
				s -= 0.25
			if s < best_s:
				best_s = s
				best = e
	return best


# ---------------------------------------------------------------- selection

func set_selection(list: Array) -> void:
	for e in selection:
		if is_instance_valid(e):
			e.set_selected(false)
	selection = list
	for e in selection:
		e.set_selected(true)
	if mode != M.PLACE:
		cancel_mode()
	selection_changed.emit()


func select_type_on_screen(def_id: String) -> void:
	var list: Array = []
	for u in world.units:
		if u.owner_id == pid and u.def_id == def_id and not u.dead and not u.hidden_inside and rig.sees(u.p):
			list.append(u)
	set_selection(list)
	Sfx.play("click")


func _finish_box() -> void:
	var r := Rect2(box_start, Vector2.ZERO).expand(box_end)
	var army: Array = []
	var workers: Array = []
	for u in world.units:
		if u.owner_id != pid or u.dead or u.hidden_inside:
			continue
		var c3 := Vector3(u.p.x, u.fly + u.height * 0.4, u.p.y)
		if not rig.in_front(c3):
			continue
		if r.grow(10).has_point(rig.to_screen(c3)):
			if u.is_worker:
				workers.append(u)
			else:
				army.append(u)
	set_selection(army if army.size() > 0 else workers)
	Sfx.play("click")


func own_units(include_workers: bool) -> Array:
	var out: Array = []
	for e in selection:
		if e is Unit and e.owner_id == pid and not e.dead and (include_workers or not e.is_worker):
			out.append(e)
	return out


func own_workers() -> Array:
	var out: Array = []
	for e in selection:
		if e is Unit and e.owner_id == pid and not e.dead and e.is_worker:
			out.append(e)
	return out


func own_producers() -> Array:
	var out: Array = []
	for e in selection:
		if e is Building and e.owner_id == pid and not e.dead and e.produces().size() > 0:
			out.append(e)
	return out


# ---------------------------------------------------------------- actions from the HUD

func action(a: String) -> void:
	var parts := a.split(":")
	match parts[0]:
		"attack":
			if own_units(false).size() > 0:
				set_mode(M.ATTACK)
				_say("Tap a target or the ground to attack-move", "hint")
		"move":
			if own_units(true).size() > 0:
				set_mode(M.MOVE)
				_say("Tap where to move (units won't stop to fight)", "hint")
		"stop":
			for u in own_units(true):
				u.cmd_stop()
			Sfx.play("click")
		"hold":
			for u in own_units(false):
				u.cmd_hold()
			Sfx.play("click")
		"rally":
			set_mode(M.RALLY)
			_say("Tap where new units should gather", "hint")
		"gather":
			var ws := own_workers()
			if ws.size() > 0:
				var n = world.nearest_resource(pid, ws[0].p, "mineral")
				if n:
					world.command_gather(ws, n)
					_ack(n.p, Color(1, 0.85, 0.3))
		"train":
			_train(parts[1])
		"cancel_q":
			var bs := own_producers()
			if bs.size() > 0:
				world.cancel_queue(bs[0], int(parts[1]))
				Sfx.play("click")
		"cancel_build":
			for e in selection:
				if e is Building and not e.built:
					world.cancel_construction(e)
		"build":
			start_place(parts[1])
		"army":
			var list: Array = []
			for u in world.units:
				if u.owner_id == pid and not u.is_worker and not u.dead:
					list.append(u)
			set_selection(list)
			if list.size() > 0:
				var c := Vector2.ZERO
				for u in list:
					c += u.p
				rig.look_at_ground(c / list.size())
			else:
				_say("No army yet", "error")
		"idle":
			var cand: Array = []
			for u in world.units:
				if u.owner_id == pid and u.is_worker and not u.dead and u.order == Unit.O.IDLE:
					cand.append(u)
			if cand.is_empty():
				_say("No idle workers", "hint")
				return
			var u = cand[0]
			for c2 in cand:
				if not selection.has(c2):
					u = c2
					break
			set_selection([u])
			rig.look_at_ground(u.p)
		"base":
			var mains: Array = []
			for b in world.buildings:
				if b.owner_id == pid and b.slot == "main" and not b.dead:
					mains.append(b)
			if mains.is_empty():
				return
			var pick_b = mains[0]
			if selection.size() == 1 and mains.has(selection[0]):
				pick_b = mains[(mains.find(selection[0]) + 1) % mains.size()]
			set_selection([pick_b])
			rig.look_at_ground(pick_b.p)
		"cancel":
			cancel_mode()
		"confirm":
			if mode == M.PLACE:
				confirm_place()


func _train(uid: String) -> void:
	var bs: Array = []
	for b in own_producers():
		if b.produces().has(uid) and b.built:
			bs.append(b)
	if bs.is_empty():
		return
	bs.sort_custom(func(a, b2): return a.queue.size() < b2.queue.size())
	var err: String = world.queue_unit(bs[0], uid)
	if err == "supply":
		var sname: String = Defs.buildings[Defs.building_id(world.players[pid].race, "supply")]["name"]
		_say("Not enough supply: build a %s" % sname, "error")
	elif err != "":
		_say(err, "error")
	else:
		Sfx.play("click")


func set_mode(m: int) -> void:
	mode = m
	mode_changed.emit()


func cancel_mode() -> void:
	if ghost:
		ghost.queue_free()
		ghost = null
	place_id = ""
	if mode != M.NONE:
		mode = M.NONE
		mode_changed.emit()


# ---------------------------------------------------------------- placing buildings

func start_place(bid: String) -> void:
	var miss := world.missing_requirement(pid, bid)
	if miss != "":
		_say("Requires %s" % miss, "error")
		return
	var bd: Dictionary = Defs.buildings[bid]
	if not world.players[pid].can_afford(bd["cost"]):
		_say("Not enough crystals" if world.players[pid].minerals < int(bd["cost"][0]) else "Not enough Void Slime", "error")
		return
	cancel_mode()
	place_id = bid
	var start := rig.focus
	# extractors and bases start on the nearest sensible spot
	if String(bd["slot"]) == "extractor":
		var best = null
		var bdist := INF
		for r in world.resources:
			if r.kind == "slime" and r.extractor == null and not r.dead:
				var d: float = r.p.distance_to(rig.focus)
				if d < bdist:
					bdist = d
					best = r
		if best:
			start = best.p
			rig.look_at_ground(best.p)
	elif String(bd["slot"]) == "main":
		var best_s = null
		var sd := INF
		for s in world.sites:
			if s["taken_by"] < 0:
				var d: float = (s["center"] as Vector2).distance_to(rig.focus)
				if d < sd:
					sd = d
					best_s = s
		if best_s:
			start = best_s["center"]
			rig.look_at_ground(start)
	place_cell = _cell_for(bid, start)
	if String(bd["slot"]) != "extractor" and String(bd["slot"]) != "main":
		var spot = world.suggest_spot(pid, bid, start)
		if spot != null:
			place_cell = spot
	_make_ghost(bid)
	set_mode(M.PLACE)
	_say("Tap to move, tap again (or ✓) to build", "hint")


func _cell_for(bid: String, g: Vector2) -> Vector2i:
	var bd: Dictionary = Defs.buildings[bid]
	var sz: int = int(bd["size"])
	if String(bd["slot"]) == "extractor":
		var s = world.snap_extractor(g)
		if s != null:
			return s
	if String(bd["slot"]) == "main":
		var s2 = world.snap_main(g)
		if s2 != null:
			return s2
	return Vector2i(int(floor(g.x - sz * 0.5 + 0.5)), int(floor(g.y - sz * 0.5 + 0.5)))


func _make_ghost(bid: String) -> void:
	var bd: Dictionary = Defs.buildings[bid]
	var sz: int = int(bd["size"])
	ghost = Node3D.new()
	ghost.name = "Ghost"
	world.add_child(ghost)
	ghost_base = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(sz, 0.08, sz)
	ghost_base.mesh = bm
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(0.3, 1, 0.4, 0.45)
	ghost_base.material_override = m
	ghost.add_child(ghost_base)
	var ps := Models.scene_for(bid)
	var inner: Node3D
	if ps:
		inner = ps.instantiate()
		ghost.add_child(inner)
		Models.fit(inner, sz - 0.1, float(bd["model_h"]) * 1.35)
	else:
		inner = Node3D.new()
		ghost.add_child(inner)
		Models._placeholder_building(inner, String(bd["slot"]), String(bd["race"]), sz, float(bd["model_h"]), world.players[pid].color)
	var gm := StandardMaterial3D.new()
	gm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	gm.albedo_color = Color(0.7, 1.0, 0.8, 0.45)
	gm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for mi in inner.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = gm
	ghost.set_meta("gm", gm)


func _update_ghost() -> void:
	if ghost == null:
		return
	var bd: Dictionary = Defs.buildings[place_id]
	var sz: int = int(bd["size"])
	ghost.position = Vector3(place_cell.x + sz * 0.5, 0.05, place_cell.y + sz * 0.5)
	place_ok = world.can_place(pid, place_id, place_cell)
	var col := Color(0.3, 1, 0.4, 0.45) if place_ok else Color(1, 0.25, 0.2, 0.5)
	(ghost_base.material_override as StandardMaterial3D).albedo_color = col
	var gm: StandardMaterial3D = ghost.get_meta("gm")
	gm.albedo_color = Color(col.r * 0.6 + 0.4, col.g * 0.6 + 0.4, col.b * 0.6 + 0.4, 0.42)


func confirm_place() -> void:
	if place_id == "":
		return
	var bd: Dictionary = Defs.buildings[place_id]
	var sz: int = int(bd["size"])
	var center := Vector2(place_cell.x + sz * 0.5, place_cell.y + sz * 0.5)
	var w = _builder_for(center)
	if w == null:
		_say("No worker available to build", "error")
		return
	var err: String = world.command_build(w, place_id, place_cell)
	if err != "":
		_say(err, "error")
		return
	world.fx.marker(center, Color(0.4, 1, 0.5))
	Sfx.play("click")
	cancel_mode()


## The selected worker nearest the site, else the nearest crystal worker.
func _builder_for(at: Vector2):
	var best = null
	var bd := INF
	for u in own_workers():
		var d: float = u.p.distance_to(at)
		if d < bd:
			bd = d
			best = u
	if best:
		return best
	for u in world.units:
		if u.owner_id != pid or not u.is_worker or u.dead or u.hidden_inside:
			continue
		if u.order == Unit.O.BUILD:
			continue
		var d: float = u.p.distance_to(at) + (4.0 if u.carry > 0 else 0.0)
		if u.order == Unit.O.GATHER and u.gnode is Building:
			d += 30.0
		if d < bd:
			bd = d
			best = u
	return best

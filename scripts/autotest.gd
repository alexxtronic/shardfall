class_name Autotest
extends Node
## Plays the game by itself in a real window and checks it works.
##   Godot --path . --resolution 1280x720 -- --autotest=/tmp/sf_shots [--only=NAME]
## Prints PASS/FAIL lines, saves screenshots, ends with AUTOTEST DONE.
## --only=title|economy|build|army|touch|combat|expand|void|full|models|fx|maps|terrain

var out_dir: String = "/tmp/sf_shots"
var args: PackedStringArray
var main
var m: Match
var passes: int = 0
var fails: int = 0
var only: String = ""


func _ready() -> void:
	for a in args:
		if a.begins_with("--only="):
			only = a.substr(7)
	DirAccess.make_dir_recursive_absolute(out_dir)
	call_deferred("_run")


func check(ok: bool, what: String) -> void:
	if ok:
		passes += 1
		print("PASS ", what)
	else:
		fails += 1
		print("FAIL ", what)


func frames(n: int = 3) -> void:
	for i in n:
		await get_tree().process_frame


func shot(name: String) -> void:
	await frames(3)
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [out_dir, name])


func want(n: String) -> bool:
	return only == "" or n in only.split(",")


## Fast-forward the simulation (no rendering in between).
func ff(seconds: float) -> void:
	var w: World = m.world
	var steps := int(seconds / 0.05)
	for i in steps:
		w.step(0.05)
		if w.over:
			break
	w._sync_visuals(0.016)


func start(races: Array, ai: bool = true, map_id: String = "shatterfield") -> void:
	if m:
		m.queue_free()
		await frames(2)
	m = Match.new()
	main.add_child(m)
	m.start({"races": races, "ai": [false, ai], "difficulty": "normal", "human": 0, "map": map_id})
	main.match_node = m
	await frames(5)


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	if want("title"):
		await _title()
	if want("economy") or want("build") or want("army") or want("touch") or want("combat") or want("expand"):
		await start(["ambron", "void"], false)
	if want("economy"):
		await _economy()
	if want("touch"):
		await _touch()
	if want("build"):
		await _build("ambron")
	if want("army"):
		await _army("ambron")
	if want("combat"):
		await _combat()
	if want("expand"):
		await _expand()
	if want("void"):
		await start(["void", "ambron"], false)
		await _build("void")
		await _army("void")
	if want("ui"):
		for race in ["ambron", "void"]:
			await start([race, "void" if race == "ambron" else "ambron"], false)
			await _ui(race)
	if want("models"):
		await _models()
	if want("fx"):
		await _fx()
	if want("maps"):
		await _maps()
	if want("terrain"):
		await _terrain()
	if want("full"):
		await _full()
	print("AUTOTEST %d passed, %d failed in %.1f s" % [passes, fails, (Time.get_ticks_msec() - t0) / 1000.0])
	print("AUTOTEST DONE")
	get_tree().quit()


# ---------------------------------------------------------------- checks

## Every map: built headless, checked for fairness and connectivity, drawn as a debug
## image (maps_<id>.png), then shown in 3D from the player's main and the centre.
func _maps() -> void:
	for id in Maps.LIST:
		var w := World.new()
		add_child(w)
		w.setup({"map": id, "visuals": false, "human": -1, "races": ["ambron", "void"], "ai": [false, false]})
		var n: int = w.grid.size
		var asym := 0
		var hasym := 0
		for y in n:
			for x in n:
				var a: bool = w.grid.kind_at(Vector2i(x, y)) == 1
				var b: bool = w.grid.kind_at(Vector2i(n - 1 - x, n - 1 - y)) == 1
				if a != b:
					asym += 1
				if absf(w.terrain.corner[y * (n + 1) + x] - w.terrain.corner[(n - y) * (n + 1) + (n - x)]) > 0.01:
					hasym += 1
		check(asym == 0, "%s: walls are mirror images (%d cells differ)" % [id, asym])
		check(hasym == 0, "%s: heights are mirror images (%d corners differ)" % [id, hasym])
		var short := 0
		for s in w.sites:
			if (s["minerals"] as Array).size() != 8 or (s["slimes"] as Array).size() != 2:
				short += 1
		check(short == 0, "%s: every base has 8 crystals and 2 slime piles (%d short)" % [id, short])
		var cut := 0
		var from: Vector2 = w.grid.nearest_walkable(w.sites[0]["center"] + Vector2(0, -4))
		for s in w.sites:
			var to: Vector2 = w.grid.nearest_walkable(s["center"] - (s["dir"] as Vector2) * 5.0)
			if w.grid.astar.get_id_path(w.grid.cell_of(from), w.grid.cell_of(to)).is_empty():
				cut += 1
		check(cut == 0, "%s: every base can be walked to from the main (%d cut off)" % [id, cut])
		var lv0: int = w.terrain.level_at(w.sites[0]["center"])
		check(lv0 == w.terrain.level_at(w.sites[1]["center"]), "%s: both mains on the same level (%d)" % [id, lv0])
		_map_image(w).save_png("%s/maps_%s.png" % [out_dir, id])
		w.queue_free()
		await frames(2)
		await start(["ambron", "void"], false, id)
		var mw: World = m.world
		mw.fog.enabled = false
		mw.fog.update()
		m.rig.look_at_ground(mw.sites[0]["center"] + Vector2(6, -14))
		m.rig.dist = 40.0
		m.rig.apply()
		await shot("maps_%s_main" % id)
		m.rig.look_at_ground(Vector2(72, 76))
		m.rig.dist = 58.0
		m.rig.apply()
		await shot("maps_%s_centre" % id)


func _map_image(w: World) -> Image:
	var n: int = w.grid.size
	var k := 4
	var img := Image.create(n * k, n * k, false, Image.FORMAT_RGB8)
	for y in n:
		for x in n:
			var c := Vector2i(x, y)
			var lv := float(w.terrain.level[y * n + x])
			var col := Color(0.25, 0.25, 0.28).lightened(lv * 0.28)
			if w.terrain.is_ramp(c):
				col = Color(0.3, 0.75, 0.35)
			elif w.terrain.is_cliff(c):
				col = Color(0.05, 0.05, 0.06)
			elif w.hazard[y * n + x] == 1:
				col = Color(1.0, 0.45, 0.1)
			elif w.grid.kind_at(c) == 1:
				col = Color(0.35, 0.4, 0.55)
			elif w.hazard[y * n + x] == 2:
				col = Color(0.55, 0.85, 1.0)
			var who = w.grid.who_at(c)
			if who is ResourceNode:
				col = Color(1, 0.8, 0.2) if who.kind == "mineral" else Color(0.6, 0.3, 0.85)
			elif who is Building:
				col = Color(0.9, 0.2, 0.2)
			img.fill_rect(Rect2i(x * k, y * k, k, k), col)
	return img


## Elevation in play: a worker walks up a ramp onto high ground, and shots fired uphill miss.
func _terrain() -> void:
	await start(["ambron", "void"], false, "shatterfield")
	var w: World = m.world
	var t: Terrain = w.terrain
	var main_c: Vector2 = w.sites[0]["center"]
	check(t.level_at(main_c) == 1, "the main base stands on high ground")
	var below := w.grid.nearest_walkable(Vector2(26, 88))
	check(t.level_at(below) == 0, "the ground below the ramp is low ground")
	var u := w.spawn_unit("ambron_lancer", 0, below)
	u.cmd_move(main_c + Vector2(6, -6))
	var peak := 0.0
	for i in 400:
		w.step(0.05)
		peak = maxf(peak, u.ground_h())
	check(u.p.distance_to(main_c + Vector2(6, -6)) < 2.0, "a unit walks up the ramp to the main (%.1f m off)" % u.p.distance_to(main_c + Vector2(6, -6)))
	check(absf(u.ground_h() - Terrain.LEVEL_H) < 0.05, "it ends up standing on the plateau (h %.2f)" % u.ground_h())
	# a straight line from below the cliff to the plateau is blocked by the cliff
	check(not w.grid.line_clear(Vector2(10, 96), Vector2(10, 106)), "the cliff blocks a straight walk")
	var lo := w.spawn_unit("ambron_lancer", 0, Vector2(12, 97))
	var hi := w.spawn_unit("void_spitter", 1, Vector2(12, 106))
	check(w.terrain.uphill(lo.p, hi.p) and not w.terrain.uphill(hi.p, lo.p), "shots up the cliff count as uphill, down doesn't")
	var misses := 0
	for i in 400:
		if w.misses(lo, hi):
			misses += 1
	check(misses > 80 and misses < 160, "about 30%% of uphill shots miss (%d of 400)" % misses)
	m.rig.look_at_ground(Vector2(26, 98))
	m.rig.dist = 26.0
	m.rig.apply()
	w._sync_visuals(0.016)
	await shot("70_ramp")
	# the camera picks the plateau top, not the ground plane under it
	var sp := m.rig.to_screen(Vector3(main_c.x + 4, Terrain.LEVEL_H, main_c.y - 8))
	var g := m.rig.screen_to_ground(sp)
	check(g.distance_to(main_c + Vector2(4, -8)) < 0.5, "tapping the plateau picks the plateau (%.2f m off)" % g.distance_to(main_c + Vector2(4, -8)))

func _title() -> void:
	main.show_title()
	await frames(5)
	check(main.title != null and main.title.get_child_count() > 0, "title screen builds")
	await shot("00_title")
	main.title.help.visible = true
	await shot("00_title_help")
	main.title.help.visible = false
	main.title.queue_free()
	main.title = null
	await frames(2)


func _economy() -> void:
	var w: World = m.world
	var pl: PlayerState = w.players[0]
	check(w.units.size() == Defs.START_WORKERS * 2, "both players start with %d workers (%d units)" % [Defs.START_WORKERS, w.units.size()])
	check(w.buildings.size() == 2, "both players start with a main base")
	var crystals := 0
	for r in w.resources:
		if r.kind == "mineral":
			crystals += 1
	check(crystals >= 70 and w.sites.size() == 10, "map has 10 base sites with crystals (%d crystals)" % crystals)
	# both halves must block alike, or one seat mines and walks faster
	var n: int = w.grid.size
	var odd := 0
	var solid := 0
	for y in n:
		for x in n:
			var a := w.grid.kind_at(Vector2i(x, y)) == 1
			if a:
				solid += 1
			if w.grid.kind_at(Vector2i(x, y)) != w.grid.kind_at(Vector2i(n - 1 - x, n - 1 - y)):
				odd += 1
	check(odd == 0 and solid > 0, "the map is point-symmetric: rocks, resources, mains (%d rock cells, %d unmatched)" % [solid, odd])
	await shot("01_start")
	var m0 := pl.minerals
	ff(30.0)
	await frames(2)
	check(pl.minerals > m0 + 200, "workers harvest crystals on their own (%d -> %d in 30 s)" % [m0, pl.minerals])
	await shot("02_harvesting")
	# train a worker from the main base
	var main_b: Building = null
	for b in w.buildings:
		if b.owner_id == 0:
			main_b = b
	m.cmd.set_selection([main_b])
	await frames(2)
	var before := w.units.size()
	m.cmd.action("train:%s" % Defs.unit_id(pl.race, "worker"))
	check(main_b.queue.size() == 1, "main base queues a worker")
	await shot("03_main_selected")
	ff(13.0)
	check(w.units.size() == before + 1, "worker trained")
	var newest: Unit = w.units[w.units.size() - 1]
	ff(1.0)
	check(newest.order == Unit.O.GATHER, "new worker goes harvesting by itself")


func _touch() -> void:
	var w: World = m.world
	var rig := m.rig
	var cmd := m.cmd
	await frames(2)
	# tap a worker
	var u: Unit = _clear_worker()
	if u == null:
		check(false, "a worker is on screen")
		return
	cmd.set_selection([])
	var sp := rig.to_screen(Vector3(u.p.x, u.height * 0.45, u.p.y))
	await _tap(sp)
	check(cmd.selection.size() == 1 and cmd.selection[0] is Unit and cmd.selection[0].owner_id == 0, "tap selects a unit")
	# tap ground moves it
	# an open bit of ground near it, clear of buildings, units and the HUD
	var g := u.p
	for i in 80:
		var q := u.p + Vector2(cos(i * 0.9), sin(i * 0.9)) * (4.0 + i * 0.15)
		var qs := rig.to_screen(Vector3(q.x, 0, q.y))
		if w.grid.kind_at(Vector2i(q)) == 0 and w.units_near(q, 3.0).is_empty() and not w._near_resources(Vector2i(q), 1, 2.5) and not m.hud.blocks(qs) and Rect2(80, 80, 1120, 400).has_point(qs):
			g = q
			break
	await _tap(rig.to_screen(Vector3(g.x, 0, g.y)))
	var sel_u: Unit = u
	check(sel_u.order == Unit.O.MOVE and sel_u.goal.distance_to(g) < 2.5, "tap on ground moves the selected worker")
	# send it back to work by tapping a crystal
	var cr = w.nearest_resource(0, sel_u.p, "mineral")
	await _tap(rig.to_screen(Vector3(cr.p.x, 0.8, cr.p.y)))
	check(sel_u.order == Unit.O.GATHER, "tap on crystals sends the worker harvesting")
	# drag pans the camera
	var f0 := rig.focus
	await _drag(Vector2(640, 360), Vector2(500, 300))
	check(rig.focus.distance_to(f0) > 2.0, "one-finger drag pans the camera")
	# pinch zooms
	var d0 := rig.dist
	await _pinch(Vector2(640, 360), 200.0, 80.0)
	check(rig.dist > d0 * 1.2, "pinch zooms out (%.1f -> %.1f)" % [d0, rig.dist])
	rig.dist = d0
	rig.look_at_ground(f0)
	await frames(2)
	# long-press + drag box select
	await _box(Vector2(300, 200), Vector2(1000, 560))
	check(cmd.selection.size() >= 3, "hold and drag box-selects (%d)" % cmd.selection.size())
	await shot("04_box_selected")
	# double tap selects all of a type
	cmd.set_selection([])
	var u2: Unit = _clear_worker()
	var sp2 := rig.to_screen(Vector3(u2.p.x, u2.height * 0.45, u2.p.y))
	await _tap(sp2)
	await _tap(rig.to_screen(Vector3(u2.p.x, u2.height * 0.45, u2.p.y)))
	check(cmd.selection.size() >= 5, "double-tap selects all of that type on screen (%d)" % cmd.selection.size())
	cmd.action("gather")
	cmd.set_selection([])


## A worker that is on screen and not under a HUD panel.
func _clear_worker() -> Unit:
	for x in m.world.units:
		if x.owner_id == 0 and x.is_worker and not x.hidden_inside and m.rig.sees(x.p):
			var sp: Vector2 = m.rig.to_screen(Vector3(x.p.x, x.height * 0.45, x.p.y))
			if not m.hud.blocks(sp) and Rect2(80, 80, 1120, 400).has_point(sp):
				return x
	return null


func _tap(sp: Vector2) -> void:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = sp
	e.pressed = true
	Input.parse_input_event(e)
	await frames(1)
	var e2 := InputEventScreenTouch.new()
	e2.index = 0
	e2.position = sp
	e2.pressed = false
	Input.parse_input_event(e2)
	await frames(2)


func _drag(a: Vector2, b: Vector2) -> void:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = a
	e.pressed = true
	Input.parse_input_event(e)
	await frames(1)
	var steps := 8
	var prev := a
	for i in steps:
		var p := a.lerp(b, float(i + 1) / steps)
		var d := InputEventScreenDrag.new()
		d.index = 0
		d.position = p
		d.relative = p - prev
		prev = p
		Input.parse_input_event(d)
		await frames(1)
	await get_tree().create_timer(0.35).timeout
	var e2 := InputEventScreenTouch.new()
	e2.index = 0
	e2.position = b
	e2.pressed = false
	Input.parse_input_event(e2)
	await frames(2)


func _pinch(c: Vector2, from_d: float, to_d: float) -> void:
	for i in 2:
		var e := InputEventScreenTouch.new()
		e.index = i
		e.position = c + Vector2((from_d * 0.5) * (1 if i == 0 else -1), 0)
		e.pressed = true
		Input.parse_input_event(e)
	await frames(1)
	var steps := 8
	for s in steps:
		var dd := lerpf(from_d, to_d, float(s + 1) / steps)
		for i in 2:
			var d := InputEventScreenDrag.new()
			d.index = i
			d.position = c + Vector2((dd * 0.5) * (1 if i == 0 else -1), 0)
			d.relative = Vector2.ZERO
			Input.parse_input_event(d)
		await frames(1)
	for i in 2:
		var e2 := InputEventScreenTouch.new()
		e2.index = i
		e2.position = c
		e2.pressed = false
		Input.parse_input_event(e2)
	await frames(2)


func _box(a: Vector2, b: Vector2) -> void:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = a
	e.pressed = true
	Input.parse_input_event(e)
	await get_tree().create_timer(0.6).timeout
	var steps := 8
	var prev := a
	for i in steps:
		var p := a.lerp(b, float(i + 1) / steps)
		var d := InputEventScreenDrag.new()
		d.index = 0
		d.position = p
		d.relative = p - prev
		prev = p
		Input.parse_input_event(d)
		await frames(1)
	var e2 := InputEventScreenTouch.new()
	e2.index = 0
	e2.position = b
	e2.pressed = false
	Input.parse_input_event(e2)
	await frames(2)


func _free_cell(id: String, near: Vector2) -> Variant:
	var w: World = m.world
	var sz: int = int(Defs.buildings[id]["size"])
	for attempt in 260:
		var a := float(attempt) * 0.7
		var q := near + Vector2(cos(a), sin(a)) * (3.0 + attempt * 0.06)
		var c := Vector2i(int(q.x - sz * 0.5), int(q.y - sz * 0.5))
		if w.grid.rect_free(c - Vector2i(1, 1), Vector2i(sz + 2, sz + 2)) and w.can_place(0, id, c):
			return c
	return null


func _place(race: String, slot: String, near: Vector2) -> Building:
	var w: World = m.world
	var id := Defs.building_id(race, slot)
	var bd: Dictionary = Defs.buildings[id]
	var sz: int = int(bd["size"])
	var cell = null
	if slot == "extractor":
		for r in w.resources:
			if r.kind == "slime" and r.extractor == null and r.p.distance_to(near) < 16.0:
				cell = r.cell
				break
	elif slot == "main":
		for s in w.sites:
			if s["taken_by"] < 0 and (s["center"] as Vector2).distance_to(near) < 60.0:
				cell = s["cell"]
				break
	else:
		cell = _free_cell(id, near)
		if cell == null and Defs.needs_power(id):
			# Ambron: the field is full, so put up another relay first
			var rid := Defs.building_id(race, "supply")
			var rc = _free_cell(rid, near + Vector2(randf_range(-8, 8), randf_range(-8, 8)))
			if rc != null:
				w.spawn_building(rid, 0, rc, true)
				cell = _free_cell(id, near)
	if cell == null:
		check(false, "found a spot for %s" % id)
		return null
	# go through the real UI path: place mode, move the ghost, confirm
	m.cmd.start_place(id)
	m.cmd.place_cell = cell
	await frames(2)
	m.cmd.confirm_place()
	var before := w.buildings.size()
	ff(25.0)
	var built: Building = null
	for b in w.buildings:
		if b.def_id == id and b.owner_id == 0 and b.cell == cell:
			built = b
	check(built != null, "worker placed a %s" % bd["name"])
	if built:
		ff(float(bd["time"]) + 2.0)
		check(built.built, "%s finished building" % bd["name"])
	return built


func _build(race: String) -> void:
	var w: World = m.world
	var pl: PlayerState = w.players[0]
	pl.minerals += 6000
	pl.slime += 4000
	var home: Vector2 = w.sites[pl.start_site]["center"]
	var away: Vector2 = -(w.sites[pl.start_site]["dir"] as Vector2).normalized()
	var spot := home + away * 4.0
	# supply first
	var cap0 := w.supply_cap(0)
	var sup := await _place(race, "supply", spot)
	check(w.supply_cap(0) == cap0 + 8, "supply building adds 8 supply")
	var ext := await _place(race, "extractor", home)
	if ext:
		ff(8.0)
		var on := 0
		for u in w.units:
			if u.owner_id == 0 and u.gnode == ext:
				on += 1
		check(on >= 2, "workers go to the new extractor by themselves (%d)" % on)
		var s0 := pl.slime
		ff(20.0)
		check(pl.slime > s0, "Void Slime is harvested (%d -> %d)" % [s0, pl.slime])
	var bar: Building = null
	for slot in ["barracks", "factory", "airfield", "special"]:
		var nb := await _place(race, slot, spot)
		if slot == "barracks":
			bar = nb
	var tower := await _place(race, "tower", spot)
	check(tower != null and not tower.weapon.is_empty(), "%s: the defence tower is built and armed" % race)
	if race == "ambron":
		# power: nothing goes up outside a relay's field
		var far := Vector2i(int(home.x) + 30, int(home.y) - 30)
		var err := w.place_error(0, Defs.building_id(race, "barracks"), far)
		check(err != "" , "ambron: buildings need a relay's power (%s)" % err)
		check(w.place_error(0, Defs.building_id("ambron", "supply"), _free_cell(Defs.building_id("ambron", "supply"), home + Vector2(9, -9))) == "", "ambron: relays go up anywhere")
		if bar:
			check(w.is_powered(bar), "ambron: the barracks is powered")
			# take its relays away: it loses power and stops training
			var cells: Array = []
			for r in w.relays(0):
				if r.p.distance_to(bar.p) <= Defs.POWER_RADIUS:
					cells.append(r.cell)
					r.hp = 0
					w.kill(r, null)
			w._cleanup()
			check(not w.is_powered(bar), "ambron: without a relay the barracks is unpowered")
			w.queue_unit(bar, Defs.unit_id(race, "infantry"))
			ff(3.0)
			check(bar.prod_t == 0.0, "ambron: an unpowered barracks doesn't train")
			for c in cells:
				w.spawn_building(Defs.building_id(race, "supply"), 0, c, true)
			w.power_rev += 1
			ff(1.0)
			check(w.is_powered(bar) and bar.prod_t > 0.0, "ambron: power back, training resumes")
	m.rig.look_at_ground(spot)
	m.rig.dist = 40.0
	await frames(4)
	await shot("10_%s_base" % race)


func _army(race: String) -> void:
	var w: World = m.world
	var pl: PlayerState = w.players[0]
	pl.minerals += 20000
	pl.slime += 20000
	# lots of supply
	var home: Vector2 = w.sites[pl.start_site]["center"]
	for i in 6:
		var id := Defs.building_id(race, "supply")
		for attempt in 200:
			var q := home + Vector2(randf_range(-14, 14), randf_range(-14, 14))
			var c := Vector2i(int(q.x), int(q.y))
			if w.can_place(0, id, c) and w.grid.rect_free(c - Vector2i(1, 1), Vector2i(4, 4)):
				var b := w.spawn_building(id, 0, c, true)
				break
	for slot in ["barracks", "factory", "airfield", "special"]:
		var b: Building = null
		for x in w.buildings:
			if x.owner_id == 0 and x.slot == slot and x.built:
				b = x
		if b == null:
			check(false, "%s exists for training" % slot)
			continue
		m.cmd.set_selection([b])
		await frames(2)
		var q0 := b.queue.size()
		for uid in b.produces():
			m.cmd.action("train:%s" % uid)
		check(b.queue.size() - q0 == b.produces().size(), "%s queues its units (%d -> %d)" % [b.def["name"], q0, b.queue.size()])
	ff(140.0)
	for slot in Defs.UNIT_SLOTS:
		var id := Defs.unit_id(race, slot)
		var n := 0
		for u in w.units:
			if u.def_id == id and u.owner_id == 0:
				n += 1
		check(n > 0, "%s trained" % Defs.units[id]["name"])
	# line them up for a picture
	var army: Array = []
	for u in w.units:
		if u.owner_id == 0 and not u.is_worker:
			army.append(u)
	var spot := home + (Vector2(72, 72) - home).normalized() * 12.0
	w.command_move(army, spot, false)
	ff(15.0)
	m.cmd.set_selection(army)
	m.rig.look_at_ground(spot)
	m.rig.dist = 24.0
	await frames(4)
	await shot("11_%s_army" % race)
	m.cmd.set_selection([])


func _combat() -> void:
	var w: World = m.world
	var pl0: PlayerState = w.players[0]
	var spot := Vector2(72, 80)
	var mine: Array = []
	var theirs: Array = []
	for i in 10:
		mine.append(w.spawn_unit(Defs.unit_id(w.players[0].race, "infantry"), 0, spot + Vector2(-8, i - 5)))
		theirs.append(w.spawn_unit(Defs.unit_id(w.players[1].race, "infantry"), 1, spot + Vector2(8, i - 5)))
	m.rig.look_at_ground(spot)
	m.rig.dist = 22.0
	w.fog.enabled = false
	m.cmd.set_selection(mine)
	await frames(2)
	await _tap(m.rig.to_screen(Vector3(spot.x + 3, 0, spot.y - 7)))
	check(mine[0].order == Unit.O.AMOVE, "tap on ground with army attack-moves")
	for i in 40:
		w.step(0.05)
	await shot("20_combat")
	ff(20.0)
	var dead := 0
	for u in mine + theirs:
		if u.dead:
			dead += 1
	check(dead >= 8, "units fight and die (%d dead)" % dead)
	check(pl0.kills + w.players[1].kills >= 8, "kills are counted")
	w.fog.enabled = true


func _expand() -> void:
	var w: World = m.world
	var pl: PlayerState = w.players[0]
	pl.minerals += 1000
	var nat: Vector2 = w.sites[2]["center"]
	var b := await _place(pl.race, "main", nat)
	if b:
		ff(20.0)
		var miners := 0
		for u in w.units:
			if u.owner_id == 0 and u.is_worker and u.gnode is ResourceNode and u.gnode.p.distance_to(nat) < 12.0:
				miners += 1
		# send six workers over
		var sent := 0
		for u in w.units:
			if u.owner_id == 0 and u.is_worker and sent < 6 and u.order == Unit.O.GATHER:
				u.cmd_gather(w.nearest_resource(0, nat, "mineral"))
				sent += 1
		ff(30.0)
		var dropped := false
		for u in w.units:
			if u.owner_id == 0 and u.is_worker and u.gnode is ResourceNode and u.gnode.p.distance_to(nat) < 12.0:
				dropped = true
		check(dropped, "workers harvest at the new base")
		m.rig.look_at_ground(nat)
		await shot("21_expansion")


## The screens a player goes through to build and train, captured on screen.
func _ui(race: String) -> void:
	var w: World = m.world
	var pl: PlayerState = w.players[0]
	pl.minerals = 2000
	pl.slime = 1000
	if race == "ambron":
		# Ambron needs a relay's field before anything else goes up
		var home: Vector2 = w.sites[pl.start_site]["center"]
		var away: Vector2 = -(w.sites[pl.start_site]["dir"] as Vector2).normalized()
		var rid := Defs.building_id(race, "supply")
		var rc = _free_cell(rid, home + away * 7.0)
		if rc != null:
			w.spawn_building(rid, 0, rc, true)
		m.rig.look_at_ground(home + away * 7.0)
		await frames(2)
	m.hud._left_action("build_menu")
	await frames(4)
	check(m.hud.card.get_child_count() >= 7, "%s: BUILD opens the build menu (%d cards)" % [race, m.hud.card.get_child_count()])
	var screen := Rect2(Vector2.ZERO, m.get_viewport().get_visible_rect().size)
	var off := 0
	for c in m.hud.card.get_children():
		var r: Rect2 = (c as Control).get_global_rect()
		if not screen.encloses(r):
			off += 1
	check(off == 0, "%s: every build card is on screen (%d off)" % [race, off])
	await shot("50_%s_build_menu" % race)
	m.hud._card_action("build:%s" % Defs.building_id(race, "barracks"))
	await frames(4)
	check(m.cmd.mode == Commander.M.PLACE, "%s: picking a building shows the placement ghost" % race)
	await shot("51_%s_placing" % race)
	var cell0: Vector2i = m.cmd.place_cell
	m.cmd.confirm_place()
	await frames(2)
	ff(4.0)
	await frames(2)
	await shot("52_%s_constructing" % race)
	ff(50.0)
	var bar: Building = null
	for b in w.buildings:
		if b.owner_id == 0 and b.slot == "barracks":
			bar = b
	check(bar != null and bar.built, "%s: the infantry building was built where it was placed" % race)
	if bar:
		m.cmd.set_selection([bar])
		m.rig.look_at_ground(bar.p + Vector2(0, 4))
		await frames(4)
		m.hud._card_action("train:%s" % Defs.unit_id(race, "infantry"))
		m.hud._card_action("train:%s" % Defs.unit_id(race, "heavy"))
		await frames(4)
		check(bar.queue.size() == 2, "%s: train buttons queue units" % race)
		await shot("53_%s_training" % race)


func _models() -> void:
	# every unit and building of both races side by side
	await start(["ambron", "void"], false)
	var w: World = m.world
	w.fog.enabled = false
	w.running = false
	var x0 := 40.0
	var row := 0
	for race in ["ambron", "void"]:
		var col := 0
		for slot in Defs.UNIT_SLOTS:
			var u := w.spawn_unit(Defs.unit_id(race, slot), 0 if race == "ambron" else 1, Vector2(x0 + col * 4.5, 60 + row * 8))
			u.facing = 0.0
			col += 1
		row += 1
	w.fog.update()
	w._sync_visuals(0.016)
	m.rig.look_at_ground(Vector2(56, 64))
	m.rig.dist = 26.0
	await shot("30_units")
	# every building of both races in two rows
	for u in w.units.duplicate():
		w.kill(u, null)
	var by := {"ambron": 58, "void": 70}
	for race in ["ambron", "void"]:
		var x := 34
		for slot in Defs.BUILDING_SLOTS:
			var id := Defs.building_id(race, slot)
			var sz: int = int(Defs.BUILDING_SLOTS[slot]["size"])
			var b = w.spawn_building(id, 0 if race == "ambron" else 1, Vector2i(x, by[race] - sz / 2), true)
			check(b != null, "%s spawns for the lineup" % id)
			x += sz + 2
	w.fog.update()
	w._sync_visuals(0.016)
	await frames(3)
	m.rig.look_at_ground(Vector2(52, 64))
	m.rig.dist = 30.0
	await shot("31_buildings")
	m.rig.look_at_ground(Vector2(40, 60))
	m.rig.dist = 18.0
	await shot("32_buildings_close")
	m.rig.look_at_ground(Vector2(44, 72))
	m.rig.dist = 18.0
	await shot("33_buildings_close_void")


## Towers and Void weapons in action, close up, in real time.
func _fx() -> void:
	await start(["ambron", "void"], false)
	if Sfx.enabled:
		var rec := 0
		for n in ["bolt", "beam", "boom", "shell", "slime"]:
			var s = Sfx.streams[n]
			if s is Array and s[0] is AudioStreamOggVorbis and not (s[0] as AudioStreamOggVorbis).loop:
				rec += 1
		check(rec == 5, "recorded clips replace the synthesised sounds, unlooped (%d of 5)" % rec)
		check(Sfx.streams["bolt"].size() == 5, "bolt has five variants")
		check(Sfx.streams["glob"] is AudioStreamWAV, "a sound without a clip keeps its synthesised version")
	var w: World = m.world
	w.fog.enabled = false
	var c := Vector2(72, 84)
	var at := w.spawn_building("ambron_arc_tower", 0, Vector2i(int(c.x) - 5, int(c.y) - 1), true)
	w.spawn_building("ambron_relay", 0, Vector2i(int(c.x) - 8, int(c.y) + 2), true)
	var vs := w.spawn_building("void_slime_spire", 1, Vector2i(int(c.x) + 4, int(c.y) - 1), true)
	check(at.weapon.size() > 0 and vs.weapon.size() > 0, "both towers are armed")
	var hp0: float = vs.hp
	var hpa: float = at.hp
	for i in 5:
		w.spawn_unit("ambron_lancer", 0, c + Vector2(-3, -3 + i * 1.4))
		w.spawn_unit("void_spitter", 1, c + Vector2(2, -3 + i * 1.4))
	for i in 2:
		w.spawn_unit("void_spinefiend", 1, c + Vector2(4.5, -1 + i * 2.5))
		w.spawn_unit("void_mauler", 1, c + Vector2(3, -2 + i * 3.0))
		w.spawn_unit("ambron_bulwark", 0, c + Vector2(-2, -2 + i * 3.0))
	w.spawn_unit("void_acidback", 1, c + Vector2(3.5, 3.5))
	w.fog.update()
	m.rig.look_at_ground(c)
	m.rig.dist = 15.0
	w.running = true
	var shots_taken := 0
	for k in 70:
		await frames(1)
		if k in [25, 40, 55, 69]:
			await shot("60_fx_%d" % shots_taken)
			shots_taken += 1
	ff(4.0)
	check(vs.hp < hp0 or vs.dead or at.hp < hpa or at.dead, "towers take part in the fight")
	var tower_hit := false
	for u in w.units:
		if u.hp < u.max_hp:
			tower_hit = true
	check(tower_hit, "units take damage in the tower fight")


func _full() -> void:
	# both sides played by bots, rendered, at high speed, to the end
	if m:
		m.queue_free()
		await frames(2)
	m = Match.new()
	main.add_child(m)
	m.start({"races": ["ambron", "void"], "ai": [true, true], "difficulty": "normal", "human": 0})
	await frames(5)
	var w: World = m.world
	var shots_taken := 0
	var t0 := Time.get_ticks_msec()
	while not w.over and w.time < 40.0 * 60.0:
		for i in 40:
			w.step(0.1)
			if w.over:
				break
		w._sync_visuals(0.016)
		if int(w.time) / 240 > shots_taken:
			shots_taken += 1
			var army: Array = []
			for u in w.units:
				if not u.is_worker:
					army.append(u)
			if army.size() > 0:
				m.rig.look_at_ground(army[randi() % army.size()].p)
			await shot("40_full_%02d" % shots_taken)
		await frames(1)
	check(w.over, "a full game ends with a winner (P%d at %s, %.0f s real)" % [w.winner + 1, UiKit.fmt_time(w.time), (Time.get_ticks_msec() - t0) / 1000.0])
	await frames(10)
	await shot("41_end_screen")

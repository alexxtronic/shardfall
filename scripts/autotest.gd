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
	m.start({"races": races, "ai": [false, ai], "difficulty": "normal", "human": 0, "map": map_id, "intro": false})
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
	if want("profile"):
		await _profile()
	if want("seats"):
		await _seats()
	if want("tutorial"):
		await _tutorial()
	if only == "previews":
		await _previews()
		await _brand()
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


## Bakes the title screen's map previews (assets/ui/maps/<id>.png): each map seen straight
## down, no fog, no HUD. Only runs when asked for by name (--only=previews).
func _previews() -> void:
	var dir := ProjectSettings.globalize_path("res://assets/ui/maps")
	DirAccess.make_dir_recursive_absolute(dir)
	for id in Maps.LIST:
		await start(["ambron", "void"], false, id)
		var mw: World = m.world
		mw.fog.enabled = false
		mw.fog.update()
		m.hud.visible = false
		var wn := m.get_node_or_null("Weather")
		if wn:
			wn.visible = false
		m.sun.directional_shadow_max_distance = 400.0
		m.rig.set_process(false)
		var cam: Camera3D = m.rig.cam
		cam.projection = Camera3D.PROJECTION_ORTHOGONAL
		cam.size = 146.0
		var n := float(mw.grid.size)
		cam.position = Vector3(n * 0.5, 120.0, n * 0.5)
		cam.look_at(Vector3(n * 0.5, 0.0, n * 0.5), Vector3(0, 0, -1))
		cam.far = 400.0
		mw._sync_visuals(0.016)
		await frames(6)
		var img := get_viewport().get_texture().get_image()
		var hgt := img.get_height()
		var crop := img.get_region(Rect2i((img.get_width() - hgt) / 2, 0, hgt, hgt))
		crop.resize(384, 384, Image.INTERPOLATE_LANCZOS)
		crop.save_png("%s/%s.png" % [dir, id])
		check(FileAccess.file_exists("%s/%s.png" % [dir, id]), "%s: preview baked" % id)
		m.rig.set_process(true)


## Bakes the app icon (icon.png, 1024 px) and boot splash (assets/ui/splash.png): a cluster
## of the game's golden crystals lit against a violet glow, and the logo under it.
func _brand() -> void:
	if m:
		m.queue_free()
		m = null
		await frames(2)
	var vp := SubViewport.new()
	vp.size = Vector2i(1024, 1024)
	vp.own_world_3d = true
	vp.msaa_3d = Viewport.MSAA_4X
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(vp)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.05, 0.03, 0.09)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.45, 0.35, 0.6)
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 0.95
	env.glow_enabled = true
	env.glow_intensity = 1.0
	env.glow_bloom = 0.15
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)
	# violet halo behind the crystals
	var halo := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(7.5, 7.5)
	var hm := StandardMaterial3D.new()
	hm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	hm.albedo_texture = Weather._dot()
	hm.albedo_color = Color(0.55, 0.3, 1.0, 0.85)
	hm.emission_enabled = true
	hm.emission = Color(0.5, 0.25, 0.95)
	hm.emission_energy_multiplier = 1.2
	q.material = hm
	halo.mesh = q
	halo.position = Vector3(0, 1.3, -2.5)
	vp.add_child(halo)
	var ps := Models.scene_for("crystal_a")
	var ps2 := Models.scene_for("crystal_c")
	for spec in [[ps, Vector3(0, 0, 0), 0.4, 2.9, 1.9], [ps2 if ps2 else ps, Vector3(-1.2, 0, 0.6), -0.6, 1.6, 1.3],
			[ps2 if ps2 else ps, Vector3(1.2, 0, 0.45), 2.2, 1.8, 1.3]]:
		if spec[0] == null:
			continue
		var c: Node3D = (spec[0] as PackedScene).instantiate()
		vp.add_child(c)
		Models.fit(c, float(spec[4]), float(spec[3]))
		c.position = spec[1]
		c.rotation.y = float(spec[2])
	var key := DirectionalLight3D.new()
	key.light_color = Color(1.0, 0.86, 0.6)
	key.light_energy = 1.5
	key.rotation_degrees = Vector3(-35, 35, 0)
	vp.add_child(key)
	var rim := DirectionalLight3D.new()
	rim.light_color = Color(0.6, 0.45, 1.0)
	rim.light_energy = 2.0
	rim.rotation_degrees = Vector3(-15, 200, 0)
	vp.add_child(rim)
	var cam := Camera3D.new()
	cam.fov = 32.0
	cam.position = Vector3(0, 2.3, 8.7)
	vp.add_child(cam)
	cam.look_at(Vector3(0, 1.1, 0), Vector3.UP)
	await frames(8)
	var icon := vp.get_texture().get_image()
	icon.convert(Image.FORMAT_RGBA8)
	icon.save_png(ProjectSettings.globalize_path("res://icon.png"))
	check(FileAccess.file_exists("res://icon.png"), "app icon baked")
	vp.queue_free()
	# splash: the icon over the logo, on black
	var sv := SubViewport.new()
	sv.size = Vector2i(1280, 720)
	sv.transparent_bg = false
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(sv)
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.015, 0.035)
	bg.size = Vector2(1280, 720)
	sv.add_child(bg)
	var tr := TextureRect.new()
	var soft: Image = icon.duplicate()
	soft.resize(512, 512, Image.INTERPOLATE_LANCZOS)
	for y in 512:
		for x in 512:
			var rr := Vector2(x - 255.5, y - 255.5).length() / 512.0
			var px: Color = soft.get_pixel(x, y)
			px.a = clampf((0.5 - rr) / 0.14, 0.0, 1.0)
			soft.set_pixel(x, y, px)
	tr.texture = ImageTexture.create_from_image(soft)
	tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tr.position = Vector2(640 - 170, 70)
	tr.size = Vector2(340, 340)
	sv.add_child(tr)
	var lg := UiKit.head("SHARDFALL", 84, UiKit.GOLD)
	lg.add_theme_constant_override("outline_size", 12)
	lg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lg.position = Vector2(0, 430)
	lg.size = Vector2(1280, 110)
	sv.add_child(lg)
	var tg := UiKit.label("Ambron  ·  versus  ·  the Void", 22, UiKit.DIM)
	tg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tg.position = Vector2(0, 545)
	tg.size = Vector2(1280, 40)
	sv.add_child(tg)
	await frames(6)
	var sp := sv.get_texture().get_image()
	sp.convert(Image.FORMAT_RGB8)
	sp.save_png(ProjectSettings.globalize_path("res://assets/ui/splash.png"))
	check(FileAccess.file_exists("res://assets/ui/splash.png"), "boot splash baked")
	sv.queue_free()


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
	m.rig.set_process(false)
	m.rig.cam.position = Vector3(40, 9, 84)
	m.rig.cam.look_at(Vector3(26, 1.5, 104), Vector3.UP)
	await shot("71_ramp_side")
	m.rig.set_process(true)
	# the camera picks the plateau top, not the ground plane under it
	var sp := m.rig.to_screen(Vector3(main_c.x + 4, Terrain.LEVEL_H, main_c.y - 8))
	var g := m.rig.screen_to_ground(sp)
	check(g.distance_to(main_c + Vector2(4, -8)) < 0.5, "tapping the plateau picks the plateau (%.2f m off)" % g.distance_to(main_c + Vector2(4, -8)))

## Neither seat starts ahead: the grid is an exact mirror, both sides' starting workers
## harvest the same amount on every map, and the march to the enemy main is the same.
func _seats() -> void:
	for id in Maps.LIST:
		for races in [["ambron", "ambron"], ["void", "ambron"]]:
			var w := World.new()
			add_child(w)
			w.setup({"map": id, "visuals": false, "human": -1, "races": races, "ai": [false, false]})
			if races[0] == "ambron":
				var odd := 0
				var n: int = w.grid.size
				for y in n:
					for x in n:
						if w.grid.kind_at(Vector2i(x, y)) != w.grid.kind_at(Vector2i(n - 1 - x, n - 1 - y)):
							odd += 1
				check(odd == 0, "%s: the walkable grid is an exact mirror (%d cells differ)" % [id, odd])
			for i in 3600:
				w.step(0.05)
			var a: int = w.players[0].gathered_m
			var b: int = w.players[1].gathered_m
			check(absi(a - b) <= maxi(a, b) * 0.06, "%s %s: both seats harvest alike in 3 min (%d vs %d)" % [id, races, a, b])
			if races[0] == "ambron":
				# the walk from each main's front door to the other main is the same
				var s0: Dictionary = w.sites[0]
				var s1: Dictionary = w.sites[1]
				var from0: Vector2 = s0["center"] - (s0["dir"] as Vector2) * 8.0
				var from1: Vector2 = s1["center"] - (s1["dir"] as Vector2) * 8.0
				var l0 := _path_len(w.grid.find_path(from0, s1["center"]))
				var l1 := _path_len(w.grid.find_path(from1, s0["center"]))
				# A* breaks equal-cost ties its own way, so allow a couple of percent
				check(absf(l0 - l1) <= maxf(l0, l1) * 0.02, "%s: the march to the enemy main is the same from both seats (%.1f vs %.1f m)" % [id, l0, l1])
			w.queue_free()
			await frames(1)


## The guided first match: each lesson waits for the player to do its thing, the bot waits
## until the last one, Skip hands over a normal game, and a tutorial never touches the
## leaderboard.
func _tutorial() -> void:
	m = null
	for c in main.get_children():
		if c is Match:
			c.queue_free()
	await frames(2)
	m = Match.new()
	main.add_child(m)
	m.start({"races": ["ambron", "void"], "ai": [false, true], "difficulty": "easy", "human": 0, "map": "shatterfield", "intro": false, "tutorial": true})
	main.match_node = m
	await frames(5)
	var w: World = m.world
	var tut: Tutorial = m.tutorial
	check(tut != null and tut.card != null and tut.step == 0, "the tutorial opens on its first lesson")
	check(w.ais.size() == 1 and w.ais[0].paused, "the bot waits during the lessons")
	await get_tree().create_timer(0.4).timeout   # the card fades in
	await shot("90_tutorial_look")
	var games0 := Profile.games()
	# 1. look around
	m.rig.focus += Vector2(14, 0)
	await _tut_wait(tut, 1)
	# 2. train a worker
	var main_b: Building = null
	for b in w.buildings:
		if b.owner_id == 0 and b.slot == "main":
			main_b = b
	w.queue_unit(main_b, Defs.unit_id("ambron", "worker"))
	await _tut_wait(tut, 2)
	# 3. supply, 4. barracks (inside the finished relay's field)
	var worker: Unit = null
	for u in w.units:
		if u.owner_id == 0 and u.is_worker:
			worker = u
			break
	w.players[0].minerals += 600
	var rid := Defs.building_id("ambron", "supply")
	var rc = w.suggest_spot(0, rid, main_b.p + Vector2(0, -8))
	w.command_build(worker, rid, rc)
	await _tut_wait(tut, 3)
	await get_tree().create_timer(0.4).timeout
	await shot("91_tutorial_production")
	for i in 600:
		w.step(0.1)
		if w.has_built(0, rid):
			break
	var bid := Defs.building_id("ambron", "barracks")
	var bc = w.suggest_spot(0, bid, Vector2(rc) + Vector2(1, 1))
	check(bc != null, "a barracks spot is found in the relay's field")
	if bc != null:
		w.command_build(worker, bid, bc)
	await _tut_wait(tut, 4)
	# 5. an army, 6. move out
	var army: Array = []
	for i in 4:
		army.append(w.spawn_unit(Defs.unit_id("ambron", "infantry"), 0, main_b.p + Vector2(4 + i, 6)))
	await _tut_wait(tut, 5)
	w.command_move(army, main_b.p + Vector2(20, -20), true)
	await _tut_wait(tut, 6)
	check(not w.ais[0].paused and w.players[1].minerals <= 300, "the last lesson wakes the bot without a hoard (%d crystals)" % w.players[1].minerals)
	await get_tree().create_timer(0.4).timeout
	await shot("92_tutorial_final")
	# a tutorial result stays off the leaderboard, and a win marks it done
	w.surrender(1)
	await get_tree().create_timer(0.9).timeout
	await shot("93_tutorial_complete")
	check(Profile.games() == games0, "a tutorial game stays off the leaderboard")
	check(bool(Prefs.get_v("tutorial_done")), "winning the tutorial marks it done")
	Prefs.data["tutorial_done"] = false
	# Skip: the card goes and the bot plays at once
	m.queue_free()
	await frames(2)
	m = Match.new()
	main.add_child(m)
	m.start({"races": ["void", "ambron"], "ai": [false, true], "difficulty": "easy", "human": 0, "map": "shatterfield", "intro": false, "tutorial": true})
	main.match_node = m
	await frames(5)
	check(String(m.tutorial.steps[1][1]).contains("Hive Heart"), "the lessons name the player's race's buildings")
	m.tutorial.skip()
	await frames(2)
	check(not is_instance_valid(m.tutorial.card) and not m.world.ais[0].paused, "Skip hands over a normal game")
	m.queue_free()
	m = null
	await frames(2)


func _tut_wait(tut: Tutorial, want_step: int) -> void:
	var t0 := Time.get_ticks_msec()
	while tut.step < want_step and Time.get_ticks_msec() - t0 < 4000:
		await frames(2)
	check(tut.step == want_step, "tutorial lesson %d is passed (now on %d: %s)" % [want_step, tut.step + 1, tut.steps[tut.step][0]])


func _path_len(path: PackedVector2Array) -> float:
	var l := 0.0
	for i in range(1, path.size()):
		l += path[i - 1].distance_to(path[i])
	return l


## The leaderboard: a game against the bot moves the rating, sets a best score and lands in
## the history; the results screen and the leaderboard panel show it.
func _profile() -> void:
	Profile.reset()
	check(Profile.rating() == 1000 and Profile.rank() > 1, "a new profile starts at 1000 (rank #%d)" % Profile.rank())
	check(Profile.elo_delta(1200.0, "normal", true, 0) == 20 and Profile.elo_delta(1200.0, "normal", false, 20) == -12,
		"Elo: an even game is worth +20 / -12 (K 40 new, 24 settled)")
	await start(["ambron", "void"], true, "frostspire")
	var w: World = m.world
	var me: PlayerState = w.players[0]
	me.value_killed = 2400.0
	me.gathered_m = 3100
	me.gathered_s = 650
	me.kills = 31
	w.time = 640.0
	w.surrender(1)
	await frames(5)
	var res: Dictionary = m.result
	check(int(res.get("delta", 0)) > 0 and Profile.rating() > 1000, "beating the normal bot raises the rating (%+d)" % int(res.get("delta", 0)))
	check(Profile.best("frostspire") == int(res.get("score", -1)) and res.get("new_best", false), "the score is the map's best (%d)" % Profile.best("frostspire"))
	check(Profile.history().size() == 1 and Profile.history()[0]["won"], "the game is in the history")
	check(m.end_layer != null, "the results screen shows")
	check(not m.hud.visible, "the HUD steps aside for the results")
	await get_tree().create_timer(0.9).timeout   # the panel fades in
	await shot("80_results")
	var lb := LeaderboardPanel.new()
	m.end_layer.add_child(lb)
	await frames(2)
	await shot("81_leaderboard")
	lb._show("history", false)
	await shot("82_history")
	lb._show("best", false)
	await shot("83_best")
	lb.queue_free()
	var r1 := Profile.rating()
	Profile.submit("shatterfield", "ambron", "void", "hard", false, me, 300.0)
	check(Profile.rating() < r1 and Profile.best("shatterfield") > 0, "a loss lowers the rating but still scores")
	Profile.set_player_name("   A really very long commander name   ")
	check(Profile.player_name().length() <= Profile.NAME_MAX and not Profile.player_name().begins_with(" "), "names are trimmed (%s)" % Profile.player_name())
	Profile.reset()


func _title() -> void:
	main.show_title()
	await frames(5)
	check(main.title != null and main.title.get_child_count() > 0, "title screen builds")
	await shot("00_title")
	main.title.help.visible = true
	await shot("00_title_help")
	main.title.help.visible = false
	var tt: Title = main.title
	check(tt.map_btns.size() == Maps.LIST.size(), "title shows a card per map")
	tt._set_map("ember_rift")
	check(tt.backdrop.texture != null and tt.map_id == "ember_rift", "picking a map swaps the backdrop")
	var got := {}
	tt.play.disconnect(main.start_match)
	tt.play.connect(func(c): got["cfg"] = c)
	tt._go()
	check(String(got.get("cfg", {}).get("map", "")) == "ember_rift", "PLAY passes the chosen map")
	await shot("00_title_ember")
	tt._open_settings()
	await frames(2)
	check(tt.root.get_node_or_null("Settings") != null, "settings panel opens")
	await shot("00_title_settings")
	tt.root.get_node("Settings").queue_free()
	var cp := CreditsPanel.new()
	cp.name = "Credits"
	tt.root.add_child(cp)
	await shot("00_title_credits")
	cp.queue_free()
	tt._set_map("shatterfield", false)
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
	var sp := rig.to_screen(Vector3(u.p.x, u.height * 0.45 + u.ground_h(), u.p.y))
	await _tap(sp)
	check(cmd.selection.size() == 1 and cmd.selection[0] is Unit and cmd.selection[0].owner_id == 0, "tap selects a unit")
	# tap ground moves it
	# an open bit of ground near it, clear of buildings, units and the HUD
	var g := u.p
	for i in 80:
		var q := u.p + Vector2(cos(i * 0.9), sin(i * 0.9)) * (4.0 + i * 0.15)
		var qs := rig.to_screen(Vector3(q.x, w.height_at(q), q.y))
		if w.grid.kind_at(Vector2i(q)) == 0 and w.units_near(q, 3.0).is_empty() and not w._near_resources(Vector2i(q), 1, 2.5) and not m.hud.blocks(qs) and Rect2(80, 80, 1120, 400).has_point(qs):
			g = q
			break
	await _tap(rig.to_screen(Vector3(g.x, w.height_at(g), g.y)))
	var sel_u: Unit = u
	check(sel_u.order == Unit.O.MOVE and sel_u.goal.distance_to(g) < 2.5, "tap on ground moves the selected worker")
	# send it back to work by tapping a crystal
	var cr = w.nearest_resource(0, sel_u.p, "mineral")
	await _tap(rig.to_screen(Vector3(cr.p.x, 0.8 + w.height_at(cr.p), cr.p.y)))
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
	# long-press + drag box select, with the camera centred on the workers
	var mid := Vector2.ZERO
	var nw := 0
	for x in w.units:
		if x.owner_id == 0 and x.is_worker and not x.hidden_inside:
			mid += x.p
			nw += 1
	rig.look_at_ground(mid / maxi(1, nw))
	await frames(2)
	await _box(Vector2(260, 150), Vector2(1020, 520))
	check(cmd.selection.size() >= 3, "hold and drag box-selects (%d)" % cmd.selection.size())
	await shot("04_box_selected")
	# double tap selects all of a type
	cmd.set_selection([])
	var u2: Unit = _clear_worker()
	var sp2 := rig.to_screen(Vector3(u2.p.x, u2.height * 0.45 + u2.ground_h(), u2.p.y))
	await _tap(sp2)
	await _tap(rig.to_screen(Vector3(u2.p.x, u2.height * 0.45 + u2.ground_h(), u2.p.y)))
	check(cmd.selection.size() >= 5, "double-tap selects all of that type on screen (%d)" % cmd.selection.size())
	cmd.action("gather")
	cmd.set_selection([])


## A worker that is on screen and not under a HUD panel.
func _clear_worker() -> Unit:
	for x in m.world.units:
		if x.owner_id == 0 and x.is_worker and not x.hidden_inside and m.rig.sees(x.p):
			var sp: Vector2 = m.rig.to_screen(Vector3(x.p.x, x.height * 0.45 + x.ground_h(), x.p.y))
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
	await _tap(m.rig.to_screen(Vector3(spot.x + 3, w.height_at(spot + Vector2(3, -7)), spot.y - 7)))
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
		var names := Sfx.streams.keys()
		var rec := 0
		var synth: Array = []
		for n in names:
			var s = Sfx.streams[n]
			if s is Array and s[0] is AudioStreamOggVorbis and not (s[0] as AudioStreamOggVorbis).loop:
				rec += 1
			else:
				synth.append(n)
		synth.sort()
		check(synth == ["alert", "lose", "win"], "every effect but the alarm has recorded clips, unlooped (synth: %s)" % [synth])
		check(Sfx.streams["bolt"].size() == 5, "bolt has five variants")
		check(Sfx.streams["alert"] is AudioStreamWAV, "a sound without a clip keeps its synthesised version")
		var th: Dictionary = m.world.theme
		check(Sfx.calm.playing and Sfx.calm_name == th["music"], "the map's music plays (%s)" % Sfx.calm_name)
		check(Sfx.amb.playing and (Sfx.amb.stream as AudioStreamOggVorbis).loop, "the map's ambience loops")
		Sfx.combat()
		await frames(2)
		check(Sfx.battle.playing and Sfx.battle_name == th["battle"], "fighting brings in the battle track")
		var missing: Array = []
		for kind in ["female", "male"]:
			for line in ["look_out", "target_destroyed", "objective_achieved", "mission_completed", "mission_failed", "new_highscore"]:
				if not ResourceLoader.exists("%s%s/%s.ogg" % [Sfx.VOICE_DIR, kind, line]):
					missing.append(kind + "/" + line)
		for id in ["menu", "win", "lose", "battle_a", "battle_ember"]:
			if not ResourceLoader.exists(Sfx.MUSIC_DIR + id + ".ogg"):
				missing.append(id)
		for id in Maps.LIST:
			var t: Dictionary = Maps.theme_of(id)
			for f in [Sfx.MUSIC_DIR + String(t["music"]), Sfx.AMB_DIR + String(t["ambience"])]:
				if not ResourceLoader.exists(f + ".ogg"):
					missing.append(f)
		check(missing.is_empty(), "every music track, ambience and voice line exists (%s missing)" % [missing])
		Sfx.announce("look_out")
		check(Sfx.announcer.playing, "the announcer speaks")
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
	await get_tree().create_timer(0.9).timeout
	await shot("41_end_screen")

class_name Match
extends Node3D
## One game: the lit world, the camera, touch control, the HUD and the end
## screen. Emits finished("restart" | "quit").

signal finished(action: String)

var cfg: Dictionary
var world: World
var rig: CameraRig
var cmd: Commander
var hud: Hud
var end_layer: CanvasLayer
var sun: DirectionalLight3D
var result: Dictionary = {}     # the leaderboard result of this game, once it's over


func start(c: Dictionary) -> void:
	cfg = c
	name = "Match"
	_environment(Maps.theme_of(String(c.get("map", "standard"))))
	world = World.new()
	world.name = "World"
	add_child(world)
	world.setup(c)
	rig = CameraRig.new()
	rig.name = "Camera"
	rig.map_size = world.grid.size
	rig.ground = world.height_at
	rig.max_h = float(world.terrain.max_level) * Terrain.LEVEL_H
	add_child(rig)
	var s: Dictionary = world.sites[world.players[0].start_site]
	var center: Vector2 = s["center"]
	rig.focus = center - (s["dir"] as Vector2).normalized() * 3.0
	rig.dist = 30.0
	rig.focus_h = world.height_at(rig.focus)
	world.cam = rig
	Sfx.set_voice_for(String(world.players[0].race))
	Sfx.music(String(world.theme.get("music", "")), String(world.theme.get("battle", "")))
	Sfx.ambience(String(world.theme.get("ambience", "")))
	var weather := Weather.new()
	add_child(weather)
	weather.setup(rig, String(world.theme.get("weather", "")))
	cmd = Commander.new()
	cmd.name = "Commander"
	cmd.world = world
	cmd.rig = rig
	cmd.pid = 0
	add_child(cmd)
	hud = Hud.new()
	hud.name = "Hud"
	add_child(hud)
	hud.setup(world, cmd, rig)
	cmd.hud = hud
	hud.menu_action.connect(_on_menu)
	world.game_over.connect(_on_over)
	if bool(c.get("intro", true)):
		_intro()
	var race: String = world.players[0].race
	var main_name: String = Defs.buildings[Defs.building_id(race, "main")]["name"]
	hud.show_message("Your workers are harvesting. Tap your %s to train more." % main_name, "hint")


## Fade in from black with the map's name, then get out of the way.
func _intro() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 30
	layer.name = "Intro"
	add_child(layer)
	var black := ColorRect.new()
	black.color = Color.BLACK
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(black)
	var d: Dictionary = Maps.get_def(world.map_id)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_CENTER_TOP)
	v.offset_left = -500
	v.offset_right = 500
	v.offset_top = 150
	v.offset_bottom = 300
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.modulate = Color(1, 1, 1, 0)
	v.theme = UiKit.make_theme()
	layer.add_child(v)
	var nm := UiKit.head(String(d.get("name", "")).to_upper(), 46, d.get("accent", UiKit.GOLD))
	nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	nm.add_theme_constant_override("outline_size", 10)
	v.add_child(nm)
	var bot: PlayerState = world.players[1]
	var line := UiKit.label("%s  ·  vs %s, %s bot" % [String(d.get("tag", "")), Defs.RACE_INFO[bot.race]["name"],
		String(cfg.get("difficulty", "normal")).capitalize()], 19, UiKit.TEXT)
	line.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(line)
	var tw := create_tween()
	tw.tween_property(black, "color:a", 0.0, 1.1).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(v, "modulate:a", 1.0, 0.6).set_delay(0.3)
	tw.tween_callback(func(): Sfx.announce("go"))
	tw.tween_interval(1.8)
	tw.tween_property(v, "modulate:a", 0.0, 0.8)
	tw.tween_callback(layer.queue_free)


func _environment(th: Dictionary) -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = th["sky_top"]
	sm.sky_horizon_color = th["sky_horizon"]
	sm.ground_bottom_color = th["ground_bottom"]
	sm.ground_horizon_color = th["ground_horizon"]
	sm.sun_angle_max = 20.0
	sky.sky_material = sm
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = float(th["ambient"])
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = float(th["exposure"])
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 1.1
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	env.adjustment_contrast = 1.05
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.light_color = th["sun"]
	sun.light_energy = float(th["sun_energy"])
	sun.rotation_degrees = th["sun_rot"]
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.shadow_blur = 1.2
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.light_color = th["fill"]
	fill.light_energy = float(th["fill_energy"])
	fill.rotation_degrees = Vector3(-35, 140, 0)
	add_child(fill)


func _on_menu(a: String) -> void:
	match a:
		"surrender":
			world.surrender(0)
		"restart":
			finished.emit("restart")
		"quit":
			finished.emit("quit")


func _on_over(winner: int) -> void:
	var won := winner == 0
	Sfx.sting("win" if won else "lose")
	cmd.set_selection([])
	var me: PlayerState = world.players[0]
	var bot: PlayerState = world.players[1]
	# a game against the bot counts for the leaderboard
	var res: Dictionary = {}
	var ai: Array = cfg.get("ai", [false, true])
	if int(cfg.get("human", 0)) == 0 and ai.size() > 1 and bool(ai[1]) and not bool(ai[0]):
		res = Profile.submit(world.map_id, me.race, bot.race, String(cfg.get("difficulty", "normal")), won, me, world.time)
	result = res
	get_tree().create_timer(1.4).timeout.connect(func():
		Sfx.announce("mission_completed" if won else "mission_failed"))
	if res.get("new_best", false) and int(res.get("best_before", 0)) > 0:
		get_tree().create_timer(3.4).timeout.connect(func(): Sfx.announce("new_highscore"))
	end_layer = CanvasLayer.new()
	end_layer.layer = 20
	add_child(end_layer)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.62)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.theme = UiKit.make_theme()
	end_layer.add_child(dim)
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -330
	p.offset_right = 330
	p.offset_top = -300 if not res.is_empty() else -230
	p.offset_bottom = 300 if not res.is_empty() else 230
	dim.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	p.add_child(v)
	var t := UiKit.head("VICTORY" if won else "DEFEAT", 54, UiKit.GOLD if won else UiKit.BAD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var sub := UiKit.label("%s  ·  %s bot  ·  %s" % [String(Maps.get_def(world.map_id).get("name", "")),
		String(cfg.get("difficulty", "normal")).capitalize(), UiKit.fmt_time(world.time)], 16, UiKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	if not res.is_empty():
		v.add_child(_results(res))
	var g := GridContainer.new()
	g.columns = 3
	g.add_theme_constant_override("h_separation", 40)
	g.add_theme_constant_override("v_separation", 2)
	g.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(g)
	var rows := [
		["", "You (%s)" % Defs.RACE_INFO[me.race]["name"], "Bot (%s)" % Defs.RACE_INFO[bot.race]["name"]],
		["Crystals gathered", str(me.gathered_m), str(bot.gathered_m)],
		["Slime gathered", str(me.gathered_s), str(bot.gathered_s)],
		["Units made", str(me.units_made), str(bot.units_made)],
		["Units lost", str(me.units_lost), str(bot.units_lost)],
		["Kills", str(me.kills), str(bot.kills)],
		["Value destroyed", str(int(me.value_killed)), str(int(bot.value_killed))],
	]
	for r in rows:
		for i in 3:
			var l := UiKit.label(r[i], 17, UiKit.DIM if i == 0 else UiKit.TEXT)
			g.add_child(l)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 16)
	v.add_child(h)
	for spec in [["Play again", "restart"], ["Leaderboard", "board"], ["Title", "quit"]]:
		var b := Button.new()
		b.text = spec[0]
		b.custom_minimum_size = Vector2(190, 60)
		b.focus_mode = Control.FOCUS_NONE
		var a: String = spec[1]
		if a == "board":
			b.pressed.connect(func(): Sfx.play("open"); dim.add_child(LeaderboardPanel.new()))
		else:
			b.pressed.connect(func(): finished.emit(a))
		h.add_child(b)


## The leaderboard part of the end screen: score (and a new best), rating change, rank.
func _results(res: Dictionary) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 2)
	var s := HBoxContainer.new()
	s.alignment = BoxContainer.ALIGNMENT_CENTER
	s.add_theme_constant_override("separation", 14)
	box.add_child(s)
	s.add_child(UiKit.label("Score", 20, UiKit.DIM))
	s.add_child(UiKit.head(UiKit.fmt_int(int(res["score"])), 32, UiKit.GOLD))
	if res["new_best"]:
		s.add_child(UiKit.head("NEW BEST", 18, UiKit.GOOD))
	var d := int(res["delta"])
	var tr: Array = res["tier"]
	var r := HBoxContainer.new()
	r.alignment = BoxContainer.ALIGNMENT_CENTER
	r.add_theme_constant_override("separation", 12)
	box.add_child(r)
	r.add_child(UiKit.label("Rating %d" % int(res["rating"]), 19, UiKit.TEXT))
	r.add_child(UiKit.head("%+d" % d, 19, UiKit.GOOD if d >= 0 else UiKit.BAD))
	r.add_child(UiKit.label("·", 19, UiKit.DIM))
	r.add_child(UiKit.label(String(tr[0]), 19, tr[1]))
	if String(tr[0]) != String((res["tier_before"] as Array)[0]):
		r.add_child(UiKit.head("PROMOTED" if d > 0 else "DEMOTED", 16, UiKit.GOOD if d > 0 else UiKit.BAD))
	r.add_child(UiKit.label("·", 19, UiKit.DIM))
	var rk := "Rank #%d" % int(res["rank"])
	if int(res["rank"]) != int(res["rank_before"]):
		rk += "  (was #%d)" % int(res["rank_before"])
	r.add_child(UiKit.label(rk, 19, UiKit.TEXT))
	return box

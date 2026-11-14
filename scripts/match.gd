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
	var race: String = world.players[0].race
	var main_name: String = Defs.buildings[Defs.building_id(race, "main")]["name"]
	hud.show_message("Your workers are harvesting. Tap your %s to train more." % main_name, "hint")


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
	Sfx.play("win" if won else "lose")
	cmd.set_selection([])
	end_layer = CanvasLayer.new()
	end_layer.layer = 20
	add_child(end_layer)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.theme = UiKit.make_theme()
	end_layer.add_child(dim)
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -300
	p.offset_right = 300
	p.offset_top = -230
	p.offset_bottom = 230
	dim.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	var t := UiKit.head("VICTORY" if won else "DEFEAT", 54, UiKit.GOLD if won else UiKit.BAD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var me: PlayerState = world.players[0]
	var bot: PlayerState = world.players[1]
	var g := GridContainer.new()
	g.columns = 3
	g.add_theme_constant_override("h_separation", 40)
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
			var l := UiKit.label(r[i], 18, UiKit.DIM if i == 0 else UiKit.TEXT)
			g.add_child(l)
	var tl := UiKit.label("Game time %s" % UiKit.fmt_time(world.time), 16, UiKit.DIM)
	tl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(tl)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 20)
	v.add_child(h)
	for spec in [["Play again", "restart"], ["Title", "quit"]]:
		var b := Button.new()
		b.text = spec[0]
		b.custom_minimum_size = Vector2(200, 60)
		b.focus_mode = Control.FOCUS_NONE
		var a: String = spec[1]
		b.pressed.connect(func(): finished.emit(a))
		h.add_child(b)

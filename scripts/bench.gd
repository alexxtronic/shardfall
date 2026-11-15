class_name Bench
extends Node
## On-device performance check: what makes the phone hot.
##
## Start it from Settings > Performance check on the title screen (it uses the current graphics
## level and ends on a Done screen), or launch with the environment variable
## SHARDFALL_BENCH=<graphics level 0-3> (with devicectl: DEVICECTL_CHILD_SHARDFALL_BENCH=0), or
## `-- --bench=<level>` on a desktop. It plays a
## bot-vs-bot match on Shatterfield, fast-forwards to mid-game, then times frames with one
## suspect switched off at a time and writes BENCH lines to the error stream and to
## user://bench.txt (on an iPhone: `xcrun devicectl device copy from --domain-type
## appDataContainer --domain-identifier com.alexdamore.shardfall --source Documents/bench.txt`).
## Settings and the profile are never written, and the sound is muted.
##
##   xcrun devicectl device process launch --console --terminate-existing --device <udid> \
##     com.alexdamore.shardfall      (with DEVICECTL_CHILD_SHARDFALL_BENCH=0 in the environment)

const SETTLE := 1.5
const MEASURE := 5.0
const LOG := "user://bench.txt"

var main
var level: int = 1
var in_app: bool = false          # started from Settings: keep the level, end on a Done screen
var banner: Label
var keep: Array = [true, true]
var m: Match
var w: World
var rid: RID
var ground: MeshInstance3D
var ground_mat: Material
var flat: StandardMaterial3D
var parts: Array = []


## The graphics level asked for, or -9 when this isn't a bench run.
static func requested() -> int:
	var env := OS.get_environment("SHARDFALL_BENCH")
	if env != "":
		return int(env)
	for a in OS.get_cmdline_args() + OS.get_cmdline_user_args():
		if a.begins_with("--bench"):
			return int(a.get_slice("=", 1)) if "=" in a else 1
	return -9


func _ready() -> void:
	var f := FileAccess.open(LOG, FileAccess.WRITE)
	if f:
		f.close()
	_run.call_deferred()


## Results go to the error stream (unbuffered, so a console sees them at once) and to a file
## that `devicectl device copy from` can fetch.
func _out(line: String) -> void:
	printerr(line)
	var f := FileAccess.open(LOG, FileAccess.READ_WRITE)
	if f:
		f.seek_end()
		f.store_line(line)
		f.close()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_out("BENCH interrupted: the app lost focus (%d); timings after this are not valid" % what)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _run() -> void:
	if in_app:
		# nothing from this run may reach the saved settings or the leaderboard
		keep = [Prefs.persist, Profile.persist]
		Prefs.persist = false
		Profile.persist = false
		level = Graphics.level()
		AudioServer.set_bus_mute(0, true)
	else:
		Prefs.set_v("graphics", level)
	m = Match.new()
	main.add_child(m)
	main.match_node = m
	m.start({"races": ["ambron", "void"], "ai": [true, true], "difficulty": "hard", "human": 0,
		"map": "shatterfield", "intro": false})
	await _frames(5)
	w = m.world
	var vp := get_viewport()
	var layer := CanvasLayer.new()
	layer.layer = 60
	add_child(layer)
	banner = UiKit.label("Performance check: please leave the phone alone for about two minutes", 20, UiKit.GOLD)
	banner.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	banner.position.y = 70
	banner.grow_horizontal = Control.GROW_DIRECTION_BOTH
	banner.add_theme_constant_override("outline_size", 6)
	layer.add_child(banner)
	_out("BENCH start level %d (%s), window %s, 3D scale %.2f, msaa %d, fps cap %d, %s" % [level,
		Graphics.LEVELS[Graphics.level()]["name"], str(DisplayServer.window_get_size()), vp.scaling_3d_scale,
		vp.msaa_3d, Engine.max_fps, OS.get_model_name()])
	# mid-game, armies on the field
	var t0 := Time.get_ticks_msec()
	while w.time < 300.0 and not w.over:
		for i in 25:
			w.step(0.1)
		await _frames(1)
	w._sync_visuals(0.016)
	_out("BENCH fast-forward %.0f s of game in %.1f s: %d units, %d buildings" % [w.time,
		(Time.get_ticks_msec() - t0) / 1000.0, w.units.size(), w.buildings.size()])
	_look()
	rid = vp.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(rid, true)
	await _wait(2.0)
	ground = w.find_child("Ground", true, false) as MeshInstance3D
	ground_mat = ground.material_override if ground else null
	flat = StandardMaterial3D.new()
	flat.albedo_color = Color(0.35, 0.32, 0.36)
	parts = m.find_children("*", "GPUParticles3D", true, false)
	await _phase("as shipped", _nop, _nop)
	# every other phase runs without the frame cap, so the frame rate shows what each part costs
	Engine.max_fps = 0
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await _phase("no fps cap", _nop, _nop)
	# and with the battle frozen, so the picture is the same in each
	w.running = false
	await _phase("sim paused", _nop, _nop)
	await _phase("no units drawn", _entities.bind(false), _entities.bind(true))
	if ground:
		await _phase("plain ground", _plain_ground.bind(true), _plain_ground.bind(false))
		await _phase("ground no shadow", _ground_shadow.bind(false), _ground_shadow.bind(true))
	await _phase("no shadows", _shadows.bind(false), _shadows.bind(true))
	if w.fog:
		await _phase("no fog", _fog.bind(false), _fog.bind(true))
	await _phase("no particles", _particles.bind(false), _particles.bind(true))
	await _phase("no 2D redraw", _ui.bind(false), _ui.bind(true))
	await _phase("no glow", _glow.bind(false), _glow.bind(bool(Graphics.setting("glow"))))
	await _phase("all cheap", _cheap.bind(true), _cheap.bind(false))
	_out("BENCH DONE")
	if not in_app:
		get_tree().quit()
		return
	w.running = true
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
	Graphics.apply(vp)
	Prefs.persist = keep[0]
	Profile.persist = keep[1]
	AudioServer.set_bus_mute(0, false)
	Prefs.apply()
	banner.text = "Performance check done. Thank you!"
	var back := Button.new()
	back.text = "Back"
	back.name = "Back"
	back.theme = UiKit.make_theme()
	back.custom_minimum_size = Vector2(220, 70)
	back.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	back.grow_horizontal = Control.GROW_DIRECTION_BOTH
	back.grow_vertical = Control.GROW_DIRECTION_BOTH
	back.pressed.connect(func() -> void:
		main.show_title()
		queue_free())
	banner.get_parent().add_child(back)


func _nop() -> void:
	pass


func _entities(on: bool) -> void:
	for e in w.units + w.buildings + w.resources:
		if is_instance_valid(e):
			e.visible = on


func _plain_ground(on: bool) -> void:
	ground.material_override = flat if on else ground_mat


func _ground_shadow(on: bool) -> void:
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if on else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _shadows(on: bool) -> void:
	m.sun.shadow_enabled = on


func _glow(on: bool) -> void:
	if is_instance_valid(m.world_env):
		m.world_env.environment.glow_enabled = on


func _fog(on: bool) -> void:
	w.fog.plane.visible = on


func _particles(on: bool) -> void:
	for p in parts:
		if is_instance_valid(p):
			p.visible = on


func _ui(on: bool) -> void:
	for n in [m.hud.overlay, m.hud.minimap, m.hud]:
		n.set_process(on)
	m.hud.overlay.visible = on


func _cheap(on: bool) -> void:
	if ground:
		_plain_ground(on)
	_shadows(not on)
	if w.fog:
		_fog(not on)
	_particles(not on)


## Look at the busiest part of the field: the middle of player 1's units.
func _look() -> void:
	var c := Vector2.ZERO
	var n := 0
	for u in w.units:
		if u.owner_id == 0 and not u.dead:
			c += u.p
			n += 1
	if n > 0:
		m.rig.look_at_ground(c / n)


func _phase(name: String, on: Callable, off: Callable) -> void:
	on.call()
	await _wait(SETTLE)
	var frames := 0
	var gpu := 0.0
	var rcpu := 0.0
	var draws := 0.0
	var prims := 0.0
	w.prof_step_us = 0
	w.prof_sync_us = 0
	var start := Time.get_ticks_usec()
	while Time.get_ticks_usec() - start < int(MEASURE * 1e6):
		await get_tree().process_frame
		frames += 1
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(rid)
		rcpu += RenderingServer.viewport_get_measured_render_time_cpu(rid) + RenderingServer.get_frame_setup_time_cpu()
		draws += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		prims += Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
	var secs := (Time.get_ticks_usec() - start) / 1e6
	var f := maxf(frames, 1)
	_out("BENCH %-17s fps %5.1f = %5.2f ms a frame | sim %5.2f ms, sync %4.2f ms | gpu %5.2f ms | render cpu %5.2f ms | %4d draws %5dk tris" % [
		name, frames / secs, 1000.0 * secs / f, w.prof_step_us / 1000.0 / f, w.prof_sync_us / 1000.0 / f,
		gpu / f, rcpu / f, int(draws / f), int(prims / f / 1000.0)])
	off.call()
	await _wait(0.5)

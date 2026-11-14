class_name Overlay
extends Control
## Drawn over the 3D view: health bars, construction and training progress,
## the box-select rectangle and rally lines.

var world: World
var rig: CameraRig
var cmd: Commander


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func _process(_d: float) -> void:
	queue_redraw()


func _bar(center: Vector2, w: float, frac: float, col: Color, back: Color = Color(0, 0, 0, 0.7)) -> void:
	var r := Rect2(center - Vector2(w * 0.5, 3), Vector2(w, 6))
	draw_rect(r.grow(1), back)
	draw_rect(Rect2(r.position, Vector2(w * clampf(frac, 0.0, 1.0), 6)), col)


func _hp_col(f: float, own: bool) -> Color:
	if not own:
		return Color(1, 0.3, 0.25).lerp(Color(1.0, 0.55, 0.3), f)
	if f > 0.6:
		return Color(0.35, 1.0, 0.45)
	if f > 0.3:
		return Color(1.0, 0.85, 0.25)
	return Color(1.0, 0.3, 0.25)


## A red lightning bolt in a ring: this building has lost its power.
func _unpowered(c: Vector2) -> void:
	var blink := 0.6 + 0.4 * sin(Time.get_ticks_msec() * 0.008)
	draw_circle(c, 15.0, Color(0.1, 0.02, 0.02, 0.8))
	draw_arc(c, 15.0, 0.0, TAU, 32, Color(1.0, 0.3, 0.25, blink), 2.5, true)
	var bolt := PackedVector2Array([c + Vector2(3, -10), c + Vector2(-6, 2), c + Vector2(-0.5, 2), c + Vector2(-3, 10), c + Vector2(6, -2), c + Vector2(0.5, -2)])
	draw_colored_polygon(bolt, Color(1.0, 0.4, 0.3, blink))


func _draw() -> void:
	if world == null or rig == null:
		return
	var vr := get_viewport_rect()
	var mpp := rig.m_per_px()
	for u in world.units:
		if u.dead or not u.shown or u.hidden_inside:
			continue
		if not u.selected and u.hp >= u.max_hp:
			continue
		var top := Vector3(u.p.x, u.fly + float(u.def.get("model_h", 1.0)) + 0.3 + u.ground_h(), u.p.y)
		if not rig.in_front(top):
			continue
		var sp := rig.to_screen(top)
		if not vr.has_point(sp):
			continue
		var w := clampf(u.radius * 2.0 / mpp, 22.0, 70.0)
		var f: float = u.hp / u.max_hp
		_bar(sp, w, f, _hp_col(f, u.owner_id == cmd.pid))
	for b in world.buildings:
		if b.dead or not b.shown:
			continue
		var show_hp: bool = b.selected or b.hp < b.max_hp - 0.5
		var show_prog: bool = (not b.built) or (b.queue.size() > 0 and b.owner_id == cmd.pid)
		var unpowered: bool = b.built and b.needs_power and b.owner_id == cmd.pid and not world.is_powered(b)
		if not show_hp and not show_prog and not unpowered:
			continue
		var top := Vector3(b.p.x, float(b.def.get("model_h", 3.0)) + 0.6 + b.ground_h(), b.p.y)
		if not rig.in_front(top):
			continue
		var sp := rig.to_screen(top)
		if not vr.has_point(sp):
			continue
		var w := clampf(b.size * 1.1 / mpp, 40.0, 140.0)
		var f: float = b.hp / b.max_hp
		if show_hp:
			_bar(sp, w, f, _hp_col(f, b.owner_id == cmd.pid))
		if b.built and b.needs_power and b.owner_id == cmd.pid and not world.is_powered(b):
			_unpowered(sp + Vector2(0, -22))
		if not b.built:
			_bar(sp + Vector2(0, 9), w, b.progress, Color(0.4, 0.85, 1.0))
		elif b.queue.size() > 0 and b.owner_id == cmd.pid:
			_bar(sp + Vector2(0, 9), w, b.queue_progress(), Color(0.95, 0.95, 1.0))
	# rally lines of the selected building
	for e in cmd.selection:
		if e is Building and e.rally_set and not e.dead and e.owner_id == cmd.pid:
			var a := rig.to_screen(Vector3(e.p.x, 0.2 + e.ground_h(), e.p.y))
			var b2 := rig.to_screen(Vector3(e.rally.x, 0.2 + e.world.height_at(e.rally), e.rally.y))
			draw_dashed_line(a, b2, Color(0.4, 0.85, 1.0, 0.8), 2.0, 8.0)
			draw_circle(b2, 6.0, Color(0.4, 0.85, 1.0, 0.8))
	if cmd.box_active:
		var r := Rect2(cmd.box_start, Vector2.ZERO).expand(cmd.box_end)
		draw_rect(r, Color(0.35, 1.0, 0.5, 0.12))
		draw_rect(r, Color(0.35, 1.0, 0.5, 0.9), false, 2.0)

class_name Overlay
extends Control
## Drawn over the 3D view: health bars, construction and training progress, how many
## workers are collecting at each of your main bases, the box-select rectangle and rally
## lines.

var world: World
var rig: CameraRig
var cmd: Commander
var line_t: float = 0.0
var line_n: Dictionary = {}        # your main bases -> collectors on their crystals (counted 4 times a second)
var line_labels: Dictionary = {}   # main base -> the text drawn over it this frame
var focus: Array = []              # enemies your units were told to attack, circled in red this frame


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func _process(d: float) -> void:
	line_t -= d
	if line_t <= 0.0 and world != null and cmd != null:
		line_t = 0.25
		line_n.clear()
		for b in world.buildings:
			if b.owner_id == cmd.pid and b.slot == "main" and b.built and not b.dead:
				line_n[b] = world.line_collectors(cmd.pid, world.site_of_main(b))
	queue_redraw()


## One of the two targets shown while holding on the ground with units selected.
func _order_target(kind: String, title: String, icon_id: String, col: Color) -> void:
	var c: Vector2 = cmd.order_spot(kind)
	var hot: bool = cmd.order_hot == kind
	var r := Commander.ORDER_R * (1.0 if hot else 0.82)
	draw_line(cmd.order_at, c, Color(col, 0.35), 2.0, true)
	draw_circle(c, r, Color(col.r * 0.35, col.g * 0.35, col.b * 0.35, 0.92) if hot else Color(0.04, 0.05, 0.08, 0.86))
	draw_arc(c, r, 0.0, TAU, 40, Color(col, 1.0 if hot else 0.8), 3.5 if hot else 2.0, true)
	var icon := UiKit.icon(icon_id)
	if icon:
		draw_texture_rect(icon, Rect2(c - Vector2(15, 22), Vector2(30, 30)), false, col.lerp(Color.WHITE, 0.25 if hot else 0.0))
	var font: Font = UiKit.font_bold if UiKit.font_bold != null else ThemeDB.fallback_font
	var tw := font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
	draw_string(font, c + Vector2(-tw * 0.5, 22.0), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, col.lerp(Color.WHITE, 0.4))


## A red ring on the ground round `t` (at its height if it flies), with a soft pulse.
func _focus_ring(t) -> void:
	var fly: float = t.fly if t is Unit else 0.0
	var h: float = t.ground_h() + fly + 0.15
	var r: float = t.radius * 1.25 + 0.25
	var pts := PackedVector2Array()
	for i in 25:
		var a := TAU * float(i) / 24.0
		var q := Vector3(t.p.x + cos(a) * r, h, t.p.y + sin(a) * r)
		if not rig.in_front(q):
			return
		pts.append(rig.to_screen(q))
	var k := 0.75 + 0.25 * sin(Time.get_ticks_msec() * 0.008)
	draw_polyline(pts, Color(0.0, 0.0, 0.0, 0.45), 5.0, true)
	draw_polyline(pts, Color(1.0, 0.22, 0.18, k), 2.5, true)


## "12/14" beside a crystal: the workers collecting on a base's crystal line and the most
## it takes. It turns gold when the line is full.
func _collectors(c: Vector2, n: int) -> String:
	var full := n >= Defs.LINE_MAX
	var text := "%d/%d" % [n, Defs.LINE_MAX]
	var font: Font = UiKit.font_bold if UiKit.font_bold != null else ThemeDB.fallback_font
	var fs := 18
	var tw := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var iw := 18.0
	var w := 8.0 + iw + 5.0 + tw + 9.0
	var r := Rect2(c - Vector2(w * 0.5, 13.0), Vector2(w, 26.0))
	var col := UiKit.GOLD if full else UiKit.TEXT
	draw_rect(r, Color(0.04, 0.05, 0.08, 0.84))
	draw_rect(r, Color(col, 0.9 if full else 0.35), false, 2.0 if full else 1.0)
	var icon := UiKit.icon("ui:crystal")
	if icon:
		draw_texture_rect(icon, Rect2(r.position + Vector2(8.0, 4.0), Vector2(iw, iw)), false, UiKit.GOLD)
	draw_string(font, r.position + Vector2(8.0 + iw + 5.0, 19.5), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)
	return text


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
		var show_prog: bool = (not b.built) or ((b.queue.size() > 0 or b.research != "") and b.owner_id == cmd.pid)
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
		elif b.research != "" and b.owner_id == cmd.pid:
			_bar(sp + Vector2(0, 9), w, b.research_progress(), Color(1.0, 0.8, 0.3))
	# a red circle round every enemy your units have been told to attack
	focus.clear()
	for u in world.units:
		if u.owner_id == cmd.pid and not u.dead and u.order == Unit.O.ATTACK and u.target != null and is_instance_valid(u.target) \
				and not u.target.dead and u.target.owner_id != cmd.pid and u.target.shown and not focus.has(u.target):
			focus.append(u.target)
	for t in focus:
		_focus_ring(t)
	# collectors on each of your crystal lines, over its main base
	line_labels.clear()
	for b in line_n:
		if not is_instance_valid(b) or b.dead:
			continue
		var ltop := Vector3(b.p.x, float(b.def.get("model_h", 3.0)) + 0.6 + b.ground_h(), b.p.y)
		if not rig.in_front(ltop):
			continue
		var lsp := rig.to_screen(ltop) + Vector2(0, -30)
		if vr.grow(60).has_point(lsp):
			line_labels[b] = _collectors(lsp, int(line_n[b]))
	# rally lines of the selected building
	for e in cmd.selection:
		if e is Building and e.rally_set and not e.dead and e.owner_id == cmd.pid:
			var a := rig.to_screen(Vector3(e.p.x, 0.2 + e.ground_h(), e.p.y))
			var b2 := rig.to_screen(Vector3(e.rally.x, 0.2 + e.world.height_at(e.rally), e.rally.y))
			draw_dashed_line(a, b2, Color(0.4, 0.85, 1.0, 0.8), 2.0, 8.0)
			draw_circle(b2, 6.0, Color(0.4, 0.85, 1.0, 0.8))
	if cmd.box_active and cmd.order_menu:
		_order_target("move", "MOVE", "ui:move", Color(0.3, 1.0, 0.45))
		_order_target("attack", "ATTACK", "ui:attack", Color(1.0, 0.3, 0.22))
	if cmd.box_active and not (cmd.order_menu and cmd.order_hot != ""):
		var r := Rect2(cmd.box_start, Vector2.ZERO).expand(cmd.box_end)
		draw_rect(r, Color(0.35, 1.0, 0.5, 0.12))
		draw_rect(r, Color(0.35, 1.0, 0.5, 0.9), false, 2.0)
		# armed but not moved yet: a pulsing ring under the finger says "now slide"
		if r.size.length() < 6.0:
			var k := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 90.0)
			draw_arc(cmd.box_start, 30.0 + 6.0 * k, 0.0, TAU, 40, Color(0.35, 1.0, 0.5, 0.85), 3.0, true)

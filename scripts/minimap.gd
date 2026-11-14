class_name Minimap
extends Control
## The map in the corner: terrain, resources, everyone you can see, the camera
## frame. Tap or drag to look somewhere; in attack/move mode a tap orders there.

var world: World
var rig: CameraRig
var cmd: Commander
var base_tex: ImageTexture
var refresh_t: float = 0.0
var pings: Array = []       # [pos, time]
var dragging: bool = false


func setup(w: World, r: CameraRig, c: Commander) -> void:
	world = w
	rig = r
	cmd = c
	mouse_filter = Control.MOUSE_FILTER_STOP
	_bake()
	if world.fog:
		var fr := ColorRect.new()
		fr.mouse_filter = Control.MOUSE_FILTER_IGNORE
		fr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		var sm := ShaderMaterial.new()
		sm.shader = load("res://shaders/minimap_fog.gdshader")
		sm.set_shader_parameter("vis", world.fog.vis_tex)
		sm.set_shader_parameter("seen", world.fog.seen_tex)
		fr.material = sm
		fr.show_behind_parent = false
		add_child(fr)


var terrain: Image


func _bake() -> void:
	var n: int = world.grid.size
	if terrain == null:
		terrain = Image.create(n, n, false, Image.FORMAT_RGBA8)
		for y in n:
			for x in n:
				var k: int = world.grid.kind_at(Vector2i(x, y))
				var c := Color(0.22, 0.21, 0.26)
				if k == 1:
					c = Color(0.08, 0.08, 0.11)
				terrain.set_pixel(x, y, c)
	var img: Image = terrain.duplicate()
	for r in world.resources:
		if r.dead:
			continue
		var col := Color(1.0, 0.8, 0.25) if r.kind == "mineral" else Color(0.5, 0.25, 0.75)
		for yy in r.cells.y:
			for xx in r.cells.x:
				img.set_pixel(r.cell.x + xx, r.cell.y + yy, col)
	base_tex = ImageTexture.create_from_image(img)


func ping(at: Vector2) -> void:
	pings.append([at, world.time])


func _process(delta: float) -> void:
	refresh_t += delta
	if refresh_t > 4.0:
		refresh_t = 0.0
		_bake()
	queue_redraw()


func to_map(q: Vector2) -> Vector2:
	return q / float(world.grid.size) * size


func from_map(m: Vector2) -> Vector2:
	return m / size * float(world.grid.size)


func _draw() -> void:
	if world == null:
		return
	draw_rect(Rect2(Vector2.ZERO, size), Color(0, 0, 0, 0.6))
	draw_texture_rect(base_tex, Rect2(Vector2.ZERO, size), false)
	var k := size.x / float(world.grid.size)
	for b in world.buildings:
		if b.dead or not b.shown:
			continue
		var c: Color = b.team_color()
		var r := Rect2(to_map(Vector2(b.cell)), Vector2(b.size, b.size) * k)
		draw_rect(r, c)
		draw_rect(r, Color(0, 0, 0, 0.6), false, 1.0)
	for u in world.units:
		if u.dead or not u.shown or u.hidden_inside:
			continue
		var c: Color = u.team_color()
		if u.selected:
			c = Color(0.5, 1.0, 0.6)
		var s := maxf(2.0, u.radius * 2.0 * k)
		draw_rect(Rect2(to_map(u.p) - Vector2(s, s) * 0.5, Vector2(s, s)), c)
	# alerts
	var i := pings.size() - 1
	while i >= 0:
		var age: float = world.time - float(pings[i][1])
		if age > 3.0:
			pings.remove_at(i)
		else:
			var pr := 6.0 + fmod(age, 1.0) * 14.0
			draw_arc(to_map(pings[i][0]), pr, 0, TAU, 20, Color(1, 0.3, 0.2, 1.0 - fmod(age, 1.0)), 2.0)
		i -= 1
	# camera frame
	var corners: Array = rig.view_corners()
	var pts := PackedVector2Array()
	for c2 in corners:
		pts.append(to_map((c2 as Vector2).clamp(Vector2(-20, -20), Vector2(world.grid.size + 20, world.grid.size + 20))))
	pts.append(pts[0])
	draw_polyline(pts, Color(1, 1, 1, 0.85), 1.5)
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.5, 0.6, 0.75, 0.7), false, 2.0)


func _gui_input(ev: InputEvent) -> void:
	var pos := Vector2.ZERO
	var press := false
	var drag := false
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
		pos = ev.position
		press = ev.pressed
		dragging = ev.pressed
		if not ev.pressed:
			accept_event()
			return
	elif ev is InputEventMouseMotion and dragging:
		pos = ev.position
		drag = true
	elif ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_RIGHT and ev.pressed:
		var q := from_map(ev.position)
		world.command_move(cmd.own_units(true), q, true)
		accept_event()
		return
	else:
		return
	accept_event()
	var q2 := from_map(pos)
	if press and cmd.mode in [Commander.M.ATTACK, Commander.M.MOVE]:
		var am := cmd.mode == Commander.M.ATTACK
		world.command_move(cmd.own_units(not am), q2, am)
		world.fx.marker(q2, Color(1, 0.35, 0.3) if am else Color(0.3, 1, 0.45))
		Sfx.play("click")
		cmd.cancel_mode()
		dragging = false
		return
	if press or drag:
		rig.look_at_ground(q2)

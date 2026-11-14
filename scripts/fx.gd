class_name Fx
extends Node3D
## Shots in flight (they carry the damage until they land), plus the flashes,
## flames, beams and explosions that show it. With world.visuals off only the
## flight timing remains, so the balance runs see the same delays.

var world
var shots: Array = []
static var shader: Shader
static var meshes: Dictionary = {}

const LOOK := {
	# kind: [colour, mesh, size, arc height, sound]
	"bolt": [Color(0.35, 0.9, 1.0), "streak", 0.09, 0.0, "bolt"],
	"glob": [Color(0.55, 1.0, 0.25), "ball", 0.13, 0.6, "glob"],
	"shell": [Color(1.0, 0.62, 0.2), "ball", 0.16, 0.2, "shell"],
	"shard": [Color(0.95, 0.88, 0.7), "spike", 0.12, 0.4, "glob"],
	"missile": [Color(0.4, 0.95, 1.0), "spike", 0.12, 2.2, "missile"],
	"spine": [Color(0.92, 0.84, 0.66), "spike", 0.18, 2.6, "missile"],
	"cannon": [Color(0.4, 0.9, 1.0), "ball", 0.28, 0.0, "shell"],
	"bomb": [Color(0.55, 1.0, 0.25), "ball", 0.3, -0.5, "glob"],
	"flame": [Color(1.0, 0.5, 0.12), "", 0.0, 0.0, "flame"],
	"acid": [Color(0.5, 1.0, 0.2), "", 0.0, 0.0, "flame"],
	"beam": [Color(0.4, 0.92, 1.0), "", 0.0, 0.0, "beam"],
	"bile": [Color(0.55, 1.0, 0.2), "", 0.0, 0.0, "beam"],
	"zap": [Color(0.4, 0.9, 1.0), "", 0.0, 0.0, ""],
	"bite": [Color(0.6, 1.0, 0.3), "", 0.0, 0.0, ""],
}


static func _shader() -> Shader:
	if shader == null:
		shader = load("res://shaders/fx.gdshader")
	return shader


static func _mesh(kind: String) -> Mesh:
	if meshes.has(kind):
		return meshes[kind]
	var m: Mesh
	match kind:
		"streak":
			var c := CapsuleMesh.new()
			c.radius = 0.5
			c.height = 5.0
			c.radial_segments = 6
			c.rings = 1
			m = c
		"spike":
			var cy := CylinderMesh.new()
			cy.top_radius = 0.0
			cy.bottom_radius = 0.5
			cy.height = 3.0
			cy.radial_segments = 6
			m = cy
		"beam":
			var cb := CylinderMesh.new()
			cb.top_radius = 1.0
			cb.bottom_radius = 1.0
			cb.height = 1.0
			cb.radial_segments = 8
			cb.rings = 1
			m = cb
		_:
			var s := SphereMesh.new()
			s.radius = 1.0
			s.height = 2.0
			s.radial_segments = 10
			s.rings = 6
			m = s
	var sm := ShaderMaterial.new()
	sm.shader = _shader()
	m.surface_set_material(0, sm)
	meshes[kind] = m
	return m


static func _particle_mesh() -> Mesh:
	if meshes.has("particle"):
		return meshes["particle"]
	var s := SphereMesh.new()
	s.radius = 0.5
	s.height = 1.0
	s.radial_segments = 6
	s.rings = 3
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.vertex_color_use_as_albedo = true
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.no_depth_test = false
	s.surface_set_material(0, m)
	meshes["particle"] = s
	return s


func _glow_node(mesh_kind: String, col: Color, size: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = _mesh(mesh_kind)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.scale = Vector3.ONE * size
	mi.set_instance_shader_parameter("tint", col)
	mi.set_instance_shader_parameter("fade", 1.0)
	add_child(mi)
	return mi


func _muzzle(u) -> Vector3:
	var y: float = u.fly + float(u.def.get("model_h", 1.0)) * 0.6
	var fwd := Vector3(sin(u.facing), 0, cos(u.facing))
	return Vector3(u.p.x, y, u.p.y) + fwd * (u.radius * 0.9)


func _aim(t) -> Vector3:
	var y := 0.5
	if t is Unit:
		y = t.fly + float(t.def.get("model_h", 1.0)) * 0.45
	elif t is Building:
		y = float(t.def.get("model_h", 2.0)) * 0.4
	return Vector3(t.p.x, y, t.p.y)


# ---------------------------------------------------------------- projectiles

func projectile(u, t, speed: float) -> void:
	var kind: String = u.def.get("fx", "bolt")
	var look: Array = LOOK.get(kind, LOOK["bolt"])
	var start := _muzzle(u)
	if kind == "bomb":
		start = Vector3(u.p.x, u.fly - 0.2, u.p.y)
	var end := _aim(t)
	var s := {
		"owner": u.owner_id, "src": u, "t": t, "w": u.weapon, "kind": kind,
		"pos": start, "end": end, "speed": speed, "arc": float(look[3]),
		"start": start, "flown": 0.0, "total": maxf(0.1, start.distance_to(end)), "node": null,
	}
	if world.visuals and u.shown:
		var n := _glow_node(String(look[1]), look[0], float(look[2]))
		n.position = start
		s["node"] = n
		_flash(start, look[0], 0.22, 0.08)
		Sfx.play_at(String(look[4]), u.p, u.race_pitch())
	shots.append(s)


func step(dt: float) -> void:
	var i := shots.size() - 1
	while i >= 0:
		var s: Dictionary = shots[i]
		var t = s["t"]
		if t and is_instance_valid(t) and not t.dead:
			s["end"] = _aim(t)
		var end: Vector3 = s["end"]
		var pos: Vector3 = s["pos"]
		var to := end - pos
		var d := to.length()
		var mv: float = s["speed"] * dt
		if d <= mv or d < 0.05:
			var live = t if (t and is_instance_valid(t) and not t.dead) else null
			var src = s["src"] if is_instance_valid(s["src"]) else null
			world.hit(s["owner"], src, live, Vector2(end.x, end.z), s["w"], s["kind"])
			if s["node"]:
				(s["node"] as Node3D).queue_free()
			shots.remove_at(i)
		else:
			pos += to / d * mv
			s["pos"] = pos
			s["flown"] = float(s["flown"]) + mv
			var n = s["node"]
			if n:
				var k: float = clampf(float(s["flown"]) / (float(s["flown"]) + d), 0.0, 1.0)
				var arc: float = s["arc"]
				var vis := pos + Vector3(0, sin(k * PI) * arc * minf(1.0, float(s["total"]) / 6.0), 0)
				var node: Node3D = n
				var prev := node.position
				node.position = vis
				var dir := vis - prev
				if dir.length() > 0.001:
					node.look_at(vis + dir, Vector3.UP if absf(dir.normalized().y) < 0.98 else Vector3.RIGHT)
					node.rotate_object_local(Vector3.RIGHT, -PI / 2)
				if s["kind"] == "missile" or s["kind"] == "spine":
					if randf() < 0.6:
						_flash(vis, Color(0.6, 0.6, 0.65, 0.5), 0.18, 0.4, 0.4)
		i -= 1


# ---------------------------------------------------------------- instant weapons

func instant(u, t) -> void:
	if not world.visuals or not (u.shown or t.shown):
		return
	var kind: String = u.def.get("fx", "zap")
	var look: Array = LOOK.get(kind, LOOK["zap"])
	var col: Color = look[0]
	var a := _muzzle(u)
	var b := _aim(t)
	match kind:
		"flame", "acid":
			_spray(a, b, col)
		"beam", "bile":
			_beam(a, b, col, 0.22 if u.slot == "special" else 0.08)
		_:
			_flash(b, col, 0.3, 0.12)
	var snd := String(look[4])
	if snd != "":
		Sfx.play_at(snd, u.p, u.race_pitch())


func _spray(a: Vector3, b: Vector3, col: Color) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.emitting = false
	p.amount = 28
	p.lifetime = 0.45
	p.explosiveness = 0.85
	var dir := (b - a)
	var L := dir.length()
	p.direction = dir.normalized() if L > 0.01 else Vector3.FORWARD
	p.spread = 14.0
	p.initial_velocity_min = L / 0.42
	p.initial_velocity_max = L / 0.32
	p.gravity = Vector3(0, 1.5, 0)
	p.scale_amount_min = 0.25
	p.scale_amount_max = 0.55
	var curve := Curve.new()
	curve.add_point(Vector2(0, 0.4))
	curve.add_point(Vector2(0.5, 1.0))
	curve.add_point(Vector2(1, 0.1))
	p.scale_amount_curve = curve
	var grad := Gradient.new()
	grad.set_color(0, Color(1, 1, 0.8, 1) if col.r > 0.8 else Color(0.85, 1, 0.7, 1))
	grad.set_color(1, Color(col.r, col.g, col.b, 0.0))
	grad.add_point(0.4, col)
	p.color_ramp = grad
	p.mesh = _particle_mesh()
	p.position = a
	add_child(p)
	p.emitting = true
	get_tree().create_timer(1.0).timeout.connect(p.queue_free)


func _beam(a: Vector3, b: Vector3, col: Color, w: float) -> void:
	var n := _glow_node("beam", col, 1.0)
	var mid := (a + b) * 0.5
	var L := a.distance_to(b)
	n.position = mid
	var dir := (b - a).normalized()
	if absf(dir.y) < 0.99:
		n.look_at(b, Vector3.UP)
		n.rotate_object_local(Vector3.RIGHT, PI / 2)
	n.scale = Vector3(w, L, w)
	var tw := create_tween()
	tw.tween_method(func(v): if is_instance_valid(n): n.set_instance_shader_parameter("fade", v), 1.0, 0.0, 0.28)
	tw.tween_callback(n.queue_free)
	_flash(b, col, 0.5, 0.15)


## A glowing sphere that grows and fades.
func _flash(at: Vector3, col: Color, size: float, life: float, grow: float = 1.8) -> void:
	if not world.visuals:
		return
	var n := _glow_node("ball", col, size)
	n.position = at
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(n, "scale", Vector3.ONE * size * grow, life)
	tw.tween_method(func(v): if is_instance_valid(n): n.set_instance_shader_parameter("fade", v), 1.0, 0.0, life)
	tw.chain().tween_callback(n.queue_free)


func impact(at: Vector2, t, kind: String, splash: float) -> void:
	var look: Array = LOOK.get(kind, LOOK["zap"])
	var y := 0.4
	if t and is_instance_valid(t):
		y = _aim(t).y
		if not t.shown:
			return
	var p3 := Vector3(at.x, y, at.y)
	if splash > 0.0:
		_flash(p3, look[0], splash * 0.5, 0.35, 2.0)
		_burst(p3, look[0], 14, 3.0)
	else:
		_flash(p3, look[0], 0.22, 0.14)


func _burst(at: Vector3, col: Color, n: int, spd: float) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.amount = n
	p.lifetime = 0.6
	p.explosiveness = 1.0
	p.direction = Vector3.UP
	p.spread = 80.0
	p.initial_velocity_min = spd * 0.4
	p.initial_velocity_max = spd
	p.gravity = Vector3(0, -9, 0)
	p.scale_amount_min = 0.05
	p.scale_amount_max = 0.14
	var grad := Gradient.new()
	grad.set_color(0, col)
	grad.set_color(1, Color(col.r, col.g, col.b, 0))
	p.color_ramp = grad
	p.mesh = _particle_mesh()
	p.position = at
	add_child(p)
	p.emitting = true
	get_tree().create_timer(1.2).timeout.connect(p.queue_free)


func death(e) -> void:
	if not world.visuals or not e.shown:
		return
	var void_race: bool = e.def.get("race", "") == "void"
	var big: float = minf(e.radius * (2.0 if e is Building else 1.0), 3.2)
	var at := Vector3(e.p.x, (e.fly if e is Unit else 0.0) + 0.5, e.p.y)
	if void_race:
		_flash(at, Color(0.5, 1.0, 0.25), 0.4 + big * 0.5, 0.45, 2.2)
		_burst(at, Color(0.45, 0.25, 0.6), 18 + int(big * 10), 4.0 + big)
		_burst(at, Color(0.55, 1.0, 0.25), 10 + int(big * 6), 3.0 + big)
		Sfx.play_at("splat", e.p, 1.0 if big < 2.0 else 0.6)
	else:
		_flash(at, Color(1.0, 0.65, 0.25), 0.5 + big * 0.6, 0.45, 2.2)
		_flash(at, Color(1.0, 0.95, 0.8), 0.3 + big * 0.3, 0.2, 1.6)
		_burst(at, Color(1.0, 0.7, 0.3), 18 + int(big * 10), 5.0 + big)
		_burst(at, Color(0.3, 0.3, 0.32), 10 + int(big * 6), 3.0 + big)
		Sfx.play_at("boom", e.p, 1.0 if big < 2.0 else 0.6)


func puff(at: Vector2, col: Color) -> void:
	_burst(Vector3(at.x, 0.6, at.y), col, 16, 3.0)


## A ring that marks where the player sent units.
func marker(at: Vector2, col: Color) -> void:
	if not world.visuals:
		return
	var n := _glow_node("ball", col, 0.35)
	n.position = Vector3(at.x, 0.08, at.y)
	n.scale = Vector3(0.6, 0.05, 0.6)
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(n, "scale", Vector3(0.1, 0.05, 0.1), 0.4)
	tw.tween_method(func(v): if is_instance_valid(n): n.set_instance_shader_parameter("fade", v), 1.0, 0.0, 0.4)
	tw.chain().tween_callback(n.queue_free)

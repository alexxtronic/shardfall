class_name Weather
extends Node3D
## Ambient particles round the camera: snow (Frostspire), embers and ash (Ember Rift) or
## drifting spores (Shatterfield). Purely a look; it follows the camera's focus and leaves
## its particles in the world as it moves.

var rig: CameraRig
var kind: String = ""


func setup(r: CameraRig, k: String, low_detail: bool = false) -> void:
	rig = r
	kind = k
	name = "Weather"
	var scale_n := 0.5 if low_detail else 1.0
	match k:
		"snow":
			_layer(int(900 * scale_n), 7.0, Vector3(46, 9, 34), Vector3(0, 12, 0), Vector3(0.4, -1.6, 0.2), 0.22,
				Color(1, 1, 1, 0.85), 0.0, 1.2)
			_layer(int(160 * scale_n), 5.0, Vector3(46, 6, 34), Vector3(0, 9, 0), Vector3(0.8, -2.4, 0.3), 0.42,
				Color(0.95, 0.97, 1.0, 0.55), 0.0, 1.8)
		"embers":
			_layer(int(260 * scale_n), 5.0, Vector3(46, 1, 34), Vector3(0, 0.5, 0), Vector3(0.2, 1.4, -0.1), 0.12,
				Color(1.0, 0.55, 0.18, 1.0), 3.0, 0.8)
			_layer(int(320 * scale_n), 8.0, Vector3(46, 8, 34), Vector3(0, 10, 0), Vector3(0.3, -0.7, 0.1), 0.16,
				Color(0.35, 0.32, 0.3, 0.6), 0.0, 1.0)
		"motes":
			_layer(int(180 * scale_n), 9.0, Vector3(46, 3, 34), Vector3(0, 2.5, 0), Vector3(0.15, 0.25, 0.05), 0.14,
				Color(0.75, 0.45, 1.0, 0.9), 1.6, 0.6)


func _layer(amount: int, life: float, box: Vector3, offset: Vector3, drift: Vector3, size: float,
		col: Color, glow: float, wobble: float) -> void:
	amount = int(amount * float(Graphics.setting("particles")))
	if amount <= 0:
		return
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = life
	p.preprocess = life
	p.local_coords = false
	p.visibility_aabb = AABB(Vector3(-60, -30, -50), Vector3(120, 60, 100))
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = box
	pm.direction = drift.normalized()
	pm.spread = 25.0
	pm.initial_velocity_min = drift.length() * 0.6
	pm.initial_velocity_max = drift.length() * 1.2
	pm.gravity = Vector3.ZERO
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = wobble
	pm.turbulence_noise_scale = 6.0
	pm.turbulence_influence_min = 0.05
	pm.turbulence_influence_max = 0.15
	pm.scale_min = 0.6
	pm.scale_max = 1.3
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 0))
	fade.set_color(1, Color(1, 1, 1, 0))
	fade.add_point(0.15, Color(1, 1, 1, 1))
	fade.add_point(0.8, Color(1, 1, 1, 1))
	var ft := GradientTexture1D.new()
	ft.gradient = fade
	pm.color_ramp = ft
	p.process_material = pm
	p.position = offset
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_color = col
	m.albedo_texture = _dot()
	if glow > 0.0:
		m.emission_enabled = true
		m.emission = Color(col.r, col.g, col.b)
		m.emission_energy_multiplier = glow
	q.material = m
	p.draw_pass_1 = q
	add_child(p)


static var _dot_tex: Texture2D


static func _dot() -> Texture2D:
	if _dot_tex:
		return _dot_tex
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = 32
	t.height = 32
	_dot_tex = t
	return t


func _process(_delta: float) -> void:
	if rig:
		position = Vector3(rig.focus.x, rig.focus_h, rig.focus.y)

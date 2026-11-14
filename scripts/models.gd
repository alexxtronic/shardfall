class_name Models
extends RefCounted
## Puts a model on every entity. Uses assets/models/<id>.glb when it exists,
## fitted to the size the game expects; otherwise a stand-in built from
## primitives in the race's colours. Also animates units each frame.

const AMBRON_BODY := Color(0.93, 0.89, 0.81)
const AMBRON_TRIM := Color(0.88, 0.64, 0.23)
const AMBRON_DARK := Color(0.17, 0.18, 0.21)
const AMBRON_GLOW := Color(0.37, 0.89, 1.0)
const VOID_BODY := Color(0.33, 0.18, 0.45)
const VOID_BONE := Color(0.85, 0.78, 0.66)
const VOID_FLESH := Color(0.45, 0.12, 0.2)
const VOID_GLOW := Color(0.55, 1.0, 0.23)

static var scenes: Dictionary = {}
static var mats: Dictionary = {}
static var rocks: Dictionary = {}


static func scene_for(id: String) -> PackedScene:
	if scenes.has(id):
		return scenes[id]
	var path := "res://assets/models/%s.glb" % id
	var ps: PackedScene = null
	if ResourceLoader.exists(path):
		ps = load(path)
	scenes[id] = ps
	return ps


static func mat(c: Color, emissive: float = 0.0, rough: float = 0.6, metal: float = 0.0) -> StandardMaterial3D:
	var key := "%s_%.2f_%.2f_%.2f" % [c.to_html(), emissive, rough, metal]
	if mats.has(key):
		return mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	if emissive > 0.0:
		m.emission_enabled = true
		m.emission = c
		m.emission_energy_multiplier = emissive
	mats[key] = m
	return m


static func _prim(parent: Node3D, mesh: Mesh, m: Material, pos: Vector3, scl: Vector3 = Vector3.ONE, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = m
	mi.position = pos
	mi.scale = scl
	mi.rotation = rot
	parent.add_child(mi)
	return mi


static func _box(parent: Node3D, size: Vector3, m: Material, pos: Vector3, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var bm := BoxMesh.new()
	bm.size = size
	return _prim(parent, bm, m, pos, Vector3.ONE, rot)


static func _sphere(parent: Node3D, r: float, m: Material, pos: Vector3, scl: Vector3 = Vector3.ONE) -> MeshInstance3D:
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = r * 2.0
	sm.radial_segments = 16
	sm.rings = 8
	return _prim(parent, sm, m, pos, scl)


static func _cyl(parent: Node3D, r_top: float, r_bot: float, h: float, m: Material, pos: Vector3, rot: Vector3 = Vector3.ZERO, sides: int = 12) -> MeshInstance3D:
	var cm := CylinderMesh.new()
	cm.top_radius = r_top
	cm.bottom_radius = r_bot
	cm.height = h
	cm.radial_segments = sides
	cm.rings = 1
	return _prim(parent, cm, m, pos, Vector3.ONE, rot)


# ---------------------------------------------------------------- fitting

static func _aabb_of(node: Node, xf: Transform3D, acc: Array) -> void:
	if node is MeshInstance3D and node.visible and node.mesh:
		var a: AABB = xf * (node as MeshInstance3D).get_aabb()
		if acc.is_empty():
			acc.append(a)
		else:
			acc[0] = (acc[0] as AABB).merge(a)
	for ch in node.get_children():
		if ch is Node3D:
			_aabb_of(ch, xf * (ch as Node3D).transform, acc)


static func local_aabb(root: Node3D) -> AABB:
	var acc: Array = []
	_aabb_of(root, Transform3D.IDENTITY, acc)
	return acc[0] if acc.size() > 0 else AABB(Vector3(-0.5, 0, -0.5), Vector3.ONE)


## Scale uniformly to fit width w (x/z) and height h, sit on y=0, centre in x/z.
static func fit(inst: Node3D, w: float, h: float) -> float:
	var a := local_aabb(inst)
	var horiz := maxf(a.size.x, a.size.z)
	var s := 1.0
	if horiz > 0.001 and a.size.y > 0.001:
		s = minf(w / horiz, h / a.size.y)
	inst.scale = Vector3.ONE * s
	var c := a.get_center()
	inst.position = Vector3(-c.x * s, -a.position.y * s, -c.z * s)
	return s


static var team_mats: Dictionary = {}


## Recolour every material named team* to the player colour. The recoloured
## copies are shared, so all units of a player batch together.
static func tint_team(root: Node, col: Color) -> void:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m3: MeshInstance3D = mi
		if m3.mesh == null:
			continue
		for i in m3.mesh.get_surface_count():
			var m: Material = m3.get_active_material(i)
			if m and m.resource_name.to_lower().begins_with("team"):
				var key := "%d_%s" % [m.get_instance_id(), col.to_html()]
				if not team_mats.has(key):
					var nm := (m as StandardMaterial3D).duplicate() if m is StandardMaterial3D else StandardMaterial3D.new()
					nm.emission_enabled = true
					nm.emission = col
					if nm.albedo_texture:
						# textured team areas (Void bone) keep their own colour and take a light wash
						nm.albedo_color = Color.WHITE.lerp(col, 0.22)
						nm.emission_energy_multiplier = 0.03
					else:
						# flat team lights glow in the player colour
						nm.albedo_color = col
						nm.emission_energy_multiplier = 0.6
					team_mats[key] = nm
				m3.set_surface_override_material(i, team_mats[key])


static var cool_mats: Dictionary = {}


## Void flesh is crimson in the source art; pull it toward violet so the
## swarm reads purple and the team colour stays legible.
static func cool_void(root: Node) -> void:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m3: MeshInstance3D = mi
		if m3.mesh == null:
			continue
		for i in m3.mesh.get_surface_count():
			var m: Material = m3.get_active_material(i)
			if m == null or not (m is StandardMaterial3D):
				continue
			var nm := m.resource_name.to_lower()
			if nm.begins_with("team") or nm.begins_with("glow"):
				continue
			var key := m.get_instance_id()
			if not cool_mats.has(key):
				var c := (m as StandardMaterial3D).duplicate() as StandardMaterial3D
				c.albedo_color = c.albedo_color * Color(0.78, 0.8, 1.0)
				cool_mats[key] = c
			m3.set_surface_override_material(i, cool_mats[key])


static func _anim_player(root: Node) -> AnimationPlayer:
	var found := root.find_children("*", "AnimationPlayer", true, false)
	return found[0] if found.size() > 0 else null


# ---------------------------------------------------------------- units

static func attach_unit(w, u) -> void:
	var holder := Node3D.new()
	holder.name = "Visual"
	u.add_child(holder)
	u.visual = holder
	var inner: Node3D
	var ps := scene_for(u.def_id)
	var race: String = u.def["race"]
	if ps:
		inner = ps.instantiate()
		holder.add_child(inner)
		fit(inner, float(u.def["model_w"]), float(u.def["model_h"]))
		if race == "void":
			cool_void(inner)
		tint_team(inner, u.team_color())
	else:
		inner = Node3D.new()
		holder.add_child(inner)
		_placeholder_unit(inner, String(u.def["slot"]), race, u.team_color())
	inner.name = "Model"
	var ap := _anim_player(inner)
	if ap:
		var names := _anim_names(ap)
		for key in ["idle", "walk", "run", "fly"]:
			if names.has(key):
				var an: Animation = ap.get_animation(names[key])
				if an:
					an.loop_mode = Animation.LOOP_LINEAR
		if names.has("attack"):
			var at: Animation = ap.get_animation(names["attack"])
			if at:
				at.loop_mode = Animation.LOOP_NONE
		u.set_meta("anim", ap)
		u.set_meta("anim_names", names)
		if names.has("idle"):
			ap.play(names["idle"])
			ap.seek(randf() * ap.current_animation_length, true)
	var tur := inner.find_children("turret", "Node3D", true, false)
	if tur.size() > 0:
		u.set_meta("turret", tur[0])
		u.set_meta("turret_rot", (tur[0] as Node3D).rotation.y)
	if u.is_worker:
		var gem := MeshInstance3D.new()
		var pm := PrismMesh.new()
		pm.size = Vector3(0.22, 0.3, 0.22)
		gem.mesh = pm
		gem.position = Vector3(0, float(u.def["model_h"]) + 0.12, 0)
		gem.visible = false
		holder.add_child(gem)
		u.set_meta("gem", gem)
		# a model may carry its own crystals (a node named cargo): shown only while carrying them
		var cargo := inner.find_children("cargo*", "MeshInstance3D", true, false)
		if cargo.size() > 0:
			u.set_meta("cargo", cargo[0])
			(cargo[0] as Node3D).visible = false
	u.make_ring(u.radius, Color(0.3, 1.0, 0.45, 0.9))
	if u.is_air and u.ring:
		u.ring.position.y = -u.fly + 0.06
	if u.shown == false:
		u.visible = false


static func _anim_names(ap: AnimationPlayer) -> Dictionary:
	var out := {}
	for n in ap.get_animation_list():
		var l := String(n).to_lower()
		for key in ["idle", "walk", "run", "attack", "fly"]:
			if l.contains(key) and not out.has(key):
				out[key] = n
	return out


static func _placeholder_unit(root: Node3D, slot: String, race: String, team: Color) -> void:
	var amb := race == "ambron"
	var body := mat(AMBRON_BODY if amb else VOID_BODY, 0.0, 0.45 if amb else 0.3)
	var trim := mat(AMBRON_TRIM if amb else VOID_BONE, 0.0, 0.5, 0.2 if amb else 0.0)
	var glow := mat(AMBRON_GLOW if amb else VOID_GLOW, 2.5)
	var dark := mat(AMBRON_DARK if amb else VOID_FLESH, 0.0, 0.6)
	var tm := mat(team, 0.6)
	match slot:
		"worker":
			_sphere(root, 0.32, body, Vector3(0, 0.55, 0), Vector3(1, 0.9, 1.1))
			_sphere(root, 0.1, glow, Vector3(0, 0.6, 0.3))
			_box(root, Vector3(0.5, 0.12, 0.3), dark, Vector3(0, 0.25, 0.2))
			_cyl(root, 0.0, 0.08, 0.3, trim, Vector3(-0.15, 0.95, -0.05), Vector3(-0.3, 0, 0))
			_cyl(root, 0.0, 0.08, 0.3, trim, Vector3(0.15, 0.95, -0.05), Vector3(-0.3, 0, 0))
		"infantry":
			_cyl(root, 0.18, 0.22, 0.6, body, Vector3(0, 0.55, 0))
			_sphere(root, 0.17, trim, Vector3(0, 1.0, 0))
			_sphere(root, 0.07, glow, Vector3(0, 1.0, 0.14))
			_box(root, Vector3(0.08, 0.08, 0.55), dark, Vector3(0.2, 0.7, 0.25))
			_box(root, Vector3(0.3, 0.06, 0.06), tm, Vector3(0, 0.75, -0.18))
			_cyl(root, 0.07, 0.07, 0.4, dark, Vector3(-0.1, 0.2, 0))
			_cyl(root, 0.07, 0.07, 0.4, dark, Vector3(0.1, 0.2, 0))
		"heavy":
			_box(root, Vector3(0.75, 0.7, 0.55), body, Vector3(0, 0.95, 0))
			_sphere(root, 0.2, trim, Vector3(0, 1.45, 0.05))
			_sphere(root, 0.08, glow, Vector3(0, 1.45, 0.22))
			_box(root, Vector3(0.3, 0.3, 0.7), dark, Vector3(0.45, 0.95, 0.2))
			_box(root, Vector3(0.12, 0.6, 0.6), trim, Vector3(-0.48, 0.95, 0.1))
			_box(root, Vector3(0.76, 0.1, 0.56), tm, Vector3(0, 1.2, 0))
			_cyl(root, 0.12, 0.14, 0.6, dark, Vector3(-0.18, 0.3, 0))
			_cyl(root, 0.12, 0.14, 0.6, dark, Vector3(0.18, 0.3, 0))
		"vehicle_flame", "vehicle_missile":
			_box(root, Vector3(1.3, 0.5, 1.9), body, Vector3(0, 0.45, 0))
			_box(root, Vector3(1.4, 0.3, 2.0), dark, Vector3(0, 0.18, 0))
			_box(root, Vector3(1.32, 0.08, 1.92), tm, Vector3(0, 0.62, 0))
			var tur := Node3D.new()
			tur.name = "turret"
			tur.position = Vector3(0, 0.75, -0.1)
			root.add_child(tur)
			if slot == "vehicle_flame":
				_cyl(tur, 0.4, 0.45, 0.35, trim, Vector3.ZERO)
				_cyl(tur, 0.08, 0.1, 0.8, dark, Vector3(-0.15, 0.05, 0.55), Vector3(PI / 2, 0, 0))
				_cyl(tur, 0.08, 0.1, 0.8, dark, Vector3(0.15, 0.05, 0.55), Vector3(PI / 2, 0, 0))
				_sphere(tur, 0.09, mat(Color(1, 0.5, 0.1), 3.0), Vector3(0, 0.05, 0.95))
			else:
				_box(tur, Vector3(0.9, 0.55, 0.9), trim, Vector3(0, 0.25, 0), Vector3(-0.35, 0, 0))
				for i in 3:
					for j in 2:
						_sphere(tur, 0.07, glow, Vector3(-0.25 + i * 0.25, 0.35 + j * 0.2, 0.42))
		"air_light":
			_sphere(root, 0.3, body, Vector3(0, 0.3, 0), Vector3(0.9, 0.6, 1.8))
			_box(root, Vector3(1.4, 0.06, 0.45), trim, Vector3(0, 0.3, -0.05))
			_sphere(root, 0.1, glow, Vector3(-0.35, 0.3, -0.45))
			_sphere(root, 0.1, glow, Vector3(0.35, 0.3, -0.45))
			_box(root, Vector3(0.5, 0.07, 0.08), tm, Vector3(0, 0.45, 0))
		"air_heavy":
			_box(root, Vector3(1.4, 0.6, 2.0), body, Vector3(0, 0.6, 0))
			for sx in [-1.0, 1.0]:
				for sz in [-1.0, 1.0]:
					_cyl(root, 0.4, 0.4, 0.18, dark, Vector3(sx * 1.0, 0.6, sz * 0.7))
					_cyl(root, 0.3, 0.3, 0.2, glow, Vector3(sx * 1.0, 0.55, sz * 0.7))
			_cyl(root, 0.12, 0.15, 1.2, trim, Vector3(0, 0.25, 0.6), Vector3(PI / 2, 0, 0))
			_box(root, Vector3(1.42, 0.1, 2.02), tm, Vector3(0, 0.85, 0))
		"special":
			_sphere(root, 1.2, body, Vector3(0, 3.0, 0), Vector3(1.2, 0.8, 1.4))
			_sphere(root, 0.35, glow, Vector3(0, 3.0, 1.5))
			for sx in [-1.0, 1.0]:
				for sz in [-1.0, 1.0]:
					_cyl(root, 0.2, 0.28, 2.6, dark, Vector3(sx * 1.2, 1.3, sz * 1.1), Vector3(sz * 0.25, 0, -sx * 0.25))
			_box(root, Vector3(2.0, 0.2, 2.6), tm, Vector3(0, 3.5, 0))
			_cyl(root, 0.18, 0.22, 2.0, trim, Vector3(0, 2.6, 1.2), Vector3(PI / 2, 0, 0))
		_:
			_sphere(root, 0.4, body, Vector3(0, 0.5, 0))
	if not amb:
		# a few bone spikes so the swarm reads differently
		var h := 0.8
		match slot:
			"heavy":
				h = 1.6
			"special":
				h = 4.0
			"vehicle_flame", "vehicle_missile":
				h = 0.9
		for i in 3:
			_cyl(root, 0.0, 0.07 * (h + 0.5), 0.35 * (h * 0.5 + 0.5), trim, Vector3(-0.2 + 0.2 * i, h, -0.1), Vector3(-0.6, 0, 0), 6)


static func animate_unit(u, delta: float) -> void:
	if u.dead:
		return
	var t: float = u.world.time
	var y: float = u.fly
	if u.is_air:
		y += sin(t * 2.0 + float(u.eid)) * 0.12
	u.position = Vector3(u.p.x, y, u.p.y)
	u.rotation.y = u.facing
	u.visible = u.shown and not u.hidden_inside
	if not u.visible or u.visual == null:
		return
	var model: Node3D = u.visual
	if u.has_meta("gem"):
		var gem: MeshInstance3D = u.get_meta("gem")
		var has_cargo: bool = u.has_meta("cargo")
		if has_cargo:
			(u.get_meta("cargo") as Node3D).visible = u.carry > 0 and u.carry_kind == "mineral"
		gem.visible = u.carry > 0 and not (has_cargo and u.carry_kind == "mineral")
		if gem.visible:
			gem.material_override = mat(Color(1.0, 0.78, 0.2), 1.2, 0.3) if u.carry_kind == "mineral" else mat(Color(0.55, 0.25, 0.95), 1.5, 0.2)
			gem.rotation.y = t * 2.0
	if u.has_meta("turret"):
		var tn: Node3D = u.get_meta("turret")
		var base: float = u.get_meta("turret_rot")
		var aim := base
		if u.target != null and is_instance_valid(u.target) and not u.target.dead:
			var to: Vector2 = u.target.p - u.p
			aim = base + wrapf(atan2(to.x, to.y) - u.facing, -PI, PI)
		tn.rotation.y = lerp_angle(tn.rotation.y, aim, clampf(delta * 6.0, 0.0, 1.0))
	if u.has_meta("anim"):
		var ap: AnimationPlayer = u.get_meta("anim")
		var names: Dictionary = u.get_meta("anim_names")
		var busy: float = u.get_meta("atk_until", -1.0)
		# a fresh shot starts the attack animation from the top
		if u.attack_anim > 0.3 and names.has("attack") and t >= busy - 0.05:
			var alen: float = ap.get_animation(names["attack"]).length
			var cdv: float = float(u.weapon.get("cd", 1.0))
			ap.speed_scale = maxf(1.0, alen / maxf(0.2, cdv * 0.9))
			ap.play(names["attack"], 0.06)
			ap.seek(0.0, true)
			u.set_meta("atk_until", t + alen / ap.speed_scale)
			return
		if t < busy:
			return
		var want := "idle"
		if u.moving:
			want = "walk" if names.has("walk") else ("run" if names.has("run") else "idle")
		if u.is_air and names.has("fly") and u.moving:
			want = "fly"
		if names.has(want) and ap.current_animation != names[want]:
			ap.play(names[want], 0.2)
		if u.moving and want == "walk":
			ap.speed_scale = clampf(u.speed / 3.0, 0.7, 1.5)
		else:
			ap.speed_scale = 1.0
		# a little lean into fast flight
		if u.is_air:
			model.rotation.x = lerpf(model.rotation.x, 0.12 if u.moving else 0.0, clampf(delta * 4.0, 0.0, 1.0))
		return
	# procedural motion for unrigged models
	var bob := 0.0
	var tilt := 0.0
	var roll := 0.0
	if u.moving and not u.is_air:
		bob = absf(sin(u.walk_phase)) * 0.05 * (1.0 + u.radius)
		roll = sin(u.walk_phase) * 0.04
		tilt = 0.05
	elif u.is_air and u.moving:
		tilt = 0.12
	else:
		bob = sin(t * 1.7 + float(u.eid)) * 0.012
	var recoil: float = u.attack_anim
	model.position = Vector3(0, bob, -recoil * 0.12)
	model.rotation = Vector3(tilt - recoil * 0.25, 0, roll)
	var sq := 1.0 + recoil * 0.06
	model.scale = Vector3(sq, 1.0 / sq, sq)


# ---------------------------------------------------------------- buildings

static func attach_building(w, b) -> void:
	var holder := Node3D.new()
	holder.name = "Visual"
	b.add_child(holder)
	b.visual = holder
	var ps := scene_for(b.def_id)
	var inner: Node3D
	var sz: float = float(b.size)
	if ps:
		inner = ps.instantiate()
		holder.add_child(inner)
		fit(inner, sz - 0.1, float(b.def["model_h"]) * 1.35)
		tint_team(inner, b.team_color())
	else:
		inner = Node3D.new()
		holder.add_child(inner)
		_placeholder_building(inner, String(b.def["slot"]), String(b.def["race"]), sz, float(b.def["model_h"]), b.team_color())
	inner.name = "Model"
	var floaty := inner.find_children("*float*", "Node3D", true, false)
	floaty.append_array(inner.find_children("*glow_core*", "Node3D", true, false))
	floaty.append_array(inner.find_children("*_crystal", "Node3D", true, false))
	floaty.append_array(inner.find_children("*halo*", "Node3D", true, false))
	if floaty.size() > 0:
		b.set_meta("floaty", floaty[0])
		b.set_meta("floaty_y", (floaty[0] as Node3D).position.y)
	var tur := inner.find_children("turret*", "Node3D", true, false)
	if tur.size() > 0:
		b.set_meta("turret", tur[0])
	b.make_ring(sz * 0.62, Color(0.3, 1.0, 0.45, 0.9))


static var field_mats: Array = []


## The power field of an Ambron relay: a faint disc with a bright rim.
static func power_field(r: float) -> Node3D:
	if field_mats.is_empty():
		var fill := StandardMaterial3D.new()
		fill.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		fill.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		fill.albedo_color = Color(0.35, 0.85, 1.0, 0.13)
		fill.no_depth_test = false
		var rim := fill.duplicate()
		rim.albedo_color = Color(0.5, 0.92, 1.0, 0.75)
		field_mats = [fill, rim]
	var root := Node3D.new()
	root.name = "PowerField"
	var disc := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = r
	cm.bottom_radius = r
	cm.height = 0.02
	cm.radial_segments = 48
	cm.rings = 1
	disc.mesh = cm
	disc.material_override = field_mats[0]
	disc.position.y = 0.06
	disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(disc)
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = r - 0.09
	tm.outer_radius = r + 0.09
	tm.rings = 64
	tm.ring_segments = 4
	ring.mesh = tm
	ring.scale = Vector3(1, 0.3, 1)
	ring.position.y = 0.08
	ring.material_override = field_mats[1]
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(ring)
	return root


static func _placeholder_building(root: Node3D, slot: String, race: String, sz: float, h: float, team: Color) -> void:
	var amb := race == "ambron"
	var body := mat(AMBRON_BODY if amb else VOID_BODY, 0.0, 0.45 if amb else 0.3)
	var trim := mat(AMBRON_TRIM if amb else VOID_BONE, 0.0, 0.5)
	var glow := mat(AMBRON_GLOW if amb else VOID_GLOW, 2.5)
	var dark := mat(AMBRON_DARK if amb else VOID_FLESH, 0.0, 0.6)
	var tm := mat(team, 0.6)
	var s := sz - 0.3
	if amb:
		_box(root, Vector3(s, 0.4, s), dark, Vector3(0, 0.2, 0))
		match slot:
			"main":
				_cyl(root, s * 0.42, s * 0.48, h * 0.55, body, Vector3(0, 0.4 + h * 0.27, 0), Vector3.ZERO, 8)
				_sphere(root, s * 0.36, body, Vector3(0, h * 0.7, 0), Vector3(1, 0.7, 1))
				_cyl(root, s * 0.43, s * 0.43, 0.15, glow, Vector3(0, h * 0.6, 0), Vector3.ZERO, 8)
				_cyl(root, s * 0.49, s * 0.49, 0.2, tm, Vector3(0, 0.55, 0), Vector3.ZERO, 8)
			"supply":
				_cyl(root, 0.15, 0.45, h * 0.8, body, Vector3(0, h * 0.4 + 0.2, 0), Vector3.ZERO, 4)
				var fl := _sphere(root, 0.25, glow, Vector3(0, h + 0.2, 0), Vector3(0.8, 1.3, 0.8))
				fl.name = "float_crystal"
			"tower":
				_cyl(root, s * 0.32, s * 0.45, h * 0.7, body, Vector3(0, h * 0.35 + 0.2, 0), Vector3.ZERO, 6)
				_cyl(root, s * 0.36, s * 0.36, 0.12, tm, Vector3(0, h * 0.55, 0), Vector3.ZERO, 6)
				var head := Node3D.new()
				head.name = "turret"
				head.position = Vector3(0, h * 0.9, 0)
				root.add_child(head)
				_sphere(head, 0.42, glow, Vector3.ZERO)
				for i in 3:
					var a := TAU * i / 3.0
					_cyl(head, 0.03, 0.08, 0.9, trim, Vector3(cos(a) * 0.45, 0.2, sin(a) * 0.45), Vector3(sin(a) * 0.4, 0, -cos(a) * 0.4), 5)
			"extractor":
				_cyl(root, s * 0.35, s * 0.42, h * 0.6, dark, Vector3(0, h * 0.3 + 0.2, 0), Vector3.ZERO, 10)
				_cyl(root, s * 0.2, s * 0.2, 0.3, mat(Color(0.6, 0.3, 1.0), 2.0), Vector3(0, h * 0.62 + 0.2, 0))
				_box(root, Vector3(s, 0.25, 0.3), trim, Vector3(0, 0.6, 0))
			_:
				_box(root, Vector3(s * 0.9, h * 0.75, s * 0.9), body, Vector3(0, h * 0.37 + 0.2, 0))
				_box(root, Vector3(s * 0.5, h * 0.45, 0.1), dark, Vector3(0, h * 0.3, s * 0.45))
				_box(root, Vector3(s * 0.92, 0.12, s * 0.92), glow, Vector3(0, h * 0.75, 0))
				_box(root, Vector3(s * 0.91, 0.15, s * 0.91), tm, Vector3(0, h * 0.5, 0))
				if slot == "special":
					_cyl(root, 0.1, s * 0.3, h * 0.8, trim, Vector3(0, h * 1.0, 0), Vector3.ZERO, 6)
	else:
		var creep := mat(Color(0.18, 0.08, 0.2), 0.0, 0.4)
		_cyl(root, s * 0.55, s * 0.6, 0.05, creep, Vector3(0, 0.03, 0), Vector3.ZERO, 16)
		match slot:
			"main":
				_sphere(root, s * 0.45, body, Vector3(0, h * 0.35, 0), Vector3(1, 0.9, 1))
				_sphere(root, s * 0.2, glow, Vector3(0, h * 0.3, s * 0.35))
				for i in 6:
					var a := TAU * i / 6.0
					_cyl(root, 0.0, 0.25, h * 0.6, trim, Vector3(cos(a) * s * 0.35, h * 0.75, sin(a) * s * 0.35), Vector3(sin(a) * 0.5, 0, -cos(a) * 0.5), 6)
				_sphere(root, s * 0.46, tm, Vector3(0, h * 0.12, 0), Vector3(1, 0.15, 1))
			"supply":
				var core := _sphere(root, 0.55, glow, Vector3(0, 0.9, 0), Vector3(1, 1.3, 1))
				core.name = "glow_core"
				for i in 4:
					var a := TAU * i / 4.0
					_cyl(root, 0.02, 0.08, 1.6, trim, Vector3(cos(a) * 0.55, 0.8, sin(a) * 0.55), Vector3(sin(a) * 0.3, 0, -cos(a) * 0.3), 5)
			"tower":
				_cyl(root, s * 0.22, s * 0.42, h * 0.75, body, Vector3(0, h * 0.37, 0), Vector3.ZERO, 9)
				_sphere(root, s * 0.42, tm, Vector3(0, h * 0.08, 0), Vector3(1, 0.2, 1))
				var maw := Node3D.new()
				maw.name = "turret"
				maw.position = Vector3(0, h * 0.85, 0)
				root.add_child(maw)
				_sphere(maw, 0.5, body, Vector3.ZERO, Vector3(1, 0.8, 1.2))
				_sphere(maw, 0.26, glow, Vector3(0, 0.05, 0.38))
				for i in 4:
					var a := TAU * i / 4.0
					_cyl(maw, 0.0, 0.09, 0.6, trim, Vector3(cos(a) * 0.4, 0.3, sin(a) * 0.4), Vector3(sin(a) * 0.5, 0, -cos(a) * 0.5), 5)
			"extractor":
				_cyl(root, s * 0.42, s * 0.48, h * 0.5, body, Vector3(0, h * 0.25, 0), Vector3.ZERO, 12)
				_cyl(root, s * 0.25, s * 0.25, 0.1, glow, Vector3(0, h * 0.5 + 0.02, 0))
				for i in 8:
					var a := TAU * i / 8.0
					_cyl(root, 0.0, 0.1, 0.5, trim, Vector3(cos(a) * s * 0.33, h * 0.6, sin(a) * s * 0.33), Vector3.ZERO, 5)
			_:
				_sphere(root, s * 0.48, body, Vector3(0, h * 0.35, 0), Vector3(1, h / s * 1.2, 1))
				_sphere(root, s * 0.15, glow, Vector3(s * 0.25, h * 0.4, s * 0.3))
				_sphere(root, s * 0.12, glow, Vector3(-s * 0.3, h * 0.3, s * 0.2))
				_sphere(root, s * 0.49, tm, Vector3(0, h * 0.1, 0), Vector3(1, 0.12, 1))
				for i in 3:
					_cyl(root, 0.0, 0.18, h * 0.6, trim, Vector3(-s * 0.25 + s * 0.25 * i, h * 0.85, -s * 0.1), Vector3(-0.4, 0, 0), 6)


static func animate_building(b, delta: float) -> void:
	if b.dead or b.visual == null:
		return
	b.visible = b.shown
	var v: Node3D = b.visual
	if not b.built:
		var k: float = 0.15 + 0.85 * b.progress
		v.scale = Vector3(0.92 + 0.08 * b.progress, k, 0.92 + 0.08 * b.progress)
	else:
		v.scale = Vector3.ONE
	if b.has_meta("turret"):
		var tn: Node3D = b.get_meta("turret")
		if is_instance_valid(tn):
			tn.rotation.y = lerp_angle(tn.rotation.y, b.facing, minf(1.0, delta * 8.0))
	if b.has_meta("floaty"):
		var f: Node3D = b.get_meta("floaty")
		if is_instance_valid(f):
			var y0: float = b.get_meta("floaty_y")
			f.position.y = y0 + sin(b.world.time * 1.6 + float(b.eid)) * 0.08
			f.rotation.y += delta * 0.6


# ---------------------------------------------------------------- resources and rocks

static func attach_resource(w, r, variant: int) -> void:
	var holder := Node3D.new()
	holder.name = "Visual"
	r.add_child(holder)
	r.visual = holder
	var id := "crystal_%s" % "abcd"[variant % 4] if r.kind == "mineral" else "slime_pile"
	var ps := scene_for(id)
	var inner: Node3D
	if ps:
		inner = ps.instantiate()
		holder.add_child(inner)
		if r.kind == "mineral":
			fit(inner, 2.1, 2.2)
		else:
			fit(inner, 3.0, 0.9)
	else:
		inner = Node3D.new()
		holder.add_child(inner)
		if r.kind == "mineral":
			var gold := mat(Color(1.0, 0.76, 0.2), 0.7, 0.25, 0.1)
			var amber := mat(Color(0.88, 0.52, 0.08), 0.5, 0.3)
			var rng := RandomNumberGenerator.new()
			rng.seed = r.eid
			for i in 6:
				var hgt := rng.randf_range(0.6, 1.8)
				var m: Material = gold if i % 2 == 0 else amber
				_cyl(inner, 0.0, rng.randf_range(0.14, 0.24), hgt, m, Vector3(rng.randf_range(-0.6, 0.6), hgt * 0.45, rng.randf_range(-0.25, 0.25)), Vector3(rng.randf_range(-0.35, 0.35), 0, rng.randf_range(-0.35, 0.35)), 6)
			_sphere(inner, 0.5, mat(Color(0.25, 0.25, 0.3)), Vector3(0, 0.05, 0), Vector3(1.6, 0.4, 0.8))
		else:
			_sphere(inner, 1.4, mat(Color(0.03, 0.02, 0.05), 0.0, 0.08, 0.3), Vector3(0, 0.0, 0), Vector3(1, 0.4, 1))
			_sphere(inner, 0.3, mat(Color(0.4, 1.0, 0.3), 1.2), Vector3(0.4, 0.4, 0.2), Vector3(1, 0.3, 1))
	inner.name = "Model"
	if r.kind == "mineral":
		# crystals face their footprint's long axis
		if r.cells.y > r.cells.x:
			holder.rotation.y = PI / 2
	r.make_ring(r.radius * 0.9, Color(1.0, 0.85, 0.3, 0.9))


static func rock_mesh(variant: int) -> Mesh:
	if rocks.has(variant):
		return rocks[variant]
	var id := "rock_%s" % "abc"[variant % 3]
	var ps := scene_for(id)
	var mesh: Mesh = null
	if ps:
		var inst: Node3D = ps.instantiate()
		var mis := inst.find_children("*", "MeshInstance3D", true, false)
		if mis.size() > 0:
			mesh = (mis[0] as MeshInstance3D).mesh
		inst.free()
	if mesh == null:
		var sm := SphereMesh.new()
		sm.radius = 1.6
		sm.height = 2.6
		sm.radial_segments = 7
		sm.rings = 4
		sm.material = mat(Color(0.25, 0.28, 0.34), 0.0, 0.9)
		mesh = sm
	rocks[variant] = mesh
	return mesh

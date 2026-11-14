class_name Entity
extends Node3D
## Anything on the map with an owner and hit points: units, buildings, and
## (with owner -1) resource nodes. The match (World) steps every entity itself,
## so the simulation can run faster than real time for the balance tests.

var world  # World
var eid: int = 0
var owner_id: int = -1
var def_id: String = ""
var def: Dictionary = {}
var hp: float = 1.0
var max_hp: float = 1.0
var armor: float = 0.0
var radius: float = 0.5
var p: Vector2 = Vector2.ZERO          # position on the ground plane (x, z)
var height: float = 1.0                 # for picking and hp bars
var dead: bool = false
var is_unit: bool = false
var is_building: bool = false
var is_resource: bool = false
var is_air: bool = false
var tags: Array = []
var sight: float = 8.0

var visual: Node3D
var ring: MeshInstance3D
var team_disc: MeshInstance3D
var selected: bool = false
var shown: bool = true              # visible to the human player (fog)
var last_damaged: float = -100.0
var flash_t: float = 0.0


func setup_common(w, id: String, owner: int) -> void:
	world = w
	def_id = id
	owner_id = owner
	def = Defs.get_def(id)
	if not def.is_empty():
		max_hp = float(def.get("hp", 100.0))
		hp = max_hp
		armor = float(def.get("armor", 0.0))
		sight = float(def.get("sight", 8.0))
		tags = (def.get("tags", []) as Array).duplicate()


func team_color() -> Color:
	if owner_id < 0 or world == null:
		return Color(1, 0.85, 0.3)
	return world.players[owner_id].color


func is_enemy_of(pid: int) -> bool:
	return owner_id >= 0 and pid >= 0 and owner_id != pid


func pos3() -> Vector3:
	return Vector3(p.x, 0.0, p.y)


func apply_damage(amount: float, src: Entity) -> void:
	if dead:
		return
	hp -= amount
	last_damaged = world.time if world else 0.0
	flash_t = 0.12
	if world:
		world.on_damaged(self, src)
	if hp <= 0.0:
		hp = 0.0
		if world:
			world.kill(self, src)


func set_selected(v: bool) -> void:
	selected = v
	if ring:
		ring.visible = v


func make_ring(r: float, col: Color) -> void:
	if world == null or not world.visuals:
		return
	ring = MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = r * 1.02
	tm.outer_radius = r * 1.18 + 0.04
	tm.rings = 32
	tm.ring_segments = 4
	ring.mesh = tm
	ring.scale = Vector3(1, 0.05, 1)
	ring.position.y = 0.06
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = col
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	ring.material_override = m
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.visible = false
	add_child(ring)


func make_team_disc(r: float) -> void:
	if world == null or not world.visuals or owner_id < 0:
		return
	team_disc = MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = r
	cm.bottom_radius = r
	cm.height = 0.02
	cm.radial_segments = 24
	cm.rings = 1
	team_disc.mesh = cm
	team_disc.position.y = 0.03
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var c := team_color()
	c.a = 0.28
	m.albedo_color = c
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	team_disc.material_override = m
	team_disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(team_disc)


func race_pitch() -> float:
	return 0.82 if String(def.get("race", "")) == "void" else 1.0


func status_text() -> String:
	return ""

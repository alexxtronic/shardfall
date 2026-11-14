class_name CameraRig
extends Node3D
## The RTS camera: looks down at the ground from the south (screen up = -z).
## One finger pans, two fingers pinch to zoom, the minimap jumps.

var cam: Camera3D
var focus: Vector2 = Vector2(30, 110)
var dist: float = 30.0
var min_d: float = 14.0
var max_d: float = 58.0
var map_size: float = 144.0
var vel: Vector2 = Vector2.ZERO   # coasting after a flick
var shake: float = 0.0


func _ready() -> void:
	cam = Camera3D.new()
	cam.fov = 40.0
	cam.near = 0.5
	cam.far = 500.0
	add_child(cam)
	cam.current = true
	apply()


func pitch() -> float:
	# a little flatter when zoomed in, steeper when zoomed out
	return deg_to_rad(lerpf(50.0, 62.0, (dist - min_d) / (max_d - min_d)))


func apply() -> void:
	focus = focus.clamp(Vector2(6, 10), Vector2(map_size - 6, map_size + 4))
	var pt := pitch()
	var off := Vector3(0, sin(pt) * dist, cos(pt) * dist)
	var f3 := Vector3(focus.x, 0, focus.y)
	var sh := Vector3.ZERO
	if shake > 0.0:
		sh = Vector3(randf() - 0.5, randf() - 0.5, randf() - 0.5) * shake
	cam.position = f3 + off + sh
	cam.look_at(f3 + sh, Vector3.UP)
	Sfx.listener = focus
	Sfx.hear_radius = 22.0 + dist


func _process(delta: float) -> void:
	if vel.length() > 0.05:
		focus += vel * delta
		vel = vel.lerp(Vector2.ZERO, clampf(delta * 5.0, 0.0, 1.0))
	shake = maxf(0.0, shake - delta * 2.0)
	# keyboard panning for desktop testing
	var k := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		k.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		k.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		k.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		k.y += 1
	if k != Vector2.ZERO:
		focus += k.normalized() * delta * (12.0 + dist)
	apply()


## World metres per screen pixel at the focus.
func m_per_px() -> float:
	var vh := get_viewport().get_visible_rect().size.y
	return 2.0 * dist * tan(deg_to_rad(cam.fov) * 0.5) / vh


func pan_pixels(d: Vector2) -> void:
	var k := m_per_px()
	focus -= Vector2(d.x * k, d.y * k / sin(pitch()))
	apply()


func fling(v_px: Vector2) -> void:
	var k := m_per_px()
	vel = -Vector2(v_px.x * k, v_px.y * k / sin(pitch()))


func zoom_by(f: float) -> void:
	dist = clampf(dist * f, min_d, max_d)
	apply()


func look_at_ground(q: Vector2) -> void:
	focus = q
	vel = Vector2.ZERO
	apply()


func screen_to_ground(sp: Vector2) -> Vector2:
	var o := cam.project_ray_origin(sp)
	var n := cam.project_ray_normal(sp)
	if absf(n.y) < 0.0001:
		return focus
	var t := -o.y / n.y
	var hitp := o + n * t
	return Vector2(hitp.x, hitp.z)


func to_screen(p3: Vector3) -> Vector2:
	return cam.unproject_position(p3)


func in_front(p3: Vector3) -> bool:
	return not cam.is_position_behind(p3)


func sees(q: Vector2) -> bool:
	var p3 := Vector3(q.x, 0, q.y)
	if cam.is_position_behind(p3):
		return false
	var sp := cam.unproject_position(p3)
	var r := get_viewport().get_visible_rect()
	return r.grow(-40).has_point(sp)


## The four ground corners of the view, for the minimap.
func view_corners() -> Array:
	var r := get_viewport().get_visible_rect()
	return [
		screen_to_ground(Vector2(0, 0)),
		screen_to_ground(Vector2(r.size.x, 0)),
		screen_to_ground(r.size),
		screen_to_ground(Vector2(0, r.size.y)),
	]

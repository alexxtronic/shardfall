class_name Fog
extends Node3D
## Fog of war for the human player, on a 2 m grid. Each fog cell is unexplored,
## explored or in sight. Enemy units show only while in sight; enemy buildings
## stay on the map once seen. The textures are filled straight from the byte
## arrays, so there's no per-pixel script work.

const EVERY := 0.2
const RES := 2.0

var world
var n: int = 72
var vis := PackedByteArray()      # 255 when in sight this update
var seen := PackedByteArray()     # 255 once explored
var vis_img: Image
var seen_img: Image
var vis_tex: ImageTexture
var seen_tex: ImageTexture
var tex: ImageTexture             # alias used by the minimap check
var t: float = 0.0
var plane: MeshInstance3D
var stamps: Dictionary = {}
var enabled: bool = true


func setup() -> void:
	n = int(ceil(world.grid.size / RES))
	vis.resize(n * n)
	seen.resize(n * n)
	vis.fill(0)
	seen.fill(0)
	vis_img = Image.create_from_data(n, n, false, Image.FORMAT_L8, vis)
	seen_img = Image.create_from_data(n, n, false, Image.FORMAT_L8, seen)
	vis_tex = ImageTexture.create_from_image(vis_img)
	seen_tex = ImageTexture.create_from_image(seen_img)
	tex = vis_tex
	plane = MeshInstance3D.new()
	var pm := PlaneMesh.new()
	var size: float = world.grid.size
	pm.size = Vector2(size + 120, size + 120)
	plane.mesh = pm
	plane.position = Vector3(size * 0.5, 0.12, size * 0.5)
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/fog.gdshader")
	sm.set_shader_parameter("vis", vis_tex)
	sm.set_shader_parameter("seen", seen_tex)
	sm.set_shader_parameter("map_size", float(n) * RES)
	plane.material_override = sm
	plane.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(plane)
	update()


func _stamp(r: int) -> Array:
	if stamps.has(r):
		return stamps[r]
	var out: Array = []
	for y in range(-r, r + 1):
		for x in range(-r, r + 1):
			if x * x + y * y <= r * r + r:
				out.append(Vector2i(x, y))
	stamps[r] = out
	return out


func step(dt: float) -> void:
	t += dt
	if t >= EVERY:
		t = 0.0
		update()


func update() -> void:
	var me: int = world.human
	vis.fill(0)
	if not enabled:
		vis.fill(255)
		seen.fill(255)
	else:
		var done := {}
		for list in [world.units, world.buildings]:
			for e in list:
				if e.dead or e.owner_id != me:
					continue
				var c := Vector2i(int(e.p.x / RES), int(e.p.y / RES))
				var r := int(round(e.sight / RES))
				var key := c * 64 + Vector2i(r, 0)
				if done.has(key):
					continue
				done[key] = true
				for o in _stamp(r):
					var q: Vector2i = c + o
					if q.x >= 0 and q.y >= 0 and q.x < n and q.y < n:
						var i := q.y * n + q.x
						vis[i] = 255
						seen[i] = 255
	for u in world.units:
		if u.owner_id == me or u.owner_id < 0:
			u.shown = true
		else:
			u.shown = vis_at(u.p)
	for b in world.buildings:
		if b.owner_id == me:
			b.shown = true
			continue
		if not b.seen and _rect_visible(b):
			b.seen = true
		b.shown = b.seen
	vis_img.set_data(n, n, false, Image.FORMAT_L8, vis)
	seen_img.set_data(n, n, false, Image.FORMAT_L8, seen)
	vis_tex.update(vis_img)
	seen_tex.update(seen_img)


func vis_at(q: Vector2) -> bool:
	var c := Vector2i(int(q.x / RES), int(q.y / RES))
	if c.x < 0 or c.y < 0 or c.x >= n or c.y >= n:
		return false
	return vis[c.y * n + c.x] > 0


func explored_at(q: Vector2) -> bool:
	var c := Vector2i(int(q.x / RES), int(q.y / RES))
	if c.x < 0 or c.y < 0 or c.x >= n or c.y >= n:
		return false
	return seen[c.y * n + c.x] > 0


func _rect_visible(b) -> bool:
	for q in [b.p, Vector2(b.cell), Vector2(b.cell) + Vector2(b.size, b.size), Vector2(b.cell.x + b.size, b.cell.y), Vector2(b.cell.x, b.cell.y + b.size)]:
		if vis_at(q):
			return true
	return false

class_name GroundBake
extends Node
## Bakes the ground's noise into two tileable textures, once per run, on the GPU.
##
## The ground used to compute about 300 noise samples for every pixel of every frame, which
## kept a phone's GPU flat out at any graphics level. Now `bake_detail.gdshader` (cracks,
## pebbles, plates, grain: one 36 m tile) and `bake_noise.gdshader` (Voronoi and layered noise)
## each render once into a small off-screen viewport; the results are read back, given
## mipmaps and kept for the rest of the run. `ground.gdshader` then needs a few texture
## reads per pixel. The same textures serve every map.

signal done

const DETAIL_PX := 2048
const NOISE_PX := 1024

static var detail: ImageTexture
static var noise: ImageTexture
static var job: GroundBake


## Calls `then` once both textures exist: at once if they already do, else after the bake.
static func ensure(then: Callable) -> void:
	if detail != null and noise != null:
		then.call()
		return
	if job == null or not is_instance_valid(job):
		job = GroundBake.new()
		job.name = "GroundBake"
		(Engine.get_main_loop() as SceneTree).root.add_child.call_deferred(job)
	job.done.connect(then, CONNECT_ONE_SHOT)


func _ready() -> void:
	_bake()


func _stage(shader_path: String, px: int, hdr: bool) -> SubViewport:
	var vp := SubViewport.new()
	vp.size = Vector2i(px, px)
	vp.disable_3d = true
	vp.transparent_bg = true          # the alpha channel carries data
	vp.use_hdr_2d = hdr               # half floats: fine noise values survive
	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	var r := ColorRect.new()
	r.size = Vector2(px, px)
	var sm := ShaderMaterial.new()
	sm.shader = load(shader_path)
	r.material = sm
	vp.add_child(r)
	add_child(vp)
	return vp


func _bake() -> void:
	var t0 := Time.get_ticks_msec()
	var dv := _stage("res://shaders/bake_detail.gdshader", DETAIL_PX, false)
	var nv := _stage("res://shaders/bake_noise.gdshader", NOISE_PX, true)
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var di: Image = dv.get_texture().get_image()
	var ni: Image = nv.get_texture().get_image()
	di.generate_mipmaps()
	ni.generate_mipmaps()
	detail = ImageTexture.create_from_image(di)
	noise = ImageTexture.create_from_image(ni)
	dv.queue_free()
	nv.queue_free()
	print("ground textures baked in %d ms (%s, %s)" % [Time.get_ticks_msec() - t0, di.get_size(), ni.get_size()])
	done.emit()
	queue_free()

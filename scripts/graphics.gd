class_name Graphics
extends RefCounted
## The graphics quality levels behind the Settings slider. Lower levels run cooler and save
## battery on phones: a lower frame cap, 3D drawn at a lower resolution (the interface stays
## sharp), smaller and harder shadows, no MSAA, no glow and fewer weather particles.
## Prefs "graphics" holds the level; -1 means automatic (Balanced on phones, Max elsewhere).

const LEVELS := [
	# name, fps cap (0 = the screen's own rate), 3D scale, shadow atlas, soft shadow quality, MSAA, glow, particles
	{"name": "Battery", "fps": 30, "scale": 0.6, "shadow": 1024, "soft": RenderingServer.SHADOW_QUALITY_HARD, "msaa": Viewport.MSAA_DISABLED, "glow": false, "particles": 0.4},
	{"name": "Balanced", "fps": 60, "scale": 0.75, "shadow": 2048, "soft": RenderingServer.SHADOW_QUALITY_SOFT_VERY_LOW, "msaa": Viewport.MSAA_DISABLED, "glow": true, "particles": 0.7},
	{"name": "High", "fps": 60, "scale": 1.0, "shadow": 4096, "soft": RenderingServer.SHADOW_QUALITY_SOFT_LOW, "msaa": Viewport.MSAA_2X, "glow": true, "particles": 1.0},
	{"name": "Max", "fps": 0, "scale": 1.0, "shadow": 4096, "soft": RenderingServer.SHADOW_QUALITY_SOFT_LOW, "msaa": Viewport.MSAA_2X, "glow": true, "particles": 1.0},
]


## The level in use: the saved one, or the automatic pick for this device.
static func level() -> int:
	var l := int(Prefs.get_v("graphics"))
	if l < 0 or l >= LEVELS.size():
		l = 1 if OS.has_feature("mobile") else 3
	return l


static func setting(key: String):
	return LEVELS[level()][key]


## "Balanced · 60 fps" for the slider.
static func describe(l: int) -> String:
	var d: Dictionary = LEVELS[l]
	var fps := "%d fps" % int(d["fps"]) if int(d["fps"]) > 0 else ("up to 120 fps" if OS.has_feature("mobile") else "full frame rate")
	return "%s · %s" % [d["name"], fps]


## Apply the level to the engine and the window's viewport. Environment glow and weather
## particles are read by the match when it builds them (and glow is updated live).
static func apply(vp: Viewport) -> void:
	var d: Dictionary = LEVELS[level()]
	Engine.max_fps = int(d["fps"])
	if vp:
		var s := float(d["scale"])
		vp.scaling_3d_scale = s
		vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR if s >= 0.99 or s < 0.7 else Viewport.SCALING_3D_MODE_FSR
		vp.msaa_3d = int(d["msaa"])
	RenderingServer.directional_shadow_atlas_set_size(int(d["shadow"]), true)
	RenderingServer.directional_soft_shadow_filter_set_quality(int(d["soft"]))

shader_type spatial;
// Fog of war over the ground. vis = in sight now, seen = explored.
render_mode unshaded, blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, shadows_disabled;

uniform sampler2D vis : filter_linear, repeat_disable;
uniform sampler2D seen : filter_linear, repeat_disable;
uniform float map_size = 144.0;
varying vec3 wpos;

void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec2 uv = wpos.xz / map_size;
	float v = texture(vis, uv).r;
	float s = texture(seen, uv).r;
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) { v = 0.0; }
	float a = mix(0.8, 0.45, s);
	a = mix(a, 0.0, smoothstep(0.2, 0.8, v));
	ALBEDO = vec3(0.02, 0.015, 0.04);
	ALPHA = a;
}

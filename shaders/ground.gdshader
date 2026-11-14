shader_type spatial;
// Alien plateau ground. Colour comes from layered value noise in world space,
// darkened near rock walls (mask.r) and paved lighter on base sites (mask.g).
render_mode diffuse_burley, specular_schlick_ggx;

uniform sampler2D mask : filter_linear, repeat_disable;
uniform float map_size = 144.0;
uniform vec3 dust : source_color = vec3(0.30, 0.28, 0.31);
uniform vec3 sand : source_color = vec3(0.46, 0.40, 0.34);
uniform vec3 dark : source_color = vec3(0.16, 0.15, 0.19);
uniform vec3 vein : source_color = vec3(0.38, 0.22, 0.48);
uniform vec3 plate : source_color = vec3(0.40, 0.40, 0.44);

varying vec3 wpos;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
	return v;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz;
	float big = fbm(p * 0.035);
	float mid = fbm(p * 0.18 + 7.0);
	float fine = noise(p * 2.7);
	vec3 col = mix(dust, sand, smoothstep(0.42, 0.68, big));
	col = mix(col, dark, smoothstep(0.55, 0.85, mid) * 0.45);
	// faint violet veins
	float v = abs(fbm(p * 0.09 + 31.0) - 0.5);
	col = mix(col, vein, (1.0 - smoothstep(0.0, 0.035, v)) * 0.35);
	col *= 0.9 + fine * 0.18;
	vec2 uv = p / map_size;
	vec4 m = texture(mask, uv);
	bool inside = uv.x >= 0.0 && uv.y >= 0.0 && uv.x <= 1.0 && uv.y <= 1.0;
	float rock = inside ? m.r : 1.0;
	float site = inside ? m.g : 0.0;
	// paved hex-ish plate under base sites
	vec2 g = abs(fract(p * 0.5) - 0.5);
	float seam = smoothstep(0.47, 0.5, max(g.x, g.y));
	vec3 paved = mix(plate * (0.92 + fine * 0.1), plate * 0.7, seam);
	col = mix(col, paved, site * 0.55);
	col = mix(col, dark * 0.8, rock * 0.75);
	ALBEDO = col;
	ROUGHNESS = 0.92 - site * 0.25;
	METALLIC = 0.0;
}

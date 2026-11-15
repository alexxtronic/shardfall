shader_type canvas_item;
render_mode blend_disabled, unshaded;
// Baked once at startup (GroundBake): one 36 m tile of the ground's small shapes, wrapping
// without a seam. The ground shader reads it once per pixel.
//   R, G: slope of the surface in x and z (0.5 = flat), for lighting
//   B: 0.5, lower in a crack between plates, higher on a pebble
//   A: fine grain

const float TILE = 36.0;          // metres; the ground shader's DETAIL_T
const float CRACKS = 16.0;        // plate cells across the tile (about 0.45 per metre)
const float PEBBLES = 94.0;       // about 2.6 per metre
const float PLATES = 25.0;        // about 0.7 per metre
const float GRAIN = 112.0;        // about 3.1 per metre

float hashp(vec2 i, float per) {
	i = mod(i, per);
	return fract(sin(dot(i, vec2(127.1, 311.7))) * 43758.5453);
}
vec2 hash2p(vec2 i, float per) {
	i = mod(i, per);
	return fract(sin(vec2(dot(i, vec2(127.1, 311.7)), dot(i, vec2(269.5, 183.3)))) * 43758.5453);
}
float noisep(vec2 p, float per) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hashp(i, per), hashp(i + vec2(1, 0), per), u.x),
		mix(hashp(i + vec2(0, 1), per), hashp(i + vec2(1, 1), per), u.x), u.y);
}
float fbm3p(vec2 p, float per) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 3; i++) { v += a * noisep(p, per); p *= 2.0; per *= 2.0; a *= 0.5; }
	return v;
}
vec2 vorop(vec2 p, float per) {
	vec2 i = floor(p); vec2 f = fract(p);
	float d1 = 8.0; float d2 = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = hash2p(i + g, per) * 0.85 + 0.075;
			float d = length(g + o - f);
			if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
		}
	}
	return vec2(d1, d2 - d1);
}

// plates, cracks and pebbles as a height, in metres
float detail_h(vec2 uv, out float crack, out float peb) {
	vec2 v = vorop(uv * CRACKS, CRACKS);
	crack = 1.0 - smoothstep(0.0, 0.035, v.y);
	vec2 q = uv * PEBBLES + 11.0;
	vec2 s = vorop(q, PEBBLES);
	peb = (1.0 - smoothstep(0.08, 0.32, s.x)) * step(0.82, hashp(floor(q), PEBBLES));
	float plates = fbm3p(uv * PLATES, PLATES) * 0.35 + (0.5 - v.x) * 0.12;
	return plates - crack * 0.22 + peb * 0.12;
}

void fragment() {
	float e = 0.06;
	float crack; float peb; float c2; float p2;
	float h = detail_h(UV, crack, peb);
	float hx = detail_h(UV + vec2(e / TILE, 0.0), c2, p2);
	float hz = detail_h(UV + vec2(0.0, e / TILE), c2, p2);
	vec2 slope = vec2(-(hx - h), -(hz - h)) / e * 0.85;
	float grain = noisep(UV * GRAIN, GRAIN);
	COLOR = vec4(clamp(slope * 0.2 + 0.5, 0.0, 1.0), clamp(0.5 + 0.5 * (peb - crack), 0.0, 1.0), grain);
}

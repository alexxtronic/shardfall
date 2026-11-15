shader_type canvas_item;
render_mode blend_disabled, unshaded;
// Baked once at startup into a half-float texture (GroundBake): one tile of noise, 8 lattice
// cells across, every octave wrapping so it repeats without a seam. The ground shader reads
// it at many scales in place of computing noise for every pixel of every frame.
//   R: gap between the two nearest Voronoi points (0 on a crack)   A: distance to the nearest
//   G: 3-octave noise minus 0.5 (centred, so thin iso-lines keep their precision)
//   B: 5-octave noise

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
float fbmp(vec2 p, float per, int octaves) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < octaves; i++) { v += a * noisep(p, per); p *= 2.0; per *= 2.0; a *= 0.5; }
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

void fragment() {
	vec2 q = UV * 8.0;
	vec2 v = vorop(q, 8.0);
	COLOR = vec4(v.y, fbmp(q, 8.0, 3) - 0.5, fbmp(q, 8.0, 5), v.x);
}

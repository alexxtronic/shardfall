shader_type spatial;
// The ground of every map. The mesh is raised to the Terrain's corner heights (plateaus,
// ramps and the cliff bands between them), then into rough mounds under rock walls and
// beyond the map edge, with gentle swells elsewhere; base sites stay flat and paved.
// The surface gets cracked plates, craters, pebbles and mineral veins from world-space
// noise, layered rock on cliff faces, and per map: snow (Frostspire), frozen lakes,
// and flowing lava with glowing veins (Ember Rift). Colours come from Maps.THEMES.
render_mode diffuse_burley, specular_schlick_ggx;

uniform sampler2D mask : filter_linear, repeat_disable;   // R rock, G base site, B lava 1 / ice 0.5
uniform sampler2D hmap : filter_linear, repeat_disable;   // Terrain corner heights
uniform float map_size = 144.0;
uniform vec3 dust : source_color = vec3(0.33, 0.29, 0.33);
uniform vec3 rust : source_color = vec3(0.47, 0.35, 0.29);
uniform vec3 basalt : source_color = vec3(0.13, 0.12, 0.16);
uniform vec3 vein : source_color = vec3(0.45, 0.22, 0.6);
uniform vec3 plate : source_color = vec3(0.40, 0.40, 0.45);
uniform vec3 cliff_a : source_color = vec3(0.2, 0.18, 0.24);
uniform vec3 cliff_b : source_color = vec3(0.36, 0.3, 0.38);
uniform vec3 hazard : source_color = vec3(1.0, 0.42, 0.08);
uniform float snow = 0.0;
uniform float hazard_glow = 0.0;
uniform float vein_glow = 0.0;
uniform float bump = 1.0;

varying vec3 wpos;
varying vec3 wnorm;
varying float rockv;
varying float sitev;
varying float lavav;
varying float icev;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 hash2(vec2 p) {
	return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm3(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 3; i++) { v += a * noise(p); p *= 2.07; a *= 0.5; }
	return v;
}
float fbm5(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
	return v;
}
// x: distance to the nearest cell point, y: gap to the second (0 on a crack)
vec2 voro(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	float d1 = 8.0; float d2 = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = hash2(i + g) * 0.85 + 0.075;
			float d = length(g + o - f);
			if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
		}
	}
	return vec2(d1, d2 - d1);
}
// sparse craters on a 9 m lattice: a bowl with a raised rim
float crater(vec2 p) {
	vec2 c = floor(p / 9.0);
	vec2 h = hash2(c * 1.37 + 3.1);
	if (h.x < 0.45) { return 0.0; }
	vec2 ctr = (c + 0.2 + h * 0.6) * 9.0;
	float r = mix(1.0, 2.8, hash(c + 9.7));
	float d = length(p - ctr) / r;
	float bowl = -(1.0 - smoothstep(0.0, 1.0, d)) * 0.55;
	float rim = exp(-pow((d - 1.0) * 3.2, 2.0)) * 0.35;
	return (bowl + rim) * r * 0.35;
}

vec4 mask_at(vec2 p) {
	vec2 uv = p / map_size;
	bool inside = uv.x >= 0.0 && uv.y >= 0.0 && uv.x <= 1.0 && uv.y <= 1.0;
	vec4 m = textureLod(mask, clamp(uv, vec2(0.0), vec2(1.0)), 0.0);
	// beyond the edge is all rock, rising away from the map
	float out_d = max(max(-p.x, p.x - map_size), max(-p.y, p.y - map_size));
	float rock = inside ? m.r : clamp(0.6 + out_d * 0.08, 0.0, 1.0);
	return vec4(rock, inside ? m.g : 0.0, inside ? m.b : 0.0, 1.0);
}

float terrain_h(vec2 p) {
	return textureLod(hmap, (p + 0.5) / (map_size + 1.0), 0.0).r;
}

// big shapes, moved in the vertex stage: the terrain, mounds under rock, swells elsewhere,
// and lava sunk a little below its banks
float coarse_h(vec2 p) {
	vec4 m = mask_at(p);
	float r = smoothstep(0.45, 1.0, m.r);
	float mound = r * (0.25 + 0.85 * fbm3(p * 0.21 + 5.0));
	float swell = (fbm3(p * 0.09) - 0.5) * 0.16 * (1.0 - m.g);
	float lava = smoothstep(0.7, 0.95, m.b);
	return terrain_h(p) + mound + swell - lava * 0.35;
}

// small shapes, lighting only: plates, cracks, pebbles, craters
float detail_h(vec2 p, float site, out float crack, out float peb) {
	vec2 v = voro(p * 0.45);
	crack = 1.0 - smoothstep(0.0, 0.035, v.y);
	vec2 s = voro(p * 2.6 + 11.0);
	peb = (1.0 - smoothstep(0.08, 0.32, s.x)) * step(0.82, hash(floor(p * 2.6 + 11.0))) * (1.0 - smoothstep(0.2, 0.7, site));
	float plates = fbm3(p * 0.7) * 0.35 + (0.5 - v.x) * 0.12;
	return plates - crack * 0.22 + peb * 0.12 + crater(p);
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float e = 0.5;
	float h = coarse_h(w.xz);
	float hx = coarse_h(w.xz + vec2(e, 0.0)) - coarse_h(w.xz - vec2(e, 0.0));
	float hz = coarse_h(w.xz + vec2(0.0, e)) - coarse_h(w.xz - vec2(0.0, e));
	VERTEX.y += h;
	wpos = w + vec3(0.0, h, 0.0);
	wnorm = normalize(vec3(-hx / (2.0 * e), 1.0, -hz / (2.0 * e)));
	vec4 m = mask_at(w.xz);
	rockv = m.r;
	sitev = m.g;
	lavav = smoothstep(0.7, 0.95, m.b);
	icev = smoothstep(0.25, 0.45, m.b) * (1.0 - lavav);
}

void fragment() {
	vec2 p = wpos.xz;
	float crack; float peb;
	float e = 0.06;
	float h = detail_h(p, sitev, crack, peb);
	float c2; float p2;
	float hx = detail_h(p + vec2(e, 0.0), sitev, c2, p2);
	float hz = detail_h(p + vec2(0.0, e), sitev, c2, p2);
	float flat_site = 1.0 - sitev * 0.75;
	float steep = 1.0 - smoothstep(0.5, 0.82, wnorm.y);
	// snow settles on flat and gently sloped ground and fills the cracks, thinning in patches
	float drift = smoothstep(0.42, 0.66, fbm3(p * 0.11 + 3.0) + fbm3(p * 0.6) * 0.25);
	float snowk = snow * drift * smoothstep(0.8, 0.95, wnorm.y) * (1.0 - sitev * 0.7);
	vec3 n = normalize(wnorm + vec3(-(hx - h) / e, 0.0, -(hz - h) / e) * 0.85 * bump * flat_site * (1.0 - icev * 0.8) * (1.0 - snowk * 0.85));

	float big = fbm5(p * 0.03);
	float mid = fbm3(p * 0.16 + 7.0);
	float fine = noise(p * 3.1);
	vec3 col = mix(dust, rust, smoothstep(0.45, 0.72, big));
	col = mix(col, basalt * 1.4, smoothstep(0.58, 0.85, mid) * 0.4);
	// mineral veins
	float v = abs(fbm3(p * 0.08 + 31.0) - 0.5);
	float vein_k = (1.0 - smoothstep(0.0, 0.014, v)) * (1.0 - steep);
	col = mix(col, vein, vein_k * 0.35);
	// cracks and crater bowls are dark, rims and pebbles catch light
	col = mix(col, basalt, crack * 0.55 * (1.0 - sitev * 0.6));
	float cr = crater(p);
	col *= 1.0 + clamp(cr, -0.4, 0.3) * 0.6;
	col = mix(col, col * 1.3 + vec3(0.04), peb * 0.6);
	col *= 0.88 + fine * 0.2;

	// paved plates under base sites
	vec2 g = abs(fract(p * 0.5) - 0.5);
	float seam = smoothstep(0.46, 0.5, max(g.x, g.y));
	vec3 paved = mix(plate * (0.9 + fine * 0.12), plate * 0.62, seam);
	col = mix(col, paved, sitev * 0.6);

	// rock ground: dark basalt, lighter where it faces up
	float rk = smoothstep(0.3, 0.9, rockv);
	vec3 rockcol = mix(basalt, basalt * 2.2 + vec3(0.03, 0.02, 0.04), clamp(n.y * 1.6 - 0.7, 0.0, 1.0)) * (0.85 + fine * 0.3);
	col = mix(col, rockcol, rk * 0.85);

	// cliff faces: layered rock in bands that follow the height
	float strata = fbm3(vec2(wpos.y * 2.6 + fbm3(p * 0.6) * 1.5, (p.x + p.y) * 0.35));
	vec3 cliffcol = mix(cliff_a, cliff_b, smoothstep(0.3, 0.75, strata)) * (0.8 + fine * 0.35);
	col = mix(col, cliffcol, steep);

	// snow, plus a dusting on cliff ledges
	col = mix(col, vec3(0.9, 0.94, 1.0) * (0.94 + fine * 0.08), snowk);
	col = mix(col, vec3(0.86, 0.9, 0.97), snow * steep * smoothstep(0.55, 0.75, strata) * 0.5);

	// frozen lakes: smooth blue ice with pale cracks
	vec2 iv = voro(p * 0.32 + 4.0);
	float icecrack = 1.0 - smoothstep(0.0, 0.05, iv.y);
	vec3 icecol = mix(hazard * 0.75, hazard * 1.15, fbm3(p * 0.2)) + vec3(icecrack * 0.25);
	col = mix(col, icecol, icev);

	// lava: a slow flow of molten rock under a cracked dark crust
	vec2 flow = p * 0.3 + vec2(TIME * 0.06, TIME * 0.04);
	vec2 lv = voro(flow + fbm3(p * 0.2 + TIME * 0.05) * 1.5);
	float crust = smoothstep(0.02, 0.16, lv.y) * smoothstep(0.35, 0.6, fbm3(flow * 1.3));
	float heat = (1.0 - crust) * (0.75 + 0.25 * sin(TIME * 1.7 + p.x * 0.3 + p.y * 0.2));
	vec3 lavacol = mix(hazard * 1.1, basalt * 0.5, crust);
	col = mix(col, lavacol, lavav);

	ALBEDO = col;
	ROUGHNESS = clamp(0.93 - sitev * 0.28 - peb * 0.1 - icev * 0.8 - snowk * 0.15, 0.08, 1.0);
	METALLIC = 0.0;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	vec3 glow = hazard * hazard_glow * heat * lavav;
	glow += vein * vein_glow * vein_k * (0.6 + 0.4 * sin(TIME * 1.3 + p.x * 0.2 + p.y * 0.1)) * (1.0 - snowk);
	EMISSION = glow;
}

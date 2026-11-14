shader_type spatial;
// Additive glow for shots, flashes and beams. Each instance sets its own tint.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 tint : source_color = vec4(1.0, 0.8, 0.3, 1.0);
instance uniform float fade = 1.0;

void fragment() {
	// bright in the middle, fading to nothing at the silhouette, so low-poly
	// balls and beams read as soft glows rather than hard polygons
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float core = pow(facing, 1.6);
	ALBEDO = tint.rgb * (0.08 + core * 2.0) * fade;
	ALPHA = fade * tint.a;
}

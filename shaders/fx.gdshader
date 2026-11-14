shader_type spatial;
// Additive glow for shots, flashes and beams. Each instance sets its own tint.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 tint : source_color = vec4(1.0, 0.8, 0.3, 1.0);
instance uniform float fade = 1.0;

void fragment() {
	float rim = pow(clamp(dot(NORMAL, VIEW), 0.0, 1.0), 0.6);
	ALBEDO = tint.rgb * (0.6 + rim * 1.4) * fade;
	ALPHA = fade * tint.a;
}

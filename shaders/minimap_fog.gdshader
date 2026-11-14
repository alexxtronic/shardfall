shader_type canvas_item;
uniform sampler2D vis : filter_linear;
uniform sampler2D seen : filter_linear;
void fragment() {
	float v = texture(vis, UV).r;
	float s = texture(seen, UV).r;
	float a = mix(0.8, 0.42, s);
	a = mix(a, 0.0, smoothstep(0.2, 0.8, v));
	COLOR = vec4(0.0, 0.0, 0.03, a);
}

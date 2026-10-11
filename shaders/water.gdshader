// Pond surface: horizontal ripple bands (offset in whole pixels) plus twinkling sparkles.
shader_type canvas_item;

uniform float ripple_px = 1.0;
uniform float ripple_speed = 1.6;
uniform vec4 sparkle_colour : source_color = vec4(0.96, 0.97, 0.9, 1.0);
uniform float sparkle_density : hint_range(0.0, 0.1) = 0.012;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 px = TEXTURE_PIXEL_SIZE;
	vec2 cell = floor(UV / px);
	float band = sin(cell.y * 0.7 + TIME * ripple_speed) + 0.5 * sin(cell.y * 0.23 - TIME * 0.7);
	vec2 uv = UV + vec2(round(band * ripple_px) * px.x, 0.0);
	vec4 c = texture(TEXTURE, uv);
	float h = hash(cell);
	float twinkle = step(1.0 - sparkle_density, h) * step(0.6, sin(TIME * 2.5 + h * 60.0));
	c.rgb = mix(c.rgb, sparkle_colour.rgb, twinkle * 0.85 * c.a);
	COLOR = c;
}

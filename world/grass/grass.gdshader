// Grass tufts drawn as MultiMesh instances (see grass_field.gd).
// INSTANCE_CUSTOM = (atlas index, phase, base x, base y). Each quad is sheared by the shared wind
// field (same formula as scripts/vale/wind.gd), pushed aside near the player, and blade tips
// (alpha 250 in the atlas) catch the light while a gust passes.
shader_type canvas_item;

uniform vec2 cell = vec2(9.0, 16.0);
uniform float columns = 16.0;
uniform vec2 atlas_px = vec2(144.0, 64.0);
uniform vec2 player_pos = vec2(-9999.0);
uniform vec4 tip_light : source_color = vec4(0.894, 0.969, 0.659, 1.0);
uniform float bend = 1.0;

varying float v_gust;

vec2 wind(vec2 p, float t) {
	float base = sin(t * 1.7 + p.x * 0.045 + p.y * 0.02) * 0.6;
	float g = sin((p.x * 0.9 + p.y * 0.35) * 0.011 - t * 1.25);
	float gust = g > 0.55 ? pow((g - 0.55) / 0.45, 2.0) : 0.0;
	return vec2(base + gust * 2.6, gust);
}

void vertex() {
	float idx = INSTANCE_CUSTOM.r;
	vec2 base = INSTANCE_CUSTOM.ba;
	vec2 w = wind(base, TIME + INSTANCE_CUSTOM.g * 0.15);
	float s = w.x;
	vec2 d = (base - player_pos) * vec2(1.0, 1.6);
	float d2 = dot(d, d);
	if (d2 < 140.0) {
		s += sign(d.x + 0.001) * 3.2 * (1.0 - sqrt(d2) / 12.0);
	}
	float h = 1.0 - UV.y;  // 0 at the base, 1 at the top of the cell
	VERTEX.x += s * h * cell.y / 3.4 * bend;
	vec2 cellpos = vec2(mod(idx, columns), floor(idx / columns));
	UV = (cellpos * cell + UV * cell) / atlas_px;
	v_gust = w.y;
}

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	if (c.a < 0.5) {
		discard;
	}
	if (c.a < 0.995 && v_gust > 0.3) {
		c.rgb = tip_light.rgb;
	}
	COLOR = vec4(c.rgb, 1.0);
}

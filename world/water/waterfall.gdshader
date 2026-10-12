// A waterfall seen from the front: a lip where the water bends over the edge, streaks of falling
// water of different speeds, ragged see-through sides, and a churning foam plume with spreading
// rings at the foot. The sprite is a blank texture; everything is drawn from UV * size.
shader_type canvas_item;

uniform vec2 size = vec2(40.0, 60.0);  // whole sprite in px (fall + splash + side padding)
uniform float pad = 10.0;  // px of padding left/right for the splash
uniform float fall_h = 40.0;  // px from the lip to the pool
uniform float speed = 1.0;
uniform float seed = 0.0;
uniform vec4 c_deep : source_color = vec4(0.208, 0.471, 0.678, 1.0);
uniform vec4 c_mid : source_color = vec4(0.380, 0.690, 0.851, 1.0);
uniform vec4 c_light : source_color = vec4(0.690, 0.890, 0.957, 1.0);
uniform vec4 c_foam : source_color = vec4(0.965, 0.992, 1.0, 1.0);

const float BAYER[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21) + seed * 0.618);
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 t = p - i;
	t = t * t * (3.0 - 2.0 * t);
	float a = hash(i), b = hash(i + vec2(1.0, 0.0)), c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
	return a + (b - a) * t.x + (c - a) * t.y + (a - b - c + d) * t.x * t.y;
}

void fragment() {
	vec2 p = floor(UV * size);
	ivec2 q = ivec2(mod(p, 4.0));
	float bay = BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
	float w = size.x - pad * 2.0;
	float x = p.x - pad;  // 0..w across the fall
	float y = p.y;  // 0 at the lip
	float t = TIME * speed;
	vec4 col = vec4(0.0);

	// the falling sheet
	float edge_wobble = (vnoise(vec2(y * 0.25 - t * 6.0, 3.0)) - 0.5) * 2.0;
	float across = (x + 0.5) / w;
	if (x >= -edge_wobble * 0.6 && x < w + edge_wobble * 0.6 && y < fall_h + 2.0) {
		float lane = floor(x / 2.0);
		float lane_speed = 34.0 + hash(vec2(lane, 7.0)) * 26.0;  // px per second, different per lane
		float s = vnoise(vec2(x * 0.7, (y - t * lane_speed) * 0.09)) * 0.7 + vnoise(vec2(x * 1.9, (y - t * lane_speed * 1.3) * 0.25)) * 0.3;
		s += bay * 0.18;
		float sidedark = smoothstep(0.0, 0.22, min(across, 1.0 - across));
		vec3 c = s > 0.7 ? c_foam.rgb : s > 0.52 ? c_light.rgb : s > 0.32 ? c_mid.rgb : c_deep.rgb;
		c = mix(c_deep.rgb, c, 0.55 + 0.45 * sidedark);
		// the lip: water rolling over the edge, bright and smooth
		if (y < 3.0) c = y < 1.0 ? c_light.rgb : (s > 0.5 ? c_foam.rgb : c_light.rgb);
		// thinner (see-through) at the ragged sides
		float a = mix(0.55, 0.95, sidedark);
		col = vec4(c, a);
	}

	// foam plume and spreading rings at the foot
	float fy = y - fall_h;  // 0 at the pool surface
	if (fy > -6.0) {
		vec2 d = vec2((x - w * 0.5) / (w * 0.5 + pad * 0.6), fy / 7.0);
		float r = length(d);
		float boil = vnoise(vec2(x * 0.35 + t * 3.0, fy * 0.5 - t * 5.0)) * 0.6 + vnoise(vec2(x * 0.9 - t * 2.0, fy * 0.9)) * 0.4;
		if (r < 1.0 && boil + bay * 0.25 > 0.32 + r * 0.45) {
			col = vec4(boil > 0.62 ? c_foam.rgb : c_light.rgb, 1.0);
		}
		// rings expanding from the plume over the pool
		float ring = fract(r * 1.2 - t * 0.8);
		if (fy > 0.0 && r > 0.85 && r < 1.6 && ring < 0.08 && hash(vec2(floor(x / 2.0), floor(t * 0.8 - r * 1.2))) > 0.3) {
			col = vec4(c_foam.rgb, 0.65 * (1.6 - r));
		}
	}
	COLOR = col;
}

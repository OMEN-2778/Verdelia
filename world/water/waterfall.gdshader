// A waterfall seen from the front, drawn as a solid, rounded sheet: the water rolls over a bright
// lip, falls as a curved sheet lit from the upper left (a highlight down the left third, shade on
// the right), carries a few long streaks that stretch as they speed up, whitens near the bottom,
// and lands in a mound of puffy foam with a skirt of floating foam and clean rings on the pool.
// Wet rock darkens along both sides. The sprite is a blank texture; everything comes from UV * size.
shader_type canvas_item;

uniform vec2 size = vec2(40.0, 60.0);  // whole sprite in px (fall + splash + side padding)
uniform float pad = 10.0;  // px of padding left/right for the splash
uniform float fall_h = 40.0;  // px from the lip to the pool
uniform float top_pad = 10.0;  // px of river above the lip drawn here too, fading in, so the river runs into the fall
uniform float speed = 1.0;
uniform float seed = 0.0;
uniform vec4 c_surface : source_color = vec4(0.243, 0.580, 0.741, 1.0);  // match WaterLayer clear_color: the river it pours from
uniform vec4 c_deep : source_color = vec4(0.153, 0.369, 0.553, 1.0);
uniform vec4 c_mid : source_color = vec4(0.247, 0.522, 0.729, 1.0);
uniform vec4 c_light : source_color = vec4(0.459, 0.741, 0.882, 1.0);
uniform vec4 c_high : source_color = vec4(0.773, 0.918, 0.973, 1.0);
uniform vec4 c_foam : source_color = vec4(0.965, 0.992, 1.0, 1.0);
uniform vec4 c_foam_shade : source_color = vec4(0.682, 0.827, 0.910, 1.0);
uniform vec4 wet_rock : source_color = vec4(0.09, 0.08, 0.07, 0.42);

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

// Foam mound at the foot: overlapping round puffs that swell and settle. Returns 0 outside,
// 1 for lit foam, 0.5 for the shaded underside of a puff.
float puffs(vec2 d, float w, float t) {
	float best = 0.0;
	for (int i = 0; i < 7; i++) {
		float fi = float(i);
		float fx = (fi / 6.0 - 0.5) * (w + 8.0) + (hash(vec2(fi, 2.0)) - 0.5) * 3.0;
		float lift = sin(t * 2.2 + fi * 1.9) * 0.8;
		float r = (4.0 + hash(vec2(fi, 5.0)) * 2.5) * (1.0 - abs(fi / 6.0 - 0.5) * 0.8) + sin(t * 3.1 + fi * 2.7) * 0.5;
		vec2 c = vec2(fx, -1.5 - r * 0.45 + lift);
		vec2 q = (d - c) * vec2(1.0, 1.15);
		float l = length(q);
		if (l < r) {
			float v = (q.x + q.y) / r > 0.45 ? 0.5 : 1.0;  // light from the upper left
			best = max(best, v);
		}
	}
	return best;
}

void fragment() {
	vec2 p = floor(UV * size);
	ivec2 bq = ivec2(mod(p, 4.0));
	float bay = BAYER[bq.y * 4 + bq.x] / 16.0 - 0.5;
	float w = size.x - pad * 2.0;
	float xc = p.x + 0.5 - size.x * 0.5;  // 0 in the middle of the fall
	float y = p.y - top_pad;  // 0 at the lip, negative on the river above
	float t = TIME * speed;
	float fall = clamp(y / fall_h, 0.0, 1.0);
	vec4 col = vec4(0.0);
	bool done = false;

	// the river above, running into the lip: its own surface colour, fading in (dithered) from the
	// top so it melts into the river WaterLayer draws, with flow lines speeding up toward the edge
	if (y < 0.0) {
		float k = (y + top_pad) / top_pad;  // 0 at the top .. 1 at the lip
		float hw0 = w * 0.5 + 2.5 * (1.0 - k) + (vnoise(vec2(y * 0.3, 11.0)) - 0.5) * 1.5;
		float u0 = xc / hw0;
		float a0 = smoothstep(0.0, 0.75, k) * (1.0 - smoothstep(0.8, 1.0, abs(u0)));
		if (a0 + bay * 0.55 > 0.5) {
			vec3 c0 = c_surface.rgb;
			float lane0 = floor((xc + 64.0) / 2.0);
			float lh0 = hash(vec2(lane0, 3.0));
			float seg0 = fract((y * (1.0 + k) - t * (10.0 + lh0 * 6.0)) / (7.0 + lh0 * 5.0) + lh0 * 5.0);
			if (lh0 > 0.55 && seg0 < 0.3 + k * 0.25) c0 = mix(c0, c_light.rgb, 0.45 + k * 0.3);
			else if (lh0 < 0.2 && seg0 < 0.3) c0 = mix(c0, c_mid.rgb, 0.4);
			col = vec4(c0, 1.0);
		}
		done = true;
	}

	// sheet outline: draws in a little just below the lip, then spreads as it falls; the edges
	// waver all the way down
	float neck = 1.2 * smoothstep(2.0, 7.0, y) * (1.0 - smoothstep(0.15, 0.45, fall));
	float wob = (vnoise(vec2(y * 0.18 - t * 2.0, 3.0)) - 0.5) * (0.8 + 1.4 * fall);
	float hw = w * 0.5 - neck + fall * 1.5 + wob;
	float u = xc / hw;  // -1..1 across the sheet

	// droplets thrown off the sides
	if (!done && abs(u) >= 1.0 && abs(u) < 1.0 + 3.0 / hw && y > 4.0 && y < fall_h - 2.0) {
		vec2 dc = vec2(floor(xc), floor((y - t * 30.0) / 3.0));
		if (hash(dc + 4.4) < 0.07) {
			col = vec4(c_high.rgb, 0.9);
			done = true;
		}
	}

	// wet rock just outside the sheet
	if (!done && y < fall_h - 1.0 && abs(u) >= 1.0 && abs(xc) < hw + 2.0) {
		col = wet_rock;
		if (abs(xc) < hw + 1.0) col.a *= 1.4;
	}

	if (!done && abs(u) < 1.0 && y < fall_h + 2.0) {
		// rounded sheet lit from the upper left: highlight a third of the way in, shade on the right
		float nz = sqrt(max(1.0 - u * u, 0.0));
		float v = 0.13 + 0.36 * nz - 0.26 * u + 0.2 * exp(-pow((u + 0.4) / 0.16, 2.0));
		if (u > 0.82) v -= 0.12;  // the shaded far edge
		// long streaks in a few lanes, stretching as the water speeds up
		float lane_w = 2.0;
		float lane = floor((xc + 64.0) / lane_w);
		float lh = hash(vec2(lane, 7.0));
		float ys = pow(y + 1.0, 0.75) * 3.0;  // stretched coordinate: streaks lengthen lower down
		float sp = 9.0 + lh * 6.0;
		float seg = fract((ys - t * sp) / (10.0 + lh * 8.0) + lh * 3.0);
		if (lh > 0.5 && seg < 0.4) v += 0.2;
		else if (lh < 0.18 && seg < 0.3) v -= 0.12;
		// the lip: a glassy band where the water rolls over, bulging forward in the middle
		float bulge = (1.0 - u * u) * 1.4;
		if (y >= bulge && y < bulge + 2.0) v = max(v, 0.84 - (y - bulge) * 0.08 - max(u, 0.0) * 0.28);
		else if (y < bulge) v = 0.5 + 0.1 * (1.0 - abs(u));
		// aerated and white low down
		float air = smoothstep(0.68, 1.0, fall) * (0.5 + 0.5 * vnoise(vec2(xc * 0.45, ys * 0.35 - t * 4.0)));
		v += air * 0.45;
		v += bay * 0.06;
		vec3 c = v > 0.92 ? c_foam.rgb : v > 0.74 ? c_high.rgb : v > 0.52 ? c_light.rgb : v > 0.32 ? c_mid.rgb : c_deep.rgb;
		if (y < bulge) c = mix(c_surface.rgb, c_light.rgb, 0.35 + bay * 0.3);  // still the river's surface
		float a = abs(u) > 0.9 ? 0.82 : 1.0;  // the thin outer edge lets a little rock through
		col = vec4(c, a);
	}

	// at the foot: rings on the pool, a skirt of floating foam, then the foam mound on top
	vec2 d = vec2(xc, y - fall_h);
	if (!done && d.y > -10.0) {
		vec2 e = d / vec2(w * 0.5 + 4.0, 3.2);  // flattened: the pool is seen at an angle
		float r = length(e);
		for (int i = 0; i < 2; i++) {
			float rr = 1.15 + fract(t * 0.35 + float(i) * 0.5) * 1.1;
			if (d.y > 0.0 && abs(r - rr) * (w * 0.5 + 4.0) < 0.6) {
				col = vec4(c_high.rgb, 0.7 * (1.0 - (rr - 1.15) / 1.1));
			}
		}
		if (d.y > -1.0 && r < 1.25) {
			float f = vnoise(vec2(xc * 0.5 + t * 0.6, d.y * 0.9 - t * 0.4)) + bay * 0.2;
			if (f > 0.35 + r * 0.25) col = vec4(f > 0.72 ? c_foam.rgb : c_foam_shade.rgb, 1.0);
		}
		float pf = puffs(d, w, t);
		if (pf > 0.75) col = vec4(c_foam.rgb, 1.0);
		else if (pf > 0.0) col = vec4(c_foam_shade.rgb, 1.0);
	}
	COLOR = col;
}

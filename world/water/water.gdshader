// Pixel-art water for every water body on the map. One deep base colour, brought to life by
// slowly drifting sky reflections, wave lines with a shadowed trough, twinkling sun glints and
// lapping foam. The shore reads as a step down: along upper shores the earth bank face shows and
// throws a shadow on the water; elsewhere a thin translucent rim lets the wet bed show through,
// with caustics playing on it. Ground.gdshader draws the matching mud bed and damp ground.
// TEXTURE = Terrain.water_texture, one texel per cell: R = water, G = distance from the shore
// (0 at the shore, 1 = Terrain.water_depth_cells away). ground_data = Terrain's ground data
// (R = dirt/sand, B without G = sand), used to colour the bank face.
shader_type canvas_item;

uniform sampler2D ground_data : filter_linear;
uniform vec2 map_px = vec2(960.0, 480.0);
uniform float seed = 0.0;

group_uniforms colours;
uniform vec4 water_color : source_color = vec4(0.169, 0.420, 0.639, 1.0);  // open water
uniform vec4 clear_color : source_color = vec4(0.243, 0.580, 0.741, 1.0);  // clearer water nearer the shore
uniform float gradient_reach : hint_range(0.05, 1.0) = 0.7;  // how far in the clear blue fades to deep (1 = water_depth_cells)
uniform vec4 reflection_color : source_color = vec4(0.231, 0.502, 0.725, 1.0);  // sky in the water
uniform vec4 sky_color : source_color = vec4(0.384, 0.635, 0.812, 1.0);  // brightest bits of sky
uniform vec4 rim_color : source_color = vec4(0.318, 0.639, 0.718, 1.0);  // translucent shallow rim
uniform vec4 line_color : source_color = vec4(0.839, 0.949, 0.988, 1.0);
uniform vec4 caustic_color : source_color = vec4(0.627, 0.886, 0.906, 1.0);
uniform vec4 caustic_glow : source_color = vec4(0.420, 0.737, 0.851, 1.0);  // softer edge of the light
uniform vec4 foam_color : source_color = vec4(0.925, 0.976, 0.984, 1.0);
uniform vec4 glint_color : source_color = vec4(1.0, 0.988, 0.906, 1.0);
uniform vec4 bank_lip : source_color = vec4(0.169, 0.361, 0.180, 1.0);  // turf overhanging the bank
uniform vec4 bank_top : source_color = vec4(0.416, 0.329, 0.204, 1.0);  // earth bank face, lit lip
uniform vec4 bank_face : source_color = vec4(0.318, 0.247, 0.157, 1.0);
uniform vec4 bank_foot : source_color = vec4(0.212, 0.180, 0.129, 1.0);  // wet foot of the face
uniform vec4 sand_face : source_color = vec4(0.698, 0.592, 0.396, 1.0);

group_uniforms shore;
uniform float rim_width : hint_range(0.05, 1.0) = 0.42;  // how far in the translucent rim reaches
uniform float rim_opacity : hint_range(0.0, 1.0) = 0.42;  // opacity right at the waterline
uniform float bank_height = 4.0;  // px of earth face showing along upper shores
uniform float bank_shadow = 4.0;  // px of shadow the face throws on the water
uniform float foam_amount : hint_range(0.0, 1.0) = 0.7;
uniform float foam_speed = 1.0;

group_uniforms surface;
uniform vec2 drift = vec2(3.0, 0.0);  // px per second the wave lines and reflections travel
uniform float reflection_amount : hint_range(0.0, 1.0) = 0.6;
uniform float line_density : hint_range(0.0, 1.0) = 0.4;  // share of cells that hold a line
uniform vec2 line_spacing = vec2(24.0, 8.0);  // px between possible lines (x, y)
uniform float line_length = 11.0;  // px, longest line
uniform float line_life = 4.0;  // seconds a line takes to appear, stretch and fade
uniform float line_opacity : hint_range(0.0, 1.0) = 0.65;
uniform float sparkle : hint_range(0.0, 0.2) = 0.015;  // sun glints
uniform float ripple_rings : hint_range(0.0, 1.0) = 0.35;  // how often rings spread on the water
uniform float ring_size = 9.0;  // px, widest ring

group_uniforms sun;
uniform float sun_x : hint_range(0.0, 1.0) = 0.5;  // column position across the screen; it stays here as the camera moves
uniform float sun_length : hint_range(0.1, 1.0) = 0.9;  // how far down the screen the column reaches
uniform vec2 sun_width = vec2(0.17, 0.05);  // column half-width at the top and at the bottom, in screen widths
uniform float sun_glitter : hint_range(0.0, 1.0) = 0.85;
uniform float sparkle_density : hint_range(0.0, 1.0) = 0.9;
uniform vec4 sun_color : source_color = vec4(1.0, 0.988, 0.933, 1.0);  // sparkle cores
uniform vec4 sun_halo : source_color = vec4(0.749, 0.886, 0.949, 1.0);  // soft light around them
uniform vec4 sun_core : source_color = vec4(0.698, 0.863, 0.941, 1.0);  // water right under the sun
uniform vec4 sun_sheen : source_color = vec4(0.400, 0.667, 0.835, 1.0);  // water lit by the sun

group_uniforms caustics;
uniform float caustic_strength : hint_range(0.0, 1.0) = 0.8;
uniform float caustic_size = 14.0;  // px per caustic cell (the whole web scales with it)
uniform float caustic_reach : hint_range(0.05, 1.0) = 0.6;  // how far from the shore they show (1 = water_depth_cells)
uniform float caustic_speed = 0.8;

const float BAYER[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
#define DATA(p) texture(TEXTURE, ((p) + 0.5) / map_px)
// water presence smoothed over a few px (hides the cell grid), plus two octaves of edge wobble;
// ground.gdshader uses the identical test so the bed and wet strip line up with the water
#define WV(p) ((DATA(p).r * 2.0 + DATA((p) + vec2(3.0, 3.0)).r + DATA((p) + vec2(-3.0, 3.0)).r + DATA((p) + vec2(3.0, -3.0)).r + DATA((p) - vec2(3.0, 3.0)).r) / 6.0)
#define EDGE(p) (WV(p) + (vnoise(p, 13.0) - 0.5) * 0.3 + (vnoise((p) + 17.0, 5.0) - 0.5) * 0.2 + (vnoise((p) + 31.0, 2.5) - 0.5) * 0.1)

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21) + seed * 0.618);
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

vec2 hash2(vec2 p) {
	return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3))) + seed) * 43758.5453);
}

float vnoise(vec2 p, float cell) {
	vec2 f = p / cell;
	vec2 i = floor(f);
	vec2 t = f - i;
	t = t * t * (3.0 - 2.0 * t);
	float a = hash(i), b = hash(i + vec2(1.0, 0.0)), c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
	return a + (b - a) * t.x + (c - a) * t.y + (a - b - c + d) * t.x * t.y;
}

float bayer(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	return BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
}

// Distance to the nearest Voronoi cell border (F2 - F1); the sites drift with time.
float cell_border(vec2 p, float t) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float d1 = 8.0, d2 = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = hash2(i + g);
			o = 0.5 + 0.4 * vec2(sin(t + 6.2831 * o.x), sin(t * 0.8 + 6.2831 * o.y));
			float d = length(g + o - f);
			if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
		}
	}
	return d2 - d1;
}

// Caustics: light focused by the moving surface onto the bed. Two webs of cell borders, bent by
// a slowly drifting warp so the threads curve, with line widths that swell and pinch; where the
// webs cross the light gathers into bright knots.
float caustic(vec2 pix, float t) {
	float k = caustic_size / 22.0;  // the warp and width noise scale with the cells
	vec2 wp = pix + (vec2(vnoise(pix + vec2(t * 4.0 * k, 0.0), 17.0 * k), vnoise(pix + vec2(50.0, t * 3.0 * k), 17.0 * k)) - 0.5) * 9.0 * k;
	float w1 = 0.07 + 0.09 * vnoise(pix + vec2(9.0, t * 2.0 * k), 23.0 * k);
	float w2 = 0.07 + 0.08 * vnoise(pix + vec2(t * 2.0 * k, 40.0), 19.0 * k);
	float l1 = 1.0 - clamp(cell_border(wp / caustic_size, t) / w1, 0.0, 1.0);
	float l2 = 1.0 - clamp(cell_border(wp / (caustic_size * 0.71) + vec2(3.7, 1.3), t * 1.3 + 2.0) / w2, 0.0, 1.0);
	return l1 * 0.75 + l2 * 0.55;
}

// A sparse field of 1px horizontal wave lines carried by `drift`. Each line grows from its
// centre, holds, shrinks away, then reappears elsewhere in its cell. 1 = core, 0.5 = soft end.
float wave_line(vec2 pix) {
	vec2 q = pix - drift * TIME;
	float row = floor(q.y / line_spacing.y);
	q.x += hash(vec2(row, 3.1)) * line_spacing.x;  // stagger the rows
	vec2 cell = vec2(floor(q.x / line_spacing.x), row);
	float phase = TIME / line_life + hash(cell + 7.7);
	vec2 id = cell + floor(phase) * 17.3;
	if (hash(id) > line_density) {
		return 0.0;
	}
	vec2 local = q - cell * line_spacing;
	float cy = floor(1.0 + hash(id + 1.3) * (line_spacing.y - 2.0));
	if (floor(local.y) != cy) {
		return 0.0;
	}
	float env = sin(3.14159 * fract(phase));
	float half_len = floor(line_length * (0.45 + 0.55 * hash(id + 2.9)) * env * 0.5);
	float dx = abs(floor(local.x) - floor(line_spacing.x * (0.25 + 0.5 * hash(id + 4.1))));
	if (half_len < 1.0 || dx > half_len) {
		return 0.0;
	}
	return dx >= half_len - 0.5 && half_len >= 2.0 ? 0.5 : 1.0;
}

// Ripple rings: now and then a flattened ring spreads from a point and fades (1 = bright, 0.5 = faint).
float ring(vec2 pix, float t) {
	float acc = 0.0;
	for (int i = 0; i < 2; i++) {
		vec2 off = vec2(float(i) * 23.0, float(i) * 17.0);
		vec2 cell = floor((pix + off) / 44.0);
		float phase = t / 2.6 + hash(cell + 5.5 + float(i));
		vec2 id = cell + floor(phase) * 11.3;
		if (hash(id + 0.7) > ripple_rings) continue;
		vec2 c = cell * 44.0 - off + 8.0 + hash2(id) * 28.0;
		float f = fract(phase);
		float r = 1.5 + f * ring_size;
		vec2 d = (pix - floor(c)) * vec2(1.0, 1.7);  // seen from above at an angle: flattened
		float e = abs(length(d) - r);
		if (e < 0.6 && hash(pix + floor(t * 6.0)) > f * 0.8) acc = max(acc, f < 0.45 ? 1.0 : 0.5);
		else if (e < 0.6 + 1.0 && f < 0.3 && length(d) < r) acc = max(acc, 0.25);  // the dip inside
	}
	return acc;
}

// Strength of the sun's glitter path at a pixel (0..1): a column hanging from the top of the
// screen at sun_x, wide and strong near the top, narrowing and fading downwards, edges wavering.
float sun_path(vec2 pix, vec2 suv, float t) {
	float v = suv.y / sun_length;
	if (v > 1.0) return 0.0;
	float wob = (vnoise(vec2(pix.y * 0.8, t * 6.0), 9.0) - 0.5) * 0.05 + (vnoise(vec2(pix.y, 40.0 + t * 3.0), 3.0) - 0.5) * 0.02;
	float half_w = mix(sun_width.x, sun_width.y, pow(v, 0.8));
	float dx = (suv.x - sun_x + wob) / half_w;
	float across = exp(-dx * dx * 1.6);
	float along = mix(1.0, 0.3, v) * (1.0 - smoothstep(0.75, 1.0, v));
	return clamp(across * along * sun_glitter, 0.0, 1.0);
}

// Round sun sparkles: each one swells and dies in a moment. Big ones (only in the bright path)
// have a white core, a soft halo and four short star points; small ones are a single bright
// pixel, which also turn up sparsely outside the path. 1 = core, 0.5 = inner glow, 0.2 = halo.
float sun_sparkles(vec2 pix, float path, float t) {
	float best = 0.0;
	vec2 cs = vec2(7.0, 5.0);
	vec2 base = floor(pix / cs);
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 cell = base + vec2(float(x), float(y));
			float phase = t * (1.4 + hash(cell + 3.3) * 1.6) + hash(cell + 8.1) * 9.0;
			vec2 id = cell + floor(phase) * 13.7;
			float roll = hash(id + 0.4);
			float chance = path * (0.25 + path) * sparkle_density + 0.004;
			if (roll > chance) continue;
			float env = sin(3.14159 * fract(phase));
			vec2 c = floor(cell * cs + 1.0 + hash2(id) * (cs - 2.0));
			// bigger sparkles where the path is strongest
			float size = (roll < chance * 0.22 && path > 0.3) ? 2.6 : (roll < chance * 0.55 && path > 0.12) ? 1.4 : 0.5;
			size *= env;
			vec2 d = pix - c;
			float r = length(d);
			float v = 0.0;
			if (r <= size * 0.6) v = 1.0;
			else if (r <= size) v = 0.5;
			else if (r <= size + 1.3 && size > 1.0) v = 0.2;
			if (size > 1.6 && env > 0.6 && (d.x == 0.0 || d.y == 0.0) && r <= size + 2.5) v = max(v, 0.5);
			best = max(best, v);
		}
	}
	return best;
}

// Sun glints: tiny stars that flare and die, gathered in slowly wandering patches of glitter.
float glint(vec2 pix, float t) {
	vec2 cell = floor(pix / 5.0);
	float phase = t * 1.3 + hash(cell + 2.2) * 7.0;
	vec2 id = cell + floor(phase) * 9.7;
	float patch = smoothstep(0.5, 0.85, vnoise(pix + vec2(t * 5.0, t * 1.5), 34.0));
	if (hash(id) > sparkle * patch * 4.0) {
		return 0.0;
	}
	vec2 l = pix - cell * 5.0 - 2.0;
	float k = sin(3.14159 * fract(phase));
	float r = abs(l.x) + abs(l.y);
	if (r < 0.5) return k > 0.25 ? 1.0 : 0.0;
	if (r < 1.5 && (l.x == 0.0 || l.y == 0.0)) return k > 0.7 ? 0.6 : 0.0;
	return 0.0;
}

void fragment() {
	vec2 pix = floor(UV * map_px);
	float bay = bayer(pix);
	vec4 w = DATA(pix);
	float edge = EDGE(pix);
	if (edge < 0.5) {
		discard;
	}
	float t = TIME;
	bool sandy = texture(ground_data, (pix + 0.5) / map_px).r > 0.4;

	// how far below the land above this pixel is: k = 1 means the pixel right above is land
	float face_h = bank_height + (vnoise(vec2(pix.x, 0.0), 6.0) > 0.55 ? 1.0 : 0.0) - (vnoise(vec2(pix.x, 9.0), 4.0) > 0.8 ? 1.0 : 0.0);
	float k_land = 99.0;
	for (int k = 1; k <= 9; k++) {
		if (float(k) > face_h + bank_shadow) break;
		vec2 q = pix - vec2(0.0, float(k));
		if (EDGE(q) < 0.5) {
			k_land = float(k);
			break;
		}
	}
	// the earth bank face along upper shores: lit lip, face, dark wet foot
	if (k_land <= face_h) {
		vec3 c;
		if (sandy) {
			c = sand_face.rgb * (k_land <= 1.0 ? 1.0 : k_land >= face_h ? 0.72 : 0.86);
		} else {
			c = k_land <= 1.0 ? bank_lip.rgb : k_land <= 2.0 ? bank_top.rgb : k_land >= face_h ? bank_foot.rgb : bank_face.rgb;
			if (k_land <= 1.0 && hash(pix + 5.0) < 0.3) c = bank_top.rgb;  // roots poking through the turf
			if (k_land > 1.0 && k_land < face_h && hash(pix * 0.91) < 0.12) c *= 0.85;  // grit
		}
		COLOR = vec4(c, 1.0);
	} else {
		// 0 at the waterline; the depth term keeps open water solid wherever the edge noise dips
		float rim = smoothstep(0.5, 0.5 + rim_width, edge + bay * 0.06 + max(w.g - 0.1, 0.0) * 5.0);
		// a gentle gradient from clear blue near the shore to the deep blue of open water, dithered
		float g = smoothstep(0.0, gradient_reach, w.g) + bay * 0.16;
		g = floor(clamp(g, 0.0, 1.0) * 5.0 + 0.5) / 5.0;
		vec3 col = mix(clear_color.rgb, water_color.rgb, g);

		// sky reflections: long soft lighter patches drifting slowly, dithered into the base colour
		float refl = vnoise((pix - drift * t * 0.6) * vec2(0.45, 1.3), 18.0) * 0.7 + vnoise(pix * vec2(0.6, 1.6) + vec2(t * 1.5, 0.0), 9.0) * 0.3;
		float rv = refl + bay * 0.18;
		if (rv > 1.0 - reflection_amount * 0.32) col = mix(col, sky_color.rgb, 0.8);
		else if (rv > 1.0 - reflection_amount * 0.62) col = mix(col, reflection_color.rgb, 0.7);

		// the translucent rim: lighter, see-through water over the wet bed (ground.gdshader)
		float a = 1.0;
		if (rim < 1.0) {
			float s = rim + bay * 0.3;
			col = s < 0.35 ? rim_color.rgb : s < 0.7 ? mix(rim_color.rgb, col, 0.5) : col;
			a = s < 0.35 ? rim_opacity : s < 0.7 ? mix(rim_opacity, 1.0, 0.5) : 1.0;
		}

		// caustics: thin lines of light playing on the bed in the shallow water
		float ct = t * caustic_speed;
		float c = caustic(pix, ct);
		float near = 1.0 - smoothstep(caustic_reach * 0.35, caustic_reach, w.g + (vnoise(pix, 9.0) - 0.5) * 0.12);
		float cv = near + bay * 0.6 > 0.35 ? c : 0.0;  // the web dissolves towards open water
		if (cv > 0.95) {  // knots where the threads cross
			col = mix(col, caustic_color.rgb, caustic_strength);
			a = max(a, 0.9);
		} else if (cv > 0.45) {  // the threads
			col = mix(col, caustic_glow.rgb, caustic_strength * 0.85);
			a = max(a, 0.75);
		}

		// shadow thrown by the bank face
		if (k_land < 99.0) {
			float sh = (k_land - face_h) / bank_shadow + bay * 0.35;
			if (sh < 0.75) col *= 0.78;
		}

		// waves: drifting lines with a darker trough just below each one
		if (rim > 0.6) {
			float l = wave_line(pix);
			if (l > 0.0) col = mix(col, line_color.rgb, line_opacity * (l > 0.75 ? 1.0 : 0.45));
			else if (wave_line(pix - vec2(0.0, 1.0)) > 0.75) col *= 0.88;
		}

		// ripple rings
		if (rim > 0.7) {
			float rr = ring(pix, t);
			if (rr > 0.9) col = mix(col, line_color.rgb, 0.6);
			else if (rr > 0.4) col = mix(col, line_color.rgb, 0.3);
			else if (rr > 0.0) col *= 0.93;
		}

		// lapping foam: a broken line that creeps up the shore and slides back
		float lap = 0.16 + 0.12 * sin(t * 1.6 * foam_speed + vnoise(pix, 22.0) * 6.28);
		float fn = vnoise(pix + vec2(t * 3.0 * foam_speed, 0.0), 4.0);
		if (rim > lap - 0.12 && rim < lap && fn > 1.0 - foam_amount * 0.75) {
			col = mix(col, foam_color.rgb, 0.75);
			a = 1.0;
		} else if (rim < 0.08 && fn > 1.0 - foam_amount * 0.5) {
			col = mix(col, foam_color.rgb, 0.4);
		}

		// sun glints on open water
		float gl = rim > 0.8 ? glint(pix, t) : 0.0;
		if (gl > 0.0) col = mix(col, glint_color.rgb, gl);

		// the sun on the water: a column of glitter running down from the top of the screen
		// (it stays put as the camera moves). Bright and wide near the sun, narrowing and fading
		// below; wave crests in it shine as streaks, and round sparkles with halos and star
		// points flicker along it, thinning out to the odd speck outside.
		float sun = sun_path(pix, SCREEN_UV, t) * smoothstep(0.4, 0.9, rim);
		if (sun > 0.0) {
			float sv = sun + bay * 0.45;
			if (sv > 0.9) col = mix(col, sun_core.rgb, 0.85);
			else if (sv > 0.6) col = mix(col, sun_core.rgb, 0.45);
			else if (sv > 0.35) col = mix(col, sun_sheen.rgb, 0.6);
			else if (sv > 0.18) col = mix(col, sun_sheen.rgb, 0.3);
			float crest = sin(pix.y * 1.25 + vnoise(pix * vec2(0.35, 1.0) + vec2(t * 2.5, 0.0), 7.0) * 7.0 - t * 2.2);
			float brk = vnoise(pix * vec2(0.7, 1.0) + vec2(-t * 6.0, 0.0), 3.0);
			if (crest > 0.9 && brk > 1.0 - sun * 0.45) col = mix(col, sun > 0.6 ? sun_color.rgb : sun_halo.rgb, 0.8);
			else if (crest > 0.75 && brk > 1.0 - sun * 0.4) col = mix(col, sun_halo.rgb, 0.4);
		}
		float sp = sun_sparkles(pix, sun_path(pix, SCREEN_UV, t), t);
		if (rim > 0.6) {
			if (sp > 0.75) col = sun_color.rgb;
			else if (sp > 0.4) col = mix(col, sun_color.rgb, 0.7);
			else if (sp > 0.0) col = mix(col, sun_halo.rgb, 0.65);
		}

		COLOR = vec4(col, a);
	}
}

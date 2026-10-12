// Pixel-art water for every water body on the map: one flat colour, a few plain wave lines
// drifting across it, and fine caustics near the shore.
// TEXTURE = Terrain.water_texture, one texel per cell: R = water, G = distance from the shore
// (0 at the shore, 1 = Terrain.water_depth_cells away). ground_data = Terrain's ground data
// (R = dirt/sand), used to pick the shore style: wet sand next to beaches, a dark bank by grass.
shader_type canvas_item;

uniform sampler2D ground_data : filter_linear;
uniform vec2 map_px = vec2(960.0, 480.0);
uniform float seed = 0.0;

group_uniforms colours;
uniform vec4 water_color : source_color = vec4(0.169, 0.420, 0.639, 1.0);
uniform vec4 line_color : source_color = vec4(0.839, 0.949, 0.988, 1.0);
uniform vec4 caustic_color : source_color = vec4(0.627, 0.851, 0.922, 1.0);
uniform vec4 bank : source_color = vec4(0.157, 0.290, 0.204, 1.0);
uniform vec4 wet_sand : source_color = vec4(0.706, 0.580, 0.384, 1.0);

group_uniforms waves;
uniform vec2 drift = vec2(3.0, 0.0);  // px per second the wave lines travel
uniform float line_density : hint_range(0.0, 1.0) = 0.35;  // share of cells that hold a line
uniform vec2 line_spacing = vec2(26.0, 9.0);  // px between possible lines (x, y)
uniform float line_length = 10.0;  // px, longest line
uniform float line_life = 4.0;  // seconds a line takes to appear, stretch and fade
uniform float line_opacity : hint_range(0.0, 1.0) = 0.55;

group_uniforms caustics;
uniform float caustic_strength : hint_range(0.0, 1.0) = 0.6;
uniform float caustic_size = 11.0;  // px per caustic cell
uniform float caustic_reach : hint_range(0.05, 1.0) = 0.4;  // how far from the shore they show
uniform float caustic_speed = 1.0;

#define DATA(p) texture(TEXTURE, ((p) + 0.5) / map_px)

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

// Animated Voronoi edges: bright where two cells meet, the web of caustic light.
float caustic_layer(vec2 p, float t) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float d1 = 8.0, d2 = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = hash2(i + g);
			o = 0.5 + 0.42 * sin(t + 6.2831 * o);
			vec2 r = g + o - f;
			float d = dot(r, r);
			if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
		}
	}
	return 1.0 - smoothstep(0.0, 0.12, sqrt(d2) - sqrt(d1));
}

// A sparse field of 1px horizontal lines carried by `drift`. Each line grows from its centre,
// holds, shrinks away, then reappears somewhere else in its cell.
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
	float cx = line_spacing.x * (0.25 + 0.5 * hash(id + 4.1));
	return abs(floor(local.x) - floor(cx)) <= half_len && half_len >= 1.0 ? 1.0 : 0.0;
}

void fragment() {
	vec2 pix = floor(UV * map_px);
	vec4 w = DATA(pix);
	float edge = w.r + (vnoise(pix, 7.0) - 0.5) * 0.36;
	if (edge < 0.5) {
		discard;
	}
	float shore = smoothstep(0.5, 0.8, edge);  // 0 at the waterline, 1 a few px in
	vec3 col = water_color.rgb;

	// caustics: thin lines of light in the shallow rim, fading out towards open water
	float t = TIME * caustic_speed;
	vec2 cp = (pix + vec2(t * 2.0, t * 1.3)) / caustic_size;
	float c = max(caustic_layer(cp, t * 1.1), caustic_layer(cp * 1.43 + 3.7, t * 1.45 + 2.0) * 0.85);
	float near = 1.0 - smoothstep(caustic_reach * 0.4, caustic_reach, w.g + (vnoise(pix, 9.0) - 0.5) * 0.15);
	float cf = c * near * smoothstep(0.1, 0.45, shore);
	if (cf > 0.8) col = mix(col, caustic_color.rgb, caustic_strength);

	// waves: a few plain lines drifting across
	if (shore > 0.5 && wave_line(pix) > 0.5) col = mix(col, line_color.rgb, line_opacity);

	// the shore itself: wet sand next to beaches, a dark undercut bank line next to grass
	float sand = texture(ground_data, (pix + 0.5) / map_px).r;
	if (sand > 0.4) {
		if (shore < 0.14) col = mix(wet_sand.rgb, col, 0.3);
	} else if (shore < 0.07) {
		col = bank.rgb;
	} else if (shore < 0.15) {
		col = mix(col, bank.rgb, 0.35);
	}

	COLOR = vec4(col, 1.0);
}

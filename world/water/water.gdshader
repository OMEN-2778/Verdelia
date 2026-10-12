// Clear, rippling pixel-art water for every water body on the map (lakes, ponds, rivers, rapids).
// TEXTURE = Terrain.water_texture, one texel per cell: R = water, G = depth (0 at the shore),
// B/A = flow direction * speed (0.5 = still). ground_data = Terrain's ground data (R = dirt/sand),
// used to pick the shore style: a dark wet bank next to grass, wet sand next to beaches.
//
// Layers: sandy/pebbly bed + moving caustics -> depth absorption (clear shallows, blue deeps) ->
// highlight ripples (across the flow) and glints -> waterline foam and waves lapping the shore ->
// white water where the flow is fast. Colours are quantised with Bayer dithering.
shader_type canvas_item;

uniform sampler2D ground_data : filter_linear;
uniform vec2 map_px = vec2(960.0, 480.0);
uniform float seed = 0.0;

group_uniforms colours;
uniform vec4 shoal : source_color = vec4(0.506, 0.835, 0.784, 1.0);  // sand showing through
uniform vec4 shallow : source_color = vec4(0.380, 0.784, 0.835, 1.0);
uniform vec4 mid : source_color = vec4(0.243, 0.600, 0.776, 1.0);
uniform vec4 deep : source_color = vec4(0.169, 0.420, 0.639, 1.0);
uniform vec4 bed_light : source_color = vec4(0.890, 0.835, 0.620, 1.0);
uniform vec4 bed_dark : source_color = vec4(0.729, 0.659, 0.459, 1.0);
uniform vec4 pebble : source_color = vec4(0.541, 0.580, 0.533, 1.0);
uniform vec4 highlight : source_color = vec4(0.839, 0.949, 0.988, 1.0);
uniform vec4 foam : source_color = vec4(0.957, 0.988, 1.0, 1.0);
uniform vec4 bank : source_color = vec4(0.157, 0.290, 0.204, 1.0);
uniform vec4 wet_sand : source_color = vec4(0.706, 0.580, 0.384, 1.0);

group_uniforms look;
uniform float clarity : hint_range(0.0, 1.0) = 0.8;  // how clearly the bed shows in the shallows
uniform float wave_speed = 1.0;
uniform float wave_density : hint_range(0.0, 1.0) = 0.5;
uniform float flow_px = 16.0;  // px per second at full flow speed
uniform float caustic_strength : hint_range(0.0, 2.0) = 1.0;
uniform float caustic_size = 13.0;  // px per caustic cell
uniform float shore_waves : hint_range(0.0, 2.0) = 1.0;
uniform float rapids_threshold : hint_range(0.0, 1.0) = 0.72;
uniform float sparkle : hint_range(0.0, 0.05) = 0.005;

const float BAYER[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
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

float bayer(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	return BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
}

// Animated Voronoi edges: bright where two cells meet, the classic web of caustic light.
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
	return 1.0 - smoothstep(0.0, 0.16, sqrt(d2) - sqrt(d1));
}

void fragment() {
	vec2 pix = floor(UV * map_px);
	float bay = bayer(pix);
	vec4 w = DATA(pix);
	float edge = w.r + (vnoise(pix, 7.0) - 0.5) * 0.36 + bay * 0.08;
	if (edge < 0.5) {
		discard;
	}
	float t = TIME * wave_speed;
	float shore = smoothstep(0.5, 0.8, edge);  // 0 at the waterline, 1 a few px in
	// depth eases in quickly so narrow streams still read as water, wide lakes get dark centres
	float depth = clamp(1.0 - pow(1.0 - w.g, 1.7) + (vnoise(pix, 10.0) - 0.5) * 0.08, 0.0, 1.0);
	vec2 flow = (w.ba - 0.5) * 2.0;
	float speed = length(flow);
	// ripples lie across real currents; on still water (only a light drift) they stay horizontal
	vec2 dir = speed > 0.3 ? flow / speed : vec2(0.0, 1.0);
	vec2 adv = pix - flow * TIME * flow_px;  // texture coordinates carried by the current

	// depth bands: flat colours with wandering edges, like contour lines on a map
	float dn = depth + (vnoise(pix, 9.0) - 0.5) * 0.14 + (vnoise(pix + vec2(t * 1.5, t * 0.6), 22.0) - 0.5) * 0.05;
	int band = dn < 0.14 ? 0 : dn < 0.36 ? 1 : dn < 0.62 ? 2 : 3;
	vec3 BANDS[4] = vec3[4](shoal.rgb, shallow.rgb, mid.rgb, deep.rgb);
	vec3 col = BANDS[band];

	// the bed shows through the two shallow bands: sand ripple marks and pebbles
	if (band <= 1) {
		float ripple_marks = sin(pix.y * 0.9 + vnoise(pix, 8.0) * 6.0);
		float k = band == 0 ? 0.5 : 0.25;
		if (ripple_marks > 0.7) col = mix(col, bed_light.rgb, k * 0.6);
		else if (ripple_marks < -0.75) col = mix(col, bed_dark.rgb, k);
		float hp = hash(floor(pix / vec2(2.0, 1.0)) + 17.0);
		if (hp < 0.03) col = mix(col, pebble.rgb, k * 1.2);
		col = mix(col, mix(bed_dark.rgb, bed_light.rgb, step(0.5, vnoise(pix, 11.0))) * vec3(0.85, 1.02, 1.0), clarity * k * 0.4);
	}

	// caustics: crisp lines of light on the bed, strongest in the shallows
	vec2 cp = (adv + vec2(t * 2.0, t * 1.3)) / caustic_size;
	float c = max(caustic_layer(cp, t * 1.1), caustic_layer(cp * 1.43 + 3.7, t * 1.45 + 2.0) * 0.9);
	float cfade = float(3 - band) / 3.0 * caustic_strength * smoothstep(0.05, 0.4, shore);
	if (c * cfade > 0.8) col = mix(col, vec3(1.0, 1.0, 0.94), 0.6);
	else if (c * cfade > 0.6) col = mix(col, vec3(0.94, 1.0, 0.98), 0.28);


	// ripples: short highlight dashes lying across the flow (horizontal on still water)
	vec2 across = vec2(-dir.y, dir.x);
	float along = dot(pix, dir) - TIME * flow_px * (speed > 0.3 ? speed : 0.0);
	float side = dot(pix, across);
	float rip = sin(along * 0.62 + vnoise(vec2(side, along) * 0.5, 9.0) * 5.0 + t * 1.4);
	float mask = vnoise(vec2(side * 0.5, along) + vec2(t * 2.0, 0.0), 7.0);
	float dash = vnoise(vec2(side, along * 3.0) + vec2(t * 3.0, 0.0), 4.0);  // break lines into short dashes
	if (rip > 0.94 && mask > 1.0 - wave_density * 0.75 && dash > 0.45) col = mix(col, highlight.rgb, 0.7);
	else if (rip < -0.96 && mask > 0.6 && dash > 0.5) col *= 0.92;

	// glints: brief 2px flashes on open water
	vec2 gcell = floor(pix / vec2(2.0, 1.0));
	if (hash(gcell + floor(t * 2.5 + hash(gcell) * 3.0) * 13.1) < sparkle * depth) col = foam.rgb;

	// waves lapping the shore (still water only) and a broken, thin foam line at the waterline
	float still = 1.0 - smoothstep(0.2, 0.45, speed);
	float lap = sin(shore * 9.0 + depth * 30.0 - t * 2.2 + vnoise(pix, 14.0) * 4.0);
	if (depth < 0.2 * shore_waves && lap > 0.9 && vnoise(pix + vec2(t * 4.0, 0.0), 5.0) > 0.5 && still > 0.5) col = mix(col, foam.rgb, 0.55);
	if (shore < 0.22 && shore > 0.1 && vnoise(pix + vec2(0.0, t * 2.0), 3.0) > 0.66) col = mix(col, foam.rgb, 0.55);

	// white water where the river runs fast
	if (speed > rapids_threshold) {
		float rf = vnoise(vec2(dot(adv, dir) * 0.35, dot(pix, across) * 1.2), 3.0) + bay * 0.2;
		float amount = smoothstep(rapids_threshold, 1.0, speed);
		if (rf > 1.0 - amount * 0.55) col = mix(col, foam.rgb, 0.85);
	}

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

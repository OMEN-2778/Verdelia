// Procedural ground for the whole map, ported from stardust-vale's arena painter.
// The sprite's TEXTURE is the terrain data (one texel per cell, linear filtered):
//   R = bare dirt / path, G = tilled soil, B = watered, A = 0 where the ground is paved
//   (A = 0 with R = 1: wooden floorboards, with G = 1: stone flags, with both: outside the rooms,
//   black; floors keep hard cell edges).
// Grass is two value-noise octaves + 4x4 Bayer dithering; dirt and tilled soil get organic,
// dithered edges from noise, paths are lighter where worn, tilled soil is drawn as mounded rows.
// Paving is a brick road laid by hand: rows that wander a little, bricks of uneven length with
// rounded corners, several kinds of stone, grain, cracks, a trodden middle, moss in the joints,
// and an edge where the bricks thin out, sink and go missing into the grass.
// water_data (Terrain.water_texture) adds the wet bed under the water's translucent rim, a strip
// of wet mud or wet sand at the waterline and darker, lusher damp grass around it.
shader_type canvas_item;

uniform vec2 map_px = vec2(426.0, 240.0);
uniform float seed = 0.0;

group_uniforms grass;
uniform vec4 grass0 : source_color = vec4(0.247, 0.561, 0.247, 1.0);
uniform vec4 grass1 : source_color = vec4(0.333, 0.655, 0.282, 1.0);
uniform vec4 grass2 : source_color = vec4(0.435, 0.749, 0.333, 1.0);
uniform vec4 grass3 : source_color = vec4(0.561, 0.820, 0.408, 1.0);

group_uniforms dirt;
uniform vec4 dirt0 : source_color = vec4(0.541, 0.416, 0.243, 1.0);
uniform vec4 dirt1 : source_color = vec4(0.655, 0.514, 0.310, 1.0);
uniform vec4 dirt2 : source_color = vec4(0.765, 0.616, 0.388, 1.0);
uniform vec4 dirt3 : source_color = vec4(0.847, 0.710, 0.478, 1.0);

group_uniforms sand;
uniform vec4 sand0 : source_color = vec4(0.757, 0.651, 0.443, 1.0);
uniform vec4 sand1 : source_color = vec4(0.851, 0.761, 0.553, 1.0);
uniform vec4 sand2 : source_color = vec4(0.914, 0.843, 0.651, 1.0);
uniform vec4 sand3 : source_color = vec4(0.957, 0.910, 0.749, 1.0);

group_uniforms tilled;
uniform vec4 till0 : source_color = vec4(0.373, 0.267, 0.157, 1.0);
uniform vec4 till1 : source_color = vec4(0.478, 0.353, 0.212, 1.0);
uniform vec4 till2 : source_color = vec4(0.584, 0.447, 0.278, 1.0);
uniform vec4 till3 : source_color = vec4(0.710, 0.553, 0.345, 1.0);
uniform vec4 till4 : source_color = vec4(0.824, 0.671, 0.439, 1.0);
uniform float wet_darken = 0.68;

group_uniforms detail;
uniform vec4 blade_dark : source_color = vec4(0.208, 0.478, 0.212, 1.0);
uniform vec4 blade_light : source_color = vec4(0.651, 0.871, 0.447, 1.0);
uniform float blade_density = 0.0028;
uniform float pebble_density = 0.0005;
uniform float ridge_period = 8.0;

group_uniforms water_edge;
uniform sampler2D water_data : filter_linear;
uniform bool has_water = false;
uniform vec4 mud0 : source_color = vec4(0.235, 0.204, 0.141, 1.0);  // bed under the shallows
uniform vec4 mud1 : source_color = vec4(0.318, 0.275, 0.180, 1.0);
uniform vec4 mud2 : source_color = vec4(0.396, 0.341, 0.224, 1.0);  // wet mud at the waterline
uniform vec4 damp : source_color = vec4(0.176, 0.396, 0.235, 1.0);  // damp grass near water
uniform float damp_reach = 12.0;  // px of damp ground around the water
uniform float wet_sand_darken = 0.78;

group_uniforms paving;
uniform float brick_row = 5.0;  // px per row of bricks
uniform float brick_len = 8.0;  // mean brick length, px
uniform vec4 joint0 : source_color = vec4(0.333, 0.294, 0.247, 1.0);
uniform vec4 joint1 : source_color = vec4(0.416, 0.373, 0.318, 1.0);
uniform vec4 joint_moss : source_color = vec4(0.275, 0.420, 0.216, 1.0);

group_uniforms floors;
uniform float board_h = 4.0;  // px per floorboard
uniform vec4 void_colour : source_color = vec4(0.055, 0.047, 0.067, 1.0);
uniform vec4 board0 : source_color = vec4(0.478, 0.341, 0.227, 1.0);  // gaps between boards
uniform vec4 board1 : source_color = vec4(0.635, 0.478, 0.329, 1.0);
uniform vec4 board2 : source_color = vec4(0.682, 0.525, 0.369, 1.0);
uniform vec4 board3 : source_color = vec4(0.725, 0.573, 0.408, 1.0);
uniform vec4 board4 : source_color = vec4(0.769, 0.624, 0.455, 1.0);
uniform float flag_row = 7.0;  // px per row of stone flags
uniform vec4 flag_joint : source_color = vec4(0.471, 0.443, 0.420, 1.0);

const float BAYER[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21) + seed * 0.618);
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float vnoise(vec2 p, float cell) {
	vec2 f = p / cell;
	vec2 i = floor(f);
	vec2 t = f - i;
	t = t * t * (3.0 - 2.0 * t);
	float a = hash(i), b = hash(i + vec2(1.0, 0.0)), c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
	return a + (b - a) * t.x + (c - a) * t.y + (a - b - c + d) * t.x * t.y;
}

// stone families for the bricks (dark .. light): warm grey, beige, ochre, cool grey, old red brick
const vec3 STONE[20] = vec3[20](
	vec3(0.420, 0.392, 0.357), vec3(0.533, 0.498, 0.451), vec3(0.635, 0.596, 0.537), vec3(0.733, 0.698, 0.635),
	vec3(0.475, 0.408, 0.322), vec3(0.588, 0.514, 0.416), vec3(0.690, 0.616, 0.502), vec3(0.788, 0.718, 0.596),
	vec3(0.494, 0.384, 0.282), vec3(0.604, 0.478, 0.353), vec3(0.702, 0.569, 0.424), vec3(0.788, 0.663, 0.514),
	vec3(0.373, 0.384, 0.392), vec3(0.475, 0.486, 0.490), vec3(0.573, 0.584, 0.584), vec3(0.678, 0.682, 0.675),
	vec3(0.478, 0.329, 0.275), vec3(0.580, 0.400, 0.337), vec3(0.678, 0.482, 0.408), vec3(0.765, 0.576, 0.494));

float joint_at(float k, float row, float len) {
	return k * len + floor((hash(vec2(k, row) + 0.31) - 0.5) * len * 0.6);
}

float bayer(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	return BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
}

// terrain data at a pixel (a macro: builtin samplers cannot be passed to functions)
#define DATA(p) texture(TEXTURE, ((p) + 0.5) / map_px)
#define WATER(p) texture(water_data, ((p) + 0.5) / map_px).r
// same smoothed water edge as water.gdshader
#define WV(p) ((WATER(p) * 2.0 + WATER((p) + vec2(3.0, 3.0)) + WATER((p) + vec2(-3.0, 3.0)) + WATER((p) + vec2(3.0, -3.0)) + WATER((p) - vec2(3.0, 3.0))) / 6.0)
#define WEDGE(p) (WV(p) + (vnoise(p, 13.0) - 0.5) * 0.3 + (vnoise((p) + 17.0, 5.0) - 0.5) * 0.2 + (vnoise((p) + 31.0, 2.5) - 0.5) * 0.1)

void fragment() {
	vec2 pix = floor(UV * map_px);
	float bay = bayer(pix);
	float t = vnoise(pix, 30.0) * 0.78 + vnoise(pix, 8.0) * 0.22 + bay * 0.11;
	vec4 col = t < 0.3 ? grass0 : t < 0.54 ? grass1 : t < 0.74 ? grass2 : grass3;
	// static blade strokes (2px dark, 1px light tip) and the odd pebble, as in the original
	float h0 = hash(pix * 1.31 + 7.0), h1 = hash((pix - vec2(0.0, 1.0)) * 1.31 + 7.0), hl = hash((pix + vec2(0.0, 1.0)) * 1.31 + 7.0);
	if (h0 < blade_density || h1 < blade_density) col = blade_dark;
	else if (hl < blade_density) col = blade_light;
	float hp = hash(floor(pix / vec2(3.0, 1.0)) * 2.17 + 3.0);
	if (hp < pebble_density) col = mod(pix.x, 3.0) < 1.0 ? vec4(0.851, 0.839, 0.769, 1.0) : vec4(0.616, 0.604, 0.533, 1.0);
	else if (hash(floor((pix - vec2(1.0, 1.0)) / vec2(3.0, 1.0)) * 2.17 + 3.0) < pebble_density) col.rgb *= 0.72;

	vec4 d = DATA(pix);
	vec4 cell = texelFetch(TEXTURE, ivec2(floor(UV * vec2(textureSize(TEXTURE, 0)))), 0);  // unblended, for floors
	vec3 soil = d.rgb * d.a;  // paving and floors (A = 0) carry no soil
	// dirt and paths
	float edge = soil.r + (vnoise(pix, 11.0) - 0.5) * 0.42 + bay * 0.12;
	if (edge > 0.5) {
		float around = (DATA(pix + vec2(5.0, 0.0)).r + DATA(pix - vec2(5.0, 0.0)).r
			+ DATA(pix + vec2(0.0, 5.0)).r + DATA(pix - vec2(0.0, 5.0)).r) * 0.25;
		float wear = smoothstep(0.6, 1.0, min(d.r, around));
		float v = 0.38 + wear * 0.24 + (vnoise(pix, 6.0) - 0.5) * 0.5 - (edge < 0.58 ? 0.25 : 0.0) + bay * 0.25;
		vec4 D[4] = vec4[4](dirt0, dirt1, dirt2, dirt3);
		col = D[clamp(int(v * 4.0), 0, 3)];
		if (soil.b > 0.5 && soil.g < 0.5) {  // beach sand: lighter, finer, the odd shell or pebble
			vec4 S[4] = vec4[4](sand0, sand1, sand2, sand3);
			float sv = 0.45 + (vnoise(pix, 5.0) - 0.5) * 0.5 + (vnoise(pix, 17.0) - 0.5) * 0.3 + bay * 0.3 - (edge < 0.58 ? 0.2 : 0.0);
			col = S[clamp(int(sv * 4.0), 0, 3)];
			float hs = hash(pix * 0.73 + 11.0);
			if (hs < 0.004) col = vec4(1.0, 0.96, 0.92, 1.0);
			else if (hs < 0.008) col = vec4(0.62, 0.58, 0.52, 1.0);
		}
	}
	// tilled soil: mounded rows, lit on top, shadowed in the furrow; watered soil is darker
	float tg = soil.g + (vnoise(pix + 77.0, 9.0) - 0.5) * 0.28 + bay * 0.08;
	if (tg > 0.5) {
		float u = pix.y + (vnoise(pix + 33.0, 22.0) - 0.5) * 2.2 + sin(pix.x * 0.035 + seed) * 1.0;
		float f = fract(u / ridge_period);
		int tone = f < 0.16 ? 0 : f < 0.3 ? 1 : f < 0.48 ? 4 : f < 0.7 ? 3 : 2;
		if (bay > 0.3 && (tone == 2 || tone == 3)) tone += 1;
		if (tg < 0.56) tone = max(tone - 2, 0);  // a darker lip where the hoed soil meets the ground
		vec4 T[5] = vec4[5](till0, till1, till2, till3, till4);
		col = T[clamp(tone, 0, 4)];
		float wet = soil.b + (vnoise(pix + 5.0, 10.0) - 0.5) * 0.3 + bay * 0.05;
		if (wet > 0.5) col.rgb *= wet_darken;
	}
	// brick paving
	float pv = (1.0 - d.a) * (1.0 - max(d.r, d.g));
	float pe = pv + (vnoise(pix + 51.0, 7.0) - 0.5) * 0.5 + (vnoise(pix + 9.0, 3.0) - 0.5) * 0.18;
	if (pe > 0.45) {
		vec4 under = col;
		// rows wander and lean a little, in whole pixels
		vec2 q = pix + vec2(round((vnoise(pix + 37.0, 17.0) - 0.5) * 3.0), round((vnoise(pix * vec2(0.5, 1.0) + 91.0, 21.0) - 0.5) * 4.0));
		float row = floor(q.y / brick_row);
		float ly = q.y - row * brick_row;
		float rx = q.x + floor(hash(vec2(row, 3.7)) * brick_len);
		float k = floor(rx / brick_len);
		float L = joint_at(k, row, brick_len), R = joint_at(k + 1.0, row, brick_len), id = k;
		if (rx < L) { R = L; L = joint_at(k - 1.0, row, brick_len); id = k - 1.0; }
		else if (rx >= R) { L = R; R = joint_at(k + 2.0, row, brick_len); id = k + 1.0; }
		float lx = rx - L;
		float rr = R - 1.0 - rx;  // 0 on the brick's last column
		vec2 bid = vec2(id, row);
		float h1 = hash(bid * 1.37 + 5.1), h2 = hash(bid * 2.11 + 9.3), h3 = hash(bid * 0.71 + 2.9), h4 = hash(bid * 3.3 + 1.7);
		bool joint = lx < 1.0 || ly < 1.0
			|| (lx < 2.0 && (ly < 2.0 || ly >= brick_row - 1.0)) || (rr < 1.0 && (ly < 2.0 || ly >= brick_row - 1.0));
		float edge_k = 1.0 - smoothstep(0.45, 0.85, pe);  // 1 at the ragged edge of the road
		float around = (DATA(pix + vec2(7.0, 0.0)).a + DATA(pix - vec2(7.0, 0.0)).a
			+ DATA(pix + vec2(0.0, 7.0)).a + DATA(pix - vec2(0.0, 7.0)).a) * 0.25;
		float wear = smoothstep(0.65, 1.0, min(pv, 1.0 - around));  // the trodden middle
		bool missing = h4 < 0.02 + edge_k * 0.6;
		if (missing) {
			col = edge_k > 0.3 ? under : (vnoise(pix, 3.0) + bay * 0.4 < 0.5 ? dirt0 : dirt1);
		} else if (joint) {
			float mossy = vnoise(pix + 3.0, 9.0) * 0.8 + vnoise(pix + 8.0, 31.0) * 0.4 + edge_k * 0.4;
			col = mossy > 0.95 ? (bay > 0.0 ? joint_moss : grass1) : (bay + vnoise(pix, 2.0) * 0.6 > 0.05 ? joint1 : joint0);
			if (edge_k > 0.5 && bay > -0.1) col = under;  // grass grows up between the outer bricks
		} else {
			// mostly warm grey and beige; patches of other stone where a stretch was mended
			float patch = vnoise(pix + 211.0, 26.0);
			int fam = h1 < 0.45 ? 0 : h1 < 0.86 ? 1 : (patch > 0.6 ? 2 : patch < 0.3 ? 3 : 0);
			if (h1 > 0.985) fam = 4;
			float v = 0.48 + (h2 - 0.5) * 0.3 + wear * 0.16 - edge_k * 0.16 + (vnoise(pix + 17.0, 40.0) - 0.5) * 0.2;
			if (ly < 2.0 || lx < 2.0) v += 0.22;  // lit top and left edges
			if (ly >= brick_row - 1.0 || rr < 1.0) v -= 0.24;  // shaded bottom and right edges
			v += (vnoise(pix * 1.7 + bid * 13.0, 2.0) - 0.5) * 0.26 + bay * 0.12;  // grain
			if (h3 < 0.16) {  // a crack running across the brick
				float slope = h3 < 0.08 ? 0.9 : -0.9;
				float cx = (R - L) * 0.5 + (ly - brick_row * 0.5) * slope + (h2 - 0.5) * 3.0;
				if (abs(lx - cx) < 0.5 && ly > 0.5) v = -1.0;
				else if (abs(lx - cx - 1.0) < 0.5 && ly > 0.5) v += 0.25;
			}
			vec3 c = v < 0.0 ? STONE[fam * 4] * 0.78 : STONE[fam * 4 + clamp(int(v * 4.0), 0, 3)];
			if (edge_k > 0.3 && hash(pix * 0.37 + bid) < edge_k * 0.18) c = mix(c, joint_moss.rgb, 0.5);  // moss creeping onto sunk bricks
			col = vec4(c, 1.0);
		}
	}
	// indoor floors: whole cells, straight edges
	bool indoor = cell.a < 0.5 && (cell.r > 0.5 || cell.g > 0.5);
	if (cell.a < 0.5 && cell.r > 0.5 && cell.g > 0.5) {
		col = void_colour;  // outside the rooms of a house
	} else if (cell.a < 0.5 && cell.r > 0.5) {
		// floorboards running across, of uneven length, staggered row to row
		float row = floor(pix.y / board_h);
		float ly = pix.y - row * board_h;
		float len = 26.0 + floor(hash(vec2(row, 1.3)) * 22.0);
		float bx = pix.x + floor(hash(vec2(row, 7.9)) * len);
		float k = floor(bx / len);
		float lx = bx - k * len;
		vec2 bid = vec2(k, row);
		float hb = hash(bid * 1.91 + 4.2);
		float v = 0.5 + (hb - 0.5) * 0.3 + (vnoise(pix + 400.0, 36.0) - 0.5) * 0.15;
		v += (vnoise(vec2(pix.x * 0.25, pix.y * 2.0) + bid * 17.0, 3.0) - 0.5) * 0.25;  // grain along the board
		if (ly < 1.0) v += 0.25;  // the lit near edge of each board
		vec4 B[4] = vec4[4](board1, board2, board3, board4);
		col = B[clamp(int((v + bay * 0.18) * 4.0), 0, 3)];
		if (ly >= board_h - 1.0 || lx < 1.0) col = board0;  // gaps between boards and at their ends
		else if (hb < 0.35 && (lx == 2.0 || lx == len - 3.0) && ly == 1.0) col = board1;  // nails on some boards
		else if (hash(pix * 0.53 + bid) < 0.006) col = board1;  // knots
	} else if (cell.a < 0.5 && cell.g > 0.5) {
		// flagstones of uneven width in staggered rows, each with its own tone, lit top-left
		float row = floor(pix.y / flag_row);
		float ly = pix.y - row * flag_row;
		float len = 8.0 + floor(hash(vec2(row, 3.1)) * 5.0);
		float fx = pix.x + floor(hash(vec2(row, 5.7)) * len);
		float k = floor(fx / len);
		float lx = fx - k * len;
		vec2 fid = vec2(k, row);
		float h1 = hash(fid * 1.37 + 2.5), h2 = hash(fid * 2.71 + 8.1);
		int fam = h1 < 0.7 ? 1 : 0;  // pale beige flags, some warm grey
		float v = 0.62 + (h2 - 0.5) * 0.2 + (vnoise(pix + fid * 9.0, 2.0) - 0.5) * 0.15 + bay * 0.08;
		if (ly < 1.0 || lx < 1.0) col = flag_joint;
		else {
			if (ly < 2.0 || lx < 2.0) v += 0.22;
			if (ly >= flag_row - 1.0 || lx >= len - 1.0) v -= 0.2;
			col = vec4(STONE[fam * 4 + clamp(int(v * 4.0), 0, 3)], 1.0);
		}
	}
	// around and under water (same edge test as water.gdshader, so the strips line up)
	if (has_water && !indoor) {
		float we = WEDGE(pix);
		bool sandy = d.r > 0.4 && d.b > 0.5 && d.g < 0.5;
		if (we >= 0.5) {  // under the water: the bed, seen through the rim
			float m = vnoise(pix, 5.0) + bay * 0.3;
			col = sandy ? col * wet_sand_darken * 0.82 : (m < 0.55 ? mud0 : mud1);
		} else if (we > 0.5 - 0.09 * vnoise(pix + 13.0, 6.0)) {  // wet strip at the waterline, uneven
			col = sandy ? vec4(col.rgb * wet_sand_darken, 1.0) : (bay > -0.2 ? damp : mud2);
		} else {
			float r = damp_reach;
			float wb = (WATER(pix + vec2(r, 0.0)) + WATER(pix - vec2(r, 0.0)) + WATER(pix + vec2(0.0, r)) + WATER(pix - vec2(0.0, r))
				+ WATER(pix + vec2(r, r) * 0.7) + WATER(pix - vec2(r, r) * 0.7) + WATER(pix + vec2(r, -r) * 0.7) + WATER(pix + vec2(-r, r) * 0.7)) * 0.125;
			float dm = max(we * 1.6, wb) + (vnoise(pix, 6.0) - 0.5) * 0.3 + bay * 0.2;
			if (sandy) {
				if (dm > 0.45) col.rgb *= mix(1.0, wet_sand_darken, 0.6);
			} else if (d.r < 0.4) {
				if (dm > 0.5) col = damp;
				else if (dm > 0.22) col.rgb = mix(col.rgb, damp.rgb, 0.55);
			}
		}
	}
	COLOR = vec4(col.rgb, 1.0);
}

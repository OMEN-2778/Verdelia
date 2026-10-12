// Procedural ground for the whole map, ported from stardust-vale's arena painter.
// The sprite's TEXTURE is the terrain data (one texel per cell, linear filtered):
//   R = bare dirt / path, G = tilled soil, B = watered.
// Grass is two value-noise octaves + 4x4 Bayer dithering; dirt and tilled soil get organic,
// dithered edges from noise, paths are lighter where worn, tilled soil is drawn as mounded rows.
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

float bayer(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	return BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
}

// terrain data at a pixel (a macro: builtin samplers cannot be passed to functions)
#define DATA(p) texture(TEXTURE, ((p) + 0.5) / map_px)

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
	// dirt and paths
	float edge = d.r + (vnoise(pix, 11.0) - 0.5) * 0.42 + bay * 0.12;
	if (edge > 0.5) {
		float around = (DATA(pix + vec2(5.0, 0.0)).r + DATA(pix - vec2(5.0, 0.0)).r
			+ DATA(pix + vec2(0.0, 5.0)).r + DATA(pix - vec2(0.0, 5.0)).r) * 0.25;
		float wear = smoothstep(0.6, 1.0, min(d.r, around));
		float v = 0.38 + wear * 0.24 + (vnoise(pix, 6.0) - 0.5) * 0.5 - (edge < 0.58 ? 0.25 : 0.0) + bay * 0.25;
		vec4 D[4] = vec4[4](dirt0, dirt1, dirt2, dirt3);
		col = D[clamp(int(v * 4.0), 0, 3)];
		if (d.b > 0.5 && d.g < 0.5) {  // beach sand: lighter, finer, the odd shell or pebble
			vec4 S[4] = vec4[4](sand0, sand1, sand2, sand3);
			float sv = 0.45 + (vnoise(pix, 5.0) - 0.5) * 0.5 + (vnoise(pix, 17.0) - 0.5) * 0.3 + bay * 0.3 - (edge < 0.58 ? 0.2 : 0.0);
			col = S[clamp(int(sv * 4.0), 0, 3)];
			float hs = hash(pix * 0.73 + 11.0);
			if (hs < 0.004) col = vec4(1.0, 0.96, 0.92, 1.0);
			else if (hs < 0.008) col = vec4(0.62, 0.58, 0.52, 1.0);
		}
	}
	// tilled soil: mounded rows, lit on top, shadowed in the furrow; watered soil is darker
	float tg = d.g + (vnoise(pix + 77.0, 9.0) - 0.5) * 0.28 + bay * 0.08;
	if (tg > 0.5) {
		float u = pix.y + (vnoise(pix + 33.0, 22.0) - 0.5) * 2.2 + sin(pix.x * 0.035 + seed) * 1.0;
		float f = fract(u / ridge_period);
		int tone = f < 0.16 ? 0 : f < 0.3 ? 1 : f < 0.48 ? 4 : f < 0.7 ? 3 : 2;
		if (bay > 0.3 && (tone == 2 || tone == 3)) tone += 1;
		if (tg < 0.56) tone = max(tone - 2, 0);  // a darker lip where the hoed soil meets the ground
		vec4 T[5] = vec4[5](till0, till1, till2, till3, till4);
		col = T[clamp(tone, 0, 4)];
		float wet = d.b + (vnoise(pix + 5.0, 10.0) - 0.5) * 0.3 + bay * 0.05;
		if (wet > 0.5) col.rgb *= wet_darken;
	}
	COLOR = vec4(col.rgb, 1.0);
}

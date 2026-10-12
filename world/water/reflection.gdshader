// Upside-down reflection of a tree, bush or rock in the water (see WaterReflection). Drawn only
// where water.gdshader draws open water (same edge test, minus the earth bank face), wobbling
// with the surface, tinted towards the water colour, broken by thin calm lines, and fading out
// with distance from the waterline.
shader_type canvas_item;

uniform sampler2D water_data : filter_linear;
uniform vec2 map_px = vec2(960.0, 480.0);
uniform vec2 origin = vec2(0.0);  // Terrain's global position
uniform float seed = 0.0;
uniform vec4 water_color : source_color = vec4(0.169, 0.420, 0.639, 1.0);
uniform float strength : hint_range(0.0, 1.0) = 0.42;  // how much of the object shows
uniform float darken : hint_range(0.0, 1.0) = 0.78;
uniform float fade_px = 46.0;  // px below the waterline where the reflection has faded out
uniform float bank_height = 4.0;  // keep in step with water.gdshader
uniform float wobble = 1.0;

const float BAYER[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
#define W(p) texture(water_data, ((p) + 0.5) / map_px).r
#define WV(p) ((W(p) * 2.0 + W((p) + vec2(3.0, 3.0)) + W((p) + vec2(-3.0, 3.0)) + W((p) + vec2(3.0, -3.0)) + W((p) - vec2(3.0, 3.0))) / 6.0)
#define EDGE(p) (WV(p) + (vnoise(p, 13.0) - 0.5) * 0.3 + (vnoise((p) + 17.0, 5.0) - 0.5) * 0.2 + (vnoise((p) + 31.0, 2.5) - 0.5) * 0.1)

varying vec2 world;

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

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	vec2 pix = floor(world - origin);
	if (EDGE(pix) < 0.5 || EDGE(pix - vec2(0.0, bank_height + 1.0)) < 0.5) {
		discard;
	}
	// the surface sways the reflection sideways, row by row
	float wob = round((sin(pix.y * 0.9 + TIME * 2.1) * 0.6 + sin(pix.y * 0.31 - TIME * 1.3) * 0.5) * wobble);
	vec4 tex = texture(TEXTURE, UV + vec2(wob * TEXTURE_PIXEL_SIZE.x, 0.0));
	if (tex.a < 0.5) {
		discard;
	}
	ivec2 q = ivec2(mod(pix, 4.0));
	float bay = BAYER[q.y * 4 + q.x] / 16.0 - 0.5;
	float dist = (1.0 - UV.y) / TEXTURE_PIXEL_SIZE.y;  // px from the mirror line
	float fade = 1.0 - dist / fade_px;
	if (fade + bay * 0.5 < 0.15) {
		discard;
	}
	// thin calm streaks where the surface breaks the image
	vec2 streak = vec2(floor((pix.x + TIME * 3.0) / 7.0), pix.y);
	if (hash(streak) < 0.1) {
		discard;
	}
	float k = strength * (fade > 0.5 ? 1.0 : 0.65);
	COLOR = vec4(mix(water_color.rgb, tex.rgb * darken * vec3(0.85, 0.95, 1.05), k), 1.0);
}

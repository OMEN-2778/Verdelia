// Full-screen look: soft contrast, lifted shadows, warm tint, gentle bloom on bright pixels,
// drifting cloud shadows and a light vignette. Sits on a CanvasLayer above the world.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D cloud_noise : repeat_enable, filter_linear;

group_uniforms grade;
uniform float contrast : hint_range(0.5, 1.5) = 0.86;
uniform float lift : hint_range(-0.2, 0.2) = 0.045;
uniform float saturation : hint_range(0.0, 1.5) = 0.92;
uniform vec3 tint : source_color = vec3(1.0, 0.98, 0.93);
uniform float vignette : hint_range(0.0, 1.0) = 0.22;

group_uniforms bloom;
uniform float bloom_strength : hint_range(0.0, 2.0) = 0.55;
uniform float bloom_threshold : hint_range(0.0, 1.0) = 0.68;
uniform float bloom_radius = 6.0;  // in screen px (the screen is the 426x240 world drawn 3x)

group_uniforms sun;
// Stardust Vale grade: warm light screened in from the top-left corner, cool multiply toward the
// bottom-right. Alpha is the strength; 0 disables.
uniform vec4 warm : source_color = vec4(1.0, 0.925, 0.667, 0.0);
uniform vec4 cool : source_color = vec4(0.078, 0.196, 0.314, 0.0);
// where the warm light comes from, in screen UV (0,0 = top-left); the cool side is opposite.
// DayNight moves it with the sun.
uniform vec2 warm_origin = vec2(0.0, 0.0);

group_uniforms clouds;
uniform float cloud_strength : hint_range(0.0, 0.5) = 0.13;
uniform float cloud_scale = 0.55;
uniform vec2 cloud_velocity = vec2(0.012, 0.005);

void fragment() {
	vec3 c = texture(screen_tex, SCREEN_UV).rgb;

	vec3 bloom = vec3(0.0);
	vec2 step_px = SCREEN_PIXEL_SIZE * bloom_radius;
	for (int i = -2; i <= 2; i++) {
		for (int j = -2; j <= 2; j++) {
			vec3 s = texture(screen_tex, SCREEN_UV + vec2(float(i), float(j)) * step_px).rgb;
			bloom += max(s - bloom_threshold, vec3(0.0));
		}
	}
	bloom /= 25.0;

	vec2 aspect = vec2(SCREEN_PIXEL_SIZE.y / SCREEN_PIXEL_SIZE.x, 1.0);
	float n = texture(cloud_noise, SCREEN_UV * aspect * cloud_scale + TIME * cloud_velocity).r;
	c *= 1.0 - cloud_strength * smoothstep(0.48, 0.68, n);

	c += bloom * bloom_strength;

	vec2 screen_px = 1.0 / SCREEN_PIXEL_SIZE;
	vec2 p = SCREEN_UV * screen_px;
	vec2 o = warm_origin * screen_px;
	float fw = max(0.0, 1.0 - length(p - o) / (length(screen_px) * 0.95)) * warm.a;
	c = 1.0 - (1.0 - c) * (1.0 - warm.rgb * fw);
	vec2 axis = (screen_px * 0.5 - o) * 2.0;
	float diag = dot(p - o, axis) / max(dot(axis, axis), 1.0);
	c *= mix(vec3(1.0), cool.rgb, clamp((diag - 0.45) / 0.55, 0.0, 1.0) * cool.a);
	float luma = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(luma), c, saturation);
	c = (c - 0.5) * contrast + 0.5 + lift;
	c *= tint;
	vec2 d = SCREEN_UV - 0.5;
	c *= 1.0 - vignette * dot(d, d) * 2.0;
	COLOR = vec4(c, 1.0);
}

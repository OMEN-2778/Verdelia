shader_type canvas_item;
// The far lake in the vista: glints of sun that come and go on its surface, more of them nearer
// the shore, and a slow shimmer along the long wave lines.

uniform float glint_rate = 0.004;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	vec2 px = floor(UV / TEXTURE_PIXEL_SIZE);
	float row = px.y * TEXTURE_PIXEL_SIZE.y;  // 0 at the horizon, 1 at the shore
	// each pixel blinks on its own slow beat
	float beat = floor(TIME * 1.3 + hash(px) * 11.0);
	float g = hash(px + vec2(beat * 7.0, beat * 3.0));
	if (row > 0.04 && g > 1.0 - glint_rate * (0.4 + row * 1.6)) {
		c.rgb = mix(c.rgb, vec3(0.95, 0.99, 1.0), 0.85);
	}
	// the lighter wave lines ripple a little brighter and dimmer as the light runs along them
	float wave = sin(px.x * 0.11 - TIME * 0.6 + px.y * 0.7) * 0.5 + 0.5;
	c.rgb += vec3(0.03, 0.04, 0.04) * wave * step(0.5, c.b - c.r);
	COLOR = c;
}

// Wind sway for plants: shears the top of the sprite, bottom stays planted.
// Neighbouring plants get different phases from their world position.
shader_type canvas_item;

uniform float amount = 1.0;  // pixels of offset at the top edge
uniform float speed = 1.4;
uniform float gust = 0.6;  // extra slow wave that rolls across the field

void vertex() {
	float world_x = MODEL_MATRIX[3].x;
	float w = 1.0 - UV.y;
	float wave = sin(TIME * speed + world_x * 0.09) + gust * sin(TIME * 0.45 - world_x * 0.02);
	VERTEX.x += wave * amount * w * w;
}

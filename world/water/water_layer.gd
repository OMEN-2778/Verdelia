@tool
class_name WaterLayer
extends Sprite2D
## Draws all the water painted into `terrain` (WaterBody nodes, the water brush, water_mask) with
## water.gdshader. One node per map; tweak the look in its material's shader parameters.

@export var terrain: Terrain:
	set(v):
		if terrain and terrain.changed.is_connected(_on_changed):
			terrain.changed.disconnect(_on_changed)
		terrain = v
		if terrain and not terrain.changed.is_connected(_on_changed):
			terrain.changed.connect(_on_changed)
		_on_changed(Rect2i())


func _ready() -> void:
	centered = false
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	z_index = -9
	if material == null:
		var m := ShaderMaterial.new()
		m.shader = preload("res://world/water/water.gdshader")
		material = m
	_on_changed(Rect2i())


func _on_changed(_cells: Rect2i) -> void:
	if not terrain or not terrain.water_texture or not is_inside_tree():
		return
	texture = terrain.water_texture
	global_position = terrain.global_position
	scale = Vector2(terrain.cell_px, terrain.cell_px)
	var m := material as ShaderMaterial
	if m:
		m.set_shader_parameter("map_px", Vector2(terrain.water.get_size() * terrain.cell_px))
		m.set_shader_parameter("ground_data", terrain.texture)
		m.set_shader_parameter("shore_depth_px", terrain.water_depth_cells * terrain.cell_px)

class_name WaterReflection
extends Node2D
## Mirrors some sprites of its parent about the parent's base line (y = 0) into the water below.
## WorldTree and WorldProp add one automatically; it only shows when there is water underneath,
## and reflection.gdshader clips it to the open water. Follows the sources each frame, so swaying
## crowns sway in the reflection too.

const SHADER := preload("res://world/water/reflection.gdshader")
static var _materials := {}  # Terrain -> ShaderMaterial

var _sources: Array[Sprite2D] = []
var _copies: Array[Sprite2D] = []
var _terrain: Terrain


## Adds a reflection of `sprites` (children of `owner_node`) under `owner_node`.
static func attach(owner_node: Node2D, sprites: Array[Sprite2D]) -> WaterReflection:
	var r := WaterReflection.new()
	r.name = "Reflection"
	r._sources = sprites
	owner_node.add_child(r)
	return r


func _ready() -> void:
	scale = Vector2(1, -1)
	visible = false
	set_process(false)
	if Engine.is_editor_hint():
		return
	_terrain = get_tree().get_first_node_in_group("terrain") as Terrain
	if _terrain == null:
		return
	for s in _sources:
		var c := Sprite2D.new()
		c.texture = s.texture
		c.centered = s.centered
		c.offset = s.offset
		c.position = s.position
		c.z_as_relative = false
		c.z_index = -9  # with the water, under the cliffs and props
		c.material = _material(_terrain)
		add_child(c)
		_copies.append(c)
	_terrain.changed.connect(_check.unbind(1))
	_check.call_deferred()


func _process(_delta: float) -> void:
	for i in _copies.size():
		_copies[i].position = _sources[i].position


## Visible only if there is water in the area the reflection would cover.
func _check() -> void:
	if _terrain == null or _terrain.water == null or _copies.is_empty():
		return
	var m := _material(_terrain)
	m.set_shader_parameter("water_data", _terrain.water_texture)
	m.set_shader_parameter("map_px", Vector2(_terrain.water.get_size() * _terrain.cell_px))
	m.set_shader_parameter("origin", _terrain.global_position)
	var rect := Rect2()
	for c in _copies:
		var r := c.get_rect()
		r.position += c.position
		rect = r if rect.size == Vector2.ZERO else rect.merge(r)
	var wet := false
	var y := 2.0  # the copies sit above the line in local space; flipped, they hang below it
	while y < -rect.position.y and not wet:
		var x := rect.position.x
		while x <= rect.end.x:
			if _terrain.water_at(global_position + Vector2(x, y)) > 0.5:
				wet = true
				break
			x += 6.0
		y += 6.0
	visible = wet
	set_process(wet)


static func _material(t: Terrain) -> ShaderMaterial:
	var m: ShaderMaterial = _materials.get(t)
	if m == null:
		m = ShaderMaterial.new()
		m.shader = SHADER
		_materials[t] = m
	return m

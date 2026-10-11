@tool
class_name Terrain
extends Sprite2D
## Map-wide ground. Holds the terrain data (one texel per cell) and draws it through
## ground.gdshader, so any map size works without tiles or seams.
##
## Authoring: paint with `paint_layer` (a TileMapLayer using terrain_brushes.tres: dirt, tilled,
## watered, grass/erase) and/or start from `mask` (an RGBA image, R=dirt G=tilled B=watered).
## At runtime, gameplay calls set_cell() (e.g. hoeing, watering); `changed` tells the grass.

signal changed(cell_rect: Rect2i)

enum Kind { GRASS, DIRT, TILLED, WATERED }
const BRUSH_KINDS: Array[int] = [Kind.DIRT, Kind.TILLED, Kind.WATERED, Kind.GRASS]  # terrain_brushes.png order

@export var map_size_px := Vector2i(426, 240):
	set(v):
		map_size_px = v
		_queue_rebuild()
@export var cell_px := 8:
	set(v):
		cell_px = maxi(1, v)
		_queue_rebuild()
@export var mask: Texture2D:
	set(v):
		mask = v
		_queue_rebuild()
@export var paint_layer: TileMapLayer:
	set(v):
		if paint_layer and paint_layer.changed.is_connected(_queue_rebuild):
			paint_layer.changed.disconnect(_queue_rebuild)
		paint_layer = v
		if paint_layer and not paint_layer.changed.is_connected(_queue_rebuild):
			paint_layer.changed.connect(_queue_rebuild)
		_queue_rebuild()

var data: Image
var _tex: ImageTexture
var _pending := false


func _ready() -> void:
	centered = false
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	z_index = -10
	if material == null:
		var m := ShaderMaterial.new()
		m.shader = preload("res://world/terrain/ground.gdshader")
		material = m
	if paint_layer and not Engine.is_editor_hint():
		paint_layer.visible = false
	rebuild()


func cells() -> Vector2i:
	return Vector2i(ceili(map_size_px.x / float(cell_px)), ceili(map_size_px.y / float(cell_px)))


func rebuild() -> void:
	_pending = false
	var n := cells()
	data = Image.create(n.x, n.y, false, Image.FORMAT_RGBA8)
	data.fill(Color(0, 0, 0, 1))
	if mask:
		var m := mask.get_image()
		if m:
			m = m.duplicate()
			m.decompress()
			m.convert(Image.FORMAT_RGBA8)
			data.blit_rect(m, Rect2i(Vector2i.ZERO, m.get_size().min(n)), Vector2i.ZERO)
	if paint_layer:
		for c in paint_layer.get_used_cells():
			if c.x >= 0 and c.y >= 0 and c.x < n.x and c.y < n.y:
				_write(c, BRUSH_KINDS[clampi(paint_layer.get_cell_atlas_coords(c).x, 0, 3)])
	_upload()
	changed.emit(Rect2i(Vector2i.ZERO, n))


## Change one cell at runtime (hoe, water, pave...). kind: Kind.
func set_cell(cell: Vector2i, kind: int) -> void:
	if not data or cell.x < 0 or cell.y < 0 or cell.x >= data.get_width() or cell.y >= data.get_height():
		return
	_write(cell, kind)
	_upload()
	changed.emit(Rect2i(cell, Vector2i.ONE))


func cell_at(world: Vector2) -> Vector2i:
	var p := _texel(world)
	return Vector2i(floori(p.x), floori(p.y))


## Smoothly interpolated terrain data at a world position (same as the shader sees, minus noise).
func sample(world: Vector2) -> Color:
	if not data:
		return Color(0, 0, 0, 1)
	var p := _texel(world) - Vector2(0.5, 0.5)
	var i := Vector2i(floori(p.x), floori(p.y))
	var f := p - Vector2(i)
	var a := _px(i)
	var b := _px(i + Vector2i(1, 0))
	var c := _px(i + Vector2i(0, 1))
	var d := _px(i + Vector2i(1, 1))
	return a.lerp(b, f.x).lerp(c.lerp(d, f.x), f.y)


## Dominant kind at a world position (for gameplay and grass placement).
func kind_at(world: Vector2) -> int:
	var s := sample(world)
	if s.g > 0.5:
		return Kind.WATERED if s.b > 0.5 else Kind.TILLED
	if s.r > 0.5:
		return Kind.DIRT
	return Kind.GRASS


## World position -> texel coordinates (the sprite is scaled by cell_px, so don't use to_local).
func _texel(world: Vector2) -> Vector2:
	return (world - global_position) / float(cell_px)


func _px(i: Vector2i) -> Color:
	i = i.clamp(Vector2i.ZERO, Vector2i(data.get_width() - 1, data.get_height() - 1))
	return data.get_pixelv(i)


func _write(cell: Vector2i, kind: int) -> void:
	var c := Color(0, 0, 0, 1)
	match kind:
		Kind.DIRT:
			c = Color(1, 0, 0, 1)
		Kind.TILLED:
			c = Color(1, 1, 0, 1)
		Kind.WATERED:
			c = Color(1, 1, 1, 1)
	data.set_pixelv(cell, c)


func _upload() -> void:
	if _tex and _tex.get_size() == Vector2(data.get_size()):
		_tex.update(data)
	else:
		_tex = ImageTexture.create_from_image(data)
	texture = _tex
	scale = Vector2(cell_px, cell_px)
	var m := material as ShaderMaterial
	if m:
		m.set_shader_parameter("map_px", Vector2(data.get_size() * cell_px))


func _queue_rebuild() -> void:
	if not is_inside_tree() or _pending:
		return
	_pending = true
	rebuild.call_deferred()

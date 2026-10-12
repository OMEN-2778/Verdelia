@tool
class_name Terrain
extends Sprite2D
## Map-wide ground. Holds the terrain data (one texel per cell) and draws it through
## ground.gdshader, so any map size works without tiles or seams.
##
## Authoring: paint with `paint_layer` (a TileMapLayer using terrain_brushes.tres: dirt, tilled,
## watered, grass/erase, water) and/or start from `mask` (an RGBA image, R=dirt G=tilled
## B=watered) and `water_mask` (grey, white = water). Nodes in the "terrain_painters" group
## (WaterBody) add their shapes through paint_terrain(terrain) on every rebuild.
## At runtime, gameplay calls set_cell() (e.g. hoeing, watering); `changed` tells the grass.
##
## Water lives in its own texture (`water_texture`, one texel per cell): R = water, G = distance
## from the shore (1 = `water_depth_cells` or more). WaterLayer draws it.

signal changed(cell_rect: Rect2i)

enum Kind { GRASS, DIRT, TILLED, WATERED, WATER, SAND }
const BRUSH_KINDS: Array[int] = [Kind.DIRT, Kind.TILLED, Kind.WATERED, Kind.GRASS, Kind.WATER]  # terrain_brushes.png order

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
@export var water_mask: Texture2D:
	set(v):
		water_mask = v
		_queue_rebuild()
@export var water_depth_cells := 5.0:  ## shore distance mapped to G = 1, in cells
	set(v):
		water_depth_cells = maxf(1.0, v)
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
var water: Image
var water_texture: ImageTexture
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
	_queue_rebuild()  # deferred, so sibling painters (lakes, rivers) are ready first


func cells() -> Vector2i:
	return Vector2i(ceili(map_size_px.x / float(cell_px)), ceili(map_size_px.y / float(cell_px)))


func rebuild() -> void:
	_pending = false
	var n := cells()
	data = Image.create(n.x, n.y, false, Image.FORMAT_RGBA8)
	data.fill(Color(0, 0, 0, 1))
	water = Image.create(n.x, n.y, false, Image.FORMAT_RGBA8)
	water.fill(Color(0, 0, 0, 1))
	if mask:
		var m := mask.get_image()
		if m:
			m = m.duplicate()
			m.decompress()
			m.convert(Image.FORMAT_RGBA8)
			data.blit_rect(m, Rect2i(Vector2i.ZERO, m.get_size().min(n)), Vector2i.ZERO)
	if water_mask:
		var wm := water_mask.get_image()
		if wm:
			wm = wm.duplicate()
			wm.decompress()
			for y in mini(wm.get_height(), n.y):
				for x in mini(wm.get_width(), n.x):
					if wm.get_pixel(x, y).v > 0.5:
						water.set_pixel(x, y, Color(1, 0, 0, 1))
	if is_inside_tree():
		for painter in get_tree().get_nodes_in_group("terrain_painters"):
			painter.paint_terrain(self)
	if paint_layer:
		for c in paint_layer.get_used_cells():
			if c.x >= 0 and c.y >= 0 and c.x < n.x and c.y < n.y:
				_write(c, BRUSH_KINDS[clampi(paint_layer.get_cell_atlas_coords(c).x, 0, 4)])
	_compute_water()
	_upload()
	changed.emit(Rect2i(Vector2i.ZERO, n))


## Change one cell at runtime (hoe, water, pave...). kind: Kind.
func set_cell(cell: Vector2i, kind: int) -> void:
	if not _in(cell):
		return
	_write(cell, kind)
	if kind == Kind.WATER or kind == Kind.GRASS:
		_compute_water()
	_upload()
	changed.emit(Rect2i(cell, Vector2i.ONE))


## For painters: mark a cell as water.
func paint_water(cell: Vector2i) -> void:
	if _in(cell):
		water.set_pixelv(cell, Color(1, 0, 0, 1))


## For painters: set the ground kind of a cell (dirt for beaches, grass to clear...).
func paint_ground(cell: Vector2i, kind: int) -> void:
	if _in(cell):
		_write(cell, kind)


## Water presence at a world position, 0..1 (smoothly interpolated, like the shader sees it).
func water_at(world: Vector2) -> float:
	if not water:
		return 0.0
	var p := _texel(world) - Vector2(0.5, 0.5)
	var i := Vector2i(floori(p.x), floori(p.y))
	var f := p - Vector2(i)
	var a := _wpx(i).r
	var b := _wpx(i + Vector2i(1, 0)).r
	var c := _wpx(i + Vector2i(0, 1)).r
	var d := _wpx(i + Vector2i(1, 1)).r
	return lerpf(lerpf(a, b, f.x), lerpf(c, d, f.x), f.y)


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
	if water_at(world) > 0.5:
		return Kind.WATER
	var s := sample(world)
	if s.g > 0.5:
		return Kind.WATERED if s.b > 0.5 else Kind.TILLED
	if s.r > 0.5:
		return Kind.SAND if s.b > 0.5 else Kind.DIRT
	return Kind.GRASS


## World position -> texel coordinates (the sprite is scaled by cell_px, so don't use to_local).
func _texel(world: Vector2) -> Vector2:
	return (world - global_position) / float(cell_px)


func _px(i: Vector2i) -> Color:
	i = i.clamp(Vector2i.ZERO, Vector2i(data.get_width() - 1, data.get_height() - 1))
	return data.get_pixelv(i)


func _in(cell: Vector2i) -> bool:
	return data != null and cell.x >= 0 and cell.y >= 0 and cell.x < data.get_width() and cell.y < data.get_height()


func _wpx(i: Vector2i) -> Color:
	i = i.clamp(Vector2i.ZERO, Vector2i(water.get_width() - 1, water.get_height() - 1))
	return water.get_pixelv(i)


func _write(cell: Vector2i, kind: int) -> void:
	if kind == Kind.WATER:
		water.set_pixelv(cell, Color(1, 0, 0, 1))
		return
	if kind == Kind.GRASS and water:
		water.set_pixelv(cell, Color(0, 0, 0, 1))  # the eraser also removes water
	var c := Color(0, 0, 0, 1)
	match kind:
		Kind.DIRT:
			c = Color(1, 0, 0, 1)
		Kind.TILLED:
			c = Color(1, 1, 0, 1)
		Kind.WATERED:
			c = Color(1, 1, 1, 1)
		Kind.SAND:
			c = Color(1, 0, 1, 1)  # dirt + "wet" bit without tilled = beach sand
	data.set_pixelv(cell, c)


## G = chamfer distance from the nearest dry cell.
func _compute_water() -> void:
	var w := water.get_width()
	var h := water.get_height()
	var dist := PackedFloat32Array()
	dist.resize(w * h)
	for y in h:
		for x in w:
			dist[y * w + x] = 1e6 if water.get_pixel(x, y).r > 0.5 else 0.0
	for y in h:
		for x in w:
			var i := y * w + x
			if dist[i] == 0.0:
				continue
			var v := dist[i]
			if x > 0: v = minf(v, dist[i - 1] + 1.0)
			if y > 0: v = minf(v, dist[i - w] + 1.0)
			if x > 0 and y > 0: v = minf(v, dist[i - w - 1] + 1.41)
			if x < w - 1 and y > 0: v = minf(v, dist[i - w + 1] + 1.41)
			dist[i] = v
	for y in range(h - 1, -1, -1):
		for x in range(w - 1, -1, -1):
			var i := y * w + x
			if dist[i] == 0.0:
				continue
			var v := dist[i]
			if x < w - 1: v = minf(v, dist[i + 1] + 1.0)
			if y < h - 1: v = minf(v, dist[i + w] + 1.0)
			if x < w - 1 and y < h - 1: v = minf(v, dist[i + w + 1] + 1.41)
			if x > 0 and y < h - 1: v = minf(v, dist[i + w - 1] + 1.41)
			dist[i] = v
	for y in h:
		for x in w:
			var d := dist[y * w + x]
			if d <= 0.0:
				continue
			var depth := clampf((d - 0.5) / water_depth_cells, 0.0, 1.0)
			water.set_pixel(x, y, Color(1, depth, 0, 1))


func _upload() -> void:
	if _tex and _tex.get_size() == Vector2(data.get_size()):
		_tex.update(data)
	else:
		_tex = ImageTexture.create_from_image(data)
	texture = _tex
	if water_texture and water_texture.get_size() == Vector2(water.get_size()):
		water_texture.update(water)
	else:
		water_texture = ImageTexture.create_from_image(water)
	scale = Vector2(cell_px, cell_px)
	var m := material as ShaderMaterial
	if m:
		m.set_shader_parameter("map_px", Vector2(data.get_size() * cell_px))


func _queue_rebuild() -> void:
	if not is_inside_tree() or _pending:
		return
	_pending = true
	rebuild.call_deferred()

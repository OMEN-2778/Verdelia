@tool
class_name TerrainPath
extends Node2D
## A path painted into the Terrain along a polyline (`points`, local): a footpath of `width` px that
## swells and narrows a little along the way. The ground shader gives it soft, worn edges. Use it
## to lead up to ramps, doors and bridges; for a tilled field use `kind` = Terrain.Kind.TILLED.

@export var terrain: Terrain:
	set(v):
		terrain = v
		_refresh()
@export var points := PackedVector2Array():
	set(v):
		points = v
		_refresh()
@export var width := 12.0:
	set(v):
		width = v
		_refresh()
@export var wobble := 0.25  ## how much the width varies along the path (0..1)
@export var kind := Terrain.Kind.DIRT


func _ready() -> void:
	add_to_group("terrain_painters")
	_refresh()


func paint_terrain(t: Terrain) -> void:
	if points.size() < 2:
		return
	var walked := 0.0
	for k in points.size() - 1:
		var a := to_global(points[k])
		var b := to_global(points[k + 1])
		var n := maxi(1, int(a.distance_to(b) / 2.0))
		for j in n + 1:
			var p := a.lerp(b, float(j) / n)
			var w := width * (1.0 + wobble * sin(walked * 0.09) * cos(walked * 0.037))
			walked += a.distance_to(b) / n
			var half := w * 0.5
			var c0 := t.cell_at(p - Vector2(half, half))
			var c1 := t.cell_at(p + Vector2(half, half))
			for cy in range(c0.y, c1.y + 1):
				for cx in range(c0.x, c1.x + 1):
					var centre := t.global_position + (Vector2(cx, cy) + Vector2(0.5, 0.5)) * t.cell_px
					if centre.distance_to(p) <= half:
						t.paint_ground(Vector2i(cx, cy), kind)


func _refresh() -> void:
	if is_inside_tree() and terrain:
		terrain.rebuild.call_deferred()

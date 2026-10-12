@tool
class_name WaterShape
extends Node2D
## A lake or pond: the polygon of the child Polygon2D named "Shape" (or `polygon`) is painted as
## water into the Terrain. The shore can stay grassy, become a sandy beach, or get rocks.
## Put it under the y-sorted Props node if it has rocks, so they sort with everything else.

enum Shore { GRASS, SAND, ROCK, SAND_AND_ROCK }

@export var terrain: Terrain:
	set(v):
		terrain = v
		_refresh()
@export var polygon := PackedVector2Array():
	set(v):
		polygon = v
		_refresh()
@export var shore := Shore.GRASS:
	set(v):
		shore = v
		_refresh()
@export var beach_width := 14.0:  ## px of sand around the water (SAND shores)
	set(v):
		beach_width = v
		_refresh()
@export var rocks := 10:  ## rocks along the shore (ROCK shores)
	set(v):
		rocks = v
		_refresh()
@export var seed := 1


func _ready() -> void:
	add_to_group("terrain_painters")
	y_sort_enabled = true
	_refresh()


func _poly() -> PackedVector2Array:
	var p: Polygon2D = get_node_or_null("Shape")
	if p:
		if not Engine.is_editor_hint():
			p.visible = false
		var out := PackedVector2Array()
		for v in p.polygon:
			out.append(p.position + v)
		return out
	return polygon


## Called by Terrain while it rebuilds.
func paint_terrain(t: Terrain) -> void:
	var poly := _poly()
	if poly.size() < 3:
		return
	var world := PackedVector2Array()
	for v in poly:
		world.append(to_global(v))
	var bounds := Rect2(world[0], Vector2.ZERO)
	for v in world:
		bounds = bounds.expand(v)
	var pad := beach_width + t.cell_px if shore in [Shore.SAND, Shore.SAND_AND_ROCK] else 0.0
	bounds = bounds.grow(pad)
	var c0 := t.cell_at(bounds.position)
	var c1 := t.cell_at(bounds.end)
	for cy in range(c0.y, c1.y + 1):
		for cx in range(c0.x, c1.x + 1):
			var centre := t.global_position + (Vector2(cx, cy) + Vector2(0.5, 0.5)) * t.cell_px
			if Geometry2D.is_point_in_polygon(centre, world):
				t.paint_water(Vector2i(cx, cy))
			elif pad > 0.0 and _edge_distance(centre, world) < beach_width:
				t.paint_ground(Vector2i(cx, cy), Terrain.Kind.SAND)


func _edge_distance(p: Vector2, poly: PackedVector2Array) -> float:
	var best := INF
	for i in poly.size():
		var a := poly[i]
		var b := poly[(i + 1) % poly.size()]
		best = minf(best, p.distance_to(Geometry2D.get_closest_point_to_segment(p, a, b)))
	return best


func _refresh() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		if c.owner == null and c is WorldProp:
			c.queue_free()
	if shore in [Shore.ROCK, Shore.SAND_AND_ROCK]:
		_place_rocks()
	if terrain:
		terrain.rebuild.call_deferred()


## Rocks along the shoreline, half in the water, spaced along the perimeter.
func _place_rocks() -> void:
	var poly := _poly()
	if poly.size() < 3:
		return
	var perim := 0.0
	for i in poly.size():
		perim += poly[i].distance_to(poly[(i + 1) % poly.size()])
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	for k in rocks:
		var d := (k + rng.randf_range(0.0, 0.8)) / rocks * perim
		for i in poly.size():
			var a := poly[i]
			var b := poly[(i + 1) % poly.size()]
			var l := a.distance_to(b)
			if d <= l:
				var p := a.lerp(b, d / maxf(l, 0.001))
				var r := WorldProp.new()
				r.library_item = "rock"
				r.skirt = 0.6
				r.position = (p + Vector2(0, 2)).round()
				add_child(r)
				break
			d -= l

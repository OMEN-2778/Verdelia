@tool
class_name River
extends Node2D
## A river or stream along a polyline (`points`, local). Paints water with a flow direction into
## the Terrain; width and speed can change along the river (per point), fast stretches foam up
## as rapids in the water shader. Optional sandy banks.

@export var terrain: Terrain:
	set(v):
		terrain = v
		_refresh()
@export var points := PackedVector2Array():
	set(v):
		points = v
		_refresh()
@export var width := 18.0:
	set(v):
		width = v
		_refresh()
@export var widths := PackedFloat32Array():  ## optional width per point (overrides `width`)
	set(v):
		widths = v
		_refresh()
@export_range(0.0, 1.0) var speed := 0.5:
	set(v):
		speed = v
		_refresh()
@export var speeds := PackedFloat32Array():  ## optional speed per point; >0.8 reads as rapids
	set(v):
		speeds = v
		_refresh()
@export var meander := 3.0  ## px of gentle width wobble
@export var bank_sand := 0.0:  ## px of sand along the banks
	set(v):
		bank_sand = v
		_refresh()


func _ready() -> void:
	add_to_group("terrain_painters")
	_refresh()


func paint_terrain(t: Terrain) -> void:
	if points.size() < 2:
		return
	var samples := _samples()
	for s in samples:
		var p: Vector2 = s[0]
		var dir: Vector2 = s[1]
		var half: float = s[2] / 2.0
		var spd: float = s[3]
		var reach := half + bank_sand + t.cell_px
		var c0 := t.cell_at(p - Vector2(reach, reach))
		var c1 := t.cell_at(p + Vector2(reach, reach))
		for cy in range(c0.y, c1.y + 1):
			for cx in range(c0.x, c1.x + 1):
				var centre := t.global_position + (Vector2(cx, cy) + Vector2(0.5, 0.5)) * t.cell_px
				var d := centre.distance_to(p)
				if d <= half:
					t.paint_water(Vector2i(cx, cy), dir * spd)
				elif bank_sand > 0.0 and d <= half + bank_sand and t.water_at(centre) < 0.5:
					t.paint_ground(Vector2i(cx, cy), Terrain.Kind.SAND)


## Smoothed samples along the river: [world position, flow direction, width, speed].
func _samples() -> Array:
	var pts := [points[0]]
	pts.append_array(points)
	pts.append(points[points.size() - 1])
	var out := []
	var k := 0
	for i in range(1, pts.size() - 2):
		var p0: Vector2 = pts[i - 1]
		var p1: Vector2 = pts[i]
		var p2: Vector2 = pts[i + 1]
		var p3: Vector2 = pts[i + 2]
		var n := maxi(2, int(p1.distance_to(p2) / 2.0))
		for j in n:
			var t := float(j) / n
			var t2 := t * t
			var t3 := t2 * t
			var p := 0.5 * (2.0 * p1 + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)
			var tangent := 0.5 * ((-p0 + p2) + 2.0 * (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t + 3.0 * (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t2)
			var seg := i - 1
			var w := width if widths.size() != points.size() else lerpf(widths[seg], widths[seg + 1], t)
			w += sin(k * 0.17) * meander
			var spd := speed if speeds.size() != points.size() else lerpf(speeds[seg], speeds[seg + 1], t)
			out.append([to_global(p), tangent.normalized(), w, spd])
			k += 1
	return out


func _refresh() -> void:
	if is_inside_tree() and terrain:
		terrain.rebuild.call_deferred()

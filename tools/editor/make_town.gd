extends SceneTree
## Writes maps/town.json: a small sample town to try the buildings in (and to start from in the
## map editor). A main street with houses, shops and the inn along it, a market square with
## stalls, a pond and some woods.
##   godot --headless --path . --script res://tools/editor/make_town.gd


func _init() -> void:
	var m := MapData.create(Vector2i(110, 62))
	m.name = "小镇"
	var rng := RandomNumberGenerator.new()
	rng.seed = 2778
	# main street, the market square and the lanes off it
	_ground(m, Rect2(0, 232, 880, 30), MapData.Ground.DIRT)
	_ground(m, Rect2(300, 262, 330, 140), MapData.Ground.SAND)
	_ground(m, Rect2(140, 262, 22, 124), MapData.Ground.DIRT)
	_ground(m, Rect2(236, 262, 22, 146), MapData.Ground.DIRT)
	for c in _cells(m, Rect2(712, 372, 120, 76)):
		var p := (Vector2(c) + Vector2(0.5, 0.5)) * m.cell_px
		if pow((p.x - 772) / 60.0, 2) + pow((p.y - 410) / 38.0, 2) < 1.0:
			m.water[m.idx(c)] = 1
	# along the street
	for b in [["cottage", 70, 228], ["cabin_red", 170, 228], ["townhouse", 270, 228], ["townhouse_rose", 356, 228],
			["shop_grocer", 470, 228], ["shop_bakery", 580, 228], ["inn", 722, 228],
			["shop_potion", 151, 384], ["cabin_blue", 247, 404]]:
		m.objects.append({"kind": "building", "id": b[0], "x": b[1], "y": b[2]})
	# the market
	var stalls := ["stall_fruit", "stall_fish", "stall_bread", "stall_veg"]
	for k in 4:
		m.objects.append({"kind": "building", "id": stalls[k], "x": 352 + k * 62, "y": 318})
		m.objects.append({"kind": "building", "id": stalls[(k + 2) % 4], "x": 352 + k * 62, "y": 382})
	# woods behind the houses and round the pond
	var taken: Array = []
	for i in 260:
		var p := Vector2(rng.randf_range(8, 872), rng.randf_range(10, 488))
		if _clear(m, p, taken):
			var r := rng.randf()
			var o := {"kind": "tree", "id": "oak" if r < 0.4 else ("birch" if r < 0.6 else ("pine" if r < 0.85 else "blossom")), "x": roundf(p.x), "y": roundf(p.y)}
			if _hides_building(m, p):  # crowns would hide a building front: a bush instead
				o = {"kind": "bush", "id": ["green", "flower", "berry"][rng.randi() % 3], "x": roundf(p.x), "y": roundf(p.y)}
			m.objects.append(o)
			taken.append(p)
	for i in 160:
		var p := Vector2(rng.randf_range(8, 872), rng.randf_range(10, 488))
		if _clear(m, p, taken, 6.0):
			m.objects.append({"kind": "flower", "id": MapWorld.FLOWERS[rng.randi() % MapWorld.FLOWERS.size()], "x": roundf(p.x), "y": roundf(p.y)})
			taken.append(p)
	m.spawn = Vector2(450, 248)
	var err := m.save("res://maps/town.json")
	print("maps/town.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _ground(m: MapData, r: Rect2, g: int) -> void:
	for c in _cells(m, r):
		m.ground[m.idx(c)] = g


func _cells(m: MapData, r: Rect2) -> Array:
	var out: Array = []
	for y in range(int(r.position.y / m.cell_px), int(ceilf(r.end.y / m.cell_px))):
		for x in range(int(r.position.x / m.cell_px), int(ceilf(r.end.x / m.cell_px))):
			if m.has_cell(Vector2i(x, y)):
				out.append(Vector2i(x, y))
	return out


## A tree here would stand in front of a building (its crown reaches ~100 px up).
func _hides_building(m: MapData, p: Vector2) -> bool:
	for o in m.objects:
		if o.kind == "building":
			var r := WorldBuilding.sprite_rect_of(o.id)
			if absf(p.x - o.x) < r.size.x / 2.0 + 44.0 and p.y > o.y - 20.0 and p.y < o.y + 125.0:
				return true
	return false


## Grass, away from water, the buildings, the street and the square, and from other plants.
func _clear(m: MapData, p: Vector2, taken: Array, spacing := 16.0) -> bool:
	var c := Vector2i(p / m.cell_px)
	if not m.has_cell(c) or m.water_at(c) or m.ground_at(c) != MapData.Ground.GRASS:
		return false
	for o in m.objects:
		if o.kind == "building":
			var r := WorldBuilding.sprite_rect_of(o.id).grow(6.0)
			r.position += Vector2(o.x, o.y)
			r.end.y += 10.0
			if r.has_point(p):
				return false
	if Vector2(p.x, p.y + 8).distance_to(Vector2(772, 410)) < 70.0 and m.water_at(Vector2i(Vector2(p.x, p.y + 10) / m.cell_px)):
		return false
	for q in taken:
		if q.distance_to(p) < spacing:
			return false
	return true

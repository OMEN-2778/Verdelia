extends SceneTree
## Writes maps/interior.json: a sample room built from the interior pieces, to try them out and to
## start interiors from in the map editor. Floorboards with stone flags round the kitchen corner,
## a row of back walls (a window, a picture, shelves), side walls running down to the front, corner
## posts, and the furniture: a fireplace, beds, a wardrobe, a bookshelf, the stove and dresser, a
## table set, rugs, a shop counter...
##   godot --headless --path . --script res://tools/editor/make_interior.gd

const LEFT := 16  ## inside of the left wall
const RIGHT := 240  ## inside of the right wall (7 back-wall segments of 32 px)
const BACK := 47  ## ground line of the back wall (its top reaches the map's top edge)

var m: MapData


func _init() -> void:
	m = MapData.create(Vector2i(32, 28))
	m.name = "室内样例"
	for i in m.ground.size():
		m.ground[i] = MapData.Ground.WOOD_FLOOR
	for c in _cells(Rect2(176, 40, 64, 72)):  # stone flags in the kitchen corner
		m.ground[m.idx(c)] = MapData.Ground.STONE_FLOOR
	var backs := ["wall_back", "wall_window", "wall_picture", "wall_back", "wall_shelf", "wall_window", "wall_back"]
	for k in backs.size():
		_put(backs[k], LEFT + 16 + 32 * k, BACK)
	var y := BACK - 5 + 32
	while y <= m.size_px().y - 8:
		_put("wall_side", LEFT - 4, y)
		_put("wall_side_r", RIGHT + 4, y)
		y += 32
	_put("wall_corner", LEFT - 4, BACK + 3)
	_put("wall_corner", RIGHT + 4, BACK + 3)
	for f in [["fireplace", 112, 15], ["bed", 16, 30], ["wardrobe", 46, 12], ["bookshelf", 72, 10], ["floor_lamp", 88, 40],
			["pot_plant", 152, 20], ["stove", 174, 14], ["dresser", 204, 12], ["chest", 18, 48], ["chair", 60, 70],
			["rug_round", 110, 70], ["table_set", 150, 75], ["rug_runner", 60, 112], ["bed_double", 30, 120],
			["counter", 184, 112]]:
		_put(f[0], LEFT + f[1], BACK + f[2])
	_check()
	m.spawn = Vector2(128, 210)
	var err := m.save("res://maps/interior.json")
	print("maps/interior.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _put(id: String, x: float, y: float) -> void:
	m.objects.append({"kind": "building", "id": id, "x": x, "y": y})


## Reports pieces that overlap one another or leave the map.
func _check() -> void:
	var bs := m.objects
	for i in bs.size():
		var a := MapWorld.building_rect(bs[i])
		if not Rect2(Vector2.ZERO, m.size_px()).encloses(a):
			print("off the map: ", bs[i].id)
		if not WorldBuilding.is_solid(bs[i].id):
			continue
		for j in range(i + 1, bs.size()):
			if WorldBuilding.is_solid(bs[j].id) and a.intersects(MapWorld.building_rect(bs[j])):
				print("overlap: ", bs[i].id, " ", bs[j].id)


func _cells(r: Rect2) -> Array:
	var out: Array = []
	for cy in range(int(r.position.y / m.cell_px), int(ceilf(r.end.y / m.cell_px))):
		for cx in range(int(r.position.x / m.cell_px), int(ceilf(r.end.x / m.cell_px))):
			if m.has_cell(Vector2i(cx, cy)):
				out.append(Vector2i(cx, cy))
	return out

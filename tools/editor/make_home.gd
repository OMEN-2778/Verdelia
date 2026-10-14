extends SceneTree
## Writes maps/home.json: the hero's home, two bedrooms, a sitting room and a small kitchen.
##   - The hero's room (top left): full of things but tidy. A desk under the window, a bookshelf,
##     the wardrobe, a chest, plants, a rug, and the double bed turned sideways along the wall,
##     with the secret little monster peeping out from the dark under it.
##   - Grandmother's room (top right), cleared since she died: the bed stripped, her things packed
##     in tied boxes, her armchair and cabinet under dust sheets, her portrait on the wall.
##   - The sitting room (bottom left), hardly used: sofa, armchair, a low table, a cold fireplace.
##   - The kitchen (bottom right), tiny, on stone flags: the stove, the dresser, a table for two.
##   godot --headless --path . --script res://tools/editor/make_home.gd

const LEFT := 16  ## inside of the outer walls
const RIGHT := 304
const BACK := 47  ## the back wall of the bedrooms
const MID := 190  ## the wall between the bedrooms and the rooms below (the strip just above it,
## hidden behind it, is left as floor to walk on)
const SPLIT_TOP := 176  ## between the bedrooms
const SPLIT_LOW := 208  ## between the sitting room and the kitchen

var m: MapData


func _init() -> void:
	m = MapData.create(Vector2i(40, 42))
	m.name = "主角的家"
	m.indoor = true
	for i in m.ground.size():
		m.ground[i] = MapData.Ground.WOOD_FLOOR
	for c in _cells(Rect2(SPLIT_LOW + 4, MID - 8, RIGHT - SPLIT_LOW + 4, 170)):  # (the wall itself stands on the edge)
		m.ground[m.idx(c)] = MapData.Ground.STONE_FLOOR
	# walls: the back of the bedrooms, the middle wall with the bedroom doors, the outer and inner sides
	_row(BACK, ["wall_shelf", "wall_window", "wall_picture", "wall_back", "wall_back",
		"wall_back", "wall_portrait", "wall_window", "wall_back"])
	_row(MID, ["wall_back", "wall_door", "wall_picture", "wall_back", "wall_back",
		"wall_door", "wall_shelf", "wall_window", "wall_back"])
	var y := BACK - 5 + 32
	while y <= m.size_px().y:
		_put("wall_side", LEFT - 4, y)
		_put("wall_side_r", RIGHT + 4, y)
		y += 32
	for yy in [BACK - 5 + 32, BACK - 5 + 64, BACK - 5 + 96, BACK - 5 + 128]:
		_put("wall_side", SPLIT_TOP, yy)
	for yy in [MID - 5 + 32, MID - 5 + 64, MID - 5 + 128]:  # a doorway between them: the third segment left out
		_put("wall_side", SPLIT_LOW, yy)
	_put("wall_corner", LEFT - 4, BACK + 3)
	_put("wall_corner", RIGHT + 4, BACK + 3)
	# the hero's room
	_put("desk", 64, 64)
	_put("bookshelf", 128, 57)
	_put("wardrobe", 158, 60)
	_put("chest", 30, 60)
	_put("pot_plant", 94, 58)
	_put("bed_side", 46, 134)
	_put("rug_round", 118, 122)
	_put("floor_lamp", 164, 116)
	_put("pot_plant", 166, 140)
	# grandmother's room
	_put("bed_bare", 284, 88)
	_put("covered_cabinet", 196, 62)
	_put("boxes_packed", 230, 72)
	_put("covered_chair", 236, 132)
	_put("boxes_packed", 286, 138)
	# the sitting room
	_put("fireplace_cold", 112, MID + 19)
	_put("sofa", 104, 262)
	_put("coffee_table", 104, 292)
	_put("armchair", 166, 270)
	_put("pot_plant", 30, MID + 16)
	_put("doormat", 52, 332)
	# the kitchen
	_put("stove", 236, MID + 18)
	_put("dresser", 284, MID + 16)
	_put("table_small", 258, 280)
	_put("pot_plant", 292, 326)
	_check()
	m.spawn = Vector2(52, 324)
	var err := m.save("res://maps/home.json")
	print("maps/home.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _row(y: int, ids: Array) -> void:
	for k in ids.size():
		_put(ids[k], LEFT + 16 + 32 * k, y)


func _put(id: String, x: float, y: float) -> void:
	m.objects.append({"kind": "building", "id": id, "x": x, "y": y})


## Reports furniture that overlaps (walls among themselves may touch) or leaves the map.
func _check() -> void:
	var bs := m.objects
	for i in bs.size():
		var a := MapWorld.building_rect(bs[i])
		if not Rect2(Vector2.ZERO, m.size_px()).encloses(a):
			print("off the map: ", bs[i].id, " ", a)
		if not WorldBuilding.is_solid(bs[i].id):
			continue
		for j in range(i + 1, bs.size()):
			if WorldBuilding.is_solid(bs[j].id) and a.intersects(MapWorld.building_rect(bs[j])):
				if not (bs[i].id.begins_with("wall") and bs[j].id.begins_with("wall")):
					print("overlap: ", bs[i].id, " ", bs[j].id)


func _cells(r: Rect2) -> Array:
	var out: Array = []
	for cy in range(int(r.position.y / m.cell_px), int(ceilf(r.end.y / m.cell_px))):
		for cx in range(int(r.position.x / m.cell_px), int(ceilf(r.end.x / m.cell_px))):
			if m.has_cell(Vector2i(cx, cy)):
				out.append(Vector2i(cx, cy))
	return out

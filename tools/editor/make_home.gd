extends SceneTree
## Writes maps/home.json: the hero's home, laid out like the house outside: a small wing on the
## left (the kitchen) joined to the larger main block on the right, whose front door is right of
## the middle; stairs in the sitting room go up to the attic (maps/home_attic.json).
##   - The hero's room (main block, back left): full of things but tidy. A desk under the window, a
##     bookshelf, the wardrobe, a chest, a lamp, a rug, and the double bed turned sideways against
##     the wall, with the secret little monster peeping out from the dark under it.
##   - Grandmother's room (main block, back right), cleared since she died: the bed stripped, her
##     things packed in tied boxes, her armchair and cabinet under dust sheets, her portrait.
##   - The sitting room (main block, front), hardly used: sofa, armchair, a low table, the cold
##     fireplace, and the stairs up against the right wall. The front door opens into it.
##   - The kitchen (the wing), tiny, on stone flags: the stove, the dresser, a table for two; a
##     doorway through to the sitting room.
## Everything outside the rooms is VOID ground (black, not walkable).
##   godot --headless --path . --script res://tools/editor/make_home.gd

const WING_L := 16  ## inside of the wing's left wall
const MAIN_L := 80  ## the wall between the wing and the main block
const RIGHT := 304  ## inside of the main block's right wall (7 segments)
const BACK := 47  ## the main block's back wall
const WING_BACK := 111  ## the wing's back wall (the wing is shallower)
const MID := 166  ## the wall between the bedrooms and the sitting room (the strip just above it,
## hidden behind it, is left as floor to walk on)
const SPLIT := 208  ## between the two bedrooms
const WING_FRONT := 239  ## the wing's front wall (a low strip, so the room stays in view)
const FRONT := 271  ## the main block's front wall, with the front door
const DOOR_X := 224  ## the front door
const STAIRS := Vector2(290, 203)  ## the foot of the stairs (they rise to the back, against MID)

var m: MapData


func _init() -> void:
	m = MapData.create(Vector2i(40, 36))
	m.name = "主角的家"
	m.indoor = true
	for cy in m.size.y:
		for cx in m.size.x:
			var c := Vector2i(cx, cy)
			var p := (Vector2(c) + Vector2(0.5, 0.5)) * m.cell_px
			var g := MapData.Ground.WOOD_FLOOR
			if p.x < MAIN_L - 4:  # the wing
				if p.x < WING_L - 8 or p.y < WING_BACK - 8 or p.y > WING_FRONT + 1:
					g = MapData.Ground.VOID
				else:
					g = MapData.Ground.STONE_FLOOR
			elif p.x > RIGHT + 8 or p.y > FRONT + 1:
				g = MapData.Ground.VOID
			m.ground[m.idx(c)] = g
	# the main block: its back wall over both bedrooms, the middle wall with their doors, the front
	_row(MAIN_L, BACK, ["wall_back", "wall_picture", "wall_window", "wall_back",
		"wall_back", "wall_portrait", "wall_window"])
	_row(MAIN_L, MID, ["wall_picture", "wall_back", "wall_door", "wall_back", "wall_back", "wall_door", "wall_back"])
	var fronts: Array = []
	for k in 7:
		fronts.append("wall_front_door" if MAIN_L + 16 + 32 * k == DOOR_X else "wall_front")
	_row(MAIN_L, FRONT, fronts)
	# the wing: back wall with the kitchen window, the low front
	_row(WING_L, WING_BACK, ["wall_shelf", "wall_window"])
	_row(WING_L, WING_FRONT, ["wall_front", "wall_front"])
	# side walls, 32 px a segment
	var y := BACK - 5 + 32
	while y <= FRONT:
		if y != WING_BACK - 5 + 32 * 3:  # the kitchen doorway (the third segment beside the wing)
			_put("wall_side", MAIN_L - 4, y)
		_put("wall_side_r", RIGHT + 4, y)
		y += 32
	y = WING_BACK - 5 + 32
	while y <= WING_FRONT:
		_put("wall_side", WING_L - 4, y)
		y += 32
	# the wall between the bedrooms runs right up to the back of MID (its end hidden behind it), so
	# the rooms are closed off from each other, even along the strip behind MID
	for yy in [BACK - 5 + 32, BACK - 5 + 64, BACK - 5 + 96, MID - 5]:
		_put("wall_side", SPLIT, yy)
	_put("wall_corner", MAIN_L - 4, BACK + 3)
	_put("wall_corner", RIGHT + 4, BACK + 3)
	_put("wall_corner", WING_L - 4, WING_BACK + 3)
	_put("wall_corner", MAIN_L - 4, WING_BACK + 3)
	# the hero's room: small and full, everything in its place. The tall wardrobe stands behind the
	# bed's head (the bed hides only its foot), the desk under the window, the chest at the bed's foot
	_put("bed_side", MAIN_L + 29, 104)
	_put("wardrobe", MAIN_L + 14, 60)
	_put("desk", 150, 64)
	_put("bookshelf", 188, 57)
	_put("chest", 150, 104)
	_put("rug_round", 178, 116)
	_put("floor_lamp", 200, 100)
	# grandmother's room
	_put("covered_cabinet", 227, 62)
	_put("boxes_packed", 256, 70)
	_put("bed_bare", 288, 96)
	_put("covered_chair", 232, 112)
	# the sitting room
	_put("fireplace_cold", 208, MID + 19)
	_put("sofa", 200, 228)
	_put("coffee_table", 200, 254)
	_put("armchair", 254, 230)
	_put("pot_plant", MAIN_L + 14, 262)
	_put("stairs", STAIRS.x, STAIRS.y, {"to": "res://maps/home_attic.json", "at": [200, 126]})
	_put("doormat", DOOR_X, 266)
	# the kitchen
	_put("stove", 32, WING_BACK + 18)
	_put("pot_plant", 57, WING_BACK + 12)
	_put("table_small", 44, 196)
	# the rooms, for the lights at night: the floor you stand on in each (the strip hidden behind
	# MID belongs to the bedroom above it) and what its light covers on screen (its floor and its
	# walls, up to the top of its back wall, 45 px above the wall's foot)
	m.rooms = [
		_room("主角的卧室", [MAIN_L, BACK, SPLIT - MAIN_L, MID - 5 - BACK], [MAIN_L - 4, 0, SPLIT - MAIN_L + 4, MID - 45]),
		_room("奶奶的房间", [SPLIT, BACK, RIGHT - SPLIT, MID - 5 - BACK], [SPLIT, 0, RIGHT - SPLIT + 4, MID - 45]),
		_room("客厅", [MAIN_L - 4, MID - 5, RIGHT - MAIN_L + 4, FRONT - MID + 5],
			[MAIN_L - 4, MID - 45, RIGHT - MAIN_L + 8, FRONT - MID + 46]),
		_room("厨房", [WING_L, WING_BACK, MAIN_L - 4 - WING_L, WING_FRONT - WING_BACK],
			[WING_L - 4, WING_BACK - 45, MAIN_L - WING_L, WING_FRONT - WING_BACK + 46]),
	]
	_check()
	m.spawn = Vector2(DOOR_X, 252)
	var err := m.save("res://maps/home.json")
	print("maps/home.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _room(room_name: String, area: Array, light: Array) -> Dictionary:
	return {"name": room_name, "area": [area], "light": [light]}


func _row(x0: int, y: int, ids: Array) -> void:
	for k in ids.size():
		_put(ids[k], x0 + 16 + 32 * k, y)


func _put(id: String, x: float, y: float, extra := {}) -> void:
	var o := {"kind": "building", "id": id, "x": x, "y": y}
	o.merge(extra)
	m.objects.append(o)


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

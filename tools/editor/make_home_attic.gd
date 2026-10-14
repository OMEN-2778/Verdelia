extends SceneTree
## Writes maps/home_attic.json: the attic of the hero's home, under the main block's roof. Low knee
## walls with the roof boards and rafters above them, a post holding up the roof, the dormer
## window (left of the middle, as on the house outside) with the hero's reading nook under it, and
## old things stored round the edges: grandmother's trunk, boxes, crates, a covered chair. The
## stairs come up through the hatch on the right (it leads back down to maps/home.json).
##   godot --headless --path . --script res://tools/editor/make_home_attic.gd

const LEFT := 16
const RIGHT := 240  ## 7 segments, the width of the main block below
const BACK := 47
const FRONT := 143  ## the low front edge under the roof's other slope
const HATCH := Vector2(226, 110)  ## above the stairs

var m: MapData


func _init() -> void:
	m = MapData.create(Vector2i(32, 20))
	m.name = "阁楼"
	m.indoor = true
	for cy in m.size.y:
		for cx in m.size.x:
			var p := (Vector2(cx, cy) + Vector2(0.5, 0.5)) * m.cell_px
			var void_ := p.x < LEFT - 8 or p.x > RIGHT + 8 or p.y > FRONT + 1
			m.ground[m.idx(Vector2i(cx, cy))] = MapData.Ground.VOID if void_ else MapData.Ground.WOOD_FLOOR
	var backs: Array = []
	for k in 7:
		backs.append("wall_attic_window" if k == 2 else "wall_attic")
	_row(BACK, backs)
	var fronts: Array = []
	for k in 7:
		fronts.append("wall_front")
	_row(FRONT, fronts)
	var y := BACK - 5 + 32
	while y <= FRONT:
		_put("wall_side", LEFT - 4, y)
		_put("wall_side_r", RIGHT + 4, y)
		y += 32
	_put("wall_corner", LEFT - 4, BACK + 3)
	_put("wall_corner", RIGHT + 4, BACK + 3)
	# the reading nook under the dormer
	_put("reading_nook", 96, 80)
	# the post holding up the roof
	_put("attic_post", 138, 108)
	# stored things round the edges
	_put("trunk_old", 38, 64)
	_put("covered_chair", 168, 68)
	_put("bookshelf", 200, 57)
	_put("chest", 30, 136)
	_put("crates", 62, 136)
	_put("boxes_packed", 112, 136)
	_put("attic_hatch", HATCH.x, HATCH.y, {"to": "res://maps/home.json", "at": [266, 214]})
	m.rooms = [{"name": "阁楼", "area": [[LEFT, BACK, RIGHT - LEFT, FRONT - BACK]],
		"light": [[LEFT - 2, BACK - 40, RIGHT - LEFT + 4, FRONT - 11 - (BACK - 40)]]}]  # one room, lit whenever
	# you are up here: between the inner faces of its walls (as in make_home.gd)
	_check()
	m.spawn = Vector2(200, 126)
	var err := m.save("res://maps/home_attic.json")
	print("maps/home_attic.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _row(y: int, ids: Array) -> void:
	for k in ids.size():
		_put(ids[k], LEFT + 16 + 32 * k, y)


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

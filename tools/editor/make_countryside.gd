extends SceneTree
## Writes maps/countryside.json: a sample of the countryside assets to try out (and to start from
## in the map editor). West of a river: a farm (coop, animal shed, greenhouse, silo, tool shed,
## beehives, a fenced field with a scarecrow...) and, below it, ruins in the grass, a forest
## shrine, a camp and a mine. Across the river (a stone bridge and a footbridge, a watermill on its
## bank): a village square with the chapel, the clock tower, the town hall, the clinic, the
## library and the museum round a fountain, lamps and benches; below it a lake with a pier,
## rowboats, a lighthouse and the harbour warehouse. Mountains beyond the north edge.
##   godot --headless --path . --script res://tools/editor/make_countryside.gd

const W := 200
const H := 120
## open ground kept free of trees: round the camp, among the ruins, in front of the mine and the mill
const CLEARINGS := [Rect2(470, 730, 260, 150), Rect2(90, 500, 330, 250), Rect2(90, 880, 140, 60), Rect2(760, 470, 140, 80)]

var m: MapData


func _init() -> void:
	m = MapData.create(Vector2i(W, H))
	m.name = "乡间"
	m.vista = "mountains"
	var rng := RandomNumberGenerator.new()
	rng.seed = 2779
	# water: the river from the north edge down into the lake, a channel, the mill race
	_water_rect(Rect2(900, 0, 28, 640))
	_water_rect(Rect2(900, 600, 160, 40))
	_water_rect(Rect2(866, 474, 40, 30))
	for c in _cells(Rect2(1000, 440, 600, 360)):
		var p := (Vector2(c) + Vector2(0.5, 0.5)) * m.cell_px
		if pow((p.x - 1300) / 260.0, 2) + pow((p.y - 620) / 150.0, 2) < 1.0:
			m.water[m.idx(c)] = 1
	# ground: the paved square and its street, dirt lanes, the field
	_ground(Rect2(990, 260, 580, 150), MapData.Ground.PAVED)
	_ground(Rect2(940, 296, 60, 24), MapData.Ground.PAVED)
	_ground(Rect2(60, 296, 840, 22), MapData.Ground.DIRT)  # lane from the farm to the bridge
	_ground(Rect2(420, 318, 22, 420), MapData.Ground.DIRT)  # down to the ruins and the camp
	_ground(Rect2(262, 228, 300, 112), MapData.Ground.TILLED)
	# the farm
	_put([["animal_shed", 140, 150], ["coop", 360, 130], ["greenhouse", 510, 150], ["silo", 650, 160],
		["tool_shed", 790, 160], ["stable", 140, 400], ["shipping_bin", 720, 270], ["compost_bin", 640, 360],
		["beehives", 260, 410], ["trellis", 760, 400], ["hay_bales", 40, 260], ["woodpile", 850, 260]])
	_put([["scarecrow", 410, 290]])
	# the field's fence: rows across at y 222 and 352, runs back at x 256 and 576, a gate in front
	for x in range(272, 576, 32):
		_put([["fence_x", x, 222]])
		_put([["fence_gate" if x == 432 else "fence_x", x, 352]])
	for y in range(254, 353, 32):
		_put([["fence_y", 256, y], ["fence_y", 576, y]])
	# ruins, shrine, camp, tower, mine
	_put([["column", 120, 560], ["column_vines", 200, 556], ["column_broken", 290, 580], ["column_fallen", 190, 640],
		["ruin_arch", 360, 610], ["ruin_wall", 540, 580], ["obelisk", 300, 720], ["shrine", 680, 560],
		["tent", 540, 790], ["campfire", 620, 830], ["watchtower", 780, 720], ["mine", 150, 880]])
	# the river: bridges and the mill
	_put([["bridge_x", 914, 308], ["footbridge", 914, 150], ["watermill", 840, 472]])
	# the village square
	_put([["chapel", 1060, 250], ["clock_tower", 1130, 254], ["town_hall", 1250, 256], ["clinic", 1400, 250],
		["library", 1520, 252], ["fountain", 1250, 360], ["museum", 1110, 490]])
	_put([["street_lamp", 1010, 300], ["street_lamp", 1480, 300], ["street_lamp_double", 1010, 404],
		["street_lamp_double", 1480, 404], ["bench", 1160, 400], ["bench", 1340, 400], ["bench_stone", 1250, 420],
		["planter", 1160, 330], ["planter", 1340, 330], ["planter_round", 1560, 360], ["notice_board", 1330, 290],
		["postbox", 1450, 270], ["signpost", 960, 330], ["barrel_planter", 1180, 270], ["barrel_planter", 1580, 270]])
	# the lake
	_put([["dock", 1180, 766], ["rowboat", 1300, 600], ["rowboat_red", 1390, 680], ["lighthouse", 1560, 480],
		["warehouse", 990, 770]])
	_put([["stone_wall_x", 1090, 880], ["stone_wall_x", 1122, 880], ["stone_wall_x", 1154, 880], ["stone_wall_post", 1176, 880],
		["hay_bales", 1260, 860], ["crates", 1060, 790], ["barrels", 1120, 780]])
	_check()
	# woods round it all, flowers
	var taken: Array = []
	for i in 700:
		var p := Vector2(rng.randf_range(8, W * 8 - 8), rng.randf_range(12, H * 8 - 6))
		if _clear(p, taken, 18.0, 70.0) and not CLEARINGS.any(func(r: Rect2) -> bool: return r.has_point(p)):
			var r := rng.randf()
			m.objects.append({"kind": "tree", "id": "oak" if r < 0.4 else ("birch" if r < 0.6 else ("pine" if r < 0.85 else "blossom")),
				"x": roundf(p.x), "y": roundf(p.y)})
			taken.append(p)
	for i in 400:
		var p := Vector2(rng.randf_range(8, W * 8 - 8), rng.randf_range(12, H * 8 - 6))
		if _clear(p, taken, 7.0, 6.0):
			var f: Array = MapWorld.FLOWERS
			m.objects.append({"kind": "flower", "id": f[rng.randi() % f.size()], "x": roundf(p.x), "y": roundf(p.y)})
			taken.append(p)
	# the fixer, at work on the mill
	m.objects.append({"kind": "npc", "id": "fixer", "x": 806, "y": 500, "act": "work", "face": "right"})
	m.spawn = Vector2(980, 330)  # at the east end of the stone bridge
	var err := m.save("res://maps/countryside.json")
	print("maps/countryside.json: ", error_string(err), ", ", m.objects.size(), " objects")
	quit()


func _put(list: Array) -> void:
	for b in list:
		m.objects.append({"kind": "building", "id": b[0], "x": b[1], "y": b[2]})


## Reports buildings whose footprints overlap, stand where they may not, or leave the map.
func _check() -> void:
	var bs := m.objects.filter(func(o): return o.kind == "building")
	for i in bs.size():
		var a := MapWorld.building_rect(bs[i])
		if not Rect2(Vector2.ZERO, m.size_px()).encloses(a):
			print("off the map: ", bs[i].id)
		var place := WorldBuilding.place_of(bs[i].id)
		var wet := 0
		var cells := 0
		for c in _cells(a):
			cells += 1
			wet += 1 if m.water_at(c) else 0
		if place == "" and wet > 0:
			print("on water: ", bs[i].id, " ", wet, "/", cells)
		if place == "water" and wet < cells:
			print("not on water: ", bs[i].id)
		for j in range(i + 1, bs.size()):
			if a.intersects(MapWorld.building_rect(bs[j])):
				print("overlap: ", bs[i].id, " ", bs[j].id)


func _water_rect(r: Rect2) -> void:
	for c in _cells(r):
		m.water[m.idx(c)] = 1


func _ground(r: Rect2, g: int) -> void:
	for c in _cells(r):
		m.ground[m.idx(c)] = g


func _cells(r: Rect2) -> Array:
	var out: Array = []
	for y in range(int(r.position.y / m.cell_px), int(ceilf(r.end.y / m.cell_px))):
		for x in range(int(r.position.x / m.cell_px), int(ceilf(r.end.x / m.cell_px))):
			if m.has_cell(Vector2i(x, y)):
				out.append(Vector2i(x, y))
	return out


## Grass, away from water, lanes and paving, buildings (with `room` above them for tree crowns)
## and other plants.
func _clear(p: Vector2, taken: Array, spacing: float, room: float) -> bool:
	var c := Vector2i(p / m.cell_px)
	if not m.has_cell(c) or m.water_at(c) or m.ground_at(c) != MapData.Ground.GRASS:
		return false
	if m.water_at(Vector2i(Vector2(p.x, p.y + 10) / m.cell_px)) or m.water_at(Vector2i(Vector2(p.x + 10, p.y) / m.cell_px)) \
			or m.water_at(Vector2i(Vector2(p.x - 10, p.y) / m.cell_px)):
		return false
	for o in m.objects:
		if o.kind == "building":
			var r := WorldBuilding.sprite_rect_of(o.id).grow(6.0)
			r.position += Vector2(o.x, o.y)
			r.end.y += room
			if r.has_point(p):
				return false
	for q in taken:
		if q.distance_to(p) < spacing:
			return false
	return true

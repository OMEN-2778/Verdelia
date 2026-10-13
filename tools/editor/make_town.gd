extends SceneTree
## Writes maps/town.json: a small sample town to try the buildings in (and to start from in the
## map editor). A brick-paved high street of houses, shops, the smithy, the inn, a manor and a
## tower; a busy market square of stalls, tents, a wagon and a well; a farm corner with the hero's
## home, a barn, a windmill and a field; dirt lanes, a pond and woods round it all, with a clearing
## at the north edge to look out over the mountain vista from.
##   godot --headless --path . --script res://tools/editor/make_town.gd


const LOOKOUT := Rect2(470, 0, 300, 100)  ## a treeless clearing at the north edge, for the view


func _init() -> void:
	var m := MapData.create(Vector2i(150, 84))
	m.name = "小镇"
	var rng := RandomNumberGenerator.new()
	rng.seed = 2778
	# brick high street and market square, dirt lanes, a field by the barn, a pond
	_ground(m, Rect2(0, 280, 1200, 32), MapData.Ground.PAVED)
	_ground(m, Rect2(296, 312, 470, 216), MapData.Ground.PAVED)
	_ground(m, Rect2(140, 312, 22, 120), MapData.Ground.DIRT)
	_ground(m, Rect2(234, 312, 22, 142), MapData.Ground.DIRT)
	_ground(m, Rect2(900, 312, 22, 190), MapData.Ground.DIRT)  # lane down to the farm
	_ground(m, Rect2(900, 480, 130, 22), MapData.Ground.DIRT)
	_ground(m, Rect2(860, 540, 330, 104), MapData.Ground.TILLED)
	for c in _cells(m, Rect2(40, 520, 200, 120)):
		var p := (Vector2(c) + Vector2(0.5, 0.5)) * m.cell_px
		if pow((p.x - 140) / 92.0, 2) + pow((p.y - 580) / 50.0, 2) < 1.0:
			m.water[m.idx(c)] = 1
	# the high street
	for b in [["cottage", 60, 276], ["cabin_red", 150, 276], ["townhouse", 242, 276], ["townhouse_rose", 324, 276],
			["shop_grocer", 424, 276], ["shop_bakery", 528, 276], ["smithy", 652, 276], ["inn", 790, 276],
			["manor", 962, 276], ["tower", 1100, 276],
			["shop_potion", 151, 430], ["cabin_blue", 245, 452], ["barn", 1000, 474], ["windmill", 1122, 470],
			["player_home", 830, 474]]:
		m.objects.append({"kind": "building", "id": b[0], "x": b[1], "y": b[2]})
	# the market
	for b in [["sail_arms", 350, 372], ["produce_stand", 450, 372], ["bake_table", 548, 372], ["sail_cloth", 648, 372],
			["pavilion", 352, 470], ["stall_fruit", 440, 452], ["stall_fish", 506, 452], ["sail_pottery", 592, 462],
			["wagon", 704, 468], ["well", 530, 512], ["banner_red", 304, 330], ["banner_blue", 756, 330],
			["barrels", 742, 400], ["crates", 412, 404], ["weapon_rack", 320, 400], ["armour", 300, 384],
			["dining", 820, 340], ["dining", 868, 352], ["barrels", 896, 320], ["banner_red", 1046, 470],
			["crates", 1160, 486], ["rug", 470, 492]]:
		m.objects.append({"kind": "building", "id": b[0], "x": b[1], "y": b[2]})
	# woods behind the houses and round the edges, bushes nearer the buildings, flowers
	var taken: Array = []
	for i in 420:
		var p := Vector2(rng.randf_range(8, 1192), rng.randf_range(10, 664))
		if _clear(m, p, taken) and not LOOKOUT.has_point(p):
			var r := rng.randf()
			var o := {"kind": "tree", "id": "oak" if r < 0.4 else ("birch" if r < 0.6 else ("pine" if r < 0.85 else "blossom")), "x": roundf(p.x), "y": roundf(p.y)}
			if _hides_building(m, p):  # crowns would hide a building front: a bush instead
				o = {"kind": "bush", "id": ["green", "flower", "berry"][rng.randi() % 3], "x": roundf(p.x), "y": roundf(p.y)}
			m.objects.append(o)
			taken.append(p)
	for i in 260:
		var p := Vector2(rng.randf_range(8, 1192), rng.randf_range(10, 664))
		if _clear(m, p, taken, 6.0):
			m.objects.append({"kind": "flower", "id": MapWorld.FLOWERS[rng.randi() % MapWorld.FLOWERS.size()], "x": roundf(p.x), "y": roundf(p.y)})
			taken.append(p)
	m.spawn = Vector2(843, 494)  # on the hero's doorstep
	m.vista = "mountains"
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
	if m.water_at(Vector2i(Vector2(p.x, p.y + 10) / m.cell_px)):
		return false
	for q in taken:
		if q.distance_to(p) < spacing:
			return false
	return true

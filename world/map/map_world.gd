class_name MapWorld
extends Node2D
## Builds a living world from a MapData: ground (Terrain), water (WaterLayer), grass, trees,
## bushes, rocks and flowers, buildings, cliffs with their ramps, the far view beyond the north
## edge (Vista), and everything that blocks walking. The map
## editor edits it live through the paint_* / add_* / remove_* calls; the game just load_map()s.
##
## Walking is worked out from what is drawn: water blocks (a shallow rim along the shore stays
## walkable), cliffs block except at ramps, trees block at the trunk and bushes and rocks at the
## base, buildings at their walls, and the passage grid can block any cell or open a water cell (a
## bridge); a deck building (a pier, a stone bridge) makes the water under it walkable.

signal rebuilt
## A building linked to another map ({..., "to": "res://maps/x.json", "at": [x, y]}) was walked
## into at its door: `to` is the map, `at` where to arrive in it (spawn if (-1, -1)).
signal door_used(to: String, at: Vector2)

const FLOWERS := [
	"res://art/library/flowers/daisy.png", "res://art/library/flowers/buttercup.png",
	"res://art/library/flowers/bluebell.png", "res://art/library/flowers/clover.png",
	"res://art/library/flowers/poppy.png", "res://art/library/flowers/forgetmenot.png",
	"res://art/library/flowers/lavender.png", "res://art/library/flowers/dandelion.png",
]
const GROUND_KIND := [Terrain.Kind.GRASS, Terrain.Kind.DIRT, Terrain.Kind.SAND, Terrain.Kind.TILLED, Terrain.Kind.WATERED, Terrain.Kind.PAVED,
	Terrain.Kind.WOOD_FLOOR, Terrain.Kind.STONE_FLOOR, Terrain.Kind.VOID]
const SHORE_INSET := 3.0  ## px of shallow water along the shore you can still wade in

var data: MapData
var vista: Vista
var terrain: Terrain
var water_layer: WaterLayer
var grass: GrassField
var cliffs_root: Node2D
var props: Node2D
var blockers: StaticBody2D
var bridges: BridgeLayer
var _obj_nodes: Array = []  # parallel to data.objects
var _cliff_nodes: Array = []  # parallel to data.cliffs
var _ground_tex: ImageTexture
var _water_tex: ImageTexture
var _decks := {}  # cells under deck buildings (piers, bridges): walkable even over water


func _ready() -> void:
	vista = Vista.new()
	vista.name = "Vista"
	vista.kind = ""
	add_child(vista)
	terrain = Terrain.new()
	terrain.name = "Terrain"
	add_child(terrain)
	water_layer = WaterLayer.new()
	water_layer.name = "Water"
	add_child(water_layer)
	water_layer.terrain = terrain
	bridges = BridgeLayer.new()
	bridges.name = "Bridges"
	bridges.world = self
	add_child(bridges)
	cliffs_root = Node2D.new()
	cliffs_root.name = "Cliffs"
	add_child(cliffs_root)
	grass = GrassField.new()
	grass.name = "Grass"
	add_child(grass)
	grass.terrain = terrain
	props = Node2D.new()
	props.name = "Props"
	props.y_sort_enabled = true
	add_child(props)
	blockers = StaticBody2D.new()
	blockers.name = "Blockers"
	add_child(blockers)
	load_data(data if data != null else MapData.create(Vector2i(120, 68)))  # data may be set before entering the tree


func load_map(path: String) -> bool:
	var d := MapData.load_file(path)
	if d == null:
		return false
	load_data(d)
	return true


func load_data(d: MapData) -> void:
	data = d
	if not is_inside_tree():
		return
	for n in _obj_nodes:
		n.queue_free()
	for n in _cliff_nodes:
		n.queue_free()
	_obj_nodes.clear()
	_cliff_nodes.clear()
	terrain.cell_px = data.cell_px
	terrain.map_size_px = Vector2i(data.size * data.cell_px)
	_ground_tex = ImageTexture.create_from_image(_ground_image())
	_water_tex = ImageTexture.create_from_image(_water_image())
	terrain.mask = _ground_tex
	terrain.water_mask = _water_tex
	for c in data.cliffs:
		_cliff_nodes.append(_make_cliff(c))
	for o in data.objects:
		_obj_nodes.append(_make_object(o))
	terrain.rebuild()
	_rebuild_blockers()
	bridges.refresh()
	vista.kind = data.vista
	rebuilt.emit()


# ------------------------------------------------------------------ editing

func paint_ground(cells: Array, g: int) -> void:
	var keep: Array = []
	for c in cells:
		if data.has_cell(c):
			data.ground[data.idx(c)] = g
			keep.append(c)
	terrain.set_ground_cells(keep, GROUND_KIND[g])


func paint_water(cells: Array, on: bool) -> void:
	var keep: Array = []
	for c in cells:
		if data.has_cell(c):
			data.water[data.idx(c)] = 1 if on else 0
			keep.append(c)
	terrain.set_water_cells(keep, on)


func set_vista(kind: String) -> void:
	data.vista = kind
	vista.kind = kind


func paint_passage(cells: Array, v: int) -> void:
	for c in cells:
		if data.has_cell(c):
			data.passage[data.idx(c)] = v


func add_object(o: Dictionary) -> void:
	data.objects.append(o)
	_obj_nodes.append(_make_object(o))
	if _is_deck(o):
		_rebuild_blockers()


## Removes objects whose base lies in any of `cells` (buildings: anywhere on their walls); returns
## how many. `buildings` false leaves buildings alone (the plant eraser).
func remove_objects_in(cells: Array, buildings := true) -> int:
	var hit := {}
	for c in cells:
		hit[c] = true
	var cp := float(data.cell_px)
	var removed := 0
	var decks_gone := false
	for i in range(data.objects.size() - 1, -1, -1):
		var o: Dictionary = data.objects[i]
		var on := false
		if o.kind == "building":
			if not buildings:
				continue
			var r := building_rect(o)
			for c in hit:
				if r.intersects(Rect2(Vector2(c) * cp, Vector2(cp, cp))):
					on = true
					break
		else:
			on = hit.has(Vector2i(floori(o.x / cp), floori(o.y / cp)))
		if on:
			if _is_deck(o):
				decks_gone = true
			_obj_nodes[i].queue_free()
			_obj_nodes.remove_at(i)
			data.objects.remove_at(i)
			removed += 1
	if decks_gone:
		_rebuild_blockers()
	return removed


func object_near(p: Vector2, radius: float) -> bool:
	for o in data.objects:
		if o.kind == "building":
			if building_rect(o).grow(radius * 0.5).has_point(p):
				return true
		elif Vector2(o.x, o.y).distance_to(p) < radius:
			return true
	return false


## The ground a building stands on, in world px.
static func building_rect(o: Dictionary) -> Rect2:
	var r := WorldBuilding.footprint_of(o.id)
	r.position += Vector2(o.x, o.y)
	return r


## Index of the building whose picture covers `p`, or -1.
func building_at(p: Vector2) -> int:
	for i in range(data.objects.size() - 1, -1, -1):
		var o: Dictionary = data.objects[i]
		if o.kind == "building":
			var r := WorldBuilding.sprite_rect_of(o.id)
			r.position += Vector2(o.x, o.y)
			if r.has_point(p):
				return i
	return -1


func remove_object(i: int) -> void:
	var deck := _is_deck(data.objects[i])
	_obj_nodes[i].queue_free()
	_obj_nodes.remove_at(i)
	data.objects.remove_at(i)
	if deck:
		_rebuild_blockers()


static func _is_deck(o: Dictionary) -> bool:
	return o.kind == "building" and WorldBuilding.place_of(o.id) == "deck"


## Cells whose middle lies on the footprint of a deck building (a pier, a bridge).
static func deck_cells(d: MapData) -> Dictionary:
	var out := {}
	var cp := float(d.cell_px)
	for o in d.objects:
		if _is_deck(o):
			var r := building_rect(o)
			for y in range(floori(r.position.y / cp), ceili(r.end.y / cp)):
				for x in range(floori(r.position.x / cp), ceili(r.end.x / cp)):
					if r.has_point((Vector2(x, y) + Vector2(0.5, 0.5)) * cp):
						out[Vector2i(x, y)] = true
	return out


func add_cliff(c: Dictionary) -> void:
	data.cliffs.append(c)
	_cliff_nodes.append(_make_cliff(c))
	_after_cliffs()


func remove_cliff(i: int) -> void:
	_cliff_nodes[i].queue_free()
	_cliff_nodes.remove_at(i)
	data.cliffs.remove_at(i)
	_after_cliffs()


## Index of the cliff whose face (or the strip just above it) is under p, or -1.
func cliff_at(p: Vector2) -> int:
	for i in _cliff_nodes.size():
		var cb: CliffBand = _cliff_nodes[i]
		if cb.texture == null:
			continue
		var pts: Array = data.cliffs[i].points
		if p.x < pts[0] or p.x > pts[pts.size() - 2]:
			continue
		if p.y >= cb.top_at(p.x) - 6.0 and p.y <= cb.bottom_at(p.x) + 2.0:
			return i
	return -1


func add_ramp(i: int, x: float, half: int, style: int) -> void:
	var c: Dictionary = data.cliffs[i]
	var ramps: Array = c.get("ramps", [])
	ramps.append_array([x, half, style])
	c.ramps = ramps
	(_cliff_nodes[i] as CliffBand).ramps = _ramps_vec(ramps)
	_after_cliffs()


## Removes the ramp of cliff i nearest x (within its width); returns true if one was removed.
func remove_ramp(i: int, x: float) -> bool:
	var c: Dictionary = data.cliffs[i]
	var ramps: Array = c.get("ramps", [])
	for k in range(0, ramps.size(), 3):
		if absf(ramps[k] - x) <= ramps[k + 1] + 4:
			for _j in 3:
				ramps.remove_at(k)
			c.ramps = ramps
			(_cliff_nodes[i] as CliffBand).ramps = _ramps_vec(ramps)
			_after_cliffs()
			return true
	return false


## Call when a brush stroke ends: syncs the ground/water textures the terrain rebuilds from, the
## blockers, and the grass around changed objects.
func end_stroke(changed_area := Rect2()) -> void:
	_ground_tex.update(_ground_image())
	_water_tex.update(_water_image())
	_rebuild_blockers()
	bridges.refresh()
	if changed_area.size != Vector2.ZERO:
		grass.rebuild.call_deferred(changed_area.grow(24.0))


func cliff_nodes() -> Array:
	return _cliff_nodes


# ------------------------------------------------------------------ building

func _ground_image() -> Image:
	var img := Image.create(data.size.x, data.size.y, false, Image.FORMAT_RGBA8)
	var cols := [Color(0, 0, 0, 1), Color(1, 0, 0, 1), Color(1, 0, 1, 1), Color(1, 1, 0, 1), Color(1, 1, 1, 1), Color(0, 0, 0, 0),
		Color(1, 0, 0, 0), Color(0, 1, 0, 0), Color(1, 1, 0, 0)]
	for y in data.size.y:
		for x in data.size.x:
			img.set_pixel(x, y, cols[data.ground[y * data.size.x + x]])
	return img


func _water_image() -> Image:
	var img := Image.create(data.size.x, data.size.y, false, Image.FORMAT_L8)
	for y in data.size.y:
		for x in data.size.x:
			if data.water[y * data.size.x + x] != 0:
				img.set_pixel(x, y, Color.WHITE)
	return img


func _make_object(o: Dictionary) -> Node2D:
	var n: Node2D
	match o.kind:
		"tree":
			var t := WorldTree.new()
			t.species = o.id
			n = t
		"bush":
			var b := WorldProp.new()
			b.library_item = "bush:" + str(o.id)
			b.sway = 0.4
			n = b
		"rock":
			var r := WorldProp.new()
			r.library_item = "rock"
			r.skirt = 0.7
			n = r
		"building":
			var h := WorldBuilding.new()
			h.building = o.id
			if o.has("to"):
				h.interior = o.to
				var at := Vector2(o.at[0], o.at[1]) if o.has("at") else Vector2(-1, -1)
				h.door_entered.connect(func(b: Node2D) -> void:
					if b is CharacterBody2D:
						door_used.emit(o.to, at))
			n = h
		_:
			var f := WorldProp.new()
			f.texture = load(o.id)
			f.skirt = 0.0
			f.shadow = false
			f.solid = false
			f.sway = 0.5
			n = f
	n.position = Vector2(o.x, o.y)
	props.add_child(n)
	return n


func _make_cliff(c: Dictionary) -> CliffBand:
	var cb := CliffBand.new()
	var pts := PackedVector2Array()
	var raw: Array = c.points
	for k in range(0, raw.size(), 2):
		pts.append(Vector2(raw[k], raw[k + 1]))
	cb.points = pts
	cb.face = int(c.get("face", 36))
	cb.seed = int(c.get("seed", 1))
	cb.ramps = _ramps_vec(c.get("ramps", []))
	cliffs_root.add_child(cb)
	return cb


func _ramps_vec(ramps: Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	for k in range(0, ramps.size() - 2, 3):
		out.append(Vector3(ramps[k], ramps[k + 1], ramps[k + 2]))
	return out


func _after_cliffs() -> void:
	terrain.rebuild.call_deferred()  # ramp mouths paint dirt; cliff feet change the grass
	grass.rebuild.call_deferred()


## Water and blocked cells become collision, merged into horizontal runs. Water keeps a shallow,
## walkable rim where it meets land; OPEN cells are never blocked.
func _rebuild_blockers() -> void:
	for c in blockers.get_children():
		c.free()
	var cp := float(data.cell_px)
	_decks = deck_cells(data)
	# the map's edges: nobody walks off it (along the top, not onto the lip of a vista's meadow)
	var full := data.size_px()
	for r in [Rect2(-32, -32, full.x + 64, 38), Rect2(-32, full.y, full.x + 64, 32),
			Rect2(-32, -32, 32, full.y + 64), Rect2(full.x, -32, 32, full.y + 64)]:
		var edge := CollisionShape2D.new()
		var er := RectangleShape2D.new()
		er.size = r.size
		edge.shape = er
		edge.position = r.get_center()
		blockers.add_child(edge)
	for y in data.size.y:
		var x := 0
		while x < data.size.x:
			var kind := _block_kind(Vector2i(x, y))
			if kind == 0:
				x += 1
				continue
			var x0 := x
			var top := _rim(Vector2i(x, y - 1), kind)
			var bot := _rim(Vector2i(x, y + 1), kind)
			while x < data.size.x and _block_kind(Vector2i(x, y)) == kind and _rim(Vector2i(x, y - 1), kind) == top and _rim(Vector2i(x, y + 1), kind) == bot:
				x += 1
			var left := _rim(Vector2i(x0 - 1, y), kind)
			var right := _rim(Vector2i(x, y), kind)
			var r := Rect2(x0 * cp + left, y * cp + top, (x - x0) * cp - left - right, cp - top - bot)
			if r.size.x > 0.5 and r.size.y > 0.5:
				var shape := CollisionShape2D.new()
				var rect := RectangleShape2D.new()
				rect.size = r.size
				shape.shape = rect
				shape.position = r.get_center()
				blockers.add_child(shape)


## 0 = walkable, 1 = water, 2 = blocked by hand or outside the rooms (VOID ground).
func _block_kind(c: Vector2i) -> int:
	var p := data.passage_at(c)
	if p == MapData.Passage.BLOCKED or (p == MapData.Passage.AUTO and data.ground_at(c) == MapData.Ground.VOID):
		return 2
	if p == MapData.Passage.OPEN or _decks.has(c):
		return 0
	return 1 if data.water_at(c) else 0


## How far a run's edge is pulled in where its neighbour is not the same kind of blocker.
func _rim(neighbour: Vector2i, kind: int) -> float:
	if kind != 1 or not data.has_cell(neighbour):
		return 0.0
	return 0.0 if _block_kind(neighbour) == 1 else SHORE_INSET

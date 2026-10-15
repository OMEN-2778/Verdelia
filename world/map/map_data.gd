class_name MapData
extends RefCounted
## Everything a map is made of, independent of how it is drawn: a grid of ground cells, a grid of
## water cells, a grid of walking overrides, placed objects (trees, bushes, rocks, flowers, buildings...),
## cliffs (with their ramps) and the spawn point. The map editor writes it, MapWorld builds a
## playable world from it, and it is saved as a small JSON file (grids as base64).

const VERSION := 1

enum Ground { GRASS, DIRT, SAND, TILLED, WATERED, PAVED, WOOD_FLOOR, STONE_FLOOR, VOID }  ## VOID: outside a house's rooms
## Flowers in older maps pointed at a third-party pack that is no longer in the project; they
## load as the project's own wild flowers instead.
const OLD_FLOWERS := "res://art/third_party/"
const OLD_FLOWER_IDS := {"Flower1": "daisy", "Flower2": "buttercup", "Flower3": "clover", "Flower5": "bluebell",
	"Flower6": "poppy", "Flower9": "forgetmenot"}

enum Passage { AUTO, BLOCKED, OPEN }  ## OPEN lets you walk on water (bridges, stepping stones)

var name := "未命名地图"
var size := Vector2i(120, 68)  ## in cells
var cell_px := 8
var ground := PackedByteArray()
var water := PackedByteArray()
var passage := PackedByteArray()
## {kind: "tree" | "bush" | "rock" | "flower" | "building" | "npc", id: String, x: float, y: float}
## (a building's x, y is the middle of its front wall's base, where the doorstep is; an npc's id is
## a character in art/characters/, with "act" and "face" for what it is doing and which way)
var objects: Array = []
## {points: [x, y, x, y, ...] (top edge, left to right), face: int, seed: int,
##  ramps: [x, half width, style, ...]} (style 0 earthen slope, 1 stone stairs, 2 grass slope)
var cliffs: Array = []
var spawn := Vector2(-1, -1)
## The far view painted beyond the north edge (Vista.KINDS): "" none, "mountains"...
var vista := ""
## Indoors (a house, a shop): no fireflies or other outdoor night life.
var indoor := false
## The rooms of a house, for lights that come on where you are at night (RoomLights):
## {name: String, area: [[x, y, w, h], ...] (the floor you stand on in it),
##  light: [[x, y, w, h], ...] (what it lights on screen: its floor and walls)}, in map px.
var rooms: Array = []


static func create(cells: Vector2i) -> MapData:
	var m := MapData.new()
	m.size = cells
	m.ground.resize(cells.x * cells.y)
	m.water.resize(cells.x * cells.y)
	m.passage.resize(cells.x * cells.y)
	m.spawn = Vector2(cells) * m.cell_px * 0.5
	return m


## A copy of this map at a new size (in cells), with everything moved by `offset` cells: the
## old map's top-left lands on cell `offset` of the new one. Ground, water and walking cells
## outside the old map start as grass; objects and cliffs that end up outside are dropped.
func resized(cells: Vector2i, offset: Vector2i) -> MapData:
	var m := MapData.create(cells)
	m.name = name
	m.cell_px = cell_px
	m.vista = vista
	m.indoor = indoor
	for y in size.y:
		for x in size.x:
			var c := Vector2i(x, y) + offset
			if m.has_cell(c):
				var i := idx(Vector2i(x, y))
				var j := m.idx(c)
				m.ground[j] = ground[i]
				m.water[j] = water[i]
				m.passage[j] = passage[i]
	var shift := Vector2(offset * cell_px)
	var bound := Rect2(Vector2.ZERO, m.size_px())
	for o in objects:
		var p := Vector2(o.x, o.y) + shift
		if bound.has_point(p):
			var o2: Dictionary = o.duplicate(true)
			o2.x = p.x
			o2.y = p.y
			m.objects.append(o2)
	for cl in cliffs:
		var c2: Dictionary = cl.duplicate(true)
		var pts: Array = c2.points
		for k in range(0, pts.size(), 2):
			pts[k] += shift.x
			pts[k + 1] += shift.y
		var ramps: Array = c2.get("ramps", [])
		for k in range(0, ramps.size(), 3):
			ramps[k] += shift.x
		var inside := false
		for k in range(0, pts.size(), 2):
			inside = inside or bound.has_point(Vector2(pts[k], pts[k + 1]))
		if inside:
			m.cliffs.append(c2)
	for r in rooms:
		var r2: Dictionary = r.duplicate(true)
		for key in ["area", "light"]:
			for q: Array in r2.get(key, []):
				q[0] += shift.x
				q[1] += shift.y
		m.rooms.append(r2)
	m.spawn = (spawn + shift).clamp(Vector2.ZERO, m.size_px() - Vector2.ONE)
	return m


func size_px() -> Vector2:
	return Vector2(size * cell_px)


func has_cell(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < size.x and c.y < size.y


func idx(c: Vector2i) -> int:
	return c.y * size.x + c.x


func ground_at(c: Vector2i) -> int:
	return ground[idx(c)] if has_cell(c) else Ground.GRASS


func water_at(c: Vector2i) -> bool:
	return has_cell(c) and water[idx(c)] != 0


func passage_at(c: Vector2i) -> int:
	return passage[idx(c)] if has_cell(c) else Passage.AUTO


func copy() -> MapData:
	return MapData.from_dict(to_dict())


func to_dict() -> Dictionary:
	return {
		"version": VERSION,
		"name": name,
		"size": [size.x, size.y],
		"cell_px": cell_px,
		"ground": Marshalls.raw_to_base64(ground),
		"water": Marshalls.raw_to_base64(water),
		"passage": Marshalls.raw_to_base64(passage),
		"objects": objects.duplicate(true),
		"cliffs": cliffs.duplicate(true),
		"spawn": [spawn.x, spawn.y],
		"vista": vista,
		"indoor": indoor,
		"rooms": rooms.duplicate(true),
	}


static func from_dict(d: Dictionary) -> MapData:
	var m := MapData.create(Vector2i(int(d.size[0]), int(d.size[1])))
	m.name = d.get("name", m.name)
	m.cell_px = int(d.get("cell_px", 8))
	m.vista = str(d.get("vista", ""))
	m.indoor = bool(d.get("indoor", false))
	var n := m.size.x * m.size.y
	for key in ["ground", "water", "passage"]:
		var raw := Marshalls.base64_to_raw(d.get(key, ""))
		if raw.size() == n:
			m.set(key, raw)
	m.objects = (d.get("objects", []) as Array).duplicate(true)
	for o in m.objects:  # maps from before the wild flowers were redrawn
		if o.get("kind") == "flower" and str(o.id).begins_with(OLD_FLOWERS):
			o.id = "res://art/library/flowers/%s.png" % OLD_FLOWER_IDS.get(str(o.id).get_file().get_basename(), "daisy")
	m.cliffs = (d.get("cliffs", []) as Array).duplicate(true)
	m.rooms = (d.get("rooms", []) as Array).duplicate(true)
	var sp: Array = d.get("spawn", [])
	if sp.size() == 2:
		m.spawn = Vector2(sp[0], sp[1])
	return m


func save(path: String) -> Error:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(to_dict(), "\t"))
	return OK


static func load_file(path: String) -> MapData:
	if not FileAccess.file_exists(path):
		return null
	var d = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(d) != TYPE_DICTIONARY:
		return null
	return MapData.from_dict(d)

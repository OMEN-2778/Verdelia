class_name MapData
extends RefCounted
## Everything a map is made of, independent of how it is drawn: a grid of ground cells, a grid of
## water cells, a grid of walking overrides, placed objects (trees, bushes, rocks, flowers, buildings...),
## cliffs (with their ramps) and the spawn point. The map editor writes it, MapWorld builds a
## playable world from it, and it is saved as a small JSON file (grids as base64).

const VERSION := 1

enum Ground { GRASS, DIRT, SAND, TILLED, WATERED, PAVED }
enum Passage { AUTO, BLOCKED, OPEN }  ## OPEN lets you walk on water (bridges, stepping stones)

var name := "未命名地图"
var size := Vector2i(120, 68)  ## in cells
var cell_px := 8
var ground := PackedByteArray()
var water := PackedByteArray()
var passage := PackedByteArray()
## {kind: "tree" | "bush" | "rock" | "flower" | "building", id: String, x: float, y: float}
## (a building's x, y is the middle of its front wall's base, where the doorstep is)
var objects: Array = []
## {points: [x, y, x, y, ...] (top edge, left to right), face: int, seed: int,
##  ramps: [x, half width, style, ...]} (style 0 earthen slope, 1 stone stairs, 2 grass slope)
var cliffs: Array = []
var spawn := Vector2(-1, -1)


static func create(cells: Vector2i) -> MapData:
	var m := MapData.new()
	m.size = cells
	m.ground.resize(cells.x * cells.y)
	m.water.resize(cells.x * cells.y)
	m.passage.resize(cells.x * cells.y)
	m.spawn = Vector2(cells) * m.cell_px * 0.5
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
	}


static func from_dict(d: Dictionary) -> MapData:
	var m := MapData.create(Vector2i(int(d.size[0]), int(d.size[1])))
	m.name = d.get("name", m.name)
	m.cell_px = int(d.get("cell_px", 8))
	var n := m.size.x * m.size.y
	for key in ["ground", "water", "passage"]:
		var raw := Marshalls.base64_to_raw(d.get(key, ""))
		if raw.size() == n:
			m.set(key, raw)
	m.objects = (d.get("objects", []) as Array).duplicate(true)
	m.cliffs = (d.get("cliffs", []) as Array).duplicate(true)
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

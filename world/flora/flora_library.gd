class_name FloraLibrary
## Read-only access to the baked flora library (art/library/manifest.json, see
## tools/art/vale/library.py). Variants are picked deterministically from a seed.

const ROOT := "res://art/library/"

static var _manifest := {}


static func manifest() -> Dictionary:
	if _manifest.is_empty():
		_manifest = JSON.parse_string(FileAccess.get_file_as_string(ROOT + "manifest.json"))
	return _manifest


static func tree(species: String, pick: int) -> Dictionary:
	var list: Array = manifest().trees.get(species, [])
	return {} if list.is_empty() else list[posmod(pick, list.size())]


static func bush(kind: String, pick: int) -> Dictionary:
	var list: Array = manifest().bushes.get(kind, [])
	return {} if list.is_empty() else list[posmod(pick, list.size())]


static func rock(pick: int) -> Dictionary:
	var list: Array = manifest().rocks
	return list[posmod(pick, list.size())]


static func building(id: String) -> Dictionary:
	for e: Dictionary in manifest().get("buildings", []):
		if e.id == id:
			return e
	return {}


static func texture(rel: String) -> Texture2D:
	return load(ROOT + rel)


## Stable pick for something placed at `pos` (so moving it in the editor changes the variant).
static func pick_at(pos: Vector2, salt := 0) -> int:
	return absi(hash(Vector3i(roundi(pos.x), roundi(pos.y), salt)))

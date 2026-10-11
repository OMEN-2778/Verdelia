class_name TuftBatch
## Shared builder for grass tuft MultiMeshes (one atlas, one mesh, one material for the whole
## game), used by GrassField for the meadow and by props for the grass in front of their base.

const MANIFEST := "res://art/library/manifest.json"
const ATLAS := preload("res://art/library/tufts.png")
const SHADER := preload("res://world/grass/grass.gdshader")

static var groups := {}
static var material: ShaderMaterial
static var _mesh: ArrayMesh


static func ensure_loaded() -> void:
	if _mesh:
		return
	var m: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	var t: Dictionary = m.tufts
	groups = t.groups
	var cell := Vector2(t.cell[0], t.cell[1])
	material = ShaderMaterial.new()
	material.shader = SHADER
	material.set_shader_parameter("cell", cell)
	material.set_shader_parameter("columns", float(t.columns))
	material.set_shader_parameter("atlas_px", Vector2(ATLAS.get_size()))
	# quad anchored at the tuft base: the atlas base pixel (column cell.x/2, bottom row) lands on (0, 0)
	var bx := floorf(cell.x / 2.0)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector2Array([Vector2(-bx, 1 - cell.y), Vector2(cell.x - bx, 1 - cell.y),
		Vector2(cell.x - bx, 1), Vector2(-bx, 1)])
	arrays[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	_mesh = ArrayMesh.new()
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)


static func pick(rng: RandomNumberGenerator, group: String) -> int:
	ensure_loaded()
	var g: Array = groups.get(group, [])
	return -1 if g.is_empty() else int(g[rng.randi() % g.size()])


## items: [[local y, local x, atlas index], ...]; world_origin: global position of the parent,
## so the wind field and the player push line up across all batches.
static func build(items: Array, rng: RandomNumberGenerator, world_origin := Vector2.ZERO) -> MultiMeshInstance2D:
	ensure_loaded()
	items.sort_custom(func(a, b): return a[0] < b[0])
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_2D
	mm.use_custom_data = true
	mm.mesh = _mesh
	mm.instance_count = items.size()
	for i in items.size():
		var it: Array = items[i]
		var pos := Vector2(roundf(it[1]), roundf(it[0]))
		var w := world_origin + pos
		mm.set_instance_transform_2d(i, Transform2D(0.0, pos))
		mm.set_instance_custom_data(i, Color(float(it[2]), rng.randf() * 6.28, w.x, w.y))
	var inst := MultiMeshInstance2D.new()
	inst.multimesh = mm
	inst.texture = ATLAS
	inst.material = material
	return inst


## Tall grass in front of a prop's base, as a child drawn over the prop's sprite.
static func skirt(points: PackedVector2Array, owner_global: Vector2, seed: int, group := "tall") -> MultiMeshInstance2D:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var items := []
	for p in points:
		items.append([p.y, p.x, pick(rng, group) if rng.randf() > 0.08 else pick(rng, "flower")])
	return build(items, rng, owner_global) if not items.is_empty() else null

@tool
class_name GrassField
extends Node2D
## Living grass for a whole map, drawn as chunked MultiMeshes (TuftBatch) so any map size stays cheap.
##
## Tufts grow on grass cells of `terrain`, thin out to short tufts along path edges, and become
## seedlings on tilled soil (if `crops_on_tilled`). Nodes in the "grass_exclude" group can veto a
## spot via grass_excludes(world_pos) -> bool; nodes in "grass_skirt" return extra positions for
## tall tufts via grass_skirt_points() -> PackedVector2Array (cliff feet, the back of rocks and
## ruins; the grass in front of a prop is drawn by the prop itself so it overlaps the prop's base).


@export var terrain: Terrain:
	set(v):
		if terrain and terrain.changed.is_connected(_on_terrain_changed):
			terrain.changed.disconnect(_on_terrain_changed)
		terrain = v
		if terrain and not terrain.changed.is_connected(_on_terrain_changed):
			terrain.changed.connect(_on_terrain_changed)
		_queue_rebuild()
@export var player: Node2D
@export_range(0.0, 3.0) var density := 1.0:
	set(v):
		density = v
		_queue_rebuild()
@export_range(0.0, 1.0) var flower_rate := 0.12
@export var crops_on_tilled := true
@export var seed := 1
@export var chunk_px := 128
@export var rebuild_now := false:
	set(_v):
		_queue_rebuild()

var _chunks := {}
var _pending := false


func _ready() -> void:
	z_index = -5
	TuftBatch.ensure_loaded()
	_queue_rebuild()


func _process(_delta: float) -> void:
	if player and TuftBatch.material:
		TuftBatch.material.set_shader_parameter("player_pos", player.global_position)


func rebuild(area: Rect2 = Rect2()) -> void:
	_pending = false
	if not terrain:
		return
	var map := Rect2(terrain.position, Vector2(terrain.map_size_px))
	if area.size == Vector2.ZERO:
		area = map
		for c in _chunks.values():
			c.queue_free()
		_chunks.clear()
	var skirts := _collect_skirts()  # [point, group]
	var excluders := get_tree().get_nodes_in_group("grass_exclude") if is_inside_tree() else []
	var c0 := Vector2i((area.position / chunk_px).floor())
	var c1 := Vector2i((area.end / chunk_px).ceil())
	for cy in range(c0.y, c1.y):
		for cx in range(c0.x, c1.x):
			var key := Vector2i(cx, cy)
			if _chunks.has(key):
				_chunks[key].queue_free()
				_chunks.erase(key)
			var rect := Rect2(Vector2(key) * chunk_px, Vector2(chunk_px, chunk_px)).intersection(map)
			if rect.size.x <= 0 or rect.size.y <= 0:
				continue
			var inst := _build_chunk(key, rect, skirts, excluders)
			if inst:
				_chunks[key] = inst
				add_child(inst)


func _build_chunk(key: Vector2i, rect: Rect2, skirts: Array, excluders: Array) -> MultiMeshInstance2D:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(key.x, key.y, seed))
	var items: Array = []  # [y, x, atlas index]
	var step := 4
	var y := int(rect.position.y)
	while y < rect.end.y:
		var x := int(rect.position.x)
		while x < rect.end.x:
			if rng.randf() < 0.11 * density:
				var p := Vector2(x + rng.randi_range(0, step - 1), y + rng.randi_range(0, step - 1))
				var idx := _pick(p, rng, excluders)
				if idx >= 0:
					items.append([p.y, p.x, idx])
			x += step
		y += step
	if crops_on_tilled:
		_add_crops(rect, rng, items)
	for sk in skirts:
		var p: Vector2 = sk[0]
		if rect.has_point(p) and not _excluded(p, excluders):
			items.append([p.y, p.x, _rand(rng, sk[1]) if rng.randf() > 0.06 else _rand(rng, "flower")])
	if items.is_empty():
		return null
	return TuftBatch.build(items, rng, global_position)


func _pick(p: Vector2, rng: RandomNumberGenerator, excluders: Array) -> int:
	if _excluded(p, excluders):
		return -1
	var wet := terrain.water_at(to_global(p))
	if wet > 0.3:
		return -1  # no grass in the water (shore grass comes from the bank edge below)
	var s := terrain.sample(p)
	if wet > 0.12:
		return _rand(rng, "meadow") if rng.randf() < 0.7 else -1  # a fringe of grass on the bank
	if s.a < 0.8 and s.r + s.g > 0.3:
		return -1  # indoor floors (floorboards, stone flags) and their edges
	if s.g > 0.4:
		return -1  # tilled soil: crops are placed on the ridges separately
	if s.a < 0.35:
		return -1  # brick paving
	if s.a < 0.8:
		return _rand(rng, "short") if rng.randf() < 0.3 else -1  # tufts along the edge of the paving
	if s.r > 0.62:
		return _rand(rng, "short") if rng.randf() < 0.04 else -1  # a rare tuft in the middle of a path
	if s.r > 0.3:
		return _rand(rng, "short") if rng.randf() < 0.45 else -1  # grass creeping onto path edges
	return _rand(rng, "flower") if rng.randf() < flower_rate else _rand(rng, "meadow")


func _add_crops(rect: Rect2, rng: RandomNumberGenerator, items: Array) -> void:
	var y := int(ceilf(rect.position.y / 8.0)) * 8 + 3
	while y < rect.end.y:
		var x := int(ceilf(rect.position.x / 8.0)) * 8
		while x < rect.end.x:
			var p := Vector2(x + rng.randi_range(-1, 1), y)
			var t := terrain.sample(p)
			if t.g > 0.62 and t.a > 0.6 and rng.randf() < 0.85:
				items.append([p.y, p.x, _rand(rng, "crop")])
			x += 8
		y += 8


func _excluded(p: Vector2, excluders: Array) -> bool:
	var world := to_global(p)
	for e in excluders:
		if e.grass_excludes(world):
			return true
	return false


func _collect_skirts() -> Array:
	var out := []
	if not is_inside_tree():
		return out
	for n in get_tree().get_nodes_in_group("grass_skirt"):
		var group: String = n.grass_skirt_group() if n.has_method("grass_skirt_group") else "tall"
		for p in n.grass_skirt_points():
			out.append([to_local(p), group])
	return out


func _rand(rng: RandomNumberGenerator, group: String) -> int:
	return TuftBatch.pick(rng, group)


func _on_terrain_changed(cells: Rect2i) -> void:
	if not terrain:
		return
	if cells.size == terrain.cells():
		_queue_rebuild()
	else:
		var r := Rect2(Vector2(cells.position * terrain.cell_px), Vector2(cells.size * terrain.cell_px))
		rebuild(r.grow(4.0))


func _queue_rebuild() -> void:
	if not is_inside_tree() or _pending:
		return
	_pending = true
	rebuild.call_deferred()

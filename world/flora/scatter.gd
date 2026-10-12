@tool
class_name Scatter
extends Node2D
## Scatters trees and props over an area. Items are strings:
##   "tree:<species>"           WorldTree from the library (oak, birch, pine, blossom, sapling, *_far)
##   "bush:<kind>" / "rock"     WorldProp from the library
##   "prop:res://path.png"      WorldProp with that texture (e.g. third-party ruins and stumps)
## Optional "@sway=0.6" / "@skirt=0" / "@shadow=0" suffixes tweak props. The area is `area` (local rect) or a
## child Polygon2D named "Area". Press `generate` in the inspector to (re)place children; at
## runtime an empty Scatter generates itself, so levels can be authored either way.

@export var area := Rect2(0, 0, 200, 120)
@export var items: PackedStringArray = PackedStringArray(["tree:oak"])
@export var weights: PackedFloat32Array = PackedFloat32Array()
@export var count := 10
@export var min_distance := 20.0
@export var seed := 1
@export var terrain: Terrain  ## optional: keep placements off paths and tilled soil
@export var clearance := 10.0  ## with `terrain`: also keep this far from paths and fields
@export var generate := false:
	set(_v):
		if Engine.is_editor_hint() and is_inside_tree():
			_generate(true)


func _ready() -> void:
	y_sort_enabled = true
	if Engine.is_editor_hint():
		return
	if not get_children().any(func(c: Node) -> bool: return c.name != "Area"):
		# deferred: the Terrain (and its lakes and rivers) builds on a deferred call too, and
		# placements must see the finished map
		_generate.call_deferred(false)


func _generate(persist: bool) -> void:
	for c in get_children():
		if c.name != "Area":
			c.free()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var poly: Polygon2D = get_node_or_null("Area")
	var bounds := area
	if poly:
		bounds = Rect2(poly.polygon[0], Vector2.ZERO)
		for p in poly.polygon:
			bounds = bounds.expand(p)
	var placed: Array[Vector2] = []
	var tries := 0
	while placed.size() < count and tries < count * 40:
		tries += 1
		var p := Vector2(rng.randf_range(bounds.position.x, bounds.end.x), rng.randf_range(bounds.position.y, bounds.end.y)).round()
		if poly and not Geometry2D.is_point_in_polygon(p, poly.polygon):
			continue
		if placed.any(func(q: Vector2) -> bool: return q.distance_to(p) < min_distance):
			continue
		if terrain and not _clear(to_global(p)):
			continue
		placed.append(p)
		var node := _make(_choose(rng))
		if node == null:
			continue
		node.position = p
		add_child(node)
		if persist:
			node.owner = get_tree().edited_scene_root


func _clear(world: Vector2) -> bool:
	if terrain.kind_at(world) != Terrain.Kind.GRASS:
		return false
	for k in 8:
		var off := Vector2.from_angle(k * TAU / 8.0) * clearance
		if terrain.kind_at(world + Vector2(off.x, off.y * 0.6)) != Terrain.Kind.GRASS:
			return false
	return true


func _choose(rng: RandomNumberGenerator) -> String:
	if weights.size() != items.size():
		return items[rng.randi() % items.size()]
	var total := 0.0
	for w in weights:
		total += w
	var r := rng.randf() * total
	for i in items.size():
		r -= weights[i]
		if r <= 0.0:
			return items[i]
	return items[-1]


func _make(item: String) -> Node2D:
	var opts := item.split("@")
	var head := opts[0]
	var node: Node2D
	if head.begins_with("tree:"):
		var t := WorldTree.new()
		t.species = head.substr(5)
		node = t
	else:
		var p := WorldProp.new()
		if head.begins_with("prop:"):
			p.texture = load(head.substr(5))
		else:
			p.library_item = head
		if head.begins_with("bush"):
			p.sway = 0.5
		for o in opts.slice(1):
			var kv := o.split("=")
			if kv.size() == 2:
				p.set(kv[0], kv[1] != "0" if typeof(p.get(kv[0])) == TYPE_BOOL else float(kv[1]))
		node = p
	node.name = head.get_file().get_basename().replace(":", "_").validate_node_name()
	return node

@tool
class_name WorldTree
extends Node2D
## A tree from the flora library. Place it at the trunk base. Crown layers sway independently,
## leaves (or petals) drift down, it casts a soft shadow, keeps grass off its roots and grows a
## little tall grass around them.

const LEAF := preload("res://art/library/fx/leaf.png")

@export_enum("oak", "birch", "pine", "blossom", "sapling", "oak_far", "pine_far") var species := "oak":
	set(v):
		species = v
		_rebuild()
@export var variant := -1:  ## -1: chosen from the position
	set(v):
		variant = v
		_rebuild()
@export var falling_leaves := true

var _entry := {}


func _ready() -> void:
	add_to_group("grass_exclude")
	add_to_group("grass_skirt")
	_rebuild()


func _notification(what: int) -> void:
	if what == NOTIFICATION_TRANSFORM_CHANGED and variant < 0 and Engine.is_editor_hint():
		_rebuild()


func _rebuild() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		if c.owner == null:
			c.queue_free()
	_entry = FloraLibrary.tree(species, variant if variant >= 0 else FloraLibrary.pick_at(global_position, 7))
	if _entry.is_empty():
		return
	set_notify_transform(true)
	var anchor := -Vector2(_entry.anchor[0], _entry.anchor[1])
	var r: Array = _entry.crown_rect
	var crown_w: float = r[2] - r[0]
	add_child(SoftShadow.sprite(int(crown_w * 0.72), int(maxf(5.0, crown_w * 0.16)), crown_w * 0.12))
	var trunk := _sprite(_entry.trunk, anchor)
	add_child(trunk)
	var mirrored: Array[Sprite2D] = [trunk]
	var k := 0
	var ph := float(FloraLibrary.pick_at(global_position, 3) % 628) / 100.0
	for layer: Dictionary in _entry.crowns:
		var s := _sprite(layer.file, anchor)
		s.set_script(preload("res://world/flora/crown_sway.gd"))
		s.phase = ph + k * 0.9
		s.amount = float(layer.sway) * (0.5 if species.ends_with("_far") else 1.0)
		add_child(s)
		mirrored.append(s)
		k += 1
	WaterReflection.attach(self, mirrored)
	var front := PackedVector2Array()
	for p in _root_grass():
		front.append(p - global_position)
	var skirt := TuftBatch.skirt(front, global_position, FloraLibrary.pick_at(global_position, 19))
	if skirt:
		add_child(skirt)
	if falling_leaves and not Engine.is_editor_hint():
		add_child(_leaves(r))


func grass_excludes(world: Vector2) -> bool:
	if _entry.is_empty():
		return false
	var d := world - global_position
	var half := 4.0 + float(_entry.crown_rect[2] - _entry.crown_rect[0]) * 0.06
	return absf(d.x) < half and d.y > -6.0 and d.y < 2.0


func grass_skirt_points() -> PackedVector2Array:
	return PackedVector2Array()  # all of a tree's root grass is in front of the trunk (see _rebuild)


func _root_grass() -> PackedVector2Array:
	var out := PackedVector2Array()
	if _entry.is_empty() or species.ends_with("_far"):
		return out
	var half := 6.0 + float(_entry.crown_rect[2] - _entry.crown_rect[0]) * 0.08
	var rng := RandomNumberGenerator.new()
	rng.seed = FloraLibrary.pick_at(global_position, 11)
	var x := -half
	while x <= half:
		if rng.randf() < 0.7:
			out.append(global_position + Vector2(x, rng.randi_range(1, 3)))
		x += 2.0
	return out


func _sprite(rel: String, offset: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = FloraLibrary.texture(rel)
	s.centered = false
	s.position = offset
	return s


func _leaves(r: Array) -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.position = Vector2((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2((r[2] - r[0]) / 2.6, (r[3] - r[1]) / 3.0)
	p.texture = LEAF
	p.amount = 6 if species == "blossom" else 3
	p.lifetime = 6.0
	p.preprocess = 6.0
	p.randomness = 1.0
	p.direction = Vector2(1, 0.4)
	p.spread = 35.0
	p.gravity = Vector2(5, 9)
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 7.0
	p.angular_velocity_min = -120.0
	p.angular_velocity_max = 120.0
	p.color = Color(_entry.leaf)
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.1, 0.8, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color.WHITE, Color.WHITE, Color(1, 1, 1, 0)])
	p.color_ramp = g
	p.z_index = 5
	return p

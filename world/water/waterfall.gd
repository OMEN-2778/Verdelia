@tool
class_name Waterfall
extends Node2D
## A waterfall dropping `height` px from this node (the top of the fall, centred) into a pool.
## Use it on a CliffBand (height = the face), or short (6-12 px) as a small step where water drops a level.
## Draws above the cliff, kicks up mist, and keeps grass away from the fall and the plume.

@export var width := 26:
	set(v):
		width = maxi(4, v)
		_build()
@export var height := 34:
	set(v):
		height = maxi(2, v)
		_build()
@export_range(0.2, 3.0) var speed := 1.0:
	set(v):
		speed = v
		_build()
@export var cliff: CliffBand:  ## snap the top to this cliff's edge and the height to its face
	set(v):
		cliff = v
		_build()
@export var mist := true:
	set(v):
		mist = v
		_build()

const PAD := 12
const SPLASH := 12

var _sprite: Sprite2D
var _fall_h := 0  # height actually used (snapped to the cliff when `cliff` is set)


func _ready() -> void:
	add_to_group("grass_exclude")
	_build()


func _build() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		if c.owner == null:
			c.queue_free()
	_fall_h = height
	if cliff and cliff.is_inside_tree() and cliff.has_method("top_at"):
		if cliff.texture == null:
			cliff.generate()
		var top := cliff.top_at(global_position.x)
		global_position.y = top - 1.0
		_fall_h = int(cliff.bottom_at(global_position.x) - top) + 2
	var w := width + PAD * 2
	var h := _fall_h + SPLASH
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color.WHITE)
	_sprite = Sprite2D.new()
	_sprite.texture = ImageTexture.create_from_image(img)
	_sprite.centered = false
	_sprite.position = Vector2(-w / 2, 0)
	_sprite.z_as_relative = false
	_sprite.z_index = -7  # over the cliff face, under the props
	var m := ShaderMaterial.new()
	m.shader = preload("res://world/water/waterfall.gdshader")
	m.set_shader_parameter("size", Vector2(w, h))
	m.set_shader_parameter("pad", float(PAD))
	m.set_shader_parameter("fall_h", float(_fall_h))
	m.set_shader_parameter("speed", speed)
	m.set_shader_parameter("seed", float(hash(global_position) % 997))
	_sprite.material = m
	add_child(_sprite)
	if mist and not Engine.is_editor_hint():
		add_child(_mist())


func _mist() -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.position = Vector2(0, _fall_h)
	p.z_as_relative = false
	p.z_index = 4
	p.amount = int(clampf(width * 0.5, 6, 30))
	p.lifetime = 2.6
	p.preprocess = 3.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(width * 0.5, 2)
	p.direction = Vector2(0, -1)
	p.spread = 70.0
	p.gravity = Vector2(3, -4)
	p.initial_velocity_min = 4.0
	p.initial_velocity_max = 10.0
	p.scale_amount_min = 1.0
	p.scale_amount_max = 2.0
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.25, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color(0.95, 0.99, 1.0, 0.45), Color(1, 1, 1, 0)])
	p.color_ramp = g
	return p


func grass_excludes(world: Vector2) -> bool:
	var d := world - global_position
	return absf(d.x) < width * 0.5 + 6 and d.y > -2 and d.y < _fall_h + 9

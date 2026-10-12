@tool
class_name WorldBuilding
extends Node2D
## A building from the library: cabins, a thatched cottage, townhouses, shops, the inn and market
## stalls (tools/art/vale/buildings.py). Place it at the middle of its front wall's base (a
## stall: the front of its counter). The walls block walking; a house or shop has a Door area on
## its doorstep that reports who steps onto it (door_entered), ready for interiors. At night the
## windows and lanterns light up and stay bright through the dark grade (the lamp mark in
## grade.gdshader), smoke rises from the chimneys, and walking behind the building fades it so the
## player stays in sight.

signal door_entered(body: Node2D)

const FADE_ALPHA := 0.45

@export var building := "cabin_red":
	set(v):
		building = v
		_rebuild()
@export var interior := ""  ## map or scene the door leads to (for later)
@export var smoke := true

var _entry := {}
var _sprite: Sprite2D
var _lamps: Sprite2D
var _fade := 1.0


func _ready() -> void:
	add_to_group("grass_exclude")
	_rebuild()


## Ground the building stands on (its walls or counter), relative to its base point.
static func footprint_of(id: String) -> Rect2:
	var e := FloraLibrary.building(id)
	if e.is_empty():
		return Rect2()
	var f: Array = e.footprint
	return Rect2(f[0], f[1], f[2], f[3])


## The whole picture (roof, chimney, doorstep), relative to its base point.
static func sprite_rect_of(id: String) -> Rect2:
	var e := FloraLibrary.building(id)
	if e.is_empty():
		return Rect2()
	return Rect2(-e.anchor[0], -e.anchor[1], e.size[0], e.size[1])


func _rebuild() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		if c.owner == null:
			c.queue_free()
	_entry = FloraLibrary.building(building)
	if _entry.is_empty():
		return
	var anchor := -Vector2(_entry.anchor[0], _entry.anchor[1])
	var fp := footprint_of(building)
	add_child(_shadow(int(fp.size.x) + 14))
	_sprite = Sprite2D.new()
	_sprite.name = "Building"
	_sprite.texture = FloraLibrary.texture(_entry.file)
	_sprite.centered = false
	_sprite.position = anchor
	add_child(_sprite)
	_lamps = Sprite2D.new()
	_lamps.name = "Lamps"
	_lamps.texture = FloraLibrary.texture(_entry.night)
	_lamps.centered = false
	_lamps.position = anchor
	_lamps.visible = false  # DayNight switches them on at dusk (group "night_lamps")
	_lamps.add_to_group("night_lamps")
	add_child(_lamps)
	if smoke:
		for c: Array in _entry.get("chimney", []):
			add_child(_smoke(Vector2(c[0], c[1])))
	WaterReflection.attach(self, [_sprite] as Array[Sprite2D])
	var body := StaticBody2D.new()
	body.name = "Walls"
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = fp.size
	shape.shape = rect
	shape.position = fp.get_center()
	body.add_child(shape)
	add_child(body)
	if _entry.get("door") != null:
		var door := Area2D.new()
		door.name = "Door"
		var ds := CollisionShape2D.new()
		var dr := RectangleShape2D.new()
		dr.size = Vector2(float(_entry.door_size[0]) - 4.0, 6.0)
		ds.shape = dr
		ds.position = Vector2(_entry.door[0], 4.0)
		door.add_child(ds)
		door.body_entered.connect(func(b: Node2D) -> void: door_entered.emit(b))
		add_child(door)


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or _sprite == null:
		return
	# fade while a player is behind the building (above its base line, inside the picture)
	var behind := false
	var r := sprite_rect_of(building)
	for p in get_tree().get_nodes_in_group("player"):
		var d: Vector2 = (p as Node2D).global_position - global_position
		if d.y < -2.0 and d.y > r.position.y + 10.0 and d.x > r.position.x + 4.0 and d.x < r.end.x - 4.0:
			behind = true
	_fade = move_toward(_fade, FADE_ALPHA if behind else 1.0, delta * 3.0)
	_sprite.modulate.a = _fade
	_lamps.modulate.a = 1.0 if _fade >= 1.0 else 0.0  # the lamp mark needs the exact colours


func grass_excludes(world: Vector2) -> bool:
	var e := sprite_rect_of(building)
	var fp := footprint_of(building)
	var d := world - global_position
	return d.x > fp.position.x - 3.0 and d.x < fp.end.x + 3.0 and d.y > e.position.y and d.y < 5.0


## A soft, wide contact shadow along the base, dithered toward its rim like SoftShadow.
static var _shadow_cache := {}


func _shadow(w: int) -> Sprite2D:
	var h := 9
	if not _shadow_cache.has(w):
		var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
		for y in h:
			for x in w:
				var dx := absf(x + 0.5 - w / 2.0) - (w / 2.0 - h / 2.0)
				var dy := y + 0.5 - h / 2.0
				var dd := (maxf(dx, 0.0) ** 2 + dy * dy) / ((h / 2.0) ** 2)
				if dd > 1.0 or (dd > 0.6 and SoftShadow.BAYER[(y & 3) * 4 + (x & 3)] < 8):
					continue
				img.set_pixel(x, y, Color(0.06, 0.18, 0.1, 0.34 if dd < 0.45 else 0.2))
		_shadow_cache[w] = ImageTexture.create_from_image(img)
	var s := Sprite2D.new()
	s.name = "Shadow"
	s.texture = _shadow_cache[w]
	s.position = Vector2(0, -1)
	s.z_as_relative = false
	s.z_index = -6
	return s


func _smoke(at: Vector2) -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.name = "Smoke"
	p.position = at + Vector2(0, -1)
	p.amount = 8
	p.lifetime = 4.0
	p.preprocess = 4.0
	p.local_coords = false
	p.direction = Vector2(0.25, -1)
	p.spread = 12.0
	p.gravity = Vector2(2.5, -1.5)  # a light breeze carries it off to the right
	p.initial_velocity_min = 4.0
	p.initial_velocity_max = 6.0
	var grow := Curve.new()
	grow.add_point(Vector2(0.0, 0.6))
	grow.add_point(Vector2(1.0, 2.2))
	p.scale_amount_curve = grow
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.15, 0.6, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color(1, 1, 1, 0.75), Color(1, 1, 1, 0.4), Color(1, 1, 1, 0)])
	p.color_ramp = g
	p.color = Color(0.92, 0.92, 0.9)
	p.texture = _puff()
	return p


static var _puff_tex: ImageTexture


static func _puff() -> ImageTexture:
	if _puff_tex == null:
		var img := Image.create(5, 5, false, Image.FORMAT_RGBA8)
		for y in 5:
			for x in 5:
				var d := Vector2(x - 2.0, y - 2.0).length()
				if d <= 2.3:
					img.set_pixel(x, y, Color(1, 1, 1, 1.0 if d < 1.5 else 0.5))
		_puff_tex = ImageTexture.create_from_image(img)
	return _puff_tex

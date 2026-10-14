@tool
class_name WorldBuilding
extends Node2D
## A building, stall or street prop from the library (tools/art/vale/buildings.py, landmarks.py,
## market.py): houses, a manor, a tower, a barn and a windmill, shops, a smithy and the inn,
## market stalls, tents and a wagon, racks, banners, tables, a well... Place it at the middle of
## its front wall's base (a stall: the front of its counter). The walls block walking (a rug lies
## flat and does not); a house or shop has a Door area on its doorstep that reports who steps onto
## it (door_entered), ready for interiors. At night windows, lanterns and the forge light up and
## stay bright through the dark grade (the lamp mark in grade.gdshader), smoke rises from the
## chimneys, animated parts move (a windmill's sails, a water wheel, a camp fire's flames), and
## walking behind the building fades it so the player stays in sight. Some things are walked on
## (rugs, a pier, a bridge's deck: not solid, drawn under everyone); `place` says where a thing
## may stand ("water": a boat, "deck": over water or land).

signal door_entered(body: Node2D)

const FADE_ALPHA := 0.45
const ANIM_FPS := 5.0  ## frames per second of an animated part that names no rate of its own

@export var building := "cabin_red":
	set(v):
		building = v
		_rebuild()
@export var interior := ""  ## map the door leads to (set from the map object's "to")
@export var smoke := true
## Its lamps light at night only while this is on: indoors, RoomLights turns off the lamps of the
## rooms you are not in.
var lamps_on := true

var _entry := {}
var _sprite: Sprite2D
var _lamps: Sprite2D
var _anims: Array = []  # [Sprite2D, fps]
var _fade := 1.0
var _solid := true
var _rect := Rect2()  # the picture, relative to the base point
var _t := 0.0


func _ready() -> void:
	add_to_group("grass_exclude")
	_rebuild()


## Whether it blocks walking (everything but rugs, decks and the like).
static func is_solid(id: String) -> bool:
	return FloraLibrary.building(id).get("solid", true)


## Where it may stand: "" on land, "water" on water (a boat), "deck" over water or land.
static func place_of(id: String) -> String:
	return FloraLibrary.building(id).get("place", "")


## Ground the building stands on (its walls or counter), relative to its base point.
static func footprint_of(id: String) -> Rect2:
	var e := FloraLibrary.building(id)
	if e.is_empty():
		return Rect2()
	var f: Array = e.footprint
	return Rect2(f[0], f[1], f[2], f[3])


## The parts of the footprint that block walking: all of it, or for an archway (an entry with a
## "passage" [x0, x1]) the piers either side of the opening.
static func solid_rects_of(id: String) -> Array[Rect2]:
	var fp := footprint_of(id)
	var gap: Array = FloraLibrary.building(id).get("passage", [])
	if gap.size() != 2:
		return [fp]
	var out: Array[Rect2] = []
	if gap[0] > fp.position.x:
		out.append(Rect2(fp.position.x, fp.position.y, gap[0] - fp.position.x, fp.size.y))
	if gap[1] < fp.end.x:
		out.append(Rect2(gap[1], fp.position.y, fp.end.x - gap[1], fp.size.y))
	return out


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
	var solid := is_solid(building)
	_solid = solid
	_rect = sprite_rect_of(building)
	_sprite = Sprite2D.new()
	_sprite.name = "Building"
	_sprite.texture = FloraLibrary.texture(_entry.file)
	_sprite.centered = false
	_sprite.position = anchor
	_anims.clear()
	if not solid:  # lies flat on the ground (or is a deck), under everyone walking over it
		_sprite.z_as_relative = false
		_sprite.z_index = -5
		add_child(_sprite)
		_add_anims(-5)
		_lamps = null
		if _entry.get("night") != null:
			_add_lamps(anchor, -5)
		return
	add_child(_shadow(fp))
	add_child(_sprite)
	_add_anims(0)
	_add_lamps(anchor, 0)
	if smoke:
		for c: Array in _entry.get("chimney", []):
			add_child(_smoke(Vector2(c[0], c[1])))
	var mirrored: Array[Sprite2D] = [_sprite]
	for a: Array in _anims:
		mirrored.append(a[0])
	WaterReflection.attach(self, mirrored)
	var body := StaticBody2D.new()
	body.name = "Walls"
	for r: Rect2 in solid_rects_of(building):
		var shape := CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = r.size
		shape.shape = rect
		shape.position = r.get_center()
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


## Animated parts: every "<name>_frames" entry has its sheet in "<name>_file", the middle of a
## frame at "<name>", maybe a rate in "<name>_fps", and "<name>_night" if it only shows at night
## (a lamp's glow) or "<name>_nightfade" if it fades in at dusk and out at dawn (the night outside
## a window).
func _add_anims(z: int) -> void:
	for key: String in _entry:
		if not key.ends_with("_frames"):
			continue
		var part := key.trim_suffix("_frames")
		var a := Sprite2D.new()
		a.name = part.capitalize()
		a.texture = FloraLibrary.texture(_entry[part + "_file"])
		a.hframes = int(_entry[key])
		a.position = Vector2(_entry[part][0], _entry[part][1])
		if z != 0:
			a.z_as_relative = false
			a.z_index = z
		if _entry.get(part + "_night", false):  # a glow shown only from dusk to dawn, like the lamps
			a.visible = false
			a.add_to_group("night_lamps")
		if _entry.get(part + "_nightfade", false):
			a.self_modulate.a = 0.0  # DayNight fades it (group "night_fade")
			a.add_to_group("night_fade")
		add_child(a)
		_anims.append([a, float(_entry.get(part + "_fps", ANIM_FPS))])


func _add_lamps(anchor: Vector2, z: int) -> void:
	_lamps = Sprite2D.new()
	_lamps.name = "Lamps"
	_lamps.texture = FloraLibrary.texture(_entry.night)
	_lamps.centered = false
	_lamps.position = anchor
	_lamps.visible = false  # DayNight switches them on at dusk (group "night_lamps")
	_lamps.add_to_group("night_lamps")
	if z != 0:
		_lamps.z_as_relative = false
		_lamps.z_index = z
	add_child(_lamps)


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or _sprite == null:
		return
	_t += delta
	for a: Array in _anims:
		a[0].frame = int(_t * a[1]) % a[0].hframes
	if _lamps == null or not _solid:
		return
	# fade while a player is behind the building (above its base line, inside the picture)
	var behind := false
	var r := _rect
	for p in get_tree().get_nodes_in_group("player"):
		var d: Vector2 = (p as Node2D).global_position - global_position
		if d.y < -2.0 and d.y > r.position.y + 10.0 and d.x > r.position.x + 4.0 and d.x < r.end.x - 4.0:
			behind = true
	_fade = move_toward(_fade, FADE_ALPHA if behind else 1.0, delta * 3.0)
	_sprite.modulate.a = _fade
	for a: Array in _anims:
		a[0].modulate.a = _fade
	_lamps.modulate.a = 1.0 if _fade >= 1.0 and lamps_on else 0.0  # the lamp mark needs the exact colours


func grass_excludes(world: Vector2) -> bool:
	var e := sprite_rect_of(building)
	var fp := footprint_of(building)
	var d := world - global_position
	return d.x > fp.position.x - 3.0 and d.x < fp.end.x + 3.0 and d.y > e.position.y and d.y < 5.0


## A soft shadow under the whole footprint, a little to the right (the sun is up on the left),
## its rounded rim dithered like SoftShadow; only its edges show round the building.
static var _shadow_cache := {}


func _shadow(fp: Rect2) -> Sprite2D:
	var w := int(fp.size.x) + 10
	var h := int(fp.size.y) + 8
	var key := Vector2i(w, h)
	if not _shadow_cache.has(key):
		var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
		var r := 5.0
		for y in h:
			for x in w:
				var dx := maxf(0.0, absf(x + 0.5 - w / 2.0) - (w / 2.0 - r))
				var dy := maxf(0.0, absf(y + 0.5 - h / 2.0) - (h / 2.0 - r))
				var dd := (dx * dx + dy * dy) / (r * r)
				if dd > 1.0 or (dd > 0.5 and SoftShadow.BAYER[(y & 3) * 4 + (x & 3)] < 8):
					continue
				img.set_pixel(x, y, Color(0.06, 0.18, 0.1, 0.32 if dd < 0.4 else 0.18))
		_shadow_cache[key] = ImageTexture.create_from_image(img)
	var s := Sprite2D.new()
	s.name = "Shadow"
	s.texture = _shadow_cache[key]
	s.centered = false
	s.position = Vector2(fp.position.x - 3.0, fp.position.y - 2.0)
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

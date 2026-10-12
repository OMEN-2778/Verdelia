@tool
class_name WorldProp
extends Node2D
## Any single-sprite world object (bush, rock, ruin, stump, flower...). Place it at its base.
## It can sway, casts a soft shadow, keeps grass off its footprint and grows a skirt of tall grass
## around it so it sits in the meadow instead of on top of it.


@export var texture: Texture2D:
	set(v):
		texture = v
		_rebuild()
## Library shortcut instead of `texture`: "bush:<kind>", "rock" (variant from the position).
@export var library_item := "":
	set(v):
		library_item = v
		_rebuild()
@export var base_offset := 1  ## pixels of the sprite below the base point (feet sink into the ground)
@export var sway := 0.0
@export var shadow := true
@export_range(0.0, 2.0) var skirt := 1.0  ## tall-grass density around the base (0 = none)
@export var footprint := Vector2.ZERO  ## no-grass ellipse radii; zero = from the sprite size

var _size := Vector2.ZERO


func _ready() -> void:
	add_to_group("grass_exclude")
	add_to_group("grass_skirt")
	_rebuild()


func _rebuild() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		if c.owner == null:
			c.queue_free()
	var tex := texture
	if library_item != "":
		var pick := FloraLibrary.pick_at(global_position, 5)
		var parts := library_item.split(":")
		var e: Dictionary = FloraLibrary.rock(pick) if parts[0] == "rock" else FloraLibrary.bush(parts[1] if parts.size() > 1 else "green", pick)
		tex = FloraLibrary.texture(e.file)
	if tex == null:
		return
	var used := _used_rect(tex)  # ignore transparent margins
	_size = Vector2(used.size)
	if shadow:
		add_child(SoftShadow.sprite(int(_size.x * 0.85), int(maxf(4.0, _size.y * 0.22)), _size.x * 0.1))
	var s := Sprite2D.new()
	s.texture = tex
	s.centered = false
	s.position = Vector2(-used.position.x - floorf(_size.x / 2.0), -used.end.y + base_offset)
	if sway > 0.0:
		var m := ShaderMaterial.new()
		m.shader = preload("res://shaders/sway.gdshader")
		m.set_shader_parameter("amount", sway)
		s.material = m
	add_child(s)
	WaterReflection.attach(self, [s] as Array[Sprite2D])
	var front := TuftBatch.skirt(_skirt(true), global_position, FloraLibrary.pick_at(global_position, 17), _skirt_group())
	if front:
		add_child(front)


## Grass height in proportion to the object: short around pebbles and small rocks, tall around ruins.
static var _used_cache := {}


static func _used_rect(tex: Texture2D) -> Rect2i:
	if not _used_cache.has(tex):
		var img := tex.get_image()
		_used_cache[tex] = img.get_used_rect() if img else Rect2i(Vector2i.ZERO, Vector2i(tex.get_size()))
	return _used_cache[tex]


func grass_skirt_group() -> String:
	return _skirt_group()


func _skirt_group() -> String:
	return "meadow" if _size.y < 28.0 else "tall"


func _footprint() -> Vector2:
	return footprint if footprint != Vector2.ZERO else Vector2(_size.x * 0.42, maxf(3.0, _size.y * 0.14))


func grass_excludes(world: Vector2) -> bool:
	var f := _footprint()
	var d := world - global_position + Vector2(0, f.y * 0.6)
	return (d.x * d.x) / (f.x * f.x) + (d.y * d.y) / (f.y * f.y) < 1.0


func grass_skirt_points() -> PackedVector2Array:
	var out := PackedVector2Array()
	for p in _skirt(false):
		out.append(global_position + p)
	return out


## Skirt points in local coordinates; front=true: the ones at or below the base line (drawn by
## this prop over its sprite), false: the ones behind it (drawn by GrassField under the props).
func _skirt(front: bool) -> PackedVector2Array:
	var out := PackedVector2Array()
	if skirt <= 0.0 or _size.x < 10.0:
		return out
	var f := _footprint()
	var rng := RandomNumberGenerator.new()
	rng.seed = FloraLibrary.pick_at(global_position, 13)
	var n := int(f.x * 1.1 * skirt)
	for ring in [1.05, 1.35]:
		for i in n:
			# mostly along the front and sides, where the base meets the meadow
			var a := rng.randf_range(-PI, PI) if ring > 1.2 else lerpf(-0.35, PI + 0.35, rng.randf())
			var r: float = ring + rng.randf_range(-0.08, 0.12)
			var p := Vector2(cos(a) * f.x * r, sin(a) * f.y * r - f.y * 0.6 + 1.0).round()
			if (p.y >= -1.0) == front:
				out.append(p)
		n = int(n * 0.6)
	return out

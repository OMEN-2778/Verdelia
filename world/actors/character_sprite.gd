class_name CharacterSprite
extends AnimatedSprite2D
## A character built from Universal LPC parts by tools/art/lpc/build.py: art/characters/<id>/
## sheet.png and frames.json. Every action comes in the four directions it was drawn in
## ("walk_down", "walk_left", ...; LPC draws left and right separately, so nothing is flipped),
## and the moods face us ("mood_happy", ...). Each frame keeps its own time from frames.json. The
## node's origin is the point between the feet.
##
## AnimatedSprite2D rather than an AnimationPlayer: only the frame changes, nothing else needs
## keying in step with it.

@export var character := "hero_a":
	set(v):
		character = v
		if is_inside_tree():
			_load()

var facing := "down"
var action := "idle"

static var _cache := {}  # character -> [SpriteFrames, {animation: offset}]
var _offsets: Dictionary


func _ready() -> void:
	centered = false
	_load()
	act(action)


## Plays an action ("idle", "walk", "run", "work", "water", or a mood "mood_happy"...) facing
## `dir` ("up", "down", "left", "right"; empty keeps the way it faces). Calling it again with the
## same action carries on where it is.
func act(what: String, dir := "") -> void:
	if dir != "":
		facing = dir
	action = what
	var anim := what if what.begins_with("mood_") else "%s_%s" % [what, facing]
	if sprite_frames == null:
		return
	if not sprite_frames.has_animation(anim):
		anim = "idle_" + facing
	if animation != anim or not is_playing():
		play(anim)
	offset = _offsets.get(anim, Vector2.ZERO)


## The direction to face for a movement `v`: whichever of across or up-down is larger.
static func dir_of(v: Vector2) -> String:
	if absf(v.x) > absf(v.y):
		return "right" if v.x > 0.0 else "left"
	return "down" if v.y > 0.0 else "up"


func has_action(what: String, dir := "down") -> bool:
	return sprite_frames != null and sprite_frames.has_animation("%s_%s" % [what, dir])


func _load() -> void:
	if not _cache.has(character):
		_cache[character] = _build(character)
	var c: Array = _cache[character]
	sprite_frames = c[0]
	_offsets = c[1]


static func _build(id: String) -> Array:
	var dir := "res://art/characters/%s/" % id
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(dir + "frames.json"))
	var sheet: Texture2D = load(dir + "sheet.png")
	var frames := SpriteFrames.new()
	frames.remove_animation(&"default")
	var offsets := {}
	for anim: String in meta.animations:
		var a: Dictionary = meta.animations[anim]
		var w: int = a.size[0]
		var h: int = a.size[1]
		frames.add_animation(anim)
		frames.set_animation_speed(anim, 1.0)  # so each frame's duration is in seconds
		frames.set_animation_loop_mode(anim, SpriteFrames.LOOP_LINEAR if a.loop else SpriteFrames.LOOP_NONE)
		for f: Array in a.frames:
			var t := AtlasTexture.new()
			t.atlas = sheet
			t.region = Rect2(int(f[0]) * w, int(a.y), w, h)
			frames.add_frame(anim, t, float(f[1]))
		offsets[anim] = -Vector2(a.anchor[0], a.anchor[1])
	return [frames, offsets]

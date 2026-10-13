class_name Vista
extends Node2D
## The far view beyond a map's north edge (the map's `vista`), painted in layers by
## tools/art/vale/vista.py: sky, drifting clouds, a lake, mountain ranges with a bank of low
## cloud at their feet, forested hills, and the meadow's lip along the edge. The layers slide at
## different speeds as the camera moves (parallax), tile left to right for any map width, and sit
## lower the further down the map the camera is, so the view rises into sight as you look out.
##
## Walking up to the north edge makes the camera ease up slowly to take in the view (update_look,
## used by MapPlay and the editor's play mode), the way Hades pans out at a lookout.
## Coordinates: y = 0 is the map's top edge, negative is above it.

const KINDS := {"": "无", "mountains": "山脉"}
const REF_Y := -70.0  ## camera centre at the full look-out: every layer sits where it was painted
const LOOK_HEIGHT := 190.0  ## how far above the map's edge the top of the screen may go
const LOOK_ZONE := 56.0  ## walking this close to the north edge starts the look-out
const LOOK_EASE := 1.1  ## how quickly the camera eases up (and back): slow, like a held breath

## [file, horizontal factor, vertical factor, bottom y]; factor 1 moves with the map, 0 with the screen
const LAYERS := [
	["lake", 0.25, 0.3, 4.0],
	["peaks_far", 0.1, 0.3, -100.0],
	["peaks", 0.14, 0.3, -97.0],
	["haze", 0.16, 0.3, -92.0],
	["hills_far", 0.4, 0.5, -30.0],
	["hills", 0.6, 0.65, 2.0],
]
const HORIZON := -96.0
const BRINK_OVERLAP := 6.0  ## the meadow's lip overlaps the map by this much, dissolving into it
const SKY_FY := 0.3
## [file, x in the cloud band, y, drift px/s]; the band is CLOUD_SPAN wide and wraps round
const CLOUDS := [
	[0, 40.0, -206.0, 2.4], [1, 300.0, -186.0, 3.1], [2, 610.0, -214.0, 2.0], [3, 820.0, -168.0, 3.6],
	[4, 1030.0, -200.0, 2.2], [5, 1330.0, -176.0, 3.3], [3, 1480.0, -222.0, 2.7],
]
const CLOUD_SPAN := 1700.0
const CLOUD_FX := 0.06
const CLOUD_FY := 0.25

@export var kind := "mountains":
	set(v):
		kind = v
		if is_inside_tree():
			_build()

var look := 0.0  ## 0..1, how far the camera has eased up into the view
var _layers: Array = []  # [Sprite2D, fx, fy, bottom]
var _clouds: Array = []  # [Sprite2D, x, y, speed]
var _sky: Node2D
var _sky_tex: Texture2D
var _sky_top := Color()
var _brink: Sprite2D
var _t := 0.0
var _view := Rect2()
var _cam_y := 0.0


func _ready() -> void:
	z_as_relative = false
	z_index = -30
	process_priority = 50  # after the camera has moved this frame
	_build()


## The look-out amount (0..1, eased) for a player at `player_y`; MapPlay and the editor move
## their camera by it.
func update_look(player_y: float, delta: float) -> float:
	var want := 1.0 if player_y < LOOK_ZONE else 0.0
	look = lerpf(look, want, 1.0 - exp(-LOOK_EASE * delta))
	return smoothstep(0.0, 1.0, look)


func _build() -> void:
	for c in get_children():
		c.free()
	_layers.clear()
	_clouds.clear()
	_sky = null
	_brink = null
	if not KINDS.has(kind) or kind == "":
		return
	var dir := "res://art/vista/%s/" % kind
	_sky_tex = load(dir + "sky.png")
	_sky_top = _sky_tex.get_image().get_pixel(0, 0)
	_sky = Node2D.new()
	_sky.name = "Sky"
	_sky.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_sky.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	_sky.draw.connect(_draw_sky)
	add_child(_sky)
	for c in CLOUDS:
		var s := _sprite(load(dir + "cloud_%d.png" % c[0]), false)
		s.name = "Cloud"
		_clouds.append([s, c[1], c[2], c[3]])
	for l in LAYERS:
		var s := _sprite(load(dir + l[0] + ".png"), true)
		s.name = l[0]
		if l[0] == "lake":
			var m := ShaderMaterial.new()
			m.shader = preload("res://world/fx/vista_lake.gdshader")
			s.material = m
		_layers.append([s, l[1], l[2], l[3]])
	_brink = _sprite(load(dir + "brink.png"), true)
	_brink.name = "Brink"
	_brink.z_as_relative = false
	_brink.z_index = -8  # over the ground's top edge, under the grass and everyone walking
	_place()


func _sprite(tex: Texture2D, tiled: bool) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = tex
	s.centered = false
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	if tiled:
		s.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		s.region_enabled = true
	add_child(s)
	return s


func _process(delta: float) -> void:
	_t += delta
	_place()


## Puts every layer where the camera sees it.
func _place() -> void:
	if _sky == null:
		return
	var cam := get_viewport().get_camera_2d()
	var centre := cam.get_screen_center_position() if cam else get_viewport_rect().size * 0.5
	var size := get_viewport_rect().size / (cam.zoom if cam else Vector2.ONE)
	_view = Rect2(centre - size * 0.5, size).grow(2.0)
	_cam_y = centre.y
	var low := maxf(centre.y - REF_Y, 0.0)  # how far below the look-out the camera is
	var left := floorf(_view.position.x)
	var w := ceilf(_view.size.x) + 2.0
	for l in _layers:
		var s: Sprite2D = l[0]
		var h := float(s.texture.get_height())
		s.position = Vector2(left, roundf(l[3] - h + low * (1.0 - l[2])))
		s.region_rect = Rect2(left - roundf(centre.x * (1.0 - l[1])), 0, w, h)
	var bh := float(_brink.texture.get_height())
	_brink.position = Vector2(left, BRINK_OVERLAP - bh)
	_brink.region_rect = Rect2(left, 0, w, bh)
	for c in _clouds:
		var s: Sprite2D = c[0]
		var x := fposmod(c[1] + _t * c[3] - centre.x * CLOUD_FX, CLOUD_SPAN) - 200.0
		s.position = Vector2(roundf(left + x), roundf(c[2] + low * (1.0 - CLOUD_FY)))
	_sky.queue_redraw()


func _draw_sky() -> void:
	var low := maxf(_cam_y - REF_Y, 0.0)
	var bottom := roundf(HORIZON + low * (1.0 - SKY_FY))
	var h := float(_sky_tex.get_height())
	var top := bottom - h
	if _view.position.y < top:
		_sky.draw_rect(Rect2(_view.position.x, _view.position.y, _view.size.x, top - _view.position.y + 1.0), _sky_top)
	_sky.draw_texture_rect(_sky_tex, Rect2(floorf(_view.position.x / 8.0) * 8.0, top, _view.size.x + 8.0, h), true)

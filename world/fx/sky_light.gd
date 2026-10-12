extends Node2D
## Drifting cloud shadows, or (with `shafts` on) warm light shafts slanting from the upper left,
## over `area` (set it to the map size). Use two instances: one normal-blended for clouds, one
## additive for shafts.

@export var shafts := false
@export var cloud_alpha := 0.17
@export var shaft_colour := Color("#fff1c4")
@export var shaft_angle := -0.42  ## radians; DayNight swings it with the sun
## 0 = the full row of steady shafts; 1 = only now and then one or two beams in view (DayNight
## uses this around noon)
@export_range(0.0, 1.0) var sparse := 0.0
@export var area := Vector2(426, 240)
@export var cloud_texture: Texture2D
@export var shaft_texture: Texture2D

var _clouds: Array[Dictionary] = []
var _shafts: Array[Dictionary] = []


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	var n_clouds := maxi(5, int(area.x * area.y / 20000.0))
	for i in n_clouds:
		_clouds.append({"p": Vector2(randf_range(-300, area.x + 300), randf_range(-100, area.y + 100)), "s": randf_range(0.9, 1.6)})
	var n_shafts := maxi(6, int(area.x / 70.0))
	for i in n_shafts:
		_shafts.append({"x": (i + randf_range(0.1, 0.9)) / n_shafts * (area.x + 300) - 150, "w": randf_range(28, 70), "ph": randf() * TAU})


func _process(dt: float) -> void:
	for c in _clouds:
		c.p += Vector2(7, 1.5) * dt
		if c.p.x > area.x + 360:
			c.p = Vector2(-360, randf_range(-100, area.y + 100))
	queue_redraw()


func _draw() -> void:
	if not shafts:
		for c in _clouds:
			var size: Vector2 = Vector2(400, 240) * float(c.s)
			draw_texture_rect(cloud_texture, Rect2(c.p - size / 2.0, size), false, Color(1, 1, 1, cloud_alpha))
		return
	var t := Wind.now()
	var steady := 1.0 - sparse
	if steady > 0.0:
		for s in _shafts:
			var a: float = (0.07 + 0.045 * sin(t * 0.35 + float(s.ph))) * steady
			draw_set_transform(Vector2(s.x, -80), shaft_angle)
			draw_texture_rect(shaft_texture, Rect2(-s.w / 2.0, 0, s.w, area.y + 300), false, Color(shaft_colour, a))
	if sparse > 0.0:
		_draw_occasional_beams(t)
	draw_set_transform(Vector2.ZERO)


## Two beams that take turns: each fades in somewhere in view, lingers, fades out, and after a
## pause comes back at a new spot.
func _draw_occasional_beams(t: float) -> void:
	var cam := get_viewport().get_camera_2d()
	var view := get_viewport_rect().size
	var centre := cam.get_screen_center_position() if cam else view / 2.0
	for k in 2:
		var period := 17.0 + k * 5.0
		var ph := t / period + k * 0.47
		var cycle := floorf(ph)
		var f := ph - cycle
		var env := smoothstep(0.0, 0.18, f) * (1.0 - smoothstep(0.42, 0.6, f))  # shines ~half the time
		if env <= 0.0:
			continue
		var h := fposmod(sin(cycle * 12.9898 + k * 78.233) * 43758.5453, 1.0)
		var x := centre.x - view.x * 0.4 + h * view.x * 0.8
		var w := 30.0 + fposmod(h * 7.31, 1.0) * 26.0
		var a := 0.24 * env * sparse
		draw_set_transform(Vector2(x, centre.y - view.y * 0.5 - 40.0), shaft_angle)
		draw_texture_rect(shaft_texture, Rect2(-w / 2.0, 0, w, view.y + 120), false, Color(shaft_colour, a))

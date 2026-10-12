class_name DayNight
extends Node
## The day: sunrise, noon, dusk and night in a seamless loop, as a sense of time passing.
##
## Holds the game clock (`hour`, shared by all scenes so time keeps running across maps) and, from a
## handful of keyframes, works out the light at every moment: overall colour, the warm light and
## cool shade (which travel with the sun from left to right), saturation, light shafts and their
## angle, cloud shadows, how long the shadows are and which way they fall, and the sun's (or
## moon's) glitter on the water. The keyframes are blended with a looping Catmull-Rom curve, so
## nothing jumps or pauses. At night fireflies come out; a small clock shows the time.
##
## Put one in a scene and point it at the scene's full-screen grade (`grade`), and optionally the
## cloud and shaft layers. Nodes in the group "daytime_only" (butterflies...) fade out at night.

@export var cycle_minutes := 12.0  ## real minutes for a whole day
@export_range(0.0, 24.0) var start_hour := 6.0  ## used when the clock has not started yet
@export var paused := false
@export var grade: CanvasItem  ## the ColorRect with grade.gdshader
@export var clouds: Node2D  ## sky_light.gd instance drawing cloud shadows
@export var shafts: Node2D  ## sky_light.gd instance drawing light shafts
@export var fireflies := true
@export var show_clock := true

static var hour := -1.0  ## 0..24, the shared game clock (-1 = not started)

# hour, ambient, warm (a = strength), cool (a = strength), saturation, contrast, lift,
# sun on water (a = glitter), shafts, clouds, shadow strength, daylight (0 night .. 1 full day),
# sky colour the water reflects (a = how much it tints the water)
const KEYS := [
	[0.0, Color(0.27, 0.32, 0.56), Color(0.55, 0.65, 1.0, 0.12), Color(0.05, 0.08, 0.2, 0.5), 0.62, 0.92, 0.03, Color(0.72, 0.84, 1.0, 0.32), 0.0, 0.03, 0.22, 0.0, Color(0.1, 0.14, 0.32, 0.6)],
	[4.6, Color(0.29, 0.33, 0.58), Color(0.6, 0.65, 1.0, 0.12), Color(0.05, 0.08, 0.2, 0.5), 0.64, 0.92, 0.03, Color(0.72, 0.84, 1.0, 0.3), 0.0, 0.03, 0.22, 0.0, Color(0.12, 0.15, 0.34, 0.6)],
	[5.6, Color(0.52, 0.45, 0.66), Color(1.0, 0.56, 0.5, 0.28), Color(0.12, 0.1, 0.28, 0.45), 0.74, 0.95, 0.02, Color(1.0, 0.62, 0.55, 0.45), 0.05, 0.06, 0.28, 0.15, Color(0.5, 0.42, 0.66, 0.5)],
	[6.6, Color(1.0, 0.87, 0.8), Color(1.0, 0.68, 0.48, 0.34), Color(0.18, 0.12, 0.3, 0.38), 0.95, 1.0, 0.0, Color(1.0, 0.72, 0.45, 1.0), 0.65, 0.12, 0.55, 0.55, Color(1.0, 0.66, 0.74, 0.44)],
	[8.2, Color(1.0, 0.96, 0.9), Color(1.0, 0.88, 0.66, 0.26), Color(0.1, 0.18, 0.3, 0.35), 0.97, 1.0, 0.0, Color(1.0, 0.95, 0.85, 0.9), 1.0, 0.17, 0.9, 0.95, Color(0.55, 0.75, 0.95, 0.2)],
	[12.0, Color(1.0, 1.0, 0.98), Color(1.0, 0.925, 0.667, 0.2), Color(0.078, 0.196, 0.314, 0.35), 1.0, 1.0, 0.0, Color(1.0, 1.0, 0.95, 0.85), 0.8, 0.17, 1.0, 1.0, Color(0.48, 0.72, 0.95, 0.15)],
	[15.8, Color(1.0, 0.96, 0.87), Color(1.0, 0.86, 0.58, 0.3), Color(0.1, 0.16, 0.3, 0.36), 1.0, 1.0, 0.0, Color(1.0, 0.92, 0.75, 0.9), 0.9, 0.17, 0.9, 1.0, Color(0.55, 0.74, 0.92, 0.2)],
	[17.9, Color(1.0, 0.8, 0.62), Color(1.0, 0.6, 0.3, 0.42), Color(0.22, 0.1, 0.26, 0.38), 1.02, 1.02, 0.0, Color(1.0, 0.62, 0.3, 1.0), 0.95, 0.14, 0.65, 0.75, Color(1.0, 0.7, 0.6, 0.46)],
	[19.0, Color(0.6, 0.56, 0.8), Color(1.0, 0.5, 0.55, 0.3), Color(0.14, 0.08, 0.26, 0.45), 0.84, 0.97, 0.01, Color(1.0, 0.52, 0.48, 0.5), 0.12, 0.08, 0.35, 0.3, Color(0.66, 0.52, 0.8, 0.46)],
	[20.4, Color(0.33, 0.37, 0.61), Color(0.55, 0.62, 1.0, 0.12), Color(0.05, 0.08, 0.2, 0.5), 0.64, 0.92, 0.03, Color(0.72, 0.84, 1.0, 0.3), 0.0, 0.03, 0.22, 0.0, Color(0.14, 0.18, 0.38, 0.6)],
]

var _firefly_layer: CanvasLayer
var _fireflies: CPUParticles2D
var _clock: Node2D
var _shadow_tick := 0.0


func _ready() -> void:
	if hour < 0.0:
		hour = start_hour
	if fireflies:
		_make_fireflies()
	if show_clock:
		_make_clock()
	_apply(0.0)


func _process(delta: float) -> void:
	if not paused:
		hour = fmod(hour + delta * 24.0 / (cycle_minutes * 60.0), 24.0)
	_apply(delta)


## 0..1 how much daylight there is (0 at night, 1 from mid-morning to late afternoon).
static func daylight() -> float:
	return clampf(_sample(hour)[10], 0.0, 1.0)


## "HH:MM" of the shared clock.
static func clock_text() -> String:
	var h := int(hour)
	var m := int((hour - h) * 60.0)
	return "%02d:%02d" % [h, m]


func _apply(delta: float) -> void:
	var k := _sample(hour)
	var ambient: Color = k[0]
	var warm: Color = k[1]
	var cool: Color = k[2]
	var sun_water: Color = k[6]
	var day: float = clampf(k[10], 0.0, 1.0)
	var night := 1.0 - smoothstep(0.22, 0.5, day)
	# the sun climbs on the left in the morning and sets on the right; the moon does the same at night
	var arc := fmod(hour - 6.0 + 24.0, 12.0) / 12.0  # 0 rising .. 1 setting
	var sun_x := -cos(arc * PI)  # -1 left .. +1 right
	var height := sin(arc * PI)  # 0 on the horizon .. 1 overhead
	if grade and grade.material is ShaderMaterial:
		var m := grade.material as ShaderMaterial
		m.set_shader_parameter("tint", Vector3(ambient.r, ambient.g, ambient.b))
		m.set_shader_parameter("warm", warm)
		m.set_shader_parameter("cool", cool)
		m.set_shader_parameter("saturation", k[3])
		m.set_shader_parameter("contrast", k[4])
		m.set_shader_parameter("lift", k[5])
		m.set_shader_parameter("warm_origin", Vector2(0.5 + sun_x * 0.62, -0.08 - (1.0 - height) * 0.1))
	RenderingServer.global_shader_parameter_set("day_sun", sun_water)
	RenderingServer.global_shader_parameter_set("day_sky", k[11])
	if shafts:
		shafts.modulate.a = k[7]
		shafts.set("shaft_colour", Color(warm.r, warm.g, warm.b).lerp(Color("#fff1c4"), 0.5))
		shafts.set("shaft_angle", sun_x * 0.5)
	if clouds:
		clouds.set("cloud_alpha", k[8])
	for n in get_tree().get_nodes_in_group("daytime_only"):
		(n as CanvasItem).modulate.a = smoothstep(0.35, 0.75, day)
	_shadow_tick -= delta
	if _shadow_tick <= 0.0:
		_shadow_tick = 0.1
		_update_shadows(sun_x, height, k[9])
	if _fireflies:
		_fireflies.modulate.a = night
		_fireflies.emitting = night > 0.05
		var cam := get_viewport().get_camera_2d()
		if cam:
			_fireflies.global_position = cam.get_screen_center_position()
	if _clock:
		_clock.queue_redraw()


## Shadows lean away from the sun: long and to the right in the morning, short at noon, long to the
## left at dusk; faint under the moon.
func _update_shadows(sun_x: float, height: float, strength: float) -> void:
	var stretch := 1.0 + (1.0 - height) * 0.9
	for s in get_tree().get_nodes_in_group("sun_shadows"):
		var sp := s as Sprite2D
		var w: float = sp.get_meta("w", 10.0)
		var base: Vector2 = sp.get_meta("base", Vector2.ZERO)
		sp.position = base + Vector2(roundf(-sun_x * w * 0.32 * (1.0 - height * 0.6)), 0.0)
		sp.scale = Vector2(stretch, 1.0)
		sp.modulate.a = strength


static func _sample(h: float) -> Array:
	var n := KEYS.size()
	var i := n - 1
	for j in n:
		if KEYS[j][0] > h:
			i = j - 1
			break
	if i < 0:
		i = n - 1
	var k1: Array = KEYS[i]
	var k2: Array = KEYS[(i + 1) % n]
	var h1: float = k1[0]
	var h2: float = k2[0] + (24.0 if (i + 1) >= n else 0.0)
	var hh := h + (24.0 if h < h1 else 0.0)
	var t := (hh - h1) / maxf(h2 - h1, 0.001)
	var k0: Array = KEYS[(i - 1 + n) % n]
	var k3: Array = KEYS[(i + 2) % n]
	var out := []
	for f in range(1, k1.size()):
		out.append(_catmull(k0[f], k1[f], k2[f], k3[f], t))
	return out


static func _catmull(a, b, c, d, t: float):
	var t2 := t * t
	var t3 := t2 * t
	if b is Color:
		var r := Color()
		for ch in 4:
			r[ch] = clampf(0.5 * (2.0 * b[ch] + (-a[ch] + c[ch]) * t + (2.0 * a[ch] - 5.0 * b[ch] + 4.0 * c[ch] - d[ch]) * t2 + (-a[ch] + 3.0 * b[ch] - 3.0 * c[ch] + d[ch]) * t3), 0.0, 1.2)
		return r
	return 0.5 * (2.0 * b + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2 + (-a + 3.0 * b - 3.0 * c + d) * t3)


func _make_fireflies() -> void:
	_firefly_layer = CanvasLayer.new()
	_firefly_layer.layer = 2  # above the grade, so they glow instead of being darkened with the scene
	_firefly_layer.follow_viewport_enabled = true
	add_child(_firefly_layer)
	var p := CPUParticles2D.new()
	p.amount = 26
	p.lifetime = 5.0
	p.preprocess = 5.0
	p.local_coords = false
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(240, 140)
	p.direction = Vector2(1, -0.3)
	p.spread = 180.0
	p.gravity = Vector2.ZERO
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 6.0
	p.angular_velocity_min = 0.0
	p.angle_min = 0.0
	p.texture = _glow_texture()
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color(1, 1, 1, 1), Color(1, 1, 1, 0.3), Color(1, 1, 1, 1), Color(1, 1, 1, 0.2), Color(1, 1, 1, 0.9), Color(1, 1, 1, 0)])
	p.color_ramp = g
	p.color = Color(0.85, 1.0, 0.55)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	p.material = mat
	_firefly_layer.add_child(p)
	_fireflies = p


static func _glow_texture() -> ImageTexture:
	var img := Image.create(5, 5, false, Image.FORMAT_RGBA8)
	for y in 5:
		for x in 5:
			var d := absf(x - 2.0) + absf(y - 2.0)
			var a := 1.0 if d == 0.0 else (0.45 if d == 1.0 else (0.12 if d == 2.0 and (x == 2 or y == 2) else 0.0))
			img.set_pixel(x, y, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)


func _make_clock() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 3
	add_child(layer)
	_clock = DayClockHud.new()
	layer.add_child(_clock)

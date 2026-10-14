extends Node2D
## Plays a map made in the map editor: builds the world from the map file, puts the walking
## character at the spawn point with a following camera, and runs the day. Walking up to the
## north edge of a map with a vista eases the camera up to take in the view.
## The map comes from `map_path`, or from the command line: `-- --map=/path/to/map.json`.
## Doors linked to other maps (the stairs up to the attic and back) fade over to that map. Indoors at
## night, the room you are in has its lights on and the others are dark (RoomLights).

@export_file("*.json") var map_path := "res://maps/sample.json"
@export var start_hour := 9.0

var world: MapWorld
var player: CharacterBody2D
var cam: Camera2D
var day: DayNight
var rooms: RoomLights
var _fade: ColorRect
var _moving := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--map="):
			map_path = a.trim_prefix("--map=")
	world = MapWorld.new()
	add_child(world)
	if not world.load_map(map_path):
		push_warning("map not found: " + map_path)
	player = CharacterBody2D.new()
	player.set_script(preload("res://world/demo/demo_player.gd"))
	var shadow := Sprite2D.new()
	shadow.name = "Shadow"
	shadow.texture = preload("res://art/library/fx/shadow.png")
	player.add_child(shadow)
	var body := Sprite2D.new()
	body.name = "Body"
	body.texture = preload("res://art/library/props/mage.png")
	body.hframes = 4
	body.offset = Vector2(0, -10)
	player.add_child(body)
	cam = Camera2D.new()
	cam.position_smoothing_enabled = true
	cam.position_smoothing_speed = 4.0
	player.add_child(cam)
	player.set("autopilot", false)
	world.props.add_child(player)
	_arrive(Vector2(-1, -1))
	world.door_used.connect(_use_door)
	world.grass.player = player
	# the look: full-screen grade and the day passing
	var layer := CanvasLayer.new()
	add_child(layer)
	var screen := ColorRect.new()
	screen.set_anchors_preset(Control.PRESET_FULL_RECT)
	screen.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/grade.gdshader")
	m.set_shader_parameter("vignette", 0.12)
	m.set_shader_parameter("bloom_strength", 0.35)
	m.set_shader_parameter("bloom_threshold", 0.78)
	m.set_shader_parameter("cloud_strength", 0.0)
	screen.material = m
	layer.add_child(screen)
	rooms = RoomLights.new()  # indoors at night, the lights of the room you are in
	rooms.world = world
	rooms.player = player
	rooms.grade = m
	add_child(rooms)
	rooms.reset()
	day = DayNight.new()
	day.start_hour = start_hour
	day.fireflies = not world.data.indoor
	day.grade = screen
	add_child(day)
	var top := CanvasLayer.new()
	top.layer = 10
	add_child(top)
	_fade = ColorRect.new()
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.color = Color(0, 0, 0, 0)
	top.add_child(_fade)


## Puts the player at `at` (or the map's spawn) and fits the camera to the map; a map smaller
## than the screen (a small house) sits in the middle of it, in the dark.
func _arrive(at: Vector2) -> void:
	var size := world.data.size_px()
	var view := get_viewport_rect().size / cam.zoom
	var mx := maxf(0.0, (view.x - size.x) * 0.5)
	var my := maxf(0.0, (view.y - size.y) * 0.5)
	cam.limit_left = int(-mx)
	cam.limit_top = int(-my)
	cam.limit_right = int(size.x + mx)
	cam.limit_bottom = int(size.y + my)
	RenderingServer.set_default_clear_color(Color(0.055, 0.047, 0.067) if world.data.indoor else Color(0.3, 0.3, 0.3))
	if at.x < 0:
		at = world.data.spawn if world.data.spawn.x >= 0 else size * 0.5
	player.position = at
	cam.reset_smoothing.call_deferred()


## Fades out, loads the map the door leads to, puts the player there, fades back in.
func _use_door(to: String, at: Vector2) -> void:
	if _moving:
		return
	_moving = true
	player.set_physics_process(false)
	var t := create_tween()
	t.tween_property(_fade, "color:a", 1.0, 0.25)
	await t.finished
	if world.load_map(to):
		map_path = to
		_arrive(at)
		if day:
			day.fireflies = not world.data.indoor
		rooms.reset()
	await get_tree().create_timer(0.1).timeout
	player.set_physics_process(true)
	t = create_tween()
	t.tween_property(_fade, "color:a", 0.0, 0.3)
	await t.finished
	_moving = false


func _process(delta: float) -> void:
	if cam == null or world.data.vista == "":
		return
	# look out over the vista: the camera may rise above the map's edge and is pulled up to it
	var k := world.vista.update_look(player.position.y, delta)
	cam.limit_top = int(-Vista.LOOK_HEIGHT * k)
	cam.position.y = -Vista.LOOK_HEIGHT * 1.4 * k  # (not offset: that would ignore the limit)

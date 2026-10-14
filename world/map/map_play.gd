extends Node2D
## Plays a map made in the map editor: builds the world from the map file, puts the walking
## character at the spawn point with a following camera, and runs the day. Walking up to the
## north edge of a map with a vista eases the camera up to take in the view.
## The map comes from `map_path`, or from the command line: `-- --map=/path/to/map.json`.

@export_file("*.json") var map_path := "res://maps/sample.json"
@export var start_hour := 9.0

var world: MapWorld
var player: CharacterBody2D
var cam: Camera2D


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
	var size := world.data.size_px()
	cam.limit_left = 0
	cam.limit_top = 0
	cam.limit_right = int(size.x)
	cam.limit_bottom = int(size.y)
	player.add_child(cam)
	player.set("autopilot", false)
	player.position = world.data.spawn if world.data.spawn.x >= 0 else size * 0.5
	world.props.add_child(player)
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
	var day := DayNight.new()
	day.start_hour = start_hour
	day.fireflies = not world.data.indoor
	day.grade = screen
	add_child(day)


func _process(delta: float) -> void:
	if cam == null or world.data.vista == "":
		return
	# look out over the vista: the camera may rise above the map's edge and is pulled up to it
	var k := world.vista.update_look(player.position.y, delta)
	cam.limit_top = int(-Vista.LOOK_HEIGHT * k)
	cam.position.y = -Vista.LOOK_HEIGHT * 1.4 * k  # (not offset: that would ignore the limit)

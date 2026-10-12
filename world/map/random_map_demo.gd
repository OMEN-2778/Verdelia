extends Node2D
## Generates a random map (MapGenerator) and sends the character on a tour of it: past the lake,
## up one ramp, along the upper level by the pond, down another ramp, over the bridge and up the
## third ramp. Seed from `seed`, or `-- --seed=123` on the command line (0 = new every run).
## Arrow keys / WASD take over from the tour.

@export var seed := 0
@export var start_hour := 8.5
@export var save_to := "res://maps/random.json"  ## also saves the map so it can be opened in the editor

var world: MapWorld
var player: CharacterBody2D


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--seed="):
			seed = int(a.trim_prefix("--seed="))
	if seed == 0:
		seed = randi() % 100000 + 1
	print("random map seed ", seed)
	var data := MapGenerator.generate(seed)
	if save_to != "":
		data.save(ProjectSettings.globalize_path(save_to))
	world = MapWorld.new()
	add_child(world)
	world.load_data(data)
	_add_player(data)
	_add_look()
	_plan_tour.call_deferred()


func _plan_tour() -> void:
	await get_tree().process_frame  # cliffs generate first
	var p := MapGenerator.points
	var feet: Array = p.ramp_feet
	var tops: Array = p.ramp_tops
	var stops: Array = [p.spawn, p.lake]
	var near := 0 if (p.lake as Vector2).x < (p.spawn as Vector2).x else 2
	var far := 2 - near
	stops.append_array([feet[near], tops[near], p.pond, tops[far], feet[far]])
	if p.has("field"):
		stops.append(p.field)
	stops.append_array([p.bridge_south, p.spawn, feet[1], tops[1]])
	player.set("waypoints", MapRoute.plan(world, stops))
	player.set("autopilot", true)


func _add_player(data: MapData) -> void:
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
	var cam := Camera2D.new()
	cam.position_smoothing_enabled = true
	cam.position_smoothing_speed = 3.0
	var size := data.size_px()
	cam.limit_left = 0
	cam.limit_top = 0
	cam.limit_right = int(size.x)
	cam.limit_bottom = int(size.y)
	player.add_child(cam)
	player.set("autopilot", false)
	player.set("pause", 0.0)
	player.set("speed", 58.0)
	player.position = data.spawn
	world.props.add_child(player)
	world.grass.player = player


func _add_look() -> void:
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
	var flies := Node2D.new()
	flies.set_script(preload("res://world/fx/butterflies.gd"))
	flies.set("player", player)
	flies.set("count", 16)
	flies.set("bounds", Rect2(Vector2(10, 10), world.data.size_px() - Vector2(20, 20)))
	flies.z_index = 6
	flies.add_to_group("daytime_only")
	add_child(flies)
	var day := DayNight.new()
	day.start_hour = start_hour
	day.grade = screen
	add_child(day)

extends CharacterBody2D
## Demo protagonist that really walks: collides with cliffs (it can only go up and down through
## ramps) and is steered with WASD / the arrow keys. Until a key is pressed it walks `waypoints` on
## its own (still colliding), skipping a waypoint it cannot reach, which is handy for recordings.
## Slower on ramps, with a little bounce on stairs. The body is a CharacterSprite (walking and
## standing in four directions) or a plain four-frame Sprite2D, mirrored for the left.

@export var waypoints: PackedVector2Array
@export var speed := 50.0
@export var pause := 0.8
@export var autopilot := true

@onready var body: Node2D = $Body

var _i := 0
var _wait := 0.0
var _t := 0.0
var _stuck := 0.0


func _ready() -> void:
	add_to_group("player")  # houses fade when the player walks behind them
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	if get_node_or_null("Feet") == null:
		var shape := CollisionShape2D.new()
		shape.name = "Feet"
		var c := CircleShape2D.new()
		c.radius = 3.0
		shape.shape = c
		add_child(shape)


# Moves in _process (not _physics_process) so the walk and the following camera advance together on
# every rendered frame: no stutter where the physics tick and the frame rate disagree.
func _process(dt: float) -> void:
	_t += dt
	var dir := _keys()
	if dir != Vector2.ZERO:
		autopilot = false
	elif autopilot:
		dir = _autopilot(dt)
	var on_ramp := -1
	for c in get_tree().get_nodes_in_group("cliffs"):
		var s: int = c.ramp_at(global_position)
		if s >= 0:
			on_ramp = s
	var mul := 0.68 if on_ramp == 1 else (0.82 if on_ramp == 0 or on_ramp == 2 else 1.0)
	velocity = dir * speed * mul
	var before := global_position
	move_and_slide()
	var moved := global_position.distance_to(before)
	if autopilot and dir != Vector2.ZERO:
		# blocked (walked into a cliff face): give up on this waypoint after a moment
		_stuck = _stuck + dt if moved < speed * mul * dt * 0.25 else 0.0
		if _stuck > 1.1:
			_stuck = 0.0
			_next()
	_animate(dir, on_ramp)


func _keys() -> Vector2:
	var v := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if Input.is_physical_key_pressed(KEY_A): v.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D): v.x += 1.0
	if Input.is_physical_key_pressed(KEY_W): v.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S): v.y += 1.0
	return v.limit_length(1.0)


func _autopilot(dt: float) -> Vector2:
	if waypoints.is_empty():
		return Vector2.ZERO
	if _wait > 0.0:
		_wait -= dt
		return Vector2.ZERO
	var to := waypoints[_i] - global_position
	if to.length() < 2.0:
		_next()
		_wait = pause
		return Vector2.ZERO
	return to.normalized() * minf(1.0, to.length() / 4.0)


func _next() -> void:
	_i = (_i + 1) % waypoints.size()


func _animate(dir: Vector2, on_ramp: int) -> void:
	if body is CharacterSprite:
		var cs := body as CharacterSprite
		if dir.length() < 0.05:
			cs.act("idle")
		else:
			cs.act("walk", CharacterSprite.dir_of(dir))
		# up the stairs every other step lifts him a pixel more
		cs.position.y = -1.0 if on_ramp == 1 and cs.frame % 4 >= 2 else 0.0
		return
	var spr := body as Sprite2D
	var h := spr.texture.get_height() / 2.0
	if dir.length() < 0.05:
		spr.frame = 0
		spr.offset.y = -h + (1.0 if int(_t / 0.5) % 2 else 0.0)
		return
	if absf(dir.x) > 0.2:
		spr.flip_h = dir.x < 0.0
	spr.frame = int(_t * 8.0) % 4
	var bob := 1.0 if spr.frame % 2 else 0.0
	if on_ramp == 1:
		bob = 2.0 if spr.frame % 2 else 0.0  # stepping up the stairs
	spr.offset.y = -h - bob

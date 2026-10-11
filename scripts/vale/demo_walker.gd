extends Node2D
## Placeholder protagonist for the demo: walks a loop of waypoints so the grass reaction shows.

@export var waypoints: PackedVector2Array
@export var speed := 34.0
@export var pause := 1.2

@onready var body: Sprite2D = $Body

var _i := 0
var _wait := 0.0
var _t := 0.0


func _process(dt: float) -> void:
	_t += dt
	if waypoints.is_empty():
		return
	if _wait > 0.0:
		_wait -= dt
		body.frame = 0
		body.offset.y = -body.texture.get_height() / 2.0 + (1.0 if int(_t / 0.5) % 2 else 0.0)
		return
	var target := waypoints[_i]
	var to := target - position
	if to.length() < 1.0:
		_i = (_i + 1) % waypoints.size()
		_wait = pause
		return
	position += to.normalized() * minf(speed * dt, to.length())
	if absf(to.x) > 0.5:
		body.flip_h = to.x < 0.0
	body.frame = int(_t * 8.0) % 4
	body.offset.y = -body.texture.get_height() / 2.0 - (1.0 if body.frame % 2 else 0.0)

extends Sprite2D
## Breathing idle: the sprite rises one pixel every other beat.

@export var beat := 0.55

var _t := 0.0


func _process(delta: float) -> void:
	_t += delta
	offset.y = -texture.get_height() / 2.0 - (1.0 if int(_t / beat) % 2 == 1 else 0.0)

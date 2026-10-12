extends Polygon2D
## Slowly breathing sun shaft (additive; brightness comes from the vertex colours).
## Fades out as the world gets dark.

@export var day_cycle: CanvasModulate

var _phase := randf() * TAU


func _process(_delta: float) -> void:
	var t := Wind.now()
	var daylight := 1.0
	if day_cycle:
		daylight = clampf((day_cycle.color.get_luminance() - 0.55) / 0.35, 0.0, 1.0)
	modulate.a = (0.7 + 0.3 * sin(t * 0.6 + _phase)) * daylight

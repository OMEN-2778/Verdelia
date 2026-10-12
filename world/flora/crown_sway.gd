extends Sprite2D
## One crown layer of a tree: sways with the wind (out of step with its sibling layers) and
## brightens briefly when a gust flips the leaves.

var base := Vector2.ZERO
var phase := 0.0
var amount := 1.0


func _ready() -> void:
	base = position


func _process(_delta: float) -> void:
	var t := Wind.now()
	var gp := global_position - position + base
	var wind := Wind.at(gp.x, gp.y, t)
	var sw := (wind.x * 0.45 + sin(t * 1.1 + phase) * 0.35 + sin(t * 2.3 + phase * 1.7) * 0.18) * amount
	# moves in steps of one screen pixel (1/3 of a world pixel): smooth, but never blurred
	var off := Vector2(sw, absf(sw) * 0.2 + sin(t * 1.6 + phase) * 0.35 * amount)
	position = base + (off * 3.0).round() / 3.0
	var shimmer := 1.0 + 0.1 * wind.y
	modulate = Color(shimmer, shimmer, shimmer * 0.97)

extends Sprite2D
## Tree crown swaying with the wind; the trunk stays put.

var base := Vector2.ZERO
var phase := 0.0
var amount := 1.0  ## pines sway less than broadleaf crowns


func _ready() -> void:
	base = position


func _process(_delta: float) -> void:
	var t := Wind.now()
	var gp: Vector2 = (get_parent() as Node2D).position
	var wind := Wind.at(gp.x + base.x, gp.y, t)
	var sw := (wind.x * 0.45 + sin(t * 1.1 + phase) * 0.35 + sin(t * 2.3 + phase * 1.7) * 0.18) * amount
	position = base + Vector2(roundf(sw), roundf(absf(sw) * 0.2 + sin(t * 1.6 + phase) * 0.35 * amount))
	# a passing gust flips leaves to their pale undersides: the crown brightens briefly
	var shimmer := 1.0 + 0.1 * wind.y
	modulate = Color(shimmer, shimmer, shimmer * 0.97)

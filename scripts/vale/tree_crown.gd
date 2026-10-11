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
	var sw := (Wind.at(gp.x, gp.y, t).x * 0.45 + sin(t * 1.1 + phase) * 0.35) * amount
	position = base + Vector2(roundf(sw), roundf(absf(sw) * 0.15))

extends Node2D
## Butterflies wandering over the meadow; they flutter away from the player.

@export var player: Node2D
@export var count := 9
@export var bounds := Rect2(10, 80, 400, 150)

var flies: Array[Dictionary] = []
const COLOURS := ["#ffffff", "#ffe066", "#9fd8ff", "#ffb0d0"]


func _ready() -> void:
	for i in count:
		flies.append({"p": Vector2(randf_range(bounds.position.x, bounds.end.x), randf_range(bounds.position.y, bounds.end.y)),
			"v": Vector2.ZERO, "t": randf() * 10.0, "z": 10.0, "target": Vector2.ZERO, "c": Color(COLOURS.pick_random())})


func _process(dt: float) -> void:
	for b in flies:
		b.t += dt
		if b.target == Vector2.ZERO or b.p.distance_to(b.target) < 8.0 or randf() < dt * 0.3:
			b.target = (b.p + Vector2(randf_range(-90, 90), randf_range(-60, 60))).clamp(bounds.position, bounds.end)
		var a: Vector2 = b.target - b.p
		if player and b.p.distance_to(player.position) < 34.0:
			a = (b.p - player.position) * 5.0
		a = a.normalized()
		b.v = b.v.lerp(Vector2(a.x * 24.0, a.y * 18.0), 1.0 - exp(-2.0 * dt))
		b.p += b.v * dt + Vector2(sin(b.t * 7.0) * 6.0, cos(b.t * 5.0) * 5.0) * dt
		b.z = 12.0 + sin(b.t * 2.6) * 5.0
	queue_redraw()


func _draw() -> void:
	for b in flies:
		var x := roundi(b.p.x)
		var y := roundi(b.p.y - b.z)
		draw_rect(Rect2(x, roundi(b.p.y), 2, 1), Color(0.05, 0.14, 0.08, 0.22))
		if sin(b.t * 24.0) > 0.0:
			draw_rect(Rect2(x - 2, y - 1, 2, 2), b.c)
			draw_rect(Rect2(x + 1, y - 1, 2, 2), b.c)
		else:
			draw_rect(Rect2(x - 1, y - 2, 1, 2), b.c)
			draw_rect(Rect2(x + 1, y - 2, 1, 2), b.c)
		draw_rect(Rect2(x, y - 1, 1, 2), Color("#2a1a10"))

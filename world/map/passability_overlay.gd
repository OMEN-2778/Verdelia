class_name PassabilityOverlay
extends Node2D
## Shows where characters can and cannot walk: every collision shape under `world` in translucent
## red (water, cliffs, trunks, rocks, house walls, hand-blocked cells), cells opened by hand in
## green, doorways in yellow, and the spawn point. Redraw after edits with refresh().

@export var world: MapWorld

const BLOCK := Color(1.0, 0.25, 0.2, 0.38)
const OPEN := Color(0.3, 1.0, 0.45, 0.35)
const DOOR := Color(1.0, 0.85, 0.25, 0.6)


func _ready() -> void:
	z_index = 60


func refresh() -> void:
	queue_redraw()


func _draw() -> void:
	if world == null or world.data == null:
		return
	var cp := float(world.data.cell_px)
	for y in world.data.size.y:
		for x in world.data.size.x:
			if world.data.passage[y * world.data.size.x + x] == MapData.Passage.OPEN:
				draw_rect(Rect2(x * cp, y * cp, cp, cp), OPEN)
	_draw_shapes(world)
	var s := world.data.spawn
	draw_circle(s, 4.0, Color(1, 0.9, 0.3, 0.9))
	draw_arc(s, 6.0, 0, TAU, 16, Color(0.2, 0.15, 0.05, 0.9), 1.0)


func _draw_shapes(n: Node) -> void:
	for c in n.get_children():
		if c is CollisionShape2D and c.shape and not c.disabled:
			var xf: Transform2D = global_transform.affine_inverse() * (c as Node2D).global_transform
			draw_set_transform_matrix(xf)
			var sh: Shape2D = c.shape
			if c.get_parent() is Area2D:
				if sh is RectangleShape2D:
					draw_rect(Rect2(-sh.size / 2.0, sh.size), DOOR)
			elif sh is RectangleShape2D:
				draw_rect(Rect2(-sh.size / 2.0, sh.size), BLOCK)
			elif sh is CircleShape2D:
				draw_circle(Vector2.ZERO, sh.radius, BLOCK)
			elif sh is CapsuleShape2D:
				var h: float = maxf(0.0, sh.height / 2.0 - sh.radius)
				draw_rect(Rect2(-sh.radius, -h, sh.radius * 2.0, h * 2.0), BLOCK)
				draw_circle(Vector2(0, -h), sh.radius, BLOCK)
				draw_circle(Vector2(0, h), sh.radius, BLOCK)
			draw_set_transform_matrix(Transform2D.IDENTITY)
		elif c is CollisionPolygon2D and not c.disabled:
			var xf2: Transform2D = global_transform.affine_inverse() * (c as Node2D).global_transform
			draw_set_transform_matrix(xf2)
			var poly: PackedVector2Array = c.polygon
			if poly.size() >= 3 and not Geometry2D.triangulate_polygon(poly).is_empty():
				draw_colored_polygon(poly, BLOCK)
			draw_set_transform_matrix(Transform2D.IDENTITY)
		_draw_shapes(c)

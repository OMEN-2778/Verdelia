class_name BridgeLayer
extends Node2D
## Wooden planks over every water cell that is marked walkable (MapData.Passage.OPEN): planks run
## across the bridge's direction, with darker rails along its sides and a soft shadow on the water.

@export var world: MapWorld

const WOOD := [Color("#6b4a2b"), Color("#8a6238"), Color("#a67a47"), Color("#c19560")]


func _ready() -> void:
	z_index = -8  # above the water, below the props


func refresh() -> void:
	queue_redraw()


func _draw() -> void:
	if world == null or world.data == null:
		return
	var d := world.data
	var cp := float(d.cell_px)
	for y in d.size.y:
		for x in d.size.x:
			var c := Vector2i(x, y)
			if not _deck(c):
				continue
			var horizontal := int(_deck(c + Vector2i(1, 0))) + int(_deck(c - Vector2i(1, 0))) >= int(_deck(c + Vector2i(0, 1))) + int(_deck(c - Vector2i(0, 1)))
			var r := Rect2(Vector2(c) * cp, Vector2(cp, cp))
			draw_rect(Rect2(r.position + Vector2(1, 2), r.size), Color(0.02, 0.08, 0.12, 0.35))  # shadow
			for k in int(cp):
				var shade: Color = WOOD[2 if (k + x * 3 + y * 5) % 4 != 0 else 1]
				if k % 4 == 3:
					shade = WOOD[0]  # gap between planks
				if horizontal:
					draw_rect(Rect2(r.position + Vector2(k, 0), Vector2(1, cp)), shade)
				else:
					draw_rect(Rect2(r.position + Vector2(0, k), Vector2(cp, 1)), shade)
			# rails where the deck ends sideways
			if horizontal:
				if not _deck(c - Vector2i(0, 1)):
					draw_rect(Rect2(r.position, Vector2(cp, 1)), WOOD[3])
				if not _deck(c + Vector2i(0, 1)):
					draw_rect(Rect2(r.position + Vector2(0, cp - 1), Vector2(cp, 1)), WOOD[0])
			else:
				if not _deck(c - Vector2i(1, 0)):
					draw_rect(Rect2(r.position, Vector2(1, cp)), WOOD[3])
				if not _deck(c + Vector2i(1, 0)):
					draw_rect(Rect2(r.position + Vector2(cp - 1, 0), Vector2(1, cp)), WOOD[0])


func _deck(c: Vector2i) -> bool:
	var d := world.data
	return d.has_cell(c) and d.water_at(c) and d.passage_at(c) == MapData.Passage.OPEN

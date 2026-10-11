extends Node2D
## Living grass: every tuft is redrawn each frame, bent by the wind and pushed aside by the player.

@export var player: Node2D

var tufts: Array = []
var colours: Array[Color] = []


func setup(data: Array, palette: Array) -> void:
	tufts = data
	colours.clear()
	for hex: String in palette:
		colours.append(Color(hex))


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	var t := Wind.now()
	var sways := PackedFloat32Array()
	var gusts := PackedFloat32Array()
	sways.resize(tufts.size())
	gusts.resize(tufts.size())
	for i in tufts.size():
		var tf: Dictionary = tufts[i]
		var w := Wind.at(tf.x, tf.y, t)
		var s := w.x
		if player:
			var dx: float = tf.x - player.position.x
			var dy: float = (tf.y - player.position.y) * 1.6
			var d2 := dx * dx + dy * dy
			if d2 < 140.0:
				s += (1.0 if dx >= 0.0 else -1.0) * 3.2 * (1.0 - sqrt(d2) / 12.0)
		sways[i] = s
		gusts[i] = w.y
	# one pass per colour, like the original, so overlapping blades layer the same way
	for pass_index in 3:
		for i in tufts.size():
			var tf: Dictionary = tufts[i]
			var level_shift := 1 if tf.get("crop", 0) else 0
			var colour := colours[pass_index + level_shift]
			var n: int = tf.n
			var h: int = tf.h
			for b in n:
				var bx: int = int(tf.x) + b * 2 - n + 1
				var hh := h - (b & 1)
				for k in hh:
					var lvl := 2 if k == hh - 1 else (1 if k >= hh / 2.0 else 0)
					if lvl != pass_index:
						continue
					var off := roundi(sways[i] * pow(float(k) / hh, 1.4) * hh / 3.5)
					draw_rect(Rect2(bx + off, int(tf.y) - k, 1, 1), colour)
	for i in tufts.size():  # gust fronts catch the light on the tips; flowers ride on top
		var tf: Dictionary = tufts[i]
		if gusts[i] > 0.3:
			draw_rect(Rect2(int(tf.x) + roundi(sways[i] * tf.h / 3.5), int(tf.y) - tf.h + 1, 1, 1), colours[3])
		if tf.fl == null:
			continue
		var fl := Color(tf.fl)
		var fx: int = int(tf.x) + roundi(sways[i] * tf.h / 3.2)
		var fy: int = int(tf.y) - tf.h - 1
		draw_rect(Rect2(fx - 1, fy, 3, 1), fl)
		draw_rect(Rect2(fx, fy - 1, 1, 3), fl)
		draw_rect(Rect2(fx, fy, 1, 1), Color("#ffffff") if tf.fl == "#ffe066" else Color("#ffe066"))

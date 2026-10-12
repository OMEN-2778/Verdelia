class_name DayClockHud
extends Node2D
## A small time readout in the top-right corner: the sun (by day) or moon (by night) travels along
## an arc, with the time in 3x5 pixel digits below. Drawn by DayNight on its own canvas layer.

const DIGITS := {
	"0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
	"2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
	"4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
	"6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
	"8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
	":": ["0", "1", "0", "1", "0"],
}
const INK := Color(1.0, 0.98, 0.92)
const SHADE := Color(0.1, 0.12, 0.18, 0.55)


func _draw() -> void:
	var vp := get_viewport_rect().size
	var origin := Vector2(vp.x - 30, 4)
	var is_day := DayNight.is_day()
	var arc := DayNight.sky_arc()
	# the arc the sun or moon travels along
	draw_rect(Rect2(origin + Vector2(-2, -1), Vector2(30, 20)), SHADE)
	for i in 13:
		var a := PI * float(i) / 12.0
		var p := origin + Vector2(13, 11) + Vector2(-cos(a) * 11.0, -sin(a) * 7.0)
		draw_rect(Rect2(p.round(), Vector2.ONE), Color(INK, 0.35))
	var b := PI * arc
	var c := (origin + Vector2(13, 11) + Vector2(-cos(b) * 11.0, -sin(b) * 7.0)).round()
	if is_day:
		draw_rect(Rect2(c - Vector2(1, 1), Vector2(3, 3)), Color(1.0, 0.86, 0.35))
		for d in [Vector2(-2, 0), Vector2(2, 0), Vector2(0, -2), Vector2(0, 2)]:
			draw_rect(Rect2(c + d, Vector2.ONE), Color(1.0, 0.75, 0.3, 0.8))
	else:
		draw_rect(Rect2(c - Vector2(1, 1), Vector2(3, 3)), Color(0.86, 0.9, 1.0))
		draw_rect(Rect2(c + Vector2(0, -1), Vector2(2, 2)), SHADE)  # crescent
	_text(DayNight.clock_text(), origin + Vector2(3, 13))


func _text(s: String, at: Vector2) -> void:
	var x := at.x
	for ch in s:
		var g: Array = DIGITS.get(ch, [])
		for row in g.size():
			var line: String = g[row]
			for col in line.length():
				if line[col] == "1":
					draw_rect(Rect2(Vector2(x + col, at.y + row), Vector2.ONE), INK)
		x += (g[0] as String).length() + 1 if g.size() > 0 else 4

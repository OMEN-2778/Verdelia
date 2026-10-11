class_name Wind
## Shared wind field (ported from Stardust Vale): a gentle base sway plus gust fronts that roll
## across the valley. Returns Vector2(sway, gust); gust is 0..1.


static func at(x: float, y: float, t: float) -> Vector2:
	var base := sin(t * 1.7 + x * 0.045 + y * 0.02) * 0.6
	var g := sin((x * 0.9 + y * 0.35) * 0.011 - t * 1.25)
	var gust := pow((g - 0.55) / 0.45, 2.0) if g > 0.55 else 0.0
	return Vector2(base + gust * 2.6, gust)


static func now() -> float:
	return Time.get_ticks_msec() / 1000.0

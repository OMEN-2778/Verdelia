class_name Wind
## Shared wind field (ported from Stardust Vale): a gentle base sway plus gust fronts that roll
## across the valley. Returns Vector2(sway, gust); gust is 0..1.


static func at(x: float, y: float, t: float) -> Vector2:
	var base := sin(t * 1.7 + x * 0.045 + y * 0.02) * 0.6
	var g := sin((x * 0.9 + y * 0.35) * 0.011 - t * 1.25)
	var gust := pow((g - 0.55) / 0.45, 2.0) if g > 0.55 else 0.0
	return Vector2(base + gust * 2.6, gust)


## Game time in seconds: advances with the game (also when recording a movie at a fixed frame rate
## or when frames are slow), not with the wall clock, so swaying never speeds up or stutters.
static func now() -> float:
	var tps := float(Engine.physics_ticks_per_second)
	return (Engine.get_physics_frames() + Engine.get_physics_interpolation_fraction()) / tps

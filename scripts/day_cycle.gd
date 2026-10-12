extends CanvasModulate
## Runs a compressed day for the demo: tints the world from `sky` and fades every light in the
## "night_lights" group in as the world gets darker. Lights may set the metas "day_energy" and
## "night_energy" to override the defaults.

@export var cycle_seconds := 24.0
@export_range(0.0, 1.0) var start_time := 0.3  ## 0 = midnight, 0.5 = noon
@export var sky: Gradient

var time_of_day := 0.0


func _ready() -> void:
	time_of_day = start_time


func _process(delta: float) -> void:
	time_of_day = fmod(time_of_day + delta / cycle_seconds, 1.0)
	color = sky.sample(time_of_day)
	var darkness := clampf((0.92 - color.get_luminance()) / 0.45, 0.0, 1.0)
	var now := Wind.now()
	for light: PointLight2D in get_tree().get_nodes_in_group("night_lights"):
		var day: float = light.get_meta("day_energy", 0.25)
		var night: float = light.get_meta("night_energy", 1.3)
		var flicker := 1.0 + 0.06 * sin(now * 3.1 + light.position.x)
		light.energy = lerpf(day, night, darkness) * flicker

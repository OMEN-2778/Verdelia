class_name RoomLights
extends Node
## Lights for the rooms of a house at night: the room the player is in has its lights on, the
## others are dark. The map lists its rooms (MapData.rooms: where you stand in each, and what its
## light covers); as the player walks from one room to the next, the light there comes up and
## the one behind goes out. The grade shader (grade.gdshader, "rooms") does the lighting from
## the rects this hands it each frame; the lamps of the furniture in a dark room are switched off.
## Maps without rooms are left alone.

const FADE := 3.0  ## how fast a room's light comes on or goes off (per second)

var world: MapWorld
var player: Node2D
var grade: ShaderMaterial

var _levels: Array[float] = []
var _current := -1
var _buildings: Array = []  # [WorldBuilding, room index]


func _ready() -> void:
	# the rects go to the shader just before each frame is drawn, after the camera has moved, so
	# the light stays on its room while the view scrolls
	RenderingServer.frame_pre_draw.connect(_apply)


func _exit_tree() -> void:
	RenderingServer.frame_pre_draw.disconnect(_apply)


## Call after a map is loaded: the room you are in starts lit, the others dark.
func reset() -> void:
	var rooms := world.data.rooms
	_levels.clear()
	_levels.resize(rooms.size())
	_levels.fill(0.0)
	_current = room_at(player.global_position) if player else -1
	if _current >= 0:
		_levels[_current] = 1.0
	_buildings.clear()
	for n in world.props.get_children():
		if n is WorldBuilding:
			var i := room_at((n as Node2D).global_position)
			if i >= 0:
				_buildings.append([n, i])
	_apply()


## The room whose floor contains `p`, or -1.
func room_at(p: Vector2) -> int:
	var rooms := world.data.rooms
	for i in rooms.size():
		for q: Array in rooms[i].get("area", []):
			if Rect2(q[0], q[1], q[2], q[3]).has_point(p):
				return i
	return -1


func _process(delta: float) -> void:
	if world == null or world.data == null or player == null:
		return
	if _levels.size() != world.data.rooms.size():  # another map was loaded
		reset()
	var here := room_at(player.global_position)
	if here >= 0:
		_current = here  # (between rooms, in a doorway, the last one stays lit)
	for i in _levels.size():
		_levels[i] = move_toward(_levels[i], 1.0 if i == _current else 0.0, delta * FADE)


func _apply() -> void:
	if grade == null or world == null or world.data == null or _levels.size() != world.data.rooms.size():
		return
	var rects := PackedVector4Array()
	var levels := PackedFloat32Array()
	var vp := get_viewport()
	var xf := vp.get_canvas_transform()
	var size := vp.get_visible_rect().size
	var rooms := world.data.rooms
	for i in rooms.size():
		for q: Array in rooms[i].get("light", []):
			if rects.size() >= 8:
				break
			var a: Vector2 = xf * Vector2(q[0], q[1]) / size
			var b: Vector2 = xf * Vector2(q[0] + q[2], q[1] + q[3]) / size
			rects.append(Vector4(a.x, a.y, b.x, b.y))
			levels.append(_levels[i])
	var n := rects.size()
	rects.resize(8)
	levels.resize(8)
	grade.set_shader_parameter("room_count", n)
	grade.set_shader_parameter("room_rect", rects)
	grade.set_shader_parameter("room_level", levels)
	for e: Array in _buildings:
		if is_instance_valid(e[0]):
			e[0].lamps_on = _levels[e[1]] > 0.5

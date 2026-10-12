extends Node
## Standalone map editor: paint ground, water, plants and cliffs with brushes of different shapes,
## place buildings, erase, undo, save and open maps, see where characters can walk, and try the map
## on foot.
##
## Mouse: left paints, right erases (or tick "橡皮擦"), middle button or Space + drag pans, the
## wheel zooms. Keys: Ctrl+Z undo, Ctrl+Y redo, E eraser, [ ] brush size, Esc leaves play mode.

const LAYERS := ["地面", "水体", "植被", "岩壁", "通行", "建筑"]
enum Layer { GROUND, WATER, PLANTS, CLIFF, PASSAGE, BUILDING }

const TOOLS := {
	Layer.GROUND: [["草地", 0], ["土路", 1], ["沙地", 2], ["耕地", 3], ["湿耕地", 4], ["砖路", 5]],
	Layer.WATER: [["水", 1]],
	Layer.PLANTS: [
		["混合树林", "mix_forest"], ["阔叶树", "tree:oak"], ["白桦", "tree:birch"], ["松树", "tree:pine"],
		["花树", "tree:blossom"], ["小树苗", "tree:sapling"], ["远景树", "tree:oak_far"],
		["绿灌木", "bush:green"], ["开花灌木", "bush:flower"], ["浆果灌木", "bush:berry"],
		["粉花灌木", "bush:pink"], ["紫花灌木", "bush:violet"], ["石头", "rock:"], ["野花", "flower:"],
		["灌木丛", "mix_shrubs"],
	],
	Layer.CLIFF: [["画岩壁", "draw"], ["土坡", 0], ["石阶", 1], ["草坡", 2]],
	Layer.PASSAGE: [["阻挡", MapData.Passage.BLOCKED], ["木桥", MapData.Passage.OPEN], ["出生点", "spawn"]],
	Layer.BUILDING: [],  # filled from the building library in select_layer()
}
const SHAPES := [["圆形", "circle"], ["方形", "square"], ["菱形", "diamond"], ["横椭圆", "hellipse"], ["竖椭圆", "vellipse"], ["喷枪", "spray"], ["直线", "line"], ["矩形", "rect"], ["填充", "fill"]]
const LAYER_TINT := [Color(0.95, 0.8, 0.4), Color(0.4, 0.75, 1.0), Color(0.5, 1.0, 0.5), Color(0.9, 0.7, 0.5), Color(1.0, 0.5, 0.45), Color(1.0, 0.85, 0.6)]
const MAX_UNDO := 60

var world: MapWorld
var overlay: PassabilityOverlay
var cursor: Node2D
var camera: Camera2D
var player: CharacterBody2D

var layer := Layer.GROUND
var tool: Variant = 1
var shape := "circle"
var brush_size := 3
var density := 0.5
var cliff_face := 36
var eraser := false
var map_path := ""

var _undo: Array = []
var _redo: Array = []
var _painting := false
var _erasing := false
var _panning := false
var _press_world := Vector2.ZERO
var _last_cell := Vector2i(-9999, -9999)
var _stroke_cells := {}  # cells already handled in this stroke (plants)
var _stroke_area := Rect2()
var _cliff_points: Array = []
var _rng := RandomNumberGenerator.new()

# ui
var _ui: CanvasLayer
var _tool_box: VBoxContainer
var _status: Label
var _hint: Label
var _eraser_btn: CheckButton
var _size_slider: HSlider
var _density_row: Control
var _face_row: Control
var _overlay_btn: CheckButton
var _play_btn: Button
var _layer_buttons: Array = []
var _new_dialog: ConfirmationDialog
var _new_w: SpinBox
var _new_h: SpinBox
var _open_dialog: FileDialog
var _save_dialog: FileDialog


func _ready() -> void:
	var win := get_window()
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	win.title = "Verdelia 地图编辑器"
	_rng.randomize()
	world = MapWorld.new()
	world.name = "World"
	add_child(world)
	overlay = PassabilityOverlay.new()
	overlay.world = world
	overlay.visible = false
	add_child(overlay)
	cursor = Node2D.new()
	cursor.z_index = 80
	cursor.draw.connect(_draw_cursor)
	add_child(cursor)
	camera = Camera2D.new()
	camera.zoom = Vector2(2, 2)
	add_child(camera)
	camera.make_current()
	_build_ui()
	new_map(Vector2i(120, 68))


# ================================================================== map files

func new_map(cells: Vector2i) -> void:
	var d := MapData.create(cells)
	world.load_data(d)
	map_path = ""
	_undo.clear()
	_redo.clear()
	camera.position = d.size_px() * 0.5
	_refresh_status()
	overlay.refresh()


## A fresh random map (MapGenerator) to start from; undo brings back the previous map.
func random_map(seed: int) -> void:
	_snapshot()
	var d := MapGenerator.generate(seed, world.data.size if world.data else Vector2i(140, 80))
	world.load_data(d)
	map_path = ""
	camera.position = d.size_px() * 0.5
	overlay.refresh()
	_flash("随机地图，种子 %d" % seed)


func open_map(path: String) -> bool:
	var d := MapData.load_file(path)
	if d == null:
		_flash("打不开：" + path)
		return false
	world.load_data(d)
	map_path = path
	_undo.clear()
	_redo.clear()
	camera.position = d.size_px() * 0.5
	_flash("已打开 " + path.get_file())
	overlay.refresh()
	return true


func save_map(path: String) -> bool:
	world.data.name = path.get_file().trim_suffix(".json").trim_suffix(".map")
	var err := world.data.save(path)
	if err != OK:
		_flash("保存失败（%d）" % err)
		return false
	map_path = path
	_flash("已保存到 " + path)
	return true


func undo() -> void:
	if _undo.is_empty():
		return
	_redo.append(world.data.copy())
	world.load_data(_undo.pop_back())
	overlay.refresh()
	_refresh_status()


func redo() -> void:
	if _redo.is_empty():
		return
	_undo.append(world.data.copy())
	world.load_data(_redo.pop_back())
	overlay.refresh()
	_refresh_status()


func _snapshot() -> void:
	_undo.append(world.data.copy())
	if _undo.size() > MAX_UNDO:
		_undo.pop_front()
	_redo.clear()


# ================================================================== input

func _unhandled_input(event: InputEvent) -> void:
	if player:
		if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
			stop_play()
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			_zoom(1)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			_zoom(-1)
		elif mb.button_index == MOUSE_BUTTON_MIDDLE or (mb.button_index == MOUSE_BUTTON_LEFT and Input.is_key_pressed(KEY_SPACE)):
			_panning = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_LEFT or mb.button_index == MOUSE_BUTTON_RIGHT:
			if mb.pressed:
				begin_stroke(_mouse_world(), eraser or mb.button_index == MOUSE_BUTTON_RIGHT)
			elif _painting:
				end_stroke(_mouse_world())
	elif event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _panning:
			camera.position -= mm.relative / camera.zoom
		elif _painting:
			continue_stroke(_mouse_world())
		cursor.queue_redraw()
		_refresh_status()
	elif event is InputEventKey and event.pressed and not event.echo:
		var k := event as InputEventKey
		if k.ctrl_pressed and k.keycode == KEY_Z:
			if k.shift_pressed:
				redo()
			else:
				undo()
		elif k.ctrl_pressed and k.keycode == KEY_Y:
			redo()
		elif k.ctrl_pressed and k.keycode == KEY_S:
			_on_save(false)
		elif k.keycode == KEY_E:
			_eraser_btn.button_pressed = not _eraser_btn.button_pressed
		elif k.keycode == KEY_BRACKETLEFT:
			_size_slider.value -= 1
		elif k.keycode == KEY_BRACKETRIGHT:
			_size_slider.value += 1


func _process(delta: float) -> void:
	if player:
		camera.position = camera.position.lerp(player.global_position, 1.0 - exp(-6.0 * delta))
		return
	var pan := Vector2.ZERO
	if Input.is_key_pressed(KEY_LEFT): pan.x -= 1
	if Input.is_key_pressed(KEY_RIGHT): pan.x += 1
	if Input.is_key_pressed(KEY_UP): pan.y -= 1
	if Input.is_key_pressed(KEY_DOWN): pan.y += 1
	if pan != Vector2.ZERO:
		camera.position += pan * 300.0 * delta / camera.zoom.x
		cursor.queue_redraw()


func _zoom(dir: int) -> void:
	var z := clampi(int(camera.zoom.x) + dir, 1, 6)
	var before := _mouse_world()
	camera.zoom = Vector2(z, z)
	camera.position += before - _mouse_world()
	cursor.queue_redraw()


func _mouse_world() -> Vector2:
	return world.get_global_mouse_position()


func _cell(p: Vector2) -> Vector2i:
	var cp := float(world.data.cell_px)
	return Vector2i(floori(p.x / cp), floori(p.y / cp))


# ================================================================== strokes (also used by tests)

func begin_stroke(p: Vector2, erase: bool) -> void:
	_snapshot()
	_painting = true
	_erasing = erase
	_press_world = p
	_stroke_cells.clear()
	_stroke_area = Rect2(p, Vector2.ZERO)
	_last_cell = _cell(p)
	if layer == Layer.CLIFF:
		_cliff_points = [p]
		return
	if layer == Layer.BUILDING:
		_building_click(p.round(), erase)
		return
	if shape in ["line", "rect"]:
		return
	if shape == "fill":
		_apply(_flood(_cell(p)), p)
		return
	if layer == Layer.PASSAGE and str(tool) == "spawn" and not erase:
		world.data.spawn = p
		return
	_apply(_stamp(_cell(p)), p)


func continue_stroke(p: Vector2) -> void:
	_stroke_area = _stroke_area.expand(p)
	if layer == Layer.BUILDING:
		return
	if layer == Layer.CLIFF:
		if str(tool) == "draw" and not _erasing and (_cliff_points.is_empty() or p.distance_to(_cliff_points[-1]) > 6.0):
			_cliff_points.append(p)
		return
	if shape in ["line", "rect", "fill"]:
		return
	var c := _cell(p)
	if c == _last_cell:
		return
	# fill the gap between the last dab and this one so fast strokes stay continuous
	var steps := maxi(absi(c.x - _last_cell.x), absi(c.y - _last_cell.y))
	for s in range(1, steps + 1):
		var cc := Vector2i(Vector2(_last_cell).lerp(Vector2(c), float(s) / steps).round())
		_apply(_stamp(cc), (Vector2(cc) + Vector2(0.5, 0.5)) * world.data.cell_px)
	_last_cell = c


func end_stroke(p: Vector2) -> void:
	_painting = false
	_stroke_area = _stroke_area.expand(p)
	if layer == Layer.CLIFF:
		_finish_cliff(p)
	elif layer == Layer.BUILDING:
		pass
	elif shape == "line":
		_apply(_line_cells(_cell(_press_world), _cell(p)), p)
	elif shape == "rect":
		_apply(_rect_cells(_cell(_press_world), _cell(p)), p)
	world.end_stroke(_stroke_area.grow(brush_size * world.data.cell_px))
	overlay.refresh()
	cursor.queue_redraw()
	_refresh_status()


## One call for scripted use: a stroke through `points` (world px).
func stroke(points: Array, erase := false) -> void:
	begin_stroke(points[0], erase)
	for k in range(1, points.size()):
		continue_stroke(points[k])
	end_stroke(points[-1])


func _apply(cells: Array, p: Vector2) -> void:
	if cells.is_empty():
		return
	var cp := float(world.data.cell_px)
	for c in cells:
		_stroke_area = _stroke_area.expand(Vector2(c) * cp)
	match layer:
		Layer.GROUND:
			world.paint_ground(cells, MapData.Ground.GRASS if _erasing else int(tool))
		Layer.WATER:
			world.paint_water(cells, not _erasing)
		Layer.PASSAGE:
			if str(tool) == "spawn":
				return
			world.paint_passage(cells, MapData.Passage.AUTO if _erasing else int(tool))
		Layer.PLANTS:
			if _erasing:
				world.remove_objects_in(cells, false)
			else:
				_scatter(cells, p)


# ------------------------------------------------------------------ brush shapes

func _stamp(center: Vector2i) -> Array:
	var r := brush_size - 1
	var out: Array = []
	for dy in range(-r - 1, r + 2):
		for dx in range(-r - 1, r + 2):
			if _in_shape(dx, dy, r):
				out.append(center + Vector2i(dx, dy))
	if shape == "spray":
		var thin: Array = []
		for c in out:
			if _rng.randf() < 0.18 + density * 0.4:
				thin.append(c)
		return thin
	return out


func _in_shape(dx: int, dy: int, r: int) -> bool:
	var fr := float(r) + 0.5
	match shape:
		"square":
			return absi(dx) <= r and absi(dy) <= r
		"diamond":
			return absi(dx) + absi(dy) <= r
		"hellipse":
			return pow(dx / (fr * 1.7), 2.0) + pow(dy / (fr * 0.75), 2.0) <= 1.0
		"vellipse":
			return pow(dx / (fr * 0.75), 2.0) + pow(dy / (fr * 1.7), 2.0) <= 1.0
		_:
			return dx * dx + dy * dy <= fr * fr


func _line_cells(a: Vector2i, b: Vector2i) -> Array:
	var seen := {}
	var steps := maxi(1, maxi(absi(b.x - a.x), absi(b.y - a.y)))
	var keep := shape
	shape = "circle"
	for s in steps + 1:
		var c := Vector2i(Vector2(a).lerp(Vector2(b), float(s) / steps).round())
		for cc in _stamp(c):
			seen[cc] = true
	shape = keep
	return seen.keys()


func _rect_cells(a: Vector2i, b: Vector2i) -> Array:
	var out: Array = []
	for y in range(mini(a.y, b.y), maxi(a.y, b.y) + 1):
		for x in range(mini(a.x, b.x), maxi(a.x, b.x) + 1):
			out.append(Vector2i(x, y))
	return out


## Every cell connected to `start` that looks the same on the current layer.
func _flood(start: Vector2i) -> Array:
	var d := world.data
	if not d.has_cell(start):
		return []
	var key := func(c: Vector2i) -> int:
		match layer:
			Layer.WATER:
				return 1 if d.water_at(c) else 0
			Layer.PASSAGE:
				return d.passage_at(c)
			_:
				return d.ground_at(c) + (10 if d.water_at(c) else 0)
	var want: int = key.call(start)
	var out: Array = []
	var seen := {start: true}
	var queue: Array = [start]
	while not queue.is_empty() and out.size() < 40000:
		var c: Vector2i = queue.pop_back()
		out.append(c)
		for n in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var nc: Vector2i = c + n
			if d.has_cell(nc) and not seen.has(nc) and key.call(nc) == want:
				seen[nc] = true
				queue.append(nc)
	return out


# ------------------------------------------------------------------ plants

func _scatter(cells: Array, p: Vector2) -> void:
	var cp := float(world.data.cell_px)
	var single := brush_size == 1 and shape in ["circle", "square", "diamond"] and _stroke_cells.is_empty()
	if single:
		_stroke_cells[_cell(p)] = true
		_place(_pick_item(), p.round())
		return
	for c in cells:
		if _stroke_cells.has(c):
			continue
		_stroke_cells[c] = true
		var item := _pick_item()
		var chance := density * (0.11 if item.begins_with("tree") else (0.14 if item.begins_with("bush") or item.begins_with("rock") else 0.3))
		if _rng.randf() < chance:
			var pos := (Vector2(c) + Vector2(_rng.randf(), _rng.randf())) * cp
			_place(item, pos.round())


func _pick_item() -> String:
	var t := str(tool)
	match t:
		"mix_forest":
			var r := _rng.randf()
			return "tree:oak" if r < 0.34 else ("tree:birch" if r < 0.5 else ("tree:pine" if r < 0.68 else ("tree:blossom" if r < 0.74 else ("tree:sapling" if r < 0.84 else "bush:green"))))
		"mix_shrubs":
			var r2 := _rng.randf()
			return "bush:green" if r2 < 0.4 else ("bush:flower" if r2 < 0.6 else ("bush:berry" if r2 < 0.72 else ("rock:" if r2 < 0.85 else "flower:")))
	return t


func _place(item: String, pos: Vector2) -> void:
	var d := world.data
	var c := _cell(pos)
	if not d.has_cell(c) or d.water_at(c) or world.cliff_at(pos) >= 0:
		return
	var parts := item.split(":")
	var kind := parts[0]
	var spacing: float = {"tree": 15.0, "bush": 10.0, "rock": 9.0, "flower": 5.0}.get(kind, 8.0)
	if world.object_near(pos, spacing):
		return
	var id := parts[1] if parts.size() > 1 else ""
	if kind == "flower":
		id = MapWorld.FLOWERS[_rng.randi() % MapWorld.FLOWERS.size()]
	world.add_object({"kind": kind, "id": id, "x": pos.x, "y": pos.y})


# ------------------------------------------------------------------ buildings

## Left click places the selected building with its doorstep at `p`; right click (or the
## eraser) removes the building under the cursor.
func _building_click(p: Vector2, erase: bool) -> void:
	if erase:
		var i := world.building_at(p)
		if i >= 0:
			var o: Dictionary = world.data.objects[i]
			_stroke_area = WorldBuilding.sprite_rect_of(o.id)
			_stroke_area.position += Vector2(o.x, o.y)
			world.remove_object(i)
		return
	var id := str(tool)
	if not can_place_building(id, p):
		_flash("这里放不下：建筑不能压在水、岩壁、别的建筑上，也不能出地图")
		return
	var r := WorldBuilding.footprint_of(id)
	r.position += p
	# clear plants and rocks off the ground it stands on and its doorstep
	var cp := float(world.data.cell_px)
	var cells: Array = []
	for y in range(floori(r.position.y / cp), ceili((r.end.y + 6.0) / cp)):
		for x in range(floori(r.position.x / cp), ceili(r.end.x / cp)):
			cells.append(Vector2i(x, y))
	world.remove_objects_in(cells, false)
	world.add_object({"kind": "building", "id": id, "x": p.x, "y": p.y})
	_stroke_area = WorldBuilding.sprite_rect_of(id)
	_stroke_area.position += p


func can_place_building(id: String, p: Vector2) -> bool:
	var d := world.data
	var r := WorldBuilding.footprint_of(id)
	r.position += p
	if r.size == Vector2.ZERO:
		return false
	var cp := float(d.cell_px)
	for y in range(floori(r.position.y / cp), ceili((r.end.y + 4.0) / cp)):
		for x in range(floori(r.position.x / cp), ceili(r.end.x / cp)):
			var c := Vector2i(x, y)
			if not d.has_cell(c) or d.water_at(c):
				return false
			if world.cliff_at((Vector2(c) + Vector2(0.5, 0.5)) * cp) >= 0:
				return false
	for o in d.objects:
		if o.kind == "building" and MapWorld.building_rect(o).grow(2.0).intersects(r):
			return false
	return true


# ------------------------------------------------------------------ cliffs

func _finish_cliff(p: Vector2) -> void:
	var t := str(tool)
	if _erasing:
		var i := world.cliff_at(p)
		if i >= 0 and not world.remove_ramp(i, p.x):
			world.remove_cliff(i)
		return
	if t == "draw":
		var pts := _cliff_points.duplicate()
		pts.append(p)
		pts.sort_custom(func(a, b): return a.x < b.x)
		var flat: Array = []
		var last_x := -INF
		for q in pts:
			if q.x - last_x >= 20.0 or q == pts[-1]:
				flat.append_array([roundf(q.x), roundf(q.y)])
				last_x = q.x
		if flat.size() >= 4 and flat[-2] - flat[0] >= 32.0:
			world.add_cliff({"points": flat, "face": cliff_face, "seed": _rng.randi() % 1000, "ramps": []})
		else:
			_flash("岩壁太短了：按住左键横着拖出一段")
		return
	var ci := world.cliff_at(p)
	if ci < 0:
		_flash("坡道要点在岩壁上")
		return
	world.add_ramp(ci, roundf(p.x), clampi(brush_size * 3 + 6, 8, 24), int(tool))


# ================================================================== play mode

func start_play() -> void:
	if player:
		return
	player = CharacterBody2D.new()
	player.set_script(preload("res://world/demo/demo_player.gd"))
	var shadow := Sprite2D.new()
	shadow.name = "Shadow"
	shadow.texture = preload("res://art/library/fx/shadow.png")
	player.add_child(shadow)
	var body := Sprite2D.new()
	body.name = "Body"
	body.texture = preload("res://art/library/props/mage.png")
	body.hframes = 4
	body.offset = Vector2(0, -10)
	player.add_child(body)
	player.set("autopilot", false)
	player.set("speed", 60.0)
	var d := world.data
	player.position = d.spawn if d.spawn.x >= 0 else d.size_px() * 0.5
	world.props.add_child(player)
	world.grass.player = player
	camera.zoom = Vector2(3, 3)
	overlay.visible = false
	cursor.visible = false
	_play_btn.text = "■ 结束试玩（Esc）"
	_hint.text = "试玩中：WASD 或方向键移动，Esc 回到编辑"


func stop_play() -> void:
	if player == null:
		return
	world.grass.player = null
	player.queue_free()
	player = null
	overlay.visible = _overlay_btn.button_pressed
	cursor.visible = true
	_play_btn.text = "▶ 试玩"
	_refresh_hint()


# ================================================================== cursor

func _draw_cursor() -> void:
	if player:
		return
	var p := _mouse_world()
	var cp := float(world.data.cell_px)
	var col: Color = Color(1, 0.35, 0.3) if (eraser or Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)) else LAYER_TINT[layer]
	cursor.draw_set_transform(Vector2.ZERO)
	if layer == Layer.BUILDING:
		_draw_building_cursor(p.round(), col)
		return
	if layer == Layer.CLIFF:
		if _painting and str(tool) == "draw" and not _erasing:
			var pts := PackedVector2Array(_cliff_points)
			pts.append(p)
			if pts.size() >= 2:
				cursor.draw_polyline(pts, col, 2.0 / camera.zoom.x)
		cursor.draw_circle(p, 3.0, Color(col, 0.7))
		return
	var cells: Array
	if _painting and shape == "line":
		cells = _line_cells(_cell(_press_world), _cell(p))
	elif _painting and shape == "rect":
		cells = _rect_cells(_cell(_press_world), _cell(p))
	elif shape == "fill":
		cells = [_cell(p)]
	else:
		var keep := shape
		if shape == "spray":
			shape = "circle"
		cells = _stamp(_cell(p))
		shape = keep
	for c in cells:
		cursor.draw_rect(Rect2(Vector2(c) * cp, Vector2(cp, cp)), Color(col, 0.22))
	var w := 1.0 / camera.zoom.x
	for c in cells:
		var r := Rect2(Vector2(c) * cp, Vector2(cp, cp))
		for side in [[Vector2i(0, -1), r.position, Vector2(r.end.x, r.position.y)], [Vector2i(0, 1), Vector2(r.position.x, r.end.y), r.end], [Vector2i(-1, 0), r.position, Vector2(r.position.x, r.end.y)], [Vector2i(1, 0), Vector2(r.end.x, r.position.y), r.end]]:
			if not cells.has(c + side[0]):
				cursor.draw_line(side[1], side[2], col, w * 2.0)


func _draw_building_cursor(p: Vector2, col: Color) -> void:
	var w := 1.0 / camera.zoom.x
	if eraser or Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		var i := world.building_at(p)
		if i >= 0:
			var o: Dictionary = world.data.objects[i]
			var r := WorldBuilding.sprite_rect_of(o.id)
			r.position += Vector2(o.x, o.y)
			cursor.draw_rect(r, Color(col, 0.25))
			cursor.draw_rect(r, col, false, w * 2.0)
		cursor.draw_circle(p, 3.0, Color(col, 0.7))
		return
	var id := str(tool)
	var e := FloraLibrary.building(id)
	if e.is_empty():
		return
	var ok := can_place_building(id, p)
	var tint := Color(1, 1, 1, 0.6) if ok else Color(1, 0.4, 0.35, 0.5)
	cursor.draw_texture(FloraLibrary.texture(e.file), p - Vector2(e.anchor[0], e.anchor[1]), tint)
	var fp := WorldBuilding.footprint_of(id)
	fp.position += p
	cursor.draw_rect(fp, Color(col if ok else Color(1, 0.35, 0.3), 0.9), false, w * 2.0)
	if e.get("door") != null:
		cursor.draw_circle(p + Vector2(e.door[0], 3.0), 2.0, Color(1.0, 0.85, 0.25, 0.9))


# ================================================================== ui

func _build_ui() -> void:
	_ui = CanvasLayer.new()
	_ui.layer = 10
	add_child(_ui)
	var theme := Theme.new()
	theme.default_font_size = 14
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = theme
	_ui.add_child(root)

	# top bar
	var top := PanelContainer.new()
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	root.add_child(top)
	var bar := HBoxContainer.new()
	bar.add_theme_constant_override("separation", 6)
	top.add_child(bar)
	_button(bar, "新建", func(): _new_dialog.popup_centered())
	_button(bar, "随机生成", func(): random_map(randi() % 100000 + 1))
	_button(bar, "打开", func(): _open_dialog.popup_centered_ratio(0.7))
	_button(bar, "保存", func(): _on_save(false))
	_button(bar, "另存为", func(): _on_save(true))
	bar.add_child(VSeparator.new())
	_button(bar, "撤销", undo)
	_button(bar, "重做", redo)
	bar.add_child(VSeparator.new())
	_overlay_btn = CheckButton.new()
	_overlay_btn.text = "显示通行范围"
	_overlay_btn.toggled.connect(_on_overlay_toggled)
	bar.add_child(_overlay_btn)
	_play_btn = _button(bar, "▶ 试玩", func(): stop_play() if player else start_play())
	_status = Label.new()
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	bar.add_child(_status)

	# side panel
	var side := PanelContainer.new()
	var solid := StyleBoxFlat.new()
	solid.bg_color = Color(0.13, 0.15, 0.14)
	solid.content_margin_left = 8
	solid.content_margin_right = 8
	solid.content_margin_top = 6
	side.add_theme_stylebox_override("panel", solid)
	var bar_style := solid.duplicate() as StyleBoxFlat
	bar_style.content_margin_top = 4
	bar_style.content_margin_bottom = 4
	top.add_theme_stylebox_override("panel", bar_style)
	side.set_anchors_preset(Control.PRESET_LEFT_WIDE)
	side.offset_top = 44
	side.custom_minimum_size = Vector2(236, 0)
	root.add_child(side)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	side.add_child(scroll)
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 6)
	scroll.add_child(col)

	_heading(col, "图层")
	var layer_grid := GridContainer.new()
	layer_grid.columns = 3
	col.add_child(layer_grid)
	var lg := ButtonGroup.new()
	for i in LAYERS.size():
		var b := _toggle(layer_grid, LAYERS[i], lg, i == 0)
		b.pressed.connect(select_layer.bind(i))
		_layer_buttons.append(b)

	_heading(col, "画笔")
	_tool_box = VBoxContainer.new()
	col.add_child(_tool_box)

	_heading(col, "形状")
	var shape_grid := GridContainer.new()
	shape_grid.columns = 3
	col.add_child(shape_grid)
	var sg := ButtonGroup.new()
	for s in SHAPES:
		var b := _toggle(shape_grid, s[0], sg, s[1] == shape)
		b.pressed.connect(_on_shape.bind(s[1]))

	_heading(col, "大小")
	_size_slider = HSlider.new()
	_size_slider.min_value = 1
	_size_slider.max_value = 16
	_size_slider.value = brush_size
	_size_slider.value_changed.connect(_on_size)
	col.add_child(_size_slider)

	_density_row = VBoxContainer.new()
	col.add_child(_density_row)
	_heading(_density_row, "密度")
	var ds := HSlider.new()
	ds.min_value = 0.1
	ds.max_value = 1.0
	ds.step = 0.05
	ds.value = density
	ds.value_changed.connect(func(v): density = v)
	_density_row.add_child(ds)

	_face_row = VBoxContainer.new()
	col.add_child(_face_row)
	_heading(_face_row, "岩壁高度")
	var fs := HSlider.new()
	fs.min_value = 22
	fs.max_value = 60
	fs.value = cliff_face
	fs.value_changed.connect(func(v): cliff_face = int(v))
	_face_row.add_child(fs)

	_eraser_btn = CheckButton.new()
	_eraser_btn.text = "橡皮擦（E，或按住右键）"
	_eraser_btn.toggled.connect(_on_eraser)
	col.add_child(_eraser_btn)

	_hint = Label.new()
	_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hint.custom_minimum_size = Vector2(210, 0)
	_hint.add_theme_font_size_override("font_size", 12)
	_hint.modulate = Color(1, 1, 1, 0.75)
	col.add_child(_hint)

	_build_dialogs(root)
	select_layer(Layer.GROUND)


func select_layer(i: int) -> void:
	layer = i
	if not _layer_buttons.is_empty():
		_layer_buttons[i].button_pressed = true
	for c in _tool_box.get_children():
		c.queue_free()
	var g := ButtonGroup.new()
	var list: Array = TOOLS[i]
	if i == Layer.BUILDING:
		list = FloraLibrary.manifest().get("buildings", []).map(func(e: Dictionary) -> Array: return [e.name, e.id, e.get("group", "")])
	tool = list[1][1] if i == Layer.GROUND else list[0][1]
	var grid: GridContainer = null
	var group_name := "-"
	for t in list:
		var tg: String = t[2] if t.size() > 2 else ""
		if grid == null or tg != group_name:  # buildings come in groups, each under a heading
			if tg != "":
				_heading(_tool_box, tg)
			grid = GridContainer.new()
			grid.columns = 2
			_tool_box.add_child(grid)
			group_name = tg
		var b := _toggle(grid, t[0], g, typeof(t[1]) == typeof(tool) and t[1] == tool)
		b.pressed.connect(select_tool.bind(t[1]))
	_density_row.visible = i == Layer.PLANTS
	_face_row.visible = i == Layer.CLIFF
	_refresh_hint()
	cursor.queue_redraw()


func _on_overlay_toggled(on: bool) -> void:
	overlay.visible = on and player == null
	overlay.refresh()


func _on_shape(id: String) -> void:
	shape = id
	cursor.queue_redraw()


func _on_size(v: float) -> void:
	brush_size = int(v)
	cursor.queue_redraw()


func _on_eraser(on: bool) -> void:
	eraser = on
	cursor.queue_redraw()


func select_tool(id: Variant) -> void:
	tool = id
	_refresh_hint()


func _refresh_hint() -> void:
	if _hint == null:
		return
	var base := "左键画，右键擦；中键或空格+拖动平移，滚轮缩放；Ctrl+Z 撤销，Ctrl+Y 重做；[ ] 调大小。"
	var extra := ""
	match layer:
		Layer.GROUND:
			extra = "草地画笔和橡皮擦都会把地面还原成草地。"
		Layer.WATER:
			extra = "画出的水自动连成一片，越往中间越深；岸边一圈浅水可以走。"
		Layer.PLANTS:
			extra = "大小为 1 时单击放一棵；大一点的笔刷按密度撒一片，会避开水和岩壁。橡皮擦删除笔刷范围内的植物和石头。"
		Layer.CLIFF:
			extra = "画岩壁：按住左键横着拖出岩壁顶边。土坡/石阶/草坡：在岩壁上单击开一个坡道，宽度随笔刷大小。右键单击岩壁：先删坡道，再删岩壁。"
		Layer.PASSAGE:
			extra = "阻挡：画出看不见的墙。木桥：在水面上铺一座能走的木桥。出生点：试玩时角色出现的位置。橡皮擦恢复成自动判断。"
		Layer.BUILDING:
			extra = "单击放一座建筑（光标点 = 门口台阶），会自动清掉脚下的植物；红色表示这里放不下。右键单击建筑把它删掉。墙不能穿过，黄点是门口（集市摊位没有门）。"
	_hint.text = extra + "\n\n" + base


func _refresh_status() -> void:
	if _status == null or world == null or world.data == null:
		return
	var c := _cell(_mouse_world())
	var nm := map_path.get_file() if map_path != "" else "未保存"
	_status.text = "%s   %d×%d 格   光标 (%d, %d)   缩放 %d×  " % [nm, world.data.size.x, world.data.size.y, c.x, c.y, int(camera.zoom.x)]


func _flash(msg: String) -> void:
	if _status:
		_status.text = msg + "  "
	print(msg)


func _on_save(as_new: bool) -> void:
	if map_path == "" or as_new:
		_save_dialog.popup_centered_ratio(0.7)
	else:
		save_map(map_path)


func _build_dialogs(root: Control) -> void:
	_new_dialog = ConfirmationDialog.new()
	_new_dialog.title = "新建地图"
	var box := GridContainer.new()
	box.columns = 2
	_new_dialog.add_child(box)
	var lw := Label.new()
	lw.text = "宽（格，每格 8 像素）"
	box.add_child(lw)
	_new_w = SpinBox.new()
	_new_w.min_value = 40
	_new_w.max_value = 400
	_new_w.value = 120
	box.add_child(_new_w)
	var lh := Label.new()
	lh.text = "高（格）"
	box.add_child(lh)
	_new_h = SpinBox.new()
	_new_h.min_value = 30
	_new_h.max_value = 400
	_new_h.value = 68
	box.add_child(_new_h)
	_new_dialog.confirmed.connect(func(): new_map(Vector2i(int(_new_w.value), int(_new_h.value))))
	root.add_child(_new_dialog)

	# maps go in the project's maps/ folder when running from the project, else the user folder
	var maps_dir := ProjectSettings.globalize_path("res://maps")
	if OS.has_feature("template") or not DirAccess.dir_exists_absolute(maps_dir):
		maps_dir = OS.get_user_data_dir() + "/maps"
	DirAccess.make_dir_recursive_absolute(maps_dir)
	_open_dialog = FileDialog.new()
	_open_dialog.title = "打开地图"
	_open_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	_open_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_open_dialog.use_native_dialog = true
	_open_dialog.filters = PackedStringArray(["*.json ; 地图文件"])
	_open_dialog.current_dir = maps_dir
	_open_dialog.file_selected.connect(open_map)
	root.add_child(_open_dialog)
	_save_dialog = FileDialog.new()
	_save_dialog.title = "保存地图"
	_save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	_save_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_save_dialog.use_native_dialog = true
	_save_dialog.filters = PackedStringArray(["*.json ; 地图文件"])
	_save_dialog.current_dir = maps_dir
	_save_dialog.current_file = "我的地图.json"
	_save_dialog.file_selected.connect(func(path): save_map(path if path.ends_with(".json") else path + ".json"))
	root.add_child(_save_dialog)


func _heading(parent: Control, text: String) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", 13)
	l.modulate = Color(1, 0.92, 0.7)
	parent.add_child(l)


func _button(parent: Control, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


func _toggle(parent: Control, text: String, group: ButtonGroup, on: bool) -> Button:
	var b := Button.new()
	b.text = text
	b.toggle_mode = true
	b.button_group = group
	b.button_pressed = on
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(b)
	return b

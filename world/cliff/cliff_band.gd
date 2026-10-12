@tool
class_name CliffBand
extends Sprite2D
## A layered sandstone cliff generated along a polyline (the top edge, left to right, in local
## coordinates). The face height wanders, rock spurs push down into the meadow and recesses cut
## back, strata are irregular with cracks and weathering, grass hangs off the lip in uneven clumps
## and only the odd vine trails down. Openings (cave mouths with a stone frame) can be cut in.
## The foot grows tall grass through GrassField (grass_skirt) and the face keeps grass off.

const ROCK := ["#3b2a24", "#5e4232", "#82603f", "#a47e52", "#c19c69", "#d9b884", "#ecd2a2", "#f8e8c4"]
const MOSS := ["#1f3d22", "#2f5a2c", "#457a36", "#62994a"]
const LEAF := ["#122a1a", "#1d4325", "#2a5f2f", "#3b7c37", "#579b45", "#7fbd58", "#aedb7a"]
const MARBLE := ["#4b5160", "#aab2c4", "#d6dce8", "#eef1f7", "#ffffff"]
const FLOWERS := ["#ffffff", "#ffe066", "#ffc4e1"]
const BAYER := [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]

@export var points := PackedVector2Array([Vector2(0, 40), Vector2(426, 40)]):
	set(v):
		points = v
		_queue()
@export var face := 30:
	set(v):
		face = v
		_queue()
@export var seed := 41:
	set(v):
		seed = v
		_queue()
@export_range(0.0, 1.0) var vines := 0.25:  ## vines per 100 px
	set(v):
		vines = v
		_queue()
@export_range(0.0, 2.0) var hanging_grass := 1.0:
	set(v):
		hanging_grass = v
		_queue()
@export var openings := PackedVector2Array():  ## (centre x, half width) of cave mouths
	set(v):
		openings = v
		_queue()
@export var regenerate := false:
	set(_v):
		_queue()

var _top := PackedFloat32Array()
var _bottom := PackedFloat32Array()
var _x0 := 0
var _y0 := 0
var _img: Image
var _rng := RandomNumberGenerator.new()
var _pending := false


func _ready() -> void:
	add_to_group("grass_exclude")
	add_to_group("grass_skirt")
	centered = false
	z_index = -8
	generate()


func generate() -> void:
	_pending = false
	if points.size() < 2:
		return
	_rng.seed = seed
	_x0 = int(points[0].x)
	var x1 := int(points[points.size() - 1].x)
	var w := x1 - _x0
	var ymin := INF
	var ymax := -INF
	for p in points:
		ymin = minf(ymin, p.y)
		ymax = maxf(ymax, p.y)
	_y0 = int(ymin) - 18
	var h := int(ymax) + face + 36 - _y0
	_img = Image.create(w, h, false, Image.FORMAT_RGBA8)
	_shape(w)
	_paint_face(w)
	_paint_lip(w)
	_paint_vines(w)
	for o in openings:
		_paint_opening(int(o.x) - _x0, int(o.y))
	_paint_foot(w)
	texture = ImageTexture.create_from_image(_img)
	offset = Vector2(_x0, _y0)


## Top and bottom of the face per column: wandering edge, spurs that reach down, recesses.
func _shape(w: int) -> void:
	_top.resize(w)
	_bottom.resize(w)
	var spurs := []
	var x := _rng.randf_range(10, 40)
	while x < w:
		spurs.append(Vector3(x, _rng.randf_range(7, 26), _rng.randf_range(-11, 20)))  # centre, half width, depth (+down / -recess)
		x += _rng.randf_range(22, 70)
	for i in w:
		var base := _line_y(i + _x0)
		var t := base + (_noise(i, 0, 52) - 0.5) * 22 + (_noise(i, 9, 15) - 0.5) * 7
		var b := t + face + (_noise(i, 3, 38) - 0.5) * 18 + (_noise(i, 21, 9) - 0.5) * 4
		for s in spurs:
			var d: float = absf(i - s.x) / s.y
			if d < 1.0:
				var bump: float = s.z * (1.0 - d * d)
				b += bump
				t += bump * 0.25 * (1.0 if s.z < 0.0 else -0.3)
		_top[i] = t
		_bottom[i] = maxf(b, t + 10)


func _paint_face(w: int) -> void:
	var strata_seed := _rng.randi_range(0, 9999)
	for i in w:
		var t := int(_top[i])
		var b := int(_bottom[i])
		var hgt := float(b - t)
		# always the same layers, but each one's thickness swells and thins smoothly along the
		# cliff, so a layer pinches out gradually instead of the strata jumping at a seam
		var n_strata := 4
		var thick := []
		var total := 0.0
		for k in n_strata:
			var th := 0.06 + pow(_noise(i, 40 + k * 13, 55), 1.6) + 0.35 * _noise(i, 90 + k * 11, 17)
			thick.append(th)
			total += th
		var bounds := [float(t)]
		var acc := 0.0
		for k in range(1, n_strata):
			acc += thick[k - 1] / total
			var y_k: float = t + hgt * acc + (_noise(i, 50 + k * 7, 18) - 0.5) * 3.0
			bounds.append(clampf(y_k, bounds[k - 1], float(b)))
		bounds.append(float(b))
		for y in range(t, b):
			var k := 0
			while k < n_strata - 1 and y >= bounds[k + 1]:
				k += 1
			var s0: float = bounds[k]
			var s1: float = bounds[k + 1]
			var f := (y - s0) / maxf(s1 - s0, 1.0)
			# cracks: hashed per stratum, spacing varies, slight slant
			var cx := float(i) + (y - s0) * (0.15 + 0.3 * _hash(k, strata_seed))
			var span := 14.0 + _hash(k, strata_seed + 1) * 30.0  # block width differs per layer
			var cell := floori((cx + _hash(k, strata_seed + 2) * span) / span)
			var crack_x := (cell + 0.2 + _hash(cell, k + strata_seed) * 0.6) * span - _hash(k, strata_seed + 2) * span
			var dc := cx - crack_x
			var v := 0.74 - f * 0.42 + (_noise(i, y, 3) - 0.5) * 0.26 + (_noise(i, y + 100, 11) - 0.5) * 0.32
			v -= 0.14 * (y - t) / maxf(hgt, 1.0)
			if f < 0.12:
				v += 0.28
			if _hash(cell, k + 77) < 0.6:
				if dc >= 0.0 and dc < 1.6:
					v -= 0.45
				elif dc < 0.0 and dc > -1.6:
					v += 0.12
			var col := _q(ROCK, v, i, y)
			if f > 0.9 and _rng.randf() < 0.5:
				col = Color(ROCK[1])
			if f < 0.07 and k > 0 and _noise(i, y + 300, 9) > 0.62:
				col = Color(MOSS[_rng.randi_range(1, 3)])
			_put(i, y, col)
	# a few rounded outcrops bulging from the face
	var x := _rng.randf_range(20, 80)
	while x < w:
		var r := _rng.randf_range(4, 8)
		var cy := lerpf(_top[int(x)], _bottom[int(x)], _rng.randf_range(0.35, 0.75))
		for yy in range(int(cy - r), int(cy + r) + 1):
			for xx in range(int(x - r * 1.3), int(x + r * 1.3) + 1):
				var dx := (xx - x) / (r * 1.3)
				var dy := (yy - cy) / r
				if dx * dx + dy * dy <= 1.0 and xx >= 0 and xx < w:
					var lit := -0.55 * dx - 0.75 * dy + 0.45 * sqrt(maxf(0.0, 1.0 - dx * dx - dy * dy))
					_put(xx, yy, _q(ROCK, 0.25 + lit * 0.6, xx, yy))
					if dx * dx + dy * dy > 0.8 and dx + dy > 0.4:
						_put(xx, yy, Color(ROCK[1]))
		x += _rng.randf_range(60, 150)


## Grass lip of uneven thickness, with clumps of grass hanging over the edge.
func _paint_lip(w: int) -> void:
	var i := 0
	while i < w:
		var t := int(_top[i])
		var lip := 1 + int(_noise(i, 7, 9) * 4.0)
		for j in lip:
			_put(i, t - j, Color(LEAF[3 if j == lip - 1 else 2]))
		if _rng.randf() < 0.35:
			_put(i, t - lip, Color(LEAF[5]))
		_blend(i, t + 1, Color(0.08, 0.12, 0.06, 0.45))
		_blend(i, t + 2, Color(0.08, 0.12, 0.06, 0.22))
		i += 1
	# hanging clumps: irregular widths and lengths, separated by bare stretches
	var x := _rng.randf_range(0, 12)
	while x < w:
		var cw := _rng.randi_range(3, 11)
		var depth := _rng.randf_range(2, 7) * hanging_grass
		for k in cw:
			var xx := int(x) + k
			if xx >= w:
				break
			var t := int(_top[xx])
			var n_px := int(depth * (1.0 - absf(k - cw / 2.0) / (cw / 2.0 + 1)) + _rng.randf_range(0, 2.5))
			for j in n_px:
				var c := Color(LEAF[2 if j < n_px - 1 else (1 if _rng.randf() < 0.5 else 3)])
				if j == 0:
					c = Color(LEAF[4])
				_put(xx, t + 1 + j, c)
			if _rng.randf() < 0.04 * hanging_grass:
				_put(xx, t + 1 + n_px, Color(FLOWERS[_rng.randi() % 3]))
		x += cw + _rng.randf_range(4, 30) / maxf(hanging_grass, 0.2)


func _paint_vines(w: int) -> void:
	var count := int(w / 100.0 * vines + 0.5)
	for n in count:
		var x := _rng.randf_range(4, w - 4)
		var t := _top[int(x)]
		var length := _rng.randf_range(5, minf(16, (_bottom[int(x)] - t) * 0.6))
		var vx := x
		for j in int(length):
			vx += sin(j * 0.6 + x) * 0.25
			_put(int(vx), int(t) + 2 + j, Color(LEAF[2]))
			if j % 3 == 1:
				var side := 1 if (j / 3) % 2 == 0 else -1
				_put(int(vx) + side, int(t) + 2 + j, Color(LEAF[4]))


func _paint_opening(cx: int, half: int) -> void:
	if cx < 0 or cx >= _bottom.size():
		return
	var by := int(_bottom[cx])
	for y in range(by - half * 2 + 2, by):
		for x in range(cx - half, cx + half + 1):
			var nx := (x - cx) / (half - 0.5)
			var ny := (y - (by - half * 0.7)) / (half * 1.3)
			if nx * nx + minf(0.0, ny) * minf(0.0, ny) <= 1.0:
				var depth := (y - (by - half * 2.0)) / (half * 2.0)
				_put(x, y, Color("#1d1428") if depth < 0.6 else Color("#2a1d3a"))
	for side in [-1, 1]:
		var x: int = cx + side * (half + 1)
		for y in range(by - int(half * 1.4), by):
			_put(x - 1, y, Color(MARBLE[0]))
			_put(x, y, Color(MARBLE[3] if side < 0 else MARBLE[2]))
			_put(x + 1, y, Color(MARBLE[0]))
	for a in range(0, 181, 7):
		var r := deg_to_rad(a)
		var x := cx + int(roundf(cos(r) * (half + 1)))
		var y := by - int(half * 1.4) - int(roundf(sin(r) * half * 0.65))
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				_put(x + dx, y + dy, Color(MARBLE[0]))
		_put(x, y, Color(MARBLE[3] if a > 90 else MARBLE[2]))
	for x in range(cx - half - 2, cx + half + 3):
		_put(x, by, Color(MARBLE[0]))
		_put(x, by + 1, Color(MARBLE[2]))
		_put(x, by + 2, Color(MARBLE[1]))


## Rubble at the foot and the cliff's shadow on the meadow.
func _paint_foot(w: int) -> void:
	for i in w:
		var b := int(_bottom[i])
		for k in 6:
			_blend(i, b + 1 + k, Color(0.08, 0.16, 0.1, 0.26 - k * 0.04))
	var count := w / 18
	for n in count:
		var x := _rng.randf_range(0, w)
		var b := _bottom[int(x)]
		var r := _rng.randf_range(1.5, 3.5)
		for y in range(int(b - r), int(b + 2)):
			for xx in range(int(x - r - 1), int(x + r + 2)):
				var dx := (xx - x) / r
				var dy := (y - b) / (r * 0.8)
				if dx * dx + dy * dy <= 1.0:
					_put(xx, y, _q(ROCK, 0.35 - 0.4 * dx - 0.5 * dy, xx, y, 2))


## Top edge / foot of the face (global y) at a global x, for snapping waterfalls and props.
func top_at(world_x: float) -> float:
	var i := clampi(int(to_local(Vector2(world_x, 0)).x) - _x0, 0, _top.size() - 1)
	return to_global(Vector2(0, _top[i])).y


func bottom_at(world_x: float) -> float:
	var i := clampi(int(to_local(Vector2(world_x, 0)).x) - _x0, 0, _bottom.size() - 1)
	return to_global(Vector2(0, _bottom[i])).y


func grass_excludes(world: Vector2) -> bool:
	var p := to_local(world)
	var i := int(p.x) - _x0
	if i < 0 or i >= _bottom.size():
		return false
	return p.y > _top[i] - 1 and p.y < _bottom[i] + 1


func grass_skirt_points() -> PackedVector2Array:
	var out := PackedVector2Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed + 5
	for i in range(0, _bottom.size(), 2):
		var x := float(i + _x0)
		var near_opening := false
		for o in openings:
			if absf(x - o.x) < o.y + 6:
				near_opening = true
		if near_opening and rng.randf() < 0.7:
			continue
		out.append(to_global(Vector2(x + rng.randi_range(-1, 1), _bottom[i] + rng.randi_range(0, 2))))
		if rng.randf() < 0.6:
			out.append(to_global(Vector2(x + rng.randi_range(-1, 1), _bottom[i] + rng.randi_range(3, 5))))
	return out


# ---------------------------------------------------------------- helpers

func _line_y(x: float) -> float:
	for k in range(points.size() - 1):
		var a := points[k]
		var b := points[k + 1]
		if x <= b.x or k == points.size() - 2:
			return lerpf(a.y, b.y, clampf((x - a.x) / maxf(b.x - a.x, 1.0), 0.0, 1.0))
	return points[0].y


func _hash(ix: int, iy: int) -> float:
	var n := (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xffffffff
	n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
	return float((n ^ (n >> 16)) & 0xffff) / 65535.0


func _noise(x: float, y: float, cell: float) -> float:
	var fx := x / cell
	var fy := y / cell
	var ix := floori(fx)
	var iy := floori(fy)
	var tx := fx - ix
	var ty := fy - iy
	tx = tx * tx * (3.0 - 2.0 * tx)
	ty = ty * ty * (3.0 - 2.0 * ty)
	var a := _hash(ix, iy)
	var b := _hash(ix + 1, iy)
	var c := _hash(ix, iy + 1)
	var d := _hash(ix + 1, iy + 1)
	return a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty


func _q(ramp: Array, v: float, x: int, y: int, lo := 1) -> Color:
	var t: float = (BAYER[(y & 3) * 4 + (x & 3)] / 16.0 - 0.5) * 0.9
	var n := ramp.size()
	return Color(ramp[clampi(int(v * (n - lo) + lo + t), lo, n - 1)])


func _put(x: int, y: int, c: Color) -> void:
	y -= _y0
	if x >= 0 and y >= 0 and x < _img.get_width() and y < _img.get_height():
		_img.set_pixel(x, y, c)


func _blend(x: int, y: int, c: Color) -> void:
	y -= _y0
	if x >= 0 and y >= 0 and x < _img.get_width() and y < _img.get_height():
		_img.set_pixel(x, y, _img.get_pixel(x, y).blend(c))


func _queue() -> void:
	if not is_inside_tree() or _pending:
		return
	_pending = true
	generate.call_deferred()

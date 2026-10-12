@tool
class_name CliffBand
extends Sprite2D
## A layered sandstone cliff generated along a polyline (the top edge, left to right, in local
## coordinates). The face height wanders, rock spurs push down into the meadow and recesses cut
## back, strata are irregular with cracks and weathering, grass hangs off the lip in uneven clumps
## and only the odd vine trails down. Openings (cave mouths with a stone frame) can be cut in, and
## ramps cut through the face so the upper level can be reached: an earthen slope or stone stairs.
## The face blocks walking (a StaticBody2D is generated along it) except where a ramp cuts through.
## The foot grows tall grass through GrassField (grass_skirt) and the face keeps grass off.

const ROCK := ["#3b2a24", "#5e4232", "#82603f", "#a47e52", "#c19c69", "#d9b884", "#ecd2a2", "#f8e8c4"]
const MOSS := ["#1f3d22", "#2f5a2c", "#457a36", "#62994a"]
const LEAF := ["#122a1a", "#1d4325", "#2a5f2f", "#3b7c37", "#579b45", "#7fbd58", "#aedb7a"]
const STONE := ["#3a3633", "#58514b", "#7a7064", "#9d917e", "#bfb39a", "#ddd3b9", "#f1ead6"]
const DIRT := ["#5f4630", "#755737", "#8a6a3e", "#a7834f", "#c39d63", "#d8b57a"]  # top four match ground.gdshader
const MEADOW := ["#3f8f3f", "#55a748", "#6fbf55", "#8fd168"]  # ground.gdshader grass0..3
const MEADOW_BLADE := "#357a36"
const STONE_MOSS := Color("#8a9a5e")  # soft olive moss that sits with the meadow
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
## Ramps up to the upper level: (centre x, half width, style). Style 0 = earthen slope, 1 = stone
## stairs, 2 = grassy slope (no path; the meadow's tufts grow on it). Each one cuts the face, leaves a gap in the collision and paints dirt at both mouths.
@export var ramps := PackedVector3Array():
	set(v):
		ramps = v
		_queue()
@export var collision := true  ## generate a StaticBody2D so characters cannot walk through the face
@export var regenerate := false:
	set(_v):
		_queue()

var _top := PackedFloat32Array()
var _top_orig := PackedFloat32Array()  # top edge before grass slopes lowered it
var _bottom := PackedFloat32Array()
var _x0 := 0
var _y0 := 0
var _img: Image
var _rng := RandomNumberGenerator.new()
var _pending := false
var _spillways: Array[Node2D] = []  # waterfalls pouring over this cliff (see add_spillway)


func _ready() -> void:
	add_to_group("grass_exclude")
	add_to_group("grass_skirt")
	add_to_group("cliffs")
	add_to_group("terrain_painters")
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
	_y0 = int(ymin) - 18 - (_notch_len() if not ramps.is_empty() else 0)  # room for ramp gullies
	var h := int(ymax) + face + 36 - _y0
	_img = Image.create(w, h, false, Image.FORMAT_RGBA8)
	_shape(w)
	_taper_for_grass_slopes(w)
	_paint_face(w)
	_paint_lip(w)
	_paint_vines(w)
	for o in openings:
		_paint_opening(int(o.x) - _x0, int(o.y))
	_paint_foot(w)
	_clear_spillways()
	for r in ramps:
		_paint_ramp(int(r.x) - _x0, int(r.y), int(r.z))
	texture = ImageTexture.create_from_image(_img)
	offset = Vector2(_x0, _y0)
	_build_collision()
	if not ramps.is_empty() and is_inside_tree():
		var t := get_tree().get_first_node_in_group("terrain")
		if t:
			t.call_deferred("rebuild")  # repaint the dirt at the ramp mouths


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
	for i in w:
		var t := int(_top[i])
		var b := int(_bottom[i])
		var hgt := float(b - t)
		# the same layers all along, but each swells and thins, dips a little, and here and there its
		# parting dissolves so neighbouring layers run into one another (no brick courses)
		var n_strata := 4
		var thick := []
		var total := 0.0
		for k in n_strata:
			var th := 0.06 + pow(_noise(i, 40 + k * 13, 55), 1.6) + 0.35 * _noise(i, 90 + k * 11, 17)
			thick.append(th)
			total += th
		var bounds := [float(t)]
		var seen := [1.0]  # how visible each parting is (the top edge always)
		var acc := 0.0
		for k in range(1, n_strata):
			acc += thick[k - 1] / total
			var dip := (_noise(i, 200 + k * 9, 90) - 0.5) * 9.0 + (_noise(i, 50 + k * 7, 18) - 0.5) * 3.0
			bounds.append(clampf(t + hgt * acc + dip, bounds[k - 1], float(b)))
			seen.append(smoothstep(0.28, 0.5, _noise(i, 500 + k * 17, 38)))
		bounds.append(float(b))
		seen.append(1.0)
		for y in range(t, b):
			var k := 0
			while k < n_strata - 1 and y >= bounds[k + 1]:
				k += 1
			var s0: float = bounds[k]
			var s1: float = bounds[k + 1]
			var f := (y - s0) / maxf(s1 - s0, 1.0)
			var above: float = seen[k]
			var below: float = seen[k + 1]
			# broad, uneven light: big facets, smaller lumps, a gentle darkening toward the foot
			var v := 0.6 + (_noise(i, y, 13) - 0.5) * 0.42 + (_noise(i + 7, y, 5) - 0.5) * 0.26 + (_noise(i, y, 2) - 0.5) * 0.12
			v -= 0.14 * (y - t) / maxf(hgt, 1.0)
			# each ledge is lit along its upper lip and shaded under its overhang, where the parting shows
			v += (0.1 - f * 0.26) * maxf(above, below * 0.5)
			var lip := 0.1 + _noise(i, y + 600, 4) * 0.12
			if f < lip and above > 0.5 and _noise(i, k * 31 + 700, 6) > 0.32:
				v += 0.24
			if f > 0.9 and below > 0.5 and _noise(i, k * 29 + 800, 5) > 0.3:
				v -= 0.22
			# rain streaks running down the face
			var streak := _noise(i, y * 0.12 + 400.0, 4)
			if streak > 0.74:
				v -= 0.12
			elif streak < 0.18:
				v += 0.06
			var col := _q(ROCK, v, i, y)
			if f < 0.08 and k > 0 and above > 0.5 and _noise(i, y + 300, 9) > 0.64:
				col = Color(MOSS[1 + (i + y) % 3])
			_put(i, y, col)
	_paint_cracks(w)
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


## Cracks that wander down the face in any direction, crossing layers, now and then forking;
## dark with a lit lower-right edge, scattered unevenly with long stretches of sound rock.
func _paint_cracks(w: int) -> void:
	var count := w / 15
	for n in count:
		var x := _rng.randf_range(0, w - 1)
		if _noise(x, 900, 60) < 0.3:
			continue  # sound stretches of rock
		var t := _top[int(x)]
		var hgt := _bottom[int(x)] - t
		var y := t + hgt * _rng.randf_range(0.08, 0.6)
		var drift := _rng.randf_range(-0.8, 0.8)
		var length := int(_rng.randf_range(3.0, maxf(6.0, hgt * 0.75))) if _rng.randf() < 0.6 else _rng.randi_range(2, 5)  # long fissures and short fractures
		_crack(x, y, drift, length, true)


func _crack(x: float, y: float, drift: float, length: int, can_fork: bool) -> void:
	for step in length:
		var ix := int(roundf(x))
		var iy := int(roundf(y))
		if ix < 1 or ix >= _bottom.size() - 1 or iy >= _bottom[ix] - 1:
			return
		var yy := iy - _y0
		if yy < 0 or yy >= _img.get_height():
			return
		var c := _img.get_pixel(ix, yy)
		if c.a > 0.5 and c.r > c.g:
			_img.set_pixel(ix, yy, c.darkened(0.5))
			if can_fork and length > 8 and step < length * 0.4:
				var c0 := _img.get_pixel(ix - 1, yy)  # the fissure is wider where it opens
				if c0.a > 0.5 and c0.r > c0.g:
					_img.set_pixel(ix - 1, yy, c0.darkened(0.3))
			var c2 := _img.get_pixel(ix + 1, yy)
			if c2.a > 0.5 and c2.r > c2.g:
				_img.set_pixel(ix + 1, yy, c2.lightened(0.14))
		y += 1.0
		x += drift + _rng.randf_range(-0.45, 0.45)
		drift = clampf(drift + _rng.randf_range(-0.15, 0.15), -1.1, 1.1)
		if can_fork and step > 2 and _rng.randf() < 0.07:
			_crack(x, y, -drift * 0.8 + _rng.randf_range(-0.3, 0.3), _rng.randi_range(2, 6), false)


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


## A waterfall pours over the edge here: no grass lip across its width, so the river above runs
## straight into the fall.
func add_spillway(fall: Node2D) -> void:
	if fall not in _spillways:
		_spillways.append(fall)
		_queue()


func _clear_spillways() -> void:
	for f in _spillways:
		if not is_instance_valid(f):
			continue
		var cx := int(to_local(f.global_position).x) - _x0
		var half := int(f.get("width")) / 2
		for i in range(cx - half, cx + half + 1):
			if i < 0 or i >= _top.size():
				continue
			for y in range(int(_top[i]) - 8, int(_top[i]) + 1):
				_put(i, y, Color(0, 0, 0, 0))


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


## A ramp cut through the face. Climbing from the lower meadow to the upper level it has to cut
## back into the high ground too, so above the top edge it runs on as a gully between two banks
## that rise from nothing at its rounded far end to the full cut where the face drops away. The
## floor (earthen slope, stone stairs, or the meadow itself) darkens the deeper it lies, the left
## bank and wall throw their shadow across it, the left side is in shade and the right side lit.
func _paint_ramp(cx: int, half: int, style: int) -> void:
	var l := cx - half
	var r := cx + half
	if r < 0 or l >= _top.size():
		return
	var span := _ramp_span(cx, half)
	var ta := span.x
	var ba := span.y
	var nl := float(_notch_len())
	var yn := ta - nl  # far end of the gully
	var y1 := int(ba) + 3
	var orig := _img.duplicate() as Image  # the uncut face, to texture the cut walls with
	# clear the face, lip, hanging grass and foot rubble across the cut
	for i in range(l, r + 1):
		for y in range(int(_top[clampi(i, 0, _top.size() - 1)]) - 10, int(_bottom[clampi(i, 0, _top.size() - 1)]) + 9):
			_put(i, y, Color(0, 0, 0, 0))
	# the floor, from the far end of the gully down to the foot
	var steps := maxi(2, int(roundf((ba - yn) / 6.0)))
	var sh := (ba - yn + 2.0) / steps
	for y in range(int(yn) - 1, y1 + 1):
		var west := float(l)
		var east := float(r)
		if y < ta:
			west = cx - _notch_hw(y, ta, nl, half, -1, cx)
			east = cx + _notch_hw(y, ta, nl, half, 1, cx)
		var depth := clampf((y - yn) / maxf(ba - yn, 1.0), 0.0, 1.0)  # 0 far end .. 1 foot
		for i in range(int(ceilf(west)), int(floorf(east)) + 1):
			if y >= ta:
				var bot_i := y1 - int(_noise(i, 9, 4) * 3.0)
				if y > bot_i:
					continue
			var u := (i - cx) / float(maxi(half, 1))  # -1..1 across
			var b: float = BAYER[(y & 3) * 4 + (i & 3)] / 16.0 - 0.5
			var fade := smoothstep(0.45, 1.0, (ta - y) / nl) if y < ta else 0.0
			if fade > 0.0 and style != 2 and _hash(i * 3 + 1, y * 7 + 5) + _noise(i, y + 300, 3) * 0.4 < fade * 1.25:
				continue  # the far end of the gully peters out into the ground
			var shadow := i - west < 1.0 + 4.0 * depth + (_noise(i, y, 3) - 0.5)  # from the left bank / wall
			var c: Color
			if style == 1:
				c = _stair_pixel(i, y, u, yn, sh, b).darkened(depth * 0.24)
				if shadow:
					c = c.darkened(0.3)
			elif style == 2:
				# the meadow itself shows through (same ground, same tufts); only shade is laid over
				# it, deepening down the slope and fading out at both ends so there is no seam
				var ends := smoothstep(0.0, 0.14, depth) * (1.0 - smoothstep(0.86, 1.0, depth))
				var shade := ((0.04 + 0.22 * depth) * ends + (0.16 if shadow else 0.0) * smoothstep(0.0, 0.25, depth)) * (1.0 - fade)
				var swell := fposmod((y + _noise(i, 60, 7) * 4.0) / 11.0, 1.0)
				if swell < 0.12 and _noise(i, y + 90, 6) > 0.5:
					shade += 0.06 * ends  # soft lumps in the turf hint at the slope
				shade *= 1.0 - smoothstep(0.55, 1.0, absf(u)) * 0.7  # soft at the sides, no hard edge
				shade = floorf((shade + b * 0.06) * 24.0) / 24.0
				c = Color(0.04, 0.12, 0.06, clampf(shade, 0.0, 0.5))
			else:
				var v: float = 0.3 + 0.55 * (1.0 - depth) + 0.12 * (1.0 - absf(u)) + (_noise(i, y, 3) - 0.5) * 0.24 + b * 0.2
				var ledge := fposmod((y + _noise(i, 40, 6) * 5.0) / 9.0, 1.0)
				if _noise(i, y + 140, 5) < 0.45:
					ledge = 0.5  # the ledges break up, so it reads as a slope rather than steps
				if ledge < 0.12:
					v -= 0.3  # little erosion ledges down the slope: a dark lip...
				elif ledge < 0.24:
					v += 0.16  # ...under a lit edge
				if shadow:
					v -= 0.42
				c = Color(DIRT[clampi(int(v * 6.0), 0, 5)])
				var g := _noise(i, y + 70, 3)
				var edge := minf(i - west, east - i) / maxf(east - west, 1.0)  # 0 at the sides
				if edge < 0.2 and g > 0.5 + edge * 1.5:
					c = Color(MEADOW[2 if g > 0.8 else 1]).darkened(depth * 0.2)  # grass creeping in from the sides
					if _hash(i, y * 3 + 7) < 0.25:
						c = Color(MEADOW_BLADE)
				elif _hash(i * 7 + y, 913) < 0.012:
					c = Color(ROCK[5])
					_put(i, y + 1, Color(ROCK[2]))
			_put(i, y, c)
	# the gully banks: soil (turf for a grass slope) rising from nothing at the far end to the cut;
	# the left bank faces away from the light, the right one into it; turf lips the high ground
	for y in range(int(yn), int(ta) + 1):
		if style == 2:
			break  # a grass slope has no gully banks: the high ground just rolls down into it
		var g := clampf((ta - y) / nl, 0.0, 1.0)  # 0 at the face .. 1 at the far end
		var bh := int(roundf((1.0 - g) * 2.4 - 0.4))
		for side in [-1, 1]:
			var edge: float = cx + side * _notch_hw(y, ta, nl, half, side, cx)
			var x0: int = int(roundf(edge)) + side
			for k in bh:
				var x: int = x0 + side * k
				var c: Color
				if style == 2:
					c = Color(MEADOW_BLADE if side < 0 else MEADOW[2])
				else:
					c = Color(DIRT[1 if side < 0 else 4]) if k < bh - 1 else Color(DIRT[0] if side < 0 else DIRT[3])
				_put(x, y, c)
			var lip_x: int = x0 + side * bh
			if _noise(lip_x, y + 50, 3) > g * 1.15:  # the turf lip breaks up as the bank dies away
				_put(lip_x, y, Color(MEADOW[0] if side < 0 else MEADOW[2]))
				if _noise(lip_x, y, 3) > 0.55:
					_put(lip_x + side, y, Color(MEADOW[1]))
	if style == 2:
		_shade_tapered_ends(l, r)
		for i in range(l - 3, r + 4):
			for k in 4:
				_blend(i, y1 + 1 + k, Color(0.08, 0.16, 0.1, 0.1 - k * 0.025))
		return
	# freshly cut side walls: the same rock, turned away from the light on the left and into it on
	# the right; widening toward the foot, with a ragged inner edge
	for side in [-1, 1]:
		for y in range(int(ta), int(ba) + 2):
			var f := clampf((y - ta) / maxf(ba - ta, 1.0), 0.0, 1.0)
			var jag := int(roundf((_noise(side * 31, y, 4) - 0.5) * 3.0))
			var wpx := int(roundf(2.0 + 4.0 * f))
			var inner: int = (l + jag) if side < 0 else (r - jag)
			for k in wpx + 1:
				var x: int = (inner - k) if side < 0 else (inner + k)
				var yy := y - _y0
				if x < 0 or x >= _img.get_width() or yy < 0 or yy >= _img.get_height():
					continue
				var c := orig.get_pixel(x, yy)
				if c.a < 0.5 or c.g > c.r:
					c = _q(ROCK, 0.45 + (_noise(x, y, 3) - 0.5) * 0.3, x, y)
				if side < 0:
					c = c.darkened(0.45 - k * 0.03)
				else:
					c = c.lightened(0.3 - k * 0.03)
				if k == 0:
					c = c.lightened(0.18) if side > 0 else c.darkened(0.1)  # the edge along the floor
				elif k == wpx:
					c = c.darkened(0.45)  # crease where the wall meets the old face
				_img.set_pixel(x, yy, c)
	# the old face rounds off into the cut: shading wraps away from the light on the left end and
	# into it on the right end
	for side in [-1, 1]:
		for d in range(0, 9):
			var x: int = (l - 8 - d) if side < 0 else (r + 8 + d)
			if x < 0 or x >= _top.size():
				continue
			var amount := (1.0 - d / 9.0) * (0.3 if side < 0 else 0.14)
			for y in range(int(_top[x]) + 1, int(_bottom[x]) + 1):
				var yy := y - _y0
				if yy < 0 or yy >= _img.get_height():
					continue
				var c := _img.get_pixel(x, yy)
				if c.a < 0.5 or c.g > c.r:
					continue  # leave grass and holes alone
				_img.set_pixel(x, yy, c.darkened(amount) if side < 0 else c.lightened(amount))
	# turf overhanging the inner top edges of the cut walls, thinning out down the slope
	for side in [-1, 1]:
		for y in range(int(ta) - 1, int(ta + (ba - ta) * 0.7)):
			var f := clampf((y - ta) / maxf(ba - ta, 1.0), 0.0, 1.0)
			var jag := int(roundf((_noise(side * 31, y, 4) - 0.5) * 3.0))
			var x: int = (l + jag) if side < 0 else (r - jag)
			if _noise(x, y, 3) > 0.3 + f * 0.6:
				_put(x, y, Color(MEADOW[1] if (y & 1) == 0 else MEADOW_BLADE).darkened(f * 0.2))
				if _noise(x, y + 30, 2) > 0.6:
					_put(x - side, y, Color(MEADOW[2]).darkened(f * 0.2))
	# soft shadow of the cut on the meadow below
	for i in range(l - 3, r + 4):
		for k in 4:
			_blend(i, y1 + 1 + k, Color(0.08, 0.16, 0.1, 0.16 - k * 0.04))


## A grass slope is no cut: the cliff sinks into it. Either side of it the top edge comes down
## toward the foot, so the face shrinks to a low lip at the slope and the high ground rolls down
## to meet it.
func _taper_for_grass_slopes(w: int) -> void:
	_top_orig = _top.duplicate()
	for r in ramps:
		if int(r.z) != 2:
			continue
		var cx := int(r.x) - _x0
		var half := int(r.y)
		var reach := half * 1.5 + 10.0
		for side in [-1, 1]:
			for d in range(1, int(reach) + 1):
				var i: int = cx + side * (half + d)
				if i < 0 or i >= w:
					continue
				var t := 1.0 - smoothstep(0.0, 1.0, (d + (_noise(i, side * 7, 6) - 0.5) * 5.0) / reach)
				var drop := (_bottom[i] - _top[i]) * 0.82 * t
				_top[i] = maxf(_top[i], _top_orig[i] + drop)


## Shade on the high ground that rolls down into a grass slope (it shows the meadow through).
func _shade_tapered_ends(l: int, r: int) -> void:
	for i in _top.size():
		if i >= l and i <= r:
			continue
		var t0 := _top_orig[i]
		var t1 := _top[i]
		if t1 - t0 < 1.0:
			continue
		for y in range(int(t0), int(t1) - 1):
			var k := (y - t0) / maxf(t1 - t0, 1.0)
			var b: float = BAYER[(y & 3) * 4 + (i & 3)] / 16.0 - 0.5
			var a := floorf((0.03 + 0.16 * k + b * 0.05) * 24.0) / 24.0
			if a > 0.0:
				_put(i, y, Color(0.04, 0.12, 0.06, a))


## How far a ramp's gully runs back into the high ground, in px.
func _notch_len() -> int:
	return clampi(int(face * 0.6), 10, 28)


## Average top edge and foot (local y) across a ramp's columns.
func _ramp_span(cx: int, half: int) -> Vector2:
	var ta := 0.0
	var ba := 0.0
	var n := 0
	for i in range(maxi(cx - half, 0), mini(cx + half + 1, _top.size())):
		ta += _top_orig[i]
		ba += _bottom[i]
		n += 1
	return Vector2(ta / maxi(n, 1), ba / maxi(n, 1))


## Half width of the gully at local y: full where it meets the face, rounding off to a narrow tip
## at its far end, each side wavering a little on its own.
func _notch_hw(y: float, ta: float, nl: float, half: int, side: int, cx: int) -> float:
	var t := clampf((y - (ta - nl)) / (nl * 0.7), 0.0, 1.0)
	return half * (0.62 + 0.38 * sqrt(t)) + (_noise(cx + side * 17, y, 5) - 0.5) * 1.8


func _stair_pixel(i: int, y: int, u: float, ta: float, sh: float, b: float) -> Color:
	var g := y - (ta - 2.0)
	var j := floori(g / sh)
	var k := g - j * sh  # 0..sh within the step, tread first
	if absf(u) > 0.86:
		return Color(STONE[1] if k > sh - 2.0 else STONE[2])  # the cheek stones either side
	var c: Color
	if k < sh - 3.0:
		c = Color(STONE[4] if _noise(i, y, 3) + b * 0.4 > 0.38 else STONE[3])  # tread
	elif k < sh - 2.0:
		c = Color(STONE[6] if _noise(i + 50, y, 2) > 0.3 else STONE[5])  # worn nosing catching the light
	else:
		c = Color(STONE[2] if k < sh - 1.0 else STONE[1])  # riser, darkest at its foot
	var span := 10.0 + _hash(j, 51) * 6.0
	if fposmod(i + _hash(j, 52) * span, span) < 1.0 and k < sh - 2.0 and k > 0.5:
		c = Color(STONE[2])  # the odd joint between slabs
	if absf(u) > 0.55 and _noise(i, y + 200, 4) > 0.7:
		c = c.lerp(STONE_MOSS, 0.55)
	return c


## Index of the ramp whose floor contains local x (with `margin` px either side), or -1.
func _ramp_index(local_x: float, margin := 0.0) -> int:
	for k in ramps.size():
		var r := ramps[k]
		if absf(local_x - r.x) <= r.y + margin:
			return k
	return -1


## Style of the ramp under a world position (0 slope, 1 stairs), or -1 if not on a ramp.
func ramp_at(world: Vector2) -> int:
	var p := to_local(world)
	var k := _ramp_index(p.x)
	if k < 0:
		return -1
	var i := clampi(int(p.x) - _x0, 0, _top.size() - 1)
	if p.y < _top[i] - _notch_len() - 2.0 or p.y > _bottom[i] + 3.0:
		return -1
	return int(ramps[k].z)


## The face blocks walking: one collision polygon per stretch between ramps.
func _build_collision() -> void:
	var old := get_node_or_null("Walls")
	if old:
		old.free()
	if not collision or _top.is_empty():
		return
	var body := StaticBody2D.new()
	body.name = "Walls"
	add_child(body)
	var cuts := []
	for r in ramps:
		cuts.append(Vector2(r.x - r.y - _x0, r.x + r.y - _x0))
	cuts.sort_custom(func(a, b): return a.x < b.x)
	var spans := []
	var start := 0
	for c in cuts:
		if c.x > start:
			spans.append(Vector2i(start, int(c.x)))
		start = maxi(start, int(c.y) + 1)
	if start < _top.size() - 1:
		spans.append(Vector2i(start, _top.size() - 1))
	# the gully banks: you walk up the floor, not out over the sides
	for r in ramps:
		var cx := int(r.x) - _x0
		var span := _ramp_span(cx, int(r.y))
		var nl := float(_notch_len())
		for side in [-1, 1]:
			var line := PackedVector2Array()
			var outer := PackedVector2Array()
			var y := span.x - nl * 0.62
			while y <= span.x + 3.0:
				var x: float = cx + side * (_notch_hw(y, span.x, nl, int(r.y), side, cx) + 1.0) + _x0
				line.append(Vector2(x, y))
				outer.insert(0, Vector2(x + side * 3.0, y))
				y += 2.0
			line.append_array(outer)
			if line.size() >= 3:
				var bank := CollisionPolygon2D.new()
				bank.polygon = line
				body.add_child(bank)
	for sp in spans:
		var poly := PackedVector2Array()
		var i: int = sp.x
		while true:
			poly.append(Vector2(i + _x0, _top[i] + 2.0))
			if i >= sp.y:
				break
			i = mini(i + 4, sp.y)
		i = sp.y
		while true:
			poly.append(Vector2(i + _x0, _bottom[i] - 1.0))
			if i <= sp.x:
				break
			i = maxi(i - 4, sp.x)
		if poly.size() >= 3:
			var cp := CollisionPolygon2D.new()
			cp.polygon = poly
			body.add_child(cp)


## Called by Terrain while it rebuilds: dirt at both mouths of each ramp, so paths lead to it.
func paint_terrain(t: Terrain) -> void:
	if _top.is_empty():
		return
	for r in ramps:
		if int(r.z) == 2:
			continue  # grass slopes need no path
		var i := clampi(int(r.x) - _x0, 0, _top.size() - 1)
		var top := to_global(Vector2(r.x, _top[i] - _notch_len()))
		var bot := to_global(Vector2(r.x, _bottom[i]))
		for area in [Rect2(top + Vector2(-r.y * 0.8, -14), Vector2(r.y * 1.6, 16)), Rect2(bot + Vector2(-r.y * 0.8, -2), Vector2(r.y * 1.6, 16))]:
			var c0 := t.cell_at(area.position)
			var c1 := t.cell_at(area.end)
			for cy in range(c0.y, c1.y + 1):
				for cx in range(c0.x, c1.x + 1):
					t.paint_ground(Vector2i(cx, cy), Terrain.Kind.DIRT)


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
	var rk := _ramp_index(p.x, 2.0)
	if rk >= 0 and int(ramps[rk].z) != 2 and p.y > _top[i] - _notch_len() - 2 and p.y <= _top[i]:
		return true  # the gully floor of a path or stairs
	if not (p.y > _top[i] - 1 and p.y < _bottom[i] + 1):
		return false
	var k := _ramp_index(p.x, -2.0)
	return not (k >= 0 and int(ramps[k].z) == 2)  # grass slopes grow the meadow's tufts


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
		if _ramp_index(x, 3.0) >= 0:
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

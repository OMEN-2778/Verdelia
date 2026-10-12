class_name MapGenerator
## Makes a random but sensible map from a seed: a cliff splitting the map into a lower and an upper
## level with three ways up (earthen slope, stone stairs, grass slope in random order), a meandering
## river across the lower level feeding a lake with a sandy shore, a pond up top, dirt paths linking
## the spawn to every ramp (with a bridge where they cross water), a tilled field, woods grown from
## noise, and bushes, flowers and rocks scattered in the clearings.
##
## generate() returns the MapData; `points` holds named spots (spawn, ramp feet and tops, bridge,
## lake shore, pond, field) for tours and quests.

const STYLE_HALF := [14, 12, 17]  # half width per ramp style

static var points := {}


static func generate(seed: int, cells := Vector2i(140, 80)) -> MapData:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var m := MapData.create(cells)
	m.name = "随机地图 %d" % seed
	var cp := float(m.cell_px)
	var wpx := cells.x * cp
	var hpx := cells.y * cp
	var noise := FastNoiseLite.new()
	noise.seed = seed
	noise.frequency = 0.012
	noise.fractal_octaves = 3
	var detail := FastNoiseLite.new()
	detail.seed = seed + 7
	detail.frequency = 0.05
	points = {}

	# ---- the cliff and its ramps
	var cliff_top := hpx * rng.randf_range(0.27, 0.33)
	var cpts: Array = []
	var x := 0.0
	while x < wpx:
		cpts.append_array([roundf(x), roundf(cliff_top + rng.randf_range(-14.0, 14.0))])
		x += rng.randf_range(70.0, 110.0)
	cpts.append_array([wpx, roundf(cliff_top + rng.randf_range(-14.0, 14.0))])
	var face := rng.randi_range(34, 44)
	var styles := [0, 1, 2]
	_shuffle(styles, rng)
	var ramps: Array = []
	var ramp_x: Array = []
	for k in 3:
		var rx := roundf(wpx * ([0.18, 0.5, 0.82][k] + rng.randf_range(-0.05, 0.05)))
		ramps.append_array([rx, STYLE_HALF[styles[k]], styles[k]])
		ramp_x.append(rx)
	m.cliffs.append({"points": cpts, "face": face, "seed": rng.randi() % 1000, "ramps": ramps})
	var cliff_y := func(px: float) -> float:
		for k in range(0, cpts.size() - 2, 2):
			if px <= cpts[k + 2] or k + 4 >= cpts.size():
				return lerpf(cpts[k + 1], cpts[k + 3], clampf((px - cpts[k]) / maxf(cpts[k + 2] - cpts[k], 1.0), 0.0, 1.0))
		return cliff_top
	var tops: Array = []
	var feet: Array = []
	for k in 3:
		var rx: float = ramp_x[k]
		tops.append(Vector2(rx, cliff_y.call(rx) - 30.0))
		feet.append(Vector2(rx, cliff_y.call(rx) + face + 16.0))
	points.ramp_tops = tops
	points.ramp_feet = feet
	points.ramp_styles = styles

	# ---- water: a river across the lower level, a lake on it, a pond up top
	var river_y := hpx * rng.randf_range(0.76, 0.82)
	var phase := rng.randf_range(0.0, TAU)
	var lake_c := Vector2(wpx * rng.randf_range(0.3, 0.38), river_y - rng.randf_range(30.0, 50.0))
	if rng.randf() < 0.5:
		lake_c.x = wpx - lake_c.x
	var lake_r := rng.randf_range(48.0, 64.0)
	var pond_c := Vector2(wpx * rng.randf_range(0.3, 0.7), (cliff_top - 80.0) * rng.randf_range(0.45, 0.6))
	for k in 3:
		if absf(pond_c.x - ramp_x[k]) < 60.0:
			pond_c.x += 90.0 if pond_c.x < wpx * 0.5 else -90.0
	var pond_r := rng.randf_range(26.0, 34.0)
	var lake_cells := {}
	for cy in cells.y:
		for cx in cells.x:
			var p := (Vector2(cx, cy) + Vector2(0.5, 0.5)) * cp
			var ry := river_y + sin(p.x * 0.006 + phase) * 26.0 + noise.get_noise_2d(p.x, 900.0) * 30.0
			var hw := 10.0 + 4.0 * (noise.get_noise_2d(p.x, 400.0) + 1.0)
			var wet := absf(p.y - ry) < hw
			var dl := p.distance_to(lake_c) / (lake_r * (1.0 + 0.3 * noise.get_noise_2d(p.x * 2.0, p.y * 2.0)))
			if dl < 1.0:
				wet = true
				lake_cells[Vector2i(cx, cy)] = true
			if p.distance_to(pond_c) / (pond_r * (1.0 + 0.3 * detail.get_noise_2d(p.x, p.y))) < 1.0:
				wet = true
			if wet:
				m.water[m.idx(Vector2i(cx, cy))] = 1
	points.lake = lake_c + Vector2(0, -lake_r - 14.0)
	points.pond = pond_c + Vector2(0, pond_r + 14.0)

	# ---- paths: spawn hub to every ramp foot, ramp tops along the upper level, south over the river
	var hub := Vector2(wpx * rng.randf_range(0.42, 0.58), lerpf(cliff_top + face + 40.0, river_y - 40.0, 0.5))
	if hub.distance_to(lake_c) < lake_r + 40.0:
		hub.x += (lake_r + 50.0) * signf(hub.x - lake_c.x + 0.01)
	m.spawn = hub
	points.spawn = hub
	var path_cells := {}
	for k in 3:
		var foot: Vector2 = feet[k]
		var end := foot if styles[k] != 2 else foot + Vector2(0, 26)  # grass slopes need no path
		_path(m, path_cells, [hub, hub.lerp(end, 0.5) + Vector2(rng.randf_range(-20, 20), rng.randf_range(-16, 16)), end], rng)
	var upper: Array = []
	for k in 3:
		var top: Vector2 = tops[k]
		upper.append(top if styles[k] != 2 else top + Vector2(0, -24))
		if k < 2:
			var nxt: Vector2 = tops[k + 1]
			upper.append(top.lerp(nxt, 0.5) + Vector2(0, -rng.randf_range(20, 50)))
	var segs: Array = []
	for k in upper.size():
		segs.append(upper[k])
	_path(m, path_cells, segs, rng)
	_path(m, path_cells, [upper[2], upper[2] + Vector2(rng.randf_range(-40, 40), -rng.randf_range(60, 90)), Vector2(upper[2].x + rng.randf_range(-60, 60), 0)], rng)
	var south := Vector2(hub.x + rng.randf_range(-40, 40), hpx)
	var crossing := Vector2(lerpf(hub.x, south.x, 0.75), river_y + sin(lerpf(hub.x, south.x, 0.75) * 0.006 + phase) * 26.0)
	_path(m, path_cells, [hub, crossing + Vector2(0, -30), crossing + Vector2(0, 30), south], rng, true)
	points.bridge_south = crossing + Vector2(0, 46)
	points.bridge = crossing

	# ---- sand around part of the lake, a tilled field
	for c in lake_cells:
		for dy in range(-3, 4):
			for dx in range(-3, 4):
				var n: Vector2i = c + Vector2i(dx, dy)
				if m.has_cell(n) and not m.water_at(n) and not path_cells.has(n) and dx * dx + dy * dy <= 9:
					if noise.get_noise_2d(n.x * 20.0, n.y * 20.0) > -0.1:
						m.ground[m.idx(n)] = MapData.Ground.SAND
	var fw := rng.randi_range(10, 15)
	var fh := rng.randi_range(5, 8)
	var field_side := -1.0 if lake_c.x > wpx * 0.5 else 1.0
	var f0 := Vector2i(int((hub.x + field_side * rng.randf_range(110, 170)) / cp) - fw / 2, int(hub.y / cp) - fh / 2 + rng.randi_range(-2, 3))
	var field_ok := true
	for cy in range(f0.y - 1, f0.y + fh + 1):
		for cx in range(f0.x - 1, f0.x + fw + 1):
			var c := Vector2i(cx, cy)
			if not m.has_cell(c) or m.water_at(c) or path_cells.has(c):
				field_ok = false
	if field_ok:
		for cy in range(f0.y, f0.y + fh):
			for cx in range(f0.x, f0.x + fw):
				m.ground[m.idx(Vector2i(cx, cy))] = MapData.Ground.TILLED
		points.field = (Vector2(f0) + Vector2(fw * 0.5, fh + 1.5)) * cp

	# ---- plants
	var placed := {}  # 16 px buckets -> [[pos, spacing]]
	var y := 6.0
	while y < hpx:
		var xx := 6.0
		while xx < wpx:
			var p := Vector2(xx + rng.randf_range(-4, 4), y + rng.randf_range(-4, 4))
			xx += 9.0
			if not _free_spot(m, p, cliff_y, face, ramps, hub):
				continue
			var edge := 1.0 - smoothstep(20.0, 70.0, minf(minf(p.x, wpx - p.x), minf(p.y, hpx - p.y)))
			var forest := noise.get_noise_2d(p.x, p.y) + (0.12 if p.y < cliff_top - 30.0 else -0.08) + edge * 0.45
			var meadow := detail.get_noise_2d(p.x, p.y)
			var item := ""
			var r := rng.randf()
			if forest > 0.22:
				if r < 0.14:
					item = _tree(rng, p.y < cliff_top)
				elif r < 0.24:
					item = "bush:" + ["green", "green", "berry", "flower"][rng.randi() % 4]
			elif forest > 0.05:
				if r < 0.022:
					item = _tree(rng, p.y < cliff_top)
				elif r < 0.07:
					item = "bush:" + ["green", "flower", "pink", "violet", "berry"][rng.randi() % 5]
				elif r < 0.082:
					item = "rock:"
			elif meadow > 0.35 and r < 0.22:
				item = "flower:"
			elif r < 0.006:
				item = "rock:"
			elif r < 0.014:
				item = "bush:" + ["green", "flower"][rng.randi() % 2]
			if item == "":
				continue
			var kind := item.split(":")[0]
			if kind == "tree" and _water_above(m, p, 6):
				continue  # its trunk would stand up across the water in front of it
			var spacing: float = {"tree": 17.0, "bush": 11.0, "rock": 10.0, "flower": 6.0}[kind]
			if _crowded(placed, p, spacing):
				continue
			var id := item.split(":")[1]
			if kind == "flower":
				id = MapWorld.FLOWERS[rng.randi() % MapWorld.FLOWERS.size()]
			m.objects.append({"kind": kind, "id": id, "x": roundf(p.x), "y": roundf(p.y)})
			var key := Vector2i(int(p.x / 16.0), int(p.y / 16.0))
			if not placed.has(key):
				placed[key] = []
			placed[key].append([p, spacing])
		y += 9.0
	return m


static func _tree(rng: RandomNumberGenerator, upper: bool) -> String:
	var pool := ["oak", "oak", "oak", "oak", "oak", "pine", "pine", "pine", "birch", "birch", "sapling"] if upper \
		else ["oak", "oak", "oak", "oak", "birch", "birch", "birch", "sapling", "sapling", "pine", "blossom"]
	return "tree:" + pool[rng.randi() % pool.size()]


## Dirt along a polyline, swelling and narrowing a little; water under it becomes a bridge if allowed.
static func _path(m: MapData, path_cells: Dictionary, pts: Array, rng: RandomNumberGenerator, bridge := false) -> void:
	var cp := float(m.cell_px)
	var walked := 0.0
	var wob := rng.randf_range(0.0, 10.0)
	for k in pts.size() - 1:
		var a: Vector2 = pts[k]
		var b: Vector2 = pts[k + 1]
		var n := maxi(1, int(a.distance_to(b) / 3.0))
		for j in n + 1:
			var p := a.lerp(b, float(j) / n)
			walked += a.distance_to(b) / n
			var r := 7.0 + 2.0 * sin(walked * 0.05 + wob)
			for cy in range(int((p.y - r) / cp) - 1, int((p.y + r) / cp) + 2):
				for cx in range(int((p.x - r) / cp) - 1, int((p.x + r) / cp) + 2):
					var c := Vector2i(cx, cy)
					if not m.has_cell(c) or ((Vector2(c) + Vector2(0.5, 0.5)) * cp).distance_to(p) > r:
						continue
					path_cells[c] = true
					if m.water_at(c):
						if bridge:
							m.passage[m.idx(c)] = MapData.Passage.OPEN
					else:
						m.ground[m.idx(c)] = MapData.Ground.DIRT


## Plants keep off water, paths, sand and fields, the cliff face, the ramps and the spawn.
static func _free_spot(m: MapData, p: Vector2, cliff_y: Callable, face: int, ramps: Array, hub: Vector2) -> bool:
	var cp := float(m.cell_px)
	var c := Vector2i(int(p.x / cp), int(p.y / cp))
	if not m.has_cell(c) or p.distance_to(hub) < 34.0:
		return false
	for dy in range(-2, 3):
		for dx in range(-2, 3):
			var n: Vector2i = c + Vector2i(dx, dy)
			if m.water_at(n):
				return false
			if absi(dx) <= 1 and absi(dy) <= 1 and m.ground_at(n) != MapData.Ground.GRASS:
				return false
	var top: float = cliff_y.call(p.x)
	if p.y > top - 20.0 and p.y < top + face + 42.0:
		return false
	for k in range(0, ramps.size(), 3):
		if absf(p.x - ramps[k]) < ramps[k + 1] + 16.0 and p.y > top - 60.0 and p.y < top + face + 50.0:
			return false
	return true


static func _water_above(m: MapData, p: Vector2, cells_up: int) -> bool:
	var c := Vector2i(int(p.x / m.cell_px), int(p.y / m.cell_px))
	for k in range(1, cells_up + 1):
		for dx in [-1, 0, 1]:
			if m.water_at(c + Vector2i(dx, -k)):
				return true
	return false


static func _crowded(placed: Dictionary, p: Vector2, spacing: float) -> bool:
	var key := Vector2i(int(p.x / 16.0), int(p.y / 16.0))
	for dy in range(-2, 3):
		for dx in range(-2, 3):
			for e in placed.get(key + Vector2i(dx, dy), []):
				if p.distance_to(e[0]) < maxf(spacing, e[1]):
					return true
	return false


static func _shuffle(a: Array, rng: RandomNumberGenerator) -> void:
	for i in range(a.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var t = a[i]
		a[i] = a[j]
		a[j] = t

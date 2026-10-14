class_name MapRoute
## Walking routes on a built MapWorld: an A* grid (one node per cell) that knows what blocks the
## way (water without a bridge, hand-drawn walls, the cliff face outside its ramps, tree trunks,
## bushes, rocks and buildings), so characters can be sent anywhere and find their way round.


static func grid(world: MapWorld) -> AStarGrid2D:
	var d := world.data
	var cp := float(d.cell_px)
	var g := AStarGrid2D.new()
	g.region = Rect2i(Vector2i.ZERO, d.size)
	g.cell_size = Vector2(cp, cp)
	g.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	g.update()
	var decks := MapWorld.deck_cells(d)
	for y in d.size.y:
		for x in d.size.x:
			var c := Vector2i(x, y)
			var p := (Vector2(c) + Vector2(0.5, 0.5)) * cp
			var solid := d.passage_at(c) == MapData.Passage.BLOCKED or (d.passage_at(c) == MapData.Passage.AUTO and d.ground_at(c) == MapData.Ground.VOID)
			if d.water_at(c) and d.passage_at(c) != MapData.Passage.OPEN and not decks.has(c):
				solid = true
			if not solid:
				solid = _in_cliff(world, p)
			g.set_point_solid(c, solid)
	for o in d.objects:
		if o.kind == "flower":
			continue
		if o.kind == "building":
			if not WorldBuilding.is_solid(o.id):
				continue
			for part: Rect2 in WorldBuilding.solid_rects_of(o.id):
				var hr := Rect2(part.position + Vector2(o.x, o.y), part.size)
				for y in range(floori(hr.position.y / cp), ceili(hr.end.y / cp)):
					for x in range(floori(hr.position.x / cp), ceili(hr.end.x / cp)):
						if g.is_in_boundsv(Vector2i(x, y)):
							g.set_point_solid(Vector2i(x, y), true)
			continue
		var base := Vector2(o.x, o.y)
		var r := 7.0 if o.kind == "tree" else 6.0
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				var c := Vector2i(int(base.x / cp) + dx, int((base.y - 2.0) / cp) + dy)
				if g.is_in_boundsv(c) and ((Vector2(c) + Vector2(0.5, 0.5)) * cp).distance_to(base) < r:
					g.set_point_solid(c, true)
	return g


## Cell on the cliff face, its banks or the edge of a ramp (the middle of a ramp is open).
static func _in_cliff(world: MapWorld, p: Vector2) -> bool:
	var cliffs := world.cliff_nodes()
	for i in cliffs.size():
		var cb: CliffBand = cliffs[i]
		if cb.texture == null:
			continue
		var top := cb.top_at(p.x)
		var bottom := cb.bottom_at(p.x)
		var ramps: Array = world.data.cliffs[i].get("ramps", [])
		for k in range(0, ramps.size(), 3):
			if absf(p.x - ramps[k]) <= ramps[k + 1] + 4.0 and p.y > top - 34.0 and p.y < bottom + 6.0:
				return absf(p.x - ramps[k]) > ramps[k + 1] - 5.0
		if p.y > top - 3.0 and p.y < bottom + 3.0:
			return true
	return false


## A walking route through `stops` (world px), as waypoints at the turns.
static func plan(world: MapWorld, stops: Array) -> PackedVector2Array:
	var g := grid(world)
	var cp := float(world.data.cell_px)
	var out := PackedVector2Array()
	for k in stops.size() - 1:
		var a := _open_near(g, Vector2i((stops[k] as Vector2) / cp))
		var b := _open_near(g, Vector2i((stops[k + 1] as Vector2) / cp))
		var cells := g.get_id_path(a, b, true)
		var prev_dir := Vector2i(99, 99)
		for i in cells.size():
			var dir := cells[mini(i + 1, cells.size() - 1)] - cells[i]
			if i == 0 or i == cells.size() - 1 or dir != prev_dir:
				out.append((Vector2(cells[i]) + Vector2(0.5, 0.5)) * cp)
			prev_dir = dir
	return out


static func _open_near(g: AStarGrid2D, c: Vector2i) -> Vector2i:
	c = c.clamp(g.region.position, g.region.end - Vector2i.ONE)
	for r in 6:
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				var n := c + Vector2i(dx, dy)
				if g.is_in_boundsv(n) and not g.is_point_solid(n):
					return n
	return c

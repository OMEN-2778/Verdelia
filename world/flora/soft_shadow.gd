class_name SoftShadow
## Cached pixel-art contact shadows: a dithered ellipse that fades toward its rim.

static var _cache := {}
const BAYER := [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]


static func texture(w: int, h: int, alpha := 0.32) -> ImageTexture:
	w = maxi(w, 3)
	h = maxi(h, 2)
	var key := Vector3i(w, h, int(alpha * 100))
	if _cache.has(key):
		return _cache[key]
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	var c := Color(0.06, 0.18, 0.1)
	for y in h:
		for x in w:
			var dx := (x + 0.5 - w / 2.0) / (w / 2.0)
			var dy := (y + 0.5 - h / 2.0) / (h / 2.0)
			var d := dx * dx + dy * dy
			if d > 1.0:
				continue
			var a := alpha * (1.0 if d < 0.55 else 0.55)
			if d > 0.8 and BAYER[(y & 3) * 4 + (x & 3)] < 8:
				continue  # dithered rim
			img.set_pixel(x, y, Color(c, a))
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex


static func sprite(w: int, h: int, offset_x := 0.0) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = texture(w, h)
	s.position = Vector2(roundf(offset_x), 0)
	s.z_as_relative = false
	s.z_index = -6
	return s

extends Node2D
## Builds the Stardust-Vale-style farm from art/vale/layout.json: y-sorted trees and ruin
## pillars, the living grass, and the placeholder protagonist.

const ART := "res://art/vale"
const LEAF := preload("res://art/vale/fx/leaf.png")

var LEAF_FADE := _fade()


static func _fade() -> Gradient:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.1, 0.8, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color.WHITE, Color.WHITE, Color(1, 1, 1, 0)])
	return g

@onready var props: Node2D = $Props
@onready var tufts: Node2D = $Tufts
@onready var player: Node2D = $Props/Player


func _ready() -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ART + "/layout.json"))
	for t: Dictionary in layout.trees:
		var tree := Node2D.new()
		tree.position = Vector2(t.x, t.y)
		var anchor := Vector2(-t.ax, -t.ay)
		var i := int(t.i)
		tree.add_child(_sprite("%s/props/trees/tree_%d_trunk.png" % [ART, i], anchor))
		var k := 0
		for layer: Dictionary in t.layers:
			var crown := _sprite("%s/props/trees/%s" % [ART, layer.f], anchor)
			crown.set_script(preload("res://scripts/vale/tree_crown.gd"))
			crown.phase = float(t.ph) + k * 0.9  # neighbouring clumps move out of step
			crown.amount = layer.sway
			tree.add_child(crown)
			k += 1
		tree.add_child(_leaves(t))
		props.add_child(tree)
	for p: Dictionary in layout.pillars:
		var pillar := Node2D.new()
		pillar.position = Vector2(p.x, p.y)
		pillar.add_child(_sprite("%s/props/pillar_%d.png" % [ART, int(p.v)], Vector2(-8, -36)))
		props.add_child(pillar)
	tufts.setup(layout.tufts, layout.tuft_colours)
	player.position = Vector2(layout.player[0], layout.player[1])


func _leaves(t: Dictionary) -> CPUParticles2D:
	## A few leaves (petals for blossom trees) drifting down from the crown.
	var p := CPUParticles2D.new()
	var r: Array = t.crown
	p.position = Vector2((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2((r[2] - r[0]) / 2.6, (r[3] - r[1]) / 3.0)
	p.texture = LEAF
	p.amount = 3 if t.kind != "blossom" else 6
	p.lifetime = 6.0
	p.preprocess = 6.0
	p.randomness = 1.0
	p.direction = Vector2(1, 0.4)
	p.spread = 35.0
	p.gravity = Vector2(5, 9)
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 7.0
	p.angular_velocity_min = -120.0
	p.angular_velocity_max = 120.0
	p.color = Color(t.leaf)
	p.color_ramp = LEAF_FADE
	p.z_index = 5
	return p


func _sprite(path: String, offset: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = load(path)
	s.centered = false
	s.position = offset
	return s

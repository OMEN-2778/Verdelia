extends Node2D
## Builds the Stardust-Vale-style farm from art/vale/layout.json: y-sorted trees and ruin
## pillars, the living grass, and the placeholder protagonist.

const ART := "res://art/vale"

@onready var props: Node2D = $Props
@onready var tufts: Node2D = $Tufts
@onready var player: Node2D = $Props/Player


func _ready() -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ART + "/layout.json"))
	for t: Dictionary in layout.trees:
		var tree := Node2D.new()
		tree.position = Vector2(t.x, t.y)
		var v := int(t.v)
		tree.add_child(_sprite("%s/props/tree_trunk_%d.png" % [ART, v], Vector2(-23, -55)))
		var crown := _sprite("%s/props/tree_crown_%d.png" % [ART, v], Vector2(-23, -55))
		crown.set_script(preload("res://scripts/vale/tree_crown.gd"))
		crown.phase = t.ph
		tree.add_child(crown)
		props.add_child(tree)
	for p: Dictionary in layout.pillars:
		var pillar := Node2D.new()
		pillar.position = Vector2(p.x, p.y)
		pillar.add_child(_sprite("%s/props/pillar_%d.png" % [ART, int(p.v)], Vector2(-8, -36)))
		props.add_child(pillar)
	tufts.setup(layout.tufts, layout.tuft_colours)
	player.position = Vector2(layout.player[0], layout.player[1])


func _sprite(path: String, offset: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = load(path)
	s.centered = false
	s.position = offset
	return s

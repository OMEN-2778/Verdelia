#!/bin/sh
# Walks around a map made with the editor: ./play_map.sh maps/sample.json
cd "$(dirname "$0")/../.." && exec "${GODOT:-godot}" --path . res://scenes/map_play.tscn -- --map="$(realpath "${1:-maps/sample.json}")"

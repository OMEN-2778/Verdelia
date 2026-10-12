#!/bin/sh
# Opens the Verdelia map editor. Needs Godot 4.7 on the PATH (or set GODOT=/path/to/godot).
cd "$(dirname "$0")/../.." && exec "${GODOT:-godot}" --path . res://scenes/editor/map_editor.tscn

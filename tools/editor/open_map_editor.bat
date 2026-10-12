@echo off
rem Opens the Verdelia map editor. Set GODOT to your Godot 4.7 exe if it is not on the PATH.
if "%GODOT%"=="" set GODOT=godot
cd /d "%~dp0\..\.."
"%GODOT%" --path . res://scenes/editor/map_editor.tscn

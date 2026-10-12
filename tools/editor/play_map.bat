@echo off
rem Walks around a map made with the editor: play_map.bat maps\sample.json
if "%GODOT%"=="" set GODOT=godot
set MAP=%~f1
if "%MAP%"=="" set MAP=%~dp0..\..\maps\sample.json
cd /d "%~dp0\..\.."
"%GODOT%" --path . res://scenes/map_play.tscn -- --map="%MAP%"

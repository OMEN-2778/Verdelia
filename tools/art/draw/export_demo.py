#!/usr/bin/env python3
"""Export the mock-up farm as separate layers and generate scenes/farm_demo.tscn.

Layers: water (with ripple shader), ground (grass/dirt/tilled), props (y-sorted, plants sway),
lights for magic plants, sun shafts, pollen/petal particles, day cycle and a full-screen grade.

    python3 tools/art/draw/export_demo.py
"""
from PIL import Image

import scene
from common import ROOT, save

SWAY = {"tree": 1.2, "bush": 0.7, "turnip": 0.6, "lumen": 0.8, "weed": 0.9, "glow_flower": 0.8}
LIGHTS = {"lumen_2": ("ffd98a", 0.9), "lumen_1": ("c9b3ff", 0.5), "lumen_0": ("c9b3ff", 0.35), "glow_flower": ("bfe6ff", 0.8)}


def export_art():
    ground = scene.render(scene.MAP, water=False, props=False)
    water = scene.render(scene.MAP, water=True, props=False)
    save(ground, "demo/ground.png")
    save(water, "demo/water.png")
    names = {}
    for _anchor, name, sprite in scene.prop_list():
        if name not in names:
            names[name] = sprite
            save(sprite, f"demo/props/{name}.png")
    pollen = Image.new("RGBA", (2, 2), (250, 240, 200, 255))
    pollen.putpixel((1, 1), (250, 240, 200, 120))
    save(pollen, "demo/fx/pollen.png")
    petal = Image.new("RGBA", (3, 2), (0, 0, 0, 0))
    for x, y, a in ((0, 0, 255), (1, 0, 255), (1, 1, 255), (2, 1, 200)):
        petal.putpixel((x, y), (236, 190, 196, a))
    save(petal, "demo/fx/petal.png")
    return ground.size, names


def tscn(size, names, props=None, out_path="scenes/farm_demo.tscn", art_dir="res://art/demo",
         water=True, extra_ext=(), extra_nodes=(), grade=None):
    """Write a demo scene. props: [((x, y), name, sprite)]; textures live at {art_dir}/props/{name}.png."""
    props = scene.prop_list() if props is None else props
    w, h = size
    ext, sub, nodes = [], [], []

    def ext_res(kind, path, rid):
        ext.append(f'[ext_resource type="{kind}" path="{path}" id="{rid}"]')
        return rid

    ext_res("Shader", "res://shaders/grade.gdshader", "grade")
    ext_res("Shader", "res://shaders/sway.gdshader", "sway")
    ext_res("Shader", "res://shaders/water.gdshader", "water")
    ext_res("Script", "res://scripts/day_cycle.gd", "day_cycle")
    ext_res("Script", "res://scripts/idle_bob.gd", "idle_bob")
    ext_res("Script", "res://scripts/light_shaft.gd", "light_shaft")
    ext_res("Texture2D", f"{art_dir}/ground.png", "ground")
    if water:
        ext_res("Texture2D", f"{art_dir}/water.png", "water_tex")
    ext_res("Texture2D", "res://art/demo/fx/pollen.png", "pollen")
    ext_res("Texture2D", "res://art/demo/fx/petal.png", "petal")
    for name in names:
        ext_res("Texture2D", f"{art_dir}/props/{name}.png", f"prop_{name}")
    ext.extend(extra_ext)

    sub.append("""[sub_resource type="Gradient" id="sky"]
offsets = PackedFloat32Array(0, 0.2, 0.28, 0.5, 0.7, 0.78, 0.86, 1)
colors = PackedColorArray(0.42, 0.46, 0.7, 1, 0.5, 0.52, 0.72, 1, 1, 0.88, 0.84, 1, 1, 0.99, 0.95, 1, 1, 0.9, 0.74, 1, 0.92, 0.66, 0.6, 1, 0.5, 0.5, 0.72, 1, 0.42, 0.46, 0.7, 1)""")
    sub.append("""[sub_resource type="FastNoiseLite" id="cloud_noise"]
frequency = 0.012
fractal_octaves = 3""")
    sub.append("""[sub_resource type="NoiseTexture2D" id="cloud_tex"]
width = 256
height = 256
seamless = true
noise = SubResource("cloud_noise")""")
    sub.append("""[sub_resource type="ShaderMaterial" id="grade_mat"]
shader = ExtResource("grade")
shader_parameter/cloud_noise = SubResource("cloud_tex")""" + "".join(
        f"\nshader_parameter/{k} = {v}" for k, v in (grade or {}).items()))
    sub.append("""[sub_resource type="ShaderMaterial" id="water_mat"]
shader = ExtResource("water")""")
    for kind, amount in SWAY.items():
        sub.append(f"""[sub_resource type="ShaderMaterial" id="sway_{kind}"]
shader = ExtResource("sway")
shader_parameter/amount = {amount}""")
    sub.append("""[sub_resource type="Gradient" id="light_falloff"]
offsets = PackedFloat32Array(0, 0.35, 1)
colors = PackedColorArray(1, 1, 1, 1, 1, 1, 1, 0.45, 1, 1, 1, 0)""")
    sub.append("""[sub_resource type="GradientTexture2D" id="light_tex"]
gradient = SubResource("light_falloff")
width = 64
height = 64
fill = 1
fill_from = Vector2(0.5, 0.5)
fill_to = Vector2(1, 0.5)""")
    sub.append("""[sub_resource type="CanvasItemMaterial" id="additive"]
blend_mode = 1""")
    sub.append("""[sub_resource type="Gradient" id="particle_fade"]
offsets = PackedFloat32Array(0, 0.2, 0.8, 1)
colors = PackedColorArray(1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0)""")

    nodes.append('[node name="FarmDemo" type="Node2D"]')
    nodes.append(f"""[node name="DayCycle" type="CanvasModulate" parent="."]
script = ExtResource("day_cycle")
cycle_seconds = 24.0
start_time = 0.32
sky = SubResource("sky")""")
    if water:
        nodes.append("""[node name="Water" type="Sprite2D" parent="."]
material = SubResource("water_mat")
texture = ExtResource("water_tex")
centered = false""")
    nodes.append("""[node name="Ground" type="Sprite2D" parent="."]
texture = ExtResource("ground")
centered = false""")
    nodes.extend(extra_nodes)  # between the ground and the y-sorted props
    nodes.append('[node name="Props" type="Node2D" parent="."]\ny_sort_enabled = true')
    counts = {}
    for (bx, by), name, sprite in props:
        counts[name] = counts.get(name, 0) + 1
        node = f"{name}_{counts[name]}"
        kind = next((k for k in SWAY if name.startswith(k)), None)
        lines = [f'[node name="{node}" type="Sprite2D" parent="Props"]']
        if kind:
            lines.append(f'material = SubResource("sway_{kind}")')
        lines += [f"position = Vector2({bx}, {by})", f'texture = ExtResource("prop_{name}")',
                  f"offset = Vector2(0, {-sprite.height / 2})"]
        if name == "protagonist":
            lines.append('script = ExtResource("idle_bob")')
        nodes.append("\n".join(lines))
        if name in LIGHTS:
            colour, scale = LIGHTS[name]
            r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
            nodes.append(f"""[node name="{node}_light" type="PointLight2D" parent="Props/{node}" groups=["night_lights"]]
position = Vector2(0, {-sprite.height * 0.55:.0f})
color = Color({r:.3f}, {g:.3f}, {b:.3f}, 1)
texture = SubResource("light_tex")
texture_scale = {scale}""")

    shafts = [(250, 70, 26), (300, 60, 18), (40, 30, 20)]
    nodes.append('[node name="SunShafts" type="Node2D" parent="."]\nz_index = 10')
    for i, (x, width, slant) in enumerate(shafts):
        nodes.append(f"""[node name="Shaft{i}" type="Polygon2D" parent="SunShafts" node_paths=PackedStringArray("day_cycle")]
material = SubResource("additive")
polygon = PackedVector2Array({x}, -10, {x + width}, -10, {x + width - slant * 4}, {h + 10}, {x - slant * 4}, {h + 10})
vertex_colors = PackedColorArray(1, 0.95, 0.8, 0.22, 1, 0.95, 0.8, 0.22, 1, 0.95, 0.8, 0, 1, 0.95, 0.8, 0)
script = ExtResource("light_shaft")
day_cycle = NodePath("../../DayCycle")""")

    for name, tex, amount, gravity, colour in (
        ("Pollen", "pollen", 40, "Vector2(4, 2)", "Color(1, 0.97, 0.85, 0.9)"),
        ("Petals", "petal", 10, "Vector2(6, 5)", "Color(1, 1, 1, 1)"),
    ):
        nodes.append(f"""[node name="{name}" type="CPUParticles2D" parent="."]
z_index = 11
position = Vector2({w / 2}, {h / 2})
amount = {amount}
lifetime = 9.0
preprocess = 9.0
texture = ExtResource("{tex}")
emission_shape = 3
emission_rect_extents = Vector2({w / 2 + 20}, {h / 2 + 10})
direction = Vector2(1, 0.3)
spread = 40.0
gravity = {gravity}
initial_velocity_min = 2.0
initial_velocity_max = 6.0
angular_velocity_min = -40.0
angular_velocity_max = 40.0
color = {colour}
color_ramp = SubResource("particle_fade")""")

    nodes.append('[node name="Grade" type="CanvasLayer" parent="."]')
    nodes.append("""[node name="Screen" type="ColorRect" parent="Grade"]
material = SubResource("grade_mat")
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
mouse_filter = 2""")
    nodes.append(f"""[node name="Camera" type="Camera2D" parent="."]
position = Vector2({w / 2}, {h / 2})""")

    out = [f"[gd_scene load_steps={len(ext) + len(sub) + 1} format=3]", ""]
    out += ext + [""] + "\n\n".join(sub).split("\n") + [""] + "\n\n".join(nodes).split("\n")
    path = ROOT / out_path
    path.write_text("\n".join(out) + "\n")
    return path


if __name__ == "__main__":
    size, names = export_art()
    print(tscn(size, names).relative_to(ROOT))

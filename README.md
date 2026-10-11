# Verdelia · 维尔德莉亚

像素风种田 + 动作战斗 + 光魔法法阵的 Demo（茵菲谷篇）。引擎：Godot 4.7。

## 开发环境

| 内容 | 位置 | 作用 |
|---|---|---|
| Godot 4.7.2 | `scripts/setup-dev-env.sh` | 安装 Godot 编辑器 / 无头运行（Linux）。其他系统到 godotengine.org 下载 |
| GodotPrompter 插件 | `.claude/settings.json` | Godot 4 的 50+ 个 skill（状态机、存档、对话、背包、相机、着色器、粒子、UI、测试等）和 9 个 agent |
| Anthropic document-skills / example-skills | `.claude/settings.json` | 读写 docx/xlsx/pdf 设计文档，skill-creator 等 |
| 游戏设计与像素美术 skill | `.claude/skills/` | pixel-art、pixel-art-sprites、game-design、narrative-design、combat-design、level-design、game-ui-design、game-audio、animation-systems、shader-programming（来自 omer-metin/skills-for-antigravity，Apache-2.0） |
| Godot MCP | `.mcp.json` | 让 Claude 启动编辑器、运行项目、读取调试输出、创建场景和节点（需要 `godot` 在 PATH 上） |

在 Claude Code 里打开本仓库时会提示信任项目插件和 `.mcp.json` 里的 MCP 服务器，确认即可。

## 美术工具

- `art/palette/verdelia.gpl`（及色板预览 `.png`）：项目调色板（`sunlit` 预设），14 条色阶 × 6 级 + 描边色和纸色。方向是“明媚但不卡通”：低饱和、偏自然的色相，暗部提亮，阴影偏紫、高光偏暖。可直接导入 Aseprite / LibreSprite / GIMP。
- `tools/art/pixeltool.py`：把第三方素材统一到项目调色板。
  - `remap in.png out.png --selout`：按 OKLab 最近色映射到调色板，并把黑描边改成只比底色深一两级的柔和描边（selout）。`--preset vivid` 是之前的高饱和版本，只留作对比。
  - `preview in.png --after out.png -o cmp.png`：放大并排对比。
  - `palette art/palette/verdelia`：修改色阶后重新生成调色板。
- `docs/art/palette-remap-demo.png`：效果演示，左边是原图，右边是处理后。原图是 Kenney 的 Tiny Battle（CC0）。

## 自绘美术（第一版）

全部素材由 `tools/art/draw/` 里的脚本逐像素绘制，颜色只取项目调色板。修改脚本后运行 `python3 tools/art/draw/build.py` 重新生成。

- `art/tiles/terrain_base.png`：草地（含花）、泥土、耕地纹理、水（可循环）
- `art/tiles/*_over.png`：草地盖泥土、泥土岸盖水、干/湿耕地。都是 4×4 的 dual-grid 过渡表，瓦片编号 = 左上×1 + 右上×2 + 左下×4 + 右下×8（该角是否属于上层地形），显示时相对逻辑格偏移半格
- `art/sprites/props.png`：萝卜 4 个生长阶段、光种花 3 个阶段、发光花、杂草 ×2、石头 ×2、篱笆
- `art/sprites/tree.png`、`bush.png`、`protagonist_front.png`（主角正面站立，16×32）
- `docs/art/farm-mockup.png`：拼起来的农场场景示意

## Godot 演示场景：光影与场景动效

`scenes/farm_demo.tscn`（主场景），用 Godot 4.7 打开即可运行。由 `tools/art/draw/export_demo.py` 生成，素材换成 Mana Seed 等正式素材时替换 `art/demo/` 里的图层即可。

- `shaders/grade.gdshader`：全屏调色，包括降对比、提亮暗部、暖色、泛光、漂移的云影和暗角。参数都能在检查器里实时调
- `shaders/sway.gdshader`：树、灌木、作物随风摇摆，相邻植物相位不同
- `shaders/water.gdshader`：水面按整像素波动，带闪烁的高光
- `scripts/day_cycle.gd`：昼夜循环（演示里 24 秒一天）。天黑后 `night_lights` 组里的灯会亮起（光种花、发光花）
- 光柱（加色混合，天黑渐隐）、花粉和花瓣粒子、主角呼吸待机
- 效果录像：`docs/art/farm-demo-daycycle.mp4` / `.gif`，四个时段截图：`docs/art/farm-demo-times.png`

素材本身也能离线柔化：`python3 tools/art/pixeltool.py soften in.png out.png --contrast 0.85 --lift 0.04 --chroma 0.9`。按颜色逐个处理，像素保持清晰。

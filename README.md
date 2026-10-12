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

## Mana Seed 试用素材演示

`scenes/manaseed_demo.tscn` 用 Mana Seed 夏季森林的免费样本拼成，加上和上面相同的光影与动效。洞口夜里会透出紫光。

Mana Seed 的许可禁止二次分发，而本仓库是公开的，所以素材原图和由它合成的图层都放在被 git 忽略的 `art/vendor/` 里，不提交。新环境里要先把素材放回 `art/vendor/manaseed/`，再运行：

    python3 tools/art/draw/manaseed_demo.py --soften   # 降对比后拼图，生成 art/vendor/demo/ 和场景文件

## 世界系统（主场景 `scenes/vale_demo.tscn`）

画法移植自 [stardust-vale](https://github.com/OMEN-2778/stardust-vale)，做成了可以在任意大小的地图上复用的节点。演示地图 960×480，镜头跟随角色走一圈：`docs/art/world-demo.mp4`。

| 节点 | 作用 | 怎么用 |
|---|---|---|
| `Terrain`（`world/terrain/`） | 整张地图的地面：抖动草地、泥路、耕地、湿耕地，由 `ground.gdshader` 实时绘制，没有瓦片接缝 | 加一个 TileMapLayer，tile_set 选 `terrain_brushes.tres`，用 泥路 / 耕地 / 浇水 / 擦除 四种刷子画，地面立刻更新；也可以给 `mask` 一张 RGBA 图（R=泥 G=耕 B=湿，每像素一格）。游戏里锄地、浇水调用 `set_cell(cell, Terrain.Kind.TILLED)` |
| `GrassField`（`world/grass/`） | 会动的草：随风摆、阵风时草尖发亮、被角色推开、开花；路边自动变稀，耕地上长幼苗 | 指定 `terrain` 和 `player`。按 128px 分块批量渲染，大地图也不卡；地形一变只重建受影响的块 |
| `WorldTree`（`world/flora/`） | 素材库里的树（oak / birch / pine / blossom / sapling / oak_far / pine_far），叶团分层摆动、阵风发亮、落叶或落花、柔和投影、树根长草 | 放在树干底部，选 `species`；`variant` = -1 时按位置自动挑变体 |
| `WorldProp` | 任意单图物件：灌木、石头、遗迹、树桩、花 | 设 `texture`，或用 `library_item` = `bush:green` / `rock`。物件底部会自动长一圈草来过渡：小物件配短草，大物件配高草，前排草盖住物件底边；物件下方不长草 |
| `Scatter` | 在矩形或多边形区域里批量散布上面这些 | `items` 写 `tree:oak`、`bush:flower`、`rock`、`prop:res://….png@sway=0.5@shadow=0`，配上 `weights`、`count`、`min_distance`、`clearance`（离路和田的距离）。点检查器里的 `generate` 就会摆好，摆完还可以手动调整 |
| `CliffBand`（`world/cliff/`） | 沿折线生成的岩壁：高度起伏、岩刺和凹槽、不规则岩层、风化和裂缝、零星的垂草和藤蔓、崖脚碎石，崖脚自动长一排高草 | `points` 是岩壁顶边，`openings` 是洞口（中心 x, 半宽） |

素材库由 `tools/art/vale/library.py` 生成（`flora.py` 是树、灌木、石头的生成器），输出到 `art/library/`：46 棵树、20 丛灌木、8 块石头、53 种草丛。改了生成器后重新运行这个脚本即可。

第三方素材：`art/third_party/grassland/` 来自上传的 *Grassland Top Down Tileset Pixel Art*。用 `tools/art/vale/grassland.py <解压目录>` 导入，导入时会把绿色微调到草地色调。演示场景用到了里面的遗迹、石堆、开花灌木、树桩和花。

旧版的一次性烘焙演示（`art/vale`、`scripts/vale`）已经被这套系统取代并删除。

## 水体（演示场景 `scenes/water_demo.tscn`）

水只有一种：湖、池塘、河、溪、水坑都是同一种水体，区别只在轮廓形状。所有水画进 `Terrain` 的水数据，再由一个 `WaterLayer` 统一绘制，相邻或重叠的水面会连成一片。演示视频：`docs/art/water-demo.mp4`；截图：`water-waterfall.png`、`water-pond.png`、`water-stream.png`、`water-beach.png`。

| 节点 | 作用 | 怎么用 |
|---|---|---|
| `WaterLayer`（`world/water/`） | 绘制所有水面：统一的深蓝色，几条素净的白线缓缓漂移，近岸有细细的焦散光纹 | 每张地图放一个，指定 `terrain`。材质参数：`water_color`（水色）；波纹线的 `drift`（漂移方向和速度）、`line_density`（多少）、`line_spacing`、`line_length`、`line_life`、`line_opacity`；焦散的 `caustic_strength`、`caustic_size`、`caustic_reach`（离岸多远还能看到）、`caustic_speed` |
| `WaterBody` | 任意一块水 | 加一个名为 `Shape` 的 Polygon2D 子节点画轮廓（或直接填 `polygon`）。河就画成长条形。`shore` 选岸：`GRASS` 草岸（深色岸线）、`SAND` 沙岸（宽度由 `beach_width` 决定，水边是湿沙）、`ROCK` 石岸（沿岸放 `rocks` 块半浸水的石头）、`SAND_AND_ROCK` 两者都有 |
| `Waterfall` | 岩壁上的瀑布 | 指定 `cliff`（一个 CliffBand），瀑布会自动贴到崖顶、高度取岩壁高度；不指定时用 `height`。`width`、`speed` 可调，`mist` 开关水雾。瀑布周围不长草 |

画水的其他方式：

- 地面刷子里有一个"水"刷子；擦除刷子也会擦掉水。
- 可以给 `Terrain.water_mask` 一张灰度图，白色的格子就是水。
- 游戏里挖水用 `set_cell(cell, Terrain.Kind.WATER)`，填回草地用 `Kind.GRASS`。
- `Kind.SAND` 是沙地。
- `Terrain.water_at(世界坐标)` 返回 0–1，表示这个位置有多少水。

草、`Scatter` 散布的树和石头都会避开水面；水边一圈长矮草过渡。

更新记录见 [CHANGELOG.md](CHANGELOG.md)。

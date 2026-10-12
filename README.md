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
| `CliffBand`（`world/cliff/`） | 沿折线生成的岩壁：高度起伏、岩刺和凹槽；柔和的泥土质感，没有深色线条，岩层只体现为互相融合的深浅色调；零星的垂草和藤蔓，崖脚自动长一排高草 | `points` 是岩壁顶边，`openings` 是洞口（中心 x, 半宽） |

素材库由 `tools/art/vale/library.py` 生成（`flora.py` 是树、灌木、石头的生成器），输出到 `art/library/`：46 棵树、20 丛灌木、8 块石头、53 种草丛。改了生成器后重新运行这个脚本即可。

第三方素材：`art/third_party/grassland/` 来自上传的 *Grassland Top Down Tileset Pixel Art*。用 `tools/art/vale/grassland.py <解压目录>` 导入，导入时会把绿色微调到草地色调。演示场景用到了里面的遗迹、石堆、开花灌木、树桩和花。

旧版的一次性烘焙演示（`art/vale`、`scripts/vale`）已经被这套系统取代并删除。

## 地图编辑器（`scenes/editor/map_editor.tscn`）

独立的画图界面：用笔刷在地图上画地面、水体、植被和岩壁，画完直接试玩。截图：`docs/art/map-editor.png`（编辑界面）、`docs/art/map-editor-walkable.png`（显示通行范围）、`docs/art/map-play.png`（试玩）。

**打开方式**：装好 Godot 4.7 后运行 `tools/editor/open_map_editor.sh`（Windows 用 `.bat`），或在 Godot 编辑器里打开 `scenes/editor/map_editor.tscn` 按 F6。

**图层和笔刷**

| 图层 | 笔刷 |
|---|---|
| 地面 | 草地、土路、沙地、耕地、湿耕地；边缘自动柔和过渡 |
| 水体 | 水；画出的水自动连成一片，越往中间越深 |
| 植被 | 混合树林、阔叶树、白桦、松树、花树、小树苗、远景树、五种灌木、石头、野花、灌木丛。笔刷大小为 1 时单击放一棵；大一点的笔刷按"密度"撒一片，自动避开水和岩壁、保持间距 |
| 岩壁 | 画岩壁：按住左键横着拖出岩壁顶边，高度用"岩壁高度"调。土坡、石阶、草坡：在岩壁上单击开一个坡道，宽度随笔刷大小 |
| 通行 | 阻挡：画看不见的墙。木桥：在水面上铺一座能走的木桥。出生点：试玩和游戏开始时角色出现的位置 |

**形状**：圆形、方形、菱形、横椭圆、竖椭圆、喷枪（随机散点）、直线（按下拖到终点）、矩形（拖出对角）、填充（把相连的同类区域整片换掉）。

**橡皮擦**：右键直接擦，或打开"橡皮擦"开关（快捷键 E）。地面擦回草地，水擦掉，植被删除笔刷范围内的植物和石头，岩壁上先删坡道、再删整条岩壁，通行恢复成自动判断。

**其他**：撤销/重做（Ctrl+Z / Ctrl+Y，可撤 60 步）、新建（设置地图大小）、打开、保存、另存为（地图存成 `.json` 文件，默认放在 `maps/`）；中键或空格+拖动平移，滚轮缩放，方向键也能平移，`[` `]` 调笔刷大小。

**能走哪里**：不用另外画，按画的内容自动判断。
- 水不能走，岸边一圈浅水可以踩。
- 岩壁只能从坡道上下。
- 树只挡树干，灌木和石头只挡底部，可以从树冠下、石头后面走过。
- 木桥能走，"阻挡"画的地方不能走。

打开"显示通行范围"会用红色标出所有不能走的地方。点"▶ 试玩"直接在当前地图上走一走（WASD 或方向键，Esc 返回）。

**在游戏里用**：`scenes/map_play.tscn` 读取一张地图文件并让角色在里面走，默认读 `maps/sample.json`（用编辑器的笔刷画的示例地图）。也可以运行 `tools/editor/play_map.sh 地图.json`。代码里用 `MapWorld.load_map(路径)` 生成整张地图。

| 文件 | 作用 |
|---|---|
| `world/map/map_data.gd` | 地图文件格式：地面、水、通行三张格子图，植物和石头的列表，岩壁和坡道，出生点 |
| `world/map/map_world.gd` | 按地图数据生成地面、水、草、树木、岩壁、木桥和碰撞；编辑器通过它实时修改 |
| `world/map/passability_overlay.gd` | 显示通行范围 |
| `world/map/bridge_layer.gd` | 画木桥 |
| `world/editor/map_editor.gd` | 编辑器界面和笔刷 |

## 坡道、台阶和行走（演示场景 `scenes/cliff_demo.tscn`）

岩壁可以劈开，做成通往上一层地面的土坡、石阶或草坡，角色只能从这些口子上下。演示视频：`docs/art/cliff-ramps.mp4`（角色先撞上岩壁被挡住，再从土坡走上去，从石阶下来，又从草坡走上去，再从土坡下来）；三种坡道的特写：`docs/art/cliff-ramps.png`。

| 节点 | 作用 | 怎么用 |
|---|---|---|
| `CliffBand.ramps` | 在岩壁上劈开坡道。土坡是一条自然的土路，上亮下暗，有零星的小土坎，边缘长草；石阶是一级级石板台阶，台阶前沿被磨亮，两侧有石块，带橄榄色青苔；草坡没有路，直接露出草地本身（同一片地面、同样的草丛随风摆动），只在上面叠一层往下渐深的阴影，两端淡出，和草地之间没有接缝。所有绿色都取自草地的颜色。土坡和石阶是从岩壁里劈出来的：切口两侧露出岩壁断面，左侧背光、右侧受光，左壁在坡道上投下一道阴影；坡道越过崖顶后继续往上层地面里切出一段沟，两侧有土坎，越往里越浅，最后淡入地面。草坡不是切口：两侧岩壁逐渐变矮、沉进坡里，上层的地面顺势滚下来，像天然的缓坡 | 每个坡道填 `(中心 x, 半宽, 样式)`，样式 0 是土坡、1 是石阶、2 是草坡。土坡和石阶的上下出口会自动铺一小片土路，用来接小路；草坡不铺路 |
| `CliffBand.collision` | 岩壁自动生成碰撞，角色穿不过去，只有坡道的口子能走 | 默认开启。洞口（`openings`）不能通行 |
| `TerrainPath`（`world/terrain/`） | 沿折线画一条土路，宽度沿途有轻微变化，边缘由地面着色器自然过渡 | `points` 是路线，`width` 是宽度，`kind` 可以改成耕地等其他地面 |
| 演示角色（`world/demo/demo_player.gd`） | 一个真正会碰撞的角色（CharacterBody2D）：用 WASD 或方向键控制；不按键时按 `waypoints` 自动走，走不通的点会自动跳过；上坡道会放慢，走石阶时一步一颠 | 按任意方向键即可切换为手动控制 |

岩壁只是贴在地面上的画，上层和下层的东西不会互相遮挡，所以不需要单独区分"高度层"，靠岩壁的碰撞就能把上下两层分开。

## 水体（演示场景 `scenes/water_demo.tscn`）

水只有一种：湖、池塘、河、溪、水坑都是同一种水体，区别只在轮廓形状。所有水画进 `Terrain` 的水数据，再由一个 `WaterLayer` 统一绘制，相邻或重叠的水面会连成一片。演示视频：`docs/art/water-demo.mp4`；截图：`water-lake-sun.png`、`water-lake.png`、`water-waterfall.png`、`water-pond.png`、`water-stream.png`、`water-beach.png`。

水面效果：

- **颜色**：岸边是澄澈的浅蓝，往水中央细微地过渡到深蓝。
- **天空倒影**：几块浅色的天光，慢慢飘动。
- **水波**：几条白色细线顺着漂，每条下面带一道暗影；偶尔有水圈荡开。
- **太阳波光**：从屏幕上方垂下一道光带，上宽下窄、越往下越淡。光带里的浪尖发亮，还有许多忽明忽灭的圆形亮斑：大的有白色光芯、柔和光晕和四角星芒，小的只是一个亮点，光带外也零星散着一些。镜头移动时光带一直留在屏幕中央；别处偶尔有星形闪光。
- **焦散**：近岸水底有一张弯曲的光网，线条有粗有细，交汇处更亮，往深处慢慢散掉。
- **岸边**：上岸露出泥土岸壁，并在水面投下阴影；下岸和两侧是一圈半透明的浅水，能看到下面湿润的泥底，还有一道来回拍岸的白沫。
- **倒影**：岸边的树、灌木和石头会在水里留下上下颠倒的倒影，随水波轻轻晃动，越远越淡。

| 节点 | 作用 | 怎么用 |
|---|---|---|
| `WaterLayer`（`world/water/`） | 绘制所有水面 | 每张地图放一个，指定 `terrain`。材质参数：<br>颜色 `water_color`（深水）、`clear_color`（近岸）、`gradient_reach`（渐变范围）<br>天光 `reflection_amount`<br>水波线 `drift`、`line_density`、`line_length`、`line_opacity`<br>水圈 `ripple_rings`<br>星形闪光 `sparkle`<br>太阳光带 `sun_x`（在屏幕上的横向位置）、`sun_length`（往下延伸多远）、`sun_width`（顶部和底部的半宽）、`sun_glitter`、`sparkle_density`（亮斑多少）<br>焦散 `caustic_strength`、`caustic_size`、`caustic_reach`、`caustic_speed`<br>岸边 `bank_height`（岸壁高度）、`bank_shadow`、`rim_width`（半透明浅水宽度）、`rim_opacity`、`foam_amount` |
| `WaterBody` | 任意一块水 | 加一个名为 `Shape` 的 Polygon2D 子节点画轮廓（或直接填 `polygon`），河就画成长条形。`shore` 选岸：<br>`GRASS` 草岸<br>`SAND` 沙岸（宽度由 `beach_width` 决定）<br>`ROCK` 石岸（沿岸放 `rocks` 块半浸水的石头）<br>`SAND_AND_ROCK` 两者都有 |
| `Waterfall` | 岩壁上的瀑布：圆润的水幕（左侧受光、右侧背光），顶部亮色翻卷的水唇，几道越往下拉得越长的水纹，底部泛白；落点堆起一团蓬松的泡沫，周围有漂浮的碎沫和扩散的水圈；两侧岩石被打湿变深 | 指定 `cliff`（一个 CliffBand）后会自动贴到崖顶，高度取岩壁高度，同时去掉落水处的崖顶草边，并在瀑布顶上补一段同宽的水面，和上游的河或湖无缝衔接；不指定时用 `height`。`width`、`speed` 可调，`mist` 开关水雾。瀑布周围不长草 |
| `WaterReflection` | 倒影 | `WorldTree` 和 `WorldProp` 会自动加，只有下方有水时才显示，不用手动处理。浓淡、晃动幅度和消失距离在 `reflection.gdshader` 里调 |

地面着色器（`ground.gdshader`）配合水体画三样东西：浅水下的湿泥、水边一条湿泥带（沙岸是湿沙）、外面一圈颜色更深的湿草。范围由 `damp_reach` 控制。

画水的其他方式：

- 地面刷子里有一个"水"刷子；擦除刷子也会擦掉水。
- 可以给 `Terrain.water_mask` 一张灰度图，白色的格子就是水。
- 游戏里挖水用 `set_cell(cell, Terrain.Kind.WATER)`，填回草地用 `Kind.GRASS`。
- `Kind.SAND` 是沙地。
- `Terrain.water_at(世界坐标)` 返回 0–1，表示这个位置有多少水。

草、`Scatter` 散布的树和石头都会避开水面；水边一圈长矮草过渡。

## 昼夜光影（`DayNight`，`world/fx/day_night.gd`）

日出、正午、黄昏、午夜无缝循环，用来表现时间流逝。时段：5:00–6:00 日出，约 10:50–13:10 正午原色，17:00–18:00 黄昏，太阳 5:00 升起、18:00 落下，其余时间月亮接班。演示视频：`docs/art/day-night.mp4`；八个时刻的对比图：`docs/art/day-night.png`。

- **画面整体**：
  - **颜色、饱和度、对比**：随时间变化。黎明发紫，日出带粉橙，上午清亮，正午（约 10:50–13:10）完全保持场景原色，黄昏金橙，入夜转紫，深夜是暗蓝色，饱和度降低。
  - **太阳方向**：暖光从屏幕左上随太阳移到右上，冷色阴影在对面。
- **光柱**：上午和下午是一排斜射的光柱，角度随太阳偏转；正午收起，改为偶尔在视野里洒下一两道近乎垂直的阳光，停留几秒后淡出，过一阵在别处再出现；夜里消失。
- **云影**：白天明显，夜里几乎看不见。
- **影子**：清晨长、偏向右，正午短，黄昏长、偏向左，月光下很淡。
- **水面**：
  - 太阳光带随时间变色：白天白金色，日出、黄昏橙红色，夜里变成淡蓝的月光。
  - 水面倒映天空：日出时水里有粉色天光，黄昏是桃色云影，入夜水色加深成紫蓝。
- **夜晚**：萤火虫出来，在调色层之上发光，不会被压暗；蝴蝶在入夜时淡出（加入 `daytime_only` 组的节点都会这样）。
- **时钟**：右上角有一个小时钟，太阳或月亮沿弧线移动，下面显示时间。

用法：

- 场景里放一个 `DayNight` 节点，`grade` 指向全屏调色的 ColorRect，`clouds` 和 `shafts` 指向云影和光柱层。
- `cycle_minutes` 是一天对应的现实分钟数，默认 12；演示场景用 0.75，45 秒过完一天。`start_hour` 是起始时间。
- `DayNight.hour` 是全局游戏时钟，切换场景时时间继续走。`DayNight.daylight()` 返回白天程度（0 到 1），`DayNight.clock_text()` 返回 "HH:MM"。
- 各时刻的光影参数写在脚本开头的 `KEYS` 表里，每行一个时刻。相邻时刻之间按循环曲线平滑过渡，改哪一行就调哪个时段。

更新记录见 [CHANGELOG.md](CHANGELOG.md)。

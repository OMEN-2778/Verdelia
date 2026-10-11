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

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

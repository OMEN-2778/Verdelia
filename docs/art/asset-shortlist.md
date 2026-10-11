# 美术资产候选清单

目标风格：接近星露谷物语（16×16 瓦片、16×32 左右的角色）+ 潜水员戴夫（像素角色配丰富的光影）。明媚但不卡通。

许可和价格以商品页为准，购买前请再核对一遍。

## 首选：Mana Seed 系列（Seliel the Shaper）

和设定最契合的一套：

- **Farmer Sprite System**（约 $29.99，有免费试用版）：纸娃娃式角色，身体、发型、服装、眼睛可以分别替换，正好对应设定里的「通用身体模型 + 通用发型，NPC 复用」。另有第三方的眼睛扩展包。
  https://seliel-the-shaper.itch.io/farmer-base
- **四季森林瓦片**（Summer / Autumn / Winter / Gentle Forest，单个 $19.99，四季合集 $44.99）：16×16。四季布局完全相同，换季节只需要替换 PNG，正好配合「季节与天气」系统。
  https://seliel-the-shaper.itch.io/summer-forest
- **作物套装**（Farming Crops #1 / #2，约 $9.99 一套）：六个生长阶段，另有会长大的果树包。
  https://seliel-the-shaper.itch.io/farming-crops
- 作者有一个 28 套素材打包的合集，约 $99.99。如果打算长期用，这个最划算。
- 许可：每个商品页都链接到 Mana Seed 用户许可，禁止 NFT 等用途。全文在作者网站，云端环境访问不到，购买前请自己看一遍。

## 低成本备选：Hana Caraka 系列（Otterisk）

- Farming & Foraging、Base Character、Livestock & Fish、Topdown Tileset。免费或自愿付费（完整版约 $4.99）。
- 许可：可商用、可修改，署名可选。禁止转售或二次分发、禁止用于训练 AI、禁止 NFT。
- 缺点：仍在开发中，内容量不如 Mana Seed；画风稍微更卡通。
  https://otterisk.itch.io/hana-caraka-farming-foraging

## 偏写实、光影更丰富的：Cainos — Pixel Art Top Down Basic

- 32×32，自愿付费。植被茂密、色调自然，最不卡通。
- 缺点：32×32 和 16×16 的星露谷比例不一致，不能和上面两套混用；许可条款在压缩包里，还没核实。
  https://cainos.itch.io/pixel-art-top-down-basic

## 不推荐

- **Sprout Lands（Cup Nooble）**：很可爱，但偏卡通，和「不卡通」冲突。免费版要求署名。
- **Farm Tileset（Cute SCKR）**：商品页标注 AI Assisted，风格一致性和版权都有风险。
- **Kenney 系列**：扁平图标风，太卡通（之前的演示已经验证过）。

## 潜水员戴夫的感觉怎么来

戴夫的观感主要来自引擎里的表现，不靠素材本身：像素角色放在有 3D 光照的场景里，加体积光、景深、水面反射。在 Godot 里可以这样做：

- 2D 光照（PointLight2D / DirectionalLight2D），给像素图加法线贴图，让阳光和魔法光有体积感；
- 后处理：轻微 bloom、暖色调色、昼夜色调曲线；
- 法阵激光、遗迹这类场景用 3D 模型，配合像素化着色器，和像素角色混合。

所以素材选 Mana Seed 这类干净的 16-bit 风格就够了，「戴夫感」由我在 Godot 里用光影和着色器补上。

## 拿到素材前需要放开的网络

云端环境的网络策略目前挡住了 itch.io，需要在环境设置的 Allowed domains 里加上 itch.io 及其下载域名，我才能直接下载免费素材或试用版。付费素材也可以由你下载后放进仓库的 `art/vendor/` 目录。

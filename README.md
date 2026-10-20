# 畲 · 凤鸣东固

> 扫描二维码进入轻量化 AR 展陈馆：**一木成像**（一段樟木在同一条进度轴上被雕成神像：选木 → 定像 → 开坯 → 修光 → 彩绘贴金 → 开光，可拖动）、**红色地标历史场景复原**（1929 东固会师 / 1930 龙冈大捷 / 1931 白云山首战 / 1931 六渡坳）、**畲族凤凰图腾动态演绎**，另附畲族文化、田野人物与配套文创。

**线上地址**：https://donggu-phoenix.pages.dev/（全球 CDN，后端同域）
**备用地址**：https://lxh113377.github.io/donggu-phoenix/
**访问统计**：Cloudflare Pages Functions + D1，匿名聚合（详见下方「访问统计与隐私」）
**交付说明**：[`docs/交付说明.md`](docs/交付说明.md) ｜ **体验与 AR 方案**：[`docs/体验设计与AR方案.md`](docs/体验设计与AR方案.md) ｜ **AR 分镜**：[`docs/ar-storyboard.md`](docs/ar-storyboard.md)

---

## 快速开始

```powershell
# 本地预览
cd site
python -m http.server 8791
# 打开 http://127.0.0.1:8791/

# 自检
python tools\verify_site.py
python tools\make_qr.py      # 含 3 枚场景直连码生成与回读
python tools\make_ar_assets.py
```

## 目录

| 目录 | 内容 |
|---|---|
| `site/` | 部署根（GitHub Pages 发布此目录） |
| `site/assets/data/ar-data.js` | AR 三场景唯一内容源（章节 / 双语 / 出处） |
| `site/assets/js/wood-to-statue.js` | **一木成像雕刻引擎**（单进度轴 0→1；落地页与 AR 场景一共用同一套几何） |
| `site/assets/js/wood-demo.js` | 落地页可拖动雕刻台（滑杆 / 画面拖拽 / 方向键） |
| `site/assets/js/ar-scenes.js` | 三场景 Canvas 渲染器（零模型文件） |
| `site/assets/js/ar.js` | AR 展陈控制层（全屏层 / 取景锁定 / 集章 / 停留计时） |
| `docs/ar-storyboard.md` | AR 分镜脚本（自动生成） |
| `docs/体验设计与AR方案.md` | 命题应答：轻量化定义、沉浸感手法、停留机制、边界清单 |
| `merch/print/` | 三版印刷图腾 SVG（单色/全彩/金线） |
| `merch/mock/` | 6 张文创效果图 |
| `qr/` | 5 规格通用二维码 + 3 枚场景直连码（`qr-ar-craft/red/phoenix.png`） |
| `tools/` | 生成与验证脚本 |
| `docs/` | 交付说明 |

## 技术

- 前端：HTML + CSS + 原生 JS，零依赖、零构建；后端：Cloudflare Pages Functions + D1（SQLite）
- 访问统计：`functions/api/` 下两个端点 —— `POST /api/track` 匿名写入、`GET /api/stats` 聚合读出；页脚实时显示「开馆至今 N 位访客 · M 次到访」
- 凤凰动画：Canvas 2D 粒子系统（2600 粒子，桌面 200+ fps）
- AR 展陈：三段共 152 秒，全部 Canvas 2D 实时绘制；零 3D 模型、零第三方库、零外部请求
- 一木成像：造像轮廓由参数化剖面 `halfWidth(u, 进度)` 定义，开坯是沿像身推进的波前，木料与神像**同一条进度轴**；工序器具（斧 / 凿槌 / 毛笔 / 金箔镊）与年轮、木屑、背光全部代码绘制
- 集章与停留计时：`localStorage` 本地持久化，不上传任何数据
- 图腾：代码生成的原创矢量 SVG（`tools/make_totem.py`，右半定义 + 镜像）
- 二维码：`qrcode` 生成 + OpenCV 回读自检
- 部署：GitHub Actions → Pages；Cloudflare Pages 备用

## 访问统计与隐私

- **采集范围**：事件名（进页 / AR 场景 / 唤凤）、路径、随机访客号（`localStorage` 的 `dg-vid`，16 位随机十六进制，可随时清除）、语言、屏幕档；地理（国家 / 城市 / 时区）与 UA 由 Cloudflare 边缘按请求头记录。**不含**任何可输入内容、姓名、联系方式，无跨站跟踪、无 Cookie。
- **部署面边界**：统计仅在 `*.pages.dev` 域名生效；GitHub Pages 备用端无 Functions，前端探测后整段休眠，一个请求都不发。
- **接口边界**：`POST /api/track` 白名单字段 + 长度截断 + 同源校验 + 批量上限 20 条；任何异常都静默降级（`ok:false`），绝不影响访客浏览。
- **数据查看**：`GET /api/stats` 返回累计 / 今日 / 近 14 天序列 / 场景热度 / 热门路径的匿名聚合；明细可经 `wrangler d1 execute donggu-analytics --remote --command "SELECT ..."` 查询。

## 降级链

摄像头不可用 / 权限拒绝 / 非 https → 自动切「点击召唤」→ 仍不可用则静帧图腾。
AR 展陈：摄像头不可用同理会切「展柜模式」，三段动画照常播放，不白屏。
`prefers-reduced-motion` 用户直接获得静态光点图腾。

## 内容来源

| 内容 | 来源 |
|---|---|
| 畲族凤凰装、三公主、大中小老凤凰装 | 福建省文物局公开文物资料 |
| 匠人段落 | `素材/` 内两份采访稿（逐字） |
| 造像五道工序、开光仪式、「丹青先生」 | 刘卷《东固传统造像的制作工艺与仪式过程及其文化功能阐释》，《装饰》2015-07；吉安市人民政府《东固传统造像》 |
| 樟木用料、开面分寸、雕銮匠与六百年传承 | 《井冈山报》2026-08-10《樟木深处听刀音——记国家级非遗项目东固传统造像代表性传承人刘节明》 |
| 东固会师 / 龙冈大捷 / 白云山 / 六渡坳 | 《江西日报》2021-08-06《赣水那边红一角》（人民网党史频道转载） |
| 团队署名 | 媒体报道清单 |

**页面无编造内容**；AR 场景每段 `sources` 字段逐条标注，页面上只作文本展示、不发起外部请求。

## AR 场景直连

| 场景 | 直连 |
|---|---|
| 造像技艺流程 | `/#ar=craft` |
| 红色地标复原 | `/#ar=red` |
| 凤凰图腾演绎 | `/#ar=phoenix` |
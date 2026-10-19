# 更新日志

本项目所有值得记录的变更都写在这里。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> 版本口径：站点是可交付的展陈作品，**版本号与 `memory/03-status.md` 的阶段一致**；
> 每次发布同时打一个 git tag，便于评委/合作方核验「看到的是哪一版」。

## [未发布]

### 新增
- PWA 离线兜底：`site/sw.js`（分层缓存：关键路径预缓存 265KB + 图片访问后缓存）与 `site/manifest.webmanifest`，含 3 个 AR 场景快捷方式。
- 应用图标 6 件，由 `tools/make_icons.py` 代码生成（原创「畲」字印章，无第三方素材）。
- 分享与检索元数据：绝对 `og:url`/`og:image`、`twitter:card`、`canonical`、`hreflang`、JSON-LD（`CreativeWork` + 三场景 `hasPart`）。
- 无障碍：`skip-link` 跳转正文、`prefers-contrast` 高对比适配、全站 `font-size` 由 px 改 rem（86 处）且根字号 `100%` 跟随用户系统设置。
- 交付治理件：`LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、issue / PR 模板。
- `tools/dev_server.js`：零依赖本地预览服务器。
- 交付门禁 `tools/verify_site.py` 新增 4 类检查：git 跟踪面对账（防「本地存在但未提交 ⇒ 线上 404」）、SW PRECACHE 清单对账、治理件存在性、PWA/无障碍/分享基线；体积预算由 4MB 收紧到 1200KB。

### 变更
- CI（`.github/workflows/deploy-pages.yml`）在发布前**实际执行** `tools/verify_site.py`；此前该脚本只在本地跑，CI 仅做 `test -f` 存在性检查，等于没有门禁。
- `verify_site.py` 的仓库根改由 `__file__` 推导（此前硬编码本机绝对路径，在 Linux runner 上必红）。
- `<main>` 的锚点 id 由 `top` 改为 `main`（配合 skip-link），品牌链接同步。

### 修复
- 「零外链」判据精确化：`og:url`/`canonical`/`hreflang`/JSON-LD 内的 URL 是元数据字符串、不产生网络请求，此前被误计入外部请求。

## [1.1.0] - 2026-10-19

### 新增
- 「一木成像」连续雕刻：`site/assets/js/wood-to-statue.js` 雕刻引擎 + `wood-demo.js` 可拖动雕刻台；AR 场景一改为复用同一引擎，消除两套造像几何各画一遍的分叉。
- AR 展陈馆三场景（造像 72s / 红色 44s / 图腾 36s，合计 152s）+ 中英双语章节 + 集章与停留计时。
- 场景直连二维码与 `#ar=craft|red|phoenix` 哈希深链。

### 修复
- 焦点陷阱选择器写错导致每次 Tab 抛 TypeError。
- AR 内容缺失时白屏 → 改为 toast 提示。
- 三大场景文案与状态未对齐。

## [1.0.0] - 2026-10-19

### 新增
- 站点首版：凤凰图腾粒子引擎（Canvas 2D，桌面 2600 粒子）、六区块单页、十二件文创、二维码生成与线上实扫验证、GitHub Actions → Pages 自动部署。

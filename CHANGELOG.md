# 更新日志

本项目所有值得记录的变更都写在这里。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> 版本口径：站点是可交付的展陈作品，**版本号与 `memory/03-status.md` 的阶段一致**；
> 每次发布同时打一个 git tag，便于评委/合作方核验「看到的是哪一版」。

## [未发布]

（暂无待发布条目；以下内容已随 1.2.0 发布）

## [1.2.0] - 2026-10-20

> 本版为「与 GitHub 优质开源项目对标」后的工程改造集：高优先级 I-1..I-4（CI 门禁接线 / PWA 离线兜底 / 治理件 / 无障碍与分享基线）与中低优先级 I-5..I-8（旁白音道 / 响应式图片 / 引擎打磨 / 场景注册表）全部落地。
> 判据同步加固：新增 3 道门禁（共 93 项）接入 CI，全部做过反向验证（9/9 破坏用例均判红）。

### 新增

### 新增
- PWA 离线兜底：`site/sw.js`（分层缓存：关键路径预缓存 265KB + 图片访问后缓存）与 `site/manifest.webmanifest`，含 3 个 AR 场景快捷方式。
- 应用图标 6 件，由 `tools/make_icons.py` 代码生成（原创「畲」字印章，无第三方素材）。
- 分享与检索元数据：绝对 `og:url`/`og:image`、`twitter:card`、`canonical`、`hreflang`、JSON-LD（`CreativeWork` + 三场景 `hasPart`）。
- 无障碍：`skip-link` 跳转正文、`prefers-contrast` 高对比适配、全站 `font-size` 由 px 改 rem（86 处）且根字号 `100%` 跟随用户系统设置。
- 交付治理件：`LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、issue / PR 模板。
- `tools/dev_server.js`：零依赖本地预览服务器。
- 交付门禁 `tools/verify_site.py` 新增 4 类检查：git 跟踪面对账（防「本地存在但未提交 ⇒ 线上 404」）、SW PRECACHE 清单对账、治理件存在性、PWA/无障碍/分享基线；体积预算由 4MB 收紧到 1200KB（**2026-10-20 轮5 再修订为整站 1600KB + 新增首屏关键路径 ≤400KB 双判据**，见下）。

- 设计系统 v2：自托管中文字体（ZCOOL 小薇子集 + Cinzel）+ 11 档 `--fs-*` 字阶令牌 + 三处打破模板感的结构改造（文化编号横排 / 文创 2x2 特写格 / 场景竖向动线）+ 移动端汉堡整屏目录。
- 文创 12 件全部换成品级实物效果图（`tools/make_merch_renders.py` 代码生成质感，透明底 620px）。
- **I-5 旁白音道**：AR 播放层 `#ar-narrate` 开关，用浏览器内置 `speechSynthesis` 逐章朗读解说（含章名与正文）。零音频文件、零外部请求；无 TTS 引擎时按钮置「旁白 不可用」并 disabled。
- **I-6 响应式图片**：`tools/make_srcset.py` 生成 12 件文创 340w 小档，前端写 `srcset`/`sizes`；匠人头像与页尾二维码补 `loading="lazy"` + `decoding="async"`。
- **I-8 场景注册表**：`AR_SCENES.register()/create()` 查表装配，重复注册与未知场景抛「往哪查」的错误；加一段场景只需改 `ar-data.js` + 一行 `register()`。
- 交付门禁新增 3 类判据并接入 CI：`orphan_asset_test.py`（零孤儿资产 / srcset 候选档存在且入版本控制 / 响应式基线）、`narration_gate_test.py`（旁白 20 项）、`engine_polish_test.py`（密度与节流 23 项）。

### 变更
- 体积门禁改为双判据：整站预算 1200KB → 1600KB，同时新增**首屏关键路径 ≤400KB**（HTML+CSS+首屏字体+首屏脚本）。上调是因为设计系统 v2 引入自托管中文字体（238KB 子集），而「零外部请求」是硬约束、不能把字体成本甩给 CDN；补偿是新增的这条比整站体积更能防退化。反向验证实测：注入 +300KB CSS 后关键路径 675KB 判红，而整站 1516KB 未触 1600 —— 两条独立生效。
- `verify_site.py` 的 SW PRECACHE 对账正则补 `woff2/png/webp/jpg/json` 扩展名，并加**计数一致性守卫**（数组条目数 ≠ 正则解析数即判红）。一手教训：原正则只认 `html|css|js|svg|webmanifest`，字体进 PRECACHE 后完全落在对账面之外 —— 注入指向不存在字体的条目，门禁仍 exit 0 且把 16 项报成 14 项。
- CI（`.github/workflows/deploy-pages.yml`）在发布前**实际执行** `tools/verify_site.py`；此前该脚本只在本地跑，CI 仅做 `test -f` 存在性检查，等于没有门禁。
- `verify_site.py` 的仓库根改由 `__file__` 推导（此前硬编码本机绝对路径，在 Linux runner 上必红）。
- `<main>` 的锚点 id 由 `top` 改为 `main`（配合 skip-link），品牌链接同步。

### 修复
- **AR 未打开时点旁白按钮无视觉反馈**：`aria-pressed` 原先只在 `paintHud()` 内同步，而该函数开头 `if (!state.scene) return`，导致 `narr.on` 已为 true 但按钮不变、读屏也不知道。状态同步抽为独立 `syncNarrBtn()`，点击 / API / 逐帧三处调用。
- **未知场景抛错后播放层白屏**：`create()` 改为抛错后，若数据层有该场景而渲染层未注册，播放层会停在「已打开但没有场景」的空舞台。现依次回落到其他已注册场景，全部不可用则关闭播放层并给出可读提示。
- **字体子集把注释字符收进产物**：`build_fonts.py` 原先按整份文件取字符，写一段中文注释就让线上 woff2 +117KB（越过 260KB 险线），而完整性判据是剥注释后检查的，两侧口径不一致。现统一为「非注释字符」。
- **门禁死循环**：`reduced_motion_test.py` 在 CSS **注释**里出现 `prefers-reduced-motion` 字样时，块定位会往前取到已结束 media 块、游标倒退，造成无限循环（表现为 CI job 静默挂死）。现只匹配真实 `@media` 块并先剥注释。
- 体积门禁的字体版本控制检查补「无 git 环境」守卫：`git archive` 产物 / 离线副本此前会误判红「字体未入版本控制」，现与其余判据一致走 SKIP + WARNING（未取证不等于通过）。
- 「零外链」判据精确化：
- 部署体积 1524KB → 1323KB：清退 322KB **部署面零引用的孤儿位图**（merch-sketch / scene-interview-1 / scene-interview-2 / merch-badge / icon-180）。素材原件仍在 `素材/`，生成器已停出并留说明。`og:url`/`canonical`/`hreflang`/JSON-LD 内的 URL 是元数据字符串、不产生网络请求，此前被误计入外部请求。

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

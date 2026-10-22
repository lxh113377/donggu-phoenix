# 更新日志

本项目所有值得记录的变更都写在这里。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> 版本口径：站点是可交付的展陈作品，**版本号与 `memory/03-status.md` 的阶段一致**；
> 每次发布同时打一个 git tag，便于评委/合作方核验「看到的是哪一版」。

## [未发布]

### 变更（轮110 · 2026-10-22 · 演示数据按老大口径重做）

老大对轮109 的样本提了三条修正，逐条落地：

1. **「浏览量线性增加太假了，不够随机」** —— 原样本是「上行趋势 × 收尾冲刺」，
   十周基本单调上升。现在改成：随机游走基线 × 两处小高峰 × 一处回落 × 天数折算，
   逐日再按周末上扬 / 周一略低 / 随机二次分配。
   实测周序列 1481 1909 2092 2191 1708 2242 1377（涨 4 次跌 2 次、峰谷比 1.63、
   最大单周环比 39%、逐日 48 天里 25 次方向反转），并新增判据 F 条守着：
   严格单调 / 反转少于 2 次 / 峰谷比 <1.45 或 >3.2 / 单周环比 >55% / 逐日取值过于集中，
   任一命中即判红。**「线性太假」从此是机器判据，不是靠人眼看。**
2. **「日期要用现实的日期，九月初到十月底」** —— 原窗口右界 2026-11-09
   **比基准日 10-22 还晚**，是不现实的日期。新窗口 2026-09-01 ~ 2026-10-18，
   右界取「最后一个已结束的周日」：周全部完整、一天不进未来、末端不会因周没结束而塌。
   代价是比「十月底」早 13 天，取舍写在 docs/后台演示数据说明.md。
   首周 09-01~09-06 只有 6 天（9-01 是周二），按 6/7 折算，不虚高。
   判据 B 新增：右界不许晚于基准日、必须是周日、每一天都不许在未来。
3. **「总量在一万到两万」** —— 累计浏览 13,000 / 全部事件 19,541，两种读法都在区间内。

判据由 5 条增到 6 条（新增形态 F 条），反向验证的 9 类退化用例全部仍然判红。
### 变更（轮109 · 2026-10-22 · 后台与页脚改静态演示数据）
- **管理后台不再需要密钥登录**，也不再读数据库：改为单文件静态演示页，
  数据来自一次生成的样本（口径以轮110 为准：窗口 2026-09-01 ~ 2026-10-18、
  累计浏览 13,000 / 全部事件 19,541，两种读法都落在 1 万~2 万）。
  现在 pages.dev、github.io 与本地双击 `site/admin/index.html` 三处都能看到，
  且**刷新多少次数字都不变** —— 修的是「演示现场后端读不到就把访问量显示成零」这个事故形态。
- 主站页脚访问计数同样改读静态样本，并明写「演示样本」不冒充真实访问量；
  此前它在 github.io 备用端因域名闸整段休眠、根本不显示，现在两面与离线都能看到。
- 真实采集链路（`POST /api/track`、`GET /api/stats`、`functions/api/admin/*`、D1）
  一行未动，只是演示面不再读它；要恢复实时的回滚方式记在 `memory/04-decisions.md`。
- 新增三条判据并接入 CI（36 → 39 条）：`admin_static_data_test.py`（数据漂移 /
  口径越界 / 求和不自洽 / 退回实时读接口）、`admin_static_render_test.py`
  （真浏览器验证数字确实渲染 + 断言刷新不变）、`reverse_admin_static.py`
  （注入 9 类退化证明前两条真有牙）。本地浏览器套件 24 → 26 条。
- 字体子集重建（`tools/build_fonts.py`）：新文案带来 19 个新汉字，
  `zcool-display.woff2` 225,588 → 224,808 字节（后台静态化删掉的旧文案更多，净减 780B）。


### 新增（轮85 · U-01 现场收口 + U-02 文创实物化）
- **真机前哨判据** `tools/preflight_device_test.py` + `tools/preflight_device.mjs`：CDP 直连，
  三档移动端 profile（微信 iOS / iPhone Safari / 微信 Android）× 真 CSS 视口 × 4G 限速 × CPU 4x 降频，
  实测首屏 FCP/LCP/CLS/LongTask、横向溢出、AR 三场景推进与画面签名、无摄像头降级、旁白可用性。
  自带双向自检（好夹具必须绿、坏夹具必须红），已接入 `run_browser_suite.py`。
- **真机自检页** `site/_device_probe.html` + `qr/qr-device-probe.png`：手机扫码即自动跑完三项并出
  PASS/FAIL，一键复制 JSON 报告；测前先 unregister SW + 清 caches 再 reload，防 cache-first 假绿。
- **文创打样文件包** `tools/make_proof_pack.py` → `merch/proof/proof-{badge,lamp,tote}.pdf`：
  A4 发厂规格卡（成品尺寸 / 出血咬口 / 材质 / 工艺 / 印刷文件 / 逐条验收复选框 / 100mm 实物比例尺）。
  规格与 `site/assets/data/culture.js` 强制对账，不一致拒绝生成；`--check` 已接入 CI。
- **实拍替换流水线** `tools/replace_merch_photo.py`：EXIF 转正 → 准入校验（≥620px、动态范围）→
  居中裁方 620 + -340 双档 → q 逐档降进 120KB/40KB 预算 → 三道门禁任一红即按 SHA256 逐字回滚 →
  写 `merch/shot-manifest.json`（源/live/render 三 sha + 日期，供素材真实性追溯）。
  `--status` 可查哪几件仍是渲染图。反向验证 `tools/reverse_replace_merch_photo.py`（7 项，含
  「伪造门禁红证明回滚是真的」）已接入 CI。

### 变更
- `run_browser_suite.py` 浏览器判据由 21 项增至 22 项（新增真机前哨）。
- `.gitignore` 新增 `merch/shot/`：实拍原图属「原图仓库」（手机直出 3~8MB/张），发布物是
  `site/assets/img/merch/` 里的成品图，原件不入库。
- 自托管字体子集随自检页文案重建：875 → 912 汉字（222KB，仍在 260KB 险线内）。

### 已知边界（不粉饰）
- 真机前哨是**模拟**，只能证伪不能证实：WebKit（Safari）与 XWEB（微信）内核差异、
  iOS 自动播放策略、真机 CPU/内存与摄像头曝光/识别阈值仍需真机自证（扫码即验）。
- U-02 的「实拍替换」**物理上尚未发生**：目检 `素材/` 九张图确认无一张实物打样照
  （设计稿与草图不算）。当前 `--status` = 实拍 0 / 渲染 12；剩余动作是把 PDF 发厂、回样后拍照入库。

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

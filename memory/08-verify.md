# 验收命令与结果

```powershell
python tools\verify_site.py     # 站点自检（含 AR 专项）
python tools\make_qr.py         # 二维码生成 + 回读
python tools\verify_live_qr.py  # 线上二维码实扫
python tools\make_totem.py      # 图腾三版重生成
python tools\make_mockups.py    # 文创效果图
python tools\make_ar_assets.py  # AR 分镜脚本重生成
```

## 最近一次结果（2026-10-19 第三轮 · 一木成像）
- verify_site.py：RESULT PASS（新增「一木成像：引擎 / 雕刻台 / AR 同源 / 六工序 / 加载顺序」专项；总体积 795KB / 27 文件）
- 雕刻台六工序逐档截图（1280×800）：选木 4% / 定像 16% / 开坯 34% / 修光 55% / 彩绘贴金 80% / 开光 100% 全部出画
- 交互实测：滑杆 input、画布 pointer 拖拽、聚焦后 ArrowRight ×3（0.30→0.36）均生效；__carve.stats() 读数正确
- AR 场景一：__ar.open('craft') 后 seek 30 / 64 截图，与雕刻台同一几何；fps 151–300
- 无障碍：reduced-motion 下 playing=false 且停在成品像；画布 role=slider 可键盘操作
- 窄屏 390×844：scrollWidth == innerWidth == 390，控制行无重叠（labelRight 186 < pctLeft 308）
- 海报元素二次吸收：背景板加三层山峦剪影 + 岭脊亮边（选木/开光两档截图复核，解说区渐变遮罩未被山脊吃掉）
- 缓存正确性：sw.js VERSION v1→v2，verify 的「SW PRECACHE 清单 14 项与磁盘对账」仍 PASS
- 控制台：0 报错（window error 监听实测为空数组）

## 轮4b 结果（2026-10-20 00:30 · 山峦 + SW 缓存纠正）
- 干净克隆复跑门禁：`git clone` 到 HEAD 后 python tools/verify_site.py → RESULT PASS（35 文件 / 848KB）
- **抓出门禁假绿并修复**：SW PRECACHE 正则 ',?$ 在 CRLF 文件上解析 0 项仍打印 PASS
  → 放宽为 ',?\r?$（CRLF/LF 实测均 14 项）+ 零项即 FAIL 守卫
  → 反向验证：改掉一项引号，计数降到 13，证明计数随内容变化、非恒真
- sw.js VERSION v1→v2（引擎内容变了但 PRECACHE 清单没变 ⇒ 缓存名不变 ⇒ 老访客 cache-first 拿不到新引擎）
- 线上双链路实测：GitHub Pages engine len=32250 含 ridgeBase、sw.js 200 且 v2、navigator.serviceWorker.controller=true、__carve 到 open 档、AR craft seek 66 出画；pages.dev 同样含引擎与雕刻台
- 提交：79d5fa3（山峦 + SW v2）、3daad0f（门禁假绿修复），origin/main 同步 0/0
- 过程事故：并发进程的 stash pop 与我的编辑在 memory/03-status.md 撞出 UU 冲突，按「保留双方 + 修正过时 Cloudflare 待办行」解决；未改写他人提交（其 4 个治理提交 + 对标报告已在 main 线上）

- 反向验证：woodGrain/lotusPath 等旧造像几何已从 ar-scenes.js 删除，verify_site.py 会因「仍留有旧造像几何」而 FAIL

## 上一轮结果（2026-10-19 第二轮）
- verify_site.py：RESULT PASS（HTML 引用 0 缺失 / 编码 0 问题 / SEO 7-7 / AR 3 场景 13 章节 152s 零外链 / 总体积 767KB）
- AR 桌面 1280×800：182–300 fps，三场景逐章截图全部出画
- AR 手机 390×844：主画面占上半屏，无横向溢出
- 集章：craft / red / phoenix 三枚可落，「三章集齐」文案生效
- 摄像头降级：拒绝授权 → 展柜模式 + toast；注入暖色流 → mode=camera、locked=true
- 减少动态：playing=false，定位到关键帧（凤凰 t=16s）
- 控制台：0 报错

## 首版结果（2026-10-19）
- verify_site.py：RESULT PASS（总体积 680KB）
- make_qr.py：5 规格全 PASS
- verify_live_qr.py：线上 qr.png 解码 == 线上 URL ✅
- 桌面 1280×800：粒子 2634，fps 288，无报错
- 手机 390×844：scrollWidth == innerWidth == 390
## 轮5 结果（2026-10-20 07:20 · 对标驱动的四项工程改造）

- **I-1 CI 门禁**：`verify` 独立 job + `deploy needs: verify`。CI run 39286281457 /
  39340960282 的 **Verify site** job 真实执行脚本（Linux runner 日志正文可读到
  15 项 PASS 与 RESULT: PASS）——此前是「11 绿 0 检」（脚本存在但从未在 CI 跑）
- **反向验证 10/10 判红**：注入 A 引用缺失 / B 删 manifest / C og 退回相对 /
  D 加外部 CDN / E1 退 1 处 px / E2 根字号写死 16px / F 删 skip-link /
  G 删 canonical / H 删 JSON-LD / I PRECACHE 指向不存在文件；还原后 exit 0
- **I-2 PWA 线上子路径实测**（本地根路径不算数，scope 解析不同）：
  getRegistrations N=1 scope=/donggu-phoenix/ active=true；controller activated；
  donggu-core-v2 精确 14 条且路径解析为 /donggu-phoenix/assets/...；
  **清缓存 + 断网 + 重载** → 9 区块 / 2634 粒子 / carve 在 / bg=rgb(11,9,8)；
  **断网中开 AR** → playing=true t=3.3s 156fps 章节文案渲染正常
- **I-4 无障碍零回归**：86 处 font-size px→rem 后实测渲染值不变
  （html/body 16px、hero 52px、正文 14px），390×844 scrollWidth==innerWidth，0 报错
- **I-3 治理件 7/7**：gh api 现取 license 由「空」变为 NOASSERTION
  （自定义双轨授权，GitHub 无法自动归类，非 OSI 认证许可 —— 刻意选择）
- 提交：3546c87（治理件）→ fb28c1c（PWA+无障碍）→ e5a78b9（CI 门禁）→
  05eba02（补交漏暂存的 CSS）→ 4c3f2c9（报告）→ aa9ed4f（报告 §9 勘误）
- **门禁首次拦住真实风险**：并发字体子集化把站点推到 1,448KB，判红
  「体积超预算 1200KB」。**不调阈值**，留给字体方案收口
- 教训入库：门禁必须在**干净克隆**里验一次 —— 我用 LF 写文件测出 PRECACHE 14 项，
  checkout 转 CRLF 后正则一条不匹配却仍打 PASS（由并发进程 3daad0f 修复）

## 轮5 结果（2026-10-20 · 设计系统 v2）
- `python tools/verify_site.py`：**RESULT PASS**，20 项 PASS / 0 FAIL；站点 1125KB / 38 文件；
  **首屏关键路径 373KB / 预算 400KB**（HTML+CSS+字体+首屏脚本）
- 字体自托管：zcool-display.woff2 244336B（1125 字子集）+ cinzel.woff2 14012B；零 Google Fonts 外链
- 多视口实测（agent-browser，探针 tools 内 `_qa/probe_viewport.js` 口径已修正为「未被祖先裁切才算溢出」）：
  360/390/768/1024/1440/1920 六档 **realOverflow=false**，最小可点 **44px**，
  H1 全部命中 ZCOOL XiaoWei（48 / 48 / 58.4 / 77.8 / 104 / 104px），汉堡按钮仅在 <860px 出现
- 交互实测：召唤 burst→flight（2634 粒子 / 225fps）；雕刻台滑杆 60%→「四·修光」、80%→「五·彩绘贴金」；
  工序轨点击→「三·开坯」；文创「高客单」筛出 3 件且特写格正确退场（「全部」12 件含 1 个 is-feature）；
  场景动线开演 AR（title/chapter/dots 齐全），「下一段」切章，关闭复位
- AR 三段逐场景：craft「三·开坯 00:33」/ red「白云山首战 00:31」/ phoenix「落羽归位 00:31」；
  窄屏 AR（390×844）copyRight 359 < 390，无横向溢出
- `prefers-reduced-motion` 实测（agent-browser set media reduced-motion）：hero 动画/入场动画/旋转全部
  `animation:none`、transition 0s、opacity 全部 1（内容仍可见，不是「停成空壳」）
- 版本对账守卫实测：注入 `--build:2` → 触发 → 重载后 `--build=3`、guardKey 复位、
  `navigation.type=reload` 一次即止；复原后不再重载
- 门禁反向验证（每条故意破坏均判红，复原 PASS）：字体引用失效 / 字号 0.625rem / 删 nav-toggle /
  改坏 .merch-item.is-feature{ / 关键路径垫到 793KB / --build 改成 9 / 删防循环闸
- 线上（GitHub Pages）：index.html 22210B、main.css 54406B、两份字体 200、sw.js v4；
  浏览器实开 --build=3、realOverflow=false、minTap=44、H1=ZCOOL XiaoWei 104px
- CI：Deploy to GitHub Pages run `39343397913`（设计系统 v2）、`39344491268`（版本对账守卫）均 success

## 轮6 结果（2026-10-20 08:06 · 社区 PR + 门禁假绿修复）
- **社区协作达成**：向 `UniversalViewer/universalviewer` 提 PR **#1898**（base=dev，1 file +1−1，README License 段 blob/master → blob/main）。
  提单前 7 个候选中 6 个被自己的证据推翻（Travis 徽章已被注释不渲染 / jsDelivr @1.2.x 实测 200 / 组件属性确实存在 /
  README 已自我说明 @latest / Mirador #4223 经 MUI 9.5.0 源码证伪 / #3904 维护者本人 PR #4464 在跑且 issue 方案已被 #4379 证明错误）。
  详见 docs/对标分析报告.md §10.2。
- **CI 现状如实记录**：两个 workflow 为 action_required（首次贡献者审批门，非缺陷）；不谎报为绿。
- **抓出并修复我自己门禁的假绿**：PRECACHE 正则缺 woff2 ⇒ 字体条目完全不在对账面内，
  注入指向不存在字体仍 exit 0 且把 16 项报成 14 项。修法＝补扩展名 + **计数一致性守卫**
  （数组条目数 ≠ 正则解析数即判红，防同类失效复发）。
  反向验证：A 字体指向不存在 → 判红 ✅；B 未知扩展名 → 守卫报「20 vs 19」✅；
  干净克隆（含 .git，等价 actions/checkout）→ 全绿 ✅
- **CHANGELOG 陈述与代码不符已修**：仍写「收紧到 1200KB」而实际 BUDGET_KB=1600。
  补双判据说明（整站 1600 + 首屏关键路径 ≤400）。实测注入 +300KB CSS ⇒
  关键路径 675KB 判红、整站 1516KB 未触 1600，两条独立生效，属真权衡非放水。
- CI run 39345640497（sha 3141982）：Verify site success → Deploy success；
  日志显示 PRECACHE 17 项（修复生效）、关键路径 375/400KB、跟踪面 22 项。
- 提交：c0a5dab（报告 §10）→ 3141982（门禁修复 + CHANGELOG 修正），origin/main 同步 0/0

## 轮5 追加（2026-10-20 08:1x）自测截图发现的缺陷 + 移动端逐屏目检
- **品牌链接误加下划线**：滚动高亮选择器 `.nav a[href^="#"]` 把 `.brand` 一并纳入，
  logo 下方常驻一条金色下划线（首屏截图可见）。改 `.nav ul a[href^="#"]`，实测 brand 不再带 `on`、
  伪元素 `transform=scaleX(0)`。提交 e7474e0。
- **移动端逐屏目检（390×844，8 屏）**：hero / 图腾 / 一木成像 / AR / 文化 / 匠人 / 文创 / 场景动线 / 扫码
  全部无横向溢出、无文字裁切；文创 2×2 特写格在窄屏正确退化为单列；三大场景动线在窄屏收成单列且
  「开演 →」隐藏（整行仍可点）。
- **移动端菜单实测**：点汉堡 → `aria-expanded=true`、菜单 `visibility:visible`；点第 4 项 →
  菜单自动收起、`aria-expanded=false`、滚动到文化段（cultureTop=95，正好落在 `scroll-padding-top:88px` 下方）。
- **清克隆门禁复核**：本地工作区被并发进程未提交改动污染（index.html 已引用其未跟踪的 statue-profile.js），
  故「本地 FAIL」不代表本轮交付；`git clone` 到 HEAD 后跑 verify_site.py → **RESULT PASS**（判据面干净）。
- **线上最终读数**：build=4、realOverflow=false、minTap=44、H1=ZCOOL XiaoWei 104px；
  CI run 39346453741 → success。

## 轮6 结果（2026-10-20 · 文创实物图 + 进场动画缺陷）
- `verify_site.py`：**RESULT PASS**（22 项 PASS / 0 FAIL）；整站 1550KB / 1600KB；首屏关键路径 **377KB / 400KB**
- 文创 12 件：**12/12 件件有图**（此前 6 件只有占位图腾），0 占位符；图片单张 ≤120KB、长边 ≤760、透明底
- 六档视口（360/390/768/1024/1440/1920）：realOverflow 全 false，最小可点 **44px**，build=6 一致
- 文创筛选实测：全部 12 / 现有延续 5 / 高频低成本 2 / 数字衍生 2 / 高客单 3，各档图片加载数与条目数一致
- 进场动画回归：8 个段落锚点逐个跳转，段内 reveal 隐藏数全 0；桌面 29 个 reveal 元素隐藏数 0
- 手机端 390×844：文创网格 opacity 1（修复前为 0，整块空白）
- 线上复核：12/12 张文创图 HTTP 200（合计 230KB）；build=6；H1 命中 ZCOOL XiaoWei
- CI：`39350567606` success（期间 `39350473761` 曾因并发进程「锁/资产未同提交」红过一次，已由后续提交 873ae48 修好）

### 门禁新增（均做反向验证）
- 进场动画：threshold ≤0.02 + `revealTall()` 必须被调用 → 改回 0.12 / 删调用 → 均判红
- 文创实物图：12 件必须件件有 image 且文件存在、≤120KB → 抽掉一件 → 判红

## 轮7 结果（2026-10-20 · 八维系统复检 + 三处真缺陷）

### 本轮做法
不再靠肉眼猜，而是把八维自检**机器化**：新建 `tools/design_audit.py` 一键跑，
读数可复核（对比度 / 行长 / 字阶 / 层级 / 动效 / 微交互 / 响应式 / 原创性）。

### 机读抓出的三处真缺陷（都已修）
| # | 缺陷 | 读数 | 修法 |
|---|---|---|---|
| 1 | **中文行长失控** | `.carve-note` 98.5 字/行、`.ar-stats` 98.5、`.ar-note p` 77.4、`.foot-copy p` 55.7（中文舒适区 20-40 字/行） | 全部加 `max-width` → 32 / 52 / 46 / 30 字/行 |
| 2 | **无 `:active` 按下态** | 8 个主要可交互元素 0 条 `:active` 规则；触屏无 hover ⇒ 按下去零反馈 | 补 40 条 `:active`（scale .975 + 阴影收窄 + 120ms） |
| 3 | **关键图无降级** | 17 张图里 14 张有 onerror，缺的正是 logo / **图腾主图** / **二维码** | 二维码失败→收起卡纸+给出可手输地址；图腾→回落 mark；logo→隐藏 |

### 一手踩坑
**`ch` 单位在中文下会砍半**：行长第一版用 `max-width:34ch`，实测 `.ar-note p` 从 77 字/行
掉到 **18.9 字/行**（ch 按 "0" 宽算，中文 1 字≈2ch）。改用 `em` 后回到 32 字/行。

### 门禁新增 4 条（全部反向验证）
- 行长必须有 max-width 且禁用 ch → 缺 max-width / 改成 ch 均判红
- 装饰元素必须标 `data-decorative`（240px 水印「畲」原对比度 1.04:1 被当正文判）→ 去掉即判红
- `:active` 规则数 ≥5 → 删光判红
- 二维码/图腾必须有 onerror + qr-fallback 替代块 → 删 fallback 判红

### 新增可复跑工具
`tools/design_audit.py`（八维一键）、`tools/extreme_viewport.py`（320/430/768/1440/横屏）、
`tools/zoom_test.py`（200% / 125% 缩放，WCAG 1.4.4）、`tools/originality_audit.py`（反模板扫描）。

### 本轮读数
- design_audit：对比度 **152 处检查 / 不达标 0**；h1 唯一、无跳级；:active 40 条；字阶 21 档
- 极端视口：320/430/768/1440/844×390 横屏 —— realOverflow 全 false、clippedText 全 0
- 200% 缩放等效视口 720×450：无溢出、无元素出屏
- 原创性 8/8 通过（无 UI 框架 / 无外链字体 / 无 AI 标配紫 / 无 emoji 堆砌）
- SEO/PWA：manifest 4 图标含 maskable、3 shortcuts；JSON-LD hasPart 3；og 1200×630；meta 无缺失
- CI：`39352624330` success


### 轮7 失败记录：一次「省带宽却毁功能」的优化（已回退）
- 动机：性能读表显示 statue-cut.webp 322KB 在首屏 85ms 就被请求（用户还没滚到雕刻台）。
  根因确认无误：imageGeom() 每帧都调用，而它顺带调用 imageReady(src) 发起网络请求。
- 改法：imageGeom 只算几何；加载时机收进 revealStatue，按 p<0.55 门限。
- 结果：首屏确实不再请求（省 322KB），但成品揭示被直接跳过 ——
  p=0.95 时画面仍是纯金剪影，isReady=false、图片从未请求。
  原因：该函数的 p 与 carve 的 p 不同源，加门限后它在到达揭示前就被 return，
  等于把「像素级复刻」这一核心兑现口掐掉了。
- 处置：立即 git checkout 回退，实测恢复（req=1、isReady=true、截图雕像正常）。
- 教训：优化必须先确认「改动前后的可见结果一致」，不能只看省了多少 KB。
  这次是自己多看一眼截图才发现的 —— 只跑数值判据会认为「成功」。


## 轮8 结果（2026-10-20 · 先修判据再优化：首屏 545→502KB/传输 329→284KB）

### 本轮最重要的一件事：发现体积门禁是「假绿」
首屏预算判据原先手写固定 8 个文件，漏掉 5 个必执行脚本与 2 张首屏 SVG：
  - 判据报 **381KB**，按 index.html 实际引用复算是 **542KB** —— 漏算 162KB。
  - 一条体积门禁若漏算实际会下载的东西，它就无法在体积失控时报警。
修法：① 改按 index.html 实际引用自动推导（14 文件）；② 判据改为**真实传输量**
（GitHub Pages 对 html/css/js/svg 默认 gzip；woff2 本身已压缩）；③ 原始量同时展示；
④ 字体单设 260KB 险。改完立刻变红（542>400），随后才做优化。

### 字体子集重建：238.6KB → 193.2KB（-45KB）
旧扫描口径两头都错（同一份代码里同时存在）：
  - 把 JS/CSS **注释里的汉字**算进子集 → 1249 字里 330 个只出现在注释
  - 又**漏掉 35 个真渲染的字**（防/输/显/退/额…）→ 这些字回退系统字体，
    在一行标题里出现「一半字形不同」的割裂
新口径只取会渲染的字符，汉字覆盖缺 0。

### 图标摆脱字体依赖
◎（切展柜）/✕（关闭）原用字符当图标，换系统字体就走形 → 改内联 SVG，
已确认字符彻底消失、按钮含 SVG 且带 aria-hidden。

### 门禁新增 2 条（各做反向验证）
- 字体完整性：抽掉字形 → 缺 807 字判红
- 首屏口径语义正确：第一版只检查变量名存在，把赋值写死 0 仍 PASS；
  改为脚本内**独立复算 gzip 传输量**对照 → 写死 0 / 改成原始量 / 两者相等 三种破坏均判红

### 实测读数
- 首屏：传输 **284KB** / 预算 400KB（原始 498KB；14 文件；字体 193KB / 260KB）
- 整站：1547KB / 1600KB
- 锚点跳转：8 个段落实测 top=88px，顶栏 82px，**无一被遮蔽**
- 滚动帧率：p95 3.4ms，0 卡顿；雕刻动画 218fps，p95 6.7ms，0 卡顿
- CLS = 0（零布局位移）；FCP 72ms（缓存态）/ 480ms（冷启）
- 线上 build=9，字体正常无割裂，2′32″ 上标字形正常
- CI：39355375628 success


## 轮9 结果（2026-10-20 · 动画热路径 236µs→41µs，并补上注释承诺的降档）

### 又纠正了一个用错的判据
此前用「帧率」当动画性能判据，实测 218fps 就认定有余量 —— 但帧率受 vsync 上限影响，
看不出热路径真实成本。改用**批量法测单函数成本**后看清真相：
  - 绘制 20000 次 arc+fill 仅 4.3ms（0.2µs/次）—— **不是瓶颈**
  - `_targets` 单次 236µs —— **这才是热点**（每帧跑，2634 粒子 × 约 5 次三角函数）

### 优化（视觉不变）
- 抖动/扑翼三角函数改查表（1024 项，量化误差 <0.0007，远低于 1 像素）
- 每帧常量提到循环外；drift 从对象改标量
- 中轴附近粒子旋转位移低于抖动幅度，安全跳过（约占 40%）
- 结果：**236µs → 41µs（5.8x）**；连续 100 帧无 NaN；截图形态与优化前一致

### 补上「注释一直在说、代码里没有」的东西
phoenix.js 第 3 行注释写着「低端机自动降级」，实际只有 reduced-motion 分支。补：
- 硬件分档：hardwareConcurrency ≤4 或 deviceMemory ≤4 → 粒子降到 900
- 运行时自适应：开场 90 帧实测 FPS <45 → 一次性降档
- `_rebuildLite` 真正减少**粒子对象数**
  （第一版只换目标点，实测反而慢 10%：每帧开销 = 粒子数 × 3 次 API，
   叠到同一点不减少绘制次数 —— 这个反直觉结果靠实测才发现）

### 反向验证本身也踩坑（重要）
第一版反向测试三种破坏**全绿**，我一开始以为是工具失效。
真实原因：agent-browser 打开的是缓存页面，改过的 JS 根本没加载
（证据：把 `_rebuildLite` 改名后，工具仍报「降档 2634→900」）。
改为每次清 SW + 换 URL 强制重载后，三种破坏全部判红：
  - 换回三角函数 → 151µs 超阈值判红
  - 注入 NaN → 200 个 NaN 判红
  - 删降档 → 判红

### 新增 tools/perf_anim.py
判据：`_targets` <120µs / 200 帧无 NaN / 降档确实减少粒子对象。可复跑。

### 实测读数
- `_targets` 42.5µs（阈值 120µs）
- 降档 2634 → 900 生效
- 线上 build=10，`lowEnd`/`_rebuildLite`/`_ptsFull` 均就位
- CI：39356214285 success


### 轮9 追加：两处「假绿」修复（perf_anim 工具自身）

**假绿 1：被测代码抛错被判成「环境原因跳过」**
反向测试删掉 `_rebuildLite` 后工具仍报 PASS。根因链：
探针里直接调 `p._rebuildLite()` → 函数不存在抛错 → 整个 eval 无返回值
→ 解析失败 → `run()` 返回 None → main 把 None 当「环境未就绪，跳过」→ PASS。
「环境跳过」与「被测坏了」被混为一谈。
修法：探针内 try/catch 记录 rebuildError；解析失败一律判 FAIL（宁可红不可假绿）。
修复后：删降档 → FAIL（缺少 _rebuildLite 降档能力）。

**假绿 2（工具自身的超时）**
轮询实现每次 spawn 一次 PowerShell（约 3s），累计超调用方 120s 上限，
表现为工具「跑不完」，很容易被当成环境问题忽略。
改为 open 一次 + 固定等待 + 单次 eval（等待逻辑放进浏览器内 Promise），约 28s 跑完。

**方法论**：本轮机读出的四个缺陷里，有两个在**判据自身**（首屏口径漏算、
perf_anim 假绿）。判据错的时候，越努力优化越偏。所以每轮先自检判据。

## 轮10 结果（2026-10-20 · 手机首屏 1.56 屏 → 1.00 屏 + 建议台账机制）

### 实测缺陷：手机首屏被撑成 1.3~1.56 屏
| 视口 | 修复前 hero | 倍数 | 修复后 |
|---|---|---|---|
| 360x780 | 1213 | 1.56x | 一屏 |
| 390x844 | 1183 | 1.40x | 844 (1.00x) |
| 393x873 | 1201 | 1.38x | 一屏 |
| 430x932 | 1226 | 1.32x | 932 (1.00x) |

根因：`.hero{min-height:100svh;padding-top:96px}` + 手机单列布局下
`.hero-visual{min-height:clamp(320px,58svh,620px)}` → 内容超出视口。
后果：用户要滚一屏多才过首屏；凤凰画布被拉到 1183px，粒子纵向摊薄。
修复后手机首屏凤凰完整居中可见。

### 修这条时踩的两个坑（都已记录）
1) **CSS 源码顺序**：先把新规则插到旧规则前面 → 被后面 `.hero-visual` 的 clamp min-height 覆盖。
   靠浏览器读数 `align=center`/`padTop=96px` 才发现「新规则没赢」；光看源码会以为改好了。
2) **测试工具自己骗人**：`hero_height_test` 第一版每次用同一 URL，SW 返回缓存旧 CSS，
   CSS 已修好（实测 heroH=844）脚本却仍报 1183。改 close --all + 唯一 URL 后恢复真实。

### 升级建议台账机制（老大要求：以后不用提醒）
新建 `memory/09-upgrade-ledger.md`，规则写在文件头：
**每轮结束前必须把当轮提出的所有建议登记为 U-xx**，不等提醒。
两级区分：台账 = 所有提出过的（含待排期/已否决）；05-next-steps = 已决定要做的。
已回填 U-01~U-08。00-index / 05-next-steps 均已加指针。

### 新增 tools/hero_height_test.py
判据：360/390/430 三档 hero/vh <= 1.05。浏览器无响应时打 SKIP 而非误判。

### 读数
- 线上 build=11，390x844 实测 hero=844/844 = 1.00x
- CI：39359940355 success

## 轮11 结果（2026-10-20 · 台账推进 U-07 完成 / U-08 实测否决）

### U-07 装饰环溢出 — 已修
实测 390x844：totem-ring.b 用 inset:-5% 向外扩，宽 399px > 视口 390（左右各溢 5px），
全靠祖先 overflow 裁切兜住 —— 隐式依赖，换容器就露横向滚动。
修法：inset:-5% → inset:0 + transform:scale(1.09)；hero-ring.b 加宽 → scale(1.10)。
transform 不参与布局盒计算，天然不溢。
修复后：hero-ring[64,326] / hero-ring.b[34,356] / totem-ring[17,373] / totem-ring.b[16,374]
—— 全部在 390 内，且保持「外环包住内环」的同心关系。
新增 tools/ring_containment_test.py（静态 + 浏览器双轨判据），反向验证恢复 inset:-5% 判红。

### U-08 入口体积（defer）— 实测否决
数据：9 个脚本共 162KB 全同步无 defer，但**全部在 18ms 内执行完、0 个长任务**；
DCL 223ms / FCP 216ms 与脚本无关（屏蔽字体后 FCP 反而变 520ms，证否「字体阻塞」假设）。
结论：加 defer 收益≈0，不值得引入执行顺序风险。**按数据否决，不为指标而改。**

### 两个真问题（方法论级别）
1) 判据基准错：最初用 scrollWidth > clientWidth 判溢出，但内容把视口撑宽时两者会一起
   变成 1248，比值永远不成立 → 漏判。基准必须是 window.innerWidth。
2) **修复被自己的测试覆盖丢失**：U-07 改完一直没提交，反向测试脚本原地改真实 CSS，
   跑了几轮后修复被覆盖没了（git checkout 时才发现恢复的是未修版本）。
   教训：修复先落盘再跑破坏性测试；破坏性测试必须在副本上做。

### 读数
- 门禁：verify_site PASS / ring_containment PASS
- CI：39363573624 success，线上 build=12

## 轮12 结果（2026-10-20 · 安全沙箱根治「测试覆盖真实文件」）

### U-09 已根治
轮11 事故根因不是某个脚本写错，而是**范式错**：破坏性测试原地改被 git 跟踪的文件。
备份→改→还原，一旦中断还原就不执行，未提交的修复直接丢。

新建 tools/safe_mutation.py：
  1. 前置检查 git status，脏工作区**拒绝跑**（未提交 = 可能被覆盖的东西）
  2. site/ 与 tools/ 复制到临时目录，在副本上改
  3. try/finally 保证副本清理
  4. 结束用 SHA256 逐个核验真实工作区**一字节未变**，变了告警
三条保证均实测成立。16 个旧脚本已加废弃头部。

### U-10 已根治：门禁不再依赖浏览器
ring 判据原来用浏览器量 getBoundingClientRect，但 agent-browser 在本机频繁卡死
（set viewport 可超时 90s），既不可靠也无法在沙箱里跑。
U-07 根因完全是代码写法 → 改纯静态判据，秒出、任意环境可跑：
  · 禁用负 inset / 禁用 >=500px 的 width 上限 / keyframes 必须保留 scale
已并入 ci_design_static，CI 实测执行到该判据：
  [PASS] 装饰环不溢出：无负 inset / 无超宽 width / keyframes 保留 scale

### 反向验证（沙箱内，真实文件零改动）
三种破坏全部判红：负 inset / 超宽 width / keyframes 丢 scale。
真实 CSS sha256 全程不变。

### 读数
- CI：39364386781 success
- 门禁：verify_site PASS / ci_design_static PASS（含 ring 判据）

## 轮13 结果（2026-10-20 · backdrop-filter 白算清理 + 三条静态门禁）

### 找到的浪费
backdrop-filter 的结果绘制在元素背景**之下**，背景不透明时被完全盖住但仍在计算。
实测两处：
  .nav.solid   rgba(11,9,8,.92)  + blur(8px)   —— position:fixed 全宽，滚动时一直白算
  .toast       rgba(18,16,15,.95) + blur(10px)
基础态 .nav 是渐变背景（末端透明），blur 那里有效果，保留。

### 一个必须先承认的错误
我最初写的是「去掉 blur 视觉零变化」。核算后发现 0.92/0.95 并非完全不透明：
透出的 8%/5% 会从「模糊」变「清晰」。量级极小但「零影响」站不住。
规范做法：把背景提到 alpha=1（#0B0908 / #12100F），此时关 blur 才是**严格**零影响。

### 新增 tools/prove_no_visual_change.py
可复跑核查 backdrop-filter 用法与背景不透明度是否自洽：
  当前全部 OK：.nav/.menu 渐变（blur 有效）、.carve-hint/.ar-dots alpha=.55（有效）、
  .nav.solid 不透明且无 blur。

### 静态门禁增至 4 条（全并入 ci_design_static，CI 可跑，无浏览器依赖）
1. 手机首屏锁定一屏（height/min-height 100svh + visual min-height:0 + 源序正确）
2. 装饰环不溢出（无负 inset / 无超宽 width / keyframes 保留 scale）
3. 不透明背景不得保留 backdrop-filter
4. 原有：按下态 / 行长 em / 零框架 / 字体自托管 / 无 AI 紫
反向验证：加回 toast 的 blur → 判红；改回 visual min-height:58svh → 判红。

### 环境限制（如实记录）
agent-browser 守护进程报 "daemon configuration mismatch"，kill + 清 ~/.agent-browser 后仍复现，
本轮无法取帧读数或截图。性能判断改由 CSS 合成语义确定性推导，防护由静态门禁承担。

### 读数
- CI：39365608408 / 39366095081 均 success
- 四门禁全 PASS
- 线上 build=14

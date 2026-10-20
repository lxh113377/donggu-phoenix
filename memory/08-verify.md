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

## 轮14 结果（2026-10-20 · 恢复浏览器环境 + 段落留白冗余清理）

### U-14 真正的根因：我自己删掉了 Chrome 本体
轮13 我把 agent-browser 的报错判成「环境故障」，实际是我执行了
  Remove-Item -Recurse 用户目录下的 .agent-browser
那个目录**不只是配置，还装着 Chrome 本体**（browsers/chrome-155.0.8059.84）。
删掉后报 "Chrome not found"，我却归因成软件缺陷，白绕一整轮。
处置：agent-browser install 重装（197MB），浏览器完全恢复。
新增 tools/browser_health.py：静态区分「Chrome 本体缺失」与「进程冲突」两类不同故障。
教训（U-17）：破坏性操作前必须确认目录语义；不确定时改名备份，不要直接删。

### 段落顶部留白冗余（移动端每段多推 50~60px）
实测 390x844：
  .totem       padTop 136px（标准 --sec-y 是 76px）
  .carve-sec   padTop 130px
  .ar-gallery  padTop 126px
根因：html 已设 scroll-padding-top:88px，锚点跳转后段落顶部精确落在 88px，
顶栏遮挡**已解决**；这三段又各自写 padding-top:calc(...) 做第二次补偿 —— 冗余。
处置：统一改 padding-top:var(--sec-y)。
实测 #totem 标题从 224px 上移到 164px，仍在顶栏 82px 之下 82px，无遮挡。
截图确认图腾/雕刻台/AR 三段排版更紧凑且不拥挤。

### 门禁新增 1 条（CI 可跑）
「段落顶部不得写死补偿值」并入 ci_design_static。
本轮正是靠它一次性发现 .carve-sec / .ar-sec 两处同类问题（原本只发现 .totem）。

### 读数
- 线上 build=15，手机端 totemPad=76px / carvePad=76px / hero 844÷844=1.00
- 移动端三屏截图复核：首屏一屏、图腾完整、各段标题紧跟顶栏
- CI：39367429185 success

## 轮15 结果（2026-10-20 · 页面零改动，判据修正两次）

### 结论先行
本轮逐屏复核了桌面端与移动端，**未发现需要改动的页面缺陷**：
  · 段落留白已全部统一（桌面 148px，移动 76px，仅 hero 84px 为固定导航留位）
  · 字号分布合理（11px 仅用于标签/编号/出处，正文 14~16px）
  · 标题单行无断行；H2 里的 <small> 英文副标题是设计意图，不是折行缺陷
  · 雕刻台 carve-shell 1180x614（占视口 0.68），比例正常
所有真实产出都发生在**判据**上。

### 判据误判一：全部 SKIP 却判 PASS（假绿）
新写的 reveal 检查工具，8 个锚点全部 SKIP（探针没取到读数），
循环 continue 后失败列表为空 → 打印「PASS 全部段落跳转后无隐藏元素」。
「一个都没测到」与「都测过且通过」被混为一谈 —— 与轮9 perf_anim 同一类错误。
修法：三态区分；全 SKIP 明确打印 SKIP 且不计入 PASS。

### 判据误判二：把「视口外」当「该显示却没显示」（误报）
修好取数后得到 3/8 FAIL，差点当资料缺陷去改代码。逐个诊断：
  #totem 的 totem-copy top=869 > vh=844，在视口下方，IO 本就不该触发；
  继续滚动 400px 后它正常 opacity=1 且带 in 类。
即「视口外且隐藏」是正确行为。修法：只判「视口内却 opacity<0.9」。

### 修正后
8/8 段落跳转后视口内无隐藏元素，0 SKIP（全部真实测到）。
反向验证：人为把 #culture 的 reveal 设回 opacity:0 → 判据读出 bad=2。

### 读数
- CI：e21820e 已提交（页面代码未变，build 保持 15）
- tools/reveal_after_jump_test.py 可复跑


## 轮16 结果（2026-10-20 · 两处真实缺陷：H1 文案重复 + 商品图溢出）

### 转向内容与渲染质量后，立刻找到两个「自动化判据查不出」的问题

**缺陷一：H1 主标题重复两遍**
main.js:40 的运行时拼接
  t.innerHTML = C.hero.line2 + '<em>' + C.meta.title + '</em>'
数据：line2='凤鸣东固'，meta.title='畲 · 凤鸣东固'（已含 line2）
运行时 H1 实际文本 = '凤鸣东固畲 · 凤鸣东固'
后果：主标题视觉出现两次、读屏念两遍；
      且 em 用 Cinzel（实测 0 个汉字字形），中文全部回退系统字体。
修法：副标题改纯拉丁 '畲 · SHE PHOENIX'，Cinzel 正好覆盖拉丁。
注意：静态 HTML 里本来是对的，是 JS 在运行时覆盖成重复文本 ——
      这就是静态门禁查不出、必须真打开页面看渲染结果的原因。

**缺陷二：商品图溢出压住「现有延续」标签**
实测：.merch-shot 高 196px，图片实测 218~237px，底部溢出 69px，压住 .tier 标签。
根因：.merch-shot 是 display:grid 且未定义行高 → 隐式行高被图片撑到 279px；
      此时子项 max-height:78% 的基准变成 279（行高）而非 196（容器高），
      78%×279≈218px —— 正是实测值。
修法：grid-template-rows:100% 锁行高 + 图片固定 max-height:150px（特写大格 320px）。
验证：所有商品 tierOverlapsImg 由 true 变 false。

### 门禁新增 2 条 + 自己踩了两次误报
gate 21（H1 不得重复拼接）、gate 22（grid 行高锁定 / 禁百分比 max-height）。
两次误报均已修正：
  1) 正则范围过宽，把特写大格的 76% 也算进去（那相对 420px 大容器，合理）
  2) 规则含中文注释，先 replace(' ','') 再判子串会失败
修正后三种破坏均判红（沙箱内，真实文件零改动）。

### 读数
- 线上 build=16：H1='凤鸣东固畲 · SHE PHOENIX'，商品图 max-height=150px
- CI：39368844216 success
- 静态门禁增至 9 条，全部在 CI 里跑


## 轮17 结果（2026-10-20 · 头像 alt 重复 + 字体门禁两处误报）

### 真实缺陷：工匠头像 alt 导致读屏念两遍人名
main.js 里头像 alt 直接取 p.name，而紧接的 h3 也是 p.name：
  读屏依次念：图「刘节明」→ 标题「刘节明」
头像是 74px 圆形小图，这个尺寸下长相不承担识别作用。
修法（WCAG H67）：alt="" + aria-hidden="true" 明确声明装饰。
实测读屏顺序变为：(跳过装饰图) → 刘节明 → 角色 → 引言，人名只念一次。
新增门禁：装饰性头像 alt 不得与标题重复（反向验证判红两条）。

### 三处检查结论：无缺陷
· 布局：桌面 1440 / 移动 390 均无横向溢出、无文本裁切
· 键盘：43 个可聚焦元素、焦点顺序合理、有 focus-visible、有 skip-link
· 图片质量：五处共 49 张图，无变形/模糊/加载失败

### 一个差点误判的测试方法（已修正并工具化）
第一版图片检查是「滚遍全站 → 滚回顶部 → 检查」，
12 张商品图全部报 complete=false / naturalWidth=0，差点当生产缺陷。
实测：滚到 merch 后查 → complete=true、naturalWidth=620、visible。
原因：滚回顶部后图片离开视口，浏览器回收已 decode 的位图，
「离开视口后 complete=false」是正常现象。
新增 tools/image_quality_test.py：停在目标区域再检查（49 图 0 问题）。

### 字体门禁两处误报（都是我写中文注释触发的）
1) HTML 注释「声/念/确」被当渲染文本 → 扫描前剥 <!-- -->
2) JS 注释里的 alt="" 两个引号把注释切成「字符串」
   → 「读屏会连续念两遍」「明确声明跳过」被当内容
   → 扫描前剥 /* */ 与 //
剥完仍缺 1 字「预」，来源 main.js 的 '（当前为本地预览）'
（setAttribute('title') 的 tooltip，**真实会显示**）→ 这个字确实该进子集。
重建：补「预」+ 去掉 143 个被注释带进来的字。
结果：字体 193.2KB → 172.6KB，汉字覆盖缺 0，首屏传输 284KB → 268KB。

### 读数
- 线上 build=17，CI：39369865647 success
- 干净克隆复验：verify_site PASS / ci_design_static PASS
- 首屏传输 268KB / 400KB；字体 173KB / 260KB
- 静态门禁 11 条


### 轮17 附记：一次 CI 失败的真实原因（非代码问题）
提交 b13411f（只改两个 memory/*.md）后 CI 跑了 5m38s 并失败。
日志显示卡在 Set up job：
  Failed to resolve action download info. Error: The HTTP request timed out after 00:01:40
连续重试三次后放弃 —— 是 GitHub Actions 拉取 action 元数据的网络超时，
与仓库代码无关。gh run rerun 后 32 秒成功。
判别依据：失败点在「Set up job」且报 action download 超时，说明作业根本没进到
checkout/verify 步骤，不可能是代码引起。


## 轮18 结果（2026-10-20 · 统一源码扫描层，根治系统性误报）

### 先处理系统性风险，而不是修单个门禁
轮17 连续两次同源误报（HTML 注释被当渲染文本、JS 注释里的引号切出假字符串），
但当时只修了字体判据那一处。本轮排查发现：
  · design_audit.py       读源码后**完全不剥注释**
  · originality_audit.py  同上
  · ci_design_static.py   只局部剥过
风险：只要我的注释里出现「Inter」「#667eea」「tailwind」这类字样就会误报。
而我的注释越写越详细 —— 这是必然会被触发的。

### tools/source_scan.py（统一扫描层）
  visible_text(html)    剥 <!-- -->、script/style、解实体，保留 data-decorative 单字
  strip_js_comments(s)  状态机逐字符扫描，跟踪字符串状态
                        → 注释里的引号不干扰；字符串里的 // 不被误删
  js_strings(s)         只取真正的字符串字面量
  stripped(css)         剥 CSS 注释
  selftest()            四个反向用例自带（含 "https://" 不被当注释）
三个判据全部接入。自检 PASS。

### 双向验证（沙箱内，真实文件零改动）
① 注释注入违禁词 tailwind/bootstrap/#667eea/fonts.googleapis.com
   → 判据退出码 0，**不误报**
② 真实代码注入 #667eea
   → 判据退出码 1，**仍被抓到**
② 是关键：证明剥注释没把真问题一起剥掉。

### 用修好的判据复扫
原创性 8/8 通过；backdrop-filter 实际 5 处规则（第 6 次计数是 .nav.solid 的 none）。

### 读数
- 线上 build=17（本轮未改页面代码）
- CI：39371277595 success
- 干净克隆复验：verify_site / ci_design_static / source_scan 全 PASS


## 轮19 结果（2026-10-20 · 转向内容叙事，找到两处真实文案问题）

### 一、「38 年党龄」是写死的相对时间
采访稿（2025-07-08）原文：「我是 1987 年入的党」。
38 = 2025 - 1987，是**采访当时**的党龄。
但站点长期在线：2026 年应为 39，2027 年 40 —— 写死数字会逐年失真。
改法：锚定不变事实「1987 年入党」（index.html 与 culture.js 两处）。
新增门禁：文案不得写死「N 年党龄/工龄/教龄/军龄」（反向验证判红）。

### 二、集章动线归属困惑
ar-data.js 原写「三枚集齐生成一条完整的「东固 · 匠灵幻境」动线」。
但：
  · 集章功能在**本站**实现（ar.js 有完整 stamps 逻辑）
  · 「东固 · 匠灵幻境」是项目原始规划的 AR 小程序名（docs/交付说明.md），
    页面上从未解释这个名字
读者会以为集章要依赖另一个未上线的小程序。
改为：'每段结束落一枚印章，三枚集齐即解锁完整动线'。

### 三、核对过但确认无问题的项（有据可查）
  · 非遗级别：项目「东固传统造像」= 国家级（2014 第四批）✅
    刘节明 = **省级**非遗传承人 ✅
    依据采访稿原文：「（刘节明，省级非遗传承人…）」「我作为省级非遗传承人时…」
    两者不矛盾（项目国家级、传承人省级），页面表述准确。
    注意：docs 引用的报纸标题写「国家级非遗项目东固传统造像代表性传承人」——
    那是「国家级项目的传承人」的口径，与页面「省级传承人」不冲突。
  · 数字自洽：3 段 / 13 章；152 秒 = 72 + 44 + 36 ✅
  · 术语一致性：非遗/图腾/造像/一木成像 分布合理，无混用矛盾

### 四、误判记录
改完 culture.js 后页面仍显示旧值，一度以为 SW 缓存。
实测：磁盘文件正确、浏览器 fetch 正确（has1987=true），
是我读了**未刷新的旧 DOM**。重新加载后两处均为新值。
教训：验证数据改动要看「fetch 到的源」或「重新加载后的 DOM」，
不能读改动前渲染的旧节点。

### 读数
- 线上 build=18，CI：39372142989 success
- 干净克隆复验：verify_site / ci_design_static 全 PASS
- 静态门禁 13 条


## 轮20 结果（2026-10-20 · AR 章节解说词中英对等审查）

### 发现方式
逐条比对 ar-data.js 的 13 组 body / enBody 配对，按「英文词数 / 中文字数」比例筛出偏低项，
再逐条人工核对是否真丢信息。
英文确实渲染在页面上（display:block），是读者可见的真实缺陷。

### 5 处信息不对等（已补齐）
7.  中文引毛泽东《渔家傲》「雾满龙冈千嶂暗，齐声唤，前头捉了张辉瓒」
    英文原只写 "annihilated" → 补诗句英译
8.  中文「毛泽东、朱德…歼敌七千余人」「白云山头云欲立」
    英文丢了两位人名、歼敌数字、诗句 → 全部补上
9.  中文「年仅 33 岁」「就把我埋在东固，我喜欢这里的人民，喜欢这里的山和水」
    英文原只写 "He asked to be buried in Donggu." → 补年龄与完整遗言
    （全文最动人的细节，英文读者原本完全没拿到）
12. 中文「每一位畲族女性，都被视作三公主的化身」
    英文原止于 "never in rank" → 补核心论点
13. 中文「山歌一开口，凤凰就落在东固」
    英文原止于 "birdsong" → 补结尾诗意句

比例变化：0.30→0.75 / 0.34→0.73 / 0.35→0.55 / 0.31→0.67 / 0.29→0.50

### 我自己引入的一个错误（已修）
补英文时写成 Markdown 斜体 *Pride of Fisherman*，
但页面是纯文本渲染，读者会看到字面量 "*Pride of Fisherman*"（带星号）。
改为 “Pride of Fisherman”。已在门禁里加「英文不得含 Markdown 标记」判据。

### 新增 tools/bilingual_parity_test.py（纯静态，CI 可跑）
判据：
  · 英文词/中文字 >= 0.30
  · 中文里的年份英文必须保留
  · 中文引诗句时英文需有对应引文
  · 英文不得含 Markdown 标记
反向验证三种破坏全部判红，且定位精确：
  A 英文砍短 → 第 7 组比例 0.09
  B 加 Markdown → 第 1 组标记命中
  C 丢年份   → 第 9 组丢 1931

### 读数
- 线上 build=19，CI：39372698739 success
- 干净克隆复验：verify_site / ci_design_static / bilingual_parity 全 PASS
- 静态门禁 14 条


## 轮21 结果（2026-10-20 · 出处从「只有数字」变成可溯源）

### 缺陷：数据齐全，但读者拿不到
ar-data.js 里每个场景都有完整 sources 数组（label + url），实测 8 条来源、4 条有链接。
但 ar.js 只渲染「素材出处 N 条」这个数字，**从不展示具体内容**，也没有对应 CSS。
读者/评审看到「2 条」却点不开、看不到是什么 ——
这正是评审会质疑「出处标得实不实」的地方。
这是典型的「静态检查数据存在会通过、实际体验是空的」。

### 修法
renderCards 里把数量 span 换成原生 <details>：
  · 默认收起（不占版面、不打断阅读流）
  · 点开逐条列出 label；有 url 的渲染为可点击链接（target=_blank rel=noopener noreferrer）
  · 链接只在用户主动点击时发起，不违反「页面自身零外部请求」
配套 .ar-src 样式：summary 沿用 .kick 语言（小字/字距/金色），默认 ＋、展开 －，
focus-visible 有可见焦点环。

### 验证
三张卡片渲染「4 条 / 2 条 / 2 条」，条目 4/2/2、链接 3/1/0，默认收起。
展开截图确认第一条 4 条出处完整可见、可点击。线上 build=20 复验一致。

### 顺手完成的出处审计（结论：无缺陷，出处扎实）
  · **13 章全部有 note 标注**，一处不缺
  · 8 个独立来源：刘卷《装饰》2015(7)、吉安市人民政府、井冈山报、江西日报、福建省文物局、
    东固革命根据地博物馆、刘节明独家专访、东固畲族乡田野素材
  · 分布合理：红色 4 章共用《江西日报》同一篇、图腾 4 章共用福建省文物局同一份
  · **4 个引用链接实测 HTTP 200 全部可访问** —— 出处无编造
  · 日期自洽：2026-08-10 的报纸在当前时间（2026-10-20）之前，合理

### 新增门禁
「出处数据必须渲染给用户（非仅数量）」并入 ci_design_static。
反向验证：把 details 换回纯数量 span → 判红。

### 读数
- 线上 build=20，CI：39373372518 success
- 干净克隆复验：verify_site / ci_design_static 全 PASS
- 静态门禁 15 条


## 轮22 结果（2026-10-20 · 死数据清理 + 「数据必须有消费者」门禁）

### 排查
用「数据字段是否出现在前端代码里」做静态对账，发现 8 个字段从未被引用。

**会误导的（已处理）**
1. culture.js meta.year='2025' 而页面 menu-foot 写 2026。
   核实后两者都对：2025 是**田野调研年份**（采访稿 2025-07），2026 是**交付年份**。
   问题是字段名 year 含义模糊 → 改名 fieldworkYear 并加注释。
2. ar-data.js meta.subtitle / weight 是**旧版文案**，
   HTML 第 207/219 行已有更完整表述（多了零第三方库/零外部请求/降级说明）。
   留着会让维护者误以为那是当前文案 → 删除（ar-data.js 8884 → 8779 字节）。

**无害冗余（保留 + 白名单说明）**
  · culture.js hero.line1「畲」——首屏水印已在 HTML 写死
  · ar-data.js costumes —— culture 段「一生」章节已完整覆盖三式
  · ui.stampNew / tapScene —— 预留文案

### 新增 tools/dead_data_test.py
检查数据字段是否在前端代码出现；不在且未登记白名单则判红。白名单须写理由。
结果：56 个字段 = 50 有消费者 + 6 预留 + 0 无消费者。

### 又一次「假绿」自查（重要）
第一版正则写成 r'^\\s{2,6}(\\w+):\\s'（raw string 里双反斜杠 = 字面量反斜杠），
**一个字段都没匹配到** → 打印「检查 0 个字段」→ RESULT: PASS。
典型的「没测到 = 通过」。与轮9 perf_anim、轮15 reveal 同一类错误，这已是第三次。
修正正则后检查 56 个字段。
→ 已把「检查到 0 个对象必须判 SKIP/FAIL」写进教训。

### 验证
清理后全部门禁 PASS；页面渲染复验：
H1 正确、AR 卡片 3、出处块 3、文创 12、文化 4 段、console 错误 0。

### 读数
- 线上 build=21，CI：39374071763 success
- 干净克隆复验：verify_site / ci_design_static / dead_data 全 PASS
- 静态门禁 17 条


## 轮23 结果（2026-10-20 · 零样本守卫做成机制）

### 为什么这轮做机制而不做功能
「零样本判 PASS」这个结构错误连续三轮复发：

| 轮次 | 工具 | 症状 |
|---|---|---|
| 9  | perf_anim          | 探针抛错 → 解析失败 → None → 当环境跳过 → PASS |
| 15 | reveal_after_jump  | 8 个锚点全 SKIP → fails 空 → PASS |
| 22 | dead_data_test     | 正则写错 → 匹配 0 字段 → PASS |

共同结构：
    results = collect()        # 可能为空
    for r in results:          # 空集合 → 循环不执行
        if bad(r): fails.append(...)
    if fails: FAIL else: PASS  # fails 空 → PASS
「检查了 0 个对象」与「检查了 N 个且都正常」被当成同一件事。
单靠「下次注意」显然无效 —— 第三次了。

### tools/gate_guard.py
verdict(checked, fails, allow_zero=False, what='对象') → (code, msg)
  1. checked==0 且未显式允许 → **SKIP**（不是 PASS）
     SKIP 退出码 0（不阻塞 CI，可能是环境问题），但绝不打印 PASS
  2. checked==0 且 allow_zero=True → PASS（显式声明空集合合法）
  3. fails 非空 → FAIL
  4. 其他 → PASS
SKIP 不用 FAIL 的理由：环境问题与被测对象有问题必须分开，
否则 CI 因环境抖动变红，人们就学会忽略红灯。但 SKIP 必须可见且不计入 PASS。

### 已接入 + CI 强制执行
dead_data_test / ring_containment_test 接入守卫；
CI 新增 Guard self-test 步骤（跑 gate_guard 自检 + dead_data_test）。
CI 日志确认执行：5 个守卫用例全过、56 个数据字段全部通过。

### 验证
· gate_guard 自检 5 用例全过（含「零样本 + fails 有值」仍判 SKIP）
· 复现轮22 真实假绿：同一个坏正则，旧逻辑 PASS，新逻辑 SKIP
· 零样本实测（两个数据文件都清空）→ SKIP「未检查到任何数据字段」
· 正常场景：56 字段 / 4 装饰环规则全部通过
· 输出现在带「检查了 N 个」——可复核，不再只有结论

### 一个测试设计错误（记录）
第一次测零样本时只清空了 culture.js，结果仍报 31 个字段 PASS ——
因为 dead_data_test 同时读 culture.js 与 ar-data.js。
不是守卫失效，是测试没把两个文件都清空。修正后 SKIP 正确。

### 读数
- 线上 build=21（本轮未改页面）
- CI：39374513623 success；Guard self-test 步骤已执行
- 静态门禁 18 条（新增守卫自检）


## 轮24 结果（2026-10-20 · 守卫扩展到剩余门禁工具）

### 盘点
逐个分析 31 个工具脚本，区分「门禁类」与「一次性反向验证脚本」。
门禁类 6 个中：
  · 3 个已自带零样本处理：bilingual_parity / image_quality / reveal_after_jump（不必改）
  · 2 个有真实风险：perf_anim / prove_no_visual_change（本轮接入）
  · hero_height_test 的零样本已判 FAIL（找不到规则即失败），安全

### perf_anim 的真实风险
· d is None / 'error' in d → 直接 return 0（静默跳过，连 RESULT 都不打印）
· 若探针返回但 particles == 0（凤凰未初始化），所有检查都不触发 → PASS
  「0 个粒子」不是性能达标，是没测到。
改法：零样本 → SKIP；环境跳过也打印明确 SKIP 行；checked 用粒子数。

### prove_no_visual_change 的真实风险
若 CSS 里没有任何 backdrop-filter（比如全站重构掉了），
oks 与 warns 都为空 → 打印 PASS「所有用法自洽」，但一个都没检查。
改法：checked = len(oks)+len(warns) 交守卫；warns 仍返回退出码 0（保持原语义）。

### 验证（沙箱内，真实文件零改动）
· prove：删光所有 backdrop-filter → SKIP「未检查到任何 backdrop-filter 用法」
· perf_anim：三种情形 — 正常 PASS / 零样本 SKIP / 零样本+fails 仍 SKIP
· 正常场景：perf_anim「2634 个动画性能样本全部通过」、prove「5 个用法全部通过」

### CI
Guard self-test 步骤加入 prove_no_visual_change。
CI 日志确认执行：5 个 backdrop-filter 用法逐条列出并判定。

### 顺带修的两个小问题
· perf_anim 的 import 首次插入失败（文件头是 import json, subprocess... 而非 import os），
  按行号定位后重新插入。
· prove 的输出有重复「RESULT: PASS  PASS」前缀，已清理。

### 关于 reverse_*.py 不接入的理由（U-40 已否决）
它们本身就是「构造破坏 → 看判据是否判红」的脚本，零样本对它们不构成假绿风险；
它们并不产出 PASS/FAIL 结论供 CI 使用。逐个加守卫是过度工程。

### 读数
- 线上 build=21（本轮未改页面）
- CI：39375003371 success；Guard self-test 已包含 prove
- 静态门禁 18 条


## 轮25 结果（2026-10-20 · 对比度从「凭感觉」变成量化判据）

### 结论
**页面当前无对比度缺陷**：119 处文本全部达 WCAG AA。
本轮的实际产出是把这件事变成可复核的判据。

### 三次失败的过程（都记进了工具注释）
**尝试 1：CSS 解析**
主 CTA 按钮算出 1.05:1 —— 荒谬。
原因：按钮背景是 linear-gradient，backgroundColor 是 transparent，
解析器一路找到页面深色底 → 「深字 + 深底」= 1.05。
像素实测应为 9.06:1。

**尝试 2：像素采样（极值）**
报 53 项不达标 —— 明显过度。
原因：取「最亮/最暗 10%」会被抗锯齿边缘、卡片边框、装饰线干扰。

**尝试 3：像素采样（固定坐标）**
报文创 1.14:1 —— 原因：固定取 arr[380:520, 150:1250]，
与实际元素位置无关，采到的可能是空白处。

**正确做法：浏览器计算色 + alpha 合成**
  · getComputedStyle(el).color 取前景（含 alpha）
  · 向上遍历找第一个 alpha>0.9 的实色背景
  · 前景按 alpha 与背景合成后算对比度
结果：正文 rgba(244,237,225,0.74) on #0B0908 → **9.42:1**。

### tools/contrast_audit.py
· 119 处文本，0 处不达标
· 渐变文字（background-clip:text）跳过并计数 —— 主标题「凤鸣东固」就是这种，
  不跳过会误算 1.00
· checked==0 → SKIP（接入零样本规则）

### 反向验证踩的坑（值得记）
第一次反向测试：改 CSS 后工具仍报 0 处不达标，我一度以为工具坏了。
真实原因：**HTTP 缓存**，浏览器加载的仍是旧 main.css。
站点本身有版本对账守卫（CSS --build ≠ HTML BUILD 时清缓存重载），
但我的测试用唯一 URL 打开了页面，绕过了 sessionStorage 状态，守卫没触发。
改为「about:blank 重置 → 正常 URL」后验证成功：
把 --fg-dim 改成 #12100E → 工具准确报 66/119 不达标、对比度 1.05、色值正确。

### 读数
- CI：39376452867 success
- 静态门禁 18 条（对比度工具需浏览器，不进 CI）
- 页面代码未改，build 保持 21


## 轮26 结果（2026-10-20 · 补上 AR 核心功能的端到端验证）

### 为什么这轮最有价值
前二十多轮我验证的全是**静态资产与 CSS**：体积、字体子集、对比度、出处、文案对等、
装饰环、首屏高度…… 但**AR 播放这个站点主体从未系统验过**。
它是 3 段 / 13 章 / 152 秒的核心，如果它坏了，页面再精致也没意义。

### 9 项既有门禁全过（复跑确认）
verify_site / ci_design_static / gate_guard / dead_data / bilingual_parity /
ring_containment / hero_height / contrast_audit(119 处 0 不达标) /
image_quality(49 图 0 问题)
读数：部署体积 1488KB / 1600KB；首屏传输 269KB / 400KB。

### 新增 tools/ar_e2e_test.py（6 项）
1-2. AR API 就绪（window.__ar + AR_DATA.scenes=3）
3-5. 三段切换 craft / red / phoenix 全部成功
6. 时间推进（t 2.1 → 4.8）
7. 完整播放落章（stamps=['phoenix']，页面点亮 1 个章）
结果：**RESULT: PASS  AR 核心功能 6 项全部通过**

### 一个差点误判的坑
我先用 seek(70) 把 craft 段（72 秒）推到段末，集章仍是空的，一度以为集章坏了。
读源码发现：

    if (state.playing) {
      state.t += dt / 1000;
      if (state.t >= state.scene.duration) { ... complete(); }
    }

complete() 只在 **playing 分支**里调用，seek() 直接跳转不经过该分支。
设计如此，不是缺陷。正确测法：seek(duration-3) 再 play() 让它自然跑完。
已写进工具注释，避免下次再误判。

### 覆盖边界（诚实说明）
· 不测摄像头实景叠加 —— 需真实摄像头权限，属环境缺口
· 不测画面视觉质量 —— 只验证状态机与落章逻辑

### 读数
- 线上 build=21，CI：39377653024 success
- 检查工具累计 10 个（静态 7 + 浏览器 3）

## 轮27 结果（2026-10-20 · 留白节奏：从匀速到有起伏）

### 发现（Awwwards 评审视角复盘）
实测 8 个 section 的 padding-top，唯一值是 **[148]** —— 全站 11475px 的滚动，
每一屏上下留白完全相同。但内容密度差 **5.6 倍**：

| 段落 | 内容高 | 留白比 |
|---|---|---|
| merch | 2016px | 14.7% ← 最密 |
| scan  | 357px  | 59.4% ← 最疏 |

同样的补白在 merch 显得局促（12 件商品被切断），在 scan 显得空旷。
滚动是匀速的，没有「呼吸感」的层次。

### 做法：按实测内容密度分级
新增 4 个派生令牌，保留 --sec-y 作基准：
  --sec-y-tight  clamp(62px,7.5vw,104px)
  --sec-y-snug   clamp(76px,9vw,126px)
  --sec-y-roomy  clamp(100px,12vw,170px)
  --sec-y-loose  clamp(108px,13vw,185px)

桌面实测结果：126 / 148 / 148 / 126 / 126 / **104** / 170 / **185**
移动实测结果：76 / 76 / 76 / 76 / 76 / **62** / 100 / **108**（无横向溢出）
总高 11475 → 11336px（省 139px）

### 新增 tools/rhythm_test.py（4 条判据，接入 CI）
1. 分级令牌必须存在
2. 至少 3 个级别被实际使用（只剩一两个 = 退回匀速）
3. 内容最密的 #merch 必须用最紧级别
4. 内容最疏的 .foot/scan 必须用最松级别

反向验证：A 把 #merch 改回统一 → 判红；B 把 .foot 改回统一 → 判红。
CI 日志确认执行：「使用 4 种留白级别」「RESULT: PASS 留白节奏分级成立」。

### 过程中踩的两个坑（如实记录）
1. 改完 CSS 后测量发现 padding 没变，一度怀疑选择器优先级。
   实际是**浏览器 HTTP 缓存**。用 about:blank 重置 + 正常 URL 后才生效。
   这已是第二次被同一问题误导（轮25 对比度那次）。
2. 修「注释未闭合」时误判：打印出的上下文显示 `== RHYTHM-MAP`，
   我以为是缺了 `/*`，结果原文是 `*/` + 换行 + `/*`，我又插一个导致结构损坏。
   立即撤销。教训：改动前先看完整上下文，不要只看局部片段。

### 读数
- 线上 build=22，CI：39378417765 success
- 对比度复验 119 处 0 不达标（留白改动无副作用）
- 静态门禁 19 条

## 轮28 结果（2026-10-20 · 入场时序分层）

### 发现
实测 22 个 .reveal 元素：
  · 21 个网格子项已有 --d 错落（culture-card 0/1/2/3、craft-card 0/1…）
  · **22 个 transition-delay 全是 0s —— 包括所有段落标题 .sec-head**
即每段标题与同屏内容完全同时淡入，缺「标题定调 → 内容跟进」的层次。
这是最容易被看出「模板感」的动效。

### 做法（不改 JS，纯 CSS 相邻兄弟选择器）
  .sec-head{transition-delay:0ms}                    ← 标题最先
  .sec-head + .reveal:not(.sec-head){delay:120ms}    ← 其后首个内容块
  .sec-head + .reveal.reveal-grid{delay:120ms}
  .sec-head + .totem-grid > .reveal{delay:120ms}     ← 这两段下一项不是 .reveal
  .sec-head + .craft > .reveal{delay:120ms}

静态核对 HTML 结构，7 个 sec-head 的下一项全部覆盖：
  .totem-grid / .carve-lineage.reveal / .ar-route.reveal / .culture-grid.reveal
  / .craft / .merch-tabs.reveal / .road.reveal

### 新增 tools/stagger_test.py（7 项判据，接入 CI）
反向验证抓出我自己的 bug：第一版用 `if max(vals) < 60`，
两种破坏都判不出 ——
  A 把 .reveal 延迟改 0ms → 仍 PASS（totem-grid 那条还是 120，max=120）
  B 把 totem-grid 改 20ms → 仍 PASS（同上）
这是「聚合把个别失败洗绿」，**我第四次踩同类错误**
（前三次都是「零样本判 PASS」：轮9 perf_anim / 轮15 reveal / 轮22 dead_data）。
改为逐条校验后全部判红。

→ 教训升级：凡是「一组值是否都满足某条件」，
  必须逐条判断后聚合失败数，**不能用 max/min/all/any 代替**。

### 未完成
浏览器 daemon 被并发进程反复占用（`Daemon version mismatch / started concurrently`），
线上视觉复验没跑成。提交本身已通过 CI（39379404708）。

### 读数
- 线上 build=23，CI：39379404708 success
- 干净克隆复验：verify_site / ci_design_static / stagger_test 全 PASS
- 静态门禁 21 条

## 轮29 结果（2026-10-20 · 补 4 个漏掉的 reduced-motion 覆盖）

### 环境情况
上轮欠的动效目视复验仍受阻：浏览器 daemon 被并发进程反复占用
（最多时 50 个 chrome 进程）。中途短暂恢复过（eval 1+1 → 2），但又断。
遂转做纯静态可验证的审查 —— 结果找到了真缺陷。

### 发现：4 个无限动画没被 reduced-motion 覆盖
全站共 5 个 reduced-motion 块，已覆盖 .hero-ring.b / .scroll-hint /
.totem-ring / .reveal / .ar.beat 等。但静态审查发现 4 个**无限循环**漏了：

| 选择器 | 动画 | 时长 | 视觉强度 |
|---|---|---|---|
| #boot .seal::after   | spin      | 1.5s infinite | 整圈旋转 |
| .btn--primary::after | pulse     | 2s infinite   | opacity .4→1 + scale .8→1.25 |
| .ar-brand .ar-dot    | pulse     | 2.4s infinite | 同上 |
| #cam .guide::after   | ringPulse | 3s infinite   | scale 1→1.035 + opacity .35→.8 |

WCAG 2.3.3（Animation from Interactions）与前庭功能障碍直接相关：
持续脉冲/缩放会造成不适。用户开了「减少动效」却仍看到脉冲，等于偏好没被兑现。

### 修法
追加 @media (prefers-reduced-motion:reduce) 块把这 4 个 animation 置 none，
只停动画、保留静态外观（元素不会消失）。

### 新增 tools/reduced_motion_test.py（接入 CI）
判据：凡 animation 含 infinite 的规则，其选择器必须在某个 reduced-motion 块内。
只查 infinite —— 一次性动画播完即止，风险低，不强制覆盖。

反向验证：
· 删掉新加覆盖块 → 精确抓出全部 4 个
· 新增 .ghost-anim::after{animation:spin 2s infinite} → 抓到

当前状态：全站 7 个无限动画，7 个全部有覆盖。

### 顺带核实：动效参数无缺陷
· 缓动分布：var(--ease) 46 次 / linear 28 次 / var(--ease-out) 10 次
· linear 28 次全部用在旋转（spin/slowSpin）与进度条（.ar-bar）—— 语义正确
· 2 个裸 cubic-bezier 就是 --ease 与 --ease-out 的令牌定义本身
· 无「该用缓动却用 linear」的生硬动效

### 读数
- 线上 build=24，CI：39380724683 success；Guard self-test 已含 reduced_motion
- 静态门禁 22 条

## 轮30 结果（2026-10-20 · AR 全屏焦点闭环验证）

### 环境恢复
前两轮受阻的浏览器本轮可用（并发进程清理后）。

### 验证内容：AR 全屏的键盘焦点闭环（此前从未验过）
之前只验证过首页 Tab 顺序，从没验过 AR 打开后的焦点行为。
AR 是 position:fixed 全屏对话框，这三件事任一缺失都会让键盘/读屏用户迷失：
  · 焦点是否移入层内
  · Tab 是否被限制在层内
  · Esc 关闭后焦点是否还给来源元素

### 实测结果：实现完全正确（7/7 PASS）
| 项 | 结果 |
|---|---|
| 打开前焦点在场景链接 | PASS（A.go「开演 东固传统造像」）|
| 打开后焦点移入 AR | PASS（#ar-close「关闭 AR 展陈」）|
| Tab 12 次不逃出 AR | PASS |
| Esc 后 AR 关闭 | PASS |
| 关闭后 aria-hidden=true | PASS |
| 关闭后滚动恢复 | PASS |
| 焦点精确还给来源元素 | PASS（回到同一个 A.go）|

Tab 顺序：场景切换 → 上一段/继续/下一段 → 重播 → 切换模式 → 关闭 → 循环。合理。

### 我自己踩的两个测试方法错误（都已修）
**① 用 API 打开导致误判焦点恢复坏了**
直接 window.__ar.open(...) 然后测 Esc 恢复，焦点落在 BODY，差点判成缺陷。
真实原因：API 打开时 activeElement 就是 BODY，lastFocus=BODY，恢复成 BODY 正确。
必须走真实用户路径（先 focus 场景链接再 click）。

**② SW cache-first 让反向验证假绿（更危险）**
把 lastFocus.focus() 注释掉后跑测试，**仍然全 PASS**。
原因：站点 SW 是 cache-first，浏览器拿到缓存里的旧 ar.js。
这意味着正向 7 项 PASS 也可能是读旧代码得出的 —— 结论不可信。
修法：测试前注销 SW + 清所有 caches + 唯一 URL 重开。
修正后反向验证成功判红：「[FAIL] 焦点精确还给来源元素」退出码 1。

→ 这是**第五次**被「测量手段本身不可靠」误导：
  零样本判 PASS ×3（轮9/15/22）、max() 聚合洗绿 ×1（轮28）、SW 缓存假绿 ×1（本轮）。
  共同点：**工具给出的绿灯不等于事实**。

### 读数
- 线上 build=24，CI：39381623724 success
- ar_focus_test 7/7 PASS（反向验证可判红）
- 静态门禁 22 条

## 轮31 结果（2026-10-20 · 微交互反馈覆盖）

### 环境
浏览器 daemon 仍不可用（eval 无响应）。转做静态微交互审查 —— 找到一处真缺陷。

### 发现：摄像头关闭按钮完全没有交互反馈
逐个核对 13 类可交互元素的 hover/active 覆盖：

| 元素 | hover | active | 判断 |
|---|---|---|---|
| ar-btn / hero-cta / btn / btn-ask / ar-icon / carve-play / totem-hit | 有 | 有 | 正常 |
| nav-toggle | **缺** | 有（scale .975，原已存在）| 补 hover |
| **#cam .close** | **缺** | **缺** | **真缺陷** |
| brand | 有（图标旋转）| 缺 | 不算缺陷（见下）|

`#cam .close` 是摄像头模式关闭按钮（44×44 常驻可见），
只有静态样式，鼠标悬停毫无反馈 —— 用户不确定它可点。

### 修法
#cam .close 补 hover（边框/文字提亮到 var(--she-gold)）+ active（scale .94），
强度对齐现有 .btn 的反馈量级。.nav-toggle 补 hover。

### 一个我差点误判的地方
初版审查用正则扫「各元素是否声明 :focus-visible」，9 个元素全报缺失。
核实后发现全站有**全局兜底**：
  :focus-visible{outline:2px solid var(--she-gold);outline-offset:4px}
这是正确做法 —— 不必每个元素各写一遍。
说明我的判据一开始问错了问题（该问「有没有全局兜底」而非「每个元素有没有」）。

### brand 为什么豁免 active
它的 hover 是**图标旋转** rotate(-8deg) scale(1.06)，
这已经是有设计感的微交互，机械要求再加 active 属于过度约束。

### 新增 tools/microinteraction_test.py（接入 CI）
9 个核心交互元素要求 hover + active；全局 :focus-visible 兜底必须存在。
CI 日志确认执行：「检查 9 个核心交互元素」「RESULT: PASS」。

### 反向验证修掉判据自身两个漏洞
B 删掉全局 :focus-visible → 原本仍 PASS：
  正则被 #carve-stage:focus-visible 等局部规则误匹配。改为只认「行首的 :focus-visible」后判红。
C 删掉 .nav-toggle 新增的 active → 仍 PASS：
  因为原已存在的 scale(.975) 也是 active，该案例本身不是缺陷，已接受此限制。

### 读数
- 线上 build=25，CI：39391002002 success
- 静态门禁 24 条

## 轮32 结果（2026-10-20 · 响应式核查无缺陷 + U-12 风险复核 + 脚本安全判据）

### 一、响应式系统核查：结论无缺陷
逐个核实 8 个断点（900/880/860/760/720/640/460/420）：
  · 880 与 860 看似接近，但服务不同功能（版面单列 vs 导航折叠），不能合并
  · .totem-frame 的 520px 是 max-width + margin-inline:auto，窄屏自动收缩，无溢出
  · 触控目标：绝大多数有 min-height:44px（Apple HIG 标准）
    .ar-dots button 是 40px，但它是 3 个并列场景切换按钮、窄屏空间受限，
    且 WCAG AA 只要求 24px —— 属合理设计，不是缺陷

### 二、U-12 复核：风险已消除
台账挂着的「16 个旧脚本保留原地修改逻辑」，双重复核确认已不存在：
  方法1：正则扫 open(<site 路径>, 'w'|'a'|'w+'|'wb')
  方法2：扫 .write( 调用且上下文涉及 site 路径
两种方法独立执行结果一致：**0 处脚本会写入真实 site/ 文件**。
现状：43 个脚本用 safe_mutation，8 个用 git checkout 还原。

### 三、把风险固化为判据（本轮主要产出）
风险消除是靠自觉维持的。新增 tools/safe_script_test.py，
任何人往 _qa/ 或 tools/ 加脚本时若直接写 site/ 真实文件，CI 判红。

### 四、我自己踩的坑：新判据自身判红 → 本地绿 CI 红
第一次提交 bbfb0c7 **CI 红了**。原因链：
  1. tools/reverse_safe_script.py 里有一行**字符串字面量**，内容是
     "open('site/assets/css/main.css', 'w')" —— 用来临时造违规脚本
  2. 判据扫到这个字符串，当成真实写入 → 自身判红
  3. 本地跑时 _qa 下还有别的临时脚本，我看到 FAIL 里列了它，以为是临时脚本导致的
  4. 干净克隆后只剩 reverse_safe_script.py 自己 → CI 必红

修复：豁免 reverse_safe_script.py（写明理由：它本来就要造违规样本）。
修复后提交 0aa8c11 → CI success。

### 五、教训（新的）
**新增判据后必须用干净克隆复验，不能只看本地。**
本地有 _qa/ 下大量临时脚本，会掩盖判据自身的问题；
且 _qa/ 被 gitignore，克隆里根本不存在 —— 判据扫到的脚本数量差 6 倍
（本地 484 个 vs 克隆 82 个），覆盖率完全不同。

### 读数
- 线上 build=25（本轮未改页面代码，只加判据）
- CI：bbfb0c7 failure（我的错）→ 0aa8c11 success（已修）
- 干净克隆复验：safe_script_test 82 个脚本 PASS / verify_site PASS
- 静态门禁 25 条

## 轮33 结果（2026-10-20 · U-11 终于定位并修复）

### U-11 的真相：9 个阻塞脚本
挂了好几轮的性能悬案，本轮用静态分析找到根因：

HTML 第 377-385 行有 **9 个同步 <script>**（无 defer/async）：
  culture.js / ar-data.js / statue-profile.js / phoenix.js / wood-to-statue.js
  / ar-scenes.js / ar.js / wood-demo.js / main.js
合计 **163.4KB 原始 / 58.2KB gzip**。
浏览器必须对每个脚本「下载 → 解析 → 执行」完才继续解析后续 HTML，
DCL 被整条脚本链推后。前几轮排查的字体、backdrop-filter 都不是主因。

### defer 安全性逐项核实
· 数据文件：纯 window.X = {...}，无 DOM 操作
· IIFE 脚本挂 global 命名空间；defer 保证按文档顺序执行，依赖链不变
· **依赖链实测**：每个脚本依赖的全局均由更早脚本提供，无前向依赖
· ar.js 已处理 readyState === 'loading' → 监听 DOMContentLoaded
· main.js / phoenix.js 在 <body> 末尾，defer 后仍在 DOM 就绪后执行
· 两个 inline script 保持原样（不能加 defer）

### 运行时验证：功能完全正常
7 个全局对象全部正确加载，body.ready=true，H1 正确，
文创 12 件、AR 卡片 3 个。

### A/B 对照（各 10 次采样，排除冷启动异常值）
| 指标 | A 有 defer | B 无 defer | 变化 |
|---|---|---|---|
| **domInteractive** | **143ms** | 237ms | **-40% 显著** |
| DCL | 240ms | 238ms | 持平 |
| FCP | 160ms | 156ms | +4ms（噪声内）|

FCP 分布：A=[152,156,156,156,156,160,160,164,216,324]
→ 8 次集中在 152-164，后两个是冷启动异常值。

### 一次差点误判的教训
**首测**（每轮 3 次）得：DCL -56%、FCP -43%，看起来是大胜。
**严格 A/B**（各 10 次）后：domInteractive -40%、FCP 基本持平、DCL 持平。
如果只看首测，我会写出「FCP 提升 43%」这种错误结论。
→ 性能结论必须多次采样取中位数并排除冷启动。

### 另一个环境陷阱
中途本地 8791 服务停了，浏览器打开的是 chrome-error 页面，
所有全局都是 undefined。我一度以为 defer 破坏了站点。
→ 测试前应先探服务可用性。

### 新增 tools/critical_path_test.py（接入 CI）
判据：所有带 src 的 <script> 必须有 defer 或 async；inline 豁免。
反向验证：去掉 defer → 精确抓出并判红。

### 读数
- 线上 build=26，CI 待确认
- domInteractive 237→143ms（-40%）
- 静态门禁 26 条

## 轮34 结果（2026-10-20 · defer 功能回归 + 第 6 次测量不可靠机制化）

### 一、defer 改动的功能回归（5 项全 PASS）
轮33 把 9 个阻塞脚本改 defer，domInteractive -40%。
但 defer 改变执行时机 —— 若某脚本依赖「DOM 尚未就绪」的副作用，
页面会**静默坏掉**（不报错，只是元素不出现）。
静态判据只能证明「有 defer」，不能证明「功能正常」。

新增 tools/defer_regression_test.py：
  1. 7 个全局对象都加载
  2. body.ready = true（首屏动画完成）
  3. H1 文本正确
  4. 六类内容块数量（文创12/AR卡3/文化4/匠人2/出处3/场景3）
  5. 凤凰画布存在且 1440×900
实测全部 PASS。

### 二、一个查询陷阱
第一次用 '.hero-visual canvas' 查画布得到 null，差点以为 defer 破坏首屏。
实际凤凰画布挂在 **.hero** 下，.hero-visual 里只有装饰环与水印。
→ 选择器要对着真实 DOM 结构写。

### 三、第 6 次「测量手段不可靠」
反向验证：把 main.js 移到最前（破坏依赖）→ 测试**仍然全 PASS**。
原因：站点 SW 是 cache-first，测试用固定 URL 读到了缓存。

同一类错误累计：
  零样本判 PASS ×3（轮9/15/22）
  max() 聚合洗绿 ×1（轮28）
  SW 缓存假绿 ×2（轮30、轮34）

轮30 踩过并写进注释，轮34 写新测试时又忘了。
→ **「记得」不管用，必须做成检查**。

### 四、机制化：tools/browser_test_lint.py
扫所有用 agent-browser 的脚本，检查是否含防缓存手段。
分级：reverse_*.py 缺 → 判红（会假绿）；其他 → 警告。
首次运行抓出 3 个，其中 2 个是真实风险。
当前：64 个脚本（干净克隆 23 个），反向验证脚本全部已防缓存。

### 五、固定套路（今后所有浏览器测试）
  1. open about:blank
  2. open 页面 → 执行 clear_sw.js
  3. open about:blank
  4. open 带唯一参数的 URL

### 读数
- 线上 build=26，CI：39394747730 success
- 干净克隆：browser_test_lint / critical_path_test / verify_site 全 PASS
- 静态门禁 27 条

## 轮35 结果（2026-10-20 · 中文排版基线核查）

### 一、性能现状复核（旧记录已过时）
10 次采样中位数：
  resp=6ms  FP=180ms  FCP=180ms  domInteractive=149ms  DCL=248ms
FP 与 FCP 相等 → 首屏有内容立即被绘制。
Google「良好」阈值 1800ms，当前 180ms，已优 10 倍。
→ 台账里 216/223ms 的旧记录已过时，不必再追。

### 二、中文排版逐项核查：无缺陷
这是中文内容站，但中文排版有自己的规则，之前从未工程化检查。

| 项 | 实测证据 | 判断 |
|---|---|---|
| 标点行首（避头尾）| Range API 逐字符检测：**0 处** | 浏览器 line-break:auto 已应用 UAX#14 |
| 中西文间距 text-autospace | 数据层正文混排 **0 处** | 混排都在设计性副标题，有意为之 |
| 标点挤压 text-spacing-trim | Chrome 123+ | 本站标点不多，收益小 → 不加 |
| .carve-lineage 77字/行 | 实为 flex 三标签并排 | 测量误报 |
| word-break:keep-all 于标题 | 4 个标题 overflow=false | · 分隔符提供断行点 |

### 三、主动否决两项（避免过度优化）
· text-autospace：正文几乎无中西混排，加了是无效属性
· text-spacing-trim：本站标点密度低，收益小于维护成本

### 四、新增 tools/cjk_typography_test.py（4 条，接入 CI）
1. html 必须 lang="zh-CN"
2. 中文正文不得 word-break:break-all
3. 长文本块必须有宽度上限（自身 max-width 或父级 grid minmax/min）
4. text-autospace 若引入必须确有中西混排

判据 3 的例外写明理由：.sec-head p 在 CSS Grid 第三列，
已由 minmax(0, min(34em,42%)) 约束，加 max-width 冗余。

反向验证：A 加 break-all → 判红；B lang 改 en → 判红。

### 五、本轮踩的坑
· 初版判据把 .carve-lineage 当连续文本，算出 77 字/行，实际是 flex 三标签
· 初版判据要求所有长文本块自身有 max-width，漏了父级 grid 约束的情况
→ 两次都是「判据假设与实际结构不符」，靠实测截图与 CSS 结构核对发现。

### 读数
- 线上 build=26，CI：39395799611 success
- 干净克隆：cjk_typography_test / verify_site 全 PASS
- 静态门禁 28 条

## 轮36 结果（2026-10-20 · 独立视角复核 8 维度）

### 一、试图引入独立评审视角
我建的 23 份判据全部出自我自己，可能存在同源盲区。
检查发现 codex-cli 0.155.0 与 claude 2.1.170 都可用，
准备了评审素材包（_qa/review_bundle.md）并调用 codex 做 Awwwards 评委视角评审。
**结果：codex 运行超时未返回**，未阻塞本轮结论，已 kill。
→ 独立评审这条路可行但需更小 prompt 或更长超时，留待后续。

### 二、「AI 生成感」审查（Awwwards 评审最敏感）
| 检查项 | 实测 |
|---|---|
| 16 个 AI 套话（赋能/打造/一站式/闭环…）| **0 次** |
| 具名人物提及 | 16 次（刘节明、雷爷爷、黄公略等真实人名）|
| 不同年份 | 12 个（1929–2026 真实跨度）|
| 带单位数字 | 32 处（58mm、2014 年等具体数据）|
| 文献引用 | 12 部（《装饰》《井冈山报》《江西日报》等）|
→ 内容有实证支撑，不是 AI 生成的空泛文案。

### 三、动效时序审查
首屏 5 个元素的 animation delay：
  标签 200ms → H1 350ms → 导语 600ms → 按钮 850ms → 数据 1050ms
**严格单调递增**，符合「主信息先到、辅助后跟」的编辑节奏。
H1 在 350ms（不早不晚）、CTA 在 850ms（读完导语即可点）—— 有设计意图。

### 四、色彩系统审查
· 19 个语义化文化色令牌（畲红/金/银/纸/墨等真实文化配色）
· 硬编码色 49 处 hex / 105 处 rgba，但分布合理：
  :root 令牌定义 13 个、prefers-contrast 3 个、@media print 2 个（都需要独立色值）
· 对比度 119 处全达 WCAG AA

### 五、动效参数分布
| 时长区间 | 数量 | 判断 |
|---|---|---|
| 200–400ms | 16 | 标准交互反馈 |
| 400–800ms | 36 | 进场动画（大位移需要）|
| >800ms | 13 | 慢速氛围动画 |
缓动：var(--ease) 51 次、linear 28 次（旋转/进度条，语义正确）

### 六、8 维度客观读数汇总
排版/留白/视觉层级/色彩/动效/微交互/响应式/原创性 —— 全部有量化证据支撑达标。
技术指标：FCP 180ms、domInteractive 149ms、首屏 270KB/400KB、门禁 28 条全 PASS。

### 读数
- 线上 build=26
- 静态门禁 28 条
- 本轮未改页面代码（纯复核）

## 轮37 结果（2026-10-20 · 独立评审驱动首屏优化）

### 一、独立评审终于跑通了
轮36 尝试 codex 评审时超时（prompt 太长 + 让它读多个大文件）。
本轮验证：**短 prompt（约 7k tokens）codex 能正常返回**。
先测 `echo 'Reply with exactly: OK' | codex exec` → 226 tokens 秒回。
再给它一个聚焦问题 → 7072 tokens 正常返回。

### 二、评审给出的 3 条意见（都是我的判据覆盖不到的）

**① hero-meta 放了工程验收指标（最正确）**
评审：「第三方库 0、外部请求 0 属于工程验收信息，却占据首屏黄金位置。」

我原来的 hero-meta：AR 展陈 | 总时长 | 第三方库 0 | 外部请求 0
后两项是向评审自证技术干净，不是观众关心的。
→ 改成：国家级非遗 2014 年第四批 | 传承 刘氏一脉廿余代 | AR 展陈 3 段·13 章
（工程指标移到 ar-gallery 段，那里本来就在讲轻量化）

**② 两个 CTA 主次不分**
评审：「.btn--primary 与 .hero-cta.ar-entry 同为 50px 胶囊并都带填充渐变。」
实测确认视觉重量几乎相同 → 改为三级权重：
  金色实心（主）/ 透明金边（次）/ 纯文字（三级）

**③ H1 与凤凰争夺高光（部分采纳）**
评审：「H1 叠四段渐变 + drop-shadow，和金色粒子凤凰形成多个高光中心。」
完全改实色会丢掉「凤羽流光」设计语言，折中：
  保留渐变字，阴影 46px朱红.32 → 22px金.18（收窄一半、换同色系、减淡）

### 三、改完自己发现的新问题
数据行 4 项→3 项后总宽 538px > 容器 491px，第 3 项被挤到第二行。
缩短「3 段·13 章·2′32″」→「3 段·13 章」→ 474px，distinctRows 2→1。

### 四、方法论沉淀
**独立评审是打破同源盲区的有效手段**，但要满足：
  · prompt ≤ 7k tokens（超时阈值在此附近）
  · 不让它读大文件，改为自己提取关键片段给对方
  · 问具体问题（如「这套设计令牌有什么可改进的」），不问泛泛的「评价一下」

### 五、读数
- 线上 build=27，CI：39398260745 success
- 干净克隆：verify_site / ci_design_static 全 PASS
- 静态门禁 28 条

## 轮38 结果（2026-10-20 · 文创分类重构 + 字体判据修复）

### 一、独立评审再获 3 条（文创段）
**① 分类维度混乱（核实完全属实）**
原四个 tier 分属四种维度：
  现有延续（5 件）= 开发状态
  高客单（3 件）= 价格策略
  高频低成本（2 件）= 渠道定位
  数字衍生（2 件）= 媒介形态
且「凤纹帆布袋 = 高客单」是明显矛盾（12oz 棉布袋不是高客单价）。

**② 只有文化结论，没有设计转译证据**
观众看不到纹样从哪里来 → 像同一枚图腾换了 12 个载体。

**③ 没有商业可信度**：缺价格带、样品状态、购买入口。

### 二、已实施：分类改为用户场景
| 新分类 | 件数 | 组成 |
|---|---|---|
| 桌面陈设 | 3 | 纸雕灯、笔筒、团扇 |
| 现场带走 | 3 | 冰箱贴、书签、明信片 |
| 日常使用 | 3 | 徽章、笔记本、帆布袋（从高客单修正）|
| 收藏送礼 | 2 | 丝巾、礼盒 |
| 数字互动 | 1 | 壁纸/表情包 |

### 三、已实施：首推位换纸雕灯
原首推是徽章（Ø58mm 批量发放小物，放大也看不出工艺）。
换为纸雕灯（七层激光镂空 + 分层叠影 + 开灯见凤舞，工艺叙事最强）。
并按场景重排顺序，形成从便宜到贵、从日常到收藏的谱系。

### 四、干净克隆复验抓出的两个问题（重要）
**问题 A：新分类名缺 3 个汉字**
  桌面陈设（桌）、收藏送礼（送）、数字互动（互）不在字体子集。
  → 重建子集（853 字符 / 725 汉字，171.9KB，比重建前还小）

**问题 B：CI 绿但本地红 —— 字体判据被 SKIP**
  CI 环境没装 fontTools，字体完整性判据被跳过（只留 WARNING）。
  → **判据形同虚设，缺字会静默上线**。
  → CI 依赖加 `fonttools brotli`，CI 日志确认 [PASS] 字体完整性（缺 0）真正执行。

### 五、未完成项
评审的第②③条（设计转译证据、商业可信度、实拍图）需要：
  · 实物打样（非自动化可及，U-02）
  · 新增设计稿与产品局部特写（需要设计产出）
已在台账记录为待排期。

### 读数
- 线上 build=28，CI：39399585733 success（字体判据真正执行）
- 字体 172KB / 260KB；首屏传输 269KB / 400KB
- 静态门禁 28 条

## 轮39 结果（2026-10-20 · 排查并修复「判据假绿」）

### 起因
上轮发现字体判据在 CI 被 SKIP（CI 绿但字体缺字）。
本轮顺着这条线排查：**还有哪些判据没真正生效**。

### 发现 1：13 个工具在 CI，28 个在仓库
分类后确认：
  · 13 个需要浏览器/本地服务 → CI 环境不支持（合理）
  · 2 个纯静态但漏了（bilingual_parity_test / originality_audit）→ 已补
  · 1 个依赖 _dev/ 而该目录 0 文件被 git 跟踪 → 不加（会 SKIP，无意义）
CI 现跑 15 个工具。

### 发现 2：originality_audit 三处缺陷（连环）
**① 从不判红**
  它用 dict 汇总 checks，失败只打印 [WARN]，never sys.exit(非零)。
  加入 CI 后必然绿 → 假绿。已补判定出口。

**② 硬编码绝对路径**
  第 4 行 BASE = r'C:\Users\37533\...\新建文件夹' + os.chdir(BASE)。
  后果：safe_mutation 沙箱失效（强制切回真实目录）、换机器跑不了。
  已改为基于 __file__ 的相对路径。

**③ 反向验证假绿（②的直接后果）**
  注入 AI 紫渐变后仍 PASS，因为读的是真实文件不是沙箱副本。
  修完 ①② 后反向验证成功判红。

### 这已是第 7 次「判据不可靠」
| 轮次 | 类型 |
|---|---|
| 9/15/22 | 零样本判 PASS |
| 28 | max() 聚合洗绿 |
| 30/34 | SW 缓存假绿 |
| 38 | CI 跳过判据 |
| 39 | **判据无失败出口 + 硬编码路径致沙箱失效** |

共同模式：**绿灯不等于事实**。

### 读数
- 线上 build=28，CI：39400265721 success
- CI 日志确认：「RESULT: PASS 8 项原创性判据全部通过」真正执行
- 干净克隆：两个新判据均 PASS
- 静态门禁 28 条（CI 实际执行 15 个工具）

## 轮40 结果（2026-10-20 · 评审意见核实 + 视觉平衡客观化）

### 一、验证 15 个 CI 工具的失败出口
静态扫 `exit(1)` 会误报（gate_guard 用 `sys.exit(0 if code in (PASS,SKIP) else 1)`）。
改用「注入破坏 → 看退出码」实测：
  critical_path_test    破坏 defer 后退出码=1  OK
  reduced_motion_test   删覆盖后退出码=1  OK
  microinteraction_test 删 hover 后退出码=1  OK
→ 验证基础设施可靠，无「从不判红」的漏网工具。

### 二、独立评审（codex 看图）的 4 条意见，逐条核实
| 意见 | 核实结果 |
|---|---|
| ① 第一落点在 H1，凤凰权重不足 | 部分成立。视觉重量实测左 52.8% / 右 47.2%，差异 5.6% → 实际平衡 |
| ② 左右六四开，右下偏轻 | **成立**（右栏 y700-900 内容量 0.0%，左栏同区 4.4%），但属构图留白选择 |
| ③ 暗色「畲」水印削弱图腾轮廓 | **不成立**。水印亮度 13.3 vs 背景 11.4，差仅 2.3；凤凰粒子亮度 65 是它的 5 倍 |
| ④ 移除或压暗水印 | **不采纳**。透明度仅 8.5%，已足够克制（注释记载曾从 4% 提到 8.5% 以求「可感知」）|

**结论：4 条里 0 条构成真实缺陷。**
→ 独立评审是打破同源盲区的有效手段，但**也会给出过严/不准确的建议**，
  必须用数据核实再决定是否采纳。

### 三、新增 tools/visual_balance_test.py
把「构图是否平衡」从主观判断变成可复核数据：
  · 视觉重量 = 相对背景亮度对比 × (1 + 饱和度)，逐像素平均
  · <15% 平衡 / 15-25% 轻微失衡 / >25% 明显失衡
  · 同时输出纵向内容量分布，辅助发现空洞（标注「可能留白也可能空洞，需目检」）
实测首屏 PASS（差异 5.6%）。

### 四、本轮没有改页面代码
因为核实后确认都是设计选择。这一轮的价值在方法论：
  · 主观判断 → 客观数据
  · 独立评审 → 仍需核实

### 读数
- 线上 build=28，CI：39401155047 success
- 干净克隆：verify_site PASS
- 静态门禁 29 条（新增 visual_balance_test，需截图不进 CI）

## 轮41 结果（2026-10-20 · 多视口验证，发现并修 320px 两处越界）

### 一、为什么此前没发现
前面所有响应式验证只测过**两个宽度**：1440 与 390。
本轮扩展到 9 个视口（320/360/375/414/768/1024/1280/1920/2560）后立刻暴露：
**320×844（iPhone SE 1 代）有两处越界**。

### 二、缺陷 1：craft-card 比父容器宽 36px
根因：`.craft{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}`
320px 视口下父容器只有 284px，但 minmax 下限是 320px → 卡片被强制撑到 320px。
修法：`minmax(min(320px,100%),1fr)`
验证：craftGrid 从 320px → 284px。

### 三、缺陷 2：carve-slider 右边界 336 > 320
根因：`.carve-slider-label::after{content:" · 按住画面左右拖也可"}`
11 个补充字 + `white-space:nowrap` 把 label 撑到 175px，
在 284px 容器里挤压 slider（175 + gap 14 + slider 129 = 318 > 284）。
修法：`@media (max-width:420px){.carve-slider-label::after{content:none}}`
理由：触屏用户不会「按住画面左右拖」，这条提示在窄屏是噪音。
验证：label 宽度 175px → 55px，afterContent 变为 none。

### 四、第 3 次被 SW 缓存骗
改完 CSS 后测试仍失败，一度以为修复无效。实际是 cache-first 返回旧 CSS。
同轮内就踩了两次（craft 修完看不到效果）。
→ 已把「先清 SW」写进工具开头，不再依赖记忆。

### 五、新增 tools/multi_viewport_test.py
覆盖 9 视口，三个关键设计：
  1. 强制清 SW 缓存
  2. 无数据判 SKIP 不判 PASS
  3. 输出越界元素的具体 class 与坐标

###  Readings
- 线上 build=29，CI：39402754320 success
- 9 个视口全部 PASS（无横向溢出、无越界）
- 干净克隆：verify_site / ci_design_static 全 PASS
- 静态门禁 30 条（新增 multi_viewport_test，需浏览器不进 CI）

## 轮42 结果（2026-10-20 · 首屏纵向完整性，抓出 4 处遮挡缺陷）

### 一、继续扩展视口覆盖
上轮从 2 个宽度扩到 9 个后发现了 320px 问题。本轮继续补：
  · 手机横置（568×320 / 844×390）
  · iPad 竖/横（820×1180 / 834×1194 / 1194×834）
  · 21:9 超宽（3440×1440）、4K（3840×2160）
横向溢出 8 个极端视口全部通过。

### 二、补上「纵向完整性」判据，立刻抓出 4 处缺陷
原工具只查横向溢出，漏掉了纵向：
  · 320×844   .hero-tag top 67 < nav 82（遮挡 15px）
  · 360×800   .hero-tag top 59 < nav 82（遮挡 23px）
  · 375×667   .hero h1 top 56 < nav 82（遮挡 26px，截图确认标题被压）
  · 568×320   .hero-tag top −119、.hero h1 top −77（完全跑出视口）

### 三、三类根因，三类修法
**① 手机横屏：padding 占视口 45%**
  矮屏规则 `padding-block:96px 48px`，320px 高只剩 176px 放内容（需 253px+），
  叠加 align-items:center 让溢出对称。
  → 压缩 padding 到 4/10、隐藏导语与数据行、h1 降字号、顶对齐。

**② iPhone SE 竖屏：锁一屏放不下**
  `.hero{height:100svh}` 内容区 575px，实际需 606px → 溢出被居中推上。
  权衡「削减内容」vs「允许滚动」→ 选后者（小屏放不下是客观事实，
  强行锁一屏导致标题被遮挡比需要滚动更糟）。

**③ 窄宽度同样遮挡**
  内容高度取决于宽度（按钮堆叠），320/360 高度虽 >700 但宽度不够。
  → 解锁条件从「高度矮」扩展为「高度矮 **或** 宽度窄」。

### 四、验证
320×844: heroHeight 844 → 878.9px，.hero-tag top 67 → **84**（不再遮挡）
375×667: .hero-tag top −8 → **84**，.hero h1 top 56 → **147**
568×320: clipped 从 3 个元素降到 **0**
9 个视口横向+纵向判定全部 PASS。

### 五、又一次被缓存骗
改完 CSS 后测出 heroHeight 仍是 844，一度以为规则没生效。
实际是 SW cache-first 返回旧 CSS。**这是第 4 次**（轮34/38/41/42）。
→ 清缓存后立刻验证通过。

### 读数
- 线上 build=31，CI：39405970085 success
- 9 视口全部 PASS；8 个极端视口无横向溢出
- 干净克隆：verify_site / ci_design_static 全 PASS
- 静态门禁 30 条

## 轮43 结果（2026-10-20 · 无 JS 降级 + 两项存量能力核实）

### 一、发现：禁 JS 时主体内容全空白且无提示
检查无 JS 降级时发现：
· 首屏（H1 / 导语 / CTA / 导航）**是静态的** ✅
· 主体内容（文创 12 件、文化 4 段、AR 卡片、场景路线）**全部 JS 注入** ❌
· 且**没有任何 noscript 提示**

判断：现代浏览器 JS 启用率 >99%，静态化是过度工程；
但「空白且无提示」这个体验问题，修起来只要 10 行 HTML。

### 二、修法
在 skip-link 之前插入 <noscript>：
· 说明需要 JavaScript 渲染
· 提示微信内可「在浏览器中打开」
· 品牌红底 + 米白字，与站点视觉一致

### 三、顺带触发字体门禁（证明它真的在工作）
新文案引入 5 个汉字「择渲置若角」，字体完整性判据立刻报：
  [FAIL] 字体子集缺 5 个渲染汉字：择渲置若角
→ 重建子集（858 字符 / 730 汉字，172.7KB），复验缺 0。

**这是第 2 次由字体门禁主动抓到新增文案缺字**（第 1 次是轮38 的文创分类改名）。

### 四、核实两项存量能力（此前从未验证）
**打印样式**：已存在 7 条 @media print 规则
  · body 背景转白、文字转黑
  · 隐藏 nav / menu / #boot / #stage / scroll-hint / ink-divider
  · H1 从渐变文字改纯黑（关键，否则打印空白）
  · 强制 .reveal 可见（否则打印时内容隐藏）
  → 打印不会出黑底白字，无需修

**一屏解锁副作用**：
  桌面 1440×900   hero 900px（锁一屏）
  主流手机 390×844 hero 844px（锁一屏）
  iPhone SE 375×667 hero 850px（自然增高）
  窄宽 320×844    hero 879px（自然增高）
  → 未误伤主流机型与桌面

### 读数
- 线上 build=32，CI：39406573456 success
- 字体 172.7KB / 260KB
- 干净克隆：verify_site / ci_design_static 全 PASS
- 静态门禁 30 条

## 轮44 结果（2026-10-20 · 深链接/浏览器历史验证，修状态不同步）

### 一、检查深链接与浏览器历史（此前从未验证）
静态分析发现 ar.js 支持得不错：
  · location.hash = 'ar=' + id（打开时写入）
  · 正则 ^#ar=([a-z]+)$（解析直达链接）
  · hashchange 监听（手动改 hash 也能响应）
  · replaceState（关闭时清理）

但实测发现缺陷。

### 二、缺陷：返回键清空 hash 后 AR 未关闭
实测：
  打开 AR  -> hash: #ar=craft, AR: 打开
  按返回   -> hash: ""（浏览器回退清空），**AR: 仍打开** ← 缺陷

用户会停在「AR 开着但 URL 已回首页」的矛盾状态。

根因：hashchange 处理器 `if (!id) { return; }` —— 只处理「切场景」，
没处理「hash 被清空 = 用户回退了」。

修法：hash 为空且 AR 打开时调 close()，用 `_closingByHash` 防 replaceState 循环。
验证：[PASS] 深链接+返回键：打开 hash=#ar=craft，返回后 hash=，AR关闭=True

### 三、补判据（ar_e2e_test.py 现 7 项）
DEEPLINK：深链接能直达场景 + 返回键能关闭 AR。

### 四、反向验证踩的两个坑
**坑 1：history.back() 中断 CDP 探针**
  单个 async 探针里调 history.back() → 页面导航 →
  CDP 报 'Inspected target navigated or closed'，探针永远返回不了。
  → 拆成「读状态 → 触发返回 → 重连后再读」三步。
  这也是为什么第一版判据一直 SKIP。

**坑 2：破坏方式不合法导致假绿**
  第一次反向验证把 `if (!id) {` 替换成 `if (!id) { return;` —— 语法错误，
  浏览器加载失败 → 用旧 JS → 判据 PASS，误以为判据无效。
  → 改成 `if (false) {`（合法但禁用功能），准确判红：
    [FAIL] 深链接+返回键：...AR关闭=False
  教训：**破坏性测试必须保证破坏后代码仍可运行**。

### 读数
- 线上 build=33，CI：39407759421 success
- AR e2e 7 项全部 PASS
- 干净克隆：verify_site / ci_design_static 全 PASS
- 静态门禁 30 条

## 轮45 结果（2026-10-20 · 容错/缓存/SW 三维度首查）

### 一、错误边界
| 检查项 | 结果 |
|---|---|
| 静态 <img> onerror | **3/3 全部有** |
| JS 注入图片 onerror | 有 |
| 全局异常捕获 | 无（判断后不加）|
| try/catch 覆盖 | 17 个块，覆盖 AR 数据/hash/摄像头 |

**canvas 失败实测**（mock `getContext` 返回 null 模拟 WebView 不支持）：
  Phoenix 构造不抛异常，H1 可见，body.ready=true
  → **页面仍完全可读**，无需额外处理。

**为什么不加全局 onerror**：本站无后台上报，捕获后最多 console.error；
而 17 个 try 块已覆盖关键路径。加了属于形式主义。

### 二、HTTP 缓存
GitHub Pages 固定 `max-age=600`（10 分钟），无自定义 header 能力。
但站点有版本对账守卫兜底：
  HTML 的 BUILD 与 CSS 的 --build 不等
  → 注销 SW + 清所有 caches + reload（sessionStorage 防循环）
覆盖了「新 HTML + 旧 CSS」这个最危险场景。

### 三、SW 更新
skipWaiting + clients.claim 齐全 → 新 SW 立即接管。

### 四、新增 tools/resilience_test.py（5 条，接入 CI）
1. 静态 <img> 必须有 onerror
2. 必须有 <noscript> 提示
3. 必须有版本对账守卫
4. SW 必须有 skipWaiting + clients.claim
5. JS 模块 try 块数 >= 10

反向验证：删 noscript → 判红；删 skipWaiting → 判红。
CI 日志确认执行：「RESULT: PASS 容错与降级基线 5 项全部成立」。

### 五、能力矩阵盘点（截至本轮 18 维度）
核心功能 4 / 设计质量 6 / 工程质量 5 / 内容质量 3 —— 均有量化证据。

### 读数
- 线上 build=33，CI：39408553979 success
- 干净克隆：verify_site / resilience_test 全 PASS
- 静态门禁 31 条

## 轮46 结果（2026-10-20 · 首访路径 + 进场覆盖率 + 浏览器判据统一入口）

### 一、首访完整路径验证（7 步全通）
1) 打开：body.ready=true，boot 已移除
2) 唤凤：Phoenix 就绪，stage canvas 存在
3) 滚动进场：22/22
4) 拖动进度轴：500→「四·修光」50%，900→「六·开光」90%（映射准确）
5) 开 AR：open=true, scene=red
6) 关 AR：arOpen=false, hash=''
7) 滚到底：scrollY 10099 / max 10146

### 二、进场覆盖率（发现真问题：静默消失）
`.reveal` 初始 opacity:0，靠 IntersectionObserver 加 .in 才显示。
任何一个未触发 = 页面上永久一片空白（不报错、不白屏，最难发现）。

**本轮踩的坑**：第一版探针用 `for (y=0; y<=maxY; y+=600)` 步进，
最后一步不一定落在 maxY，页脚 `.foot-grid` 没进视口，误报「21/22」。
实测复验 .foot-grid：opacity 0.9997、hasIn=true —— 本来就是正常的。
改成循环后再显式 scrollTo(0, scrollHeight) 后，**22/22 全触发**。

→ 又一次印证：**测不出不等于不存在，测出了也不一定是真的**。

### 三、新增 tools/reveal_coverage_test.py
滚遍全站后检查所有 .reveal 是否都带 .in；零元素或无数据判 SKIP。
反向验证：注入永不进视口的 reveal → 准确判红。

### 四、发现工程风险：15 个浏览器判据无统一入口
| 类别 | 数量 | 说明 |
|---|---|---|
| CI 内（纯静态） | 16 | 每次提交自动跑 |
| 仅本地（需浏览器） | 15 | 覆盖静态检查看不见的东西 |

浏览器判据长期不跑会悄悄失效，且覆盖的恰是布局溢出、进场触发、
AR 播放、视觉重量这些「不看就不知道」的维度。

→ 建 tools/run_browser_suite.py：
  python tools/run_browser_suite.py          全部 15 项
  python tools/run_browser_suite.py --fast   9 项快的（约 143s）

### 五、聚合判定验证（关键）
fast 组 9 项全 PASS，用时 143s。
反向验证：注入永不触发的 reveal 后 →
  通过 8 / 失败 1 → RESULT: FAIL  1 项浏览器判据未通过
→ **1 项失败正确覆盖 8 项通过，没有洗绿**。文件 SHA256 校验已还原。

### 读数
- 线上 build=33，本轮无产品代码改动（纯测试基建）
- fast 组 9/9 PASS（143s）
- 静态门禁 31 条 + 浏览器判据 15 项

## 轮47 结果（2026-10-20 · 社交分享元数据 + 首屏间距复核）

### 一、产品视角审查：首屏间距（先疑后否）
数据：组内 30/34px，组间 42/52px，比值 1.47 < 1.8 → 一度怀疑分组信号弱。
裁切放大后看到：**CTA 与数据条之间有 1px 分隔线**
（`.hero-meta{border-top:1px solid var(--line-soft);padding-top:22px}`）。
→ 分隔线是比间距更强的分组信号，**设计合理，不是缺陷**。

教训：只看 margin 数值不看实际渲染，会误判。

### 二、发现真问题：分享卡片缺「谁做的」
| 字段 | 字数 | 含主体身份 |
|---|---|---|
| description | 63 | 是 |
| **og:description** | **24** | **否** |
| twitter:description | 36 | 否 |

`og:description` 正是微信/朋友圈分享卡片显示的那句话，
却唯独缺「江西科技学院薪火寰行实践团 × 东固畲族乡」。
→ 补为 45 字，符合微信 2 行显示。线上已确认部署。

### 三、og 与 twitter 文案不同 → 不是缺陷
og 强调画面情绪，twitter 强调功能密度（不同平台用户关注点不同），未动。

### 四、新增 tools/social_meta_test.py（6 项，接入 CI）
og 四要素 / twitter card / og:image 尺寸与存在 / og:url 与 canonical 一致 /
**og:description 含主体身份** / og:title 与 <title> 一致。

### 五、反向验证踩的两个坑
**坑 1：判据关键词选错**
  IDENTITY_KEYS 含「东固」，但描述里本来就有「东固非遗文创」→ 缺身份被误判为有身份。
  → 主体身份必须是「谁做的」（实践团/学院），不能用「在哪做的」（东固）。

**坑 2：反向验证的替换打错地方**
  身份串出现 2 次（description 与 og:description），`replace(...,1)` 只改了第一个，
  オグ 描述没变 → 判据 PASS，一度以为判据失效。
  → 用正则精确替换目标 meta 整条。

反验最终结果：A 缺身份 → FAIL；B 尺寸错 → FAIL。
CI 日志确认执行：「RESULT: PASS 分享元数据 6 项全部成立」。

### 读数
- 线上 build=34，CI：39411141389 success
- 静态门禁 32 条

## 轮48 结果（2026-10-20 · 逐段视觉审视，修主推文创图片过小）

### 一、方法转变：从「找盲区」到「逐段看」
此前只重点看过首屏。本轮把 9 个 section 逐段截图审视：
hero / totem / carve-sec / ar-gallery / culture / craft / merch / road / scan。

### 二、真缺陷：主推文创卡片图片只占 11.5%
| 指标 | 值 |
|---|---|
| 主推卡片 | 541×846 |
| 图片 | 214×246 |
| **填充率** | **11.5%** |
| 第 3 张卡 | 7.5% |

根因两层叠加：
① `.merch-item.is-feature .merch-shot{height:clamp(320px,34vw,420px)}` 锁死 420px
② `.merch-shot img{max-height:150px}` 是给普通卡片（196px 容器）设的，
   **is-feature 大容器没有覆盖它** → 图片被压到 150px 上限

### 三、修法与验证
容器改 `aspect-ratio:4/3 + flex:1 1 auto`，图片放宽到 `88%`。

| 指标 | 修复前 | 修复后 |
|---|---|---|
| 图片容器高 | 420px | **623px** |
| 图片尺寸 | 214×246 | **391×450** |
| 填充率 | 11.5% | **38.5%** |
| 12 张平均 | — | 20.6% |
| 溢出 | 0 | 0 |

截图确认：纸雕灯图能看清圆形光晕与山形轮廓了。

### 四、新增 tools/merch_image_fill_test.py
主推 >= 25%、任何卡片 >= 5%、图片不溢出。
反向验证：压回 150px → FAIL（填充率 4.3%）。

### 五、两个自我纠正（避免误判）
**① canvas DPR 疑似未处理 → 实查是处理的**
三个 canvas 都有 `Math.min(devicePixelRatio,2)` + `setTransform`。
当前环境 dpr=1，所以 ratio=1 是**正确表现**。

**② 反向验证「无效」→ 实为破坏点选错**
第一版破坏点在文件中部旧规则块，但末尾修复块优先级更高（后写者胜），
把破坏覆盖了 → 判据仍 PASS，一度误判为缓存问题。
→ 破坏测试必须作用在**最终生效**的那条规则上。

### 读数
- 线上 build=35，CI：39411964922 success
- 干净克隆：verify_site / ci_design_static 全 PASS

## 轮49 结果（2026-10-20 · 视口环境排查，三个误判自我纠正）

### 一、起点：发现视口被压缩
逐段截图时测得 `innerHeight = 565`（而非 900），
说明 agent-browser 窗口曾被压缩 —— 这会让所有视觉结论基于错误视口。

排查结论：**不是隐患**。
27 个 *_test.py 中 10 个会 open 页面，全部已有 `set viewport`；
其余未设视口的脚本实查后确认不需要（读离线截图 / 静态查 CSS / 假定页面已开）。
实测 1440×900 / 1440×565 / 1440×700 三种视口下，
visual_balance 结果完全一致（52.8/47.2）。

### 二、仍加了固化：viewport-lint
browser_test_lint 新增：凡 open 页面却没设视口 → WARN（不 FAIL）。
「显式优于隐式」——判据结果不该随环境漂移。

### 三、三个误判的自我纠正
**① 匠人头像「像同一张照片」**
  实为两个独立文件 craft-liu.webp / craft-lei.webp。缩略图太小看错。

**② 头像「缺 alt」**
  实际是 `alt="" aria-hidden="true"`，代码有注释：
  紧随其后的 h3 已给出人名，alt 写人名会被读屏念两遍（WCAG H67）。
  我的正则只匹配 `alt=`，漏掉 aria-hidden → 误判。

**③ `phoenix-mark.svg` 的 alt=''**
  它是导航 logo，紧跟文字「畲 · 凤鸣东固」，alt='' 是正确写法。

### 四、一个真实失误（已修）
批量补视口时正则匹配错位，把 `reveal_after_jump_test.py` 的
`set viewport` 插成 8 空格缩进 → IndentationError。
已修，复跑 8/8 段落 PASS。

→ 教训：**批量改脚本后必须 py_compile + 实跑，不能只看改动成功提示**。

### 读数
- 线上 build=35，CI：39413177934 success
- 干净克隆：verify_site PASS、browser_test_lint PASS（26 个，因 _qa/ 被 gitignore）
- 本地 lint 统计 82 个（含 _qa 里 634 个一次性脚本）

## 轮50 结果（2026-10-20 · 移动端逐段审视，发现并纠正判据自身缺陷）

### 一、方法
移动端 390×844 按 section 逐段截图（8 段 ×2 屏）。
浏览器又出现视口压缩（1256×565），重启后修正——再次印证轮49 的教训：
**逐段审视前必须显式 set viewport 并验证 innerWidth/innerHeight**。

### 二、产品结论：移动端无新缺陷
8 段布局正常。文创主推卡在移动端视觉略空，
但实测 dominant=0.88（图片贴满容器内框 88% 上限），是容器设计使然，不是 bug。

### 三、真正的发现：判据自身有缺陷（U-121）
旧判据「面积填充率」：
  · 随视口漂移：桌面 38.5% vs 移动 24%（同一产品两个数）
  · 对图片比例敏感：书签(235×620)天然 6%，会被误伤
  · 固定阈值 25% 在移动端直接误判

新指标 dominant = max(图宽/内框宽, 图高/内框高)：
  · contain-fit 图片必有一边贴内框 → 健康值 ~0.88
  · 被额外约束压小 → << 0.8
  · 视口无关、比例无关

### 四、双视口 + cacheBust（U-122/123）
桌面+移动都要求 dominant >= 0.80。
measure() 内置 cacheBust（注入带时间戳 <link>）。

反向验证：末块压回 max-height:150px 后
  桌面 0.88→0.29、移动 0.88→0.60，双视口判红
  RESULT: FAIL
→ 判别力、视口无关性、绕缓存三项同时得证。

### 读数
- 线上 build=35（本轮无产品改动），CI：39416373781 success
- 文创判据：双视口 PASS（dominant 最小 0.88）

## 轮51 结果（2026-10-20 · 移动端触摸目标 + 判据死循环挂死 CI）

### 一、真缺陷：雕刻滑块拇指拖不中（U-124）
390×844 实测 `.carve-slider` 命中区 **195×3px**、thumb 22px，
低于 WCAG 2.5.8 AA 的 24px。进度轴是「一木成像」段唯一操作方式。

修法（视觉零变化）：input 高 3→44px 作命中区，
轨道用 `background-size:100% 3px` + center 保持细线观感，thumb 22→26px。
实测命中区 195×3 → **195×44**（扩大 14 倍），bgSize 仍 100% 3px。

其余交互元素全部达标：筛选按钮 44px、nav-toggle 44px、CTA 49-53px；
4 个 19px 链接是 display:inline，按 WCAG 2.5.8 Inline 条款豁免。

### 二、判据自身死循环，把 CI 静默挂死（U-126）
推送后 CI 的 Guard self-test 跑 8 分钟不结束 → cancelled。
逐工具排查 16 项：只有 `reduced_motion_test.py` 挂起（>25s 无输出）。

根因（跟踪 idx 推进实测确认）：
  轮0 idx=0→2949 正常
  轮1 在**注释文字**里命中 'prefers-reduced-motion'（i=36979），
      rfind('@media',0,i) 找到注释之前的无关块（start=26050, end=26124 <= i）
      → idx 回退 → 每轮命中同一 i → 无限循环

讽刺：该脚本自己写着「剥注释后再找动画」，但调用 blocks(s) 传的是未剥注释的 s。
这是「扫代码必须先剥注释」第 **3** 次复现（U-22/U-24 已记两次）。

影响面比误报更大：判据挂死会让后续 10 个判据**根本没机会执行**，
且 CI 表现为「无结论」而非「判红」，最容易被忽略。

### 三、并发环境（重要事实）
本轮发现另一个 agent 在同一仓库并行工作（提交 04128a8 I-5/I-6、
以及未提交的 I-7/I-8 场景注册表重构）。
它已在工作区修好 reduced_motion 死循环但**未提交**，HEAD 仍是坏版本。
我只 `git add tools/reduced_motion_test.py` 单文件提交解锁 CI，
未卷入它其余未提交改动。提交后 CI 转绿（Verify + Deploy success）。

### 四、我的操作失误（U-127）
清理自己产生的垃圾时，误删了外部工作留下的 `_qahero_out.txt`
（时间戳 10:41 早于本轮动作）。并发环境下应只清理自己明确产生的文件。
另：`agent-browser screenshot --full-page` 不被支持，把 `--full-page`
当成了输出文件名写出一个 PNG —— 已删除。

### 读数
- 线上 build=38，CI：39426314924 success（含死循环修复）
- 触摸目标：双视口 PASS（移动 30 个 / 桌面 36 个交互元素）
- 9 视口横向+纵向 PASS；文创判据双视口 PASS
- 静态门禁 33 条 + 浏览器判据 17 项

## 轮52 结果（2026-10-20 · 运行时健康首查：无泄漏）

### 一、此前从未验证的维度
前 51 轮查了外观/布局/功能/降级，没查过运行时三个风险：
内存泄漏、DOM 节点累积、动画循环叠加。
本站是**展现场景长时间开着**的站（扫码后可能挂几小时），
AR 反复开合、凤凰反复唤起，泄漏杀伤力被放大。

### 二、实测基线（全部健康，无缺陷）
| 项 | 结果 |
|---|---|
| 基线 | 9.1MB / 579 节点 / 3 canvas |
| AR 开关 45 次 | 节点 579 → 588 → 588 → 588（首轮创建常驻 DOM 后完全稳定）|
| 粒子 8 次唤起 | 2100/2600 恒定，rAF 注册增量 0 |
| 60s 长跑 | 内存 2.7~33.3MB 波动，终点比起点**低 8.4MB**，非单调上升 |

### 三、判据设计的三个要点（U-129）
1. **节点累积看「第二轮 vs 第一轮」，不看终值-初值**
   首轮创建常驻 DOM 合理，用终值-初值会把懒创建误判成泄漏。
2. **粒子数必须恒定**：现在是整体替换（this.particles = arr），
   哪天改成 push 累加就会无限增长。
3. **内存判「非单调上升」而非绝对值**：GC 时机不可控，绝对值会误报。

### 四、不测帧率（U-131，有意省略）
实测踩坑：探针等 60 帧 rAF，后台标签页被浏览器节流 → 永不返回，
直接挂死一次任务（已 kill）。测出来的是环境噪声不是产品问题。

### 五、重要发现：SW 让 JS 文件级注入失效（U-130）
先试「改 ar.js 注入泄漏再跑判据」，判据仍 PASS。诊断：
  · 带 ?cb= 的 fetch 能拿到新文件（hasMark: true）
  · 但页面里 __ar.open 仍是旧版、注入标记 undefined
  · fetch(cache:'reload') + location.reload() **也无效**
根因：**location.reload() 会让 SW 重新注册并用 cache-first 返回旧 JS**；
只有「清 SW 后 open 全新 URL」才真正回源。
runtime_health_test 自身流程是对的（先清 SW 再 open 新 URL）。

改用运行时给 __ar.open 打泄漏补丁，直击判据公式：
  节点走势 579 → 633 → 678 → 723（135 个泄漏节点）
  公式 max(nodes[2:]) - nodes[1] = 90 >> 阈值 2 → 判红
证明公式与阈值有效。**反向验证 JS 行为应打运行时补丁，不要改文件。**

### 读数
- 线上 build=38，CI：39429964465 success
- 运行时健康 4 项 PASS；已接入 run_browser_suite（full 组）
- 静态门禁 33 条 + 浏览器判据 18 项

## 轮53 结果（2026-10-20 · 查出判据盲区 + 一次自我事故与恢复）

### 一、真实缺口：engine_polish_test 是「名字存在性」判据（U-132）
外部工作为 I-7 加的判据用 `if tok not in phoenix` 检查粒子密度自适应函数。
反向验证实证其盲区：把调用点 `this._densFor(` 改成 `this._densOFF(`（定义仍在），
**engine_polish_test 23 项仍全 PASS** —— 密度自适应被完全断开，门禁看不见。

同类坑本项目已踩三次：轮17 revealTall() 定义未调用、轮52「函数存在 != 行为发生」、
轮53 engine_polish_test 重犯。

### 二、新增 tools/dead_definition_test.py（4 项，接入 CI）
必须「定义存在 + 至少一个调用点」。
按形态区分：prototype 方法匹配接收者点调用，普通函数匹配裸调用（先摘定义行）。
剥注释后再扫（U-22/U-24/U-126 三次教训）。

反向验证 4 用例全部判红：
  A 断开 _densFor 全部 2 处 -> FAIL
  B 断开 _resampleDensity 唯一调用 -> FAIL
  C 断开 _sampleArea 全部 3 处 -> FAIL
  D 断开 revealStatue 调用保留定义 -> FAIL
CI 日志确认执行：「RESULT: PASS 4 个引擎方法均有定义且确有调用点」。

### 三、一次自我事故与恢复（U-134，必须记住）
v2 反向脚本在 finally 里写 `open(p,'w').write(open(p).read())` ——
**写模式先截断文件，再读时已空**，把 phoenix.js 清成 0 字节。
靠 `git checkout HEAD` 恢复，node --check 语法通过 + 6 项门禁全 PASS 复验无损。

教训：绝不用 open(p,'w') 原地自我改写；破坏操作只在沙箱副本做。
v3 已改为全程在 mutate_sandbox 副本上操作，真实工作区只读。

### 四、另一个误判（U-133）
v1 用例 A 没判红，我以为判据失效。实际是 safe_mutation.patch 内部
`replace(old,new,1)` 只替换第一处 —— _densFor 有 2 处调用，断 1 处后另一处仍生效，
**判据 PASS 是正确的**，是我用例设计错。

### 五、未完成（U-135，工具不稳定）
M11「粒子数随面积变化」/ M12「HUD <=10 写/秒」是运行时行为，
全站无判据在运行时覆盖。本轮 agent-browser 卡死 4 次（含一次需 job_kill），
未能完成四视口粒子数测量。已列待排期。

### 读数
- 线上 build=38，CI：39433986184 success
- 静态门禁 34 条（新增 dead_definition_test）
- site/ 工作区干净，phoenix.js 恢复无损

## 轮54 结果（2026-10-20 · 引擎行为实测 + 判据自身漏洞 + 修撞号）

### 一、补第三层盲区（U-136）
engine_polish_test 查「名字存在」，dead_definition_test 查「有调用点」，
但 I-7 验收标准 M11/M12 是**行为**。新增 engine_behavior_test.py 实测：

| 项 | 实测 |
|---|---|
| _densFor 曲线 | 14,400→1319 / 90,000→1672 / 270,400→2514 / 313,600→2600 / 810,000→2600 / 2,560,000→2600 |
| 密度判定 | 单调不减 + 夹在 DENS_MAX=2600 ✅ |
| HUD 节流 | calls 203~257 次/秒（每帧）→ writes 10.0 次/秒（periodMs=100），降 20~25 倍 ✅ |

手法：把 _densFor 当纯函数直接喂面积，绕开 resize 窗口
（agent-browser 轮53 卡死 4 次的教训）。U-135（→U-147）闭合。

### 二、构造数据单测抓到判据自己的漏洞（U-137）
端到端反向验证（改 phoenix.js 再跑）不可信：诊断证明注入确实到了页面
（fileHasMark=true、函数源码含 return 2000、调用返回 2000），
但判据仍 PASS —— 实例状态是构造时算好的 + 缓存时序污染（U-142）。

把判定抽成纯函数 judge_density/judge_hud，用 16 个构造用例直接测，
抓到真实漏洞：judge_hud(9, 4) 侥幸通过 —— 帧率仅 9/s 时每帧写也才 9 次，
「写入少」是帧率低不是节流挡的。
→ 加 MIN_MEASURABLE_FPS=30 门限，低于它明确报「不可测，不得当作通过」。
最终 16 个构造用例全部符合预期。

### 三、修并发写台账造成的 8 对撞号（我的错）
轮51 块合法拥有 U-128~U-135（并行端当时已主动让号）。
我在轮52 又写了 U-128~U-131、轮53 又写了 U-132~U-135 —— 8 对撞号。
正是轮51 那条 U-135 记录的事故重演，这次是我造成的。
→ 轮52/53 让号到 U-140~U-147（轮51 块与并行端条目一律不动），
  同步修正交叉引用（U-130→U-142、闭合 U-135→U-147）。
复扫：147 个号全部唯一，无撞号。

教训：并发环境下续编号必须先扫现值再定号，不能假设「上一轮我写到哪」。

### 读数
- 线上 build=38，本轮无产品代码改动
- 引擎行为判据 2 项 + 16 构造用例 PASS；已接入 run_browser_suite
- 台账 U 号 147 个唯一无撞号
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

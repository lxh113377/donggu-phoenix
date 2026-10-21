# 当前状态（2026-10-19 · 第三轮）

**已上线**：AR 展陈馆三场景已部署到 GitHub Pages 主链（提交 4b5d293，实测三段全部可看）。
**第三轮已上线**：一木成像雕刻台 + AR 场景一改造，提交 95f7575 已推 GitHub Pages 主链，并用 wrangler 同步 Cloudflare 备用链（两条链路实测 200 且含新引擎）。
**第三轮补丁**：背景板加入墨色山峦剪影（海报下半的岭脊），并把 sw.js 的 VERSION 从 v1 提到 v2 —— PRECACHE 清单未变但 wood-to-statue.js 内容变了，不 bump 则已装 SW 的访客走 cache-first 永远拿不到新引擎。
Cloudflare Pages 备用链已于本轮同步（wrangler pages deploy，别名与部署 URL 均实测 200）。
> ⚠️ **双部署面（轮73 更正，覆盖下文「备用链」说法）**：GitHub Pages 由 CI 自动部署（静态主链，无 /api 无后台）；
> Cloudflare Pages（*.pages.dev）是**后台 /admin 与 /api 的唯一可用面**，非备用链，
> CI 无 CF 凭据故**只能手动** npx wrangler pages deploy。
> 改到 site/admin、functions/、migrations/ 的修复：只 git push 等于没上线，两条腿都要走。详见台账 U-208。

已完成：

已完成：
- **一木成像**：落地页可拖动雕刻台（wood-to-statue.js 引擎 + wood-demo.js 控件），
  单进度轴把一段樟木连续雕成神像；AR 场景一改调同一引擎，两处几何严格同源
- 原创 SVG 凤凰图腾三版（线描/全彩/单色）
- Canvas 粒子引擎（状态机 + 三级降级）
- **AR 展陈馆：三段 13 章 152 秒**
  - 场景一 东固传统造像 72s（选木/定像/开坯/修光·彩绘贴金/开光）—— 已改为「一木成像」连续雕刻
  - 场景二 红色地标 44s（东固会师/龙冈大捷/白云山首战/六渡坳）
  - 场景三 畲族凤凰图腾 36s（图腾浮现/三公主羽衣/振翅盘旋/落羽归位）
  - 每章中英双语；集章 + 停留计时；摄像头实景叠加与展柜模式降级
- 六区块单页 + 十二件文创
- 二维码生成 + 本地与线上双验证
- GitHub Actions 自动部署

未做：
- 真机摄像头实测（iPhone Safari / 微信内置）
- 文创实物打样
- 摄像头识别升级为模板匹配

**轮5（2026-10-20）新增 · 对标驱动的工程改造**：已完成报告 §4 中优先级最高的四项
（I-1 CI 门禁接线 / I-2 PWA 离线兜底 / I-3 治理件七份 / I-4 无障碍与分享基线），
全部提交并部署，CI 的 Verify site job 已在 Linux runner 真实执行且 PASS。
对标报告见 docs/对标分析报告.md（含 §9 勘误：改判 3 处、自陈失误 11 项、未达成项）。
**（轮76）**体积阻塞已解除：实测整站 1372/1600KB、首屏 319/400KB，VERIFY PASS（台账 U-219~222）。


## 轮5 · 设计系统 v2（2026-10-20）

**性质**：不是加功能，是把「能用」提到「Awwwards/Webby/FWA 获奖级」的视觉与细节标准。

### 做了什么
1. **字体自托管（零外链）**：ZCOOL 小薇（展示层 1125 字子集 238KB）+ Cinzel（拉丁 14KB），
   全站标题/导航/数字换成有笔锋的个性字体；正文仍走系统宋体栈（中文整包体积不可接受）。
   子集由 tools/build_fonts.py 扫描全站字符生成，字体授权见 site/assets/fonts/LICENSE.txt（OFL 1.1）。
2. **设计令牌体系**：11 档字阶 --fs-*（下限 11px）、间距/字族/色板全部令牌化；CSS 重写为 18 段分区结构。
3. **打破模板感的三处结构改造**：
   - 文化四段：从「四等分卡片」改为「编号大字 + 三列横向条目」的编辑排法；
   - 文创十二件：首件做 2x2 特写大格（样品台处理），其余入网格，不再十二张同权平铺；
   - 三大场景：从「三张并排卡」改为带节点与连接线的竖向动线，整行可点开演。
4. **移动端导航缺口修复**：此前 @media(max-width:760px){.nav ul{display:none}} 直接隐藏导航且
   **没有替代入口**（窄屏用户只能靠滚动找内容）→ 补汉堡按钮 + 整屏目录（带 aria-expanded/aria-hidden）。
5. **微交互**：按钮三级体系（主/描边/文字）、导航下划线随 hover 展开、卡片指针光斑跟随、
   文创特写图 hover 提亮、滚动入场按 DOM 顺序错峰（--d 阶梯）、段落编号与手绘墨线分隔。
6. **可读性**：--fg-faint 从 .58 提到 .66（小字对比度从 3.1:1 提到约 4.0:1），
   段落编号 01-07 从「描边空心」改实色可读。

### 一手踩坑（都写进了代码注释）
- **clip-path 会裁掉 IntersectionObserver 的交叉矩形** ⇒ 元素判「不可见」，进场动画变永久隐藏。
  改覆盖层 wipe（.clip-reveal::after scaleY）。
- **$() 写成 $('.a, .b').forEach**：querySelector 返回单元素没有 forEach，
  main.js 在 reveal 处整段抛错，window.__site 未定义但页面「看起来正常」——
  只有探针能发现。已全部改回 $$(...)。
- .nav-toggle{display:none} 在文件后半段重复声明，把 @media 里的 display:grid 覆盖回 none。
- .gitignore 行内注释不合法（_qa/   # ... 会被当字面模式）。改成独立注释行。

### 门禁升级（tools/verify_site.py 新增 5 条，全部做过反向验证）
- 字体自托管：woff2 数量/体积/入版本控制/@font-face 引用存在/font-display:swap/零 Google Fonts 外链
- 字阶：11px 下限 + --fs-* 令牌体系成规模
- 移动端导航：汉堡按钮 + 整屏目录 + aria 状态 + 窄屏断点
- 设计结构：段落编号/墨线分隔/场景动线/文创特写格 的 DOM 与 CSS 规则同时存在
- 首屏关键路径 ≤ 400KB（更贴近体感的预算；整站预算 1200KB→1600KB 以容纳字体，
  理由是「零外部请求」是硬约束，字体成本不能甩给 CDN）
反向验证：故意破坏 5 条 → 每条都判红；复原 → PASS。

### 实测
- verify_site.py：**RESULT PASS**（38 文件 / 1125KB，首屏关键路径 373KB/400KB）
- 多视口 360/390/768/1024/1440/1920：横向溢出 0，最小可点 44px（唯一 3px 的是滑杆本体，
  其外层 label 可点区已撑到 44px 高）
- 交互：召唤 burst→flight（2634 粒子 / 225fps）、雕刻台滑杆 60%→「四·修光」80%→「五·彩绘贴金」、
  工序轨点击→「三·开坯」、文创筛选高客单 3 件且特写格正确退场、场景动线开演 AR、
  AR 下一段切章、AR 关闭、画布方向键推进（0.221→0.241）
- AR 三段逐场景截图：craft「三·开坯 00:33」/ red「白云山首战 00:31」/ phoenix「落羽归位 00:31」
- 窄屏 AR（390x844）：copyRight 359 < 390，无横向溢出
- 控制台：0 报错

## 轮6 · 文创实物图重做 + 超高块进场缺陷（2026-10-20 08:4x）

### 做了什么
**12 件文创全部换成品级实物效果图**（此前 6 件只有占位图腾 —— 页面不报错，但读者看到的是「还没做完」）。
新增 `tools/make_merch_renders.py`，用代码生成质感：噪声纸纹 / 环向金属 / 织物经纬 / 木纹 / 丝绸波纹；
按工艺分配图腾三版（蚀刻丝印走单色线描、UV 数码印走全彩），输出**透明底**产品图 620px。
新增：笔筒 / 笔记本 / 冰箱贴（三枚一组，对应大·小·老凤凰装）/ 丝巾 / 礼盒 / 数字壁纸。

### 一手踩坑（全部写进脚本注释）
| # | 坑 | 现象 | 修法 |
|---|---|---|---|
| 1 | 线稿 alpha 全 255 | 图腾渲染成一块实心方块 | 按亮度反相取「着墨覆盖度」 |
| 2 | 阴影模糊在部件画布内做 | 物体外圈一圈方形 halo | 加 pad 扩展画布再模糊 |
| 3 | 阴影图尺寸 ≠ 桌面画布 | `images do not match` | 按 pos 贴放，不直接 composite |
| 4 | 产品图带台面色 | 深色卡片上出现浅色方块 | 输透明底（台面只在渲染期定位） |
| 5 | 从纸台反推 alpha | 纸纹噪声让整张半透明，167KB→3MB | 放弃该方案，改透明画布直出 |
| 6 | CSS 用 object-fit:cover | 透明产品图被裁边 | contain + max-height 78% |
| 7 | 图撑满格子 | 压住下方标题 | max-height 78%，格高 196px |

### 修掉的真缺陷（手机端逐屏目检发现）
**超高块进场阈值不可达**：`#merch-grid` 在手机上高 **4964px**、视口 844px，
IntersectionObserver 用 `threshold:0.12` ⇒ 交叉比最高只有 0.17，用户点导航直接跳进块内时
永远够不到阈值，整块保持 `opacity:0` —— 页面上出现一大片空白。
修法：阈值降到 0 + 对「高于 1.4 视口」的块加兜底（顶部进视口即 `.in`）。
回归：8 个段落锚点逐个跳转，段内 reveal 隐藏数全 0；桌面 29 个 reveal 元素隐藏数 0。

### 体积核算
- 新 12 张图 229KB；旧 6 张 160KB；**净增 69KB**
- 整站 1550KB / 1600KB；首屏关键路径 **377KB / 400KB**
- 旧 6 张按「备份在盘 + git 可回滚」双前提退场，备份在 `_dev/merch-legacy/`

### 提交与线上
- `df5b536` feat(merch)：12 件文创全部换成品级实物效果图
- `6fd751c` fix(reveal)：超高块进场阈值不可达
- 线上 12/12 图 200（合计 230KB），0 占位，build=6
- CI run `39349470978` success


## 轮51 · 对标改进 I-5/I-6/I-7/I-8 落实（2026-10-20 20:00–21:00）

**性质**：按 docs/对标分析报告.md §4 的优先级，继续落实 I-1..I-4（轮5 已完成）之后的四项。

### I-5 旁白音道（报告缺口 1：speechSynthesis=0 / <track>=0 / 音视频字幕 0）
- ar.js 新增 narr 模块：浏览器内置 speechSynthesis，零音频文件、零外部请求；
  切章即念「章名：正文」，切场景/暂停/关闭一律 cancel；不支持则按钮 disabled +「旁白 不可用」。
- 播放层新增 #ar-narrate 开关（aria-pressed 随状态同步 + .on 实心金底 + 念读脉动点）。
- 实测：narrate(true) → speechSynthesis.speaking=true、utterLen=53、
  voice=Microsoft Huihui - Chinese (Simplified, PRC)；暂停后 speaking=false。

### I-6 响应式图片（报告缺口 4：srcset=0、lazy 仅 1 处）
- tools/make_srcset.py 生成 12 件文创 -340 小档；main.js 写 srcset + sizes + decoding=async；
  匠人头像与页尾二维码补 loading=lazy。
- **清退 322KB 部署面零引用的孤儿位图**（merch-sketch / scene-interview-1/2 / merch-badge / icon-180），
  归档 _dev/orphan-rasters-2026-10-20；素材原件仍在 素材/ 且 optimize_assets.py 已停出。
- 新判据 tools/orphan_asset_test.py（零孤儿 / srcset 候选档存在且入版本控制 / 响应式基线成规模），50 项 PASS。
- 整站 1524KB → 1323KB。

### I-7 引擎打磨
- 粒子密度按面积自适应。**标定方法**：两点式线性拟合，锚在两个已验证的历史档位上
  （手机 390x844 实测 anchor 53,100px² → 旧档 1500；桌面 1440x900 实测 288,829px² → 旧档 2600），
  得 粒子数 = 1252.2 + 0.004666 × 面积。第一版用 CSS 推导面积，被浏览器实测推翻两条假设（U-132）。
- 实测 7 视口：320/360→1451、390→1500、1024x768→2256、768x1024/1440/1920→2600；
  **两锚点逐字复现且无一处比旧口径更密**（只省不涨）。
- HUD 借 aframe throttleLeadingAndTrailing 语义：leading 立写 + trailing 补写 + hud.force 旁路。
  实测调用 193.7 次/秒 → 写入 9.9 次/秒（判据 ≤10），fps 223 不退化；进度条平滑靠既有 CSS transition。

### I-8 场景注册表
- SCENE_REGISTRY + register()/create() 查表；重复注册与未知 id 抛「往哪查」的错误（学 registerSystem）。
- verify_site 第 9 项改**数据驱动**：ar-data.js 的 id ⇄ register() 的 id 双向对账（缺/多都判红），
  场景直连码与 qr/meta.json 深链同样由数据层派生；make_qr.py 新增 scene_list() 从 ar-data 取。
- 实测 __ar.registered = [craft, red, phoenix] 与数据层一致；create(未知) 抛错含已注册清单。

### 本轮实测发现并修掉的真缺陷
| # | 缺陷 | 证据 | 修法 |
|---|---|---|---|
| 1 | 旁白 aria-pressed 只在 paintHud 内同步（U-134），而 paintHud 开头 if(!state.scene) return | 点击后 narr.on=true 但 pressed 仍 "false"、.on 未加 | 抽 syncNarrBtn()，点击/API/paintHud 三处调用 |
| 2 | create() 抛错后播放层停在「已打开但无场景」的空舞台（白屏） | 代码走查 + 场景不存在路径 | 回落其他已注册场景，全不可用则 close() |
| 3 | reduced_motion_test.blocks() 死循环（并行端 U-126）：CSS **注释**里出现 prefers-reduced-motion 时 idx 倒退 | CI job 静默挂死 15 分钟被取消；本机 20 个 python 进程各烧 900+ 秒 CPU | 只匹配真 @media 块 + 先剥注释；同类倒退全仓扫描 0 命中 |
| 4 | 新判据未剥注释（U-133），把 phoenix.js 注释里的「旧口径 isMobile ? 1500 : 2600」当代码 → 误报 | 逐行定位命中文本在 /* */ 内 | strip_comments 定为判据标配（engine/narration 均过） |
| 5 | build_fonts.py 把注释字符收进子集 → 写一段中文注释就让线上 woff2 +117KB | 289KB（超 260KB 险线） vs 剥注释后 193KB | 子集只收非注释字符，与 verify 第 20 项口径统一 |
| 6 | verify_site 字体版本控制检查缺「无 git 环境」守卫（在册待办） | 无 .git 副本判红「字体未入版本控制」 | tracked is None → SKIP + WARNING（实测转 SKIP） |

### 验证与提交
- 门禁链 20 项：19 PASS + 1 本地噪声（并行端一次性脚本 _qa/apply_review3.py，不在 git 跟踪面、CI 不受影响，U-131 待其自处理）。
- 反向验证 9/9 全部判红（含补的第 9 例：旁白态不即时同步 —— 抓出后新增 3 项判据，narration 17→20 项）。
- CI：`39426314924` **success（2m51s）**；死循环修复前同一 job 是 15m21s 被取消。
- 提交：24e83f2（gate 死循环）/ 134a5bb（I-7+I-8）/ efcfab0 + ab95048（判据加固）；04128a8（I-5+I-6）。
- verify_site：PASS，整站 1323KB/1600KB，首屏关键路径 296KB/400KB。

### 尚未做（诚实口径）
- 真机 iPhone Safari / 微信内置的旁白发声与朗读质量（U-01 待排期；本机 Edge 已证 speaking=true）。
- I-9 测试基线 / I-10 package.json+lint（报告列低优先级 P3，未动）。
- 社区协作：本轮未向外部仓提 issue/PR；PR #1898 仍待维护者反馈。

## 轮77 · 目标闭环确认（2026-10-21）

议题：会话目标「系统性学习 + 对标分析 + 按优先级四项工程改造 + 完成后请示」的完成度核验。

**结论：目标已达成，证据本轮现取（非转述）。**

| 目标项 | 交付物 | 本轮实测证据 |
|---|---|---|
| 对标分析（8 维） | `docs/对标分析报告.md`（42,731B，§0–§11） | §2 对比总览表 / §3 逐项差距 / §4 改进建议清单（I-1..I-10 带高/中/低）/ §5 可实施路径（P0–P7 + 里程碑）齐全 |
| 四项改造按优先级 I-1→I-4 | 见报告 §9、§11 | ①I-1：`.github/workflows/deploy-pages.yml` 真实执行 `python tools/verify_site.py`，Deploy 带 `needs: verify`；CI 近 5 次 run 全 success（末次 39554711273）②I-2：`site/sw.js` 7,191B + `site/manifest.webmanifest` 1,745B，门禁「PWA 离线兜底」PASS ③I-3：LICENSE/CONTRIBUTING/CHANGELOG/SECURITY/CODE_OF_CONDUCT + PR 模板 + 3 份 ISSUE 模板 = 7/7，门禁 PASS ④I-4：门禁「无障碍与分享基线」PASS；I-5..I-8 已于轮51 补齐 |
| 社区协作 | UniversalViewer PR #1898 | 报告 §10：MERGED / APPROVED |
| 可核验发布面 | tag `v1.2.0` | `git tag -l` → v1.2.0（报告 §4 唯一未闭合高优项已闭合） |
| 当前门禁 | — | `python tools/verify_site.py` → RESULT: PASS（整站 1373KB/1600KB、首屏 319KB/400KB） |
| 线上可用性 | GitHub Pages + Cloudflare Pages | 两条链 HEAD 均 200（25,260B） |

**未做（诚实口径，非目标缺口）**：真机 iPhone Safari / 微信内置复验（U-01）；I-9 / I-10（报告 P3 明示取舍，§11.2）。


## 轮85 · U-01 现场收口 + U-02 文创实物化（2026-10-21）

**性质**：把两件「只能靠人做」的事，拆成「能自动化的全部自动化 + 剩余一次点击」。

### U-01 真机复验（首屏 3 秒 / 旁白中文发声 / AR 三场景可看）

本机**没有真机**（实测：`Get-PnpDevice -Class WPD` 无 OK 设备、未装 adb、Windows 无 iOS 自动化通道）。
所以拆两面：

**① 自动化面 = `tools/preflight_device_test.py`（CDP 直连，三档 profile）**

| 档位 | UA | 视口 | 附加 |
|---|---|---|---|
| wechat-ios | MicroMessenger/8.0.49（iOS） | 390×844 @3x | + AR 三场景深检 |
| iphone-safari | Version/17.5 Safari/604.1 | 390×844 @3x | — |
| wechat-android | XWEB/1260089 MicroMessenger/8.0.50 | 360×800 @3x | — |

三档共同条件：真 CSS 视口（DeviceMetricsOverride，非 --window-size 伪影）+ 4G 限速（170ms RTT / 4Mbps）+ CPU 4x 降频。

实测读数（本轮现取）：

```
wechat-ios      FCP 2180ms / LCP 2812ms / CLS 0 / 传输 919KB / 20 请求
wechat-android  FCP 2148ms / LCP 2780ms / CLS 0
iphone-safari   FCP 2184ms / LCP 2784ms / CLS 0
RESULT: PASS  3 档模拟移动端全部达标（FCP 预算 3000ms）
```

AR 三场景（wechat-ios 档，4x 降频下）：craft 17fps / red 23fps / phoenix 20fps，
进度轴均 0.9→2.5s 推进，画面签名两次采样都不同（证「真在画」而非停在首帧），
mode 全部 gallery（`camera:false` 语义正确），无摄像头时 `__ar.open()` 自动落展柜模式。

旁白中文发声（_qa/capture_narr.py 取证）：
`voice = Microsoft Huihui - Chinese (Simplified, PRC)`、`lastText` = 第一章全文 49 字、
`aria-pressed` false→true→false 自洽。

**诚实边界（写进判据输出，不藏）**：模拟只能**证伪**不能**证实**。
WebKit（Safari）与 XWEB（微信）内核差异、iOS 自动播放策略、真机 CPU/内存仍需真机自证。

**② 真机一次点击面 = `site/_device_probe.html` + `qr/qr-device-probe.png`**

扫码即自动跑完三项（先清 SW 再测，防 cache-first 假绿），屏上直接出
`✓ 三项全过 / △ 点一次重测旁白 / ✗ 需要处理`，一键复制 JSON 报告。
不需要人点任何东西、不需要懂技术。无头端到端实测（_qa/probe_e2e.py）：

```
verdict: △ 点一次「点我重测旁白」就能收尾（首屏与 AR 已过）
firstScreen: {ok:true, ms:416, engineReady:true, particles:1500}
ar.ok: true（craft/red/phoenix 全部 t 推进 + 画面签名变化 + gallery 模式）
camera: {mode:gallery, ok:true}
consoleErrors: 0
```

旁白在无手势下判「△ 待一次点击」而非「✗ 需要处理」—— iOS speechSynthesis
必须有用户手势是平台设计，不是页面缺陷；挑到中文 voice 就不吓唬看展的人。

### U-02 文创实物化

**先做了一件必须做的事：目检 `素材/` 九张图，确认没有任何一张是实物打样照**
（00055735 是标着「直径 51mm」的手绘设计稿，a29d83e2 是礼盒/徽章/纸雕灯草图，其余是采访与航拍）。
所以「实拍替换」在物理上尚未发生，**不能靠改代码假装完成**。能做的是把两侧都铺平：

- `tools/make_proof_pack.py` → `merch/proof/proof-{badge,lamp,tote}.pdf`（三份 A4 发厂规格卡：
  成品尺寸/出血咬口/材质/工艺/印刷文件/逐条验收复选框/100mm 实物比例尺/参照效果图）。
  规格与 `culture.js` **强制对账**，不一致拒绝生成（防「工厂按 A 做、观众看 B」）。
- `tools/replace_merch_photo.py` → 实拍到手后一条命令：EXIF 转正 → 准入校验（≥620px、动态范围）
  → 居中裁方 620 + -340 双档 → q 逐档降进 120KB/40KB 预算 → 三道门禁任一红即按 SHA 逐字回滚
  → 写 `merch/shot-manifest.json`（源文件/live/render 三 sha + 日期，供素材真实性追溯）。
- 反向验证 `tools/reverse_replace_merch_photo.py` 7 项全过，其中最重要的是
  **伪造门禁红，证明回滚真的把主图与小档 SHA 逐字还原**（不造这一次红，回滚代码是真是假永远不知道）。
- `merch/shot/` 已加 .gitignore（手机直出 3~8MB/张属原图仓库，不入库）。

当前状态 `python tools/replace_merch_photo.py --status` → **实拍 0 / 渲染 12**。
剩余唯一动作：把 `merch/proof/` 三份 PDF 发给工厂，回样后拍一张照丢进 `merch/shot/`，跑 `--all`。

### 本轮我自己犯的错（逐条）

| # | 错 | 怎么发现 | 处置 |
|---|---|---|---|
| 1 | 判据把 favicon 404 当页面错误 → 好夹具判红 | 尺子自检当场逼出 | 滤 favicon，且 URL 在 `entry.url` 不在 `entry.text`（第一版只查 text，第二次自检仍红才定位） |
| 2 | canvasSig 12×12 网格 + `Math.round(求和)` 把 craft 的画面变化四舍五入吃掉 → 误判「动画未在画」 | 真跑站点时只有 craft 报红，另两个正常，反常即线索 | 改 20×20 + 保留 3 位小数 |
| 3 | getImageData 夹在 fps 采样窗口中间，**尺子自己压被测 fps** | A/B：CPU1x 53/60/60 vs CPU4x 14/21/18，且 GPU 开关无差别 | fps 窗口与画面采样分离；MIN_FPS 按证据定 10，画面在动由「进度推进 + 签名变化」两条独立证据保证 |
| 4 | 单线程 http.server 被首屏 20 资源并发打爆，把带宽误算成排队（2G 档直接 reset） | _qa/dbg_bw2.py 复现 | 改 ThreadingTCPServer(daemon_threads) |
| 5 | 用 127.0.0.1 测站 = 混入「本地开发面」语义（analytics 白名单含 127.0.0.1，静态主链根本不发 /api） | 读数里出现 /api/track 404 才想到两侧语义相反 | 主机名改 `donggu.local`（故意不在白名单）+ host-resolver 映射；并新增「静态面 /api 请求必须为 0」判据 |
| 6 | 不加 `--no-proxy-server` 时 Chrome 走系统代理，别名解析变 502/5s | _qa/dbg_host.py A/B 三组 | 列为硬需求写进 CHROME_ARGS |
| 7 | 预注入采集器没装上时，错误/LCP/CLS 全空读数而判据照样绿（U-221 同族） | 自查 | 探针回填 `pfInstalled`，false 直接判违规 |
| 8 | 自检页 camera 链未 await，报告写完 2.5s 后才回填 → 屏上永远「待测」 | 无头端到端实测 | 并入 promise 链，复跑 camera={mode:gallery,ok:true} |
| 9 | **String.raw 写 HTML 内联 JS 正则，双反斜杠原样落盘 → 页面 SyntaxError**，肉眼读源码看不出 | 无头加载一次即抓到 | 产物写完必过 `node --check`（提取 <script> 单独验）再进浏览器；「写了」≠「能跑」 |
| 10 | 第一版 PDF 所有中文变成字母 I（reportlab Helvetica 不含中文字形） | PyMuPDF 抽文本实测 | 注册 simsun/msyh/simhei（TTC 必须带 subfontIndex）→ 降级 CID → 全不可用则拒绝生成，绝不静默出豆腐 |
| 11 | 规格对账两次误报（拿工艺数字比尺寸 / 圆形只有 1 个数字） | --check 自己判红 | 按语义切段：只比「成品尺寸段」的数字 |
| 12 | 改了中文文案没重建字体子集 → verify 字体完整性判红（缺 10 字） | 门禁当场拦（U-212 立过的规矩，我又踩一次） | 固定动作链：改文案 → build_fonts.py → verify；并留 _qa/check_subset.py 做替换前 cmap 预检 |

### 接入与验证

- CI（`.github/workflows/deploy-pages.yml` Guard self-test 段）新增 3 条：
  `make_proof_pack.py --check` / `reverse_replace_merch_photo.py`（反向验证）。
- 本地套件 `run_browser_suite.py` 新增 `preflight_device_test.py`（--list 复核无重复条目，U-218 纪律）。
- `verify_site.py` → **RESULT: PASS**（整站 1383KB/1600KB、首屏 328KB/400KB、字体缺 0）。
- `ledger_id_test` → PASS（262 条，U 号唯一）。
- `safe_script_test` → PASS（新工具不写真实 site/；PIL save 类生成器与该判据口径本就无关，
  与 make_srcset/build_statue_asset 同类）。
- 自检页二维码 `qr/qr-device-probe.png`：生成 + OpenCV 回读解码 == 目标 URL 双验通过。

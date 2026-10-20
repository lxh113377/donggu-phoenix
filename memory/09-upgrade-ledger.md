# 升级建议台账

> 规则（2026-10-20 立）：**每轮结束前必须把当轮提出的所有升级建议写进本文件**，
> 不等老大提醒。写进这里是「已登记」；进入 `05-next-steps.md` 是「已排期」；
> 两者都要有，避免「只在对话里说过 = 等于没说」。
>
> 字段：ID / 提出轮次 / 问题 / 建议做法 / 状态 / 落地位置
> 状态：待排期 → 已排期 → 进行中 → 已完成 / 已否决（须写原因）

## 开放条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-01 | 3 | 真机未测：所有移动端结论来自 390×844 模拟，iPhone Safari / 微信内置浏览器的曝光、侧光、识别阈值均未验 | 真机走 charles/代理抓包 + 现场拍照留证；至少覆盖 iOS Safari 与微信各一台 | 待排期 | 05-next-steps |
| U-02 | 3-6 | 文创仍是代码渲染图，非实拍；评审一眼能看出「像设计稿不像产品」 | 徽章/纸雕灯/帆布袋打样后实拍替换，保留渲染图作占位回退 | 待排期 | 05-next-steps |
| U-03 | 6 | 手机首屏被撑到 1.32~1.56 屏 | 已改纯静态判据并并入 ci_design_static（CI 实测执行）；反向验证判红 | **已完成**（轮13） | tools/ci_design_static.py |
| U-04 | 8 | 首屏判据曾漏算 5 个脚本 + 2 张 SVG（假绿），已改按实际引用推导 | 判据类改动一律先反向验证；把「判据自检」列为每轮第一步 | 已完成 | memory/08-verify.md |
| U-05 | 9 | perf_anim 假绿：被测抛错被当环境跳过 | 解析失败一律判红；跳过必须打 SKIP 且不计入 PASS | 已完成 | tools/perf_anim.py |
| U-06 | 9 | 注释承诺「低端机自动降级」但代码没有 | 已补硬件分档 + 运行时自适应；建议全站扫一遍「注释与实现不符」 | 已完成（待扩展扫描） | site/assets/js/phoenix.js |
| U-07 | 6 | 装饰环 hero-ring/totem-ring 左右各溢出 7~10px（靠 overflow:clip 兜住） | 已改 transform:scale，天然不溢出；新增 ring_containment_test.py 双轨判据 | **已完成**（轮11） | tools/ring_containment_test.py |
| U-08 | 6 | 入口体积：9 个同步脚本 162KB，无 defer | **实测否决**：脚本全部在 18ms 内执行完、无长任务；DCL 223ms 与脚本无关。加 defer 收益≈0，不值得引入执行顺序风险 | **已否决**（轮11，有实测依据） | memory/08-verify.md |
## 轮11 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-09 | 11 | 反向测试脚本原地改真实文件，把未提交的修复覆盖丢失 | 已建 tools/safe_mutation.py 沙箱：脏工作区拒绝、副本上破坏、结束 SHA256 核验真实文件未变；16 个旧脚本已标废弃 | **已完成**（轮12） | tools/safe_mutation.py |
| U-10 | 11 | 浏览器会话（agent-browser）频繁卡死，单次 set viewport 可超时 90s | 门禁已全部改纯静态（ring 判据不再依赖浏览器）；浏览器仅用于截图与人工核对，不进 CI 判据 | **已完成**（轮12） | tools/ring_containment_test.py |
| U-11 | 11 | DCL 223ms / FCP 216ms 的构成未定位 | 已排除脚本（18ms 执行完/0 长任务）与字体（屏蔽后 FCP 反变 520ms）两个假设；找到 .nav/.toast 的 backdrop-filter 白算但非首绘主因；**受浏览器环境故障阻塞，待环境恢复** | 待排期 | — |
## 轮12 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-12 | 12 | 仍有 16 个 _qa/ 旧脚本保留原地修改逻辑（已标废弃但代码还在） | 后续新测试一律用 safe_mutation；旧脚本仅在需要历史复现时手动跑 | 待排期 | _qa/reverse_*.py |
| U-13 | 12 | 浏览器位置验证（getBoundingClientRect）不再是门禁，仅截图人工看 | 若需自动化位置验证，应在 CI 外单独跑并接受其不稳定；不纳入判红 | 待排期 | — |
## 轮13 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-14 | 13 | agent-browser 报 daemon mismatch / Chrome not found | **已查明：根因是我误删 ~/.agent-browser（内含 Chrome 本体，不只是配置）**。已 agent-browser install 重装；新增 tools/browser_health.py 静态区分「本体缺失」与「进程冲突」 | **已完成**（轮14） | tools/browser_health.py |
| U-15 | 13 | 我曾把「视觉零变化」说成确定结论，实际背景 alpha=0.92/0.95 并非完全不透明 | 判据类结论必须先核算再下断言；已把背景提到 alpha=1 使结论成立，并做 prove_no_visual_change.py 核查 | **已完成**（轮13） | tools/prove_no_visual_change.py |
## 轮14 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-16 | 14 | 段落顶部冗余补偿：.totem/.carve-sec/.ar-sec 各多推 50~60px（锚点已由 scroll-padding-top 处理） | 已统一为 var(--sec-y)；新增静态门禁「段落顶部不得写死补偿值」 | **已完成**（轮14） | tools/ci_design_static.py |
| U-17 | 14 | 破坏性/清理操作前未确认目录语义（删 ~/.agent-browser 删掉了 Chrome 本体） | 删除前先列目录内容确认；不确定时改名备份而非删除 | 待排期 | — |
## 轮15 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-18 | 15 | reveal 判据两次误判：①全 SKIP 判 PASS（假绿）②视口外元素算失败（误报） | 已修：三态区分（PASS/FAIL/SKIP，全SKIP不计PASS）；只判视口内隐藏。反向验证可识别真缺陷 | **已完成**（轮15） | tools/reveal_after_jump_test.py |
| U-19 | 15 | 桌面端逐屏复核未发现新缺陷；段落留白已全部统一（桌面 148px / 移动 76px） | — | **已完成**（轮15，结论：无需改动） | memory/08-verify.md |
## 轮16 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-20 | 16 | H1 主标题重复两遍：main.js 把 hero.line2 与 meta.title 拼接，且 em 用 Cinzel（0汉字字形）渲染中文 | 副标题改纯拉丁「畲 · SHE PHOENIX」；新增 gate 21 | **已完成** | tools/ci_design_static.py |
| U-21 | 16 | 商品图溢出压住标签：grid 隐式行高被撑到 279px，max-height:78% 基准变行高 | 锁 grid-template-rows:100% + 图片固定 150px；新增 gate 22 | **已完成** | tools/ci_design_static.py |
| U-22 | 16 | 门禁自身两次误报（正则范围过宽 / 未剥注释） | 写门禁后必须反向验证该绿时绿、该红时红 | **已完成** | memory/08-verify.md |
## 轮17 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-23 | 17 | 工匠头像 alt 取 p.name，与紧跟的 h3 重复 → 读屏念两遍人名 | 改 alt="" + aria-hidden（装饰性）；新增 gate | **已完成** | tools/ci_design_static.py |
| U-24 | 17 | 字体门禁两处误报：HTML/JS 注释被当成渲染文本 | 扫描前先剥注释；重建子集 193→173KB，首屏 284→268KB | **已完成** | tools/verify_site.py |
| U-25 | 17 | 图片质量检查方法错误：滚回顶部后图片 naturalWidth=0 被误判未加载 | 改为停在目标区域检查；新增 tools/image_quality_test.py（49 图 0 问题） | **已完成** | tools/image_quality_test.py |
## 轮18 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-26 | 18 | 判据把注释当内容是**系统性风险**（轮17 连续两次）：design_audit / originality_audit 仍是裸 read() | 新建 tools/source_scan.py 统一扫描层，三个判据全部接入；双向验证（注释注入不误报 / 真代码注入仍判红） | **已完成** | tools/source_scan.py |
| U-27 | 18 | 我写的中文注释越详细，越容易触发「把注释当内容」的误报 | 判据一律通过 source_scan 读取；新增判据时先想「注释里会不会出现关键字」 | **已完成** | memory/08-verify.md |
## 轮19 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-28 | 19 | 「38 年党龄」是写死的相对时间，源自 2025 年采访，站点长期在线会逐年失真 | 锚定不变事实「1987 年入党」；新增门禁「不得写死 N 年党龄/工龄/教龄」 | **已完成** | tools/ci_design_static.py |
| U-29 | 19 | 集章动线被归到页面上未解释的「东固 · 匠灵幻境」名下，读者会以为依赖未上线的小程序 | 改为陈述本站事实「三枚集齐即解锁完整动线」 | **已完成** | site/assets/data/ar-data.js |
| U-30 | 19 | 内容核对项（非遗级别/数字自洽/术语一致）全部确认无问题 | 已记录核对依据（采访稿原文、时长加总） | **已完成** | memory/08-verify.md |
## 轮20 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-31 | 20 | 5 处中英信息不对等：英文丢失诗句/人名/数字/核心论点/遗言 | 全部补齐英译；新增 bilingual_parity_test.py（比例/年份/引诗/Markdown 四判据） | **已完成** | tools/bilingual_parity_test.py |
| U-32 | 20 | 我补英文时引入 Markdown 斜体 *Pride of Fisherman*，页面纯文本渲染会显示星号 | 改为引号；门禁加「英文不得含 Markdown 标记」判据 | **已完成** | tools/bilingual_parity_test.py |
## 轮21 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-33 | 21 | 出处数据齐全但读者看不到：ar.js 只渲染「素材出处 N 条」，从不展示 label/url | 改原生 `<details>` 可展开列表，默认收起；加 .ar-src 样式；新增门禁「出处必须渲染 label」 | **已完成** | site/assets/js/ar.js |
| U-34 | 21 | 出处审计（13 章全有 note、8 个独立来源、4 个链接实测 HTTP 200 可访问） | 确认无编造；改为可展开后读者可自行追溯 | **已完成** | memory/08-verify.md |
## 轮22 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-35 | 22 | 8 个数据字段从未被前端引用，其中 meta.year 与页面年份语义不同、ar-data.js meta.subtitle/weight 是旧版文案 | year 改名 fieldworkYear 并注明；删除过时字段（-105B）；新增 dead_data_test.py | **已完成** | tools/dead_data_test.py |
| U-36 | 22 | dead_data_test 第一版正则写成双反斜杠 → 匹配 0 个字段却判 PASS（假绿） | 修正正则；教训：检查到 0 个对象时必须判 SKIP/FAIL，不能 PASS | **已完成** | tools/dead_data_test.py |
## 轮23 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-37 | 23 | 「零样本判 PASS」结构错误连续三轮复发（轮9/15/22），单靠提醒无效 | 建 tools/gate_guard.py：checked==0 且未显式允许 → SKIP（绝不 PASS）；SKIP 退出码 0 但必须可见 | **已完成** | tools/gate_guard.py |
| U-38 | 23 | 守卫自身也会坏 | gate_guard 自检（5 用例）+ dead_data_test 接入 CI 的 Guard self-test 步骤，CI 日志确认执行 | **已完成** | .github/workflows/deploy-pages.yml |
| U-39 | 23 | 其余工具尚未接入统一守卫 | 逐个评估 31 个脚本：门禁类 6 个中 3 个已自带处理，perf_anim 与 prove_no_visual_change 有真实风险 → 已接入；prove 并入 CI | **已完成**（轮24） | tools/gate_guard.py |
## 轮24 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-40 | 24 | 一次性反向验证脚本（reverse_*.py）未接入守卫 | 它们本就是「构造破坏→看判红」，零样本不构成假绿风险；仅在 R50 记录，不改 | **已否决**（有理据） | — |
## 轮25 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-41 | 25 | 对比度长期靠肉眼估，无量化判据 | 建 tools/contrast_audit.py：浏览器计算色 + alpha 合成，119 处全达标；反向验证可抓出 66/119 | **已完成** | tools/contrast_audit.py |
| U-42 | 25 | 对比度测量前三次尝试（CSS 解析/像素极值/固定坐标）全部不可信 | 教训：CSS 背景要处理渐变与 alpha 合成；像素采样要绑定元素真实位置。已记入工具注释 | **已完成** | tools/contrast_audit.py |
| U-43 | 25 | 反向验证被 HTTP 缓存误导（改 CSS 后浏览器仍加载旧文件） | 站点有版本对账守卫，但测试用唯一 URL 绕过 sessionStorage 状态；正确做法是 about:blank 重置后走正常 URL | **已完成** | tools/reverse_contrast3.py |
## 轮26 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-44 | 26 | 前二十多轮验证全在静态资产与 CSS，**AR 播放这个站点主体从未系统验过** | 建 tools/ar_e2e_test.py：6 项端到端（API/三段切换/时间推进/落章），实测全 PASS | **已完成** | tools/ar_e2e_test.py |
| U-45 | 26 | 用 seek() 跳到段末不落章，一度误判集章坏了 | complete() 只在 playing 分支调用，设计如此；正确测法 seek(duration-3)+play()。已写进工具注释 | **已完成** | tools/ar_e2e_test.py |
## 轮27 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-46 | 27 | 8 个 section 留白全为 148px（唯一值），但内容密度差 5.6 倍 → 滚动匀速、无节奏起伏 | 按实测内容密度分级：tight 104 / snug 126 / base 148 / roomy 170 / loose 185；桌面总高 11475→11336 | **已完成** | site/assets/css/main.css |
| U-47 | 27 | 留白分级可能被后续改动退回统一值 | 新增 rhythm_test.py 4 条判据（令牌存在/≥3级在用/最密用最紧/最疏用最松），接入 CI | **已完成** | tools/rhythm_test.py |
## 轮28 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-48 | 28 | 22 个 .reveal 元素 transition-delay 全为 0s（含所有 .sec-head）→ 标题与内容同时淡入，无层次 | 纯 CSS 相邻兄弟选择器给标题后首块 120ms；标题置 0ms；7 个 sec-head 三类下一项全覆盖 | **已完成** | site/assets/css/main.css |
| U-49 | 28 | stagger_test 第一版用 `if max(vals) < 60` 判定 → 两种破坏都判不出（聚合洗绿） | 改逐条校验：任何一条 <60ms 即判红。这是第 4 次同类错误（前 3 次：零样本判 PASS） | **已完成** | tools/stagger_test.py |
| U-50 | 28 | 浏览器 daemon 被并发进程反复占用，无法跑浏览器复验 | 改用 HTTP 直接取线上 CSS 静态核对：STAGGER-TUNE 5 条规则 + RHYTHM-MAP + 留白令牌全部存在，线上 build=23 | **已完成**（替代验证） | _qa/check_live_css.py |
## 轮29 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-51 | 29 | 4 个无限循环动画漏 reduced-motion 覆盖（spin/pulse/ringPulse）→ WCAG 2.3.3 前庭障碍风险 | 追加 media 块置 animation:none，保留静态外观；新增 reduced_motion_test.py 接入 CI | **已完成** | site/assets/css/main.css |
| U-52 | 29 | 动效参数审查（缓动/时长/linear 用法）结论：无缺陷 | linear 用于旋转与进度条，语义正确；2 个裸 cubic-bezier 是令牌定义本身 | **已核实无问题** | — |

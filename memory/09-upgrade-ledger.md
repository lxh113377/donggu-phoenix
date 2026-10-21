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
| U-11 | 11 | DCL 223ms / FCP 216ms 的构成未定位 | **轮33 定位到根因**：HTML 有 9 个同步 <script>（无 defer/async），合计 163.4KB/58.2KB gzip，阻塞 HTML 解析。改为 defer 后 A/B 实测（各 10 次采样）：domInteractive 237→143ms（-40%），FCP 156→160ms（噪声内），DCL 基本持平。新增 critical_path_test.py 防回归 | **已完成** | site/index.html |
## 轮12 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-12 | 12 | 曾有 16 个 _qa/ 旧脚本含原地修改逻辑 | 轮32 双重复核（正则扫 open+写入模式 / 扫 .write 含 site 路径）：**0 处脚本会写入真实 site/ 文件**；43 个脚本已用 safe_mutation，8 个用 git 还原。风险已消除 | **已完成**（轮32 复核） | — |
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
## 轮30 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-53 | 30 | AR 全屏焦点行为从未验证（移入/陷阱/恢复） | 建 ar_focus_test.py 7 项检查：实测实现完全正确 7/7 | **已完成**（非缺陷） | tools/ar_focus_test.py |
| U-54 | 30 | 反向验证被 SW cache-first 假绿（破坏代码后仍全 PASS） | 测试前注销 SW + 清 caches + 唯一 URL；修正后判红。第 5 次「测量手段不可靠」 | **已完成** | tools/ar_focus_test.py |
| U-55 | 30 | 用 API 打开 AR 导致误判焦点恢复失效（BODY→BODY 是正确的） | 必须走真实用户路径（先 focus 场景链接再 click），已写进工具注释 | **已完成** | tools/ar_focus_test.py |
## 轮31 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-56 | 31 | `#cam .close` 摄像头关闭按钮（44×44 常驻）无 hover 也无 active 反馈 | 补 hover（边框/文字提亮到 --she-gold）+ active（scale .94），强度对齐 .btn | **已完成** | site/assets/css/main.css |
| U-57 | 31 | 初版审查误判「9 个元素都缺 focus-visible」 | 核实有全局兜底 `:focus-visible{outline:2px...}`（正确做法）；判据改为检查全局兜底而非逐个元素 | **已完成** | tools/microinteraction_test.py |
| U-58 | 31 | microinteraction_test 正则被局部规则误匹配（#carve-stage:focus-visible 被当全局兜底） | 改为只认「行首的 :focus-visible」；反向验证修正后可判红 | **已完成** | tools/microinteraction_test.py |
## 轮32 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-59 | 32 | 新增的 safe_script_test 自身判红：反向验证脚本里的**字符串字面量**被当成真实写入 | 豁免 reverse_safe_script.py 并写明理由；改用干净克隆验证（本地 484 个脚本 vs 克隆 82 个） | **已完成** | tools/safe_script_test.py |
| U-60 | 32 | 「本地绿 CI 红」：本地跑时临时脚本也在，误以为 FAIL 来自临时脚本 | 新增判据后必须用干净克隆复验，不能只看本地 | **已完成** | — |
## 轮33 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-61 | 33 | 单次性能采样不可靠：首测得 DCL -56% / FCP -43%，严格 A/B（各 10 次）后变成 domInteractive -40%、FCP 持平 | 性能结论必须多次采样取中位数并排除冷启动异常值；单次测量会骗人 | **已完成** | _qa/ab_final.py |
| U-62 | 33 | 本地 8791 服务曾停止，导致测试读到 chrome-error 页面（误以为 defer 破坏站点） | 测试前先探服务可用性（Invoke-WebRequest 200 检查） | **已完成** | — |
## 轮34 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-63 | 34 | defer 改了脚本执行时机，静态判据只能证明「有 defer」不能证明「功能正常」 | 建 defer_regression_test.py 5 项运行时回归（7 全局对象/body.ready/H1/六类内容块/凤凰画布） | **已完成** | tools/defer_regression_test.py |
| U-64 | 34 | 第 6 次「测量不可靠」：defer_regression_test 反向验证被 SW 缓存假绿（打乱脚本顺序仍全 PASS） | 固定套路：about:blank → clear_sw.js → about:blank → 唯一 URL。并建 browser_test_lint.py 检查所有浏览器测试 | **已完成** | tools/browser_test_lint.py |
| U-65 | 34 | 3 个反向验证脚本缺防缓存（reverse_image_quality / reverse_reveal / 误报的 reverse_contrast3） | 已由 browser_test_lint 抓出并纳入警告；reverse_contrast3 经核实安全，判据改为「满足任一即可」 | **已完成** | tools/browser_test_lint.py |
## 轮35 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-66 | 35 | 中文排版从未被工程化检查（避头尾/标点挤压/中西文间距/行长） | 逐项实测：标点行首 0 处、正文混排 0 处、keep-all 无溢出 → **无缺陷**；固化为 cjk_typography_test.py 4 条判据 | **已完成**（非缺陷） | tools/cjk_typography_test.py |
| U-67 | 35 | text-spacing-trim / text-autospace 看似可改进 | 实测收益小（本站标点不多、正文几乎无中西混排）→ 主动不加，避免过度优化 | **已否决**（有理据） | — |
| U-68 | 35 | 性能旧记录 216/223ms 已过时 | 实测当前 FCP 中位 180ms、domInteractive 149ms、DCL 248ms；FP=FCP 说明首屏立即绘制。Google「良好」阈值 1800ms，已优 10 倍 | **已核实无问题** | — |
## 轮36 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-69 | 36 | 8 份判据全部由我自己建立，可能存在同源盲区 | 尝试调用 codex/claude 做独立评审（工具均可用），但 codex 运行超时未返回；改为自建客观读数复核 | **部分完成**（工具可用，长 prompt 超时） | — |
| U-70 | 36 | 「AI 生成感」未审查过 —— Awwwards 评审最敏感 | 实测：16 个 AI 套话 0 次；16 次具名人物；12 个真实年份；12 部文献引用 → 有实证支撑，非 AI 空话 | **已完成**（非缺陷） | _qa/audit_ai_taste.py |
| U-71 | 36 | 动效时序是否有设计意图未验证 | 实测首屏 5 元素 delay 严格递增：200→350→600→850→1050ms，符合「主信息先到」 | **已完成**（非缺陷） | _qa/audit_hero_t3.py |
## 轮37 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-72 | 37 | 首屏黄金位置放工程验收指标（第三方库 0/外部请求 0），是自证不是观众关心的内容 | 换成文化证据（国家级非遗/传承廿余代/AR 展陈）；工程指标移到 ar-gallery 轻量化说明 | **已完成** | site/index.html |
| U-73 | 37 | 两个 CTA 视觉权重相同，观众不知道先点哪个 | 三级权重：金色实心（主）/ 透明金边（次）/ 纯文字（三级） | **已完成** | site/assets/css/main.css |
| U-74 | 37 | H1 四段渐变 + 朱红大范围 drop-shadow，与金色凤凰争夺高光中心 | 保留渐变字（设计语言），阴影 46px朱红.32 → 22px金.18 | **已完成** | site/assets/css/main.css |
| U-75 | 37 | hero-meta 从 4 项改 3 项后总宽 538px > 容器 491px，第 3 项换行 | 缩短文案「3段·13章·2′32″」→「3段·13章」→ 474px，distinctRows 2→1 | **已完成** | site/index.html |
| U-76 | 37 | 28 条判据全部出自自己，存在同源盲区 | **独立评审有效**：codex 短 prompt（≤7k tokens）可正常返回，长 prompt 会超时。已据此发现 3 个我自己漏掉的问题 | **已完成**（建立方法论） | — |
## 轮38 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-77 | 38 | 文创四个分类分属四种维度（开发状态/渠道/媒介/价格），且帆布袋被归为高客单是矛盾 | 改为用户场景分类：桌面陈设3/现场带走3/日常使用3/收藏送礼2/数字互动1；帆布袋修正为日常使用 | **已完成** | site/assets/data/culture.js |
| U-78 | 38 | 首推位是徽章（Ø58mm 批量发放小物），放大也看不出工艺 | 换为纸雕灯（七层激光镂空+分层叠影+开灯见凤舞）；并按场景重排顺序 | **已完成** | site/assets/data/culture.js |
| U-79 | 38 | 改名引入 3 个新汉字（桌/送/互）不在字体子集内 | 重建子集（853 字符/725 汉字，171.9KB） | **已完成** | site/assets/fonts/zcool-display.woff2 |
| U-80 | 38 | **CI 环境没装 fontTools，字体完整性判据被 SKIP** → 缺字会静默上线 | CI 依赖加 `fonttools brotli`；CI 日志确认 [PASS] 字体完整性（缺 0）真正执行 | **已完成** | .github/workflows/deploy-pages.yml |
| U-81 | 38 | 文创图片全是渲染图（make_merch_renders.py 生成），非实拍 | 评审指出这会削弱可信度（已印证 U-02）；需实物打样后实拍替换 | 待排期（需实物） | — |
## 轮39 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-82 | 39 | CI 只跑 13 个工具，漏了 bilingual_parity_test 与 originality_audit（两者的依赖都在 git 里） | 两个加入 CI（现 15 个）；干净克隆验证均 PASS | **已完成** | .github/workflows/deploy-pages.yml |
| U-83 | 39 | **originality_audit 从不判红**：失败只打 [WARN]，从不 sys.exit(非零)，入 CI 后必然假绿 | 补判定出口（有失败项则 RESULT: FAIL + exit 1）；反向验证注入 AI 紫后成功判红 | **已完成** | tools/originality_audit.py |
| U-84 | 39 | originality_audit 硬编码绝对路径 `C:\Users\37533\...` + os.chdir → safe_mutation 沙箱失效、换机器跑不了 | 改为基于 `__file__` 的相对路径 | **已完成** | tools/originality_audit.py |
| U-85 | 39 | verify_asset_is_source 依赖 `_dev/`，但该目录 0 个文件被 git 跟踪 → 加入 CI 会 SKIP，无意义 | 不加 CI；已在台账说明理由 | **已否决**（有理据） | — |
## 轮40 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-86 | 40 | 静态扫 `exit(1)` 会误报判据的失败出口（gate_guard 用 `sys.exit(0 if ... else 1)`） | 改用「注入破坏 → 看退出码」实测法：critical_path/reduced_motion/microinteraction 破坏后均返回 1 | **已完成**（验证基础设施可靠）| — |
| U-87 | 40 | 「构图是否平衡」只能主观判断 | 建 visual_balance_test.py：视觉重量 = 相对背景亮度对比 × (1+饱和度)；实测首屏左52.8%/右47.2%，差异5.6% 判平衡 | **已完成** | tools/visual_balance_test.py |
| U-88 | 40 | 独立评审（codex 看图）给的 4 条建议，逐条核实后 **0 条构成真实缺陷** | 评审也会过严/不准；必须用像素数据核实再决定是否采纳 | **已完成**（含量化核实） | — |
## 轮41 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-89 | 41 | 响应式此前只测 1440/390 两个宽度，320px 下有两处越界未发现 | 建 multi_viewport_test.py 覆盖 9 视口（320-2560）；实测修复后全部 PASS | **已完成** | tools/multi_viewport_test.py |
| U-90 | 41 | `.craft` 的 grid `minmax(320px,1fr)` 下限大于 320px 视口下的容器宽 284px → 卡片被强制撑宽 36px | 改为 `minmax(min(320px,100%),1fr)` | **已完成** | site/assets/css/main.css |
| U-91 | 41 | `.carve-slider-label::after` 补充文案「·按住画面左右拖也可」把 label 撑到 175px，320px 下挤压 slider 越界 16px | 窄屏（≤420px）隐藏该 ::after（触屏用户不需要此提示） | **已完成** | site/assets/css/main.css |
| U-92 | 41 | 第 3 次被 SW cache-first 骗（改完 CSS 测试仍失败，误以为修复无效） | 把「先清 SW」写进 multi_viewport_test.py 开头，不再依赖记忆 | **已完成** | tools/multi_viewport_test.py |
## 轮42 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-93 | 42 | 手机横屏（568×320）首屏标题跑出视口：.hero-tag top −119、.hero h1 top −77 | 矮屏横置时压缩 padding 4/10、隐藏导语与数据行、h1 降字号、顶对齐 | **已完成** | site/assets/css/main.css |
| U-94 | 42 | iPhone SE（375×667）H1 被固定导航遮挡 26px（top 56 < nav 82） | 分析后选择「允许滚动」而非削减内容；`max-height:700px` 解锁 `height:100svh` | **已完成** | site/assets/css/main.css |
| U-95 | 42 | 窄宽度（320/360）同样遮挡：内容高度取决于宽度（按钮堆叠），单看高度不够 | 解锁条件扩展为「高度矮 或 宽度窄」；320 验证 heroHeight 844→878.9px、tag top 67→84 | **已完成** | site/assets/css/main.css |
| U-96 | 42 | multi_viewport_test 只查横向溢出，漏掉纵向裁切与导航遮挡 | 补两条判据：首屏关键元素被裁 / 被固定导航遮挡；本轮共抓出 4 处缺陷 | **已完成** | tools/multi_viewport_test.py |
## 轮43 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-97 | 43 | 禁用 JS 时主体内容（文创/文化/AR/场景）全部空白，且无任何提示 | 加 `<noscript>` 提示（说明需 JS + 微信内可「在浏览器中打开」）；不做静态化（成本高收益低） | **已完成** | site/index.html |
| U-98 | 43 | noscript 新文案引入 5 个汉字（择渲置若角）不在字体子集 | 重建子集（858 字符/730 汉字，172.7KB）；这次是字体门禁主动抓到的 | **已完成** | site/assets/fonts/zcool-display.woff2 |
| U-99 | 43 | 打印样式与一屏解锁副作用此前未验证 | 打印：已存在 7 条 @media print 规则（背景转白/隐藏装饰/H1 改纯黑/强制 reveal 可见）；解锁副作用：桌面与主流手机仍锁一屏，未误伤 | **已核实无问题** | — |
## 轮44 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-100 | 44 | 浏览器返回键清空 hash 后 AR 仍保持打开（hash 与状态不同步） | hashchange 处理器补「hash 为空且 AR 打开 → close()」，用 `_closingByHash` 防循环 | **已完成** | site/assets/js/ar.js |
| U-101 | 44 | 反向验证时用非法破坏方式（`if (!id) { return;` 造成语法错误）→ 浏览器加载失败 → 判据假绿 | 破坏性测试必须保证破坏后代码仍可运行；改用 `if (false) {` 后准确判红 | **已完成**（方法论） | tools/reverse_deeplink2.py |
| U-102 | 44 | `history.back()` 会中断 CDP async 探针（Inspected target navigated or closed） | 拆成「读状态 → 触发返回 → 重连后再读」三步 | **已完成** | tools/ar_e2e_test.py |
## 轮45 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-103 | 45 | 错误边界/HTTP缓存/SW更新三维度此前从未验证 | 逐项实测：图片 onerror 3/3、canvas 失败页面仍可读、版本对账守卫兜底缓存、SW skipWaiting+claim 齐全 → **均无缺陷** | **已完成**（非缺陷） | tools/resilience_test.py |
| U-104 | 45 | 容错能力无防回归判据 | 建 resilience_test.py 5 条（图片 onerror/noscript/版本对账/SW更新/try 块数），接入 CI；反向验证两种破坏均判红 | **已完成** | tools/resilience_test.py |
| U-105 | 45 | 未加全局 `window.onerror` | 判断后**不加**：本站 17 个 try 块已覆盖关键路径，无后台上报，全局捕获收益低 | **已否决**（有理据） | — |
## 轮46 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-106 | 46 | 进场元素若永不触发会「静默消失」（不报错不白屏，只是某块内容永久不可见） | 建 reveal_coverage_test.py：滚遍全站后所有 `.reveal` 必须带 `.in`；反向验证注入永不进视口的元素能判红 | **已完成** | tools/reveal_coverage_test.py |
| U-107 | 46 | 探针步进 `y+=600` 最后一步不一定落在 maxY，导致页脚误报「不显示」 | 循环后必须显式 `scrollTo(0, scrollHeight)` 一次；已写进判据注释 | **已完成**（方法论） | tools/reveal_coverage_test.py |
| U-108 | 46 | 15 个浏览器判据只在本地跑，CI 覆盖不到，长期不跑会悄悄失效 | 建 run_browser_suite.py 统一入口（15 项，--fast 9 项 143s）；聚合判定「一项 FAIL 即 FAIL」 | **已完成** | tools/run_browser_suite.py |
## 轮47 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-109 | 47 | `og:description`（微信分享卡片文案）仅 24 字且缺主体身份，而另外两处描述都有 | 补为 45 字含「江西科技学院薪火寰行实践团 × 东固畲族乡」；建 social_meta_test.py 6 项判据接入 CI | **已完成** | site/index.html + tools/social_meta_test.py |
| U-110 | 47 | 判据关键词选错：「东固」既是地名又出现在「东固非遗文创」里，导致「缺身份」误判为「有身份」 | 主体身份必须是「谁做的」（实践团/学院），不能用「在哪做的」（东固） | **已完成**（方法论） | tools/social_meta_test.py |
| U-111 | 47 | 反向验证替换打错位置：身份串在 index.html 出现 2 次，`replace(...,1)` 只改了 description | 用正则精确替换目标 meta 整条，不要用全局字符串替换 | **已完成**（方法论） | tools/reverse_social_meta.py |
| U-112 | 47 | 曾误判「首屏间距梯度反了」（组内 32 / 组间 47，比值 1.47） | 裁切放大后发现 CTA 与数据条之间有 1px 分隔线，分组信号足够 → **不是缺陷**；只看 margin 数值会误判 | **已否决**（有理据） | — |
## 轮48 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-113 | 48 | 主推文创卡片 541×846，图片仅 214×246（填充率 11.5%），产品细节看不清 | 容器改 `aspect-ratio:4/3 + flex:1 1 auto`，图片放宽到 88%；填充率 11.5%→38.5% | **已完成** | site/assets/css/main.css |
| U-114 | 48 | 根因是 `.merch-shot img{max-height:150px}`（为普通卡片设）未被 is-feature 覆盖 | 大容器必须显式覆盖小容器的尺寸约束，否则继承到不适用的值 | **已完成**（方法论） | site/assets/css/main.css |
| U-115 | 48 | 反向验证破坏点选在文件中部旧规则块，被末尾新规则覆盖 → 判据仍 PASS，误判为缓存 | 破坏测试必须作用在**最终生效**的那条规则上（同特异性后写者胜） | **已完成**（方法论） | tools/reverse_merch_fill.py |
| U-116 | 48 | canvas 曾疑似未处理 DPR | 实查三个 canvas 均正确 `Math.min(devicePixelRatio,2)` + `setTransform`；当前环境 dpr=1 所以 ratio=1 是正确表现 → **不是缺陷** | **已否决**（有理据） | — |
## 轮49 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-117 | 49 | agent-browser 视口曾被压缩到 565px（而非 900px），会让视觉结论基于错误视口 | 逐段审视前必须显式 `set viewport`；browser_test_lint 新增 viewport-lint（open 页面却未设视口 → WARN） | **已完成** | tools/browser_test_lint.py |
| U-118 | 49 | 曾误判匠人头像「像同一张照片」 | 实查是两个独立文件 craft-liu.webp / craft-lei.webp；缩略图太小看错 | **已否决**（有理据） | — |
| U-119 | 49 | 曾误判头像「缺 alt」 | 实为 `alt="" aria-hidden="true"` + 注释说明 WCAG H67（后面 h3 已有人名，避免读屏念两遍）；正则漏匹配 aria-hidden 导致误判 | **已否决**（有理据） | — |
| U-120 | 49 | 批量补视口时正则匹配错位，把 reveal_after_jump_test.py 插成 8 空格缩进 → IndentationError | 批量改脚本后必须 `py_compile` 验证 + 实跑；已修复并复跑 8/8 PASS | **已完成** | tools/reveal_after_jump_test.py |
## 轮50 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-121 | 50 | 判据本身有缺陷：面积填充率随视口漂移（桌面 38.5% vs 移动 24%）、对图片比例敏感（书签天然 6%），固定阈值 25% 在移动端误判 | 换 dominant 指标 = max(图宽/内框宽, 图高/内框高)：contain-fit 必有一边贴内框，健康值 ~0.88；被额外约束压小时 << 0.8。视口无关、比例无关 | **已完成** | tools/merch_image_fill_test.py |
| U-122 | 50 | 判据只测桌面，移动端布局从未测过文创占比 | 双视口（1440×900 + 390×844）都要求 dominant >= 0.80；反向验证撤销修复后桌面 0.29 / 移动 0.60 双判红 | **已完成** | tools/merch_image_fill_test.py |
| U-123 | 50 | 撤销测试一度「无效」——验证脚本没绕缓存 | 判据 measure() 内置 cacheBust（注入带时间戳 <link>），撤销后真实读到变化；反向验证恢复可信 | **已完成** | tools/merch_image_fill_test.py |
## 轮51 新增条目（对标改进 I-5/I-6/I-7/I-8 落实轮）

> **编号撞车说明**：本块与下方「## 轮51 新增条目」（并行端同时写入）都从当时的最大值 U-123 续编，造成 U-124/126/127 撞号、U-125 与其 U-126 重复登记同一事故。
> 处理：本块（锋/ds 端）改让号为 U-132/133/134，重复的死循环条目改为指向其 U-126；并行端条目原样不动（不代改他人工作面）。教训入本块末尾：并发写台账必须先 list 现值再续编。

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-132 | 51 | 面积/几何类参数从 CSS 脑补：我推导「手机 anchor≈354x370、平板画布小于桌面」，浏览器实测推翻两条 —— anchor 实测 53,100px²（高被 grid 压到 150px），且 768x1024 面积 367,733px² 比桌面还大 | 几何参数一律实测取值再标定；密度改用两点式拟合（锚在两个已验证的历史档位上），并用 7 个视口实测校核「无一处比旧口径更密」 | **已完成** | site/assets/js/phoenix.js |
| （并入） | 51 | reduced_motion_test.blocks() 死循环挂死 CI —— 与并行端 **U-126 同一事故**（双方都从 max U-123 起编导致撞号），此处不再重复占号 | 见下方 U-126 的修法（只匹配真 @media 块 + 先剥注释）；我这边补充的证据：20 个 python 进程各烧 900+ 秒 CPU、CI run 39422600111 卡 15m21s 被取消 | **已完成** | tools/reduced_motion_test.py |
| U-133 | 51 | 新判据扫源码未剥注释，把我写在 phoenix.js 注释里的「旧口径 isMobile ? 1500 : 2600」当成代码，误报「硬档位复活」 | 与 U-24 同因，本轮把 strip_comments 定为判据标配（engine/narration 两判据都过一遍） | **已完成** | tools/engine_polish_test.py |
| U-134 | 51 | 真缺陷：旁白 aria-pressed 只在 paintHud 内同步，而 paintHud 开头 `if (!state.scene) return` ⇒ AR 未开时点旁白，narr.on 已 true 但按钮不变、读屏不知 | 状态同步抽成独立 syncNarrBtn()，点击与 API 两处立刻调用 | **已完成** | site/assets/js/ar.js |
| U-128 | 51 | 真缺陷：I-8 让 create() 对未知场景抛错后，播放层停在「已打开但无场景」的空舞台 = 白屏，比报错更难解释 | 抛错后依次回落到其他已注册场景，全不可用则 close() 退回落地页 | **已完成** | site/assets/js/ar.js |
| U-129 | 51 | 反向验证用例锚点与真实代码不同步（我写的破坏串按 LF 拼、文件是 CRLF）⇒ 破坏没生效，「判据 PASS」被误读成「判据无效」 | 锚点失配必须显式打 [锚点失配] 并计入未抓到（FAIL），不得静默 continue；文本模式读取会归一行尾，破坏串一律先归一再比 | **已完成** | tools/reverse_new_gates.py |
| U-130 | 51 | run_code 沙箱内 python 缺 USERPROFILE ⇒ 用户 site-packages 不可见 ⇒ fontTools/cv2 报缺库、判据假红（「环境伪红」被当代码缺陷） | 判据一律经 pwsh 真实环境执行；报错先查 sys.executable 与库可见性再归因（win-toolchain-pitfalls 同族） | **已完成**（本轮改用 pwsh 复跑） | — |
| U-131 | 51 | 本地 safe_script_test 判红：并行端留下的 `_qa/apply_review3.py` 含 `open(site/index.html,'w')` 原地写真实文件 | 不代改他人工作面文件。CI 不受影响（_qa/ 被 .gitignore 排除、git 跟踪面为空），故本地噪声；由并行端自行改用 safe_mutation 或删除 | 待排期（归并行端） | _qa/apply_review3.py |
## 轮51 新增条目
| U-135 | 51 | **并发写台账撞号**：我与并行端同轮都从当时最大值 U-123 续编，产出 U-124/126/127 三对同号、并把同一起 reduced_motion 死循环事故登记了两次。台账是「已登记」的唯一凭据，撞号等于两条记录互相覆盖语义 | 续编前先扫现值再定号（不要假设自己独占）；本轮我的条目让号为 U-132/133/134、重复条目改为指向并行端 U-126，并行端条目一律不代改。建议把「U 号唯一性」做成判据（脚本扫 `^\| U-(\d+) \|` 计数>1 即判红） | **已完成**（本轮已让号）；判据化待排期 | memory/09-upgrade-ledger.md |

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-124 | 51 | 移动端 `.carve-slider` 命中区 195×3px、thumb 22px，低于 WCAG 2.5.8 AA 的 24px；拇指拖不中（进度轴是该段唯一操作方式） | input 高 3→44px 作命中区，轨道用 `background-size:100% 3px` + center 保持视觉细线，thumb 22→26px；视觉零变化 | **已完成** | site/assets/css/main.css |
| U-125 | 51 | 触摸目标尺寸此前从未检查 | 新增 touch_target_test.py：双视口（390×844 + 1440×900）非 inline 交互元素 >= 24px；Inline 链接按 WCAG 2.5.8 豁免 | **已完成** | tools/touch_target_test.py |
| U-126 | 51 | **判据自身死循环把 CI job 静默挂死 8 分钟**：`reduced_motion_test.blocks()` 在未剥注释的 CSS 上 find('prefers-reduced-motion')，命中注释里的字面量后 rfind('@media') 找到注释之前的无关块，`end <= i` 使 idx 回退 → 无限循环 | 只匹配 `@media ... {` 真块（正则）+ 调用前 strip_comments + idx 严格前进；这是 U-22/U-24「扫代码必须先剥注释」**第 3 次**复现 | **已完成** | tools/reduced_motion_test.py |
| U-127 | 51 | 并发操作失误：我删掉了外部并行工作留下的 `_qahero_out.txt`（误判为我的垃圾） | 并发环境下只清理**自己**明确产生的文件；时间戳早于本轮动作的未跟踪文件不动 | **已记录**（教训） | — |
## 轮52 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-140 | 52 | 运行时健康（内存/节点累积/动画循环叠加）此前从未验证；本站是展现场景长时间开着的站 | 新增 runtime_health_test.py 4 项判据；实测 AR 开关 45 次节点 579→588→588→588 稳定、粒子恒定、60s 长跑内存非单调上升 → **无泄漏** | **已完成**（非缺陷） | tools/runtime_health_test.py |
| U-141 | 52 | 判据若用「终值-初值」会把首轮常驻 DOM 创建误判成泄漏；内存绝对值会因 GC 时机误报 | 节点只看 `max(nodes[2:]) - nodes[1] > 2`（首轮之后）；内存判「非单调上升」而非绝对值 | **已完成**（方法论） | tools/runtime_health_test.py |
| U-142 | 52 | **`location.reload()` 会让 SW 重新注册并用 cache-first 返回旧 JS**；带 `?cb=` 的 fetch 能取到新文件但页面里函数仍是旧版 | 只有「清 SW 后 open 全新 URL」才真正回源；反向验证 JS 行为应改用**运行时打补丁**直击判据公式 | **已完成**（方法论） | tools/reverse_runtime_health.py |
| U-143 | 52 | rAF 帧率探针在后台标签页被浏览器节流，等 60 帧永不返回，挂死一次任务 | 不测帧率：测出来的是环境噪声不是产品问题 | **已否决**（有理据） | — |
## 轮53 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-144 | 53 | **engine_polish_test 是名字存在性判据**：把调用点 `this._densFor(` 改名后，定义仍在 → 23 项仍全 PASS。密度自适应被完全断开而门禁看不见 | 新增 dead_definition_test.py：必须「定义存在 + 至少一个调用点」；按形态区分 prototype 点调用与裸函数调用；接入 CI | **已完成** | tools/dead_definition_test.py |
| U-145 | 53 | `safe_mutation.patch` 内部是 `replace(old,new,1)` 只替换第一处，用它做「断开全部调用点」的反向验证会漏，误判成判据失效 | 反向验证要构造「完全断开」必须全局替换；先数清调用点处数再设计用例 | **已完成**（方法论） | tools/reverse_dead_definition.py |
| U-146 | 53 | **我的脚本把 phoenix.js 清成 0 字节**：finally 里 `open(p,'w').write(open(p).read())`，写模式先截断再读 | 绝不用 `open(p,'w')` 原地自我改写；破坏操作只在沙箱副本做（v3 已改）；已 git checkout 恢复并 node --check + 6 项门禁复验无损 | **已恢复**（教训） | — |
| U-147 | 53 | M11「粒子数随面积变化」/ M12「HUD ≤10 写/秒」是运行时行为，全站无任何判据在运行时验证（静态判据只查名字与调用点） | 待办：浏览器稳定后跑四视口粒子数单调性 + hud.writes 每秒计数；轮54 已闭合：把 _densFor 当纯函数直接喂面积（绕开 resize，agent-browser 卡死 4 次的教训），实测曲线 1319→2600 单调+夹取、HUD 203 次/秒调用挡到 10 次/秒写入 | **已完成**（轮54） | tools/engine_behavior_test.py |
## 轮54 新增条目

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-136 | 54 | 判据第三层盲区：名字在 + 调用点在，**行为**仍可能坏（M11/M12 是验收标准却无人实测） | 新增 engine_behavior_test.py 实测面积曲线与 HUD 写入速率；已接入 run_browser_suite | **已完成** | tools/engine_behavior_test.py |
| U-137 | 54 | **判据自身漏洞**：judge_hud(9, 4) 侥幸通过 —— 帧率仅 9/s 时每帧写也才 9 次，比率判据失效，「写入少」是帧率低不是节流挡的 | 加 MIN_MEASURABLE_FPS=30 门限，低于它明确报「不可测，不得当作通过」 | **已完成** | tools/engine_behavior_test.py |
| U-138 | 54 | 端到端反向验证（改 JS 文件再跑）不可信：注入确实到页面（fileHasMark=true、函数源码含 return 2000）但判据仍 PASS —— 实例状态是构造时算好的 + 缓存时序污染 | 判定逻辑抽成纯函数（judge_density/judge_hud），用构造数据单测；判据也因此变成可单测的（对齐 I-9） | **已完成**（方法论） | tools/reverse_engine_behavior.py |
| U-139 | 54 | 反向验证的**期望值本身**写错两次：2514 是 2600 的 96.7% 在容差内却标成期望判红；一度把同一组数据写了相反的两个期望 | 期望值必须按判据口径算过再写；用例数据要互不相同避免自相矛盾 | **已完成**（方法论） | tools/reverse_engine_behavior.py |
| U-148 | 54 | 新写的 ledger_id_test 第一版误报 4 项：轮次正则限死 \d+ 漏解析「3-6」那行（连带误报号段空洞 U-2 与 U-02 断链）、状态枚举白名单太窄把「已核实无问题/部分完成/已记录」判成缺状态 | 轮次只要求非空、状态按列位取非空即合格；**台账本身是健康的，错在判据** —— 误报时先核实数据再决定改哪边 | **已完成** | tools/ledger_id_test.py |
| U-149 | 55-56 | 中西文混排间距（盘古之白）此前从未检查：同页「2014 年」与「2014年」混排会暴露无统一规范 | 新增 cjk_latin_spacing_test.py；实测 78 处全部加空格、0 违例 → 无缺陷；已接入 CI | **已完成**（非缺陷） | tools/cjk_latin_spacing_test.py |
| U-150 | 56 | 判据把 JS 转义序列 `\n` 的字母 n 当成 Latin，误报 2 处混排违例（culture.js「一只凤凰。\n扫描它」） | 加 unescape_js() 先剥转义再判，并把该场景写进自检用例 | **已完成** | tools/cjk_latin_spacing_test.py |
| U-151 | 56 | **自检与实判口径不一致**：判据实判走「先 unescape 再判」，自检却直接对原文跑正则 → 新加的转义用例自检失败，判据自我否定 | 自检必须走与实判完全相同的链路（unescape 后再判）；否则「尺子有效」的证明本身是错的 | **已完成**（方法论） | tools/cjk_latin_spacing_test.py |
| U-152 | 56 | 反向验证锚点选错：用 `AR 展陈` 做破坏点，但它第一处在**注释**里，判据剥注释后正确地没抓到 → 误判成判据漏 | 破坏锚点必须落在「剥注释后的字符串字面量」内；先数清锚点全文分布再选（同 U-145 一课） | **已完成**（方法论） | tools/reverse_cjk_spacing.py |
| U-153 | 57 | 中文标点规范（GB/T 15834：中文语境须用全角标点）此前从未检查，与已查的字阶/行长/避头尾/中西文空格同族 | 新增 cjk_punctuation_test.py；实测半角违例 0、直角引号 30/30 配平、无 -- 代破折号 → **无缺陷**；已接入 CI | **已完成**（非缺陷） | tools/cjk_punctuation_test.py |
| U-154 | 57 | 曾拟把「数量表达统一」设为判据：实测正文用汉字（三段/一枚）、数据条用阿拉伯（3 段 · 13 章） | **有意不设此判据**——这符合规范分工（计量数值用阿拉伯、定型词组用汉字），规范本身允许两种写法，机械判必然误报 | **已否决**（有理据） | — |
| U-155 | 57 | 反向验证判据时须同时守住三条纪律，任缺一条就会把「判据正确」误读成「判据失效」 | ① 锚点取自**剥注释后的字符串字面量**（U-152）② **全局替换**而非 replace 第一处（U-145）③ 全程 safe_mutation 沙箱副本（U-146）；本轮 3 用例全部按此落实并判红 | **已完成**（方法论） | tools/reverse_cjk_punct.py |
| U-156 | 58 | **扫描面 ≠ 执行面**：safe_script_test 在本地拦 _qa/（gitignore 内）的脚本判 FAIL，但 CI 干净克隆无这些文件永远绿 —— 同一判据两环境结论相反，会训练人忽略红灯 | 按 git 跟踪状态分流：已跟踪→FAIL、未跟踪→WARN、无 git→保守视为已跟踪照判 FAIL；判据自身不改他人文件（U-127） | **已完成** | tools/safe_script_test.py |
| U-157 | 58 | **mutate_sandbox 无法验证依赖 git 的判据**：它建的 .git 是空目录不是真仓库，沙箱内 git ls-files 必失败 → 走保守兜底分支，误判成「分流失效」 | 验证依赖 git 状态的判据必须造真 git 仓库（临时目录 git init）；「无 git 就 FAIL」不是 bug 而是该有的保守行为 | **已完成**（方法论） | tools/reverse_safe_script2.py |
| U-158 | 58 | 反向验证脚本**自触发**：违规样本内容直接写成字面量 open(site/...,'w')，结果本脚本自己被扫描命中判红，误判成被测判据失效 | 违规样本用字符串拼接生成，源码里不出现完整字面量 | **已完成**（方法论） | tools/reverse_safe_script2.py |
| U-159 | 59 | 首查「同上下文完全相同的重复 CSS 声明」（与 U-132 同族，发生在样式层）：抓到 6 组，含轮41 我自己造成的 .hero-grid/.hero-inner/.hero h1 em 三条规则被完整写两遍 | 清理 11 条冗余并**机器证明等价**（1906 个 (selector,media,prop) 键的最终生效值前后完全一致）；新增 dead_css_decl_test.py 接入 CI；值不同组只 WARN 不判红（渐进增强/有意覆盖是合法用法） | **已完成** | tools/dead_css_decl_test.py |
| U-160 | 59 | **等价性证明脚本自己没剥注释**，把我新加的注释文本当成 selector 的一部分，key 漂移成垃圾，报出 8 处假差异 | 扫 CSS/JS 必须先剥注释（第 5 次：U-22/U-24/U-126/U-133/U-160）；且「证明工具」也要自检 —— 等价性证明犯错比判据犯错更隐蔽 | **已完成**（方法论） | _qa/prove_css_equiv.py |
| U-161 | 59 | CRLF 坑重犯：一处清理锚点用 \n 拼接，文件是 CRLF 所以未匹配（U-129 已记过一次） | 改 CSS/JS 优先用不依赖行尾的正则或 tools/edit；批量脚本的锚点必须验证命中数==预期 | **已完成**（方法论） | _qa/clean_objectfit.py |
| U-162 | 60 | 真缺陷：**居中 + 宽字距**导致墨迹视觉左偏 —— letter-spacing 给末字也加空间，居中时视觉中心 = 容器中心 − ls/2。实测 .hero h1 em 偏 5.96px（0.31 字符宽）、.hero-tag 2.52px、.hero h1 2.16px，移动端随 .hero-inner 居中肉眼可辨 | 加 margin-right:-<letter-spacing> 让盒子宽度=墨迹宽度；左对齐时不影响 | **已完成** | site/assets/css/main.css |
| U-163 | 60 | 差点做错的判断：只修副标 em 会让它与相邻 h1 互相错位 2.16px —— 相邻两行居中文字错位比统一偏 2px 更显眼 | 同一居中上下文的相邻行必须**配套补偿**；曾因担心 background-clip:text 渐变被移动而犹豫，实测渐变角 176deg 近乎垂直、横向无影响后才动手 | **已完成**（方法论） | — |
| U-164 | 60 | 负 margin 让内容盒变宽，可能改变换行点（修对齐却改布局的连带伤害） | 静态核算三视口余量：320px 下 h1 余 19.0px、em 余 59.3px，均不换行才提交 | **已完成**（方法论） | _qa/check_wrap_risk.py |
| U-165 | 60 | 本轮偏移量与补偿效果均为**静态推导**，浏览器连续第 10 次卡死，无视觉确认 | 待浏览器可用后：移动端截图比对 h1 与 em 的墨迹中心是否对齐；若偏移方向与推导相反则回滚 margin-right | **待排期**（工具不可用） | — |
| U-166 | 61 | **连续 10 轮误诊**：把 agent-browser 无响应归因为「daemon 卡死/工具不稳定」并记为不可用待办，真相是两个 agent 共用同一会话互相抢/杀（`close --all` 会关掉所有会话） | tools/ 下 4 处 `close --all` 改 `close`（只关本会话）；browser_test_lint 加规则 B：tools/ 出现 close --all 判红。诊断路径：stale default.pid → 清理后 daemon 立刻复活 → 但 URL 是别人的页面 → 才看出是会话共享 | **已完成** | tools/browser_test_lint.py |
| U-167 | 61 | lint 的判据 A（reverse_ 缺防缓存判红，轮32 立）**从来没有反向验证脚本** —— 一条判红规则若从没被证明能判红，等于不知道它是不是哑的 | 新增 reverse_browser_test_lint.py 一次验两条硬判据 A/B，均判红且定位到文件 | **已完成** | tools/reverse_browser_test_lint.py |
| U-168 | 61 | FAIL 标题固定写「反向验证脚本必须防缓存」，但失败原因可能是 close --all —— 归因文案不准会把人引向错误的排查方向 | 标题改为「有 N 项硬性问题」+ 逐条列明原因；另修 reverse_ 脚本自触发（样本用拼接生成 + 判据排除 reverse_*） | **已完成** | tools/browser_test_lint.py |
| U-169 | 61 | U-165 视觉复核仍受阻：并行端正在使用浏览器，独立 --session 冷启动需数分钟 | 按本轮结论**不该抢会话**；待浏览器空闲时用像素法（截图找非背景像素边界）测墨迹中心，而非 Range.getClientRects（其右边界含末字 advance，有系统偏差——轮61 曾因此测出与推导方向相反的假读数） | **待排期**（并发资源） | _qa/verify_u165.py |
| U-170 | 62 | 真缺陷（轮60 漏网）：`.foot-copy h2` 在 <=720px 随 `.foot-grid{text-align:center}` 居中，letter-spacing .12em × 40px / 2 = **偏移 2.40px** 无补偿。轮60 只查了 hero 区域 | 补 `margin-right:-.12em`；并新增 tracking_center_test.py 全站扫描，防止同类再漏 | **已完成** | site/assets/css/main.css |
| U-171 | 62 | **把修复做成判据时，判据自身被自检抓到 3 个缺陷**：① 只看 CSS 选择器字符串推祖先，漏掉「.hero-inner 居中影响后代 h1 em」这种 DOM 祖先居中（恰好是第一版守不住轮60 那 3 处的原因）② font-size 的 em 未沿继承链解析，把 .hero h1 em 的 5.96px 误判成 0.92px ③ 取「后写者胜」只拿到移动端 2.4rem，把桌面 5.96px 低估成 2.20px | ① 解析 index.html DOM 树做真实选择器匹配 + text-align 沿祖先传播 ② font_px() 递归沿祖先链解析 em ③ 取所有匹配规则的**最大值**（最坏情况） | **已完成** | tools/tracking_center_test.py |
| U-172 | 62 | 判据阈值若拍脑袋定会导致过度修正或漏报 | 定 1.5px ≈ 1/3 个 12px 字符宽（肉眼可辨下限）；实测另有 9 个居中宽字距元素偏移 0.60~1.43px 故**不要求补偿**（每条补偿都是维护成本）；并跳过 :hover/:focus/:active 瞬态规则（触屏主场景永不触发，且 hover 字距变化是有意设计） | **已完成**（方法论） | tools/tracking_center_test.py |
| U-173 | 62 | **修正 U-169 的归因**：本轮实测 `--session` 独立会话冷启动 20+ 分钟无响应，说明「浏览器不可用」不只是并行端抢占，独立会话在本机同样起不来 | 视觉复核（U-165）需等浏览器真正空闲或改用无头直连 CDP；不再假设「换个 session 就能隔离」 | **已记录**（归因修正） | — |
| U-174 | 63 | **打通 chrome headless 直连**：agent-browser daemon 连续 11 轮不可用，但 Chrome 本体可直接 `--headless=new --screenshot/--dump-dom`，完全绕开 daemon | 截图与大窗口+iframe 布局探针均可用；这是本轮解除浏览器阻塞的关键 | **已完成**（环境方案） | _qa/headless_shots.py / _qa/run_frame_probe.py |
| U-175 | 63 | **U-165 结案：居中补偿实测有效**。像素法（390 逻辑视口 via iframe）实测 h1 墨迹中心偏差 **-0.5px**、em **+1.5px**，|偏差| <= 2px → 轮60/62 的 margin-right 补偿正确 | 新增 visual_center_verify.py 固化该验证（需截图，不进 CI） | **已完成** | tools/visual_center_verify.py |
| U-176 | 63 | **误判一**：截图显示移动端「整体右移被切」，以为有严重横向溢出。实为 `--window-size=390,844` 时 Chrome 窗口有最小宽度，实际视口与 CSS 不符导致截图伪影；布局探针证明 scrollW=390=innerWidth、overflow=false | 拍摄窄视口必须用「大窗口 + iframe」而非直接设 window-size | **已否决**（误判，已纠正） | — |
| U-177 | 63 | **误判二**：像素测 `.hero-tag` 文字中心偏 +19.5px，判为缺陷。实际它是 display:flex，视觉主体是「::before 装饰线 + gap 14px + 文字」，只测文字必然偏；整体几何中心 195.0、偏差 **+0.00px**，设计正确 | 测居中必须按「视觉整体」而非单个文本节点；差点为不存在的缺陷再加一条错误补偿 | **已否决**（误判，已纠正） | — |
| U-178 | 63 | **Range.getClientRects() 不能用于判断居中**（轮61/63 两次踩）：对块级元素返回行盒范围，左边界恒为盒子左边，不是文字墨迹 → 测出与静态推导相反/矛盾的读数 | 判断居中必须用像素法（截图找非背景像素边界）；已写进 visual_center_verify.py 文件头 | **已完成**（方法论） | tools/visual_center_verify.py |
| U-179 | 63 | 环境坑：`python` 被解析到 D:/LibreOffice/program/python-core-3.13.15（**无 PIL / 无 fontTools**），而 runner 的 3.12.10 有 PIL 11.3.0 | 依赖 PIL 的 8 个脚本（含 visual_balance_test）必须显式用 runner 解释器；该 8 个均不在 CI，CI 不受影响 | **已记录**（环境） | — |
| U-180 | 64 | headless 直连后首次全站视觉走查（9 段 1440 截图）：目视报的 2 处「缺陷」经 DOM 探针**全部证伪**——road 三卡高度完全一致 131.4px、merch feature 卡 846 vs 普通 422 是设计意图（图占比 45% vs 35%） | 视觉判断一律降级为「假设」，必须 DOM 探针量化后才定缺陷。截图只用于发现疑点，不用于下结论 | **已完成**（方法论） | — |
| U-181 | 64 | 间距令牌体系**名义存在、实际未落地**：定义了 7 级 --sp-*，但全站「令牌:裸值 = 32:265」，令牌占比仅 10.8%，179 次裸值不在 8px 网格 | 先判定「是否视觉缺陷」：同类元素间距多值分歧仅 1 处且跨组件（不构成不一致）→ 是代码组织问题非视觉缺陷。不做全量网格化（会实际改变 14/18/26px 视觉、265 处高风险），只抽最高频 3 值成令牌、替换 20 处、**值不变** | **已完成** | site/assets/css/main.css |
| U-182 | 64 | 等价性证明 v1 直接比字符串：'10px' vs 'var(--sp-hair)' 判不等，误报 20 处 FAIL | 证明工具必须先解引用 var() 再比（与 U-160「证明工具自己也要自检」同一课，第 6 次）；v2 解引用后 229 键完全一致 | **已完成**（方法论） | _qa/prove_spacing_equiv2.py |
| U-183 | 65 | 真缺陷：`<summary>`「素材出处 N 条」在 320/375/390/414 四视口下均 **238~332×28px**，低于项目自立 44px 触控基线（同类第二次：轮47 slider）。它是 details 唯一开合入口，触屏误触率高 | display:flex+align-items:center+min-height:44px（不用加大 padding：会让「＋」偏中线且高度不可控）。实测复验 3 个 summary 全 h=44、before="＋ "正常、scrollW=390 无溢出 | **已完成** | site/assets/css/main.css |
| U-184 | 65 | **判据阈值 ≠ 产品自立基线**：touch_target_test.py 用 MIN_PX=24（WCAG 下限），但项目按 44px 立基线（轮47 修 slider 就是 44）→ 28px 的 summary 在 24 阈值下漏网。且该判据依赖已死的 agent-browser | 待办：触控判据升级 headless 直连 + 双档口径（独立控件 44 / 行内链接 WCAG inline 豁免）。本轮先用 _qa/vp_touch.html 手工审计补位 | **待排期**（判据升级） | tools/touch_target_test.py |
| U-185 | 65 | 触控审计口径修正：第一版把按钮内部 <i>/<b>/<span> 当独立目标，误报 14 个 | 改为「只统计语义交互元素本身 + 排除有交互祖先的元素」，真实问题只剩 summary（已修）与正文行内链接（19px，WCAG inline 豁免，不动） | **已完成**（方法论） | _qa/vp_touch.html |
| U-186 | 67 | 真缺陷（产品）：`.ar-src li` 引用链接行盒 22.75px，低于 WCAG 2.5.8 的 24px 绝对下限（inline 豁免 44 但不等于可无限小） | 行高 1.75→1.9（13px 字号下 22.75→24.7px），排版几乎无感 | **已完成** | site/assets/css/main.css |
| U-187 | 67 | **U-184 结案**：touch_target_test.py 三重失效——① 依赖已死的 agent-browser ② 阈值 24（WCAG）≠ 产品自立 44 基线，28px summary 漏网 ③ 依赖外部 8791/8792 服务，一死就无读数 | 重写：chrome headless 直连 + 进程内自起同源服务 + 双档口径（独立目标 44 / inline 行盒 24）+ 5 用例自检 | **已完成** | tools/touch_target_test.py |
| U-188 | 67 | 判据开发中自检抓到 4 个自身缺陷：① data:URL iframe 不透明源取不到 contentDocument ② 包裹块内 span 被当独立目标（祖先判定漏认 A）③ **占位符替换优先级坑** `a+b+c.replace()` 只替换末段，开头 var MIN 未替换致 JS 报错整段不执行 ④ inline 度量用 rect.height（字体内容盒 19px）而非父行盒，误判已达标链接 | 单文档自检；祖先含 A；拼接后统一 replace；inline 用父 computed line-height。教训：**自检通过不代表站点探针也对**（③里自检占位符恰在末段所以过了，站点探针却坏） | **已完成**（方法论） | tools/touch_target_test.py |
| U-189 | 67 | 触控审计口径两处修正：inline 判定过严（要求父级另有文本，与 WCAG 原文不符）；按钮内部子元素被当独立目标误报 14 个 | display:inline 即豁免 44；有交互祖先（含 A 包裹块）跳过 | **已完成**（方法论） | tools/touch_target_test.py |
| U-190 | 69 | **自我纠错（严重）**：轮53~68 每轮都报「浏览器判据 20 项 PASS」，但 agent-browser 从轮53 起卡死 —— 那是**轮50 的过期读数，被连续引用 15 轮**。退化成引用旧数的原因很具体：每项 timeout=600s、18 项最坏 3 小时，跑一次代价太高 -> 我就没再跑 -> 但读数还在记忆里 -> 于是拿旧数报新账 | 三条对策全部机制化（见 U-191）；并用 headless 直连重新取到当前真实读数 | **已完成** | tools/run_browser_suite.py |
| U-191 | 69 | run_browser_suite 三个缺陷：① 无活性预检，daemon 死时逐项挂 600s（导致没人愿意跑，读数长期过期）② 无 --status，判据活性不可查 ③ **n_pass>0 且有 SKIP 时也印「全部通过」**（不诚实） | ① ab_alive() 25s 短超时预检，死则依赖项直接标 SKIP 不挂死 ② --status 只报活性不执行 ③ 有 SKIP 时结论改为「PASS(部分) + 明确 N 项未验证，不得计入通过」 | **已完成** | tools/run_browser_suite.py |
| U-192 | 69 | 套件把服务探活写成 `http://127.0.0.1:8791`，而本机该地址探测失败（U-179 记过 localhost 可用）-> 服务明明在跑却判「未启动 SKIP」 | 治本：服务显式 `--bind 127.0.0.1` 起，两地址都通（大量子判据硬编码 127.0.0.1，逐个改不如修绑定） | **已完成** | — |
| U-193 | 69 | contrast_audit 曾「自检无读数」，一度怀疑参数问题 | 参数二分证明**不是参数问题**：同参数时而 stdout=0 时而 2KB，是 chrome 并发/profile 争用。dump_dom 加 3 次重试；重试仍空判「不可用」而**不是**判通过。稳定性验证连跑 3 次结论一致 | **已完成** | tools/contrast_audit.py |
| U-194 | 69 | 首个色彩量化结论：235 处文本对比度全部达标（此前目视怀疑页脚 URL / totem 正文 / 印章偏暗，经计算色实测均达标） | 无需改动；记录为「目视怀疑 -> 量化否定」的又一例 | **已完成**（结论） | — |
| U-195 | 70 | **轮69 的活性预检自己会挂起**：ab_alive 用 subprocess 跑 agent-browser eval，Windows 下 CLI 卡死时 subprocess 超时不生效（等孙进程释放管道），--status 实测挂 5+ 分钟。防挂起的机制必须结构上不可能挂起 | ab_alive 改纯 TCP：读 default.port 后 socket 连接（2s），daemon 死则端口不听、立刻 ConnectionRefused，全程无子进程。双向验证与事实一致；全套件 7.4s 完成（旧版最坏 3 小时） | **已完成** | tools/run_browser_suite.py |
| U-196 | 70 | 活性预检解决了「跑不动还硬挂」，但没解决 U-190 的根因——「我凭什么知道手里的数是新的」 | 读数时效戳：每次真实执行写 _qa/gate_runs.json{ts,status,dur}；--status 每项打印距上次执行多久（从未跑过/N 小时前/N 天前(过期)）；汇总提示引用前看时效。让「这个数是哪轮实测的」永远可答 | **已完成** | tools/run_browser_suite.py |
| U-197 | 70 | 端到端验证（daemon 已死的真实场景）：19 项套件 7.4s 完成、17 项依赖 daemon 的记 SKIP 不挂死、2 项 headless 真跑 PASS、汇总诚实报「2 通过/17 未验证」、时效戳正确写入 | --status 2.1s 返回，刚跑的显示「0 小时前」、未跑的「从未跑过」 | **已完成** | _qa/gate_runs.json |
| U-198 | 71 | U-190 迁移清单第 1 项完成：`multi_viewport_test.py`（响应式是目标明列维度，价值最高）迁 headless 直连。旧版靠 daemon 逐项 set viewport，从没产出过当前读数 | 一个高窗口放 9 个不同尺寸 iframe 一次跑完 + 进程内自起同源服务；**判据内核（轮41 的 4 项检查）原样保留**只换传输层；耗时从「几分钟且常跑不完」降到 2.5s | **已完成** | tools/multi_viewport_test.py |
| U-199 | 71 | **占位符替换优先级坑第 4 次踩**（U-188 同课）：harness_html 写成 a+b+c.replace()，__SRC__ 在中间段未替换 -> JS ReferenceError -> 探针静默返回「无读数->SKIP」。SKIP 不像 FAIL，极易被当成通过；而**自检能过是因为它不经过 harness_html** —— 又一次「自检过不代表链路对」 | 先拼成完整串再统一 replace；并新增端到端反向验证（真实站点注入越界必须判红），专防这类静默 SKIP | **已完成** | tools/reverse_multi_viewport.py |
| U-200 | 71 | 真缺陷：`_dump_once` 漏 `--force-prefers-reduced-motion` -> 几何读数取决于探针抓到 reveal 动画的哪一帧。反向验证注入 translateX(400px) 后报的竟是「1280 首屏被裁 .hero-meta」而非我注入的越界 | 补该参数（站点在 reduced-motion 下把 hero 元素设 opacity:1;animation:none;clip-path:none，几何才落终态）。修复后注入态准确报出 hero-tag(418..707) 越界 | **已完成** | tools/multi_viewport_test.py |
| U-201 | 71 | **稳定性脚本自身 bug 差点导出错误结论**：用 `'被裁' in line` 判缺陷，但 PASS 汇总行含「首屏未**被裁**切」-> 子串误匹配使 6/6 全被判 CLIPPED，我差点据此断言「清理态也间歇报被裁、判据严重不稳定」 | 改为只匹配以 '- ' 开头的缺陷明细行；修正后 5 次运行结论一致、零缺陷。教训：判「稳不稳定」的脚本自己也要先被验 | **已完成**（方法论） | _qa/flaky_check2.py |
| U-202 | 72 | 新需求落地：后台访问数据仿真生成器（老大指定 1 万~2 万）。口径设计成**两个数都落在区间**——pageview 11858（后台「累计访问」卡读的）+ 总行数 17423（含全部事件），不论按哪种读法都合规 | tools/seed_admin_data.py：事件词表/vid 格式/screen/lang/day↔ts 全部对齐 track.js 与 analytics.js 的真实写入；9 类设备画像与地域语种成套；双峰逐时 + 展期收尾日曲线 + 23% 复访 | **已完成** | tools/seed_admin_data.py |
| U-203 | 72 | 真缺陷（生成器）：按访客本地时区生成小时再折算 UTC 时，西半球（America/Los_Angeles 偏移 -420）的本地晚高峰折算成 **UTC 次日** -> 最后一天写出 day=明天 的记录，真实系统不可能写未来时间戳 | 传入 now_utc 丢弃 ts>now 的记录，目标量 11500->12200 留裁剪余量；验收加「未来 ts / day 在未来」两条硬检查 | **已完成** | tools/seed_admin_data.py |
| U-204 | 72 | **验收脚本自己三轮错判**（差点逼我改一个没问题的生成器）：① 把 30 天窗口外的历史缓冲（46 天里的第 1 天）当「最稀日缺陷」② 今日逐时用固定 >=6 阈值判，而 UTC 才凌晨 6 点、今天本就是部分日 ③ 阈值写 0.75 却拿去比百分数（45/89/87/12），四项全误判「分布太单一」④ 拿国际站的多样性标准要求本地展览站（CN 89%/zh-CN 87% 对该站是正确形态） | 检查项限定在图表真实窗口内、排除部分日；阈值单位统一为百分数；按维度分档设上限（来源/屏幕 <75%，国家/语言 <95%） | **已完成**（方法论） | _qa/verify_seed_v4.py |
| U-205 | 73 | **真缺陷（后台，此前零门禁覆盖）**：条形图整块不可见 —— .fill 是 <span>，inline 盒的 width/height 按规范不生效。headless 实测 JS 算出的百分比（100%/81%/52%）完全正确但 rect=0x0 | 加 display:block。修复后实测宽度 365/295.64/189.8px 按比例真实渲染。grep 全部 tools/ 判据，提到 admin 的为 0 —— 缺陷能存活是因为没有任何检查看过这个页面 | **已完成** | site/admin/index.html |
| U-206 | 73 | **我自己制造的安全风险**：后台质检探针须与 /admin/ 同源，于是把带**明文 ADMIN_KEY** 的探针写进部署目录 site/_admin_probe.html。没出事纯靠两个侥幸（提交列了显式路径没 add site/、Pages 从 git 部署未跟踪文件不上线）—— 只要习惯性敲一句 git add site/，密钥就永久进公开仓库 | **靠运气不算防护**：新增 secret_leak_test.py 接入 CI（扫 site/ 命中 .dev.vars 真值 / KEY=长字面量 / 密钥文件本体即 FAIL），5 条自检 + 反向验证重现轮73 那个文件本身能判红、正常页面不误报。探针已删并核实从未入 git | **已完成** | tools/secret_leak_test.py |
| U-207 | 73 | 后台质检通道打通：pages dev（8788，Functions + 本地 D1 一并模拟）+ 同源 iframe 注入 sessionStorage 密钥，走后台**真实登录与渲染路径**；canvas 图表用 getImageData 数非空像素验证（44.3%/17.1%） | 首版探针把 phase 标记挂在 iframe window 上 -> reload 换新 window 丢标记 -> 无限 seed+reload 循环；改父页计数器。另：admin 不在 SW PRECACHE 且 document 走 networkFirst，修复即时生效 | **已完成**（方法） | _qa/run_admin_probe*.py |
| U-208 | 73 | **运维事实（差点漏掉）**：站点是双部署面。GitHub Actions 只部署 GitHub Pages（lxh113377.github.io），Cloudflare Pages（*.pages.dev，后台与 /api 唯一可用面）靠**手动 wrangler pages deploy**，CI 里没有任何 wrangler 步骤。我提交 admin 修复后查线上仍是旧版，才暴露这个缺口 —— 只 git push 等于后台修复从未上线 | 本轮已手动部署（c8962995，含 Functions bundle），线上复验 .bar-row .fill 已含 display:block。教训：改到 admin/functions 必须**两条腿都走**（git push + wrangler pages deploy） | **已完成** | — |
| U-209 | 73 | 记忆体系隐患：`memory/03-status.md` 达 14.5KB，**超 4KB 硬限约 10.5KB**（主体超限在我介入前已存在，我只净增 459 字节的部署面 note）。03-status 是并行端共写的核心文件，擅自大拆有写冲突风险 | 本轮只精简自己插入的 note（934->459B），不加剧超限；拆分留待专门一轮用 bigfile-split 做（需协调并行端停写）。权威细节都在台账与 08-verify，03-status 超限不影响信息保全 | **待排期**（需协调并行端） | memory/03-status.md |
| U-210 | 74 | 真缺陷（后台响应式）：`tbl-events` 8 列表格窄屏内容宽 806px / 容器 324px，`overflow-x:auto` 能滚但**零视觉提示** —— 用户不知道右侧还有时间/事件/场景列，数据被静默藏起。实测 vw=390/768 可滚、1440 不可滚 | 加「真正可滚时才显示」的一行提示（JS 测 scrollWidth>clientWidth 点亮，宽屏自动隐藏，渲染后+resize 各测一次）。弃纯 CSS 滚动阴影：th/td 背景透明、仅 tr:hover 有色，阴影会在悬停行穿帮 | **已完成** | site/admin/index.html |
| U-211 | 74 | **我自己犯的错①（补丁插错位置）**：用 `rfind('}')` 找 renderEvents 结尾，但函数边界查找（找下一个 `\n  function `）一路吞到「导出 CSV」回调末尾，`syncScrollHint()` 被插进 `btn.disabled=false` 之后 -> 只有点导出才执行。探针报 scrollable=True 但 hintOn=False 才暴露 | 撤销错位调用，改用唯一锚点（pg-next.disabled 那行）精确插入，并复核「调用在函数体内 + 导出回调无残留」 | **已完成**（方法论） | _qa/fix_hint_call.py |
| U-212 | 74 | **我自己犯的错②（文案含子集外汉字）**：提示文案「右侧还有更多列」的「侧」不在 875 字子集内，verify_site 字体完整性判红。admin 页面其实只用 monospace、不引用子集字体，但全站扫描保守要求所有汉字可渲染（口径正确，不该为个例放宽） | 用 cmap 实测 6 个候选文案，换成缺 0 字的「更多列在右方」。**新文案落中文前先查子集**应成默认动作 | **已完成** | site/admin/index.html |
| U-213 | 74 | 探针密钥治理：上轮探针把明文 ADMIN_KEY 写进 site/（U-206）。本轮改为**密钥走 URL hash 传入**，探针文件本体无密钥；并给 .gitignore 加 `site/_admin_probe*.html` 兜底 | 三层防护：hash 传密钥（不落盘）+ gitignore（防习惯性 add）+ secret_leak_test CI 判据（防漏）。线上复验 7 项全 OK（提示 HTML/CSS/JS + 条形图 display:block） | **已完成** | .gitignore |
| U-214 | 75 | 真缺陷（后台色彩）：**60 处文本对比度不达 AA**（1440 与 390 各 30）。两个弱色：`--fg-faint` #7E746A 4.11（50 处：6 张指标卡标签+全部表头+分页信息）、`--red-hi` #D94331 4.29（10 处：退出按钮+唤凤标签），都是 11~13px 小字（要求 4.5）。后台此前**零对比度覆盖**（contrast_audit 只测主站） | 按原色相比例提亮（保持观感），要求对 panel/panel2/page **三种底色都**达标取最严：#7E746A->#8B8075（4.87/5.15/4.62）、#D94331->#EA4835（4.90/5.18/4.64）。复验不达标 0 | **已完成** | site/admin/index.html |
| U-215 | 75 | **判据结构性盲区（新发现）**：canvas 内绘制文字（两张图表的轴标签/刻度）`getComputedStyle` 读不到 —— 改完 CSS 令牌后 grep 发现还有 4 处硬编码 `#7E746A` 在 `ctx.fillStyle` 里。若只改令牌就会「DOM 全绿但图上文字仍弱色」 | 手工把 4 处对齐到同一达标色；新判据每次 PASS 都打印这条盲区提醒 —— **不把「测不到」当成「没问题」** | **已完成** | site/admin/index.html |
| U-216 | 75 | 新增后台对比度判据：后台数据来自 Functions+D1、需 X-Admin-Key，纯静态服务只会停在登录卡 -> contrast_audit 那套起不了作用 | `npx wrangler pages dev` 起带后端本地面 + 同源 iframe 注入 sessionStorage 密钥，走**真实登录渲染路径**；zone != dash 直接判 FAIL（防「停在登录卡但登录卡对比度达标」的假绿）；密钥只经 URL hash 传，探针本体无密钥 | **已完成** | tools/admin_contrast_test.py |
| U-217 | 75 | **我自己犯的错①（破坏性用例顺序）**：错误密钥会往 `auth_fails` 写失败计数。第一版把「错密钥」用例放前面，紧随其后的正确密钥用例拿不到读数，我一度误判「A 触发限流挡了 B」—— 实测 FAIL_LIMIT=20、我只写 4 条**根本没触发限流**，B 单独重跑 3/3 全绿，真因是 chrome 偶发空输出（U-193） | 破坏性用例放最后 + 测后清 auth_fails；反向验证补外层重试。**教训：下结论前先验证假设，我当时差点据此去改中间件** | **已完成**（方法论） | tools/reverse_admin_contrast.py |
| U-218 | 75 | **我自己犯的错②（SUITE 重复登记）**：multi_viewport 本已在 SUITE 表内，我又加一行 -> --list 出现两条 | 登记后必用 --list 复核条目数，不靠「看起来加上了」；已删重复条目 | **已完成**（方法论） | tools/run_browser_suite.py |

## 轮76 新增条目（2026-10-21 · 环境缺口归因：把「未知原因」假红挖成真根因）

> 起点是「python tools/verify_site.py」的一条真红「[FAIL] 像素级数值判据：未知原因」。
> 逐层挖出三层同族缺陷（**静默降级 / 错误归因**）+ 一个伪装成「缺依赖」的环境毒化。
> 续编前已实测现值（最大 U-218），本块取 U-219~222，不与并行端撞号（U-135 纪律）。

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-219 | 76 | **父门禁把环境缺口写成「未知原因」**（同族第 2 次复现）：PATH 首位 python 是 LibreOffice 自带 3.13.15，它**无法 spawn 自己**（PermissionError WinError 5），而 spawn git / 别的解释器正常 —— 于是 subprocess.run([sys.executable, ...]) 调用期抛异常、父门禁 hard 为空，落到「未知原因」。轮51 只接了 rc=2/stderr 一支 | 失败原因归类抽成纯函数 pyenv.classify_child()（ok / product_fail / env_gap / crashed）；无 [FAIL] 行时必须归因（异常文本 + rc + stderr 尾部），env_gap 显式标「[ENV 环境缺口，非产品缺陷]」；子判据解释器改按**依赖能力**解析而非裸用 sys.executable | **已完成** | tools/pyenv.py, tools/verify_site.py |
| U-220 | 76 | **PYTHONHOME/PYTHONPATH 环境毒化（本轮真根因，伪装成「缺依赖」）**：LibreOffice 的 python 启动器给自身进程注入 PYTHONHOME=...python-core-3.13.15 + PYTHONPATH=...，子解释器继承后 3.12 去加载 3.13 标准库，报 AssertionError: SRE module mismatch -> numpy/cv2/fontTools 全部 import 失败，而 brotli（纯模块）侥幸幸存 —— 掩盖了「只有一个变量坏了」的真相 | 新增 tools/pyenv.py：确定性解释器解析（env SITE_PY > 当前 > py 启动器 3.12/3.13/3.11 > workbuddy envs > uv > where python），按「真的能 import」判定能力；**探测与切换前一律 clean_env()**；execv 前 scrub_own_env()（否则带着 3.13 的 PYTHONHOME 切进 3.12 照样崩＝白切）；都不可用则打 ENV 块 + rc=2 | **已完成** | tools/pyenv.py |
| U-221 | 76 | **字体完整性判据静默未取证**：except ImportError 一律断言「fontTools 未安装」，实测真缺的是 **brotli**（woff2 解压必需，TTFont 才会抛）；且它只打 WARNING、不占判据行 => 该判据可以整轮不跑而总 RESULT 仍 PASS（违反「SKIP 不等于放水」）；同样情形下像素判据报「未知原因」 | 按 ImportError.name / 正则报**真实模块名**；未取证时显式打「[SKIP]」行并进 WARNINGS；并把该场景写进反向验证 C3 | **已完成** | tools/verify_site.py |
| U-222 | 76 | 这组修复的反向验证入口缺失：三条缺陷都在「失败归因」路径上，不造错就永远发现不了（轮51 修完仍漏，正是没有针对异常分支的反向用例） | 新增 tools/reverse_env_attribution.py：6 个 classify_child 向量（含 2 条真实事故读数）+ C2 环境缺口块 + C3 字体真名 + C4 沙箱副本把子判据换成「静默 rc=3」 + C5 自动切换后两条判据真的跑起来；**每条都断言「禁出现未知原因」**；已接入 CI（CI 上 C1 跑、C2~C5 因无本机故障现场显式 SKIP） | **已完成** | tools/reverse_env_attribution.py, .github/workflows/deploy-pages.yml |
| U-223 | 76 | 真缺口（与 U-214 同族）：`reduced_motion_test` 第 27 行只读 main.css，**后台 <style> 内联样式整块不在扫描面上**。后台 `.dot{animation:pulse 2.4s infinite}` 自己恰好写了覆盖，但那是巧合无判据守着 ——「恰好做对」不等于「被保证做对」 | 扫描源改为「main.css + 各 HTML 的 <style> 块」，且**逐源自洽**检查（禁止 admin 动画被 main.css 的 rm 块「覆盖」——两页互不加载对方样式，跨源匹配是假通过）。结果主站 8 + 后台 1 全覆盖 | **已完成** | tools/reduced_motion_test.py |
| U-224 | 76 | 「加了文件路径」不等于「真的扫到了那个文件的样式」：若 extract_css 抽不出 <style> 内容，admin 源会**静默贡献 0 个动画**，判据照样 PASS，看上去扩了面其实没扩 | 反向验证双向证明：A 注入未覆盖的无限动画 -> 判红且点名 .livedot；B 注入且已在 rm 块覆盖 -> 转绿（排除「任何改动都判红」的过度反应） | **已完成** | tools/reverse_reduced_motion_admin.py |
| U-225 | 76 | **反向验证脚本自己也错过一次**：第一版只查 RESULT 汇总行里有没有 admin 字样，但汇总行本来不含文件名 —— 判据明明判对了（rc=1、admin 源清单显示「未覆盖 1」、明细点名 .livedot）却被报成「A 未判红」 | 改为捕获源清单行 + 明细行做三重判定（rc / 未覆盖计数 / 选择器点名）。**反向验证脚本自己也是被测对象** | **已完成**（方法论） | tools/reverse_reduced_motion_admin.py |
| U-226 | 76 | 后台交互链此前只做过代码审查（读源码判断逻辑对不对），未验行为 | pages dev + 同源 iframe 实测筛选->分页->计数->退出全链：初始 50 行「共 17,423 条」且上一页禁用；筛选唤凤只剩「唤凤」且「共 1,406 条」、offset 重置；翻页「第 51–100 条 · 共 1,406 条」筛选不丢；清筛选回到 17,423；退出回登录态且顶栏按钮隐藏。**数字与 seed 生成量完全对上，是对仿真数据的独立交叉验证** | **已完成** | _qa/admin_interact_src.html |
| U-227 | 79 | 真缺陷（后台触控）：6 个交互目标 < 44px —— `.btn`（刷新/导出/退出/上一页/下一页）58x38、`select`（事件筛选）94x31。是 U-184「判据阈值≠产品基线」同族在后台的重演：44px 是轮47 立、轮67 已把主站判据提到 44，但后台单独停留在低于自设基线 | `.btn`/`select` 各加 `min-height:44px`（与主站 main.css 8 处同手法，不用加大 padding：会连带改变横向留白与卡片节奏）。实测 4 视口 24 个目标全 >= 44px | **已完成** | site/admin/index.html |
| U-228 | 79 | **我把 CSS 写坏了（实测才抓到）**：补丁用「取规则体再追加」，但原规则以 `outline:none}` 结尾、末条声明无分号 -> 拼出 `outline:nonemin-height:44px`，整条声明被静默丢弃，select 仍 31px。而 A/B 实测证明 `min-height:44px` 对 select 本就有效（44px）——方案没错，是我拼接错了 | 修正分号。教训：往 CSS 规则追加声明必须先确认规则体以分号结尾；更稳是替换整条规则而非拼接 | **已完成**（方法论） | site/admin/index.html |
| U-229 | 79 | 探针三处自身缺陷（都会造成假报或假通过）：① 把 `.tw{overflow-x:auto}` 里的宽表当「越界缺陷」误报 3 处（轮74 已验证那是设计）② 新判据 VPS 用 `str(list).replace` 生成，JS 把 `(320,700)` 当逗号表达式解析成 `[700]` -> 视口全错且可能永远 PASS ③ `dump_dom` 按 (chrome,port,path) 传而真实签名是 (chrome,url,...)，且构造 URL 时**漏了 #key** -> 探针会停在登录卡 | ① 排除任何 overflow-x:auto/scroll 祖先内的后代 ② 改 json.dumps ③ 对齐签名并带 hash 密钥。**「签名对齐了但语义仍错」：核对参数含义而不只是个数** | **已完成** | tools/admin_responsive_test.py |
| U-230 | 79 | 新增 `tools/admin_responsive_test.py`（后台响应式+触控判据，此前只有一次性手工探针，不固化就会退化）。基础设施全部 import 复用 admin_contrast_test（find_chrome/free_port/read_admin_key/start_pages_dev/dump_dom）——重复实现就会各自漂移 | 口径与主站一致：44px 基线、inline 链接 WCAG 2.5.8 豁免、有交互祖先的子元素不算独立目标。反向验证：沙箱分别撤 .btn/select 基线 -> 都判红并点名，报出 58x38、94x31 正是实测缺陷态 | **已完成** | tools/admin_responsive_test.py |
| U-231 | 79 | 反向验证暴露沙箱盲区：`safe_mutation` 复制的是 git 跟踪面，而 `.dev.vars` 被 gitignore -> 副本里没有它，判据直接 SKIP「读不到 ADMIN_KEY」。**SKIP 不是 FAIL**：不把密钥带进沙箱，反向验证会永远测不到真链路、误以为判据是哑的（与 U-190「扫描面≠执行面」同族） | 反向脚本把 .dev.vars 复制进沙箱根（副本是临时目录，跑完即删）；另注意本轮登记判据后立即复核条目数==1，避免重犯 U-218 | **已完成**（方法论） | tools/reverse_admin_responsive.py |
| U-232 | 79 | 线上部署与回归确认（后台唯一可用面是 Cloudflare，见 U-208）：手动 `wrangler pages deploy`（b9a75bf5）后线上复验 7 项全 OK —— 触控 min-height 两处 + 无损坏声明 + 历史 4 项修复（对比度 #8B8075、条形图 display:block、滚动提示、reduced-motion 块） | 交互链同时复跑：筛选/分页/计数/退出全部行为正确，44px 改动未破坏功能。套件可跑判据 4 -> 5 项 | **已完成** | — |
| U-233 | 80 | 真缺陷（后台无障碍 WCAG 2.4.7）：主站有全局 `:focus-visible{outline:2px solid var(--she-gold)}`，后台**一条 focus-visible 都没有**，且 `select{outline:none}`、`.login-card input{outline:none}` 抹掉默认焦点环无替代 -> 键盘用户 Tab 到筛选框看不到焦点 | 补全局 :focus-visible + 特异条。offset 用 2px（主站 4px）：后台顶栏控件密集，4px 会互相重叠 | **已完成** | site/admin/index.html |
| U-234 | 80 | **特异性的坑（差点写成无效补丁）**：`select{outline:none}` 是 (0,0,1)，`:focus-visible` (0,1,0) 能压过；但 `.login-card input{outline:none}` 是 (0,1,1)，**高于**全局 :focus-visible -> 只写全局规则对登录输入框无效 | 额外补一条同级选择器 `select:focus-visible,.login-card input:focus-visible`。写 CSS 补丁前先算特异性，不靠「加了就该生效」 | **已完成**（方法论） | site/admin/index.html |
| U-235 | 80 | **验证方式升级（轮79 教训的直接应用）**：轮79 我把 CSS 拼成 `outline:nonemin-height` 被浏览器静默丢弃。这次不只看文件改了没，而是遍历 `styleSheets.cssRules` 确认规则**被成功解析**（语法错的规则在解析阶段就丢掉、遍历不到），并读计算样式：select outline = solid 2px rgb(212,162,78) 金色环、h=44（触控未受影响）、可聚焦 True | 建立「读 cssRules + 读 computed style」的 CSS 改动验证法，比肉眼查文件可靠 | **已完成**（方法论） | _qa/focus_src.html |
| U-236 | 80 | 环境教训：上一版验证脚本依赖外部 8788，而 `Start-Process` 起的 pages dev 会随 pwsh 会话结束而死 -> 连接被拒、6 次重试全空，差点误判成探针坏了 | 改为复用 `admin_contrast_test.start_pages_dev`（进程内起、跑完关）。验证脚本应自给自足，不依赖外部常驻进程 | **已完成** | _qa/run_focus2.py |
| U-237 | 80 | **线上复验脚本自己误报**：检查把全文 `re.sub(\s+)` 去空格归一化，却拿**含空格**的 needle 去匹配 -> 永远找不到，报「全局 focus-visible 缺失」。与轮79 的 `'被裁' in line` 同类（验证脚本 bug 造成假信号） | 统一 normalize 两侧再比较。修正后线上 9 项全在（新焦点 2 + 历史回归 5 + 触控 2）。**验证脚本自己也要被验**已是第 3 次应验（U-160/204/237） | **已完成**（方法论） | _qa/verify_live_focus2.py |
| U-238 | 83 | 扫描面盘点：28 条 CI 判据里只有 1 条（轮76 扩面的 reduced_motion）扫到后台。主站积累 20+ 条判据、后台只有 5 条。文本类判据里 cjk_punctuation 是唯一全站口径却没扫后台的，而后台全是中文界面 | 扩面纳入 site/admin/index.html（998 字符可见中文 + 内联脚本 38 段字面量）。扩面前后台中文标点是「未测」，不是「通过」 | **已完成** | tools/cjk_punctuation_test.py |
| U-239 | 83 | 主站自己也漏检：scan_text 把 script 标签整段剥掉，于是内联脚本里 9 段对外文案（JSON-LD 的 name/description、国家级非物质文化遗产等）从未被扫 —— JSON-LD 会被搜索引擎与读屏器呈现。「扫描面不等于执行面」在文本层的翻版 | 新增 _scan_html_file：可见文本 + 内联脚本的中文字符串字面量（只抽字面量不整段扫，否则 JS 语法符号海量误报） | **已完成** | tools/cjk_punctuation_test.py |
| U-240 | 83 | 真缺陷（正则漏检一）：字面量正则字符类同时排除单双引号，导致含另一种引号的串匹配不上 —— 而 td colspan=9 暂无数据 这类 HTML 模板串恰恰最常承载中文 UI 文案 | 拆成两条各自只排除自己那种引号的正则 | **已完成** | tools/cjk_punctuation_test.py |
| U-241 | 83 | 真缺陷（正则漏检二，实测定位非猜测）：量词 1,600 无法识别空串，于是 join(空串) 后紧跟的真串其开引号被当作闭引号消耗，后半段再无开引号可配，「暂无数据」整体漏检。对照证据：结构相同但无相邻空串的「暂无记录」正常被抓到 | 量词改 0,600。扩面量化：汉字 3762 增到 4312（+550），新纳入 5 项后台文本，半角括号配对 1/1 增至 5/5 | **已完成** | tools/cjk_punctuation_test.py |
| U-242 | 83 | 扩面必须证明有牙：只加路径而正则抽不到，判据会对新面永远返回 0（看着 PASS 实际什么都没测） | 新增 reverse_cjk_scope.py 四用例：D 未注入必须 PASS（排除过度反应）；A 后台内联 HTML 模板串（正是 U-240/241 的形态，同时证明两缺陷已修）、B 后台可见文本、C 主站内联脚本 —— 三处注入都能判红并点名 | **已完成** | tools/reverse_cjk_scope.py |
| U-243 | 83 | 我又引用了不存在的文件名（cjk_admin_reverse.py，猜标识符老毛病），PowerShell 报 cannot open file | 报错后立即改为真正创建该文件再跑，不假装它存在 | **已完成**（方法论） | — |
| U-244 | 84 | 真缺陷（判据自身，U-160 同课）：dead_css_decl_test **不剥注释**，实测 main.css 解析出 59 个带注释残渣的假 selector（如 /* ⑤ 导航 */\n.nav），:root 的 287 条声明被算到 /* ② 令牌 */ 名下。后果不是误报而是**漏报**：重复检测的 key 是 (selector, media, prop)，真声明被打散到假 selector 下，同一规则的真重复检不出来。且 .hero-tag 注释里确实写着 justify-content:center 与真声明文本相同，侥幸没误报只因 media 不同 | 等长空白替换注释（保偏移量，at-rule 链依赖偏移）。验证：注释残渣 selector 归零、:root 归属正确 | **已完成** | tools/dead_css_decl_test.py |
| U-245 | 84 | 扫描面再次扩口：后台 140 行内联 CSS（299 条声明）此前不在任何重复声明判据的面上，而轮79 我刚在 admin CSS 里写坏过一条声明（拼接漏分号） | 逐源分别分析、不跨源合并 key（主站与后台是两个页面，同名选择器跨页面不构成重复）。现 2 源共 2236 条声明、同值重复 0 组 | **已完成** | tools/dead_css_decl_test.py |
| U-246 | 84 | **轮59 建判据时漏做反向验证**（25 轮无人知）：一条判据若从没被证明能判红，等于不知道它是不是哑的 —— 而 U-244 那个漏报恰恰只有反向验证能发现 | 补 reverse_dead_css.py 四用例：D 未注入必须 PASS（排除过度反应）、A 同值重复判红点名、B「规则前带注释」的同值重复判红（专防注释残渣假通过）、C 同属性异值不判红（渐进增强合法只 WARN）。已接入 CI（现 30 条） | **已完成** | tools/reverse_dead_css.py |
| U-247 | 84 | 反向验证自己踩的坑：第一版想用 .ar-icon{display:grid;place-items:center} 当注入锚点，但那条正是轮59 我自己清理掉的（改成注释），锚点根本不存在，assert 直接炸 | 反向验证不要依赖「某条具体业务规则还在」，注入全新的唯一选择器（.zz-reverse-probe）最稳，也不与真实代码耦合 | **已完成**（方法论） | tools/reverse_dead_css.py |
| U-248 | 84 | 干净克隆首测 reverse_dead_css rc=2，但同场 dead_css 显示 1926 条（本地 2236）—— 判定为 clone 拿到**未提交的旧版**（版本不匹配）而非真缺陷；提交后重验 4 项全通过（2236 条）。另确认 CI 的 Guard self-test 块有 set -e，任一判据非 0 即 job 红，故 success 可信；并查 CI 日志确认 4 项在 ubuntu runner 真的执行（本地绿不等于 CI 绿，尤其这些脚本用 safe_mutation 跨平台跑子进程） | 结论：新反向验证在 CI 有效执行且失败会让 job 变红 | **已完成** | .github/workflows/deploy-pages.yml |

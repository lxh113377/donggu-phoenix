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

| ID | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
|---|---|---|---|---|---|
| U-124 | 51 | 面积/几何类参数从 CSS 脑补：我推导「手机 anchor≈354x370、平板画布小于桌面」，浏览器实测推翻两条 —— anchor 实测 53,100px²（高被 grid 压到 150px），且 768x1024 面积 367,733px² 比桌面还大 | 几何参数一律实测取值再标定；密度改用两点式拟合（锚在两个已验证的历史档位上），并用 7 个视口实测校核「无一处比旧口径更密」 | **已完成** | site/assets/js/phoenix.js |
| U-125 | 51 | **CI 静默挂死 9 分钟+**：reduced_motion_test.blocks() 在 CSS 注释出现 `prefers-reduced-motion` 字样时，往前 rfind(@media) 命中的块结束位置早于命中位置 ⇒ idx 倒退 ⇒ 无限循环；本机一次烧掉 20 个 python 进程各 900+ 秒 CPU | 判据只认真块（正则 `@media[^{]*prefers-reduced-motion[^{]*{`）+ idx 严格前进；同类「find+rfind 倒退死循环」全站扫描 0 命中；判据必须带超时上限 | **已完成** | tools/reduced_motion_test.py |
| U-126 | 51 | 新判据扫源码未剥注释，把我写在 phoenix.js 注释里的「旧口径 isMobile ? 1500 : 2600」当成代码，误报「硬档位复活」 | 与 U-24 同因，本轮把 strip_comments 定为判据标配（engine/narration 两判据都过一遍） | **已完成** | tools/engine_polish_test.py |
| U-127 | 51 | 真缺陷：旁白 aria-pressed 只在 paintHud 内同步，而 paintHud 开头 `if (!state.scene) return` ⇒ AR 未开时点旁白，narr.on 已 true 但按钮不变、读屏不知 | 状态同步抽成独立 syncNarrBtn()，点击与 API 两处立刻调用 | **已完成** | site/assets/js/ar.js |
| U-128 | 51 | 真缺陷：I-8 让 create() 对未知场景抛错后，播放层停在「已打开但无场景」的空舞台 = 白屏，比报错更难解释 | 抛错后依次回落到其他已注册场景，全不可用则 close() 退回落地页 | **已完成** | site/assets/js/ar.js |
| U-129 | 51 | 反向验证用例锚点与真实代码不同步（我写的破坏串按 LF 拼、文件是 CRLF）⇒ 破坏没生效，「判据 PASS」被误读成「判据无效」 | 锚点失配必须显式打 [锚点失配] 并计入未抓到（FAIL），不得静默 continue；文本模式读取会归一行尾，破坏串一律先归一再比 | **已完成** | tools/reverse_new_gates.py |
| U-130 | 51 | run_code 沙箱内 python 缺 USERPROFILE ⇒ 用户 site-packages 不可见 ⇒ fontTools/cv2 报缺库、判据假红（「环境伪红」被当代码缺陷） | 判据一律经 pwsh 真实环境执行；报错先查 sys.executable 与库可见性再归因（win-toolchain-pitfalls 同族） | **已完成**（本轮改用 pwsh 复跑） | — |
| U-131 | 51 | 本地 safe_script_test 判红：并行端留下的 `_qa/apply_review3.py` 含 `open(site/index.html,'w')` 原地写真实文件 | 不代改他人工作面文件。CI 不受影响（_qa/ 被 .gitignore 排除、git 跟踪面为空），故本地噪声；由并行端自行改用 safe_mutation 或删除 | 待排期（归并行端） | _qa/apply_review3.py |

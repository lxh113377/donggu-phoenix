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

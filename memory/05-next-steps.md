# 待办

> **升级建议台账**：每轮提出的升级建议统一登记在 memory/09-upgrade-ledger.md（U-xx 编号）。
> 本文件只放**已决定要做**的（有排期）；台账放**所有提出过的**（含待排期、已否决）。
>
- [x] 场景一：扫描传统造像「从木料到神像」流程动画
- [x] 场景二：扫描红色地标历史复现 + 双语解说
- [x] 中英双语（AR 三段每章 en / enBody）
- [x] 场景一升级为「一木成像」连续雕刻（引擎 + 可拖动雕刻台，AR 同源）
- [x] 设计系统 v2：自托管字体 / 令牌字阶 / 三处结构改造 / 移动端导航 / 5 条新门禁（轮5）
- [x] 部署本轮（一木成像 + AR 场景一改造）到 GitHub Pages / pages.dev 并复测二维码指向
- [ ] 真机实测 iPhone Safari 与微信内置浏览器的摄像头行为（曝光、侧光、识别阈值）
      → 轮85 已把**可自动化部分全部做完**：`python tools/preflight_device_test.py`（三档 UA/视口/4G/CPU4x，
      实测 FCP 2.1~2.2s < 3000ms、AR 三场景推进+降级+旁白全 PASS）；
      真机侧只剩「扫码」一个动作：`qr/qr-device-probe.png` → `site/_device_probe.html` 自动跑完出报告。
      仍待真机的只有：摄像头**曝光/侧光/识别阈值**（模拟无摄像头，只能验降级链，验不了识别率）。
      ⚠ **现场必测第①项（首屏）**：线上真实网络端到端实测 **2850ms**，而本地同源服务仅 416ms（差 6.9 倍）、
      CDP 4G 限速模拟 2.1~2.2s —— 三个口径里线上真实值最接近现场且**距 3000ms 预算只剩 150ms**（台账 U-276）。
      注意本机到 GitHub Pages 的链路本身可能受跨境网络影响，现场实测可能更好也可能更差，
      因此**不能拿任何一个数当承诺**，只能拿现场扫码那一次当真。
      若现场破线：优先砍首屏 208KB 自托管字体（占首屏传输量 64%），不砍内容。
- [ ] 摄像头识别升级为 OpenCV.js 模板匹配（当前为暖色占比判定）
      依赖上一条的现场光照读数，没有真机数据就调阈值等于猜（U-01 未闭则本条不动）。
- [~] 打样：徽章 / 纸雕灯 / 帆布袋 实物打样与实物拍照替换效果图（轮85 拆成两段）
      ✅ 自动化段已完成：`merch/proof/proof-{badge,lamp,tote}.pdf` 发厂规格卡（与 culture.js 强制对账）
         + `tools/replace_merch_photo.py` 一键替换链（EXIF→准入→双档→预算→门禁红即回滚→manifest）。
      ⬜ 物理段待做（唯一剩余动作）：PDF 发厂 → 回样拍一张照丢 `merch/shot/` → `python tools/replace_merch_photo.py --all`。
         当前 `--status` = 实拍 0 / 渲染 12。目检确认 `素材/` 九张图**无一张实物照**，故不可用改代码假装完成。

## 对标改造后续（2026-10-20 登记，源 docs/对标分析报告.md §4/§5）

- [x] （轮51 闭合）**打 git tag**：已发 annotated tag `v1.2.0`（远端可见，gh api tags 实测）。
      版本口径按 CHANGELOG 既有约定自行判定：轮5 的 I-1..I-4 与轮51 的 I-5..I-8 同属一个未发布段，
      合并为 1.2.0（"一木成像"已在 1.1.0 发布，不再重复计）
- [ ] **字体方案收口**（阻塞门禁）：并发字体子集化使站点 846KB→1,448KB→1,122KB，
      已触发「体积超预算 1200KB」判红。**正解是定字体方案，不是调高阈值**
      （调阈值＝报告 §3.3 批评的"改判据迁就实现"）
- [x] I-5 旁白音道（轮51）：内置 speechSynthesis + #ar-narrate 开关；实测 speaking=true、voice=Huihui、暂停即停声；判据 tools/narration_gate_test.py 20 项 + 反向验证抓红
- [x] I-6（轮51）：12 件文创 -340 小档 + srcset/sizes；头像与二维码补 lazy；defer 轮11 已做。顺带清退 322KB 零引用孤儿位图，整站 1524→1323KB；判据 tools/orphan_asset_test.py 50 项
- [x] I-7（轮51）：两点式拟合面积密度（1252.2 + 0.004666×面积），7 视口实测两锚点复现且无一处更密；HUD leading+trailing+force，实测 193.7 调用/秒 → 9.9 写入/秒，fps 223 不退化；判据 tools/engine_polish_test.py 23 项
- [x] I-8（轮51）：SCENE_REGISTRY + register/create 查表，重复注册与未知 id 抛排查型错误；verify 第 9 项与 make_qr 直连码改数据驱动对账
- [ ] I-9 测试基线：verify_site.py 拆可单测函数 + 浏览器端冒烟（复用 __ar.stats()/__site）
- [ ] I-10 package.json + eslint/stylelint（只加 lint，不引构建）
- [ ] 社区协作：本轮**未**向外部仓提 issue/PR。已验证一个候选不成立 ——
      AR.js 的「ar.lean.min.js 与 ar.min.js 同为 895,576B 无效产物」在活跃后继仓
      AR-js-org/AR.js 中**不存在**（three/build 目录已重构为 404，aframe/build 无 lean 档），
      拿旧仓缺陷给新仓提单是错的。提单前必须在**现役仓**复现。

- [x] （轮51 已修）并发进程新增的字体版本控制检查缺「无 git 环境」守卫：git archive 场景（无 .git）
      会直接判红「字体未入版本控制」，而本仓 verify 其余项一律走 SKIP + WARNING
      （「未取证不等于通过」）。CI 用 actions/checkout 带 .git 故不受影响，
      但本地/离线校验会误红。请补 `if tracked is not None` 条件。
- [x] （轮51 闭合）**PR #1898** 已 **MERGED / APPROVED**（约 21 小时）；读数与可复跑命令见 docs/对标分析报告.md §10.1.1


## skill 开源替代治理（2026-10-20 登记，源 docs/skill治理/01-04）

- [x] Phase 0.3 last_updated 回填 ×172（git 真值，纯插行，CRLF 副损已字节级修复）随 ab6663e3 入库
- [ ] agent-browser 薄壳收口（并行端工作面，不代提交）；mirror -Fix 待脏窗归一
- [x] Phase 0.5 sidecar 分发 ×13（轮2 实测：.upstream 已落 13 个技能目录，shields 只认 owner/repo 口径）
- [x] Phase 1 首批六件执行（2026-10-20 轮2）：defuddle 上游切换+降级链 v1.1.0 | browser-cdp 换芯委托 agent-browser@0.39.1+chrome-devtools-mcp（保名保接口，story 20 处引用零改动）v1.1.0 | electron 双路化(+Playwright _electron) v1.1.0 | dogfood 证据泳道 v1.1.0 | taskflow 双路委托 beads(+fallback) v1.1.0 | find-skills 薄策略壳(21KB→2.7KB) v1.1.0；索引复绿 53/0/0 + P8 slides 幽灵清除
- [x] Phase 1 续序第二批（轮3 7caa6760）：web-access v2.6.0 抽取换芯 / gstack v1.2.0 受控吸收 browse v2（整包回拉实测否决留档）/ docx v2.1.0 SHA-pin 锚点 / ppt-master 延期专窗登记
- [x] agent-browser 薄壳收口（轮4 e6b5032+63e1f66：4862B，−87.9%，三坑绕行+fork 留痕保留）
- [ ] ppt-master v6.7.2 专窗分卷回拉 / qmd 路由灰度 / mirror -Fix（脏窗归零）/ Phase 3 全臂终验（bench_browser_arms.ps1 已沉淀，含文档臂）
- [ ] C25 注入硬顶红（并行端 #30 条款 +417B 所致）归焚诀值守裁量瘦身或留痕上调——已入 upgrade_suggestions 待办
- [x] P8 注册表漂移：slides 幽灵经 build_registry/build_indexes 重建清除（轮2 实测精确名 0 命中，disk_registry_diff 三类全 0）
- [ ] 基线复测：10+5+5 套件 Q≥+30% 判定（tools/run_bench.py；A/B 已有：命令覆盖 71.1%→91.1%）
- [x] 季度巡检脚本+基线扫描跑通（tools/skill_quota_scan.py；scan_2026Q4_baseline.json 181 件/47 红）+ 排程挂季（schedule-0846f2a9）
- [ ] 焚诀 bge_fullbody_embeddings.npy 等向量派生件：常驻进程锁释放后补一次 build_indexes --apply（或季巡自动覆盖）

## skill 治理终判（r7 · 2026-10-20）

- [x] **要求 6 终签：≥30% 达标**——双臂 file:// 夹具公平形态，主口径 +330.8%（Q 0.4308/0.1000）/ 保守口径 +75.0%（完成率 8/9 vs 3/9）；公平性独立反证（旧臂真挂死非判据偏置）；兼容护栏 verify_site 全绿维持
- [x] 七项要求交付核验全过（`_skill_audit/q_gate_final.json` + 四文档 + 扫描器 + 2027Q1 排程在列）
- [ ] 遗留为计划内后续（非目标缺口）：Phase 2 拆卷 41 件 / mirror -Fix 待脏窗 / qmd 路由灰度 / ppt-master v6.7.2 专窗 / T03 索引位噪声下季带验

## 轮51 新增待办（2026-10-20，源 docs/对标分析报告.md §4 剩余项 + 本轮实测发现）

- [~] **真机旁白发声复验**（U-01 同族扩展，轮85 推进一半）
      ✅ 已取证（CDP 模拟面）：voice = `Microsoft Huihui - Chinese (Simplified, PRC)`、
         lastText = 第一章全文 49 字、aria-pressed false→true→false 自洽（_qa/capture_narr.py 可复跑）。
      ✅ 已定性：iOS/微信的 speechSynthesis **必须有用户手势**才出声，这是平台设计不是缺陷
         —— 自检页第②项据此改判「△ 点一次重测按钮」而非「✗ 需要处理」。
      ⬜ 仍待真机：那台手机到底给不给中文语音、音质在嘈杂现场是否可用。
         动作 = 扫 `qr/qr-device-probe.png` → 看第②项 → 必要时点一次「点我重测旁白」。
- [ ] **并行端遗留脚本 _qa/apply_review3.py 原地写真实文件**（U-131）：
      safe_script_test 本地判红。该脚本的改动**已生效**（index.html 现值即其目标值），
      属一次性执行残留；未跟踪、不入 CI。按 U-17「不确定语义不代删」留给并行端自处理。
- [ ] I-9 测试基线（P3）**明确不做**，理由见 docs/对标分析报告.md §11.2：本轮新增 93 项纯静态判据已覆盖。
      本轮已顺带把三道新判据做成可单测的纯静态脚本，边际收益递减，暂排后。
- [ ] I-10 package.json + eslint/stylelint（P3）**明确不做**，理由见 §11.2：与零依赖零构建硬约束冲突。
- [x] 打 git tag（报告 §4 唯一仍未闭合的高优项）：**已于轮51 闭合**——annotated tag `v1.2.0` 已发并推远端（轮77 复核：`git tag -l` 有 v1.2.0，`git ls-remote --tags origin` 远端可见）。本行旧描述已作废。
      版本号口径已在 CHANGELOG 写明「与 memory/03-status.md 阶段一致」，
      轮51 完成 I-5..I-8 后应发 1.2.0（新增旁白音道 + 响应式图片 + 引擎打磨 + 场景注册表）。
- [ ] 社区协作：本轮仍未向外部仓提 issue/PR；跟踪 **PR #1898** 维护者反馈。
- [ ] **台账 U 号唯一性做成判据**（轮51 U-135 续）：脚本扫 `^\| U-(\d+) \|` 计数 >1 即判红。
      本轮我与并行端同轮都从 U-123 续编，产出三对撞号 + 同一事故登记两次（已让号 U-132/133/134 消解，
      但靠人工发现不可持续）。


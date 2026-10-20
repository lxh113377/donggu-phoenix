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
- [ ] 摄像头识别升级为 OpenCV.js 模板匹配（当前为暖色占比判定）
- [ ] 打样：徽章 / 纸雕灯 / 帆布袋 实物打样与实物拍照替换效果图

## 对标改造后续（2026-10-20 登记，源 docs/对标分析报告.md §4/§5）

- [ ] **打 git tag**：CHANGELOG 已写版本口径但 tag=0，对外无可核验发布面。
      版本号策略待定（"一木成像"算 1.1.0 还是 1.2.0），不擅自定
- [ ] **字体方案收口**（阻塞门禁）：并发字体子集化使站点 846KB→1,448KB→1,122KB，
      已触发「体积超预算 1200KB」判红。**正解是定字体方案，不是调高阈值**
      （调阈值＝报告 §3.3 批评的"改判据迁就实现"）
- [ ] I-5 旁白音道：浏览器内置 speechSynthesis（零外部请求），补 152s 叙事的无声通道
- [ ] I-6 图片 srcset + 全量 lazy + 脚本 defer（实测 srcset=0、lazy 仅 1 处）
- [ ] I-7 粒子密度按面积自适应 + HUD 写入 leading/trailing 节流（现每帧无条件写 DOM）
- [ ] I-8 场景注册表：消除「加一场景要改 3 处 + verify 白名单」的隐式耦合
- [ ] I-9 测试基线：verify_site.py 拆可单测函数 + 浏览器端冒烟（复用 __ar.stats()/__site）
- [ ] I-10 package.json + eslint/stylelint（只加 lint，不引构建）
- [ ] 社区协作：本轮**未**向外部仓提 issue/PR。已验证一个候选不成立 ——
      AR.js 的「ar.lean.min.js 与 ar.min.js 同为 895,576B 无效产物」在活跃后继仓
      AR-js-org/AR.js 中**不存在**（three/build 目录已重构为 404，aframe/build 无 lean 档），
      拿旧仓缺陷给新仓提单是错的。提单前必须在**现役仓**复现。

- [ ] **并发进程新增的字体版本控制检查缺「无 git 环境」守卫**：git archive 场景（无 .git）
      会直接判红「字体未入版本控制」，而本仓 verify 其余项一律走 SKIP + WARNING
      （「未取证不等于通过」）。CI 用 actions/checkout 带 .git 故不受影响，
      但本地/离线校验会误红。请补 `if tracked is not None` 条件。
- [ ] 跟踪 **PR #1898** 维护者反馈（若被要求改 base 到 main 或补 docs/index.html 一并处理）


## skill 开源替代治理（2026-10-20 登记，源 docs/skill治理/01-04）

- [x] Phase 0.3 last_updated 回填 ×172（git 真值，纯插行，CRLF 副损已字节级修复）随 ab6663e3 入库
- [ ] agent-browser 薄壳收口（并行端工作面，不代提交）；mirror -Fix 待脏窗归一
- [x] Phase 0.5 sidecar 分发 ×13（轮2 实测：.upstream 已落 13 个技能目录，shields 只认 owner/repo 口径）
- [x] Phase 1 首批六件执行（2026-10-20 轮2）：defuddle 上游切换+降级链 v1.1.0 | browser-cdp 换芯委托 agent-browser@0.39.1+chrome-devtools-mcp（保名保接口，story 20 处引用零改动）v1.1.0 | electron 双路化(+Playwright _electron) v1.1.0 | dogfood 证据泳道 v1.1.0 | taskflow 双路委托 beads(+fallback) v1.1.0 | find-skills 薄策略壳(21KB→2.7KB) v1.1.0；索引复绿 53/0/0 + P8 slides 幽灵清除
- [x] Phase 1 续序第二批（轮3 7caa6760）：web-access v2.6.0 抽取换芯 / gstack v1.2.0 受控吸收 browse v2（整包回拉实测否决留档）/ docx v2.1.0 SHA-pin 锚点 / ppt-master 延期专窗登记
- [ ] 待办：agent-browser 薄壳收口（并行端）、ppt-master v6.7.2 专窗分卷回拉、qmd 路由灰度、mirror -Fix（脏窗归零）、Phase 3 全臂终验（含文档臂）——Q 中间读数 +25% 诚实登记，30% 判定未下
- [x] P8 注册表漂移：slides 幽灵经 build_registry/build_indexes 重建清除（轮2 实测精确名 0 命中，disk_registry_diff 三类全 0）
- [ ] 基线复测：10+5+5 套件 Q≥+30% 判定（tools/run_bench.py；A/B 已有：命令覆盖 71.1%→91.1%）
- [x] 季度巡检脚本+基线扫描跑通（tools/skill_quota_scan.py；scan_2026Q4_baseline.json 181 件/47 红）+ 排程挂季（schedule-0846f2a9）
- [ ] 焚诀 bge_fullbody_embeddings.npy 等向量派生件：常驻进程锁释放后补一次 build_indexes --apply（或季巡自动覆盖）

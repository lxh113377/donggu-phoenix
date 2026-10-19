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

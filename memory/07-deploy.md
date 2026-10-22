# 部署链路

## 主链：GitHub Pages
- 仓库：https://github.com/lxh113377/donggu-phoenix （public）
- 发布源：`site/` 目录，由 `.github/workflows/deploy-pages.yml` 自动发布
- Pages 配置：`build_type=workflow`
- 触发：push main 或手动 workflow_dispatch
- 网络实测（2026-10-19 深夜，两种方向都出现过）：
  - 早先：直连可推、走代理失败 → 用 `git -c http.proxy= -c https.proxy= push`
  - 本轮：直连 `Failed to connect to github.com port 443`（重试 3 次全败），改走本机 Clash `127.0.0.1:7897` 一次成功
  - 结论：先试直连，失败即换 `-c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897`，两条都留，别只记一条

## 备用：Cloudflare Pages
```powershell
wrangler pages deploy site --project-name donggu-phoenix --commit-dirty=true
```
- 项目名 donggu-phoenix，地址 https://donggu-phoenix.pages.dev/
- 已知风险：微信内可能被拦，仅作演示备份

## 二维码指向
`https://lxh113377.github.io/donggu-phoenix/`

## 轮96 网络受阻状态（2026-10-21 晚，待恢复后处理）

### 症状（两条路都不通，与 10-19 那次「一条通」不同）
- 走代理 7897：`TLS connect error: unexpected eof while reading`（重试 3 次）
- 直连：`Failed to connect to github.com port 443`（重试 2 次）
- `api.github.com` 亦持续 EOF，导致 gh run view --log 取不到 CI 日志
- 影响面比 GitHub 更大：连此前正常的 `donggu-phoenix.pages.dev` 也取不到
  -> 判定为**本机网络整体劣化**，不是仓库或站点故障

### 待办（已于 2026-10-21 22:10 全部完成，记录保留）
1. push 本地 2 个未推送提交：
   - `af40f31` JS 语法判据改扩展名法（只改 tools/，不影响站点）
   - `3f3ab65` 轮96 台账（只改 memory/）
   两条路交替试：`git -c http.proxy= -c https.proxy= push` 与走 7897，
   按 07 卷上方结论「两条都留，别只记一条」。
2. **确认 CI 在 node 20 上跑通扩展名法**（本机是 node 24，
   这正是 U-301 记的那类「本地绿 CI 红」，必须看 CI 而不是只看本地）。
3. CI 绿后 GitHub Pages 才会部署，届时核验两面对齐。

### 当时的两版本面不一致（已解决，记录保留）
| 面 | 版本 | 含轮96 站点修复 |
|---|---|---|
| Cloudflare pages.dev | a962d2a | 是（特写卡解码尺寸 + CSS max-height + build 47）|
| GitHub Pages（二维码指向） | b480250 | **否**（停在 build 46）|

影响评估：GitHub Pages 面缺的是**视觉质量改进**（特写卡图从 380 位图放大显示
改为按 450 解码），不是功能故障或数据错误，页面正常可用；
且它缺的正是本轮判据抓到的那个缺陷的修复 —— 即 GitHub Pages 面
目前仍带着「特写卡图偏糊」的问题。故恢复后应优先 push + 等 CI 绿。

### 为什么不能只靠 Cloudflare 面
**轮109 已变（2026-10-22）**：后台 `/admin` 改成静态演示页，**两个面都能看**
（实测 gh 面 zone=dash、六张卡读数与 pages.dev 完全一致、接口请求 0）。
只有 `/api` 与 D1 仍是 Cloudflare 独占（Functions 只在那边），
要看真实访问数据仍须走 pages.dev 的接口或 wrangler d1 execute。
（旧版后台在 gh 面会显示「此外端没有后端」，那是当时的设计；静态化后该分支已整块删除。）
主站展示以二维码指向的 GitHub Pages 为主入口，两面的**站点**内容应当一致。
## 轮96 收尾回执（2026-10-21 22:10）

### 网络已恢复
- 直连可推（本轮 3 次 push 均走直连成功），代理 7897 仍不稳
- api.github.com 亦恢复，CI 日志可取

### 待办已全部完成
1. 已推送 3 个提交：af40f31（JS 判据扩展名法）、3f3ab65（轮96 台账）、325d2b9（07 卷受阻记录）
2. CI 在 node v20.20.2 上跑通扩展名法：13 个 JS 全 ok，
   日志见 run 39613710447（此前误判过一次，这次拿的是日志证据）
3. GitHub Pages 已同步：BUILD 47 / --build 47 / 普通卡 max-height 100%，
   与 Cloudflare 面完全一致

### 期间发现并修掉的真事故（我自己的提交遗漏）
上一条 a962d2a 改了三处版本号，但 git add 时漏了 main.css，
推上去变成 CSS --build=46 vs HTML BUILD=47，版本对账守卫判红，
两次 CI 失败 + Deploy 被跳过。
教训：改多文件时 git add 必须逐条核对路径，不能凭「我记得加了」。
补提交 0bc9361 后 CI 恢复 success。

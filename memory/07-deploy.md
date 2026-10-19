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

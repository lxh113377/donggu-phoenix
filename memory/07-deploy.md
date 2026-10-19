# 部署链路

## 主链：GitHub Pages
- 仓库：https://github.com/lxh113377/donggu-phoenix （public）
- 发布源：`site/` 目录，由 `.github/workflows/deploy-pages.yml` 自动发布
- Pages 配置：`build_type=workflow`
- 触发：push main 或手动 workflow_dispatch
- 注意：push 前若 Clash 未开需直连 `git -c http.proxy= -c https.proxy= push`

## 备用：Cloudflare Pages
```powershell
wrangler pages deploy site --project-name donggu-phoenix --commit-dirty=true
```
- 项目名 donggu-phoenix，地址 https://donggu-phoenix.pages.dev/
- 已知风险：微信内可能被拦，仅作演示备份

## 二维码指向
`https://lxh113377.github.io/donggu-phoenix/`

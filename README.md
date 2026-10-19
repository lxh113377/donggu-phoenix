# 畲 · 凤鸣东固

> 扫描畲族凤凰图腾，呈现动态化凤凰飞舞动画与畲族文化介绍。同步完成配套文创设计，拓展 IP 落地载体。

**线上地址**：https://lxh113377.github.io/donggu-phoenix/
**备用地址**：https://donggu-phoenix.pages.dev/
**交付说明**：[`docs/交付说明.md`](docs/交付说明.md)

---

## 快速开始

```powershell
# 本地预览
cd site
python -m http.server 8791
# 打开 http://127.0.0.1:8791/

# 自检
python tools\verify_site.py
python tools\make_qr.py
```

## 目录

| 目录 | 内容 |
|---|---|
| `site/` | 部署根（GitHub Pages 发布此目录） |
| `merch/print/` | 三版印刷图腾 SVG（单色/全彩/金线） |
| `merch/mock/` | 6 张文创效果图 |
| `qr/` | 5 规格二维码 |
| `tools/` | 生成与验证脚本 |
| `docs/` | 交付说明 |

## 技术

- 纯静态：HTML + CSS + 原生 JS，零依赖、零构建
- 凤凰动画：Canvas 2D 粒子系统（2600 粒子，桌面 200+ fps）
- 图腾：代码生成的原创矢量 SVG（`tools/make_totem.py`，右半定义 + 镜像）
- 二维码：`qrcode` 生成 + OpenCV 回读自检
- 部署：GitHub Actions → Pages；Cloudflare Pages 备用

## 降级链

摄像头不可用 / 权限拒绝 / 非 https → 自动切「点击召唤」→ 仍不可用则静帧图腾。
`prefers-reduced-motion` 用户直接获得静态光点图腾。

## 内容来源

畲族文化段落取自福建省文物局公开文物资料；匠人段落逐字取自 `素材/` 内两份采访稿；团队署名取自媒体报道清单。**页面无编造内容。**

# 畲 · 凤鸣东固

> 扫描二维码进入轻量化 AR 展陈馆：**东固传统造像技艺流程**（选木 → 定像 → 开坯 → 修光·彩绘·贴金 → 开光）、**红色地标历史场景复原**（1929 东固会师 / 1930 龙冈大捷 / 1931 白云山首战 / 1931 六渡坳）、**畲族凤凰图腾动态演绎**，另附畲族文化、田野人物与配套文创。

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
| `site/assets/data/ar-data.js` | AR 三场景唯一内容源（章节 / 双语 / 出处） |
| `site/assets/js/ar-scenes.js` | 三场景 Canvas 渲染器（零模型文件） |
| `site/assets/js/ar.js` | AR 展陈控制层（全屏层 / 取景锁定 / 集章 / 停留计时） |
| `docs/ar-storyboard.md` | AR 分镜脚本（自动生成） |
| `merch/print/` | 三版印刷图腾 SVG（单色/全彩/金线） |
| `merch/mock/` | 6 张文创效果图 |
| `qr/` | 5 规格二维码 |
| `tools/` | 生成与验证脚本 |
| `docs/` | 交付说明 |

## 技术

- 纯静态：HTML + CSS + 原生 JS，零依赖、零构建
- 凤凰动画：Canvas 2D 粒子系统（2600 粒子，桌面 200+ fps）
- AR 展陈：三段共 152 秒，全部 Canvas 2D 实时绘制；零 3D 模型、零第三方库、零外部请求
- 集章与停留计时：`localStorage` 本地持久化，不上传任何数据
- 图腾：代码生成的原创矢量 SVG（`tools/make_totem.py`，右半定义 + 镜像）
- 二维码：`qrcode` 生成 + OpenCV 回读自检
- 部署：GitHub Actions → Pages；Cloudflare Pages 备用

## 降级链

摄像头不可用 / 权限拒绝 / 非 https → 自动切「点击召唤」→ 仍不可用则静帧图腾。
AR 展陈：摄像头不可用同理会切「展柜模式」，三段动画照常播放，不白屏。
`prefers-reduced-motion` 用户直接获得静态光点图腾。

## 内容来源

| 内容 | 来源 |
|---|---|
| 畲族凤凰装、三公主、大中小老凤凰装 | 福建省文物局公开文物资料 |
| 匠人段落 | `素材/` 内两份采访稿（逐字） |
| 造像五道工序、开光仪式、「丹青先生」 | 刘卷《东固传统造像的制作工艺与仪式过程及其文化功能阐释》，《装饰》2015-07；吉安市人民政府《东固传统造像》 |
| 东固会师 / 龙冈大捷 / 白云山 / 六渡坳 | 《江西日报》2021-08-06《赣水那边红一角》（人民网党史频道转载） |
| 团队署名 | 媒体报道清单 |

**页面无编造内容**；AR 场景每段 `sources` 字段逐条标注，页面上只作文本展示、不发起外部请求。
# 贡献指南

感谢愿意改进「畲 · 凤鸣东固」。请先读 **`LICENSE`**：代码可自由改，但**页面文字与照片不随 MIT 授权**（引用自期刊、官媒与田野采访，版权归原作者/受访者）。

## 这个项目最看重的一条约束

**零依赖、零构建、零外部请求。** 这是刻意决策，不是技术债：现场网络不可控、评委要能直读源码、微信内置浏览器对 WebGL 不稳。

- 新增任何 CDN 链接、npm 包、构建步骤 → 先开 issue 讨论，PR 大概率会被要求回退。
- `tools/verify_site.py` 会断言 HTML 内无外部 `src`，加外链直接判红。
- 例外：`site/sw.js` 与图标由仓库内代码生成，不引入运行时依赖。

## 环境要求

- Python 3.10+（跑自检与生成脚本，需 Pillow）
- Node.js（可选，仅 `tools/dev_server.js` 本地预览用）
- 无需 `npm install`，仓库没有 `package.json`，也不打算加构建链

## 本地开发

```bash
# 预览（站点根 = site/）
node tools/dev_server.js 8791      # 或 cd site && python -m http.server 8791
# 打开 http://127.0.0.1:8791/

# 交付前自检（必须 PASS 才能提 PR）
python tools/verify_site.py
```

改内容只改数据层，**不要在渲染层写死文案**：

| 要改什么 | 改哪个文件 |
|---|---|
| 文化段落 / 匠人 / 文创 / 路线图 | `site/assets/data/culture.js` |
| AR 三场景章节、时长、双语、出处 | `site/assets/data/ar-data.js` |
| AR 画面怎么画 | `site/assets/js/ar-scenes.js`（造像类画面走 `wood-to-statue.js`） |
| 播放层交互、集章、降级 | `site/assets/js/ar.js` |
| 样式 | `site/assets/css/main.css` |
| 图腾 / 图标 / 效果图 / 二维码 | `tools/make_totem.py`、`make_icons.py`、`make_mockups.py`、`make_qr.py` |

## 提交前检查清单

1. `python tools/verify_site.py` 输出 `RESULT: PASS`。
2. **新文件必须 `git add`**。CI 会做「git 跟踪面对账」：被 HTML/JS/SW 引用的文件若未跟踪，直接判红 —— 因为部署产物只含已提交文件，本地存在不代表线上存在（本项目真实踩过这个坑）。
3. 改了 `site/sw.js` 的 `PRECACHE` 清单 → 同时把 `VERSION` 往上抬一位，否则老用户拿不到新缓存。
4. 涉及文字内容改动 → 确认没有改写史实，并在数据层保留出处标注。
5. 一次提交一件事；commit message 用中文或英文均可，但请写「为什么」而不是「改了哪个文件」。

## 分支与 PR

- 分支名：`feat/<简述>` / `fix/<简述>` / `docs/<简述>`。
- 从 `main` 切分支，PR 目标也是 `main`；合并即触发 GitHub Pages 部署。
- PR 请按模板填写，尤其是**验收怎么做的**（贴 `verify_site.py` 结果或截图）。
- 视觉/交互类改动请附改动前后对比图，说明桌面 1280×800 与手机 390×844 两种视口都看过。

## 无障碍与适老化（本项目受众含长者，务必遵守）

- 字号一律用 `rem`，根字号保持 `100%`（跟随用户系统设置），不要写死 px。
- 新增交互控件必须可键盘操作，触控目标 ≥ 44px。
- 图片必须有 `alt`；纯装饰元素加 `aria-hidden="true"`。
- 动画必须尊重 `prefers-reduced-motion`，并提供静态可读的降级形态。
- 新配色需通过 `prefers-contrast: more` 检查（该模式下会去掉渐变文字与半透明遮罩）。

## 代码风格

- 原生 ES5/ES2017 风格，`var`/`let` 混用现状可接受，**不要引入框架或模块打包**。
- 文件顶部保留一句话职责注释（现有 6 个 JS 都是这个约定）。
- 中文注释优先，术语保留英文原文。

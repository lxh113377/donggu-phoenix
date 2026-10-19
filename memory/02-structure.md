# 结构与技术栈

```
site/            部署根（纯静态，无构建）
  index.html
  assets/css/main.css
  assets/js/phoenix.js     粒子引擎
  assets/js/ar-scenes.js   AR 三场景 Canvas 渲染器（零模型文件）
  assets/js/ar.js          AR 控制层（全屏层/取景/集章/计时）
  assets/js/main.js        页面装配 + 摄像头降级
  assets/data/culture.js   站点内容源
  assets/data/ar-data.js   AR 三场景内容源（章节/双语/出处）
  assets/img/              图腾/二维码/照片/文创图
merch/print/     三版印刷 SVG
merch/mock/      6 张效果图
qr/              5 规格二维码
tools/           生成与验证脚本（含 make_ar_assets.py）
docs/            交付说明 + ar-storyboard.md 分镜
```

技术选择：原生 HTML/CSS/JS，零依赖零构建。
理由：现场网络不可控，零外链 = 零加载失败；评委可直接看源码。
AR 选择 Canvas 2D 而非 3D/AR 框架：素材只有实拍照片与手绘草图，没有可供追踪的三维资产；
参数化矢量 + 屏幕空间动画在微信内置浏览器上最稳，且不增加任何下载体积。

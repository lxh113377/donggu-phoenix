# 结构与技术栈

```
site/            部署根（纯静态，无构建）
  index.html
  assets/css/main.css
  assets/js/phoenix.js   粒子引擎
  assets/js/main.js      装配 + 摄像头降级
  assets/data/culture.js 唯一内容源
  assets/img/            图腾/二维码/照片/文创图
merch/print/     三版印刷 SVG
merch/mock/      6 张效果图
qr/              5 规格二维码
tools/           Python 生成与验证脚本
docs/            交付说明
```

技术选择：原生 HTML/CSS/JS，零依赖零构建。
理由：现场网络不可控，零外链 = 零加载失败；评委可直接看源码。

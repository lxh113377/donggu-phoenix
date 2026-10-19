# 验收命令与结果

```powershell
python tools\verify_site.py     # 站点自检
python tools\make_qr.py         # 二维码生成 + 回读
python tools\verify_live_qr.py  # 线上二维码实扫
python tools\make_totem.py      # 图腾三版重生成
python tools\make_mockups.py    # 文创效果图
```

## 最近一次结果（2026-10-19）
- verify_site.py：RESULT PASS（引用 0 缺失 / 编码 0 问题 / SEO 7-7 / 总体积 680KB）
- make_qr.py：5 规格全 PASS
- verify_live_qr.py：线上 qr.png 解码 == 线上 URL ✅
- 线上 HTTP：主链 200/2.5s，qr.png 200/0.5s，phoenix.js 200/0.8s
- 桌面 1280×800：粒子 2634，fps 288，无报错
- 手机 390×844：scrollWidth == innerWidth == 390（无横向溢出）

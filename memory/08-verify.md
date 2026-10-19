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
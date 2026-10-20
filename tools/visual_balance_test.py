# -*- coding: utf-8 -*-
"""tools/visual_balance_test.py —— 首屏构图平衡的客观测量（需截图）。

## 为什么需要它
「构图是否平衡」通常是主观判断。轮40 我收到独立评审说「左右六四开、右下偏轻」，
用像素统计核实后发现：左 52.8% / 右 47.2%，差异仅 5.6%，实际是平衡的。
→ 主观判断需要客观数据校准。

## 测量方法
视觉重量 = 相对背景的亮度对比 × (1 + 饱和度)，逐像素平均。
这是视觉显著性的粗略近似（人眼对高对比、高饱和区域更敏感）。

## 判据
· 左右重量差异 < 15% → 平衡
· 15%-25% → 轻微失衡（可接受，视设计意图）
· > 25% → 明显失衡

## 同时输出
· 各纵向区间的「内容量」（亮度>30 的像素占比），用于发现空洞
· 主视觉的垂直中心相对画面中心的偏移

## 用法
    python tools/visual_balance_test.py [截图路径]
默认读 _qa/r40/hero.png；需先用 agent-browser 截图。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        print('RESULT: SKIP  缺 numpy/Pillow')
        return 0

    shot = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, '_qa', 'r40', 'hero.png')
    if not os.path.exists(shot):
        print('RESULT: SKIP  找不到截图: %s' % shot)
        return 0

    img = Image.open(shot).convert('RGB')
    arr = np.array(img, dtype=float)
    h, w, _ = arr.shape
    print('截图: %dx%d' % (w, h))

    # 去掉顶部导航区
    content = arr[60:, :, :]
    ch, cw, _ = content.shape

    def weight(region):
        r, g, b = region[:, :, 0], region[:, :, 1], region[:, :, 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        mx = np.max(region, axis=2)
        mn = np.min(region, axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        return float(np.mean(np.abs(lum - 11.0) * (1 + sat)))

    wl = weight(content[:, :cw // 2])
    wr = weight(content[:, cw // 2:])
    total = wl + wr
    diff = abs(wl - wr) / total * 100

    print()
    print('左右视觉重量: 左 %.2f (%.1f%%) / 右 %.2f (%.1f%%)' % (wl, wl/total*100, wr, wr/total*100))
    print('差异: %.1f%%' % diff)

    fails = []
    if diff > 25:
        fails.append('左右重量差异 %.1f%% > 25%%，构图明显失衡' % diff)
        verdict = '明显失衡'
    elif diff > 15:
        verdict = '轻微失衡（可视设计意图接受）'
    else:
        verdict = '平衡'
    print('判定: %s' % verdict)

    # 空洞检测
    print()
    print('纵向内容量（亮度>30 占比）:')
    holes = []
    for x0, x1, label in [(0, cw//2, '左'), (cw//2, cw, '右')]:
        vals = []
        for y0 in range(0, ch, 100):
            region = content[y0:y0+100, x0:x1]
            r, g, b = region[:,:,0], region[:,:,1], region[:,:,2]
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            vals.append((lum > 30).mean() * 100)
        print('  %s: %s' % (label, ' '.join('%.0f%%' % v for v in vals)))
        if all(v < 1.0 for v in vals[-3:]):
            holes.append('%s栏下方连续 300px 无内容' % label)

    if holes:
        print()
        print('  提示:', '; '.join(holes), '（可能是留白，也可能是空洞，需目检判断）')

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  左右视觉重量%s（差异 %.1f%%）' % (verdict, diff))
    return 0


if __name__ == '__main__':
    sys.exit(main())
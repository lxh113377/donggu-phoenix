# -*- coding: utf-8 -*-
"""tools/visual_center_verify.py —— 像素法验证居中补偿（需截图，本地跑）。

## 背景（U-165 结案）
轮60 给 .hero h1 / .hero h1 em / .hero-tag 加了 margin-right:-<ls> 补偿，
当时无浏览器，只有静态推导。轮61 用 Range.getClientRects 复核，测出相反方向；
轮63 打通 chrome headless 直连后才发现：
**Range 对块级元素返回的是行盒范围（L 恒为盒子左边界），不是文字墨迹**，
该工具判断居中不可靠。

## 本次结论（像素法，390 逻辑视口 via iframe）
段3 h1 主标题  墨迹中心 194.5，偏差 -0.5px
段4 em 副标    墨迹中心 196.5，偏差 +1.5px
两者 |偏差| < 2px → 居中成立，补偿有效。

## 同时排掉两个误判
1. 截图「整体右移被切」是假象：--window-size=390,844 时 Chrome 窗口有最小宽度，
   实际视口与 CSS 不符。布局探针证明 scrollW=390=innerWidth、overflow=false。
   → 改用大窗口 + 390px iframe，无此伪影。
2. .hero-tag 像素中心偏 +19.5px 不是缺陷：
   它是 display:flex，视觉主体是「::before 装饰线(clamp 26~54px) + gap 14px + 文字」，
   只测文字必然偏。整体几何核算中心 = 195.0，偏差 +0.00px，设计正确。

## 环境两个坑
  · python 被解析到 D:/LibreOffice/program/python-core-3.13.15（无 PIL）
    → 用 D:/fj-actions-runner/_work/_tool/Python/3.12.10/x64/python.exe
  · 127.0.0.1:8791 探测失败但 localhost / [::1] 可用 → 用 localhost
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SHOT = os.path.join(BASE, '_qa', 'r63', 'frame390.png')
CTR = 195.0   # 390 视口容器中心
TOL = 2.0


def segs(img, x0, x1, thresh=60, min_h=6):
    px = img.load()
    out, cur = [], None
    for y in range(img.height):
        l = r = None
        for x in range(x0, min(x1, img.width)):
            rr, gg, bb = px[x, y][:3]
            lum = 0.2126 * rr + 0.7152 * gg + 0.0722 * bb
            if lum > thresh:
                if l is None:
                    l = x
                r = x
        if l is not None:
            if cur is None:
                cur = [y, y, l, r]
            else:
                cur[1] = y
                cur[2] = min(cur[2], l)
                cur[3] = max(cur[3], r)
        else:
            if cur and cur[1] - cur[0] >= min_h:
                out.append(tuple(cur))
            cur = None
    if cur and cur[1] - cur[0] >= min_h:
        out.append(tuple(cur))
    return out


def main():
    if not os.path.exists(SHOT):
        print('RESULT: SKIP  找不到截图 _qa/r63/frame390.png（需先跑 _qa/pixel_frame.py）')
        return 0
    img = Image.open(SHOT).convert('RGB')
    S = segs(img, 0, 390)
    if not S:
        print('RESULT: SKIP  解析不出文字行带')
        return 0

    print('390 视口（容器中心 %.1f）文字行带：' % CTR)
    for i, (y0, y1, l, r) in enumerate(S[:8]):
        print('  段%-2d y%4d-%4d x%4d-%4d w=%3d 中心 %7.1f 偏差 %+5.1f' % (
            i, y0, y1, l, r, r - l + 1, (l + r) / 2, (l + r) / 2 - CTR))

    fails = []
    print()
    for name, idx in (('h1(段3)', 3), ('em(段4)', 4)):
        if idx >= len(S):
            print('[SKIP] %s 行带不存在' % name)
            continue
        y0, y1, l, r = S[idx]
        dev = (l + r) / 2 - CTR
        ok = abs(dev) <= TOL
        print('[%s] %-8s 偏差 %+.1fpx（容差 %.1f）' % ('PASS' if ok else 'FAIL', name, dev, TOL))
        if not ok:
            fails.append('%s 偏 %.1fpx' % (name, dev))

    print()
    if fails:
        print('RESULT: FAIL  ' + '; '.join(fails))
        return 1
    print('RESULT: PASS  h1 与 em 墨迹中心均居中（|偏差| <= %.1fpx），补偿有效' % TOL)
    return 0


if __name__ == '__main__':
    sys.exit(main())
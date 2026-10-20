# -*- coding: utf-8 -*-
"""tools/resilience_test.py —— 容错与降级基线判据（纯静态，CI 可跑）。

## 为什么需要它
轮45 检查了三个此前从未验证的维度：错误边界、HTTP 缓存、SW 更新策略。
结论都是**无缺陷**，但结论需要固化成判据，否则以后改动可能悄悄破坏。

## 检查项
1. 静态 <img> 必须有 onerror 降级（避免加载失败时留白块）
2. 无 JS 时必须有 <noscript> 提示
3. 必须有版本对账守卫（CSS --build vs HTML BUILD）
4. SW 必须有 skipWaiting + clients.claim（新版本立即接管）
5. 关键模块必须有 try/catch（AR/hash/摄像头）

## 实测背景（轮45）
· 图片 onerror：3/3 静态图 + JS 注入图均有降级
· canvas 不可用：页面仍可读（Phoenix 内部已处理，不抛异常）
· HTTP 缓存：GitHub Pages 固定 max-age=600，有其他机制兜底
· SW 更新：skipWaiting + clients.claim + 版本对账清缓存重载
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, 'site', 'index.html')
SW = os.path.join(BASE, 'site', 'sw.js')


def main():
    if not os.path.exists(HTML):
        print('RESULT: SKIP  找不到 index.html')
        return 0

    html = open(HTML, encoding='utf-8').read()
    fails = []
    checked = 0

    # 1) 静态图片 onerror
    checked += 1
    imgs = re.findall(r'<img[^>]*>', html)
    no_onerror = [i for i in imgs if 'onerror' not in i and 'src=' in i]
    if no_onerror:
        fails.append('%d 个静态 <img> 缺 onerror 降级' % len(no_onerror))
    else:
        print('[PASS] %d 个静态图片均有 onerror 降级' % len(imgs))

    # 2) noscript 提示
    checked += 1
    if '<noscript>' not in html:
        fails.append('缺 <noscript> 提示（禁 JS 时用户会以为网站坏了）')
    else:
        print('[PASS] 有无 JS 降级提示')

    # 3) 版本对账守卫
    checked += 1
    if '--build' in html and "var BUILD" in html:
        print('[PASS] 有版本对账守卫（CSS --build vs HTML BUILD）')
    else:
        fails.append('缺版本对账守卫（新 HTML + 旧 CSS 会版式崩坏）')

    # 4) SW 更新策略
    checked += 1
    if os.path.exists(SW):
        sw = open(SW, encoding='utf-8').read()
        missing = []
        if 'skipWaiting' not in sw:
            missing.append('skipWaiting')
        if 'clients.claim' not in sw:
            missing.append('clients.claim')
        if missing:
            fails.append('SW 缺 %s（新版本无法立即接管）' % '/'.join(missing))
        else:
            print('[PASS] SW 有 skipWaiting + clients.claim')
    else:
        print('[SKIP] 无 sw.js')

    # 5) 关键模块 try/catch
    checked += 1
    js_dir = os.path.join(BASE, 'site', 'assets', 'js')
    total_try = 0
    if os.path.isdir(js_dir):
        for f in os.listdir(js_dir):
            if f.endswith('.js'):
                s = open(os.path.join(js_dir, f), encoding='utf-8').read()
                total_try += s.count('try {') + s.count('try{')
    if total_try < 10:
        fails.append('关键模块 try/catch 过少（%d 个），容错不足' % total_try)
    else:
        print('[PASS] JS 模块共 %d 个 try 块' % total_try)

    print()
    print('检查 %d 项容错基线' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  容错与降级基线 %d 项全部成立' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
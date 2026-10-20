# -*- coding: utf-8 -*-
"""tools/rhythm_test.py —— 留白节奏判据（纯静态，CI 可跑）。

## 为什么需要它

轮27 实测发现：8 个 section 的 padding-top 唯一值是 [148] ——
全站 11475px 的滚动，每一屏上下留白完全相同。
但内容密度差 5.6 倍（merch 内容 2016px vs scan 357px）。

同样的补白在密处局促、在疏处空旷。滚动是匀速的，没有起伏。
这是 Awwwards 评审会注意到的「节奏」问题。

修法：按实测内容密度分级留白（tight / snug / base / roomy / loose）。

## 判据（防止回归）

1. CSS 里必须定义分级令牌（--sec-y-tight/snug/roomy/loose）
2. 至少 3 个不同的留白级别被实际使用
   （若只剩一两个级别，说明又退化成匀速）
3. 内容最密的段（merch）必须用最紧的级别
4. 内容最疏的段（scan）必须用最松的级别

## 判据 3/4 的依据
它们由实测内容高度决定，不是随意指定：
  merch 内容 2016px → 最密 → tight
  scan  内容  357px → 最疏 → loose
若这两条不成立，说明分级逻辑被改坏了。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')

TIERS = ['sec-y-tight', 'sec-y-snug', 'sec-y-roomy', 'sec-y-loose']


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0

    s = open(CSS, encoding='utf-8').read()
    # 剥离 CSS 注释，只留生效规则
    body = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)

    fails = []
    checked = 0

    # 1) 令牌是否定义
    for t in TIERS:
        checked += 1
        if ('--%s:' % t) not in body:
            fails.append('缺少留白分级令牌 --%s' % t)

    # 2) 实际使用了几种级别
    used = set()
    for t in TIERS:
        # 在 padding 声明里被引用
        if re.search(r'padding[^;{}]*var\(--%s\)' % t, body):
            used.add(t)
    checked += 1
    if len(used) < 3:
        fails.append('只用到 %d 种留白级别（应 >=3，否则退化成匀速）: %s'
                     % (len(used), sorted(used)))
    else:
        print('  使用 %d 种留白级别: %s' % (len(used), ', '.join(sorted(used))))

    # 3) merch 用最紧级别
    checked += 1
    merch_rule = re.search(r'section#merch\s*\{([^}]*)\}', body)
    if not merch_rule:
        fails.append('找不到 section#merch 的留白规则')
    elif 'var(--sec-y-tight)' not in merch_rule.group(1):
        fails.append('#merch（内容最密）没有用最紧级别 --sec-y-tight')

    # 4) scan 用最松级别
    checked += 1
    scan_rule = re.search(r'section\.foot\s*\{([^}]*)\}', body)
    if not scan_rule:
        fails.append('找不到 section.foot 的留白规则')
    elif 'var(--sec-y-loose)' not in scan_rule.group(1):
        fails.append('.foot/scan（内容最疏）没有用最松级别 --sec-y-loose')

    print('检查 %d 项留白节奏判据' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  留白节奏分级成立（%d 级，密紧疏松）' % len(used))
    return 0


if __name__ == '__main__':
    sys.exit(main())

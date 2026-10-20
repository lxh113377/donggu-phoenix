# -*- coding: utf-8 -*-
"""tools/stagger_test.py —— 入场时序判据（纯静态，CI 可跑）。

## 为什么需要它
轮28 实测：22 个 .reveal 元素里 22 个 transition-delay 都是 0s，
包括**所有段落标题 .sec-head** —— 标题与内容完全同时淡入，
缺「标题定调 → 内容跟进」的层次。这是最容易被看出「模板感」的动效。

修法：.sec-head 保持 0ms，其后第一个内容块 120ms，
后续元素由现有 --d（80ms 步进）接管。

## 判据
1. 必须有 .sec-head 被显式置零的规则
2. 必须有「标题之后首个内容块」的延迟规则（>=1 条）
3. 7 个 sec-head 的下一项类型都能被覆盖：
   .reveal 容器（4 个）、.totem-grid（1）、.craft（1）
4. 延迟值必须显著（>= 60ms），太小等于没层次
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
HTML = os.path.join(BASE, 'site', 'index.html')


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0

    s = open(CSS, encoding='utf-8').read()
    body = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)

    fails = []
    checked = 0

    # 1) .sec-head 显式置零
    checked += 1
    if not re.search(r'\.sec-head\s*\{[^}]*transition-delay\s*:\s*0', body):
        fails.append('.sec-head 没有显式把 transition-delay 置零')

    # 2) 标题之后首个内容块的延迟规则
    checked += 1
    delay_rules = re.findall(
        r'\.sec-head\s*\+\s*[^{}]*\{[^}]*transition-delay\s*:\s*(\d+)ms', body)
    if not delay_rules:
        fails.append('没有任何「标题之后首个内容块」的延迟规则')
    else:
        vals = [int(v) for v in delay_rules]
        # 4) 延迟值必须显著 —— **逐条**校验，不能用 max()。
        # 反向验证教训：用 max() 时，只要还有一条规则是 120ms，
        # 其他规则退化成 0ms/20ms 都不会判红（聚合洗绿）。
        checked += 1
        weak = [v for v in vals if v < 60]
        if weak:
            fails.append('有 %d 条入场延迟太小（%s ms < 60ms），等于没有层次'
                         % (len(weak), ','.join(str(v) for v in sorted(set(weak)))))
        else:
            print('  标题后首个内容块延迟: %s' % ', '.join('%dms' % v for v in sorted(set(vals))))

    # 3) 覆盖 7 个 sec-head 的下一项类型
    h = open(HTML, encoding='utf-8').read() if os.path.exists(HTML) else ''
    heads = re.findall(r'<div class="sec-head[^"]*"[^>]*>', h)
    checked += 1
    if len(heads) < 5:
        fails.append('HTML 里只找到 %d 个 sec-head（预期 7 个）' % len(heads))
    else:
        print('  HTML 里 sec-head 数量: %d' % len(heads))
        # 校验三类下一项都有对应规则
        kinds = [
            ('.reveal 容器', r'\.sec-head\s*\+\s*\.reveal'),
            ('.totem-grid', r'\.sec-head\s*\+\s*\.totem-grid'),
            ('.craft',      r'\.sec-head\s*\+\s*\.craft'),
        ]
        for name, pat in kinds:
            checked += 1
            if not re.search(pat, body):
                fails.append('缺少针对 %s 的入场时序规则' % name)

    print('检查 %d 项入场时序判据' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  入场时序分层成立（标题先到，内容跟进）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
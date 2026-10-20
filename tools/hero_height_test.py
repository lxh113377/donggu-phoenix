# -*- coding: utf-8 -*-
"""tools/hero_height_test.py —— 手机首屏必须真的是一屏（U-03 长期防护）。

改成纯静态的理由：轮10 用浏览器量 getBoundingClientRect 修好了「首屏被撑成 1.32~1.56 屏」，
但 agent-browser 在本机频繁卡死，一个跑不稳的脚本防不住回退。回退根因是 CSS 写法，可静态判。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')


def media_blocks(css, width):
    out = []
    for m in re.finditer(r'@media\s*\(max-width:\s*' + str(width) + r'px\)\s*\{', css):
        start = m.end()
        depth, i = 1, start
        while i < len(css) and depth > 0:
            if css[i] == '{':
                depth += 1
            elif css[i] == '}':
                depth -= 1
            i += 1
        out.append((m.start(), css[start:i - 1]))
    return out


def main():
    css = open(CSS, encoding='utf-8').read()
    fails = []
    blocks = media_blocks(css, 900)
    if not blocks:
        print('RESULT: FAIL')
        print('  - 找不到 @media (max-width:900px) 块')
        return 1
    pos, block = blocks[-1]

    mh = re.search(r'\.hero\s*\{([^}]*)\}', block)
    if not mh:
        fails.append('手机断点里没有 .hero 规则（无法锁定一屏）')
    else:
        body = mh.group(1).replace(' ', '')
        if 'height:100svh' not in body:
            fails.append('.hero 未设 height:100svh（首屏会被内容撑长）')
        if 'min-height:100svh' not in body:
            fails.append('.hero 未设 min-height:100svh')

    mv = re.search(r'\.hero-visual\s*\{([^}]*)\}', block)
    if not mv:
        fails.append('手机断点里没有 .hero-visual 规则（固定 min-height 未被覆盖）')
    elif 'min-height:0' not in mv.group(1).replace(' ', ''):
        fails.append('.hero-visual 未设 min-height:0（clamp 会顶破一屏）')

    base_pos = css.find('.hero-visual{')
    if base_pos >= 0 and pos < base_pos:
        fails.append('手机断点写在基础 .hero-visual 之前，会被后面的 clamp min-height 覆盖')

    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  手机首屏锁定一屏（height 100svh + visual min-height 0 + 顺序正确）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
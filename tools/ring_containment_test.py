# -*- coding: utf-8 -*-
"""tools/ring_containment_test.py —— 装饰元素必须天然不溢出（U-07 防护）。

## 判据设计（纯静态，不依赖浏览器）

轮11 教训：第一版用浏览器量 getBoundingClientRect，但本机 agent-browser 会话
频繁卡死（单次 set viewport 可超时 90s），导致门禁本身不可靠、也无法放进
破坏性测试沙箱（sandbox 里同样卡死）。

而 U-07 的根因完全是**代码写法**，静态判定更稳、更快、更可复现：
  · 负 inset（如 inset:-5%）会把布局盒向外扩 → 可能超出父级/视口
  · width 上限过大（如 530px/560px）会撑大布局盒
  · 正确写法是 transform:scale —— transform 不参与布局盒计算，天然不产生滚动

另外校验 @keyframes 是否保留 scale：动画会覆盖静态 transform，
若 keyframes 里没有 scale，环会在动画启动后缩回原尺寸（轮11 踩过）。

浏览器位置验证移到 tools/visual_check.py（可选，不进门禁）。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_guard import verdict, emit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')

RING_SELECTORS = ['.hero-ring{', '.hero-ring.b{', '.totem-ring{', '.totem-ring.b{']


def rule_of(css, sel):
    i = css.find(sel)
    if i < 0:
        return None
    return css[i: css.find('}', i) + 1]


def main():
    css = open(CSS, encoding='utf-8').read()
    fails = []
    checked = 0

    for sel in RING_SELECTORS:
        rule = rule_of(css, sel)
        if rule is None:
            fails.append('找不到装饰环规则 %s' % sel)
            continue
        checked += 1

        # 1) 负 inset 会向外扩布局盒
        m = re.search(r'inset:\s*-', rule)
        if m:
            fails.append('%s 使用负 inset（%s），会向外扩布局盒' % (sel.rstrip('{'), m.group(0)))

        # 2) 超宽的 width 上限会撑大布局盒
        mw = re.search(r'width:\s*min\(\s*\d+%\s*,\s*(\d+)px\s*\)', rule)
        if mw and int(mw.group(1)) >= 500:
            fails.append('%s 的 width 上限 %spx 过大，可能撑大布局盒'
                         % (sel.rstrip('{'), mw.group(1)))

    # 3) 使用 scale 的环，其 @keyframes 必须保留 scale
    ks = re.search(r'@keyframes slowSpin\{(.*?)\}\}', css, re.S)
    if ks:
        body = ks.group(1)
        if 'scale' not in body:
            fails.append('@keyframes slowSpin 未保留 scale —— 动画会覆盖静态缩放，环缩回原尺寸')

    # 4) 若环使用了 scale，keyframes 里出现的 scale 值应与基础规则一致
    hero_b = rule_of(css, '.hero-ring.b{') or ''
    m_rule = re.search(r'scale\(([\d.]+)\)', hero_b)
    if m_rule and ks:
        v = m_rule.group(1)
        if v not in ks.group(1):
            fails.append('.hero-ring.b 的 scale(%s) 与 keyframes 里的值不一致' % v)

    # 汇总
    for f in fails:
        print('  -', f)
    code, msg = verdict(checked=checked, fails=fails, what='装饰环规则')
    return emit(code, msg)


if __name__ == '__main__':
    sys.exit(main())

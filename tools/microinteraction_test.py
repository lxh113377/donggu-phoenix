# -*- coding: utf-8 -*-
"""tools/microinteraction_test.py —— 微交互反馈判据（纯静态，CI 可跑）。

## 为什么需要它
轮31 静态审查 13 类可交互元素的 hover/active 覆盖，发现两处缺口：
  #cam .close   摄像头关闭按钮（44×44 常驻可见）—— hover 与 active 都没有
  .nav-toggle   移动端菜单按钮 —— 有 active 缺 hover
鼠标悬停毫无反馈，用户不确定它可点。这是「看起来能点但没反应」的典型。

## 判据
对核心交互元素，要求同时具备 :hover 与 :active（或由全局规则统一提供）。

## 白名单（有特殊设计的元素）
  brand —— hover 是图标旋转 rotate(-8deg) scale(1.06)，已是有设计感的反馈，
            不需要再加 active。机械要求 active 反而是过度约束。

## 已确认的全局兜底
  :focus-visible  全站统一 outline:2px solid var(--she-gold)，
  所以各元素不必各自声明焦点样式。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')

# 需要 hover + active 的核心交互元素
CORE = [
    'ar-btn', 'hero-cta', 'btn', 'btn-ask', 'ar-icon',
    'carve-play', 'nav-toggle', 'totem-hit', 'close',
]

# 有特殊 hover 设计、豁免 active 的元素
EXEMPT_ACTIVE = {'brand'}


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0

    css = re.sub(r'/\*.*?\*/', ' ', open(CSS, encoding='utf-8').read(), flags=re.S)

    # 全局 focus-visible 兜底必须存在
    # 只认「行首的 :focus-visible」（全局兜底）；
    # 局部规则如 #carve-stage:focus-visible 不能当全局兜底。
    if not re.search(r'(^|\})\s*:focus-visible\s*\{', css):
        print('RESULT: FAIL')
        print('  - 缺少全局 :focus-visible 兜底（键盘焦点将不可见）')
        return 1
    print('  全局 :focus-visible 兜底存在')

    fails = []
    checked = 0
    for cls in CORE:
        checked += 1
        esc = re.escape(cls)
        # 要求规则**以该选择器开头**（允许前导 .a .b 这类祖先），
        # 避免被组合选择器里顺带提到的同类名误判。
        has_hover = bool(re.search(r'(^|[,}\s])\.%s[^{},]*:hover' % esc, css, re.M))
        has_active = bool(re.search(r'(^|[,}\s])\.%s[^{},]*:active' % esc, css, re.M))
        if not has_hover:
            fails.append('.%s 缺 :hover 反馈' % cls)
        if not has_active and cls not in EXEMPT_ACTIVE:
            fails.append('.%s 缺 :active 反馈' % cls)

    print('检查 %d 个核心交互元素' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个核心交互元素均有 hover/active 反馈' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
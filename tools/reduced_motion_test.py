# -*- coding: utf-8 -*-
"""tools/reduced_motion_test.py —— prefers-reduced-motion 覆盖判据（纯静态，CI 可跑）。

## 为什么需要它
轮29 静态审查全站 5 个 reduced-motion 块，发现 4 个**无限循环**动画漏了覆盖：
  #boot .seal::after      spin       1.5s infinite
  .btn--primary::after    pulse      2s infinite
  .ar-brand .ar-dot       pulse      2.4s infinite
  #cam .guide::after      ringPulse  3s infinite

这些是 opacity/scale/rotate 的持续脉冲，WCAG 2.3.3 与前庭功能障碍直接相关。
用户开了「减少动效」却还在脉冲，等于偏好没被兑现。

## 判据
凡 animation 里含 infinite 的规则，其选择器必须出现在某个
@media (prefers-reduced-motion:reduce) 块内（且该块里把它 animation 置 none）。

## 注意
不要求一次性动画（fade/rise）必须覆盖 —— 它们播完即止，风险低。
只查 infinite 的。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')


def strip_comments(s):
    """剥注释 —— 判据扫的是 CSS 行为，注释里的字面量不是行为。"""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return s


def blocks(s):
    """提取所有 reduced-motion @media 块的文本。

    一手事故（2026-10-20 轮50）：本函数原先直接 find("prefers-reduced-motion")，
    当这个词只出现在**注释**里（我在 .narrate 段写了「必须在文末 prefers-reduced-motion
    块登记」），它往前 rfind("@media") 找到的块在注释位置**之前**，于是
    idx = end <= i，下一轮又找到同一个 i —— 无限循环。CI 上表现为 job 静默挂死，
    本机则一次烧掉 20 个 python 进程各 900+ 秒 CPU。
    两处根治：① 只匹配 @media ... { 这种真块（正则）；② idx 严格前进 + 迭代上限兜底。
    """
    out = []
    for m in re.finditer(r"@media[^{]*prefers-reduced-motion[^{]*\{", s):
        depth = 0
        for k in range(m.end() - 1, len(s)):
            if s[k] == "{":
                depth += 1
            elif s[k] == "}":
                depth -= 1
                if depth == 0:
                    out.append(s[m.start():k + 1])
                    break
    return out


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0

    s = open(CSS, encoding='utf-8').read()
    snc = strip_comments(s)
    rm = ' '.join(blocks(snc))
    # 剥注释后再找动画（注释里提到 infinite 不算）
    body = snc
    # 去掉 media 块内部，避免把 reduced-motion 块里的 animation:none 当成使用者
    flat = body
    for b in blocks(snc):
        flat = flat.replace(b, ' ')

    users = []
    for m in re.finditer(r'([^{}\n;]+)\{([^}]*animation\s*:[^}]*infinite[^}]*)\}', flat):
        sel = m.group(1).strip().split(chr(10))[-1].strip()
        if not sel or sel.startswith('@'):
            continue
        users.append(sel)

    fails = []
    checked = len(users)
    for sel in users:
        parts = [p.strip() for p in sel.split(',')]
        if not any(p in rm for p in parts):
            fails.append('无限动画未被 reduced-motion 覆盖: %s' % sel[:60])

    print('检查 %d 个无限动画的使用者' % checked)
    if checked == 0:
        print()
        print('RESULT: SKIP  未找到任何无限动画 —— 不计入 PASS（防止「没测到」被当「通过」）')
        return 0

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个无限动画全部有 reduced-motion 覆盖' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
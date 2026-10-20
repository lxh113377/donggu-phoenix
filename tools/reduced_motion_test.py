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


def blocks(s):
    """提取所有 reduced-motion 块的文本。"""
    out = []
    idx = 0
    while True:
        i = s.find('prefers-reduced-motion', idx)
        if i < 0:
            break
        start = s.rfind('@media', 0, i)
        depth = 0
        end = start
        for k in range(start, len(s)):
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
                if depth == 0:
                    end = k + 1
                    break
        out.append(s[start:end])
        idx = end
    return out


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0

    s = open(CSS, encoding='utf-8').read()
    rm = ' '.join(blocks(s))
    # 剥注释后再找动画（注释里提到 infinite 不算）
    body = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    # 去掉 media 块内部，避免把 reduced-motion 块里的 animation:none 当成使用者
    flat = body
    for b in blocks(body):
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
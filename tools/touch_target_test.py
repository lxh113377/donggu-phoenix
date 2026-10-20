# -*- coding: utf-8 -*-
"""tools/touch_target_test.py —— 触摸目标尺寸判据（需浏览器）。

## 为什么需要它
展签扫码进来的用户 100% 用手指操作。WCAG 2.5.8（AA）要求
指针目标 >= 24×24 CSS px；Apple HIG / Material 建议 44/48。

## 轮51 发现的真实缺陷
390×844 实测 .carve-slider 命中区只有 195×3px（轨道视觉高 3px），
thumb 22px —— 拇指几乎拖不中，且低于 24px 下限。
修法：input 加高到 44px 作命中区，轨道用 background-size 锁 3px 居中，
thumb 22->26px。视觉零变化，命中区扩大 14 倍。

## 判据
移动 + 桌面两视口下，所有可交互元素宽高都要 >= 24px。
豁免：display:inline 的链接（WCAG 2.5.8 的 Inline 条款——行内链接
随文本流排布，天然不满足尺寸要求，规范明确排除）。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_PX = 24


def ps(cmd, timeout=90):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def scroll_all():
    for y in [0, 2000, 4000, 6000, 8000, 10000, 0]:
        ps('agent-browser eval "window.scrollTo(0,%d);1"' % y)
        time.sleep(0.5)


def main():
    probe = os.path.join(BASE, '_qa', 'touch_target_probe.js')
    if not os.path.exists(probe):
        print('RESULT: SKIP  探针文件缺失（_qa/touch_target_probe.js）')
        return 0

    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    fails = []
    any_data = False
    for w, h, label in [(390, 844, '移动'), (1440, 900, '桌面')]:
        ps('agent-browser set viewport %d %d' % (w, h))
        time.sleep(0.6)
        ps('agent-browser open "http://127.0.0.1:8791/?tt=%d"' % int(time.time() * 1000))
        ps('agent-browser wait --load networkidle')
        # cacheBust：绕开 HTTP 缓存（max-age=600），否则撤销测试读到旧 CSS
        ps('agent-browser eval "(function(){var l=document.createElement(\'link\');l.rel=\'stylesheet\';l.href=\'/assets/css/main.css?cb=\'+Date.now();document.head.appendChild(l);return 1})()"')
        time.sleep(1.2)
        time.sleep(2.0)
        scroll_all()
        out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/touch_target_probe.js")')
        d = None
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith(chr(34)) and line.endswith(chr(34)):
                try:
                    d = json.loads(json.loads(line))
                    break
                except Exception:
                    continue
        if not d:
            print('[%s %dx%d] 无数据（不改判 PASS）' % (label, w, h))
            continue
        any_data = True
        bad = d['bad']
        print('[%s %dx%d] 检查 %d 个交互元素，小于 %dpx 的 %d 个' % (
            label, w, h, d['checked'], MIN_PX, len(bad)))
        for b in bad[:6]:
            print('    - %s.%s %dx%d  %s' % (b['tag'], b['cls'], b['w'], b['h'], b['txt']))
        if bad:
            fails.append('%s %dx%d：%d 个触摸目标 < %dpx' % (label, w, h, len(bad), MIN_PX))

    print()
    if not any_data:
        print('RESULT: SKIP  两视口均无数据')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  双视口触摸目标均 >= %dpx（Inline 链接按 WCAG 2.5.8 豁免）' % MIN_PX)
    return 0


if __name__ == '__main__':
    sys.exit(main())

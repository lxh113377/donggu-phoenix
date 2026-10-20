# -*- coding: utf-8 -*-
"""tools/run_browser_suite.py —— 一键跑全部浏览器测试（本地）。

## 为什么需要它
项目有 16 个纯静态判据在 CI 里自动跑，另有 15 个需要浏览器的判据只能在本地跑。
浏览器判据如果长期不跑，很容易悄悄失效——而它们覆盖的恰恰是
静态检查看不见的东西：布局溢出、动画触发、AR 播放、视觉重量。

## 用法
  python tools/run_browser_suite.py            # 跑全部
  python tools/run_browser_suite.py --fast     # 只跑快的（跳过 AR 播放类）
  python tools/run_browser_suite.py --list     # 只列出

## 聚合判定（关键）
**任何一个子测试 FAIL，总判定必须 FAIL。**
绝不能因为「大多数通过」就报绿——这是 audit-runner-safe-aggregate 的核心教训：
全局 any()/max() 会把单个失败洗白。

## 前置
需要本地服务 http://127.0.0.1:8791（python -m http.server 8791 --directory site）。
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
PY = sys.executable

# (脚本, 是否 fast 组, 说明)
SUITE = [
    ('tools/multi_viewport_test.py', True, '9 视口横向+纵向完整性'),
    ('tools/reveal_coverage_test.py', True, '进场元素全部可见'),
    ('tools/visual_balance_test.py', True, '首屏视觉重量平衡'),
    ('tools/hero_height_test.py', True, '手机首屏锁一屏'),
    ('tools/ring_containment_test.py', True, '装饰环在画布内'),
    ('tools/anchor_offset_test.py', True, '锚点偏移正确'),
    ('tools/zoom_test.py', True, '缩放下布局不崩'),
    ('tools/image_quality_test.py', True, '图片尺寸/格式'),
    ('tools/reveal_after_jump_test.py', True, '跳转后进场不失效'),
    ('tools/touch_target_test.py', False, '双视口触摸目标 >= 24px'),
    ('tools/defer_regression_test.py', False, 'defer 后运行时不回归'),
    ('tools/ar_e2e_test.py', False, 'AR 端到端 7 项'),
    ('tools/ar_playback_test.py', False, 'AR 播放时序'),
    ('tools/ar_scenes_test.py', False, 'AR 三场景'),
    ('tools/ar_stamp_test.py', False, '集章持久化'),
    ('tools/ar_focus_test.py', False, 'AR 焦点闭环'),
]


def server_alive():
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command',
                            "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8791/' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }"],
                           capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
        return '200' in (r.stdout or '')
    except Exception:
        return False


def main():
    args = sys.argv[1:]
    if '--list' in args:
        for s, fast, desc in SUITE:
            print('%-40s %-6s %s' % (s, 'fast' if fast else 'full', desc))
        return 0

    fast_only = '--fast' in args
    todo = [x for x in SUITE if x[1] or not fast_only]

    if not server_alive():
        print('本地服务 http://127.0.0.1:8791 未启动，无法跑浏览器测试。')
        print('请先运行：python -m http.server 8791 --directory site')
        print()
        print('RESULT: SKIP  服务未启动')
        return 0

    print('浏览器判据套件：%d 项%s' % (len(todo), '（fast）' if fast_only else ''))
    print('=' * 64)

    results = []
    t0 = time.time()
    for script, _fast, desc in todo:
        path = os.path.join(BASE, script)
        if not os.path.exists(path):
            print('%-34s SKIP  文件不存在' % script)
            results.append((script, 'SKIP', desc))
            continue
        start = time.time()
        try:
            r = subprocess.run([PY, script], cwd=BASE, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=600)
            out = (r.stdout or '') + (r.stderr or '')
            code = r.returncode
        except subprocess.TimeoutExpired:
            out, code = 'TIMEOUT', 2
        dur = time.time() - start
        if code == 0:
            status = 'PASS'
        elif code == 2 or 'SKIP  服务未启动' in out:
            status = 'SKIP'
        else:
            status = 'FAIL'
        results.append((script, status, desc))
        print('%-34s %-6s %5.1fs  %s' % (script.replace('tools/', ''), status, dur, desc))
        if status == 'FAIL':
            for line in out.splitlines():
                line = line.strip()
                if line.startswith('- '):
                    print('      ', line[:100])

    print('=' * 64)
    n_pass = sum(1 for _, s, _ in results if s == 'PASS')
    n_fail = sum(1 for _, s, _ in results if s == 'FAIL')
    n_skip = sum(1 for _, s, _ in results if s == 'SKIP')
    print('通过 %d / 失败 %d / 跳过 %d，用时 %.1fs' % (n_pass, n_fail, n_skip, time.time() - t0))
    print()

    # 聚合判定：只要有一个 FAIL 就 FAIL（绝不用 any() 洗绿）
    if n_fail:
        print('RESULT: FAIL  %d 项浏览器判据未通过' % n_fail)
        return 1
    if n_pass == 0:
        print('RESULT: SKIP  无一可跑')
        return 0
    print('RESULT: PASS  %d 项浏览器判据全部通过' % n_pass)
    return 0


if __name__ == '__main__':
    sys.exit(main())
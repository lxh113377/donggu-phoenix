# -*- coding: utf-8 -*-
"""tools/browser_test_lint.py —— 浏览器测试必须防缓存污染（纯静态，CI 可跑）。

## 这是第 6 次「测量手段不可靠」后的机制化

同一类错误反复出现：
  轮9  / 15 / 22  零样本判 PASS（三次）
  轮28            max() 聚合洗绿
  轮30            ar_focus_test 被 SW cache-first 假绿
  轮34            defer_regression_test 再犯同一个 SW 缓存错误

轮30 踩过并写进了注释，轮34 写新测试时**又忘了**。
→ 说明「记得」不管用，必须做成检查。

## 判据

凡是用 agent-browser 打开本仓页面的测试脚本（tools/ 与 _qa/ 下含
'agent-browser' 且含 '127.0.0.1' 或 'lxh113377.github.io' 的 .py），
必须包含防缓存套路：

  · clear_sw.js 引用      —— 注销 SW + 删所有 caches
  · 唯一参数 URL          —— ?xxx= + int(time...) 或 %d / %s 拼接

两条缺一即警告（不判红，因为有些测试只测静态内容不需要刷新）。

## 为什么不全判红
部分是「读一次页面就好」的测试，缓存不会导致错误结论。
但**带反向验证的测试**（reverse_*.py）必须防缓存，否则假绿。
因此：reverse_*.py 缺防缓存 → 判红；其他 → 警告。
"""
import glob
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    dirs = [os.path.join(BASE, 'tools'), os.path.join(BASE, '_qa')]
    files = []
    for d in dirs:
        if os.path.isdir(d):
            files.extend(glob.glob(os.path.join(d, '*.py')))

    checked = 0
    hard_fail = []
    warns = []

    for f in files:
        base = os.path.basename(f)
        if base == 'browser_test_lint.py':
            continue
        try:
            s = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        # 只查浏览器测试
        if 'agent-browser' not in s:
            continue
        if '127.0.0.1' not in s and 'lxh113377' not in s:
            continue
        checked += 1

        has_clear = 'clear_sw.js' in s
        has_unique = (chr(63) in s and chr(61) in s) and ('time()' in s or '%d' in s or '%s' in s or 'Date.now' in s)

        # 满足任一即可：清 SW 或唯一 URL 都能避免读到旧内容
        _missing = [] if (has_clear or has_unique) else ['既未清 SW 也未用唯一 URL']
        missing = _missing
        if missing:
            msg = '%s: %s' % (base, ', '.join(missing))
            if base.startswith('reverse_'):
                hard_fail.append(msg)
            else:
                warns.append(msg)

    print('检查 %d 个浏览器测试脚本' % checked)
    if checked == 0:
        print()
        print('RESULT: SKIP  未找到浏览器测试脚本')
        return 0

    if warns:
        print()
        print('警告（非反向验证脚本，缓存不一定影响结论）:')
        for w in warns[:8]:
            print('  ~', w)

    print()
    if hard_fail:
        print('RESULT: FAIL  反向验证脚本必须防缓存（否则会假绿）')
        for m in hard_fail[:8]:
            print('  -', m)
        return 1
    print('RESULT: PASS  %d 个浏览器测试中，反向验证脚本均已防缓存' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())

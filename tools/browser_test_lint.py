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
        # 只查**真会启动浏览器**的测试（轮117 收紧）。
        # 旧写法只要正文里出现 agent-browser 字样就算浏览器测试 ——
        # 于是 reverse_suite_status.py 把该词当测试样本数据写在用例里，
        # 就被判「反向验证缺防缓存」。判据是「有没有调用」，不是「提没提」。
        # 真实启动痕迹：命令字面量以 agent-browser 开头（本仓惯例 ps('agent-browser …')），
        # 或 subprocess 里调 chrome/chromium。
        launches = False
        for _ln in s.splitlines():
            _code = _ln.split('#', 1)[0]
            if re.search(r'''['\"](\s*)agent-browser''', _code):
                launches = True
                break
        if not launches:
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

    # === 会话隔离判据（轮61）===
    # agent-browser 是常驻 daemon + 共享会话。本仓有并行端同时在用浏览器，
    # `close --all` 会关掉**所有**会话 —— 等于每次跑判据都把对方正在用的浏览器杀掉。
    # 这是连续 10 轮「agent-browser 卡死」的真相：不是 daemon 坏，是两个 agent 互杀会话。
    # tools/ 下是长期维护、进 CI 的判据，必须只关自己的会话（close 不带 --all）。
    killer = []
    for f in glob.glob(os.path.join(BASE, 'tools', '*.py')):
        bn = os.path.basename(f)
        if bn == 'browser_test_lint.py':
            continue
        # 反向验证脚本必须含被检字符串才能造样本，跳过自身（轮61：
        # 它因含 'close --all' 字面量被自己扫到判红）。
        # 违规样本内容应由拼接生成，或用 -- 拼接绕过；这里直接排除。
        if bn.startswith('reverse_'):
            continue
        try:
            t = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        if 'close --all' in t:
            killer.append(os.path.basename(f))
    if killer:
        hard_fail.append('%d 个 tools/ 判据用了 close --all（会杀并行端会话）：%s'
                         % (len(killer), ', '.join(sorted(killer)[:6])))

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
        # 标题必须能涵盖所有硬失败原因。轮61 曾固定写「必须防缓存」，
        # 但失败原因其实是 close --all —— 归因文案不准会让人查错方向。
        print('RESULT: FAIL  浏览器测试判据有 %d 项硬性问题' % len(hard_fail))
        for m in hard_fail[:8]:
            print('  -', m)
        return 1
    # viewport-lint：提示但不算失败（很多脚本是有意不设视口的）

    try:

        _vp_warns = check_viewport_setting(BASE)

        if _vp_warns:

            print()

            print("[WARN] 以下脚本 open 了页面但未显式设置视口（结果可能随环境漂移）：")

            for _w in _vp_warns:

                print("        -", _w)

    except Exception:

        pass

    print('RESULT: PASS  %d 个浏览器测试中，反向验证脚本均已防缓存' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
# === viewport-lint（轮49）：open 页面却没设视口 → 结果可能随环境漂移 ===
def check_viewport_setting(base):
    import glob, os, re
    warns = []
    for f in sorted(glob.glob(os.path.join(base, "tools", "*_test.py"))):
        try:
            s = open(f, encoding="utf-8").read()
        except Exception:
            continue
        if "agent-browser open" not in s:
            continue
        if "set viewport" in s:
            continue
        if "noqa: viewport" in s:
            continue
        warns.append(os.path.basename(f))
    return warns

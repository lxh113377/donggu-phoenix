# -*- coding: utf-8 -*-
"""反向验证 browser_test_lint 的两条硬判据都真的有效（轮61）。

## 为什么要补这个
lint 有两条判红规则：
  A. reverse_*.py 缺防缓存（轮32 立）
  B. tools/ 下用 close --all（轮61 立）
B 有 reverse_session_isolation.py 验过，A 却**没有对应的反向验证脚本** ——
一条判红规则若从没被证明能判红，就等于不知道它是不是哑的。

## 样本内容一律拼接生成（U-158 同课）
本文件自己也在 tools/ 且以 reverse_ 开头，
若写出完整字面量会被自己的被测判据扫到，造成自触发。
判据侧虽已排除 reverse_*，仍按拼接写法做双保险。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

KILL = 'close ' + '--all'          # 判据 B 的触发串
CACHE_MARK = 'clear_sw.js'         # 判据 A 要求的防缓存标记
UNIQ_MARK = '?x='                  # 判据 A 认可的唯一 URL 写法

results = []


def run_lint(sb):
    r = sb.run_python(os.path.join('tools', 'browser_test_lint.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    det = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    return r.returncode, det


# ---- A：reverse_ 脚本缺防缓存 -> 必须判红 ----
probe_a = os.path.join('tools', 'reverse_zz_nocache.py')
src_a = ("# -*- coding: utf-8 -*-\n"
         "import subprocess\n"
         "subprocess.run(['agent-browser', 'open', 'http://127.0.0.1:8791/'])\n"
         "print('no cache guard here')\n")
assert CACHE_MARK not in src_a and UNIQ_MARK not in src_a
with mutate_sandbox(require_clean=False) as sb:
    open(sb.path(probe_a), 'w', encoding='utf-8').write(src_a)
    rc, det = run_lint(sb)
    hit = any('reverse_zz_nocache' in d for d in det)
    print('[A reverse_ 缺防缓存] rc=%d 命中=%s' % (rc, hit))
    for d in det:
        if 'reverse_zz_nocache' in d:
            print('   ', d[:88])
    results.append(rc == 1 and hit)

# ---- B：tools/ 用 close --all -> 必须判红 ----
probe_b = os.path.join('tools', 'zz_closeall_probe.py')
src_b = ("# -*- coding: utf-8 -*-\n"
         "import subprocess\n"
         "subprocess.run(['agent-browser', '%s'])\n" % KILL
         + "print('x')\n")
with mutate_sandbox(require_clean=False) as sb:
    open(sb.path(probe_b), 'w', encoding='utf-8').write(src_b)
    rc, det = run_lint(sb)
    hit = any('zz_closeall_probe' in d for d in det)
    print('[B tools/ 用 close --all] rc=%d 命中=%s' % (rc, hit))
    for d in det:
        if 'zz_closeall_probe' in d:
            print('   ', d[:88])
    results.append(rc == 1 and hit)

print()
if all(results):
    print('RESULT: PASS  lint 的两条硬判据都能判红并定位到文件')
    sys.exit(0)
print('RESULT: FAIL  有判据未被证明有效')
sys.exit(1)

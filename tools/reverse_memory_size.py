# -*- coding: utf-8 -*-
r"""tools/reverse_memory_size.py —— 反向验证 memory_size_test 的棘轮（轮125）。

## 为什么必须验
memory_size_test 是**今天必然 PASS** 的判据（存量债务不判红）。
一条「建好就绿」的判据最危险 —— 它可能只是恒真。
必须证明：变大 / 新建超限 / 棘轮收紧 三种情形各按预期反应。

## 用例（破坏产品状态，不破坏判据）
  A 基线已建立 -> PASS
  B active-core 文件比基线变大 -> FAIL（点名「比基线变大」）
  C 新建一个超限的 active-core 文件 -> FAIL（点名「新建即超限」）
  D active-core 文件拆小 -> PASS 且基线收紧（棘轮生效）
  E append-only 日志（08/09）变大 -> 仍 PASS（R48 豁免不误伤）

## 环境缺口与判据不通过分开
沙箱建不起来 -> SKIP，不判 PASS。
"""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

GATE = os.path.join('tools', 'memory_size_test.py')
DIRS = ('memory', 'tools')


def run(sb):
    r = sb.run_python(GATE, timeout=120)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), out


bad = []

# ---- A 基线 + B 变大 ----
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    rc, res, out = run(sb)
    print('[A 基线] rc=%d %s' % (rc, res[:60]))
    if rc != 0:
        bad.append('A 基线未 PASS')

    # B: 把 06-sources.md 撑大（它原本合规，基线已记其实际值）
    p = sb.path(os.path.join('memory', '06-sources.md'))
    s = io.open(p, encoding='utf-8').read()
    io.open(p, 'w', encoding='utf-8').write(s + '\n' + ('x' * 900) + '\n')
    rc, res, out = run(sb)
    why = [l.strip() for l in out.splitlines() if '比基线变大' in l]
    print('[B 文件变大] rc=%d %s' % (rc, res[:60]))
    for w in why[:1]:
        print('     ', w[:100])
    if not (rc == 1 and why):
        bad.append('B 变大未被抓到（或未点名原因）')

# ---- C 新建超限文件 ----
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    run(sb)  # 先建立基线
    p = sb.path(os.path.join('memory', '10-brand-new.md'))
    io.open(p, 'w', encoding='utf-8').write('# 新记忆\n' + ('y' * 5000))
    rc, res, out = run(sb)
    print('[C 新建超限文件] rc=%d %s' % (rc, res[:60]))
    print('     ', [l.strip()[:80] for l in out.splitlines()
                    if '10-brand-new' in l][:2])
    if rc == 0:
        bad.append('C 新建超限文件却判 PASS（应 FAIL）')

# ---- D 拆小 -> 棘轮收紧 ----
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    run(sb)
    p = sb.path(os.path.join('memory', '06-sources.md'))
    before = os.path.getsize(p)
    io.open(p, 'w', encoding='utf-8').write('# 精简后\n')
    rc, res, out = run(sb)
    tight = [l.strip() for l in out.splitlines() if '棘轮收紧' in l]
    print('[D 拆小] rc=%d %s' % (rc, res[:60]))
    for t in tight[:1]:
        print('     ', t[:90])
    if rc != 0:
        bad.append('D 拆小后反而判红（应允许）')
    if not tight:
        bad.append('D 棘轮未收紧基线（下次仍可悄悄长回去）')
    # 收紧后再变大，必须被抓
    io.open(p, 'w', encoding='utf-8').write('# 精简后\n' + ('z' * 400))
    rc2, res2, out2 = run(sb)
    print('   收紧后再变大 -> rc=%d %s' % (rc2, res2[:50]))
    if rc2 != 1:
        bad.append('D2 收紧后未生效：再变大没被抓到')

# ---- E 日志类变大不应误伤 ----
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    run(sb)
    p = sb.path(os.path.join('memory', '09-upgrade-ledger.md'))
    s = io.open(p, encoding='utf-8').read()
    io.open(p, 'w', encoding='utf-8').write(s + '\n| U-999 | x | y | z | w | v |\n')
    rc, res, out = run(sb)
    print('[E 台账变大（R48 豁免）] rc=%d %s' % (rc, res[:60]))
    if rc != 0:
        bad.append('E 归档类日志被误判红（R48 豁免失效）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  棘轮 5 类情形反应全部正确（变大/新建超限/收紧/豁免都按预期）')
sys.exit(0)

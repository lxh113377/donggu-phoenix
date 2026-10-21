# -*- coding: utf-8 -*-
"""反向验证 admin_colspan_test（轮87）。

## 特别针对上一轮的自欺
轮87 我自己写的 check_colspan.py 在「归属失败」时仍输出 PASS ——
所以本判据的反向验证重点测两件事：
  1. 硬编码退化能被抓到（常规）
  2. **表格被删光时不能假通过**（归属失败必须出声）
第 2 条是上轮那个 bug 的直接对应物。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')
DYN = 'colspan="\' + span + \''


def run(sb):
    r = sb.run_python(os.path.join('tools', 'admin_colspan_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), out


bad = []

# 基线
with mutate_sandbox(require_clean=False) as sb:
    rc, res, _ = run(sb)
    print('[基线 未改] rc=%d %s' % (rc, res[:56]))
    if rc != 0:
        bad.append('基线未 PASS')

# A 退回硬编码
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    assert DYN in t, '动态 colspan 锚点未找到（改法变了？）'
    open(p, 'w', encoding='utf-8', newline='').write(
        t.replace(DYN, 'colspan="9"', 1))
    rc, res, out = run(sb)
    print('[A 退回硬编码] rc=%d %s' % (rc, res[:56]))
    hard_line = [l.strip() for l in out.splitlines() if 'colspan="9"' in l]
    for h in hard_line[:2]:
        print('      %s' % h[:70])
    if not (rc == 1 and hard_line):
        bad.append('A 硬编码退化未被抓到')

# B 删光表格 -> 必须 SKIP（不能假 PASS）
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    for tid in ('tbl-country', 'tbl-dev', 'tbl-events'):
        t = re.sub(r'<table id="%s".*?</table>' % tid, '<!-- removed -->',
                   t, flags=re.S)
    open(p, 'w', encoding='utf-8', newline='').write(t)
    rc, res, out = run(sb)
    print('[B 表格全删] rc=%d %s' % (rc, res[:56]))
    # 全删后不该给出 PASS（那是「没东西可查」的假通过）
    if 'RESULT: PASS' in res:
        bad.append('B 表格全删仍报 PASS（归属失败未出声 = 上轮那个自欺 bug）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  硬编码退化能判红；表格全删不会假通过')
sys.exit(0)

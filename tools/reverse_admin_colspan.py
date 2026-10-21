# -*- coding: utf-8 -*-
"""反向验证 admin_colspan_test（轮94 修正：去掉硬编码表名）。

## 本轮为什么失败（我自己上一轮写的脚本自欺）
轮92 我把 #tbl-dev 拆成 #tbl-lang + #tbl-screen，
而本脚本的 B 用例硬编码删 ('tbl-country','tbl-dev','tbl-events') ——
tbl-dev 已不存在，删不干净，实际还剩表，
于是「表格全删」这个用例根本没在测它声称的东西：
判据正常扫到表格给 PASS，脚本就报「B 仍假通过」。

讽刺：这个用例正是为防「归属失败仍报通过」而写的，
结果它自己因硬编码表名而失效。教训与判据本身同源 ——
**不要硬编码你无法保证存在的标识符**，要现场发现。

## 修正
  · 表名从文件正则发现（<table id="...">），不写死
  · 删之前先算「发现几张、删掉几张、还剩几张」，删不净就报错而非静默
  · A 用例的动态 colspan 写法也现场发现，不依赖具体变量名
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')


def run(sb):
    r = sb.run_python(os.path.join('tools', 'admin_colspan_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), out


def table_ids(text):
    return re.findall(r'<table id="([\w-]+)"', text)


def dynamic_colspan_expr(text):
    """现场发现动态 colspan 写法（colspan="' + xxx 形态），不写死变量名。"""
    m = re.search(r'''colspan="' \+ [^+]+''', text)
    return m.group(0) if m else None


bad = []

with mutate_sandbox(require_clean=False) as sb:
    t = open(sb.path(ADMIN), encoding='utf-8', newline='').read()
    ids = table_ids(t)
    expr = dynamic_colspan_expr(t)
    print('现场发现：表 %d 张 %s；动态 colspan 写法=%s' % (len(ids), ids, bool(expr)))
    if len(ids) < 2 or not expr:
        print('RESULT: FAIL  无法发现表或动态写法，反向验证前提不成立')
        sys.exit(1)
    rc, res, _ = run(sb)
    print('[基线] rc=%d %s' % (rc, res[:54]))
    if rc != 0:
        bad.append('基线未 PASS')

# A 退回硬编码
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    expr = dynamic_colspan_expr(t)
    t2 = t.replace(expr, 'colspan="9"', 1)
    assert t2 != t, 'A 替换未生效'
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, out = run(sb)
    hits = [l.strip() for l in out.splitlines() if 'colspan="9"' in l]
    print('[A 退回硬编码] rc=%d %s' % (rc, res[:54]))
    for h in hits[:1]:
        print('      %s' % h[:66])
    if not (rc == 1 and hits):
        bad.append('A 硬编码退化未被抓到')

# B 删光所有表（表名现场发现）
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    ids = table_ids(t)
    removed = 0
    for tid in ids:
        t2 = re.sub(r'<table id="%s".*?</table>' % re.escape(tid),
                    '<!-- removed -->', t, flags=re.S)
        if t2 != t:
            removed += 1
        t = t2
    left = table_ids(t)
    print('[B] 发现 %d 张，删掉 %d 张，剩余 %d 张' % (len(ids), removed, len(left)))
    if left:
        bad.append('B 未删净（剩 %s），用例前提不成立' % left)
    open(p, 'w', encoding='utf-8', newline='').write(t)
    rc, res, out = run(sb)
    print('[B 表格全删] rc=%d %s' % (rc, res[:54]))
    if 'RESULT: PASS' in res:
        bad.append('B 表格全删仍报 PASS（归属失败未出声）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  硬编码退化能判红；表格全删不会假通过（表名现场发现）')
sys.exit(0)

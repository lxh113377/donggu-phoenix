# -*- coding: utf-8 -*-
"""反向验证 cjk_punctuation_test 的扩面真的有牙（轮83）。

## 为什么必须做
扩面只是「把文本纳入扫描」，若正则或抽取路径有缺陷，
判据会对新面永远返回 0 —— 看起来 PASS，实际什么都没测。
所以要在沙箱里往**新纳入的面**（后台内联脚本）注入一个已知违规，
确认判据能抓到并点名。

## 三个用例覆盖三条新路径
  A 后台内联脚本的 HTML 模板串（含嵌套双引号 + 相邻空串，正是轮83 修过的形态）
  B 后台 HTML 可见文本（表头/标签类）
  C 主站内联脚本字面量（JSON-LD 那类）
每个都必须判红；再加 D：不注入时必须 PASS（排除过度反应）。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')
INDEX = os.path.join('site', 'index.html')


def run(sb):
    r = sb.run_python(os.path.join('tools', 'cjk_punctuation_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    hits = [l.strip() for l in out.splitlines() if l.strip().startswith('- [')]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), hits


bad = []

# D 基线：不注入必须 PASS
with mutate_sandbox(require_clean=False) as sb:
    rc, res, hits = run(sb)
    print('[D 未注入] rc=%d %s' % (rc, res[:56]))
    if rc != 0:
        bad.append('D 基线未 PASS（判据过度反应）')

# A 后台内联脚本的 HTML 模板串
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    anchor = "toast('已导出 '"
    if anchor not in t:
        # 退到确定存在的锚点
        anchor = "function renderEvents() {"
    assert anchor in t, 'A 锚点未找到'
    inj = ("  var _t = '<td colspan=\"9\">测试,违规</td>';\n    ")
    open(p, 'w', encoding='utf-8', newline='').write(
        t.replace(anchor, inj + anchor, 1))
    rc, res, hits = run(sb)
    print('[A 后台模板串] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('测试' in h for h in hits)):
        bad.append('A 后台内联模板串违规未被抓到')

# B 后台 HTML 可见文本
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    anchor = '<h2>访问明细'
    assert anchor in t, 'B 锚点未找到'
    t2 = t.replace(anchor, '<h2>可见文本,违规</h2>\n    ' + anchor, 1)
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, hits = run(sb)
    print('[B 后台可见文本] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('可见文本' in h for h in hits)):
        bad.append('B 后台可见文本违规未被抓到')

# C 主站内联脚本字面量
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(INDEX)
    t = open(p, encoding='utf-8', newline='').read()
    anchor = 'function boot()'
    if anchor not in t:
        anchor = '<script>'
    assert anchor in t, 'C 锚点未找到'
    t2 = t.replace(anchor, "var _x = '主站内联,违规';\n" + anchor, 1)
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, hits = run(sb)
    print('[C 主站内联脚本] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('主站内联' in h for h in hits)):
        bad.append('C 主站内联脚本违规未被抓到')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  三条新路径都能抓到违规，且未注入时不误报')
sys.exit(0)

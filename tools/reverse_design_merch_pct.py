# -*- coding: utf-8 -*-
"""反向验证 ci_design_static 的商品图判据（轮95 条件式改法）。

## 为什么必须做（这是「自己改判据让自己通过」的场景）
本轮我为了让自己的 CSS 改动通过，修改了判据逻辑：
把「.merch-shot img 禁用百分比 max-height」改成条件式
（只在 grid 行高未锁定时判红）。
「改判据让红灯变绿」是最需要独立证据的动作 ——
条件写错防护就悄悄没了，而 CI 从此永远绿。

## 依据（A/B 实测，_qa/r95/ab_gridrow.html）
  锁行高 grid-template-rows:100% -> img 196px，不溢出（百分比基准=容器高）
  未锁行高                       -> img 345px，越 shot 底 138px 并压住标签
即轮16 的因果是「未锁行高 => 百分比基准错」，
旧代码却把因果两端实现成两条独立规则，误伤「已锁行高+百分比」这个安全组合。

## 四用例（B 是关键：证明防护未降级）
  A 锁行高 + 百分比   -> PASS（本轮改动的正当性）
  B 未锁行高 + 百分比 -> 必须 FAIL（轮16 的真实危险组合仍被抓）
  C 未锁行高 + px     -> 必须 FAIL（未锁行高本身就该红）
  D 锁行高 + px       -> PASS（合法写法不误伤）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

CSS = os.path.join('site', 'assets', 'css', 'main.css')
ROW_LOCK = 'grid-template-rows:100%;grid-template-columns:100%'


def run(sb):
    r = sb.run_python(os.path.join('tools', 'ci_design_static.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    line = [l.strip() for l in out.splitlines() if '商品图' in l]
    return r.returncode, (line[-1] if line else '(无该判据行)')


def patch(sb, drop_lock=False, to_px=False):
    p = sb.path(CSS)
    t = open(p, encoding='utf-8', newline='').read()
    if drop_lock:
        assert ROW_LOCK in t, '行高锁定锚点未找到'
        t = t.replace(ROW_LOCK, '', 1)
    if to_px:
        t2 = re.sub(r'(\.merch-shot img\{[^{}]*?)max-height:100%',
                    r'\g<1>max-height:170px', t, flags=re.S)
        assert t2 != t, '百分比锚点未找到'
        t = t2
    open(p, 'w', encoding='utf-8', newline='').write(t)


bad = []
cases = [
    ('A 锁行高+百分比', False, False, True),
    ('B 未锁行高+百分比', True, False, False),
    ('C 未锁行高+px', True, True, False),   # to_px=True：真正测 px 写法
    ('D 锁行高+px', False, True, True),
]
for name, drop, to_px, want_pass in cases:
    with mutate_sandbox(require_clean=False) as sb:
        patch(sb, drop_lock=drop, to_px=to_px)
        rc, line = run(sb)
        got = (rc == 0)
        mark = 'OK' if got == want_pass else '** 判定不符 **'
        print('[%-18s] rc=%d %s' % (name, rc, line[:56]))
        print('    期望%-5s 实得%-5s -> %s' % (
            'PASS' if want_pass else 'FAIL',
            'PASS' if got else 'FAIL', mark))
        if got != want_pass:
            bad.append('%s 判定不符（防护降级或误伤）' % name)

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  条件式未降级防护：未锁行高的两种写法仍判红，合法写法不误伤')
sys.exit(0)

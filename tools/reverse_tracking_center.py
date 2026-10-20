# -*- coding: utf-8 -*-
"""反向验证 tracking_center_test：撤掉补偿，必须判红。

破坏点打在 CSS 字符串上（safe_mutation 沙箱副本，真实工作区只读）。
样本里的选择器用真实存在的 .hero-tag，确保走的是 DOM 匹配路径。
"""
import hashlib
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

CSS = os.path.join('site', 'assets', 'css', 'main.css')
REAL = os.path.join(BASE, CSS.replace('/', os.sep))


def sha():
    return hashlib.sha256(open(REAL, 'rb').read()).hexdigest()


b0 = sha()
orig = open(REAL, encoding='utf-8', newline='').read()

CASES = [
    ('A 撤掉 .hero-tag 补偿', '  margin-right:-.42em', '  /*removed*/'),
    ('B 撤掉 .hero h1 em 补偿', 'margin-right:-.62em', 'margin-right:0'),
    ('C 撤掉 .foot-copy h2 补偿', 'margin-right:-.12em', 'margin-right:0'),
]

bad = 0
try:
    for label, old, new in CASES:
        if old not in orig:
            print('[%s] 锚点不存在（可能已改法）' % label)
            bad += 1
            continue
        with mutate_sandbox(require_clean=False) as sb:
            p = sb.path(CSS)
            t = open(p, encoding='utf-8', newline='').read()
            open(p, 'w', encoding='utf-8', newline='').write(t.replace(old, new, 1))
            r = sb.run_python(os.path.join('tools', 'tracking_center_test.py'), timeout=90)
            out = (r.stdout or '') + (r.stderr or '')
            res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
            miss = [l.strip() for l in out.splitlines() if '缺补偿' in l]
            ok = r.returncode == 1 and bool(miss)
            if not ok:
                bad += 1
            print('[%s] rc=%d %s' % (label, r.returncode, res[-1][:40] if res else '(无)'))
            for m in miss[:1]:
                print('     ', m[:80])
finally:
    print()
    print('真实文件未变:', b0 == sha())

print()
if bad:
    print('RESULT: FAIL  %d 个用例未被抓到' % bad)
    sys.exit(1)
print('RESULT: PASS  三处补偿任一被撤都能判红')
sys.exit(0)

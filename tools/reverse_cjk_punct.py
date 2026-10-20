# -*- coding: utf-8 -*-
"""反向验证 cjk_punctuation_test：把全角标点改成半角，必须判红。

## 两个纪律（都是本项目踩过的坑）
1. 锚点必须落在**字符串字面量**内（U-152：落在注释里判据正确地不算违例）
   → 锚点由 pick_punct_anchor.py 从「剥注释后的字面量」里挑出
2. 替换必须**全局**（U-145：safe_mutation.patch 内部 replace 只改第一处，
   残留一处时判据 PASS 是正确的，会误判成判据失效）
   → 本脚本自己做全局替换，不用 sb.patch
3. 全程在 safe_mutation 沙箱副本操作，真实工作区只读（U-146 事故教训）
"""
import hashlib
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

DATA = os.path.join('site', 'assets', 'data', 'ar-data.js')
REAL = os.path.join(BASE, DATA.replace('/', os.sep))


def sha():
    return hashlib.sha256(open(REAL, 'rb').read()).hexdigest()


orig = open(REAL, encoding='utf-8', newline='').read()
b0 = sha()

# (说明, 全角锚点, 半角替换) —— 锚点已确认在字面量内
CASES = [
    ('A 逗号改半角', '一木成像：拖动进度，看这段樟木里的神像被让出来',
     '一木成像：拖动进度,看这段樟木里的神像被让出来'),
    ('B 冒号改半角', '一木成像：拖动进度', '一木成像:拖动进度'),
    ('C 分号改半角', '田野调查；樟木用料', '田野调查;樟木用料'),
]

bad = 0
for label, old, new in CASES:
    n = orig.count(old)
    if n == 0:
        print('[%s] 锚点不存在，用例无效' % label)
        bad += 1
        continue
    with mutate_sandbox(require_clean=False) as sb:
        p = sb.path(DATA)
        txt = open(p, encoding='utf-8', newline='').read()
        # 全局替换
        open(p, 'w', encoding='utf-8', newline='').write(txt.replace(old, new))
        r = sb.run_python(os.path.join('tools', 'cjk_punctuation_test.py'), timeout=90)
        out = (r.stdout or '') + (r.stderr or '')
        res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
        det = [l.strip() for l in out.splitlines() if '半角' in l and l.strip().startswith('- ')]
        ok = r.returncode == 1
        if not ok:
            bad += 1
        print('[%s] 锚点 %d 处 -> rc=%d %s' % (label, n, r.returncode,
                                                res[-1][:40] if res else '(无)'))
        for d in det[:1]:
            print('      ', d[:80])

print()
print('真实文件未变:', b0 == sha())
print()
if bad:
    print('RESULT: FAIL  %d 个用例未被抓到' % bad)
    sys.exit(1)
print('RESULT: PASS  判据能识别三种全角→半角违例（逗号/冒号/分号）')
sys.exit(0)

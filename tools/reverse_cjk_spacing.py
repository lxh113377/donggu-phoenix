# -*- coding: utf-8 -*-
"""反向验证 cjk_latin_spacing_test：注入混排违例，必须判红。

用 safe_mutation 沙箱（真实工作区全程只读），避免轮54 那种
open(p,'w') 自我改写把文件清空的事故。
"""
import hashlib
import os
import sys

# 本脚本在 tools/ 下运行时 sys.path[0] 就是 tools/，须显式补仓库根
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

DATA = os.path.join('site', 'assets', 'data', 'culture.js')
REAL = os.path.join(BASE, DATA.replace('/', os.sep))


def sha():
    return hashlib.sha256(open(REAL, 'rb').read()).hexdigest()


b0 = sha()

# 锚点要求：确实在字符串字面量内（不在注释里），否则判据剥注释后不算违例。
# 轮56 实测：'AR 展陈' 第一处在注释里，替换后判据正确地没抓到 ——
# 与 U-145「破坏点要打在最终生效处」同一课。
CASES = [
    # 全文各仅 1 处，均在字面量内
    ('A Latin 紧贴中文', 'AR 明信片', 'AR明信片'),
    ('B Latin 紧贴中文2', 'AR 数字展陈', 'AR数字展陈'),
    # '1987 年入党' 有 2 处，改第 1 处 -> 制造同页混排不统一（真实缺陷形态）
    ('C 数字紧贴中文', '1987 年入党', '1987年入党'),
]

bad = 0
for label, old, new in CASES:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(DATA, [(old, new)])
        except AssertionError as e:
            print('[%s] 锚点未命中: %s' % (label, str(e)[:44]))
            bad += 1
            continue
        r = sb.run_python(os.path.join('tools', 'cjk_latin_spacing_test.py'), timeout=90)
        out = (r.stdout or '') + (r.stderr or '')
        res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
        det = [l.strip() for l in out.splitlines() if '缺空格' in l or '混排写法' in l]
        ok = r.returncode == 1
        if not ok:
            bad += 1
        print('[%s] rc=%d %s' % (label, r.returncode, res[-1][:52] if res else '(无 RESULT)'))
        for d in det[:2]:
            print('      ', d[:78])

print()
print('真实文件未变:', b0 == sha())
print()
if bad == 0:
    print('RESULT: PASS  判据能识别两类混排违例')
    sys.exit(0)
print('RESULT: FAIL  %d 个用例未被抓到' % bad)
sys.exit(1)

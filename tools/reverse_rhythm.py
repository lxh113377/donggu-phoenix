# -*- coding: utf-8 -*-
'''反向验证 rhythm_test：把分级改回统一值，必须判红。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

cases = [
    ('A 全部改回统一留白', 'section#merch{padding-top:var(--sec-y-tight);padding-bottom:var(--sec-y-tight)}',
     'section#merch{padding-top:var(--sec-y);padding-bottom:var(--sec-y)}'),
    ('B scan 不再用最松级别', 'section.foot{padding-top:var(--sec-y-loose)}',
     'section.foot{padding-top:var(--sec-y)}'),
]

for label, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(CSS, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:60]))
            continue
        r = sb.run_python('tools/rhythm_test.py', timeout=60)
        out = ((r.stdout or '') + (r.stderr or ''))
        fails = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fails[:2]:
            print('    ', f)

print()
print('真实文件未变:', before == sha(CSS))
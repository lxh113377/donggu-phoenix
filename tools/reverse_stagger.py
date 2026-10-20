# -*- coding: utf-8 -*-
'''反向验证 stagger_test：删掉时序规则必须判红。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

cases = [
    ('A 删掉标题后延迟规则',
     '.sec-head + .reveal:not(.sec-head){transition-delay:120ms}',
     '.sec-head + .reveal:not(.sec-head){transition-delay:0ms}'),
    ('B 延迟值退化成 20ms',
     '.sec-head + .totem-grid > .reveal{transition-delay:120ms}',
     '.sec-head + .totem-grid > .reveal{transition-delay:20ms}'),
]

for label, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(CSS, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:50]))
            continue
        r = sb.run_python('tools/stagger_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:2]:
            print('    ', f)

print()
print('真实文件未变:', before == sha(CSS))
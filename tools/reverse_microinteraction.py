# -*- coding: utf-8 -*-
'''反向验证 microinteraction_test。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

cases = [
    ('A 删掉 close 的 hover', '#cam .close:hover{border-color:var(--she-gold);color:var(--she-gold)}', ''),
    ('B 删掉全局 focus-visible', ':focus-visible{outline:2px solid var(--she-gold);outline-offset:4px;border-radius:4px}', ''),
    ('C 删掉 nav-toggle 的 active', '.nav-toggle:active{transform:scale(.94)}', ''),
]

for label, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(CSS, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:50]))
            continue
        r = sb.run_python('tools/microinteraction_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:2]:
            print('    ', f)

print()
print('真实文件未变:', before == sha(CSS))
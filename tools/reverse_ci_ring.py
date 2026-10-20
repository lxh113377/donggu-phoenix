
# -*- coding: utf-8 -*-
"""反向验证 ci_design_static 里的 ring 判据（安全沙箱，不碰真实文件）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

css = open(CSS, encoding='utf-8').read()
totem = css[css.index('.totem-ring.b{'): css.index('}', css.index('.totem-ring.b{')) + 1]

with mutate_sandbox(require_clean=False) as sb:
    sb.patch(CSS, [(totem, '.totem-ring.b{inset:-5%;border-style:dashed;opacity:.5;animation-delay:-1.4s}')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or ''))
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if '装饰环' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip())

print()
print('真实 CSS 未变:', before == sha(CSS))

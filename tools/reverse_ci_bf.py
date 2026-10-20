
# -*- coding: utf-8 -*-
"""反向验证「不透明背景 + backdrop-filter」判据（沙箱）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

with mutate_sandbox(require_clean=False) as sb:
    # 把 toast 的 backdrop-filter 加回去
    sb.patch(CSS, [('background:rgba(18,16,15,.95);', 'background:rgba(18,16,15,.95);backdrop-filter:blur(10px);')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    print('退出码:', r.returncode)
    for l in ((r.stdout or '') + (r.stderr or '')).splitlines():
        if 'backdrop' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip())

print()
print('真实 CSS 未变:', before == sha(CSS))

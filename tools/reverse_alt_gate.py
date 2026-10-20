
# -*- coding: utf-8 -*-
"""反向验证 avatar alt 门禁（沙箱）。"""
import hashlib, re, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

JS = 'site/assets/js/main.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(JS)

with mutate_sandbox(require_clean=False) as sb:
    sb.patch(JS, [('alt="" aria-hidden="true"', 'alt="\' + (p.name || \'\') + \'"')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    print('退出码:', r.returncode)
    for l in ((r.stdout or '') + (r.stderr or '')).splitlines():
        if '头像' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip())

print()
print('真实文件未变:', before == sha(JS))

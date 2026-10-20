
# -*- coding: utf-8 -*-
"""反向验证 ci_design_static 里的 hero 判据（沙箱）。"""
import hashlib, re, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

css = open(CSS, encoding='utf-8').read()
m = re.search(r'\.hero-visual\{min-height:0;height:100%\}', css)
target = m.group(0)
print('目标规则:', target)

with mutate_sandbox(require_clean=False) as sb:
    sb.patch(CSS, [(target, '.hero-visual{min-height:58svh;height:100%}')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    print('退出码:', r.returncode)
    for l in ((r.stdout or '') + (r.stderr or '')).splitlines():
        if '首屏' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip())

print()
print('真实 CSS 未变:', before == sha(CSS))

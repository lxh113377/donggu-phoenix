
# -*- coding: utf-8 -*-
"""反向验证相对时间门禁（沙箱）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

HTML = 'site/index.html'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(HTML)

with mutate_sandbox(require_clean=False) as sb:
    sb.patch(HTML, [('一位 1987 年入党的畲族党员', '一位 38 年党龄的畲族党员')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or ''))
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if '相对时间' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip())

print()
print('真实文件未变:', before == sha(HTML))

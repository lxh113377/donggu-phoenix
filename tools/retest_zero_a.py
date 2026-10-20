
# -*- coding: utf-8 -*-
"""重测 A：两个数据文件都清空，守卫应报 SKIP。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

D1 = 'site/assets/data/culture.js'
D2 = 'site/assets/data/ar-data.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
b1, b2 = sha(D1), sha(D2)

with mutate_sandbox(require_clean=False) as sb:
    open(sb.path(D1), 'w', encoding='utf-8').write('window.CULTURE = {};\n')
    open(sb.path(D2), 'w', encoding='utf-8').write('window.AR_DATA = {};\n')
    r = sb.run_python('tools/dead_data_test.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    print('退出码=%d' % r.returncode)
    print('输出:')
    for l in out.splitlines():
        if l.strip():
            print('   ', l.strip())

print()
print('真实文件未变:', b1 == sha(D1) and b2 == sha(D2))
